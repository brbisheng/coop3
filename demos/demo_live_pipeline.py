"""Official live smoke runner for the full phase-1 pipeline."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from pathlib import Path

from _demo_common import OUTPUT_DIR
from perspective_extractor.compete import run_compete
from perspective_extractor.decompose import run_decompose
from perspective_extractor.final import run_final
from perspective_extractor.stress import run_stress
from perspective_extractor.trace import run_trace

LIVE_OUTPUT_DIR = OUTPUT_DIR / "live"


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser for the live smoke runner."""

    parser = argparse.ArgumentParser(
        prog="demo_live_pipeline",
        description="Run decompose->trace->compete->stress->final via live OpenRouter calls and persist each artifact.",
    )
    parser.add_argument("--model", required=True, help="OpenRouter model name.")
    parser.add_argument(
        "--api-key",
        help="OpenRouter API key. Falls back to OPENROUTER_API_KEY when omitted.",
    )
    parser.add_argument("--question", required=True, help="Question to analyze.")
    return parser


def _resolve_api_key(cli_api_key: str | None) -> str:
    api_key = (cli_api_key or os.environ.get("OPENROUTER_API_KEY", "")).strip()
    if not api_key:
        raise ValueError("Provide --api-key or set OPENROUTER_API_KEY")
    return api_key


def _save_artifact(data: object, filename: str) -> Path:
    LIVE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = LIVE_OUTPUT_DIR / filename
    output_path.write_text(
        json.dumps(asdict(data), indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_path


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    model = args.model.strip()
    question = args.question.strip()
    if not model:
        raise ValueError("--model must not be empty")
    if not question:
        raise ValueError("--question must not be empty")

    api_key = _resolve_api_key(args.api_key)

    decompose_result = run_decompose(question, model=model, api_key=api_key)
    decompose_path = _save_artifact(decompose_result, "01_decompose.json")

    trace_result = run_trace(decompose_result, model=model, api_key=api_key)
    trace_path = _save_artifact(trace_result, "02_trace.json")

    compete_result = run_compete(decompose_result, trace_result, model=model, api_key=api_key)
    compete_path = _save_artifact(compete_result, "03_compete.json")

    stress_result = run_stress(decompose_result, trace_result, compete_result, model=model, api_key=api_key)
    stress_path = _save_artifact(stress_result, "04_stress.json")

    final_report = run_final(
        decompose_result,
        trace_result,
        compete_result,
        stress_result,
        model=model,
        api_key=api_key,
    )
    final_path = _save_artifact(final_report, "05_final.json")

    print("Saved live pipeline artifacts:")
    for path in (decompose_path, trace_path, compete_path, stress_path, final_path):
        print(f"- {path}")


if __name__ == "__main__":
    main()
