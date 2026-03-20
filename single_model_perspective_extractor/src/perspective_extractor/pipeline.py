"""End-to-end pipeline orchestration."""

from __future__ import annotations

from dataclasses import dataclass

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
from .review import review_notes as review_note_decisions, review_records
from .synthesize import synthesize_map, synthesize_summary
from .axes import generate_axes
from .expand import expand_axis as expand_axis_note
from .prompts import PromptVariant, resolve_prompt_variant


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


@dataclass(frozen=True, slots=True)
class PipelinePromptConfig:
    """Reserved prompt/lens options for forward-compatible pipeline entrypoints."""

    prompt_variant: PromptVariant | None = None
    lens: PromptVariant | None = None

    @property
    def resolved_prompt_variant(self) -> PromptVariant | None:
        """Return the validated prompt variant selected for this pipeline run."""

        return resolve_prompt_variant(prompt_variant=self.prompt_variant, lens=self.lens)



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


def review_notes(question_card: QuestionCard, notes: list[PerspectiveNote]) -> list[ReviewDecision]:
    """Review expanded notes for overlap, novelty, and rewrite needs."""

    return review_note_decisions(question_card, notes)


def build_perspective_map(
    question_card: QuestionCard,
    kept_notes: list[PerspectiveNote],
    review_decisions: list[ReviewDecision],
) -> PerspectiveMap:
    """Assemble the final perspective map from reviewed notes."""

    return synthesize_map(question_card, kept_notes, review_decisions)


def _partition_notes_by_review_action(
    notes: list[PerspectiveNote],
    review_decisions: list[ReviewDecision],
) -> dict[str, list[PerspectiveNote]]:
    """Group expanded notes by review action for debug-friendly pipeline output."""

    note_lookup = {note.note_id: note for note in notes}
    grouped_notes: dict[str, list[PerspectiveNote]] = {
        "keep": [],
        "merge": [],
        "rewrite": [],
        "drop": [],
    }

    for decision in review_decisions:
        note = note_lookup.get(decision.target_note_id)
        if note is None:
            continue
        grouped_notes[decision.action].append(note)

    return grouped_notes


def run_pipeline(
    question: str,
    *,
    prompt_variant: PromptVariant | None = None,
    lens: PromptVariant | None = None,
) -> PipelineResult:
    """Run the full structured perspective-extraction pipeline for one question.

    The returned ``PipelineResult`` preserves the full stage-by-stage trace:
    normalized question, support cards, axis cards, raw notes, review decisions,
    action-specific note partitions, and the synthesized final map.
    """

    PipelinePromptConfig(
        prompt_variant=prompt_variant,
        lens=lens,
    ).resolved_prompt_variant

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

    review_decisions = review_notes(question_card, perspective_notes)
    notes_by_action = _partition_notes_by_review_action(perspective_notes, review_decisions)
    kept_notes = notes_by_action["keep"]
    perspective_map = build_perspective_map(
        question_card,
        kept_notes,
        review_decisions=review_decisions,
    )

    return PipelineResult(
        question_card=question_card,
        axis_cards=axis_cards,
        knowledge_cards=knowledge_cards,
        variable_cards=variable_cards,
        controversy_cards=controversy_cards,
        perspective_notes=perspective_notes,
        review_decisions=review_decisions,
        kept_notes=kept_notes,
        merged_notes=notes_by_action["merge"],
        rewrite_notes=notes_by_action["rewrite"],
        dropped_notes=notes_by_action["drop"],
        perspective_map=perspective_map,
    )


class PerspectiveExtractionPipeline:
    """Backward-compatible orchestrator for the earlier scaffold interface."""

    def run(
        self,
        pipeline_input: PipelineInput,
        *,
        prompt_variant: PromptVariant | None = None,
        lens: PromptVariant | None = None,
    ) -> list[PerspectiveRecord]:
        normalized_topic = normalize_text(pipeline_input.topic)
        source_text = normalize_text(pipeline_input.source_text)
        background = collect_background(normalized_topic)
        result = run_pipeline(
            normalized_topic,
            prompt_variant=prompt_variant,
            lens=lens,
        )

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

    def summarize(
        self,
        pipeline_input: PipelineInput,
        *,
        prompt_variant: PromptVariant | None = None,
        lens: PromptVariant | None = None,
    ) -> str:
        return synthesize_summary(
            self.run(
                pipeline_input,
                prompt_variant=prompt_variant,
                lens=lens,
            )
        )


__all__ = [
    "PerspectiveExtractionPipeline",
    "PipelinePromptConfig",
    "build_perspective_map",
    "expand_axis",
    "expand_axes",
    "generate_axes",
    "review_notes",
    "run_pipeline",
]
