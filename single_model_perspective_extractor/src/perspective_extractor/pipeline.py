"""End-to-end pipeline orchestration."""

from __future__ import annotations

from .models import (
    AxisCard,
    ControversyCard,
    KnowledgeCard,
    PerspectiveMap,
    PerspectiveNote,
    PerspectiveRecord,
    PipelineInput,
    PipelineResult,
    QuestionCard,
    ReviewDecision,
    VariableCard,
)
from .normalize import normalize_question, normalize_text
from .knowledge import (
    collect_background,
    generate_controversy_cards,
    generate_knowledge_cards,
    generate_variable_cards,
)
from .review import review_records
from .synthesize import synthesize_summary
from .axes import generate_axes
from .expand import expand_axis as expand_axis_note


def _card_id(card: KnowledgeCard | VariableCard | ControversyCard) -> str:
    if isinstance(card, KnowledgeCard):
        return card.knowledge_id
    if isinstance(card, VariableCard):
        return card.variable_id
    return card.controversy_id


def _card_label(card: KnowledgeCard | VariableCard | ControversyCard) -> str:
    if isinstance(card, KnowledgeCard):
        return card.title
    if isinstance(card, VariableCard):
        return f"{card.variable_role}:{card.name}"
    return card.question


def _unique_card_ids(*card_groups: list[KnowledgeCard | VariableCard | ControversyCard]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for group in card_groups:
        for card in group:
            card_identifier = _card_id(card)
            if card_identifier not in seen:
                seen.add(card_identifier)
                ordered.append(card_identifier)
    return ordered


def _summarize_supporting_cards(
    *,
    knowledge_cards: list[KnowledgeCard] | None = None,
    variable_cards: list[VariableCard] | None = None,
    controversy_cards: list[ControversyCard] | None = None,
) -> list[str]:
    summary: list[str] = []
    for label, cards in (
        ("knowledge", knowledge_cards or []),
        ("variable", variable_cards or []),
        ("controversy", controversy_cards or []),
    ):
        if cards:
            summary.append(
                f"{label} support: " + ", ".join(_card_label(card) for card in cards[:2])
            )
    return summary


def _note_id_for_axis(axis_id: str) -> str:
    """Derive a deterministic note identifier for a given axis identifier."""

    if axis_id.startswith("axis_"):
        return f"note_{axis_id[5:]}"
    return f"note_{axis_id}"



def _select_axis_context_cards(
    axis_card: AxisCard,
    *,
    knowledge_cards: list[KnowledgeCard] | None = None,
    variable_cards: list[VariableCard] | None = None,
    controversy_cards: list[ControversyCard] | None = None,
) -> list[KnowledgeCard | VariableCard | ControversyCard]:
    """Return only the supporting cards assigned to the current axis."""

    ordered_cards: list[KnowledgeCard | VariableCard | ControversyCard] = [
        *(knowledge_cards or []),
        *(variable_cards or []),
        *(controversy_cards or []),
    ]
    if not axis_card.supporting_card_ids:
        return []

    card_lookup = {_card_id(card): card for card in ordered_cards}
    return [
        card_lookup[card_id]
        for card_id in axis_card.supporting_card_ids
        if card_id in card_lookup
    ]



def expand_axis(
    axis_card: AxisCard,
    question_card: QuestionCard,
    *,
    knowledge_cards: list[KnowledgeCard] | None = None,
    variable_cards: list[VariableCard] | None = None,
    controversy_cards: list[ControversyCard] | None = None,
) -> list[PerspectiveNote]:
    """Expand one axis into an isolated traceable perspective note."""

    note = expand_axis_note(
        question_card,
        axis_card,
        context_cards=_select_axis_context_cards(
            axis_card,
            knowledge_cards=knowledge_cards,
            variable_cards=variable_cards,
            controversy_cards=controversy_cards,
        ),
    )
    note.note_id = _note_id_for_axis(axis_card.axis_id)
    return [note]



def expand_axes(
    axis_cards: list[AxisCard],
    question_card: QuestionCard,
    *,
    knowledge_cards: list[KnowledgeCard] | None = None,
    variable_cards: list[VariableCard] | None = None,
    controversy_cards: list[ControversyCard] | None = None,
) -> list[PerspectiveNote]:
    """Expand all axes independently and return the raw PerspectiveNote list."""

    perspective_notes: list[PerspectiveNote] = []
    for axis_card in axis_cards:
        perspective_notes.extend(
            expand_axis(
                axis_card,
                question_card,
                knowledge_cards=knowledge_cards,
                variable_cards=variable_cards,
                controversy_cards=controversy_cards,
            )
        )
    return perspective_notes


def review_notes(notes: list[PerspectiveNote]) -> list[ReviewDecision]:
    """Return a keep decision for each note until richer review logic lands."""

    return [
        ReviewDecision(
            target_note_id=note.note_id,
            action="keep",
            reason="Retained as a distinct scaffolded perspective note.",
        )
        for note in notes
    ]


def build_perspective_map(
    question_card: QuestionCard,
    kept_notes: list[PerspectiveNote],
    controversy_cards: list[ControversyCard] | None = None,
) -> PerspectiveMap:
    """Assemble the final perspective map from reviewed notes."""

    competing_pairs: list[tuple[str, str]] = []
    evidence_contests: list[str] = []
    controversy_cards = controversy_cards or []
    if len(kept_notes) >= 2:
        competing_pairs.append((kept_notes[0].note_id, kept_notes[1].note_id))
    for card in controversy_cards:
        evidence_contests.extend(card.evidence_contests)

    return PerspectiveMap(
        question_id=question_card.question_id,
        kept_notes=kept_notes,
        competing_perspectives=competing_pairs,
        evidence_contests=evidence_contests,
        final_summary=f"Generated {len(kept_notes)} kept perspective notes for {question_card.cleaned_question}",
    )


def run_pipeline(question: str) -> PipelineResult:
    """Run the structured perspective-extraction pipeline for one question."""

    question_card = normalize_question(question)
    knowledge_cards = generate_knowledge_cards(question_card)
    variable_cards = generate_variable_cards(question_card)
    controversy_cards = generate_controversy_cards(question_card)

    axis_cards = generate_axes(
        question_card,
        knowledge_cards=knowledge_cards,
        variable_cards=variable_cards,
        controversy_cards=controversy_cards,
    )

    perspective_notes = expand_axes(
        axis_cards,
        question_card,
        knowledge_cards=knowledge_cards,
        variable_cards=variable_cards,
        controversy_cards=controversy_cards,
    )

    review_decisions = review_notes(perspective_notes)
    kept_note_ids = {decision.target_note_id for decision in review_decisions if decision.action == "keep"}
    kept_notes = [note for note in perspective_notes if note.note_id in kept_note_ids]
    perspective_map = build_perspective_map(
        question_card,
        kept_notes,
        controversy_cards=controversy_cards,
    )

    return PipelineResult(
        question_card=question_card,
        axis_cards=axis_cards,
        knowledge_cards=knowledge_cards,
        variable_cards=variable_cards,
        controversy_cards=controversy_cards,
        perspective_notes=perspective_notes,
        review_decisions=review_decisions,
        perspective_map=perspective_map,
    )


class PerspectiveExtractionPipeline:
    """Backward-compatible orchestrator for the earlier scaffold interface."""

    def run(self, pipeline_input: PipelineInput) -> list[PerspectiveRecord]:
        normalized_topic = normalize_text(pipeline_input.topic)
        source_text = normalize_text(pipeline_input.source_text)
        background = collect_background(normalized_topic)
        result = run_pipeline(normalized_topic)

        records = [
            PerspectiveRecord(
                axis=axis_card.name,
                summary=(
                    f"{len([note for note in result.perspective_notes if note.axis_id == axis_card.axis_id])} note(s) "
                    f"using {len(axis_card.supporting_card_ids)} support card(s) and {len(background)} background item(s)"
                ),
                evidence=[*background, source_text] if source_text else list(background),
            )
            for axis_card in result.axis_cards
        ]
        return review_records(records)

    def summarize(self, pipeline_input: PipelineInput) -> str:
        return synthesize_summary(self.run(pipeline_input))


__all__ = [
    "PerspectiveExtractionPipeline",
    "build_perspective_map",
    "expand_axis",
    "expand_axes",
    "generate_axes",
    "review_notes",
    "run_pipeline",
]
