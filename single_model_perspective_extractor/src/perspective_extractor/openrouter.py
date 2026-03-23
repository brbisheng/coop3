"""OpenRouter chat completion helpers."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from urllib import error, request

from .llm import StagePrompt

OPENROUTER_CHAT_COMPLETIONS_URL = "https://openrouter.ai/api/v1/chat/completions"


class OpenRouterError(RuntimeError):
    """Raised when a live OpenRouter request fails."""


Message = Mapping[str, str]


def build_openrouter_stage_caller(
    *,
    api_key: str,
    model: str,
    temperature: float = 0.0,
    max_tokens: int = 2000,
):
    """Build a stage-level model caller backed by OpenRouter chat completions."""

    def _call(stage_prompt: StagePrompt) -> str:
        return call_openrouter(
            api_key=api_key,
            model=model,
            messages=[{"role": "user", "content": stage_prompt.prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )

    return _call


def call_openrouter(
    *,
    api_key: str,
    model: str,
    messages: Sequence[Message],
    temperature: float,
    max_tokens: int,
) -> str:
    """Execute one OpenRouter chat completion request and return the text content."""

    normalized_api_key = api_key.strip()
    normalized_model = model.strip()
    if not normalized_api_key:
        raise OpenRouterError("OpenRouter API key is required")
    if not normalized_model:
        raise OpenRouterError("OpenRouter model is required")
    if not messages:
        raise OpenRouterError("OpenRouter messages must not be empty")
    if max_tokens <= 0:
        raise OpenRouterError("OpenRouter max_tokens must be positive")

    payload = json.dumps(
        {
            "model": normalized_model,
            "messages": list(messages),
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
    ).encode("utf-8")
    http_request = request.Request(
        OPENROUTER_CHAT_COMPLETIONS_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {normalized_api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with request.urlopen(http_request) as response:
            response_body = response.read().decode("utf-8")
    except error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise OpenRouterError(
            f"OpenRouter request failed with status {exc.code}: {error_body}"
        ) from exc
    except error.URLError as exc:
        raise OpenRouterError(f"OpenRouter request failed: {exc.reason}") from exc

    try:
        parsed_response = json.loads(response_body)
    except json.JSONDecodeError as exc:
        raise OpenRouterError("OpenRouter returned invalid JSON") from exc

    try:
        content = parsed_response["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise OpenRouterError("OpenRouter response did not include a message content field") from exc

    if isinstance(content, str):
        normalized_content = content.strip()
    elif isinstance(content, list):
        normalized_content = "".join(
            part.get("text", "")
            for part in content
            if isinstance(part, dict)
        ).strip()
    else:
        raise OpenRouterError("OpenRouter response content had an unsupported shape")

    if not normalized_content:
        raise OpenRouterError("OpenRouter response content was empty")
    return normalized_content


__all__ = [
    "OPENROUTER_CHAT_COMPLETIONS_URL",
    "OpenRouterError",
    "build_openrouter_stage_caller",
    "call_openrouter",
]
