from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "MeowVerse AI"
    environment: str = "development"
    debug: bool = True

    database_url: str = "postgresql+asyncpg://meowverse:meowverse@localhost:5433/meowverse"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = "change-me-in-.env"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7

    # Generative AI providers — absent keys mean the app falls back to
    # NullProvider implementations rather than failing.
    llm_provider: str = "anthropic"
    anthropic_api_key: str | None = None
    # Not a guess at "the current best model" — pinned to a specific,
    # known-real Anthropic model. Override via .env if you want a
    # different one; check https://docs.anthropic.com/en/docs/about-claude/models
    # for the current list before changing it.
    anthropic_model: str = "claude-sonnet-4-5-20250929"
    anthropic_max_output_tokens: int = 1024
    anthropic_timeout_seconds: float = 20.0
    openai_api_key: str | None = None

    image_generation_provider: str = "none"
    image_generation_api_key: str | None = None

    cors_origins: list[str] = ["http://localhost:3000"]

    max_upload_size_mb: int = 10

    # Applied to POST /api/v1/analyses (the only endpoint that can call
    # a paid external API) via app/core/rate_limit.py. In-memory,
    # per-process, per-client-IP — fine for a pre-auth single-instance
    # deployment; revisit with a shared store once Phase 9 adds auth.
    rate_limit_per_minute: int = 20

    # Breed classifier weights/class list. If either file is missing, the
    # pipeline runs in demo mode instead of failing — see app/ml/breed_classifier.py.
    breed_classifier_weights_path: str = "ml/models/breed_classifier.pt"
    breed_classifier_class_names_path: str = "ml/models/class_names.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()
