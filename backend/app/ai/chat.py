"""Generic JSON chat-completion helper built on the configured provider.

Used by AI evaluation and skill-test generation. Extraction keeps its own path
(``extract_profile``); this helper only runs when ``LLM_PROVIDER=openai`` -
the offline ``stub`` provider has deterministic builders in the services
themselves, so tests never need a key.
"""

from __future__ import annotations

import json
import logging
import re

import httpx
from pydantic import ValidationError

from app.ai.base import (
    InvalidProviderOutputError,
    ProviderError,
    ProviderUnavailableError,
)
from app.core.config import settings

logger = logging.getLogger(__name__)

_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.IGNORECASE)


def chat_json(system_prompt: str, user_prompt: str, *, purpose: str = "AI call") -> dict:
    """Call the OpenAI-compatible endpoint and return its JSON object.

    Raises :class:`ProviderUnavailableError` when no key/provider is configured
    and :class:`InvalidProviderOutputError` when the model replies with
    anything other than a JSON object - a bad reply is rejected, never guessed.
    """
    api_key = settings.effective_llm_api_key
    if not api_key:
        raise ProviderUnavailableError(
            "LLM_API_KEY is not set. Configure LLM_PROVIDER=openai with LLM_API_KEY "
            f"for {purpose}, or use LLM_PROVIDER=stub for offline deterministic output."
        )

    payload = {
        "model": settings.llm_model,
        "temperature": 0,
        "max_tokens": settings.llm_max_output_tokens,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        with httpx.Client(timeout=settings.llm_timeout_seconds) as client:
            response = client.post(
                f"{settings.llm_base_url.rstrip('/')}/chat/completions",
                json=payload,
                headers=headers,
            )
    except httpx.TimeoutException as exc:
        raise ProviderError(
            f"AI provider timed out after {settings.llm_timeout_seconds:.0f}s during {purpose}."
        ) from exc
    except httpx.HTTPError as exc:
        raise ProviderError(f"Could not reach the AI provider for {purpose}: {exc}") from exc

    if response.status_code == 401:
        raise ProviderUnavailableError(
            "AI provider rejected the credentials (401). Check LLM_API_KEY."
        )
    if response.status_code == 429:
        raise ProviderError(f"AI provider rate limit reached (429) during {purpose}. Retry shortly.")
    if response.status_code >= 400:
        raise ProviderError(
            f"AI provider returned HTTP {response.status_code} during {purpose}: "
            f"{response.text[:300]}"
        )

    try:
        body = response.json()
        content = body["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise InvalidProviderOutputError("AI provider returned an unexpected response shape.") from exc

    if not content or not content.strip():
        raise InvalidProviderOutputError("AI provider returned an empty completion.")

    cleaned = _FENCE_RE.sub("", content.strip())
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise InvalidProviderOutputError(
            f"{purpose}: AI provider did not return valid JSON, so the response was rejected."
        ) from exc

    if not isinstance(parsed, dict):
        raise InvalidProviderOutputError(f"{purpose}: AI provider returned JSON that is not an object.")

    return parsed


def validate_structured(model_cls, data: dict, *, purpose: str):
    """Validate a parsed payload against a Pydantic model, mapping failures."""
    try:
        return model_cls.model_validate(data)
    except ValidationError as exc:
        raise InvalidProviderOutputError(
            f"{purpose}: AI output failed schema validation ({exc.error_count()} issue(s))."
        ) from exc
