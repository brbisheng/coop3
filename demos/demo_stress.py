"""Runnable phase-1 demo for the stress stage."""

from __future__ import annotations

from _demo_common import SAMPLE_PROBLEM, print_json_artifact, save_json_artifact
from perspective_extractor.compete import build_competing_mechanisms
from perspective_extractor.decompose import decompose_problem
from perspective_extractor.stress import build_stress_test
from perspective_extractor.trace import build_trace

TRACE_TARGET = "Alternate-port rerouting after a fuel terminal disruption"


def main() -> None:
    decompose_result = decompose_problem(SAMPLE_PROBLEM)
    trace_result = build_trace(decompose_result, trace_target=TRACE_TARGET)
    compete_result = build_competing_mechanisms(decompose_result, trace_result)
    artifact = build_stress_test(decompose_result, trace_result, compete_result)
    print_json_artifact(artifact)
    output_path = save_json_artifact(artifact, "stress_example.json")
    print(f"\nSaved demo output to: {output_path}")


if __name__ == "__main__":
    main()
