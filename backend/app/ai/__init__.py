"""Provider factory + package exports.

The provider is selected purely through environment configuration:

    LLM_PROVIDER=none | stub | openai
    LLM_API_KEY=...        (never committed, never hardcoded)
    LLM_MODEL=...
    LLM_BASE_URL=...       (any OpenAI-compatible endpoint)
"""

from app.ai.base import (
    ExtractionResult,
    InvalidProviderOutputError,
    LLMProvider,
    ProviderError,
    ProviderUnavailableError,
)
from app.ai.factory import get_provider, get_provider_name

__all__ = [
    "ExtractionResult",
    "InvalidProviderOutputError",
    "LLMProvider",
    "ProviderError",
    "ProviderUnavailableError",
    "get_provider",
    "get_provider_name",
]
