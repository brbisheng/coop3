"""Runnable phase-1 demo for the final stage."""

from __future__ import annotations

from _demo_common import OUTPUT_DIR, SAMPLE_PROBLEM
from perspective_extractor.compete import build_competing_mechanisms
from perspective_extractor.decompose import decompose_problem
from perspective_extractor.final import build_final_report
from perspective_extractor.stress import build_stress_test
from perspective_extractor.trace import build_trace

TRACE_TARGET = "Alternate-port rerouting after a fuel terminal disruption"


SECTION_LABELS = {
    "key_actors_and_nodes": "Key Actors and Nodes",
    "critical_mechanism_chains": "Critical Mechanism Chains",
    "competing_explanations_and_divergent_predictions": "Competing Explanations and Divergent Predictions",
    "likely_surprises": "Likely Surprises",
    "main_uncertainties_and_hidden_assumptions": "Main Uncertainties / Hidden Assumptions",
}


def render_markdown_report(report) -> str:
    lines = ["# Final Dense Report", ""]
    if report.executive_summary:
        lines.extend(["## Executive Summary", "", report.executive_summary, ""])

    for field_name, heading in SECTION_LABELS.items():
        lines.extend([f"## {heading}", ""])
        for item in getattr(report, field_name):
            lines.append(f"- {item}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"



def main() -> None:
    decompose_result = decompose_problem(SAMPLE_PROBLEM)
    trace_result = build_trace(decompose_result, trace_target=TRACE_TARGET)
    compete_result = build_competing_mechanisms(decompose_result, trace_result)
    stress_result = build_stress_test(decompose_result, trace_result, compete_result)
    report = build_final_report(decompose_result, trace_result, compete_result, stress_result)

    markdown = render_markdown_report(report)
    print(markdown)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "final_example.md"
    output_path.write_text(markdown, encoding="utf-8")
    print(f"Saved demo output to: {output_path}")


if __name__ == "__main__":
    main()
