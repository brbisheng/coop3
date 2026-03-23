"""Minimal stage-level model invocation helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol


class ModelInvocationError(RuntimeError):
    """Raised when live model execution is misconfigured or returns invalid output."""


@dataclass(frozen=True, slots=True)
class StagePrompt:
    """One explicit model request for one stage."""

    stage_name: str
    prompt: str
    response_format: Literal["json", "text"] = "json"


class StageModelCaller(Protocol):
    """Callable interface for a live stage-specific model integration."""

    def __call__(self, stage_prompt: StagePrompt) -> str: ...


def invoke_stage_prompt(
    stage_prompt: StagePrompt,
    *,
    call_model: StageModelCaller | None = None,
) -> str:
    """Run one explicit stage prompt against a live model integration."""

    if call_model is None:
        raise ModelInvocationError(
            f"{stage_prompt.stage_name} requires an explicit live model caller"
        )

    response = call_model(stage_prompt)
    if not response.strip():
        raise ModelInvocationError(
            f"{stage_prompt.stage_name} returned an empty model response"
        )
    return response


__all__ = [
    "ModelInvocationError",
    "StageModelCaller",
    "StagePrompt",
    "invoke_stage_prompt",
]
