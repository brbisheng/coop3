"""Expansion helpers for isolated single-axis perspective notes."""

from __future__ import annotations

from collections.abc import Iterable

from .models import (
    AxisCard,
    ControversyCard,
    KnowledgeCard,
    PerspectiveNote,
    PerspectiveRecord,
    QuestionCard,
    VariableCard,
)

_ContextCard = KnowledgeCard | VariableCard | ControversyCard
_ALLOWED_CONTEXT_CARD_TYPES = (KnowledgeCard, VariableCard, ControversyCard)


def expand_candidates(records: list[PerspectiveRecord]) -> list[PerspectiveRecord]:
    """Return records unchanged until expansion logic is implemented."""

    return records


def expand_axis(
    question_card: QuestionCard,
    axis_card: AxisCard,
    context_cards: Iterable[_ContextCard] | None = None,
) -> PerspectiveNote:
    """Expand a single axis into one isolated perspective note.

    The expansion only sees the original question, the current ``AxisCard``, and
    an optional minimal set of knowledge / variable / controversy cards. Full
    notes from other axes are deliberately excluded to preserve isolated passes.
    """

    cards = _normalize_context_cards(context_cards)
    support_ids = _supporting_card_ids(axis_card=axis_card, context_cards=cards)

    actor = question_card.actor_entity or "the focal actor"
    outcome = question_card.outcome_variable or "the focal outcome"
    domain = question_card.domain_hint or "the focal domain"

    knowledge_cards = [card for card in cards if isinstance(card, KnowledgeCard)]
    variable_cards = [card for card in cards if isinstance(card, VariableCard)]
    controversy_cards = [card for card in cards if isinstance(card, ControversyCard)]

    claim_parts = [
        f"Within the {axis_card.name} axis, the relationship between {actor} and {outcome}",
        f"should be interpreted through {axis_card.focus.rstrip('.')}.",
    ]
    if variable_cards:
        claim_parts.append(
            f"The most relevant measurable levers are {_join_phrases(card.name for card in variable_cards[:2])}."
        )
    core_claim = " ".join(claim_parts)

    reasoning_parts = [
        f"This note isolates the {axis_card.axis_type} lens instead of mixing it with other perspective answers.",
        axis_card.how_is_it_distinct,
        (
            f"For the question '{question_card.cleaned_question}', that means tracing how this lens "
            f"changes what counts as a persuasive explanation in {domain}."
        ),
    ]
    if knowledge_cards:
        reasoning_parts.append(
            "Relevant background cards emphasize "
            + _join_phrases(card.title.lower() for card in knowledge_cards[:2])
            + "."
        )
    if controversy_cards:
        reasoning_parts.append(
            "A remaining disagreement is whether "
            + controversy_cards[0].question[0].lower()
            + controversy_cards[0].question[1:].rstrip("?")
            + "."
        )
    reasoning = " ".join(reasoning_parts)

    counterexample = (
        f"A plausible counterexample is a setting where {actor} and {outcome} move together for reasons "
        f"outside the {axis_card.name} lens, such as selection effects, measurement artifacts, or an "
        "omitted institutional change."
    )
    if controversy_cards:
        counterexample = (
            f"A plausible counterexample is the competing view that {controversy_cards[0].sides[1].rstrip('.')}, "
            f"so the {axis_card.name} axis would overstate its own explanatory power."
        )

    boundary_condition = (
        f"This perspective is most informative only when the question stays within the stated scope of {domain} "
        f"and when {axis_card.focus.rstrip('.').lower()} is actually observable."
    )
    if knowledge_cards:
        boundary_condition = (
            boundary_condition[:-1]
            + f" It becomes weaker if {knowledge_cards[0].title.lower()} is poorly specified or if the population, timeframe, or comparator changes."
        )

    evidence_needed = [
        f"Direct evidence about whether {axis_card.focus.rstrip('.').lower()} explains variation in {outcome}.",
        f"Measures that distinguish the {axis_card.axis_type} lens from rival explanations for {actor}.",
    ]
    for card in cards[:3]:
        evidence_needed.append(f"Support card {_card_identifier(card)}: {_card_evidence_line(card)}")

    testable_implication = (
        f"If the {axis_card.name} axis is doing real explanatory work, then differences in "
        f"{_implication_driver(axis_card, variable_cards)} should predict a different pattern in {outcome} "
        "even before combining this note with other axes."
    )

    verification_question = (
        axis_card.verification_question
        or f"What evidence would show that the {axis_card.name} axis adds explanatory value on its own?"
    )

    return PerspectiveNote(
        axis_id=axis_card.axis_id,
        core_claim=core_claim,
        reasoning=reasoning,
        counterexample=counterexample,
        boundary_condition=boundary_condition,
        evidence_needed=evidence_needed,
        testable_implication=testable_implication,
        verification_question=verification_question,
        supporting_card_ids=support_ids,
        competing_perspectives=[card.question for card in controversy_cards[:1]],
        compatible_perspectives=[axis_card.axis_type],
    )


def _normalize_context_cards(context_cards: Iterable[_ContextCard] | None) -> list[_ContextCard]:
    if context_cards is None:
        return []

    cards = list(context_cards)
    for card in cards:
        if not isinstance(card, _ALLOWED_CONTEXT_CARD_TYPES):
            raise TypeError(
                "context_cards may only contain KnowledgeCard, VariableCard, or ControversyCard instances"
            )
    return cards


def _supporting_card_ids(*, axis_card: AxisCard, context_cards: list[_ContextCard]) -> list[str]:
    allowed_ids = {
        getattr(card, "knowledge_id", None)
        or getattr(card, "variable_id", None)
        or getattr(card, "controversy_id", None)
        for card in context_cards
    }
    ordered: list[str] = []
    for card_id in axis_card.supporting_card_ids:
        if card_id in allowed_ids and card_id not in ordered:
            ordered.append(card_id)
    return ordered


def _card_identifier(card: _ContextCard) -> str:
    if isinstance(card, KnowledgeCard):
        return card.knowledge_id
    if isinstance(card, VariableCard):
        return card.variable_id
    return card.controversy_id


def _card_evidence_line(card: _ContextCard) -> str:
    if isinstance(card, KnowledgeCard):
        return (
            f"Knowledge card '{card.title}' needs verification via: "
            f"{card.verification_question or card.content}."
        )
    if isinstance(card, VariableCard):
        return (
            f"Variable card '{card.name}' requires measurement evidence: "
            f"{card.measurement_notes or card.definition}."
        )
    return (
        f"Controversy card '{card.question}' needs evidence that can separate: "
        f"{_join_phrases(card.sides[:2])}."
    )


def _implication_driver(axis_card: AxisCard, variable_cards: list[VariableCard]) -> str:
    if variable_cards:
        return _join_phrases(card.name for card in variable_cards[:2])
    return axis_card.name


def _join_phrases(values: Iterable[str]) -> str:
    cleaned = [value.strip() for value in values if value and value.strip()]
    if not cleaned:
        return "the focal factors"
    if len(cleaned) == 1:
        return cleaned[0]
    if len(cleaned) == 2:
        return f"{cleaned[0]} and {cleaned[1]}"
    return ", ".join(cleaned[:-1]) + f", and {cleaned[-1]}"
