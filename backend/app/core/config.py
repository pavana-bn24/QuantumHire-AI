"""Application configuration.

All settings are read from environment variables (or a local ``.env`` file),
so no secret or connection string is ever hardcoded in the source tree.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/core/config.py -> backend/
BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Typed application settings loaded from the environment."""

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application -------------------------------------------------------
    app_name: str = "QuantumHire AI API"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = False
    api_prefix: str = "/api"

    # --- MongoDB -----------------------------------------------------------
    mongodb_uri: str = "mongodb://127.0.0.1:27017"
    mongodb_db_name: str = "quantumhire"
    mongodb_server_selection_timeout_ms: int = 3000

    # --- CORS --------------------------------------------------------------
    cors_origins: str = "http://localhost:5000,http://127.0.0.1:5000"

    # --- Seeding -----------------------------------------------------------
    seed_on_startup: bool = True

    # --- Resume upload -----------------------------------------------------
    max_resume_size_mb: int = 10
    #: Minimum usable characters before a PDF is treated as scanned/image-only.
    resume_min_chars: int = 80
    allowed_resume_extension: str = ".pdf"

    # --- AI / LLM provider -------------------------------------------------
    #: "none" (no provider -> clear 503), "stub" (offline deterministic
    #: extractor) or "openai" (any OpenAI-compatible chat completions API).
    llm_provider: str = "stub"
    llm_api_key: str | None = None
    llm_model: str = "gpt-4o-mini"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_timeout_seconds: float = 90.0
    llm_max_output_tokens: int = 4000

    # --- Knowledge base (RAG) ----------------------------------------------
    #: Directory holding the markdown knowledge documents used for retrieval.
    knowledge_dir: str = str(BACKEND_DIR / "knowledge")
    #: How many chunks retrieval returns per query.
    knowledge_top_k: int = 4

    # --- Auth (JWT) --------------------------------------------------------
    jwt_secret: str = Field(
        default="",
        validation_alias=AliasChoices("JWT_SECRET", "SESSION_SECRET"),
    )
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 720
    #: Demo recruiter seeded on startup (kept in .env, never committed).
    seed_admin_email: str = ""
    seed_admin_password: str = ""

    # --- Integrations ------------------------------------------------------
    #: Outbound webhook target for workflow events; empty -> simulated delivery.
    external_webhook_url: str | None = None
    webhook_timeout_seconds: float = 10.0

    # --- Legacy / alias -----------------------------------------------------
    openai_api_key: str | None = None

    @property
    def cors_origin_list(self) -> list[str]:
        """CORS origins as a normalised list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def effective_llm_api_key(self) -> str | None:
        """``LLM_API_KEY`` with ``OPENAI_API_KEY`` as a backwards-compatible fallback."""
        return self.llm_api_key or self.openai_api_key or None

    @property
    def max_resume_size_bytes(self) -> int:
        """Upload ceiling in bytes."""
        return self.max_resume_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    """Return a cached ``Settings`` instance."""
    return Settings()


settings = get_settings()
