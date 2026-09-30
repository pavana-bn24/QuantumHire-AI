"""OpenAI-compatible chat-completions provider.

Works against OpenAI itself or any compatible gateway (Azure-style proxies,
local vLLM/Ollama gateways, etc.) purely through environment configuration.

The API key is injected at construction time from settings - it is never read
from, or written to, the source tree.
"""

from __future__ import annotations

import json
import logging
import re

import httpx
from pydantic import ValidationError

from app.ai.base import (
    ExtractionResult,
    InvalidProviderOutputError,
    LLMProvider,
    ProviderError,
    ProviderUnavailableError,
)
from app.ai.prompts import SYSTEM_PROMPT, build_user_prompt
from app.models.profile import CandidateProfile

logger = logging.getLogger(__name__)

_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.IGNORECASE)


class OpenAICompatibleProvider(LLMProvider):
    """Extract a structured profile using a chat-completions endpoint."""

    name = "openai"

    def __init__(
        self,
        *,
        api_key: str | None,
        model: str,
        base_url: str,
        timeout_seconds: float = 90.0,
        max_output_tokens: int = 4000,
    ) -> None:
        if not api_key:
            raise ProviderUnavailableError(
                "LLM_API_KEY is not set. Configure LLM_API_KEY (and LLM_PROVIDER=openai) "
                "to enable AI resume extraction."
            )
        if not model:
            raise ProviderUnavailableError("LLM_MODEL is not set.")

        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds
        self._max_output_tokens = max_output_tokens

    @property
    def model(self) -> str:
        return self._model

    def extract_profile(self, resume_text: str) -> ExtractionResult:
        """Call the model and validate the JSON it returns."""
        payload = {
            "model": self._model,
            "temperature": 0,
            "max_tokens": self._max_output_tokens,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(resume_text)},
            ],
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(
                    f"{self._base_url}/chat/completions", json=payload, headers=headers
                )
        except httpx.TimeoutException as exc:
            raise ProviderError(
                f"AI provider timed out after {self._timeout:.0f}s. Try again or reduce the "
                "resume length."
            ) from exc
        except httpx.HTTPError as exc:
            raise ProviderError(f"Could not reach the AI provider: {exc}") from exc

        if response.status_code == 401:
            raise ProviderUnavailableError(
                "AI provider rejected the credentials (401). Check LLM_API_KEY."
            )
        if response.status_code == 429:
            raise ProviderError("AI provider rate limit reached (429). Retry shortly.")
        if response.status_code >= 400:
            detail = response.text[:300]
            raise ProviderError(
                f"AI provider returned HTTP {response.status_code}: {detail}"
            )

        try:
            body = response.json()
            content = body["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise InvalidProviderOutputError(
                "AI provider returned an unexpected response shape."
            ) from exc

        return ExtractionResult(
            profile=self._parse_profile(content),
            provider=self.name,
            model=self._model,
            warnings=[],
        )

    @staticmethod
    def _parse_profile(content: str | None) -> CandidateProfile:
        """Parse and Pydantic-validate the model's JSON output."""
        if not content or not content.strip():
            raise InvalidProviderOutputError("AI provider returned an empty completion.")

        cleaned = _FENCE_RE.sub("", content.strip())

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise InvalidProviderOutputError(
                "AI provider did not return valid JSON, so the profile was rejected "
                "rather than guessed."
            ) from exc

        if not isinstance(parsed, dict):
            raise InvalidProviderOutputError("AI provider returned JSON that is not an object.")

        try:
            return CandidateProfile.model_validate(parsed)
        except ValidationError as exc:
            raise InvalidProviderOutputError(
                f"AI provider output failed schema validation: {exc.error_count()} issue(s)."
            ) from exc
