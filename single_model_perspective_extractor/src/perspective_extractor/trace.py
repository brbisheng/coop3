"""Core trace stage for phase-1 consequence chaining."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import asdict

from .models import DecomposeResult, TraceResult, TraceStep
from .openrouter import call_openrouter

_GENERIC_NODE = "the primary operational node"
_GENERIC_ACTOR = "the primary decision-maker"
_GENERIC_CONSTRAINT = "binding operational limits"

TRACE_SCHEMA = {
    "type": "object",
    "properties": {
        "trace_target": {"type": "string"},
        "consequence_chain": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "order": {"type": "integer"},
                    "event": {"type": "string"},
                    "mechanism": {"type": "string"},
                    "affected_entities": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["order", "event", "mechanism", "affected_entities"],
            },
        },
    },
    "required": ["trace_target", "consequence_chain"],
}


def build_trace(
    decompose_result: DecomposeResult,
    *,
    trace_target: str | None = None,
) -> TraceResult:
    """Build a deterministic 1st/2nd/3rd-order consequence chain."""

    node_name = _first_or_fallback(
        (node.name for node in decompose_result.node_cards),
        fallback=_GENERIC_NODE,
    )
    actor_name = _first_or_fallback(
        (actor.name for actor in decompose_result.actor_cards),
        fallback=_GENERIC_ACTOR,
    )
    constraint = _first_or_fallback(
        (constraint.constraint for constraint in decompose_result.constraint_cards),
        fallback=_GENERIC_CONSTRAINT,
    )
    applies_to = _first_non_empty(
        (constraint_card.applies_to for constraint_card in decompose_result.constraint_cards),
        fallback=[actor_name, node_name],
    )
    target = trace_target or _infer_trace_target(decompose_result, node_name=node_name)

    first_order_entities = _dedupe([node_name, actor_name, *applies_to])
    second_order_entities = _dedupe([
        *_additional_actor_names(decompose_result, limit=3),
        *_additional_node_names(decompose_result, limit=2),
        node_name,
    ])
    if not second_order_entities:
        second_order_entities = [node_name, actor_name]

    third_order_entities = _dedupe([
        *_additional_actor_names(decompose_result, limit=4),
        *_problem_scope_entities(decompose_result),
        actor_name,
    ])
    if not third_order_entities:
        third_order_entities = [actor_name, node_name]

    consequence_chain = [
        TraceStep(
            order=1,
            event=(
                f"{target} immediately constrains activity at {node_name} and forces {actor_name} to absorb the first operational shock"
            ),
            mechanism=(
                f"The first-order mechanism is direct disruption: {constraint} tightens at {node_name}, so the actors closest to the node lose throughput, access, or decision latitude before anyone else can adjust"
            ),
            affected_entities=first_order_entities,
        ),
        TraceStep(
            order=2,
            event=(
                f"Secondary actors reroute, reprioritize, or substitute around {node_name}, spreading pressure into adjacent nodes and decisions"
            ),
            mechanism=(
                f"The second-order mechanism is propagation through adaptation: once {actor_name} and related operators respond to the initial constraint, queues, substitutions, compliance delays, and bargaining shifts move the disruption into neighboring entities rather than leaving it isolated"
            ),
            affected_entities=second_order_entities,
        ),
        TraceStep(
            order=3,
            event=(
                "Tertiary outcomes emerge after the adaptive response changes incentives, expectations, or downstream performance in the wider problem frame"
            ),
            mechanism=(
                f"The third-order mechanism is system-level pass-through: the earlier rerouting and prioritization choices alter who bears scarcity, delay, or political cost, which changes the broader outcome targeted by '{decompose_result.problem_frame.decision_or_analysis_target}'"
            ),
            affected_entities=third_order_entities,
        ),
    ]

    return TraceResult(trace_target=target, consequence_chain=consequence_chain)


trace_problem = build_trace
generate_trace = build_trace


def build_trace_prompt(
    problem_text_or_artifact: str | DecomposeResult,
    *,
    trace_target: str | None = None,
    prompt_patch: str | None = None,
) -> str:
    """Return the live trace-stage prompt."""

    if isinstance(problem_text_or_artifact, DecomposeResult):
        input_body = json.dumps(
            asdict(problem_text_or_artifact),
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
    else:
        normalized_problem = " ".join(problem_text_or_artifact.split())
        if not normalized_problem:
            raise ValueError("problem_text must not be empty")
        input_body = normalized_problem

    target_instruction = trace_target or "Infer the most operationally relevant trace target."
    patch_block = f"\nImprovement patch for this round:\n{prompt_patch.strip()}\n" if prompt_patch and prompt_patch.strip() else ""
    return (
        "You are running the phase-1 rigor pipeline trace stage. Return JSON only and no markdown.\n\n"
        "Task: produce an ordered first-, second-, and third-order consequence chain with concrete mechanisms and affected entities.\n\n"
        f"Schema:\n{json.dumps(TRACE_SCHEMA, indent=2, ensure_ascii=False, sort_keys=True)}\n\n"
        "Rules:\n"
        "- consequence_chain must start at order 1 and increase by 1.\n"
        "- Use concrete operational language, not generic strategic prose.\n"
        "- affected_entities should stay tightly tied to the described mechanism.\n"
        "- Hard constraint: include at least one substitute-path adaptation (rerouting, replacement, work-around, or policy substitution) in order 2 or order 3.\n"
        "- Hard constraint: order 2 and order 3 must be true second-/third-order effects caused by adaptation or feedback, not restatements of order 1.\n"
        "- Hard constraint: each step's mechanism must explicitly explain why that step follows from the previous step.\n\n"
        f"{patch_block}"
        f"Trace target: {target_instruction}\n\n"
        f"Input artifact or problem text:\n{input_body}\n"
    )


def run_trace(
    problem_text_or_artifact: str | DecomposeResult,
    *,
    model: str,
    api_key: str,
    trace_target: str | None = None,
    prompt_patch: str | None = None,
) -> TraceResult:
    """Run the live trace stage directly from this module."""

    response_text = call_openrouter(
        api_key=api_key,
        model=model,
        messages=[
            {"role": "system", "content": "Return strict JSON for the requested schema only."},
            {
                "role": "user",
                "content": build_trace_prompt(
                    problem_text_or_artifact,
                    trace_target=trace_target,
                    prompt_patch=prompt_patch,
                ),
            },
        ],
        temperature=0.0,
        max_tokens=2200,
    )
    payload = _load_json_object(response_text, stage_name="trace")
    return TraceResult(
        trace_target=payload["trace_target"],
        consequence_chain=[TraceStep(**item) for item in payload["consequence_chain"]],
    )


def _infer_trace_target(decompose_result: DecomposeResult, *, node_name: str) -> str:
    core_question = decompose_result.problem_frame.core_question.rstrip("?")
    if node_name != _GENERIC_NODE:
        return f"Operational consequences of stress on {node_name}"
    return core_question or "Operational consequence chain"


def _first_or_fallback(values: Iterable[str], *, fallback: str) -> str:
    for value in values:
        cleaned = value.strip()
        if cleaned:
            return cleaned
    return fallback


def _first_non_empty(values: Iterable[list[str]], *, fallback: list[str]) -> list[str]:
    for value in values:
        cleaned = [item.strip() for item in value if item and item.strip()]
        if cleaned:
            return cleaned
    return fallback


def _additional_actor_names(decompose_result: DecomposeResult, *, limit: int) -> list[str]:
    return [actor.name for actor in decompose_result.actor_cards[:limit] if actor.name.strip()]


def _additional_node_names(decompose_result: DecomposeResult, *, limit: int) -> list[str]:
    return [node.name for node in decompose_result.node_cards[:limit] if node.name.strip()]


def _problem_scope_entities(decompose_result: DecomposeResult) -> list[str]:
    scope_entities: list[str] = []
    scope_entities.extend(decompose_result.problem_frame.scope_notes[:2])
    if decompose_result.problem_frame.decision_or_analysis_target:
        scope_entities.append(decompose_result.problem_frame.decision_or_analysis_target)
    return [entity for entity in scope_entities if entity.strip()]


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
    "TRACE_SCHEMA",
    "build_trace",
    "build_trace_prompt",
    "generate_trace",
    "run_trace",
    "trace_problem",
]
