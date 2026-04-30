from __future__ import annotations

from dataclasses import dataclass
import json
import logging
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class AIProviderConfigurationError(RuntimeError):
    pass


class AIProviderResponseError(RuntimeError):
    pass


class AIProviderParseError(RuntimeError):
    pass


@dataclass(slots=True)
class AIConversationTurn:
    role: str
    content: str


@dataclass(slots=True)
class AIProviderResult:
    content: str
    provider: str
    model: str
    response_id: str | None = None


@dataclass(slots=True)
class AIProviderStructuredResult:
    data: dict[str, Any]
    provider: str
    model: str
    response_id: str | None = None


def _truncate_error_text(text: str, limit: int = 400) -> str:
    sanitized = " ".join(text.split())
    if len(sanitized) <= limit:
        return sanitized
    return f"{sanitized[:limit].rstrip()}..."


def _extract_response_text(payload: dict[str, Any]) -> str:
    output_items = payload.get("output", [])
    parts: list[str] = []

    for item in output_items:
        if item.get("type") != "message" or item.get("role") != "assistant":
            continue
        for content_item in item.get("content", []):
            if content_item.get("type") == "output_text" and content_item.get("text"):
                parts.append(content_item["text"].strip())

    if not parts and payload.get("output_text"):
        parts.append(str(payload["output_text"]).strip())

    response_text = "\n\n".join(part for part in parts if part)
    if not response_text:
        raise AIProviderResponseError("AI provider returned an empty response")
    return response_text


def _serialize_turn(turn: AIConversationTurn) -> dict[str, Any]:
    content_type = "output_text" if turn.role == "assistant" else "input_text"
    return {
        "role": turn.role,
        "content": [{"type": content_type, "text": turn.content}],
    }


def _build_response_input(conversation: list[AIConversationTurn]) -> list[dict[str, Any]]:
    if conversation:
        return [_serialize_turn(turn) for turn in conversation]
    return [
        {
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": "Generate the best response that follows the instructions exactly.",
                }
            ],
        }
    ]


async def generate_ai_reply(
    *,
    system_prompt: str,
    conversation: list[AIConversationTurn],
) -> AIProviderResult:
    provider_result = await _generate_response(
        system_prompt=system_prompt,
        conversation=conversation,
    )
    return AIProviderResult(
        content=_extract_response_text(provider_result),
        provider=get_settings().llm_provider.lower(),
        model=get_settings().llm_model,
        response_id=provider_result.get("id"),
    )


async def generate_structured_json(
    *,
    system_prompt: str,
    conversation: list[AIConversationTurn],
    schema_name: str,
    json_schema: dict[str, Any],
) -> AIProviderStructuredResult:
    provider_result = await _generate_response(
        system_prompt=system_prompt,
        conversation=conversation,
        text_format={
            "type": "json_schema",
            "name": schema_name,
            "strict": True,
            "schema": json_schema,
        },
    )
    response_text = _extract_response_text(provider_result)
    try:
        parsed_data = json.loads(response_text)
    except json.JSONDecodeError as exc:
        raise AIProviderParseError("AI provider returned invalid JSON") from exc

    settings = get_settings()
    return AIProviderStructuredResult(
        data=parsed_data,
        provider=settings.llm_provider.lower(),
        model=settings.llm_model,
        response_id=provider_result.get("id"),
    )


async def _generate_response(
    *,
    system_prompt: str,
    conversation: list[AIConversationTurn],
    text_format: dict[str, Any] | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    provider = settings.llm_provider.lower()

    if provider != "openai":
        raise AIProviderConfigurationError(f"Unsupported LLM provider: {settings.llm_provider}")
    if not settings.llm_api_key:
        raise AIProviderConfigurationError("AI provider is not configured")

    payload = {
        "model": settings.llm_model,
        "instructions": system_prompt,
        "input": _build_response_input(conversation),
    }
    if text_format is not None:
        payload["text"] = {"format": text_format}

    headers = {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
    }
    timeout = httpx.Timeout(settings.llm_timeout_seconds)
    base_url = settings.llm_base_url.rstrip("/") + "/"

    try:
        async with httpx.AsyncClient(base_url=base_url, timeout=timeout) as client:
            response = await client.post("responses", json=payload, headers=headers)
            response.raise_for_status()
    except httpx.TimeoutException as exc:
        raise AIProviderResponseError(
            f"AI provider request timed out after {settings.llm_timeout_seconds} seconds"
        ) from exc
    except httpx.HTTPStatusError as exc:
        response_text = _truncate_error_text(exc.response.text)
        logger.warning(
            "AI provider HTTP error",
            extra={
                "status_code": exc.response.status_code,
                "response_text": response_text,
                "model": settings.llm_model,
            },
        )
        raise AIProviderResponseError(
            f"AI provider request failed ({exc.response.status_code}): {response_text}"
        ) from exc
    except httpx.HTTPError as exc:
        raise AIProviderResponseError(f"AI provider request failed: {exc}") from exc

    return response.json()
