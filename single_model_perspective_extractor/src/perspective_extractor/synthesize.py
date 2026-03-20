"""Synthesis stage for perspective extraction."""

from .models import PerspectiveRecord


def synthesize_summary(records: list[PerspectiveRecord]) -> str:
    """Create a newline-delimited summary for the current records."""

    return "\n".join(f"- {record.axis}: {record.summary}" for record in records)
