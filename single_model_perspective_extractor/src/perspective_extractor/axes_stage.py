"""Explicit axis-generation stage prompt builder."""

from __future__ import annotations

from .llm import StageModelCaller, StagePrompt, invoke_stage_prompt
from .models import ControversyCard, KnowledgeCard, QuestionCard, VariableCard

_AXES_STAGE_PROMPT = """Generate perspective axes for the research question below.

Question:
- {cleaned_question}

Known context:
- actor: {actor}
- outcome: {outcome}
- domain: {domain}
- assumptions: {assumptions}
- missing pieces: {missing_pieces}
- support summary: {support_summary}

Return JSON with one top-level key named axes containing a list of axis objects.
Each axis object must include:
- name
- axis_type
- focus
- how_is_it_distinct

Rules:
- Produce 8 to 12 axes.
- Cover multiple structure types rather than only mechanism.
- Axis names should be short noun phrases, not conclusions.
- Do not answer the question.
- Make each axis distinct enough to inspect on its own.
"""


def build_axes_stage_prompt(
    question_card: QuestionCard,
    *,
    knowledge_cards: list[KnowledgeCard] | None = None,
    variable_cards: list[VariableCard] | None = None,
    controversy_cards: list[ControversyCard] | None = None,
) -> StagePrompt:
    """Return the explicit axis-stage prompt for a live model call."""

    knowledge_cards = knowledge_cards or []
    variable_cards = variable_cards or []
    controversy_cards = controversy_cards or []

    support_summary = _support_summary(
        knowledge_cards=knowledge_cards,
        variable_cards=variable_cards,
        controversy_cards=controversy_cards,
    )
    actor = question_card.actor_entity or "the focal actor"
    outcome = question_card.outcome_variable or "the focal outcome"
    domain = question_card.domain_hint or "general"
    return StagePrompt(
        stage_name="axes",
        prompt=_AXES_STAGE_PROMPT.format(
            cleaned_question=question_card.cleaned_question,
            actor=actor,
            outcome=outcome,
            domain=domain,
            assumptions=", ".join(question_card.assumptions[:3]) or "none noted",
            missing_pieces=", ".join(question_card.missing_pieces[:4]) or "none noted",
            support_summary=support_summary,
        ),
    )


def run_axes_stage(
    question_card: QuestionCard,
    *,
    knowledge_cards: list[KnowledgeCard] | None = None,
    variable_cards: list[VariableCard] | None = None,
    controversy_cards: list[ControversyCard] | None = None,
    call_model: StageModelCaller | None = None,
) -> str:
    """Run the axis-stage prompt with an explicit live model caller."""

    return invoke_stage_prompt(
        build_axes_stage_prompt(
            question_card,
            knowledge_cards=knowledge_cards,
            variable_cards=variable_cards,
            controversy_cards=controversy_cards,
        ),
        call_model=call_model,
    )


def _support_summary(
    *,
    knowledge_cards: list[KnowledgeCard],
    variable_cards: list[VariableCard],
    controversy_cards: list[ControversyCard],
) -> str:
    summary: list[str] = []
    if knowledge_cards:
        summary.append("knowledge: " + ", ".join(card.title for card in knowledge_cards[:2]))
    if variable_cards:
        summary.append("variables: " + ", ".join(card.name for card in variable_cards[:3]))
    if controversy_cards:
        summary.append("controversies: " + ", ".join(card.question for card in controversy_cards[:2]))
    return "; ".join(summary) or "no auxiliary cards supplied"


__all__ = [
    "build_axes_stage_prompt",
    "run_axes_stage",
]
