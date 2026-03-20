"""Expansion helpers for isolated single-axis perspective notes."""

from __future__ import annotations

from collections.abc import Iterable, Sequence

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
_Subanswer = tuple[str, str]


def expand_candidates(records: list[PerspectiveRecord]) -> list[PerspectiveRecord]:
    """Return records unchanged until expansion logic is implemented."""

    return records


def plan_axis_subquestions(
    question_card: QuestionCard,
    axis_card: AxisCard,
    context_cards: Iterable[_ContextCard] | None = None,
) -> list[str]:
    """Plan a focused set of axis-specific subquestions for isolated expansion."""

    cards = _normalize_context_cards(context_cards)
    actor = question_card.actor_entity or "the focal actor"
    outcome = question_card.outcome_variable or "the focal outcome"
    focus = axis_card.focus.rstrip(".")
    domain = question_card.domain_hint or "the focal domain"

    knowledge_cards = [card for card in cards if isinstance(card, KnowledgeCard)]
    variable_cards = [card for card in cards if isinstance(card, VariableCard)]
    controversy_cards = [card for card in cards if isinstance(card, ControversyCard)]

    subquestions = [
        f"Within the {axis_card.name} axis, which part of {focus} most directly links {actor} to {outcome}?",
        f"Within the {axis_card.name} axis, what observable variation would show that the {axis_card.axis_type} lens explains {outcome} rather than merely redescribing the question?",
        f"Which scope conditions in {domain} must hold before the {axis_card.name} axis should be treated as informative?",
    ]

    if variable_cards:
        for card in variable_cards[:2]:
            subquestions.append(
                f"Within the {axis_card.name} axis, how should {card.name} be measured or compared so it tests this lens instead of a rival explanation?"
            )

    if knowledge_cards:
        subquestions.append(
            f"Within the {axis_card.name} axis, how does the background card '{knowledge_cards[0].title}' sharpen or constrain this interpretation?"
        )
    else:
        subquestions.append(
            f"Which concrete mechanism or decision point inside {focus} would make this axis produce a distinct prediction?"
        )

    if controversy_cards:
        subquestions.append(
            f"Within the {axis_card.name} axis, how would answering '{controversy_cards[0].question}' change confidence in this lens?"
        )
    else:
        subquestions.append(
            f"What is the strongest nearby counter-hypothesis that could mimic the {axis_card.name} pattern?"
        )

    return _bounded_unique_questions(subquestions, minimum=3, maximum=7)



