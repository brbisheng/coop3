"""Core final stage for assembling the dense phase-1 report."""

from __future__ import annotations

import json
import re
from dataclasses import asdict

from .models import CompeteResult, DecomposeResult, FinalReport, StressResult, TraceResult
from .openrouter import call_openrouter
from .policy import PolicyVersion, resolve_policy_version

_GENERIC_TARGET = "the focal problem"

FINAL_SCHEMA = {
    "type": "object",
    "properties": {
        "key_actors_and_nodes": {"type": "array", "items": {"type": "string"}},
        "critical_mechanism_chains": {"type": "array", "items": {"type": "string"}},
        "competing_explanations_and_divergent_predictions": {
            "type": "array",
            "items": {"type": "string"},
        },
        "likely_surprises": {"type": "array", "items": {"type": "string"}},
        "main_uncertainties_and_hidden_assumptions": {
            "type": "array",
            "items": {"type": "string"},
        },
        "executive_summary": {"type": "string"},
    },
    "required": [
        "key_actors_and_nodes",
        "critical_mechanism_chains",
        "competing_explanations_and_divergent_predictions",
        "likely_surprises",
        "main_uncertainties_and_hidden_assumptions",
        "executive_summary",
    ],
}


def build_final_report(
    decompose_result: DecomposeResult,
    trace_result: TraceResult,
    compete_result: CompeteResult,
    stress_result: StressResult,
) -> FinalReport:
    """Assemble a dense final report from prior phase-1 artifacts."""

    actor_lines = [
        f"Actor {actor.name} ({actor.type}) matters because {actor.why_relevant}"
        for actor in decompose_result.actor_cards
    ]
    node_lines = [
        f"Node {node.name} ({node.type}) matters because {node.why_relevant}"
        for node in decompose_result.node_cards
    ]
    constraint_lines = [
        f"Constraint: {constraint.constraint} — applies to {', '.join(constraint.applies_to)} because {constraint.why_it_matters}"
        for constraint in decompose_result.constraint_cards
    ]
    key_actors_and_nodes = _bounded_non_empty(
        [*actor_lines, *node_lines, *constraint_lines],
        fallback=[f"No structured actors or nodes were extracted for {trace_result.trace_target}."],
    )

    critical_mechanism_chains = [
        (
            f"{_ordinal_label(step.order)}-order step: {step.event} "
            f"Mechanism: {step.mechanism}. "
            f"Affected entities: {', '.join(step.affected_entities)}."
        )
        for step in trace_result.consequence_chain
    ]

    competing_explanations_and_divergent_predictions = [
        (
            f"Mechanism {mechanism.label}: {mechanism.core_mechanism} Explains: {mechanism.what_it_explains} "
            f"Prediction: {mechanism.prediction} Observable signal: {mechanism.observable_signal}"
        )
        for mechanism in compete_result.competing_mechanisms
    ]
    competing_explanations_and_divergent_predictions.append(compete_result.divergence_note)

    likely_surprises = [
        (
            f"{entry.surprise} Why it may be missed: {entry.why_shallow_analysis_misses_it} "
            f"Depends on: {', '.join(entry.what_actor_or_node_it_depends_on)}"
        )
        for entry in stress_result.surprise_ledger
    ]

    main_uncertainties_and_hidden_assumptions = [
        (
            f"Claim under stress: {entry.claim_under_stress} Hidden assumption: {entry.hidden_assumption} "
            f"Failure mode: {entry.how_it_could_fail} Breaking evidence: {entry.what_evidence_would_break_it}"
        )
        for entry in stress_result.falsification_ledger
    ]

    executive_summary = _build_executive_summary(
        decompose_result=decompose_result,
        trace_result=trace_result,
        compete_result=compete_result,
        stress_result=stress_result,
    )

    return FinalReport(
        key_actors_and_nodes=key_actors_and_nodes,
        critical_mechanism_chains=critical_mechanism_chains,
        competing_explanations_and_divergent_predictions=competing_explanations_and_divergent_predictions,
        likely_surprises=likely_surprises,
        main_uncertainties_and_hidden_assumptions=main_uncertainties_and_hidden_assumptions,
        executive_summary=executive_summary,
    )


build_final = build_final_report
assemble_final_report = build_final_report


