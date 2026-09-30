"""Select the configured extraction provider."""

from __future__ import annotations

import logging

from app.ai.base import LLMProvider, ProviderUnavailableError
from app.ai.providers.openai_provider import OpenAICompatibleProvider
from app.ai.providers.stub_provider import StubProvider
from app.core.config import settings

logger = logging.getLogger(__name__)

SUPPORTED_PROVIDERS = ("none", "stub", "openai")


def get_provider_name() -> str:
    """Configured provider id, lower-cased."""
    return (settings.llm_provider or "none").strip().lower()


def get_provider() -> LLMProvider:
    """Build the provider named by ``LLM_PROVIDER``.

    Raises :class:`ProviderUnavailableError` with an actionable message when the
    configuration is missing - the API surface turns that into a clear 503 rather
    than letting the caller fall back to invented data.
    """
    name = get_provider_name()

    if name in ("", "none", "disabled", "off"):
        raise ProviderUnavailableError(
            "AI extraction is disabled. Set LLM_PROVIDER=openai (with LLM_API_KEY/LLM_MODEL) "
            "or LLM_PROVIDER=stub for the offline deterministic extractor."
        )

    if name == "stub":
        return StubProvider()

    if name == "openai":
        return OpenAICompatibleProvider(
            api_key=settings.effective_llm_api_key,
            model=settings.llm_model,
            base_url=settings.llm_base_url,
            timeout_seconds=settings.llm_timeout_seconds,
            max_output_tokens=settings.llm_max_output_tokens,
        )

    raise ProviderUnavailableError(
        f"Unknown LLM_PROVIDER '{name}'. Supported values: {', '.join(SUPPORTED_PROVIDERS)}."
    )
