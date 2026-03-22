"""Minimal runnable demo for the phase-1 decompose module."""

from __future__ import annotations

from pathlib import Path

from perspective_extractor.decompose import decompose_to_json, save_decompose_result

SAMPLE_PROBLEM = (
    "How could a disruption at the main fuel import terminal force shippers, customs, and regional distributors "
    "to reroute through alternate ports and inland pipeline chokepoints over the next 30 days?"
)


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    output_path = repo_root / "examples" / "out" / "decompose_example.json"
    print(decompose_to_json(SAMPLE_PROBLEM))
    save_decompose_result(SAMPLE_PROBLEM, output_path)
    print(f"\nSaved demo output to: {output_path}")


if __name__ == "__main__":
    main()
