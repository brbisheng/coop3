"""Lightweight evaluation helpers for phase-1 artifact bundles.

This module intentionally starts small: it computes checkable structural metrics from
phase-1 artifacts and reserves stable output slots for future score families
(ANCS / MNR / SDR / SUR / DPQ / RSMS).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Mapping

REQUIRED_FINAL_REPORT_FIELDS = (
    "key_actors_and_nodes",
    "critical_mechanism_chains",
    "competing_explanations_and_divergent_predictions",
    "likely_surprises",
    "main_uncertainties_and_hidden_assumptions",
)


@dataclass(frozen=True, slots=True)
class EvaluationMetricSnapshot:
    """Current lightweight phase-1 metrics extracted from five core artifacts."""

    actor_count: int
    node_count: int
    trace_depth: int
    competing_mechanism_count: int
    has_exactly_two_competing_mechanisms: bool
    predictions_differ: bool
    hidden_assumption_count: int
    surprise_count: int
    final_report_section_presence: dict[str, bool]


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    """Stable evaluation artifact envelope for forward-compatible scoring expansion."""

    artifact_type: str = "phase1_evaluation"
    artifact_version: str = "0.1.0"
    metrics: EvaluationMetricSnapshot = field(default_factory=lambda: EvaluationMetricSnapshot(
        actor_count=0,
        node_count=0,
        trace_depth=0,
        competing_mechanism_count=0,
        has_exactly_two_competing_mechanisms=False,
        predictions_differ=False,
        hidden_assumption_count=0,
        surprise_count=0,
        final_report_section_presence={field_name: False for field_name in REQUIRED_FINAL_REPORT_FIELDS},
    ))
    # Placeholder score slots: intentionally fixed keys for future evolution.
    future_scores: dict[str, float | None] = field(default_factory=lambda: {
        "ANCS": None,
        "MNR": None,
        "SDR": None,
        "SUR": None,
        "DPQ": None,
        "RSMS": None,
    })

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dictionary."""

        return asdict(self)


def load_json_artifact(path: str | Path) -> dict[str, Any]:
    """Load one artifact JSON file into a dictionary."""

    artifact_path = Path(path)
    return json.loads(artifact_path.read_text(encoding="utf-8"))


def evaluate_phase1_artifacts(
    *,
    decompose_artifact: Mapping[str, Any],
    trace_artifact: Mapping[str, Any],
    compete_artifact: Mapping[str, Any],
    stress_artifact: Mapping[str, Any],
    final_artifact: Mapping[str, Any],
) -> EvaluationResult:
    """Evaluate the minimal check set from five phase-1 artifacts."""

    actor_cards = decompose_artifact.get("actor_cards") or []
    node_cards = decompose_artifact.get("node_cards") or []
    consequence_chain = trace_artifact.get("consequence_chain") or []
    mechanisms = compete_artifact.get("competing_mechanisms") or []
    falsification_ledger = stress_artifact.get("falsification_ledger") or []
    surprise_ledger = stress_artifact.get("surprise_ledger") or []

    normalized_predictions = {
        str(mechanism.get("prediction", "")).strip().casefold()
        for mechanism in mechanisms
        if isinstance(mechanism, Mapping)
    }
    normalized_predictions.discard("")

    final_section_presence = {
        field_name: bool(final_artifact.get(field_name))
        for field_name in REQUIRED_FINAL_REPORT_FIELDS
    }

    metrics = EvaluationMetricSnapshot(
        actor_count=len(actor_cards),
        node_count=len(node_cards),
        trace_depth=len(consequence_chain),
        competing_mechanism_count=len(mechanisms),
        has_exactly_two_competing_mechanisms=len(mechanisms) == 2,
        predictions_differ=len(normalized_predictions) > 1,
        hidden_assumption_count=sum(
            1
            for entry in falsification_ledger
            if isinstance(entry, Mapping) and str(entry.get("hidden_assumption", "")).strip()
        ),
        surprise_count=len(surprise_ledger),
        final_report_section_presence=final_section_presence,
    )
    return EvaluationResult(metrics=metrics)


def evaluate_from_json_paths(
    *,
    decompose_path: str | Path,
    trace_path: str | Path,
    compete_path: str | Path,
    stress_path: str | Path,
    final_path: str | Path,
) -> EvaluationResult:
    """File-based evaluation entrypoint for stable artifact-driven workflows."""

    return evaluate_phase1_artifacts(
        decompose_artifact=load_json_artifact(decompose_path),
        trace_artifact=load_json_artifact(trace_path),
        compete_artifact=load_json_artifact(compete_path),
        stress_artifact=load_json_artifact(stress_path),
        final_artifact=load_json_artifact(final_path),
    )


__all__ = [
    "EvaluationMetricSnapshot",
    "EvaluationResult",
    "REQUIRED_FINAL_REPORT_FIELDS",
    "evaluate_from_json_paths",
    "evaluate_phase1_artifacts",
    "load_json_artifact",
]
