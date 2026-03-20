"""Prompt templates used by the perspective extractor."""

from __future__ import annotations

from typing import Literal

PromptVariant = Literal[
    "language_lens",
    "cultural_lens",
    "institutional_lens",
]

_RESERVED_PROMPT_VARIANTS: tuple[PromptVariant, ...] = (
    "language_lens",
    "cultural_lens",
    "institutional_lens",
)

EXTRACTION_PROMPT = """Extract perspectives about: {topic}

Source:
{source_text}"""

NORMALIZATION_PROMPT = """Normalize the user's raw research question into a structured QuestionCard.

Return JSON with the following keys:
- raw_question: the original question text
- cleaned_question: a concise, clearer research question
- actor_entity: the main actor, intervention, entity, or subject under study
- outcome_variable: the main outcome, dependent variable, or target phenomenon
- assumptions: explicit assumptions already embedded in the question
- domain_hint: short domain label such as economics, public health, climate, education, technology, or politics
- keywords: compact list of useful retrieval keywords
- missing_pieces: important missing scope details needed for rigorous research design

Guidelines:
- Clean whitespace, remove filler phrasing, and preserve the core intent.
- Rewrite the question so it is specific and research-oriented without answering it.
- Prefer short noun phrases for actor_entity and outcome_variable.
- List only assumptions that are actually implied by the wording.
- missing_pieces should focus on missing population, geography, timeframe, comparator, mechanism, or measurement details when relevant.

Raw question:
{question}
"""


def resolve_prompt_variant(
    *,
    prompt_variant: PromptVariant | None = None,
    lens: PromptVariant | None = None,
) -> PromptVariant | None:
    """Resolve the reserved prompt-configuration aliases used across the pipeline.

    v1 keeps all variants behaviorally identical, but the resolver centralizes the
    public API now so future lens-specific prompt changes will not require another
    round of pipeline signature updates.
    """

    if prompt_variant is not None and prompt_variant not in _RESERVED_PROMPT_VARIANTS:
        allowed = ", ".join(_RESERVED_PROMPT_VARIANTS)
        raise ValueError(f"Unsupported prompt_variant: {prompt_variant}. Expected one of: {allowed}")
    if lens is not None and lens not in _RESERVED_PROMPT_VARIANTS:
        allowed = ", ".join(_RESERVED_PROMPT_VARIANTS)
        raise ValueError(f"Unsupported lens: {lens}. Expected one of: {allowed}")
    if prompt_variant and lens and prompt_variant != lens:
        raise ValueError("prompt_variant and lens must match when both are provided")
    return prompt_variant or lens


def build_normalization_prompt(
    question: str,
    *,
    prompt_variant: PromptVariant | None = None,
    lens: PromptVariant | None = None,
) -> str:
    """Format the question-normalization prompt for a raw question.

    ``prompt_variant`` and ``lens`` are reserved extension points for future
    language/cultural/institutional prompt customization. They intentionally do
    not change the v1 prompt body yet.
    """

    resolve_prompt_variant(prompt_variant=prompt_variant, lens=lens)
    return NORMALIZATION_PROMPT.format(question=question)


__all__ = [
    "EXTRACTION_PROMPT",
    "NORMALIZATION_PROMPT",
    "PromptVariant",
    "build_normalization_prompt",
    "resolve_prompt_variant",
]
