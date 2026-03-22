"""Core final stage for assembling the dense phase-1 report."""

from __future__ import annotations

from .models import CompeteResult, DecomposeResult, FinalReport, StressResult, TraceResult


_GENERIC_TARGET = "the focal problem"


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


__all__ = ["assemble_final_report", "build_final", "build_final_report"]
