"""Knowledge access hooks for the perspective extractor."""


def collect_background(topic: str) -> list[str]:
    """Return placeholder background items for a topic."""

    return [f"background:{topic}"]
