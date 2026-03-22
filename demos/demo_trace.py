"""Runnable phase-1 demo for the trace stage."""

from __future__ import annotations

from _demo_common import SAMPLE_PROBLEM, print_json_artifact, save_json_artifact
from perspective_extractor.decompose import decompose_problem
from perspective_extractor.trace import build_trace

TRACE_TARGET = "Alternate-port rerouting after a fuel terminal disruption"


def main() -> None:
    decompose_result = decompose_problem(SAMPLE_PROBLEM)
    artifact = build_trace(decompose_result, trace_target=TRACE_TARGET)
    print_json_artifact(artifact)
    output_path = save_json_artifact(artifact, "trace_example.json")
    print(f"\nSaved demo output to: {output_path}")


if __name__ == "__main__":
    main()
