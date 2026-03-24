"""Top-level package for the perspective extractor scaffold."""

from .decompose import decompose_problem
from .evaluate import evaluate_phase1_artifacts
from .pipeline import PerspectiveExtractionPipeline, run_phase1_pipeline, run_pipeline

__all__ = [
    "PerspectiveExtractionPipeline",
    "decompose_problem",
    "evaluate_phase1_artifacts",
    "run_phase1_pipeline",
    "run_pipeline",
]
