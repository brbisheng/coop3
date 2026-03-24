"""Evaluate a phase-1 live run from persisted JSON artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from _demo_common import OUTPUT_DIR
from perspective_extractor.evaluate import evaluate_from_json_paths

LIVE_OUTPUT_DIR = OUTPUT_DIR / "live"


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser for the phase-1 artifact evaluator."""

    parser = argparse.ArgumentParser(
        prog="demo_evaluate_live_run",
        description=(
            "Compute lightweight structural evaluation metrics from decompose/trace/compete/stress/final JSON artifacts."
        ),
    )
    parser.add_argument("--decompose", type=Path, default=LIVE_OUTPUT_DIR / "decompose.json")
    parser.add_argument("--trace", type=Path, default=LIVE_OUTPUT_DIR / "trace.json")
    parser.add_argument("--compete", type=Path, default=LIVE_OUTPUT_DIR / "compete.json")
    parser.add_argument("--stress", type=Path, default=LIVE_OUTPUT_DIR / "stress.json")
    parser.add_argument("--final", type=Path, default=LIVE_OUTPUT_DIR / "final.json")
    parser.add_argument(
        "--output",
        type=Path,
        default=LIVE_OUTPUT_DIR / "evaluate.json",
        help="Output file for the evaluation artifact JSON.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    evaluation = evaluate_from_json_paths(
        decompose_path=args.decompose,
        trace_path=args.trace,
        compete_path=args.compete,
        stress_path=args.stress,
        final_path=args.final,
    )

    payload = evaluation.to_dict()
    rendered = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True)
    print(rendered)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered + "\n", encoding="utf-8")
    print(f"Saved evaluation artifact to: {args.output}")


if __name__ == "__main__":
    main()
