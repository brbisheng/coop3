"""Shared data models for the perspective extractor pipeline."""

from dataclasses import dataclass, field


@dataclass(slots=True)
class PerspectiveRecord:
    """A minimal representation of an extracted perspective."""

    axis: str
    summary: str
    evidence: list[str] = field(default_factory=list)


@dataclass(slots=True)
class PipelineInput:
    """User input for a pipeline run."""

    topic: str
    source_text: str
