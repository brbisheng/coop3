"""CLI entry point for the perspective extractor scaffold."""

from .models import PipelineInput
from .pipeline import PerspectiveExtractionPipeline


def main() -> None:
    """Run a small demo summary for local verification."""

    pipeline = PerspectiveExtractionPipeline()
    demo_input = PipelineInput(
        topic="example topic",
        source_text="Example source text for perspective extraction.",
    )
    print(pipeline.summarize(demo_input))


if __name__ == "__main__":
    main()
