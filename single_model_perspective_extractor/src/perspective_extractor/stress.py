"""Core stress stage for phase-1 falsification and surprise ledgers."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import asdict

from .models import (
    CompeteResult,
    DecomposeResult,
    FalsificationEntry,
    StressResult,
    SurpriseEntry,
    TraceResult,
)
from .openrouter import call_openrouter

_GENERIC_ACTOR = "the lead actor"
_GENERIC_NODE = "the focal node"
_GENERIC_CONSTRAINT = "binding operating limits"

STRESS_SCHEMA = {
    "type": "object",
    "properties": {
        "falsification_ledger": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "claim_under_stress": {"type": "string"},
                    "hidden_assumption": {"type": "string"},
                    "how_it_could_fail": {"type": "string"},
                    "what_evidence_would_break_it": {"type": "string"},
                },
                "required": [
                    "claim_under_stress",
                    "hidden_assumption",
                    "how_it_could_fail",
                    "what_evidence_would_break_it",
                ],
            },
        },
        "surprise_ledger": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "surprise": {"type": "string"},
                    "why_shallow_analysis_misses_it": {"type": "string"},
                    "what_actor_or_node_it_depends_on": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": [
                    "surprise",
                    "why_shallow_analysis_misses_it",
                    "what_actor_or_node_it_depends_on",
                ],
            },
        },
    },
    "required": ["falsification_ledger", "surprise_ledger"],
}


def build_stress_test(
    decompose_result: DecomposeResult,
    trace_result: TraceResult,
    compete_result: CompeteResult,
) -> StressResult:
    """Generate falsification and surprise entries from prior artifacts."""

    actor_name = _first_or_fallback(
        (actor.name for actor in decompose_result.actor_cards),
        _GENERIC_ACTOR,
    )
    node_name = _first_or_fallback(
        (node.name for node in decompose_result.node_cards),
        _GENERIC_NODE,
    )
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


def build_stress_prompt(
    decompose_result: DecomposeResult,
    trace_result: TraceResult,
    compete_result: CompeteResult,
) -> str:
    """Return the live stress-stage prompt."""

    return (
        "You are running the phase-1 rigor pipeline stress stage. Return JSON only and no markdown.\n\n"
        "Task: stress-test the current mechanism cards with falsification and surprise ledgers.\n\n"
        f"Schema:\n{json.dumps(STRESS_SCHEMA, indent=2, ensure_ascii=False, sort_keys=True)}\n\n"
        "Rules:\n"
        "- Make falsification entries concrete enough to break the current claim.\n"
        "- Surprise entries should identify actors or nodes that shallow analysis might miss.\n"
        "- Keep every entry grounded in the provided artifacts.\n\n"
        "Decompose artifact:\n"
        f"{json.dumps(asdict(decompose_result), indent=2, ensure_ascii=False, sort_keys=True)}\n\n"
        "Trace artifact:\n"
        f"{json.dumps(asdict(trace_result), indent=2, ensure_ascii=False, sort_keys=True)}\n\n"
        "Compete artifact:\n"
        f"{json.dumps(asdict(compete_result), indent=2, ensure_ascii=False, sort_keys=True)}\n"
    )


def run_stress(
    decompose_result: DecomposeResult,
    trace_result: TraceResult,
    compete_result: CompeteResult,
    *,
    model: str,
    api_key: str,
) -> StressResult:
    """Run the live stress stage directly from this module."""

    response_text = call_openrouter(
        api_key=api_key,
        model=model,
        messages=[
            {"role": "system", "content": "Return strict JSON for the requested schema only."},
            {
                "role": "user",
                "content": build_stress_prompt(
                    decompose_result,
                    trace_result,
                    compete_result,
                ),
            },
        ],
        temperature=0.0,
        max_tokens=2400,
    )
    payload = _load_json_object(response_text, stage_name="stress")
    return StressResult(
        falsification_ledger=[
            FalsificationEntry(**item) for item in payload["falsification_ledger"]
        ],
        surprise_ledger=[SurpriseEntry(**item) for item in payload["surprise_ledger"]],
    )


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


def _load_json_object(response_text: str, *, stage_name: str) -> dict[str, object]:
    cleaned = response_text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    payload = json.loads(cleaned)
    if not isinstance(payload, dict):
        raise ValueError(f"{stage_name} must return a JSON object")
    return payload


__all__ = [
    "STRESS_SCHEMA",
    "build_stress",
    "build_stress_prompt",
    "build_stress_test",
    "generate_stress_entries",
    "run_stress",
]
