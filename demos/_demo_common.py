"""Shared helpers for runnable phase-1 demos from the repository root."""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_SRC = REPO_ROOT / "single_model_perspective_extractor" / "src"
if str(PACKAGE_SRC) not in sys.path:
    sys.path.insert(0, str(PACKAGE_SRC))

OUTPUT_DIR = REPO_ROOT / "examples" / "out"
SAMPLE_PROBLEM = (
    "How could a disruption at the main fuel import terminal force shippers, customs, and regional distributors "
    "to reroute through alternate ports and inland pipeline chokepoints over the next 30 days?"
)


def artifact_to_dict(artifact: Any) -> dict[str, Any]:
    """Convert a dataclass artifact into a JSON-serializable dictionary."""

    return asdict(artifact)



def print_json_artifact(artifact: Any) -> None:
    """Pretty-print a structured artifact to stdout."""

    print(json.dumps(artifact_to_dict(artifact), indent=2, ensure_ascii=False, sort_keys=True))



def save_json_artifact(artifact: Any, filename: str) -> Path:
    """Save a structured artifact under examples/out/."""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    destination = OUTPUT_DIR / filename
    destination.write_text(
        json.dumps(artifact_to_dict(artifact), indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return destination
