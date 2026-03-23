"""Standalone CLI entry point for the phase-1 reasoning stages."""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Sequence

from .compete import run_compete
from .decompose import run_decompose
from .final import run_final
from .stress import run_stress
from .trace import run_trace


JsonDict = dict[str, Any]


def _add_live_model_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--model",
        help="Required OpenRouter model name for CLI execution.",
    )
    parser.add_argument(
        "--api-key",
        help="OpenRouter API key. Falls back to OPENROUTER_API_KEY when omitted.",
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level CLI parser."""

    parser = argparse.ArgumentParser(
        prog="perspective-extractor",
        description=(
            "Run the dedicated phase-1 commands directly. Each command accepts plain "
            "text or a text file, emits structured JSON, and can save its artifact "
            "without depending on the unfinished wider system."
        ),
    )
    _add_live_model_arguments(parser)
    subparsers = parser.add_subparsers(dest="command", required=True)

    decompose_parser = subparsers.add_parser(
        "decompose",
        help="Decompose a problem into actors, nodes, and constraints.",
    )
    _add_problem_input_arguments(decompose_parser)
    _add_output_arguments(decompose_parser)

    trace_parser = subparsers.add_parser(
        "trace",
        help="Build an ordered consequence chain from a problem statement.",
    )
    _add_problem_input_arguments(trace_parser)
    trace_parser.add_argument(
        "--trace-target",
        help="Optional explicit target to trace instead of the inferred default.",
    )
    _add_output_arguments(trace_parser)

    compete_parser = subparsers.add_parser(
        "compete",
        help="Generate two competing mechanisms with divergent predictions.",
    )
    _add_problem_input_arguments(compete_parser)
    compete_parser.add_argument(
        "--trace-target",
        help="Optional explicit target to trace before building competing mechanisms.",
    )
    _add_output_arguments(compete_parser)

    stress_parser = subparsers.add_parser(
        "stress",
        help="Stress-test the competing mechanisms with falsification and surprise ledgers.",
    )
    _add_problem_input_arguments(stress_parser)
    stress_parser.add_argument(
        "--trace-target",
        help="Optional explicit target to trace before stress-testing.",
    )
    _add_output_arguments(stress_parser)

    final_parser = subparsers.add_parser(
        "final",
        help="Assemble the dense final phase-1 report from direct stage execution.",
    )
    _add_problem_input_arguments(final_parser)
    final_parser.add_argument(
        "--trace-target",
        help="Optional explicit target to trace before assembling the final report.",
    )
    _add_output_arguments(final_parser)

    return parser


def _add_problem_input_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "input_text",
        nargs="?",
        help="Plain problem text to analyze.",
    )
    parser.add_argument(
        "--input-file",
        type=Path,
        help="Read plain problem text from a UTF-8 file.",
    )


def _add_output_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--format",
        choices=("json",),
        default="json",
        help="Stable output format. JSON remains the primary machine-readable mode.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path where the JSON artifact should also be written.",
    )


def _resolve_live_model_config(args: argparse.Namespace) -> tuple[str, str]:
    model = (args.model or "").strip()
    api_key = (args.api_key or os.environ.get("OPENROUTER_API_KEY", "")).strip()

    if not model:
        raise ValueError("Provide --model for CLI execution")
    if not api_key:
        raise ValueError(
            "Provide --api-key or set OPENROUTER_API_KEY for CLI execution"
        )
    return model, api_key


def _resolve_problem_text(args: argparse.Namespace) -> str:
    input_text = args.input_text.strip() if args.input_text else None
    input_file = args.input_file

    if input_text and input_file is not None:
        raise ValueError("Provide either input_text or --input-file, not both")
    if input_file is not None:
        problem_text = input_file.read_text(encoding="utf-8").strip()
    elif input_text:
        problem_text = input_text
    else:
        raise ValueError("Provide input_text or --input-file")

    if not problem_text:
        raise ValueError("problem_text must not be empty")
    return problem_text


def _emit_payload(payload: JsonDict, *, output_path: Path | None) -> None:
    rendered = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True)
    print(rendered)
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered + "\n", encoding="utf-8")


def _decompose_payload(problem_text: str, *, model: str, api_key: str) -> JsonDict:
    return asdict(run_decompose(problem_text, model=model, api_key=api_key))


def _trace_payload(problem_text: str, *, model: str, api_key: str, trace_target: str | None = None) -> JsonDict:
    decompose_result = run_decompose(problem_text, model=model, api_key=api_key)
    return asdict(run_trace(decompose_result, trace_target=trace_target, model=model, api_key=api_key))


def _compete_payload(problem_text: str, *, model: str, api_key: str, trace_target: str | None = None) -> JsonDict:
    decompose_result = run_decompose(problem_text, model=model, api_key=api_key)
    trace_result = run_trace(decompose_result, trace_target=trace_target, model=model, api_key=api_key)
    return asdict(run_compete(decompose_result, trace_result, model=model, api_key=api_key))


def _stress_payload(problem_text: str, *, model: str, api_key: str, trace_target: str | None = None) -> JsonDict:
    decompose_result = run_decompose(problem_text, model=model, api_key=api_key)
    trace_result = run_trace(decompose_result, trace_target=trace_target, model=model, api_key=api_key)
    compete_result = run_compete(decompose_result, trace_result, model=model, api_key=api_key)
    return asdict(run_stress(decompose_result, trace_result, compete_result, model=model, api_key=api_key))


def _final_payload(problem_text: str, *, model: str, api_key: str, trace_target: str | None = None) -> JsonDict:
    decompose_result = run_decompose(problem_text, model=model, api_key=api_key)
    trace_result = run_trace(decompose_result, trace_target=trace_target, model=model, api_key=api_key)
    compete_result = run_compete(decompose_result, trace_result, model=model, api_key=api_key)
    stress_result = run_stress(decompose_result, trace_result, compete_result, model=model, api_key=api_key)
    return asdict(run_final(decompose_result, trace_result, compete_result, stress_result, model=model, api_key=api_key))


def main(argv: Sequence[str] | None = None) -> int:
    """Run the phase-1 CLI."""

    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        model, api_key = _resolve_live_model_config(args)
        problem_text = _resolve_problem_text(args)

        if args.command == "decompose":
            payload = _decompose_payload(problem_text, model=model, api_key=api_key)
        elif args.command == "trace":
            payload = _trace_payload(problem_text, model=model, api_key=api_key, trace_target=args.trace_target)
        elif args.command == "compete":
            payload = _compete_payload(problem_text, model=model, api_key=api_key, trace_target=args.trace_target)
        elif args.command == "stress":
            payload = _stress_payload(problem_text, model=model, api_key=api_key, trace_target=args.trace_target)
        elif args.command == "final":
            payload = _final_payload(problem_text, model=model, api_key=api_key, trace_target=args.trace_target)
        else:
            parser.error(f"Unknown command: {args.command}")
            return 2
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    _emit_payload(payload, output_path=args.output)
    return 0


__all__ = ["build_parser", "main"]
