"""Core stress stage for phase-1 falsification and surprise ledgers."""

from __future__ import annotations

from collections.abc import Iterable

from .models import (
    CompeteResult,
    DecomposeResult,
    FalsificationEntry,
    StressResult,
    SurpriseEntry,
    TraceResult,
)


_GENERIC_ACTOR = "the lead actor"
_GENERIC_NODE = "the focal node"
_GENERIC_CONSTRAINT = "binding operating limits"


def build_stress_test(
    decompose_result: DecomposeResult,
    trace_result: TraceResult,
    compete_result: CompeteResult,
) -> StressResult:
    """Generate falsification and surprise entries from prior artifacts."""

    actor_name = _first_or_fallback((actor.name for actor in decompose_result.actor_cards), _GENERIC_ACTOR)
    node_name = _first_or_fallback((node.name for node in decompose_result.node_cards), _GENERIC_NODE)
    constraint = _first_or_fallback(
        (constraint.constraint for constraint in decompose_result.constraint_cards),
        _GENERIC_CONSTRAINT,
    )
    mechanism_a, mechanism_b = compete_result.competing_mechanisms

    falsification_ledger = [
        FalsificationEntry(
            claim_under_stress=mechanism_a.prediction,
            hidden_assumption=(
                f"The main constraint really is concentrated at {node_name} rather than being displaced into substitute actors, nodes, or decision processes"
            ),
            how_it_could_fail=(
                f"{constraint} or a closely related bottleneck remains binding outside {node_name}, so nominal recovery at the focal node does not translate into real system recovery"
            ),
            what_evidence_would_break_it=(
                f"Evidence that downstream delays, shortages, or performance gaps remain elevated after measurable recovery at {node_name} would falsify the claim that direct throughput restoration is sufficient"
            ),
        ),
        FalsificationEntry(
            claim_under_stress=mechanism_b.prediction,
            hidden_assumption=(
                f"Actor behavior rather than direct capacity loss is doing most of the explanatory work, and {actor_name} is still reacting to expected risk rather than current conditions"
            ),
            how_it_could_fail=(
                f"Once the first-order bottleneck clears, the second- and third-order effects unwind quickly, showing that coordination frictions were secondary rather than dominant"
            ),
            what_evidence_would_break_it=(
                f"If substitute nodes decongest and exposed actors normalize behavior soon after the first-order shock eases, the expectation-and-coordination account loses force"
            ),
        ),
    ]

    surprise_ledger = [
        SurpriseEntry(
            surprise=(
                f"A secondary node or actor outside {node_name} becomes the real bottleneck once attention and mitigation resources concentrate on the headline disruption"
            ),
            why_shallow_analysis_misses_it=(
                "Shallow analysis stays fixed on the initial shock and underweights the way rerouting, substitution, and political attention can create a new constraint elsewhere"
            ),
            what_actor_or_node_it_depends_on=_dedupe([
                node_name,
                *_actor_names(decompose_result, limit=2),
                *_node_names(decompose_result, limit=2),
            ]),
        ),
        SurpriseEntry(
            surprise=(
                f"An institutional or behavioral response from {actor_name} amplifies the third-order effects more than the physical disruption itself"
            ),
            why_shallow_analysis_misses_it=(
                "Surface-level tracing often assumes actors passively absorb shocks, even though defensive prioritization, compliance choices, or public signaling can magnify downstream consequences"
            ),
            what_actor_or_node_it_depends_on=_dedupe([
                actor_name,
                node_name,
                *trace_result.consequence_chain[-1].affected_entities[:2],
            ]),
        ),
    ]

    return StressResult(
        falsification_ledger=falsification_ledger,
        surprise_ledger=surprise_ledger,
    )


build_stress = build_stress_test
generate_stress_entries = build_stress_test


def _first_or_fallback(values: Iterable[str], fallback: str) -> str:
    for value in values:
        cleaned = value.strip()
        if cleaned:
            return cleaned
    return fallback



def _actor_names(decompose_result: DecomposeResult, *, limit: int) -> list[str]:
    return [actor.name for actor in decompose_result.actor_cards[:limit] if actor.name.strip()]



def _node_names(decompose_result: DecomposeResult, *, limit: int) -> list[str]:
    return [node.name for node in decompose_result.node_cards[:limit] if node.name.strip()]



def _dedupe(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        cleaned = " ".join(value.split())
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            ordered.append(cleaned)
    return ordered


__all__ = ["build_stress", "build_stress_test", "generate_stress_entries"]
