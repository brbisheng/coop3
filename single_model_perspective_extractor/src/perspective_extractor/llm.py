"""LLM abstractions for the perspective extractor."""

from .prompts import EXTRACTION_PROMPT


class LLMClient:
    """Placeholder LLM client for future integration."""

    def build_prompt(self, topic: str, source_text: str) -> str:
        return EXTRACTION_PROMPT.format(topic=topic, source_text=source_text)
