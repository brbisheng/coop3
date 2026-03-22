"""Explicit axis-expansion stage prompt and demo fixture."""

from __future__ import annotations

import json
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
    """Return the explicit expand-stage prompt and a runnable demo fixture."""

    cards = list(context_cards or [])
    support_ids = [
        getattr(card, "knowledge_id", None)
        or getattr(card, "variable_id", None)
        or getattr(card, "controversy_id", None)
        for card in cards
    ]
    actor = question_card.actor_entity or "the focal actor"
    outcome = question_card.outcome_variable or "the focal outcome"

    demo_note = {
        "axis_id": axis_card.axis_id,
        "core_claim": (
            f"Demo fixture: inspect whether the {axis_card.name} axis changes how {actor} should be related to {outcome}."
        ),
        "reasoning": (
            f"This fixture keeps the {axis_card.axis_type} lens separate by focusing only on {axis_card.focus.rstrip('.')}. "
            "It is a runnable placeholder for stage wiring, not a claim that the axis is already resolved."
        ),
        "counterexample": (
            f"A nearby rival explanation could reproduce the same pattern without the {axis_card.name} lens doing the real work."
        ),
        "boundary_condition": "This note only applies if the prompt-specified scope and definitions are actually observed.",
        "evidence_needed": [
            f"Evidence that directly tests the {axis_card.name} axis.",
            f"Measures that distinguish {actor} from alternative explanations for {outcome}.",
        ],
        "testable_implication": (
            f"If the {axis_card.name} axis matters, changing the focal conditions should change the observed pattern in {outcome}."
        ),
        "verification_question": (
            f"What evidence would show that the {axis_card.name} axis adds explanatory value on its own?"
        ),
        "supporting_card_ids": [support_id for support_id in support_ids if support_id],
    }
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
        demo_response=json.dumps(demo_note, indent=2, ensure_ascii=False, sort_keys=True),
    )


def run_expand_stage(
    question_card: QuestionCard,
    axis_card: AxisCard,
    *,
    context_cards: Iterable[KnowledgeCard | VariableCard | ControversyCard] | None = None,
    call_model: StageModelCaller | None = None,
) -> str:
    """Run the expand-stage prompt or return the fixed demo fixture."""

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
