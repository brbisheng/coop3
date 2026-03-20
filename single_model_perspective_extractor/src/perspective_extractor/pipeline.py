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


def generate_axes(
    question_card: QuestionCard,
    *,
    knowledge_cards: list[KnowledgeCard] | None = None,
    variable_cards: list[VariableCard] | None = None,
    controversy_cards: list[ControversyCard] | None = None,
) -> list[AxisCard]:
    """Generate axis cards for a normalized question.

    The optional knowledge / variable / controversy cards are auxiliary inputs.
    The resulting ``supporting_card_ids`` field records exactly which upstream
    cards were passed into each axis so downstream stages can trace provenance.
    """

    actor = question_card.actor_entity or "focal actor"
    outcome = question_card.outcome_variable or "focal outcome"
    domain = question_card.domain_hint or "general"
    variable_cards = variable_cards or []
    knowledge_cards = knowledge_cards or []
    controversy_cards = controversy_cards or []

    role_map = {card.variable_role: card for card in variable_cards}
    knowledge_primary = knowledge_cards[:2]
    mechanism_knowledge = knowledge_cards[1:3] or knowledge_cards[:2]
    controversy_primary = controversy_cards[:2]

    axis_specs: list[tuple[str, str, str, str, list[KnowledgeCard | VariableCard | ControversyCard]]] = [
        (
            "baseline framing",
            "framing",
            f"Clarify how {actor} and {outcome} should be defined before comparing perspectives.",
            "Separates construct definition and scope setting from later causal or evaluative claims.",
            [*knowledge_primary, *[card for role, card in role_map.items() if role in {"actor", "outcome", "constraint"}]],
        ),
        (
            "causal pathways",
            "mechanism",
            f"Examine the direct and indirect channels through which {actor} could shape {outcome}.",
            "Centers mechanism differences rather than only the direction of the effect.",
            [*mechanism_knowledge, *[card for role, card in role_map.items() if role in {"actor", "state", "outcome"}], *controversy_primary[:1]],
        ),
        (
            "decision and implementation",
            "decision",
            f"Compare choices about whether, when, and how to deploy {actor} in the {domain} domain.",
            "Focuses on actionable levers and implementation tradeoffs instead of abstract relationship claims.",
            [*[card for role, card in role_map.items() if role in {"decision", "constraint", "outcome"}], *controversy_primary[:1]],
        ),
        (
            "scope conditions",
            "scope",
            f"Test when claims about {actor} and {outcome} travel across populations, settings, and time horizons.",
            "Highlights heterogeneity and external-validity boundaries that can reverse conclusions.",
            [*[card for role, card in role_map.items() if role in {"state", "constraint", "outcome"}], *controversy_primary[1:2], *knowledge_cards[2:4]],
        ),
    ]

    axes: list[AxisCard] = []
    for priority, (name, axis_type, focus, distinctness, supporting_cards) in enumerate(axis_specs, start=1):
        summary = _summarize_supporting_cards(
            knowledge_cards=[card for card in supporting_cards if isinstance(card, KnowledgeCard)],
            variable_cards=[card for card in supporting_cards if isinstance(card, VariableCard)],
            controversy_cards=[card for card in supporting_cards if isinstance(card, ControversyCard)],
        )
        axes.append(
            AxisCard(
                name=name,
                axis_type=axis_type,
                focus=focus,
                how_is_it_distinct=(distinctness + (f" Support trace: {'; '.join(summary)}." if summary else "")),
                priority=priority,
                evidence_needed=[
                    f"Evidence needed for the {name} axis on question {question_card.question_id}.",
                ],
                verification_question=f"Does the {name} axis add a distinct lens on {question_card.cleaned_question}",
                supporting_card_ids=_unique_card_ids(supporting_cards),
            )
        )
    return axes


def expand_axis(
    axis_card: AxisCard,
    question_card: QuestionCard,
    *,
    knowledge_cards: list[KnowledgeCard] | None = None,
    variable_cards: list[VariableCard] | None = None,
    controversy_cards: list[ControversyCard] | None = None,
) -> list[PerspectiveNote]:
    """Expand one axis into a small set of traceable perspective notes."""

    actor = question_card.actor_entity or "the focal actor"
    outcome = question_card.outcome_variable or "the focal outcome"
    support_ids = list(axis_card.supporting_card_ids)
    support_summary = _summarize_supporting_cards(
        knowledge_cards=knowledge_cards,
        variable_cards=variable_cards,
        controversy_cards=controversy_cards,
    )
    trace_text = "; ".join(support_summary) if support_summary else "no auxiliary cards supplied"

    notes = [
        PerspectiveNote(
            axis_id=axis_card.axis_id,
            core_claim=f"The {axis_card.name} axis suggests one explanation for how {actor} relates to {outcome}.",
            reasoning=(
                f"This note stays within the {axis_card.axis_type} lens and uses traceable support from {trace_text}."
            ),
            boundary_condition="Interpretation may change when population, setting, or timeframe shifts.",
            evidence_needed=[
                f"Evidence that directly speaks to the {axis_card.name} axis.",
                *[f"Support card {card_id}" for card_id in support_ids[:3]],
            ],
            testable_implication=f"If this {axis_card.name} perspective is right, observed patterns in {outcome} should differ across the axis focus.",
            verification_question=f"What evidence would confirm or falsify the {axis_card.name} perspective?",
            supporting_card_ids=support_ids,
        )
    ]

    if controversy_cards:
        notes.append(
            PerspectiveNote(
                axis_id=axis_card.axis_id,
                core_claim=f"A competing perspective on {axis_card.name} emphasizes disagreement rather than consensus.",
                reasoning=(
                    f"This alternative note foregrounds contested explanations for {actor} and {outcome} while preserving the same support trace."
                ),
                counterexample="A different causal story may fit the same observations if scope conditions change.",
                evidence_needed=[
                    "Evidence that distinguishes competing explanations.",
                    *[f"Support card {card_id}" for card_id in support_ids[:3]],
                ],
                verification_question="Which observations would favor one competing explanation over another?",
                competing_perspectives=[axis_card.name],
                supporting_card_ids=support_ids,
            )
        )

    return notes


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
    "generate_axes",
    "review_notes",
    "run_pipeline",
]
