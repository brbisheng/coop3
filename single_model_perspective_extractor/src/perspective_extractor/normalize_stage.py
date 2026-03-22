"""Explicit normalize-stage prompt and demo fixture."""

from __future__ import annotations

import json

from .llm import StageModelCaller, StagePrompt, invoke_stage_prompt

_NORMALIZE_STAGE_PROMPT = """Normalize the research question below into one QuestionCard JSON object.

Return JSON with exactly these keys:
- raw_question
- cleaned_question
- actor_entity
- outcome_variable
- assumptions
- domain_hint
- keywords
- missing_pieces

Rules:
- Preserve the user's core question.
- Rewrite for clarity without answering it.
- Keep actor_entity and outcome_variable short and concrete.
- assumptions must only include assumptions already implied by the wording.
- missing_pieces should name missing scope details such as population, geography, timeframe, comparator, mechanism, or measurement.

Question:
{question}
"""


def build_normalize_stage_prompt(question: str) -> StagePrompt:
    """Return the full normalize-stage prompt and its fixed demo response."""

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
    return StagePrompt(
        stage_name="normalize",
        prompt=_NORMALIZE_STAGE_PROMPT.format(question=question),
        demo_response=json.dumps(demo_response, indent=2, ensure_ascii=False, sort_keys=True),
    )


def run_normalize_stage(
    question: str,
    *,
    call_model: StageModelCaller | None = None,
) -> str:
    """Run the normalize-stage prompt or return the fixed demo fixture."""

    return invoke_stage_prompt(
        build_normalize_stage_prompt(question),
        call_model=call_model,
    )


__all__ = [
    "build_normalize_stage_prompt",
    "run_normalize_stage",
]
