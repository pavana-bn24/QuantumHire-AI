"""AI provider abstraction: contracts shared by every extraction provider."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.models.profile import CandidateProfile


class ProviderError(RuntimeError):
    """Raised when a provider is reachable but the extraction call failed."""


class ProviderUnavailableError(ProviderError):
    """Raised when no usable provider is configured (missing key/model/etc.)."""


class InvalidProviderOutputError(ProviderError):
    """Raised when the provider responded, but not with a valid profile."""


@dataclass
class ExtractionResult:
    """Validated output of an extraction call."""

    profile: CandidateProfile
    provider: str
    model: str
    warnings: list[str] = field(default_factory=list)


class LLMProvider(ABC):
    """Interface every extraction provider must implement.

    Implementations receive the raw resume text and must return a
    :class:`CandidateProfile` containing **only** facts grounded in that text.
    """

    #: Short identifier recorded on the candidate document for traceability.
    name: str = "unknown"

    @property
    @abstractmethod
    def model(self) -> str:
        """Model identifier used for the call (recorded for traceability)."""

    @abstractmethod
    def extract_profile(self, resume_text: str) -> ExtractionResult:
        """Extract a structured profile from ``resume_text``.

        Implementations must raise :class:`ProviderError` (or a subclass) rather
        than returning partially invented data.
        """
