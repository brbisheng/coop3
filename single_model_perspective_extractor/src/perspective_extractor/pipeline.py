"""End-to-end pipeline orchestration."""

from .axes import derive_axes
from .expand import expand_candidates
from .knowledge import collect_background
from .models import PerspectiveRecord, PipelineInput
from .normalize import normalize_text
from .review import review_records
from .synthesize import synthesize_summary


class PerspectiveExtractionPipeline:
    """Minimal orchestrator for the perspective extractor scaffold."""

    def run(self, pipeline_input: PipelineInput) -> list[PerspectiveRecord]:
        topic = normalize_text(pipeline_input.topic)
        source_text = normalize_text(pipeline_input.source_text)
        background = collect_background(topic)
        axes = derive_axes(topic)
        records = [
            PerspectiveRecord(
                axis=axis,
                summary=f"Perspective on {axis} from {len(background)} knowledge item(s)",
                evidence=[source_text] if source_text else [],
            )
            for axis in axes
        ]
        return review_records(expand_candidates(records))

    def summarize(self, pipeline_input: PipelineInput) -> str:
        return synthesize_summary(self.run(pipeline_input))
