"""Explicit demo fixtures reserved for tests and manual demos."""

from __future__ import annotations

import json
from collections.abc import Iterable

from .models import AxisCard, ControversyCard, KnowledgeCard, QuestionCard, VariableCard


def build_normalize_stage_fixture(question: str) -> str:
    """Return the normalize-stage fixture payload for tests and demos."""

    cleaned_question = " ".join(question.split()) or "How does the focal actor affect the focal outcome?"
    demo_response = {
        "raw_question": question,
        "cleaned_question": cleaned_question,
        "actor_entity": "demo actor",
        "outcome_variable": "demo outcome",
        "assumptions": ["The wording implies a relationship worth testing."],
        "domain_hint": "demo domain",
        "keywords": ["demo actor", "demo outcome"],
        "missing_pieces": [
            "Target population is not specified.",
            "Time frame is not specified.",
            "Geographic scope is not specified.",
        ],
    }
    return json.dumps(demo_response, indent=2, ensure_ascii=False, sort_keys=True)


def build_axes_stage_fixture(
    question_card: QuestionCard,
    *,
    knowledge_cards: list[KnowledgeCard] | None = None,
    variable_cards: list[VariableCard] | None = None,
    controversy_cards: list[ControversyCard] | None = None,
) -> str:
    """Return the axes-stage fixture payload for tests and demos."""

    actor = question_card.actor_entity or "the focal actor"
    outcome = question_card.outcome_variable or "the focal outcome"
    domain = question_card.domain_hint or "general"
    demo_axes = {
        "axes": [
            {
                "name": "construct definition",
                "axis_type": "framing",
                "focus": f"Clarify how {actor} and {outcome} are defined before comparing explanations.",
                "how_is_it_distinct": "Separates category boundaries from causal or policy claims.",
            },
            {
                "name": "causal pathways",
                "axis_type": "mechanism",
                "focus": f"Trace the channels through which {actor} could shape {outcome}.",
                "how_is_it_distinct": "Focuses on process rather than only measurement or scope.",
            },
            {
                "name": "measurement strategy",
                "axis_type": "measurement",
                "focus": f"Compare how {actor} and {outcome} are operationalized in {domain}.",
                "how_is_it_distinct": "Centers indicators and validity rather than substantive interpretation.",
            },
            {
                "name": "scope conditions",
                "axis_type": "scope",
                "focus": f"Test whether claims about {actor} and {outcome} travel across settings.",
                "how_is_it_distinct": "Highlights where the claim stops generalizing.",
            },
            {
                "name": "temporal dynamics",
                "axis_type": "temporal",
                "focus": f"Distinguish short-run and long-run links between {actor} and {outcome}.",
                "how_is_it_distinct": "Organizes disagreement around timing and sequence.",
            },
            {
                "name": "decision levers",
                "axis_type": "decision",
                "focus": f"Examine which choices change exposure to {actor} in the {domain} domain.",
                "how_is_it_distinct": "Looks at controllable levers instead of only descriptive patterns.",
            },
            {
                "name": "distributional effects",
                "axis_type": "distributional",
                "focus": f"Compare which groups benefit or lose when {actor} changes {outcome}.",
                "how_is_it_distinct": "Moves from average effects to subgroup variation.",
            },
            {
                "name": "evidence quality",
                "axis_type": "evidence",
                "focus": f"Evaluate what evidence would be needed before inferring how {actor} affects {outcome}.",
                "how_is_it_distinct": "Treats inference quality as its own lens.",
            },
        ]
    }
    return json.dumps(demo_axes, indent=2, ensure_ascii=False, sort_keys=True)



def build_expand_stage_fixture(
    question_card: QuestionCard,
    axis_card: AxisCard,
    *,
    context_cards: Iterable[KnowledgeCard | VariableCard | ControversyCard] | None = None,
) -> str:
    """Return the expand-stage fixture payload for tests and demos."""

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
    return json.dumps(demo_note, indent=2, ensure_ascii=False, sort_keys=True)


__all__ = [
    "build_axes_stage_fixture",
    "build_expand_stage_fixture",
    "build_normalize_stage_fixture",
]
