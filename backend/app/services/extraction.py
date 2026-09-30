"""Resume -> structured profile orchestration.

Keeps the provider contract out of the HTTP layer and maps provider failures to
two distinct, recruiter-readable outcomes:

* :class:`ExtractionUnavailableError` - no usable provider configured (HTTP 503).
* :class:`ExtractionFailedError`      - provider reachable but the call failed,
  timed out or returned something that failed schema validation (HTTP 502).

In both cases the upload is rejected: we never persist an invented profile.
"""

from __future__ import annotations

import logging

from app.ai.base import (
    ExtractionResult,
    InvalidProviderOutputError,
    ProviderError,
    ProviderUnavailableError,
)
from app.ai.factory import get_provider

logger = logging.getLogger(__name__)


class ExtractionUnavailableError(Exception):
    """No AI provider is available for extraction."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ExtractionFailedError(Exception):
    """The AI provider was available but could not produce a valid profile."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def extract_candidate_profile(resume_text: str) -> ExtractionResult:
    """Run the configured provider over ``resume_text``.

    Raises :class:`ExtractionUnavailableError` or :class:`ExtractionFailedError`
    with a message safe to show to a recruiter.
    """
    try:
        provider = get_provider()
    except ProviderUnavailableError as exc:
        raise ExtractionUnavailableError(str(exc)) from exc

    try:
        result = provider.extract_profile(resume_text)
    except ProviderUnavailableError as exc:
        raise ExtractionUnavailableError(str(exc)) from exc
    except InvalidProviderOutputError as exc:
        logger.warning("Provider %s returned invalid output: %s", provider.name, exc)
        raise ExtractionFailedError(
            f"The AI provider ({provider.name}/{provider.model}) returned output that failed "
            f"schema validation, so it was rejected rather than saved: {exc}"
        ) from exc
    except ProviderError as exc:
        logger.warning("Provider %s failed: %s", provider.name, exc)
        raise ExtractionFailedError(
            f"AI extraction failed via {provider.name}/{provider.model}: {exc}"
        ) from exc

    logger.info(
        "Extracted profile via %s/%s (%s warning(s))",
        result.provider,
        result.model,
        len(result.warnings),
    )
    return result
