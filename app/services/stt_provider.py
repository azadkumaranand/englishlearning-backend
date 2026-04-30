from __future__ import annotations

from dataclasses import dataclass
import logging

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class STTProviderConfigurationError(RuntimeError):
    pass


class STTProviderResponseError(RuntimeError):
    pass


@dataclass(slots=True)
class STTTranscriptionResult:
    text: str
    provider: str
    model: str
    mime_type: str | None = None
    language: str | None = None
    duration_ms: int | None = None
    source: str | None = None
    file_name: str | None = None


def _truncate_error_text(text: str, limit: int = 400) -> str:
    sanitized = " ".join(text.split())
    if len(sanitized) <= limit:
        return sanitized
    return f"{sanitized[:limit].rstrip()}..."


def _is_usable_transcript(text: str) -> bool:
    normalized = " ".join(text.split())
    if not normalized:
        return False

    meaningful_char_count = sum(1 for char in normalized if char.isalnum())
    if meaningful_char_count < 2:
        return False

    return True


async def _request_transcription(
    *,
    base_url: str,
    timeout: httpx.Timeout,
    headers: dict[str, str],
    file_name: str,
    file_bytes: bytes,
    mime_type: str | None,
    model: str,
    language: str | None,
) -> dict:
    files = {
        "file": (file_name, file_bytes, mime_type or "application/octet-stream"),
    }
    data: dict[str, str] = {
        "model": model,
        "response_format": "json",
    }
    if language:
        data["language"] = language

    async with httpx.AsyncClient(base_url=base_url, timeout=timeout) as client:
        response = await client.post(
            "audio/transcriptions",
            headers=headers,
            files=files,
            data=data,
        )
        response.raise_for_status()
        return response.json()


async def transcribe_audio(
    *,
    file_bytes: bytes,
    file_name: str,
    mime_type: str | None,
    duration_ms: int | None = None,
    source: str | None = None,
    language_hint: str | None = None,
    use_default_language_hint: bool = True,
) -> STTTranscriptionResult:
    settings = get_settings()
    provider = settings.stt_provider.lower()

    if provider != "openai":
        raise STTProviderConfigurationError(f"Unsupported STT provider: {settings.stt_provider}")
    if not settings.stt_api_key:
        raise STTProviderConfigurationError("Speech-to-text provider is not configured")

    headers = {
        "Authorization": f"Bearer {settings.stt_api_key}",
    }
    timeout = httpx.Timeout(settings.stt_timeout_seconds)
    base_url = settings.stt_base_url.rstrip("/") + "/"
    selected_language_hint = language_hint.strip() if language_hint and language_hint.strip() else None
    if selected_language_hint is None and use_default_language_hint and settings.stt_language_hint:
        selected_language_hint = settings.stt_language_hint.strip() or None
    attempted_models: list[str] = []
    candidate_models = [settings.stt_model]
    if settings.stt_fallback_model and settings.stt_fallback_model != settings.stt_model:
        candidate_models.append(settings.stt_fallback_model)

    try:
        payload: dict | None = None
        selected_model: str | None = None

        for model in candidate_models:
            attempted_models.append(model)
            payload = await _request_transcription(
                base_url=base_url,
                timeout=timeout,
                headers=headers,
                file_name=file_name,
                file_bytes=file_bytes,
                mime_type=mime_type,
                model=model,
                language=selected_language_hint,
            )
            transcript = str(payload.get("text", "")).strip()
            if _is_usable_transcript(transcript):
                selected_model = model
                break
    except httpx.TimeoutException as exc:
        raise STTProviderResponseError(
            f"Speech transcription timed out after {settings.stt_timeout_seconds} seconds"
        ) from exc
    except httpx.HTTPStatusError as exc:
        response_text = _truncate_error_text(exc.response.text)
        logger.warning(
            "STT provider HTTP error",
            extra={
                "status_code": exc.response.status_code,
                "response_text": response_text,
                "model": settings.stt_model,
            },
        )
        raise STTProviderResponseError(
            f"Speech transcription failed ({exc.response.status_code}): {response_text}"
        ) from exc
    except httpx.HTTPError as exc:
        raise STTProviderResponseError(f"Speech transcription failed: {exc}") from exc

    if payload is None or selected_model is None:
        raise STTProviderResponseError(
            "Speech could not be transcribed clearly. Please speak for 2 to 5 seconds, pause briefly before talking, and keep the phone close to your mouth."
        )

    transcript = str(payload.get("text", "")).strip()
    if not _is_usable_transcript(transcript):
        raise STTProviderResponseError(
            "Speech could not be transcribed clearly. Please speak for 2 to 5 seconds, pause briefly before talking, and keep the phone close to your mouth."
        )

    return STTTranscriptionResult(
        text=transcript,
        provider=provider,
        model=selected_model,
        mime_type=mime_type,
        language=payload.get("language"),
        duration_ms=duration_ms,
        source=source,
        file_name=file_name,
    )
