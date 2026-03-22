"""Shared data models for the perspective extractor pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal
from uuid import uuid4

ReviewAction = Literal["keep", "merge", "rewrite", "drop"]
ActorType = Literal["person", "organization", "state", "firm", "proxy", "institution", "other"]
NodeType = Literal["facility", "route", "market", "institutional node", "platform", "other"]
_ALLOWED_REVIEW_ACTIONS = {"keep", "merge", "rewrite", "drop"}
_ALLOWED_ACTOR_TYPES = {"person", "organization", "state", "firm", "proxy", "institution", "other"}
_ALLOWED_NODE_TYPES = {"facility", "route", "market", "institutional node", "platform", "other"}


def _make_id(prefix: str) -> str:
    """Create a lightweight stable-enough identifier for in-memory pipeline objects."""

    return f"{prefix}_{uuid4().hex[:12]}"



def _clean_string_list(values: list[str] | None) -> list[str]:
    """Return a trimmed list of non-empty strings."""

    if not values:
        return []
    return [value.strip() for value in values if value and value.strip()]



def _require_text(value: str, field_name: str) -> str:
    """Ensure a text field is present and not blank."""

    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} must not be empty")
    return cleaned



def _require_allowed_literal(value: str, field_name: str, allowed_values: set[str]) -> str:
    """Ensure a string field is one of the accepted literal values."""

    cleaned = _require_text(value, field_name)
    if cleaned not in allowed_values:
        allowed = " | ".join(sorted(allowed_values))
        raise ValueError(f"{field_name} must be one of: {allowed}")
    return cleaned



def _clean_relation_pairs(values: list[tuple[str, str]] | None, field_name: str) -> list[tuple[str, str]]:
    """Validate pair-wise perspective relationship references."""

    if not values:
        return []

    cleaned_pairs: list[tuple[str, str]] = []
    for left, right in values:
        cleaned_pairs.append((
            _require_text(left, field_name),
            _require_text(right, field_name),
        ))
    return cleaned_pairs



def _require_non_empty_list(values: list[str], field_name: str) -> list[str]:
    """Ensure a cleaned list contains at least one item."""

    cleaned_values = _clean_string_list(values)
    if not cleaned_values:
        raise ValueError(f"{field_name} must contain at least one item")
    return cleaned_values


@dataclass(slots=True)
class ProblemFrame:
    """Top-level framing for a single phase-1 analysis problem."""

    core_question: str
    decision_or_analysis_target: str
    scope_notes: list[str] = field(default_factory=list)
    problem_frame_id: str = field(default_factory=lambda: _make_id("problem_frame"))

    def __post_init__(self) -> None:
        self.problem_frame_id = _require_text(self.problem_frame_id, "problem_frame_id")
        self.core_question = _require_text(self.core_question, "core_question")
        self.decision_or_analysis_target = _require_text(
            self.decision_or_analysis_target,
            "decision_or_analysis_target",
        )
        self.scope_notes = _clean_string_list(self.scope_notes)


@dataclass(slots=True)
class ActorCard:
    """Concrete actor relevant to the current problem frame."""

    name: str
    type: ActorType
    role: str
    goal_guess: str
    why_relevant: str
    actor_id: str = field(default_factory=lambda: _make_id("actor"))

    def __post_init__(self) -> None:
        self.actor_id = _require_text(self.actor_id, "actor_id")
        self.name = _require_text(self.name, "name")
        self.type = _require_allowed_literal(self.type, "type", _ALLOWED_ACTOR_TYPES)
        self.role = _require_text(self.role, "role")
        self.goal_guess = _require_text(self.goal_guess, "goal_guess")
        self.why_relevant = _require_text(self.why_relevant, "why_relevant")


@dataclass(slots=True)
class NodeCard:
    """Operational node, facility, route, or market that matters for the problem."""

    name: str
    type: NodeType
    function: str
    why_relevant: str
    node_id: str = field(default_factory=lambda: _make_id("node"))

    def __post_init__(self) -> None:
        self.node_id = _require_text(self.node_id, "node_id")
        self.name = _require_text(self.name, "name")
        self.type = _require_allowed_literal(self.type, "type", _ALLOWED_NODE_TYPES)
        self.function = _require_text(self.function, "function")
        self.why_relevant = _require_text(self.why_relevant, "why_relevant")


@dataclass(slots=True)
class ConstraintCard:
    """Binding constraint that shapes what actors or nodes can realistically do."""

    constraint: str
    applies_to: list[str]
    why_it_matters: str
    constraint_id: str = field(default_factory=lambda: _make_id("constraint"))

    def __post_init__(self) -> None:
        self.constraint_id = _require_text(self.constraint_id, "constraint_id")
        self.constraint = _require_text(self.constraint, "constraint")
        self.applies_to = _require_non_empty_list(self.applies_to, "applies_to")
        self.why_it_matters = _require_text(self.why_it_matters, "why_it_matters")


@dataclass(slots=True)
class DecomposeResult:
    """Primary structured output for the phase-1 decompose step."""

    problem_frame: ProblemFrame
    actor_cards: list[ActorCard] = field(default_factory=list)
    node_cards: list[NodeCard] = field(default_factory=list)
    constraint_cards: list[ConstraintCard] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.actor_cards = list(self.actor_cards)
        self.node_cards = list(self.node_cards)
        self.constraint_cards = list(self.constraint_cards)


@dataclass(slots=True)
class TraceStep:
    """One ordered consequence in a causal trace."""

    order: int
    event: str
    mechanism: str
    affected_entities: list[str]

    def __post_init__(self) -> None:
        if self.order < 1:
            raise ValueError("order must be greater than or equal to 1")
        self.event = _require_text(self.event, "event")
        self.mechanism = _require_text(self.mechanism, "mechanism")
        self.affected_entities = _require_non_empty_list(
            self.affected_entities,
            "affected_entities",
        )


@dataclass(slots=True)
class TraceResult:
    """Primary structured output for the phase-1 trace step."""

    trace_target: str
    consequence_chain: list[TraceStep] = field(default_factory=list)
    trace_id: str = field(default_factory=lambda: _make_id("trace"))

    def __post_init__(self) -> None:
        self.trace_id = _require_text(self.trace_id, "trace_id")
        self.trace_target = _require_text(self.trace_target, "trace_target")
        self.consequence_chain = list(self.consequence_chain)
        if not self.consequence_chain:
            raise ValueError("consequence_chain must contain at least one TraceStep")

        expected_order = 1
        for step in self.consequence_chain:
            if step.order != expected_order:
                raise ValueError("consequence_chain orders must start at 1 and increase by 1")
            expected_order += 1


@dataclass(slots=True)
class CompetingMechanism:
    """One competing explanation with a differentiating prediction."""

    label: str
    core_mechanism: str
    what_it_explains: str
    prediction: str
    observable_signal: str

    def __post_init__(self) -> None:
        self.label = _require_text(self.label, "label")
        self.core_mechanism = _require_text(self.core_mechanism, "core_mechanism")
        self.what_it_explains = _require_text(self.what_it_explains, "what_it_explains")
        self.prediction = _require_text(self.prediction, "prediction")
        self.observable_signal = _require_text(self.observable_signal, "observable_signal")


@dataclass(slots=True)
class CompeteResult:
    """Primary structured output for the phase-1 compete step."""

    competing_mechanisms: list[CompetingMechanism]
    divergence_note: str
    compete_id: str = field(default_factory=lambda: _make_id("compete"))

    def __post_init__(self) -> None:
        self.compete_id = _require_text(self.compete_id, "compete_id")
        self.competing_mechanisms = list(self.competing_mechanisms)
        if len(self.competing_mechanisms) != 2:
            raise ValueError("competing_mechanisms must contain exactly two entries")
        self.divergence_note = _require_text(self.divergence_note, "divergence_note")

        predictions = {
            mechanism.prediction.casefold() for mechanism in self.competing_mechanisms
        }
        if len(predictions) != len(self.competing_mechanisms):
            raise ValueError("competing_mechanisms predictions must not be identical")


@dataclass(slots=True)
class FalsificationEntry:
    """One stress-test against the current strongest claim."""

    claim_under_stress: str
    hidden_assumption: str
    how_it_could_fail: str
    what_evidence_would_break_it: str

    def __post_init__(self) -> None:
        self.claim_under_stress = _require_text(self.claim_under_stress, "claim_under_stress")
        self.hidden_assumption = _require_text(self.hidden_assumption, "hidden_assumption")
        self.how_it_could_fail = _require_text(self.how_it_could_fail, "how_it_could_fail")
        self.what_evidence_would_break_it = _require_text(
            self.what_evidence_would_break_it,
            "what_evidence_would_break_it",
        )


@dataclass(slots=True)
class SurpriseEntry:
    """One plausible surprise pathway that shallow analysis would likely miss."""

    surprise: str
    why_shallow_analysis_misses_it: str
    what_actor_or_node_it_depends_on: list[str]

    def __post_init__(self) -> None:
        self.surprise = _require_text(self.surprise, "surprise")
        self.why_shallow_analysis_misses_it = _require_text(
            self.why_shallow_analysis_misses_it,
            "why_shallow_analysis_misses_it",
        )
        self.what_actor_or_node_it_depends_on = _require_non_empty_list(
            self.what_actor_or_node_it_depends_on,
            "what_actor_or_node_it_depends_on",
        )


@dataclass(slots=True)
class StressResult:
    """Primary structured output for the phase-1 stress step."""

    falsification_ledger: list[FalsificationEntry] = field(default_factory=list)
    surprise_ledger: list[SurpriseEntry] = field(default_factory=list)
    stress_id: str = field(default_factory=lambda: _make_id("stress"))

    def __post_init__(self) -> None:
        self.stress_id = _require_text(self.stress_id, "stress_id")
        self.falsification_ledger = list(self.falsification_ledger)
        self.surprise_ledger = list(self.surprise_ledger)
        if not self.falsification_ledger:
            raise ValueError("falsification_ledger must contain at least one entry")
        if not self.surprise_ledger:
            raise ValueError("surprise_ledger must contain at least one entry")


@dataclass(slots=True)
class FinalReport:
    """Dense final phase-1 report assembled from the structured artifacts."""

    key_actors_and_nodes: list[str]
    critical_mechanism_chains: list[str]
    competing_explanations_and_divergent_predictions: list[str]
    likely_surprises: list[str]
    main_uncertainties_and_hidden_assumptions: list[str]
    report_id: str = field(default_factory=lambda: _make_id("report"))
    executive_summary: str | None = None

    def __post_init__(self) -> None:
        self.report_id = _require_text(self.report_id, "report_id")
        self.key_actors_and_nodes = _require_non_empty_list(
            self.key_actors_and_nodes,
            "key_actors_and_nodes",
        )
        self.critical_mechanism_chains = _require_non_empty_list(
            self.critical_mechanism_chains,
            "critical_mechanism_chains",
        )
        self.competing_explanations_and_divergent_predictions = _require_non_empty_list(
            self.competing_explanations_and_divergent_predictions,
            "competing_explanations_and_divergent_predictions",
        )
        self.likely_surprises = _require_non_empty_list(
            self.likely_surprises,
            "likely_surprises",
        )
        self.main_uncertainties_and_hidden_assumptions = _require_non_empty_list(
            self.main_uncertainties_and_hidden_assumptions,
            "main_uncertainties_and_hidden_assumptions",
        )
        self.executive_summary = (
            _require_text(self.executive_summary, "executive_summary")
            if self.executive_summary is not None
            else None
        )


@dataclass(slots=True)
class PerspectiveRecord:
    """A minimal representation of an extracted perspective."""

    axis: str
    summary: str
    evidence: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.axis = _require_text(self.axis, "axis")
        self.summary = _require_text(self.summary, "summary")
        self.evidence = _clean_string_list(self.evidence)


@dataclass(slots=True)
class PipelineInput:
    """User input for a pipeline run."""

    topic: str
    source_text: str

    def __post_init__(self) -> None:
        self.topic = _require_text(self.topic, "topic")
        self.source_text = self.source_text.strip()


# Legacy many-perspectives schemas retained only for backward compatibility while
# the codebase transitions to the phase-1 rigor pipeline.


@dataclass(slots=True)
class QuestionCard:
    """Normalized representation of the original research question."""

    raw_question: str
    cleaned_question: str
    question_id: str = field(default_factory=lambda: _make_id("question"))
    actor_entity: str | None = None
    outcome_variable: str | None = None
    domain_hint: str | None = None
    assumptions: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    missing_pieces: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.question_id = _require_text(self.question_id, "question_id")
        self.raw_question = _require_text(self.raw_question, "raw_question")
        self.cleaned_question = _require_text(self.cleaned_question, "cleaned_question")
        self.actor_entity = self.actor_entity.strip() if self.actor_entity else None
        self.outcome_variable = self.outcome_variable.strip() if self.outcome_variable else None
        self.domain_hint = self.domain_hint.strip() if self.domain_hint else None
        self.assumptions = _clean_string_list(self.assumptions)
        self.keywords = _clean_string_list(self.keywords)
        self.missing_pieces = _clean_string_list(self.missing_pieces)


@dataclass(slots=True)
class KnowledgeCard:
    """Background knowledge that can inform axis expansion without becoming a full answer."""

    title: str
    content: str
    knowledge_id: str = field(default_factory=lambda: _make_id("knowledge"))
    source_type: str | None = None
    relevance: str | None = None
    evidence_needed: list[str] = field(default_factory=list)
    verification_question: str | None = None

    def __post_init__(self) -> None:
        self.knowledge_id = _require_text(self.knowledge_id, "knowledge_id")
        self.title = _require_text(self.title, "title")
        self.content = _require_text(self.content, "content")
        self.source_type = self.source_type.strip() if self.source_type else None
        self.relevance = self.relevance.strip() if self.relevance else None
        self.evidence_needed = _clean_string_list(self.evidence_needed)
        self.verification_question = (
            self.verification_question.strip() if self.verification_question else None
        )


@dataclass(slots=True)
class VariableCard:
    """Named variable, mechanism, or measurable factor relevant to the question."""

    name: str
    variable_role: str
    definition: str
    variable_id: str = field(default_factory=lambda: _make_id("variable"))
    possible_values: list[str] = field(default_factory=list)
    measurement_notes: str | None = None
    evidence_needed: list[str] = field(default_factory=list)
    testable_implication: str | None = None
    verification_question: str | None = None

    def __post_init__(self) -> None:
        self.variable_id = _require_text(self.variable_id, "variable_id")
        self.name = _require_text(self.name, "name")
        self.variable_role = _require_text(self.variable_role, "variable_role")
        self.definition = _require_text(self.definition, "definition")
        self.possible_values = _clean_string_list(self.possible_values)
        self.measurement_notes = self.measurement_notes.strip() if self.measurement_notes else None
        self.evidence_needed = _clean_string_list(self.evidence_needed)
        self.testable_implication = (
            self.testable_implication.strip() if self.testable_implication else None
        )
        self.verification_question = (
            self.verification_question.strip() if self.verification_question else None
        )


@dataclass(slots=True)
class ControversyCard:
    """A contested claim or fault line that differentiates perspectives."""

    question: str
    sides: list[str]
    controversy_id: str = field(default_factory=lambda: _make_id("controversy"))
    evidence_contests: list[str] = field(default_factory=list)
    verification_question: str | None = None
    competing_perspectives: list[str] = field(default_factory=list)
    compatible_perspectives: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.controversy_id = _require_text(self.controversy_id, "controversy_id")
        self.question = _require_text(self.question, "question")
        self.sides = _clean_string_list(self.sides)
        if len(self.sides) < 2:
            raise ValueError("sides must contain at least two distinct positions")
        self.evidence_contests = _clean_string_list(self.evidence_contests)
        self.verification_question = (
            self.verification_question.strip() if self.verification_question else None
        )
        self.competing_perspectives = _clean_string_list(self.competing_perspectives)
        self.compatible_perspectives = _clean_string_list(self.compatible_perspectives)


@dataclass(slots=True)
class AxisCard:
    """Legacy axis schema from the earlier many-perspectives flow."""

    name: str
    axis_type: str
    focus: str
    how_is_it_distinct: str
    axis_id: str = field(default_factory=lambda: _make_id("axis"))
    priority: int = 0
    evidence_needed: list[str] = field(default_factory=list)
    verification_question: str | None = None
    supporting_card_ids: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.axis_id = _require_text(self.axis_id, "axis_id")
        self.name = _require_text(self.name, "name")
        self.axis_type = _require_text(self.axis_type, "axis_type")
        self.focus = _require_text(self.focus, "focus")
        self.how_is_it_distinct = _require_text(
            self.how_is_it_distinct,
            "how_is_it_distinct",
        )
        if self.priority < 0:
            raise ValueError("priority must be greater than or equal to 0")
        self.evidence_needed = _clean_string_list(self.evidence_needed)
        self.verification_question = (
            self.verification_question.strip() if self.verification_question else None
        )
        self.supporting_card_ids = _clean_string_list(self.supporting_card_ids)


@dataclass(slots=True)
class PerspectiveNote:
    """Legacy per-axis note schema retained for backward compatibility."""

    axis_id: str
    core_claim: str
    reasoning: str
    note_id: str = field(default_factory=lambda: _make_id("note"))
    counterexample: str | None = None
    boundary_condition: str | None = None
    evidence_needed: list[str] = field(default_factory=list)
    testable_implication: str | None = None
    verification_question: str | None = None
    competing_perspectives: list[str] = field(default_factory=list)
    compatible_perspectives: list[str] = field(default_factory=list)
    supporting_card_ids: list[str] = field(default_factory=list)
    planned_subquestions: list[str] = field(default_factory=list)
    subanswer_trace: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.note_id = _require_text(self.note_id, "note_id")
        self.axis_id = _require_text(self.axis_id, "axis_id")
        self.core_claim = _require_text(self.core_claim, "core_claim")
        self.reasoning = _require_text(self.reasoning, "reasoning")
        self.counterexample = self.counterexample.strip() if self.counterexample else None
        self.boundary_condition = (
            self.boundary_condition.strip() if self.boundary_condition else None
        )
        self.evidence_needed = _clean_string_list(self.evidence_needed)
        self.testable_implication = (
            self.testable_implication.strip() if self.testable_implication else None
        )
        self.verification_question = (
            self.verification_question.strip() if self.verification_question else None
        )
        self.competing_perspectives = _clean_string_list(self.competing_perspectives)
        self.compatible_perspectives = _clean_string_list(self.compatible_perspectives)
        self.supporting_card_ids = _clean_string_list(self.supporting_card_ids)
        self.planned_subquestions = _clean_string_list(self.planned_subquestions)
        self.subanswer_trace = _clean_string_list(self.subanswer_trace)


@dataclass(slots=True)
class PerspectiveBranch:
    """Lightweight hierarchical view for one perspective and its attached qualifiers."""

    note_id: str
    axis_id: str
    claim: str
    child_note_ids: list[str] = field(default_factory=list)
    boundary_conditions: list[str] = field(default_factory=list)
    counterexamples: list[str] = field(default_factory=list)
    evidence_disputes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.note_id = _require_text(self.note_id, "note_id")
        self.axis_id = _require_text(self.axis_id, "axis_id")
        self.claim = _require_text(self.claim, "claim")
        self.child_note_ids = _clean_string_list(self.child_note_ids)
        self.boundary_conditions = _clean_string_list(self.boundary_conditions)
        self.counterexamples = _clean_string_list(self.counterexamples)
        self.evidence_disputes = _clean_string_list(self.evidence_disputes)


@dataclass(slots=True)
class AxisHierarchy:
    """Axis-level hierarchy connecting a main perspective to sub-perspectives."""

    axis_id: str
    main_note_id: str
    sub_perspective_ids: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.axis_id = _require_text(self.axis_id, "axis_id")
        self.main_note_id = _require_text(self.main_note_id, "main_note_id")
        self.sub_perspective_ids = _clean_string_list(self.sub_perspective_ids)


@dataclass(slots=True)
class ReviewDecision:
    """Legacy overlap or novelty judgment for a generated perspective."""

    target_note_id: str
    action: ReviewAction
    reason: str
    decision_id: str = field(default_factory=lambda: _make_id("decision"))
    merge_target_note_id: str | None = None
    verification_question: str | None = None

    def __post_init__(self) -> None:
        self.decision_id = _require_text(self.decision_id, "decision_id")
        self.target_note_id = _require_text(self.target_note_id, "target_note_id")
        self.reason = _require_text(self.reason, "reason")
        if self.action not in _ALLOWED_REVIEW_ACTIONS:
            allowed = " | ".join(sorted(_ALLOWED_REVIEW_ACTIONS))
            raise ValueError(f"action must be one of: {allowed}")
        self.merge_target_note_id = (
            self.merge_target_note_id.strip() if self.merge_target_note_id else None
        )
        self.verification_question = (
            self.verification_question.strip() if self.verification_question else None
        )
        if self.action == "merge" and not self.merge_target_note_id:
            raise ValueError("merge_target_note_id is required when action='merge'")
        if self.action != "merge" and self.merge_target_note_id:
            raise ValueError("merge_target_note_id is only allowed when action='merge'")


@dataclass(slots=True)
class PerspectiveMap:
    """Legacy final map from the previous many-perspectives path."""

    question_id: str
    kept_notes: list[PerspectiveNote]
    map_id: str = field(default_factory=lambda: _make_id("map"))
    merged_groups: list[list[str]] = field(default_factory=list)
    axis_hierarchies: list[AxisHierarchy] = field(default_factory=list)
    perspective_branches: list[PerspectiveBranch] = field(default_factory=list)
    competing_perspectives: list[tuple[str, str]] = field(default_factory=list)
    compatible_perspectives: list[tuple[str, str]] = field(default_factory=list)
    evidence_contests: list[str] = field(default_factory=list)
    boundary_cases: list[str] = field(default_factory=list)
    final_summary: str | None = None

    def __post_init__(self) -> None:
        self.map_id = _require_text(self.map_id, "map_id")
        self.question_id = _require_text(self.question_id, "question_id")
        self.kept_notes = list(self.kept_notes)
        cleaned_groups: list[list[str]] = []
        for group in self.merged_groups:
            cleaned_group = _clean_string_list(group)
            if cleaned_group:
                cleaned_groups.append(cleaned_group)
        self.merged_groups = cleaned_groups
        self.axis_hierarchies = list(self.axis_hierarchies)
        self.perspective_branches = list(self.perspective_branches)
        self.competing_perspectives = _clean_relation_pairs(
            self.competing_perspectives,
            "competing_perspectives item",
        )
        self.compatible_perspectives = _clean_relation_pairs(
            self.compatible_perspectives,
            "compatible_perspectives item",
        )
        self.evidence_contests = _clean_string_list(self.evidence_contests)
        self.boundary_cases = _clean_string_list(self.boundary_cases)
        self.final_summary = self.final_summary.strip() if self.final_summary else None


@dataclass(slots=True)
class PipelineResult:
    """Legacy top-level structured output for the many-perspectives execution path."""

    question_card: QuestionCard
    axis_cards: list[AxisCard] = field(default_factory=list)
    knowledge_cards: list[KnowledgeCard] = field(default_factory=list)
    variable_cards: list[VariableCard] = field(default_factory=list)
    controversy_cards: list[ControversyCard] = field(default_factory=list)
    perspective_notes: list[PerspectiveNote] = field(default_factory=list)
    review_decisions: list[ReviewDecision] = field(default_factory=list)
    kept_notes: list[PerspectiveNote] = field(default_factory=list)
    merged_notes: list[PerspectiveNote] = field(default_factory=list)
    rewrite_notes: list[PerspectiveNote] = field(default_factory=list)
    dropped_notes: list[PerspectiveNote] = field(default_factory=list)
    perspective_map: PerspectiveMap | None = None

    def __post_init__(self) -> None:
        self.axis_cards = list(self.axis_cards)
        self.knowledge_cards = list(self.knowledge_cards)
        self.variable_cards = list(self.variable_cards)
        self.controversy_cards = list(self.controversy_cards)
        self.perspective_notes = list(self.perspective_notes)
        self.review_decisions = list(self.review_decisions)
        self.kept_notes = list(self.kept_notes)
        self.merged_notes = list(self.merged_notes)
        self.rewrite_notes = list(self.rewrite_notes)
        self.dropped_notes = list(self.dropped_notes)


__all__ = [
    "ActorCard",
    "ActorType",
    "CompeteResult",
    "CompetingMechanism",
    "ConstraintCard",
    "DecomposeResult",
    "FalsificationEntry",
    "FinalReport",
    "NodeCard",
    "NodeType",
    "ProblemFrame",
    "StressResult",
    "SurpriseEntry",
    "TraceResult",
    "TraceStep",
    "AxisHierarchy",
    "AxisCard",
    "ControversyCard",
    "KnowledgeCard",
    "PerspectiveMap",
    "PerspectiveBranch",
    "PerspectiveNote",
    "PerspectiveRecord",
    "PipelineInput",
    "PipelineResult",
    "QuestionCard",
    "ReviewAction",
    "ReviewDecision",
    "VariableCard",
]
