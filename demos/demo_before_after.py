"""Run baseline-vs-phase1 live comparison and persist side-by-side outputs."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from pathlib import Path

from _demo_common import SAMPLE_PROBLEM
from perspective_extractor.baseline import run_baseline_analysis
from perspective_extractor.pipeline import run_phase1_pipeline

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "examples" / "out" / "before_after"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="demo_before_after",
        description="Generate baseline and phase-1 outputs with the same OpenRouter model.",
    )
    parser.add_argument("--model", required=True, help="OpenRouter model name")
    parser.add_argument(
        "--api-key",
        help="OpenRouter API key; falls back to OPENROUTER_API_KEY environment variable.",
    )
    parser.add_argument("--question", default=SAMPLE_PROBLEM, help="Question to analyze")
    return parser


def _resolve_api_key(cli_api_key: str | None) -> str:
    api_key = (cli_api_key or os.environ.get("OPENROUTER_API_KEY", "")).strip()
    if not api_key:
        raise ValueError("Provide --api-key or set OPENROUTER_API_KEY")
    return api_key


def _render_comparison_md(*, question: str, baseline_md: str, final_payload: dict[str, object]) -> str:
    section_map = {
        "actor/node coverage": "key_actors_and_nodes",
        "mechanism depth": "critical_mechanism_chains",
        "competing predictions": "competing_explanations_and_divergent_predictions",
        "hidden assumptions": "main_uncertainties_and_hidden_assumptions",
        "surprise usefulness": "likely_surprises",
    }

    lines = [
        "# Before vs After (Baseline vs Phase-1)",
        "",
        "## Question",
        "",
        question.strip(),
        "",
        "## Baseline (single-shot)",
        "",
        "The baseline content is stored in `baseline.md` and included below for manual reading:",
        "",
        baseline_md.strip(),
        "",
        "## Phase-1 Final (structured)",
        "",
        "- Structured output source: `final.json`",
        "",
        "## Human-readable comparison",
        "",
    ]

    for label, field_name in section_map.items():
        lines.extend([f"### {label}", "", "**Baseline**", "", "- See baseline narrative above.", "", "**Phase-1 Final**", ""])
        values = final_payload.get(field_name, [])
        if isinstance(values, list) and values:
            lines.extend(f"- {value}" for value in values)
        else:
            lines.append("- (No content)")
        lines.append("")

    executive_summary = final_payload.get("executive_summary")
    if isinstance(executive_summary, str) and executive_summary.strip():
        lines.extend(["### phase-1 executive summary", "", executive_summary.strip(), ""])

    return "\n".join(lines).rstrip() + "\n"


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

    baseline_md = run_baseline_analysis(question, model=model, api_key=api_key)
    phase1_artifacts = run_phase1_pipeline(question, model=model, api_key=api_key)
    final_payload = asdict(phase1_artifacts.final_report)

    comparison_md = _render_comparison_md(
        question=question,
        baseline_md=baseline_md,
        final_payload=final_payload,
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    baseline_path = OUTPUT_DIR / "baseline.md"
    final_path = OUTPUT_DIR / "final.json"
    comparison_path = OUTPUT_DIR / "comparison.md"

    baseline_path.write_text(baseline_md.strip() + "\n", encoding="utf-8")
    final_path.write_text(json.dumps(final_payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    comparison_path.write_text(comparison_md, encoding="utf-8")

    print("Saved before/after outputs:")
    for path in (baseline_path, final_path, comparison_path):
        print(f"- {path}")


if __name__ == "__main__":
    main()
