"""Explicit axis-expansion stage prompt builder."""

from __future__ import annotations

from collections.abc import Iterable

from .llm import StageModelCaller, StagePrompt, invoke_stage_prompt
from .models import AxisCard, ControversyCard, KnowledgeCard, QuestionCard, VariableCard

_EXPAND_STAGE_PROMPT = """Expand one perspective axis into one inspectable note.

Question:
- {question}

Axis:
- id: {axis_id}
- name: {axis_name}
- type: {axis_type}
- focus: {axis_focus}
- distinctness: {axis_distinctness}

Context cards:
{context_block}

Return JSON with exactly these keys:
- axis_id
- core_claim
- reasoning
- counterexample
- boundary_condition
- evidence_needed
- testable_implication
- verification_question
- supporting_card_ids

Rules:
- Write one note for this axis only.
- Do not blend in other axes as if they are already solved.
- Keep the claim conditional and inspectable.
- Make the evidence list concrete enough to check.
"""


def build_expand_stage_prompt(
    question_card: QuestionCard,
    axis_card: AxisCard,
    *,
    context_cards: Iterable[KnowledgeCard | VariableCard | ControversyCard] | None = None,
) -> StagePrompt:
    """Return the explicit expand-stage prompt for a live model call."""

    cards = list(context_cards or [])
    return StagePrompt(
        stage_name="expand",
        prompt=_EXPAND_STAGE_PROMPT.format(
            question=question_card.cleaned_question,
            axis_id=axis_card.axis_id,
            axis_name=axis_card.name,
            axis_type=axis_card.axis_type,
            axis_focus=axis_card.focus,
            axis_distinctness=axis_card.how_is_it_distinct,
            context_block=_format_context_cards(cards),
        ),
    )


def run_expand_stage(
    question_card: QuestionCard,
    axis_card: AxisCard,
    *,
    context_cards: Iterable[KnowledgeCard | VariableCard | ControversyCard] | None = None,
    call_model: StageModelCaller | None = None,
) -> str:
    """Run the expand-stage prompt with an explicit live model caller."""

    return invoke_stage_prompt(
        build_expand_stage_prompt(
            question_card,
            axis_card,
            context_cards=context_cards,
        ),
        call_model=call_model,
    )


def _format_context_cards(
    context_cards: list[KnowledgeCard | VariableCard | ControversyCard],
) -> str:
    if not context_cards:
        return "- none"

    lines: list[str] = []
    for card in context_cards:
        card_id = (
            getattr(card, "knowledge_id", None)
            or getattr(card, "variable_id", None)
            or getattr(card, "controversy_id", None)
        )
        label = getattr(card, "title", None) or getattr(card, "name", None) or getattr(card, "question", None)
        lines.append(f"- {card_id}: {label}")
    return "\n".join(lines)


__all__ = [
    "build_expand_stage_prompt",
    "run_expand_stage",
]
