"""Core compete stage for phase-1 competing mechanism cards."""

from __future__ import annotations

from collections.abc import Iterable

from .models import CompeteResult, CompetingMechanism, DecomposeResult, TraceResult


_GENERIC_CONSTRAINT = "binding operational constraints"
_GENERIC_ACTOR = "the lead actor"
_GENERIC_NODE = "the focal node"


def build_competing_mechanisms(
    decompose_result: DecomposeResult,
    trace_result: TraceResult,
) -> CompeteResult:
    """Generate exactly two competing mechanism cards with divergent predictions."""

    actor_name = _first_or_fallback((actor.name for actor in decompose_result.actor_cards), _GENERIC_ACTOR)
    node_name = _first_or_fallback((node.name for node in decompose_result.node_cards), _GENERIC_NODE)
    constraint = _first_or_fallback(
        (constraint.constraint for constraint in decompose_result.constraint_cards),
        _GENERIC_CONSTRAINT,
    )
    first_step = trace_result.consequence_chain[0]
    last_step = trace_result.consequence_chain[-1]

    competing_mechanisms = [
        CompetingMechanism(
            label="A",
            core_mechanism=(
                f"Direct throughput and capacity loss at {node_name} is the dominant mechanism; the problem persists mainly because the first-order bottleneck from '{first_step.event}' is still binding"
            ),
            what_it_explains=(
                f"Why the immediate disruption around {node_name} should account for most of the downstream effects seen in {last_step.event.lower()}"
            ),
            prediction=(
                f"If mechanism A is right, conditions should improve quickly once {node_name} regains workable throughput or the most binding part of '{constraint}' is relaxed"
            ),
            observable_signal=(
                f"Operational recovery at {node_name} should precede normalization elsewhere: queue lengths, throughput, or service availability near {node_name} improve before broader downstream symptoms fully clear"
            ),
        ),
        CompetingMechanism(
            label="B",
            core_mechanism=(
                f"Coordination, incentives, and expectation effects among {actor_name} and adjacent actors are the dominant mechanism, so downstream disruption keeps spreading even after the focal node begins recovering"
            ),
            what_it_explains=(
                f"Why the second- and third-order effects from '{trace_result.consequence_chain[1].event}' can remain large even if the original node-level shock eases"
            ),
            prediction=(
                f"If mechanism B is right, downstream disruption should persist after {node_name} stabilizes because actors continue hoarding, reprioritizing, or mis-coordinating around the expected risk"
            ),
            observable_signal=(
                f"Broader symptoms remain elevated despite improving conditions at {node_name}: substitute nodes stay congested, allocations remain distorted, or affected actors keep acting as though the shock is still binding"
            ),
        ),
    ]

    divergence_note = (
        f"The cards diverge on whether the dominant driver is the direct bottleneck at {node_name} or the adaptive behavior that follows it. Mechanism A predicts fast normalization once the node-level bottleneck eases, while mechanism B predicts persistent downstream effects after nominal recovery."
    )
    return CompeteResult(
        competing_mechanisms=competing_mechanisms,
        divergence_note=divergence_note,
    )


build_compete = build_competing_mechanisms
generate_competing_mechanisms = build_competing_mechanisms


def _first_or_fallback(values: Iterable[str], fallback: str) -> str:
    for value in values:
        cleaned = value.strip()
        if cleaned:
            return cleaned
    return fallback


__all__ = [
    "build_compete",
    "build_competing_mechanisms",
    "generate_competing_mechanisms",
]
