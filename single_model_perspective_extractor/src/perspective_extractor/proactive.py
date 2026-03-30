"""Proactive rerun trigger rules for phase-1 pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .evaluate import EvaluationMetricSnapshot


@dataclass(frozen=True, slots=True)
class ProactiveTriggerConfig:
    """Thresholds used to decide whether a targeted rerun is required."""

    min_actor_count: int = 2


@dataclass(frozen=True, slots=True)
class ProactiveAction:
    """Record of one proactive targeted rerun decision and its impact."""

    trigger_reason: str
    rerun_stage: str
    before: dict[str, Any]
    after: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "trigger_reason": self.trigger_reason,
            "rerun_stage": self.rerun_stage,
            "before": self.before,
            "after": self.after,
        }


def collect_proactive_triggers(
    metrics: EvaluationMetricSnapshot,
    *,
    config: ProactiveTriggerConfig,
) -> list[tuple[str, str]]:
    """Return ordered (reason, stage) trigger pairs for a proactive rerun flow."""

    triggers: list[tuple[str, str]] = []
    if metrics.actor_count < config.min_actor_count:
        triggers.append((f"actor_count<{config.min_actor_count}", "decompose"))
    if not metrics.predictions_differ:
        triggers.append(("predictions_differ=False", "compete"))
    if metrics.surprise_count == 0:
        triggers.append(("surprise_count=0", "stress"))
    return triggers


__all__ = [
    "ProactiveAction",
    "ProactiveTriggerConfig",
    "collect_proactive_triggers",
]
