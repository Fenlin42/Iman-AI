"""Anthropic API access. MOCK_AI=1 swaps in canned content for tests."""
import asyncio
import json
from typing import AsyncIterator

import anthropic

from . import config, mock

# Models that support server-side refusal fallbacks.
_FALLBACK_MODELS = {"claude-fable-5-2", "claude-fable-5-1", "claude-opus-5-5", "claude-opus-5", "claude-sonnet-5-5"}
_FALLBACK_BETA = "server-side-fallback-2026-07-01"

_client: anthropic.AsyncAnthropic | None = None


class AIError(Exception):
    """An error with a message that can be shown to the user."""


def client() -> anthropic.AsyncAnthropic:
    global _client
    if not config.has_api_key():
        raise AIError("Kein ANTHROPIC_API_KEY gesetzt. Trage ihn in der .env-Datei ein und starte die App neu.")
    if _client is None:
        _client = anthropic.AsyncAnthropic()
    return _client


def _request(system: str | list, user: str, max_tokens: int, effort: str, schema: dict | None = None) -> dict:
    output_config: dict = {"effort": effort}
    if schema:
        output_config["format"] = {"type": "json_schema", "schema": schema}
    req = dict(
        model=config.MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
        output_config=output_config,
    )
    if config.MODEL in _FALLBACK_MODELS:
        req.update(betas=[_FALLBACK_BETA], fallbacks="default")
    return req


def _translate(e: Exception) -> AIError:
    if isinstance(e, AIError):
        return e
    if isinstance(e, anthropic.AuthenticationError):
        return AIError("Der ANTHROPIC_API_KEY wurde abgelehnt. Bitte den Key in der .env pruefen.")
    if isinstance(e, anthropic.PermissionDeniedError):
        return AIError(f"Der API-Key hat keinen Zugriff auf das Modell {config.MODEL}.")
    if isinstance(e, anthropic.NotFoundError):
        return AIError(f"Modell {config.MODEL} nicht gefunden. Bitte ANTHROPIC_MODEL pruefen.")
    if isinstance(e, anthropic.RateLimitError):
        return AIError("Rate-Limit der Anthropic API erreicht. Bitte in einer Minute erneut versuchen.")
    if isinstance(e, anthropic.BadRequestError):
        return AIError(f"Die Anthropic API hat die Anfrage abgelehnt: {e.message}")
    if isinstance(e, anthropic.APIStatusError):
        return AIError(f"Fehler der Anthropic API ({e.status_code}). Bitte erneut versuchen.")
    if isinstance(e, anthropic.APIConnectionError):
        return AIError("Keine Verbindung zur Anthropic API. Bitte Internetverbindung pruefen.")
    return AIError(f"Unerwarteter Fehler: {e}")


def _check_stop(message) -> None:
    if message.stop_reason == "refusal":
        raise AIError("Das Modell hat diese Anfrage abgelehnt. Bitte das Thema anders formulieren.")
    if message.stop_reason == "max_tokens":
        raise AIError("Die Antwort war zu lang und wurde abgeschnitten. Bitte erneut versuchen.")


async def structured(kind: str, system: str, user: str, schema: dict) -> dict:
    """One structured call; returns the parsed JSON object."""
    if config.MOCK_AI:
        await asyncio.sleep(0.05)
        return mock.structured(kind)
    try:
        async with client().beta.messages.stream(**_request(system, user, 16000, "medium", schema)) as stream:
            message = await stream.get_final_message()
        _check_stop(message)
        text = next(b.text for b in message.content if b.type == "text")
        return json.loads(text)
    except Exception as e:  # noqa: BLE001 - translated into a user-facing message
        raise _translate(e) from e


async def write(context: str, system: str, user: str) -> AsyncIterator[str]:
    """Stream long-form Markdown. `context` is identical for every part of a product, so it is cached."""
    if config.MOCK_AI:
        async for chunk in mock.write(user):
            yield chunk
        return
    system_blocks = [
        {"type": "text", "text": system},
        {"type": "text", "text": context, "cache_control": {"type": "ephemeral"}},
    ]
    try:
        async with client().beta.messages.stream(**_request(system_blocks, user, 32000, "high")) as stream:
            async for text in stream.text_stream:
                yield text
            message = await stream.get_final_message()
        _check_stop(message)
    except Exception as e:  # noqa: BLE001
        raise _translate(e) from e