def build_final_prompt(
    decompose_result: DecomposeResult,
    trace_result: TraceResult,
    compete_result: CompeteResult,
    stress_result: StressResult,
    *,
    prompt_patch: str | None = None,
    policy_version: str | PolicyVersion | None = None,
) -> str:
    """Return the live final-stage prompt."""

    policy = resolve_policy_version(policy_version)
    stage_policy = policy.stage("final", default_max_tokens=2600)
    patch_block = f"\nImprovement patch for this round:\n{prompt_patch.strip()}\n" if prompt_patch and prompt_patch.strip() else ""
    extra_rules = "".join(f"{rule}\n" for rule in stage_policy.prompt_rules_extra)
    return (
        "You are running the phase-1 rigor pipeline final stage. Return JSON only and no markdown.\n\n"
        f"{stage_policy.prompt_prefix}"
        "Task: assemble a dense final report that faithfully summarizes the previous phase-1 artifacts.\n\n"
        f"Schema:\n{json.dumps(FINAL_SCHEMA, indent=2, ensure_ascii=False, sort_keys=True)}\n\n"
        "Rules:\n"
        "- Preserve disagreement, uncertainty, and surprises rather than flattening them away.\n"
        "- Every list should contain concise but content-rich strings.\n"
        "- executive_summary should read like a decision memo paragraph, not a bullet list.\n"
        "- Hard constraint: do not open executive_summary with a generic macro-summary phrase (forbidden openings include: 'Overall', 'In summary', 'This situation highlights', 'At a high level').\n"
        "- Hard constraint: open executive_summary with concrete actors, nodes, or mechanism conflict from the artifacts.\n"
        "- Hard constraint: every section must include artifact-grounded specifics (named actors/nodes/mechanisms/signals), not broad geopolitical or market platitudes.\n\n"
        f"{extra_rules}"
        f"{patch_block}"
        "Decompose artifact:\n"
        f"{json.dumps(asdict(decompose_result), indent=2, ensure_ascii=False, sort_keys=True)}\n\n"
        "Trace artifact:\n"
        f"{json.dumps(asdict(trace_result), indent=2, ensure_ascii=False, sort_keys=True)}\n\n"
        "Compete artifact:\n"
        f"{json.dumps(asdict(compete_result), indent=2, ensure_ascii=False, sort_keys=True)}\n\n"
        "Stress artifact:\n"
        f"{json.dumps(asdict(stress_result), indent=2, ensure_ascii=False, sort_keys=True)}\n"
    )


def run_final(
    decompose_result: DecomposeResult,
    trace_result: TraceResult,
    compete_result: CompeteResult,
    stress_result: StressResult,
    *,
    model: str,
    api_key: str,
    prompt_patch: str | None = None,
    policy_version: str | PolicyVersion | None = None,
) -> FinalReport:
    """Run the live final stage directly from this module."""

    policy = resolve_policy_version(policy_version)
    stage_policy = policy.stage("final", default_max_tokens=2600)
    response_text = call_openrouter(
        api_key=api_key,
        model=model,
        messages=[
            {"role": "system", "content": stage_policy.system_prompt},
            {
                "role": "user",
                "content": build_final_prompt(
                    decompose_result,
                    trace_result,
                    compete_result,
                    stress_result,
                    prompt_patch=prompt_patch,
                    policy_version=policy,
                ),
            },
        ],
        temperature=stage_policy.temperature,
        max_tokens=stage_policy.max_tokens,
    )
    payload = _load_json_object(response_text, stage_name="final")
    return FinalReport(**payload)


def _ordinal_label(value: int) -> str:
    if value == 1:
        return "1st"
    if value == 2:
        return "2nd"
    if value == 3:
        return "3rd"
    return f"{value}th"


def _build_executive_summary(
    *,
    decompose_result: DecomposeResult,
    trace_result: TraceResult,
    compete_result: CompeteResult,
    stress_result: StressResult,
) -> str:
    target = trace_result.trace_target or _GENERIC_TARGET
    first_step = trace_result.consequence_chain[0]
    last_step = trace_result.consequence_chain[-1]
    divergence = compete_result.divergence_note
    key_uncertainty = stress_result.falsification_ledger[0].hidden_assumption
    main_surprise = stress_result.surprise_ledger[0].surprise
    return (
        f"For {target}, the current best structured reading is that {first_step.event.lower()}, then the pressure propagates until {last_step.event.lower()}. "
        f"The main live dispute is: {divergence} The leading hidden assumption to test is that {key_uncertainty.lower()}. "
        f"A plausible surprise is that {main_surprise.lower()}. The problem frame remains anchored in '{decompose_result.problem_frame.core_question}'."
    )


def _bounded_non_empty(values: list[str], *, fallback: list[str]) -> list[str]:
    cleaned = [" ".join(value.split()) for value in values if value and value.strip()]
    return cleaned or fallback


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
    "FINAL_SCHEMA",
    "assemble_final_report",
    "build_final",
    "build_final_prompt",
    "build_final_report",
    "run_final",
]
