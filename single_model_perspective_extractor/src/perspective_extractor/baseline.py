"""Minimal single-shot baseline path for direct model analysis."""

from __future__ import annotations

from .openrouter import call_openrouter


def build_baseline_prompt(question: str) -> str:
    """Build a single direct-analysis prompt without phase-1 decomposition."""

    cleaned_question = question.strip()
    if not cleaned_question:
        raise ValueError("question must not be empty")

    return (
        "You are the baseline path for a reasoning quality comparison.\\n"
        "Provide one straightforward analysis answer in markdown, without JSON schema.\\n"
        "Keep it concise but concrete, and explain your logic in a normal analyst style.\\n"
        "Do not mention internal chain-of-thought or hidden reasoning.\\n\\n"
        f"Question:\\n{cleaned_question}"
    )


def run_baseline_analysis(question: str, *, model: str, api_key: str) -> str:
    """Run one direct OpenRouter completion and return markdown text."""

    response_text = call_openrouter(
        api_key=api_key,
        model=model,
        messages=[
            {
                "role": "system",
                "content": "Return a direct, practical markdown analysis answer.",
            },
            {
                "role": "user",
                "content": build_baseline_prompt(question),
            },
        ],
        temperature=0.0,
        max_tokens=1800,
    )
    return response_text.strip()


__all__ = ["build_baseline_prompt", "run_baseline_analysis"]
