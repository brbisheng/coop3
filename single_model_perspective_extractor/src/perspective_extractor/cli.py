"""Standalone CLI entry point for the phase-1 rigor engine."""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Sequence

from .compete import build_competing_mechanisms, run_compete
from .decompose import decompose_problem, run_decompose
from .final import build_final_report, run_final
from .stress import build_stress_test, run_stress
from .trace import build_trace, run_trace

JsonDict = dict[str, Any]


def _add_live_model_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--model",
        help="Required OpenRouter model name for live execution.",
    )
    parser.add_argument(
        "--api-key",
        help="OpenRouter API key. Falls back to OPENROUTER_API_KEY when omitted.",
    )
    parser.add_argument(
        "--use-fixture",
        action="store_true",
        help="Run the deterministic local test fixture path instead of the live OpenRouter path.",
    )


def _add_problem_input_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--question",
        help="Plain question text to analyze.",
    )
    parser.add_argument(
        "--input-file",
        type=Path,
        help="Read plain question text from a UTF-8 file.",
    )


def _add_output_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
        help="Render stdout and --output as either machine-readable JSON or a markdown artifact.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path where the rendered JSON or markdown artifact should also be written.",
    )


def _build_stage_parser(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    name: str,
    *,
    help_text: str,
    trace_target: bool = False,
) -> argparse.ArgumentParser:
    parser = subparsers.add_parser(name, help=help_text)
    _add_live_model_arguments(parser)
    _add_problem_input_arguments(parser)
    if trace_target:
        parser.add_argument(
            "--trace-target",
            help="Optional explicit target to trace instead of the inferred default.",
        )
    _add_output_arguments(parser)
    return parser


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level CLI parser."""

    parser = argparse.ArgumentParser(
        prog="perspective-extractor",
        description=(
            "Run the phase-1 rigor engine (decompose -> trace -> compete -> stress -> final) against a live OpenRouter model. "
            "Legacy perspective-extraction stages are intentionally non-core and not exposed in this CLI; fixture mode is opt-in for tests and demos only."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    _build_stage_parser(
        subparsers,
        "decompose",
        help_text="Decompose a question into actors, nodes, and constraints.",
    )
    _build_stage_parser(
        subparsers,
        "trace",
        help_text="Build an ordered consequence chain from a question.",
        trace_target=True,
    )
    _build_stage_parser(
        subparsers,
        "compete",
        help_text="Generate two competing mechanisms with divergent predictions.",
        trace_target=True,
    )
    _build_stage_parser(
        subparsers,
        "stress",
        help_text="Stress-test the competing mechanisms with falsification and surprise ledgers.",
        trace_target=True,
    )
    _build_stage_parser(
        subparsers,
        "final",
        help_text="Assemble the dense final phase-1 report from direct stage execution.",
        trace_target=True,
    )

    return parser


def _resolve_problem_text(args: argparse.Namespace) -> str:
    question = args.question.strip() if args.question else None
    input_file = args.input_file

    if question and input_file is not None:
        raise ValueError("Provide either --question or --input-file, not both")
    if input_file is not None:
        problem_text = input_file.read_text(encoding="utf-8").strip()
    elif question:
        problem_text = question
    else:
        raise ValueError("Provide --question or --input-file")

    if not problem_text:
        raise ValueError("question must not be empty")
    return problem_text


def _resolve_live_model_config(args: argparse.Namespace) -> tuple[str, str]:
    model = (args.model or "").strip()
    api_key = (args.api_key or os.environ.get("OPENROUTER_API_KEY", "")).strip()

    if not model:
        raise ValueError("Provide --model for live CLI execution")
    if not api_key:
        raise ValueError(
            "Provide --api-key or set OPENROUTER_API_KEY for live CLI execution"
        )
    return model, api_key


def _emit_payload(
    command: str,
    payload: JsonDict,
    *,
    output_path: Path | None,
    output_format: str,
) -> None:
    rendered = _render_payload(command, payload, output_format=output_format)
    print(rendered)
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered + "\n", encoding="utf-8")


def _render_payload(command: str, payload: JsonDict, *, output_format: str) -> str:
    if output_format == "json":
        return json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True)
    if output_format == "markdown":
        return _render_markdown(command, payload)
    raise ValueError(f"Unsupported output format: {output_format}")


def _render_markdown(command: str, payload: JsonDict) -> str:
    pretty_json = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True)
    lines = [
        f"# perspective-extractor {command}",
        "",
        "## Output",
        "",
        "```json",
        pretty_json,
        "```",
    ]
    return "\n".join(lines)


def _decompose_payload(problem_text: str, *, use_fixture: bool, model: str | None = None, api_key: str | None = None) -> JsonDict:
    if use_fixture:
        return asdict(decompose_problem(problem_text))
    if model is None or api_key is None:
        raise ValueError("Live decompose execution requires model and api_key")
    return asdict(run_decompose(problem_text, model=model, api_key=api_key))


def _trace_payload(
    problem_text: str,
    *,
    use_fixture: bool,
    model: str | None = None,
    api_key: str | None = None,
    trace_target: str | None = None,
) -> JsonDict:
    if use_fixture:
        decompose_result = decompose_problem(problem_text)
        return asdict(build_trace(decompose_result, trace_target=trace_target))
    if model is None or api_key is None:
        raise ValueError("Live trace execution requires model and api_key")
    decompose_result = run_decompose(problem_text, model=model, api_key=api_key)
    return asdict(
        run_trace(
            decompose_result,
            trace_target=trace_target,
            model=model,
            api_key=api_key,
        )
    )


def _compete_payload(
    problem_text: str,
    *,
    use_fixture: bool,
    model: str | None = None,
    api_key: str | None = None,
    trace_target: str | None = None,
) -> JsonDict:
    if use_fixture:
        decompose_result = decompose_problem(problem_text)
        trace_result = build_trace(decompose_result, trace_target=trace_target)
        return asdict(build_competing_mechanisms(decompose_result, trace_result))
    if model is None or api_key is None:
        raise ValueError("Live compete execution requires model and api_key")
    decompose_result = run_decompose(problem_text, model=model, api_key=api_key)
    trace_result = run_trace(
        decompose_result,
        trace_target=trace_target,
        model=model,
        api_key=api_key,
    )
    return asdict(run_compete(decompose_result, trace_result, model=model, api_key=api_key))


def _stress_payload(
    problem_text: str,
    *,
    use_fixture: bool,
    model: str | None = None,
    api_key: str | None = None,
    trace_target: str | None = None,
) -> JsonDict:
    if use_fixture:
        decompose_result = decompose_problem(problem_text)
        trace_result = build_trace(decompose_result, trace_target=trace_target)
        compete_result = build_competing_mechanisms(decompose_result, trace_result)
        return asdict(build_stress_test(decompose_result, trace_result, compete_result))
    if model is None or api_key is None:
        raise ValueError("Live stress execution requires model and api_key")
    decompose_result = run_decompose(problem_text, model=model, api_key=api_key)
    trace_result = run_trace(
        decompose_result,
        trace_target=trace_target,
        model=model,
        api_key=api_key,
    )
    compete_result = run_compete(decompose_result, trace_result, model=model, api_key=api_key)
    return asdict(
        run_stress(
            decompose_result,
            trace_result,
            compete_result,
            model=model,
            api_key=api_key,
        )
    )


def _final_payload(
    problem_text: str,
    *,
    use_fixture: bool,
    model: str | None = None,
    api_key: str | None = None,
    trace_target: str | None = None,
) -> JsonDict:
    if use_fixture:
        decompose_result = decompose_problem(problem_text)
        trace_result = build_trace(decompose_result, trace_target=trace_target)
        compete_result = build_competing_mechanisms(decompose_result, trace_result)
        stress_result = build_stress_test(decompose_result, trace_result, compete_result)
        return asdict(
            build_final_report(
                decompose_result,
                trace_result,
                compete_result,
                stress_result,
            )
        )
    if model is None or api_key is None:
        raise ValueError("Live final execution requires model and api_key")
    decompose_result = run_decompose(problem_text, model=model, api_key=api_key)
    trace_result = run_trace(
        decompose_result,
        trace_target=trace_target,
        model=model,
        api_key=api_key,
    )
    compete_result = run_compete(decompose_result, trace_result, model=model, api_key=api_key)
    stress_result = run_stress(
        decompose_result,
        trace_result,
        compete_result,
        model=model,
        api_key=api_key,
    )
    return asdict(
        run_final(
            decompose_result,
            trace_result,
            compete_result,
            stress_result,
            model=model,
            api_key=api_key,
        )
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Run the phase-1 CLI."""

    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code)

    try:
        problem_text = _resolve_problem_text(args)
        model: str | None = None
        api_key: str | None = None
        if not args.use_fixture:
            model, api_key = _resolve_live_model_config(args)

        if args.command == "decompose":
            payload = _decompose_payload(
                problem_text,
                use_fixture=args.use_fixture,
                model=model,
                api_key=api_key,
            )
        elif args.command == "trace":
            payload = _trace_payload(
                problem_text,
                use_fixture=args.use_fixture,
                model=model,
                api_key=api_key,
                trace_target=args.trace_target,
            )
        elif args.command == "compete":
            payload = _compete_payload(
                problem_text,
                use_fixture=args.use_fixture,
                model=model,
                api_key=api_key,
                trace_target=args.trace_target,
            )
        elif args.command == "stress":
            payload = _stress_payload(
                problem_text,
                use_fixture=args.use_fixture,
                model=model,
                api_key=api_key,
                trace_target=args.trace_target,
            )
        elif args.command == "final":
            payload = _final_payload(
                problem_text,
                use_fixture=args.use_fixture,
                model=model,
                api_key=api_key,
                trace_target=args.trace_target,
            )
        else:
            parser.error(f"Unknown command: {args.command}")
            return 2
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    _emit_payload(
        args.command,
        payload,
        output_path=args.output,
        output_format=args.format,
    )
    return 0


__all__ = ["build_parser", "main"]
