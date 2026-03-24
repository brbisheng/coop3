"""Live phase-1 demo for the decompose stage."""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path

from perspective_extractor.decompose import run_decompose

SAMPLE_PROBLEM = (
    "How could a disruption at the main fuel import terminal force shippers, customs, and regional distributors "
    "to reroute through alternate ports and inland pipeline chokepoints over the next 30 days?"
)


def _require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Set {name} before running this live demo")
    return value


def main() -> None:
    model = _require_env("OPENROUTER_MODEL")
    api_key = _require_env("OPENROUTER_API_KEY")

    result = run_decompose(SAMPLE_PROBLEM, model=model, api_key=api_key)
    rendered = json.dumps(asdict(result), indent=2, ensure_ascii=False, sort_keys=True)

    repo_root = Path(__file__).resolve().parents[1]
    output_path = repo_root / "examples" / "out" / "decompose_example.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered + "\n", encoding="utf-8")

    print(rendered)
    print(f"\nSaved demo output to: {output_path}")


if __name__ == "__main__":
    main()