def compose_perspective_note_from_subanswers(
    question_card: QuestionCard,
    axis_card: AxisCard,
    subanswers: Sequence[_Subanswer],
    context_cards: Iterable[_ContextCard] | None = None,
) -> PerspectiveNote:
    """Compose a traceable perspective note from planned subanswers."""

    if not subanswers:
        raise ValueError("subanswers must not be empty")

    cards = _normalize_context_cards(context_cards)
    support_ids = _supporting_card_ids(axis_card=axis_card, context_cards=cards)

    actor = question_card.actor_entity or "the focal actor"
    outcome = question_card.outcome_variable or "the focal outcome"
    domain = question_card.domain_hint or "the focal domain"

    knowledge_cards = [card for card in cards if isinstance(card, KnowledgeCard)]
    variable_cards = [card for card in cards if isinstance(card, VariableCard)]
    controversy_cards = [card for card in cards if isinstance(card, ControversyCard)]

    planned_subquestions = [question for question, _ in subanswers]
    subanswer_trace = [f"Q{index}: {question} -> {answer}" for index, (question, answer) in enumerate(subanswers, start=1)]

    claim_parts = [
        f"Within the {axis_card.name} axis, the relationship between {actor} and {outcome}",
        f"should be interpreted through {axis_card.focus.rstrip('.')}.",
        f"This claim is anchored in {subanswer_trace[0].split(' -> ', 1)[1]}",
    ]
    if len(subanswer_trace) > 1:
        claim_parts.append(f"and refined by {subanswer_trace[1].split(' -> ', 1)[1]}")
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
        "Derived from subquestions: " + " | ".join(subanswer_trace[:4]),
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
        f"outside the {axis_card.name} lens, such as { _extract_counterweight(subanswers)}."
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
    for index, (question, answer) in enumerate(subanswers, start=1):
        evidence_needed.append(f"Subquestion trace Q{index}: {question} -> {answer}")
    for card in cards[:3]:
        evidence_needed.append(f"Support card {_card_identifier(card)}: {_card_evidence_line(card)}")

    testable_implication = (
        f"If the {axis_card.name} axis is doing real explanatory work, then differences in "
        f"{_implication_driver(axis_card, variable_cards)} should predict a different pattern in {outcome} "
        f"because {subanswer_trace[min(2, len(subanswer_trace) - 1)].split(' -> ', 1)[1]}"
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
        planned_subquestions=planned_subquestions,
        subanswer_trace=subanswer_trace,
    )



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
    subquestions = plan_axis_subquestions(question_card, axis_card, context_cards=cards)
    subanswers = [
        (subquestion, _draft_subanswer(subquestion, question_card, axis_card, cards))
        for subquestion in subquestions
    ]
    return compose_perspective_note_from_subanswers(
        question_card,
        axis_card,
        subanswers,
        context_cards=cards,
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



def _bounded_unique_questions(values: Sequence[str], *, minimum: int, maximum: int) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        question = value.strip()
        if not question or question in seen:
            continue
        seen.add(question)
        ordered.append(question)
        if len(ordered) == maximum:
            break
    if len(ordered) < minimum:
        raise ValueError(f"expected at least {minimum} subquestions, got {len(ordered)}")
    return ordered



def _draft_subanswer(
    subquestion: str,
    question_card: QuestionCard,
    axis_card: AxisCard,
    cards: list[_ContextCard],
) -> str:
    actor = question_card.actor_entity or "the focal actor"
    outcome = question_card.outcome_variable or "the focal outcome"
    domain = question_card.domain_hint or "the focal domain"
    knowledge_cards = [card for card in cards if isinstance(card, KnowledgeCard)]
    variable_cards = [card for card in cards if isinstance(card, VariableCard)]
    controversy_cards = [card for card in cards if isinstance(card, ControversyCard)]

    if "most directly links" in subquestion:
        return (
            f"the decisive pathway is whether {axis_card.focus.rstrip('.').lower()} creates an observable channel from {actor} to changes in {outcome}"
        )
    if "observable variation" in subquestion:
        driver = _implication_driver(axis_card, variable_cards)
        return f"the axis earns explanatory status only if variation in {driver} predicts {outcome} better than a generic restatement of the question"
    if "scope conditions" in subquestion:
        return f"the lens is informative only when the comparison stays inside {domain} and the relevant population, timeframe, and comparator are stable"
    if "measured or compared" in subquestion and variable_cards:
        return f"the measure must distinguish {_join_phrases(card.name for card in variable_cards[:2])} from confounds so the {axis_card.name} axis can be tested directly"
    if knowledge_cards and knowledge_cards[0].title in subquestion:
        return f"'{knowledge_cards[0].title}' narrows the interpretation by highlighting {knowledge_cards[0].content.rstrip('.')}"
    if controversy_cards and controversy_cards[0].question in subquestion:
        return f"confidence rises if evidence resolves '{controversy_cards[0].question}' in favor of the axis rather than the competing side '{controversy_cards[0].sides[1]}'"
    if "counter-hypothesis" in subquestion:
        return f"a nearby rival is that selection effects or measurement artifacts, not {axis_card.focus.rstrip('.').lower()}, are generating the apparent pattern"
    return f"the answer should stay tied to {axis_card.name} by checking whether {axis_card.focus.rstrip('.').lower()} changes what counts as evidence for {outcome}"



def _extract_counterweight(subanswers: Sequence[_Subanswer]) -> str:
    for _, answer in reversed(subanswers):
        lowered = answer.lower()
        if "selection effects" in lowered or "measurement artifacts" in lowered:
            return "selection effects, measurement artifacts, or omitted institutional changes"
    return "selection effects, measurement artifacts, or an omitted institutional change"
