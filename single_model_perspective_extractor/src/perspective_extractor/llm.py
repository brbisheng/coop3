"""Minimal stage-level model invocation helpers.

This module intentionally does *not* provide a broad client abstraction. Each
stage owns its own prompt text and demo fixture. The only shared helper here is
the tiny call boundary that either invokes a supplied model function or returns
the stage's explicit demo response.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol


@dataclass(frozen=True, slots=True)
class StagePrompt:
    """One explicit model request for one stage."""

    stage_name: str
    prompt: str
    demo_response: str
    response_format: Literal["json", "text"] = "json"


class StageModelCaller(Protocol):
    """Callable interface for a live stage-specific model integration."""

    def __call__(self, stage_prompt: StagePrompt) -> str: ...


def invoke_stage_prompt(
    stage_prompt: StagePrompt,
    *,
    call_model: StageModelCaller | None = None,
) -> str:
    """Run one explicit stage prompt or return its fixed demo response."""

    if call_model is None:
        return stage_prompt.demo_response

    response = call_model(stage_prompt)
    if not response.strip():
        raise ValueError(f"{stage_prompt.stage_name} returned an empty model response")
    return response


__all__ = [
    "StageModelCaller",
    "StagePrompt",
    "invoke_stage_prompt",
]
