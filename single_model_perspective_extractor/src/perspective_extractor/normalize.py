"""Normalization helpers for extracted perspective content."""


def normalize_text(text: str) -> str:
    """Normalize whitespace for downstream processing."""

    return " ".join(text.split())
