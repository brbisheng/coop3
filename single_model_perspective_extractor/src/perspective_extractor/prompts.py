"""Prompt templates used by the perspective extractor."""

EXTRACTION_PROMPT = """Extract perspectives about: {topic}\n\nSource:\n{source_text}"""

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


def build_normalization_prompt(question: str) -> str:
    """Format the question-normalization prompt for a raw question."""

    return NORMALIZATION_PROMPT.format(question=question)
