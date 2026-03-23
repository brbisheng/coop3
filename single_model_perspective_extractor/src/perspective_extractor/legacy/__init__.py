"""Legacy perspective-extraction path kept only for compatibility."""

from .axes import generate_axes
from .expand import expand_axis
from .review import review_notes, review_records
from .synthesize import synthesize_map, synthesize_summary

__all__ = [
    "expand_axis",
    "generate_axes",
    "review_notes",
    "review_records",
    "synthesize_map",
    "synthesize_summary",
]
