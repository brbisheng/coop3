"""Explicit normalize-stage prompt builder."""

from __future__ import annotations

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
    """Return the full normalize-stage prompt for a live model call."""

    return StagePrompt(
        stage_name="normalize",
        prompt=_NORMALIZE_STAGE_PROMPT.format(question=question),
    )


def run_normalize_stage(
    question: str,
    *,
    call_model: StageModelCaller | None = None,
) -> str:
    """Run the normalize-stage prompt with an explicit live model caller."""

    return invoke_stage_prompt(
        build_normalize_stage_prompt(question),
        call_model=call_model,
    )


__all__ = [
    "build_normalize_stage_prompt",
    "run_normalize_stage",
]
