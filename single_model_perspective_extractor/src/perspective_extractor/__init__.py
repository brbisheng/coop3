"""Top-level package for the perspective extractor scaffold."""

from .decompose import decompose_problem
from .pipeline import PerspectiveExtractionPipeline, run_pipeline

__all__ = ["PerspectiveExtractionPipeline", "decompose_problem", "run_pipeline"]
