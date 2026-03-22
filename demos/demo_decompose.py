"""Runnable phase-1 demo for the decompose stage."""

from __future__ import annotations

from _demo_common import SAMPLE_PROBLEM, print_json_artifact, save_json_artifact
from perspective_extractor.decompose import decompose_problem


def main() -> None:
    artifact = decompose_problem(SAMPLE_PROBLEM)
    print_json_artifact(artifact)
    output_path = save_json_artifact(artifact, "decompose_example.json")
    print(f"\nSaved demo output to: {output_path}")


if __name__ == "__main__":
    main()
