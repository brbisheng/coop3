"""Shared data models for the perspective extractor pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal
from uuid import uuid4

ReviewAction = Literal["keep", "merge", "rewrite", "drop"]
_ALLOWED_REVIEW_ACTIONS = {"keep", "merge", "rewrite", "drop"}


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
    """One structurally distinct observation window on the question."""

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
    """An independently generated perspective tied to a single axis."""

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
class ReviewDecision:
    """Overlap or novelty judgment for a generated perspective."""

    target_note_id: str
    action: ReviewAction
    reason: str
    decision_id: str = field(default_factory=lambda: _make_id("decision"))
    merge_target_note_id: str | None = None

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
        if self.action == "merge" and not self.merge_target_note_id:
            raise ValueError("merge_target_note_id is required when action='merge'")
        if self.action != "merge" and self.merge_target_note_id:
            raise ValueError("merge_target_note_id is only allowed when action='merge'")


@dataclass(slots=True)
class PerspectiveMap:
    """Final structured map preserving perspective tension and compatibility."""

    question_id: str
    kept_notes: list[PerspectiveNote]
    map_id: str = field(default_factory=lambda: _make_id("map"))
    merged_groups: list[list[str]] = field(default_factory=list)
    competing_perspectives: list[tuple[str, str]] = field(default_factory=list)
    compatible_perspectives: list[tuple[str, str]] = field(default_factory=list)
    evidence_contests: list[str] = field(default_factory=list)
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
        self.competing_perspectives = _clean_relation_pairs(
            self.competing_perspectives,
            "competing_perspectives item",
        )
        self.compatible_perspectives = _clean_relation_pairs(
            self.compatible_perspectives,
            "compatible_perspectives item",
        )
        self.evidence_contests = _clean_string_list(self.evidence_contests)
        self.final_summary = self.final_summary.strip() if self.final_summary else None


@dataclass(slots=True)
class PipelineResult:
    """Top-level structured output for a complete pipeline execution."""

    question_card: QuestionCard
    axis_cards: list[AxisCard] = field(default_factory=list)
    knowledge_cards: list[KnowledgeCard] = field(default_factory=list)
    variable_cards: list[VariableCard] = field(default_factory=list)
    controversy_cards: list[ControversyCard] = field(default_factory=list)
    perspective_notes: list[PerspectiveNote] = field(default_factory=list)
    review_decisions: list[ReviewDecision] = field(default_factory=list)
    perspective_map: PerspectiveMap | None = None

    def __post_init__(self) -> None:
        self.axis_cards = list(self.axis_cards)
        self.knowledge_cards = list(self.knowledge_cards)
        self.variable_cards = list(self.variable_cards)
        self.controversy_cards = list(self.controversy_cards)
        self.perspective_notes = list(self.perspective_notes)
        self.review_decisions = list(self.review_decisions)


__all__ = [
    "AxisCard",
    "ControversyCard",
    "KnowledgeCard",
    "PerspectiveMap",
    "PerspectiveNote",
    "PerspectiveRecord",
    "PipelineInput",
    "PipelineResult",
    "QuestionCard",
    "ReviewAction",
    "ReviewDecision",
    "VariableCard",
]
