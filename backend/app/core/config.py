from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "MeowVerse AI"
    environment: str = "development"
    debug: bool = True

    database_url: str = "postgresql+asyncpg://meowverse:meowverse@localhost:5433/meowverse"
    redis_url: str = "redis://localhost:6379/0"

    # --- Auth (Phase 9) ---
    # DB-backed opaque session tokens in an httpOnly cookie, not JWT —
    # see ARCHITECTURE.md's auth section for the full rationale. Only
    # the *hash* of the token is stored server-side (same principle as
    # password hashing: a DB leak shouldn't hand over usable sessions).
    session_cookie_name: str = "meowverse_session"
    session_expire_days: int = 30
    # True in production (HTTPS-only cookie); false in local dev over
    # plain http://localhost. Distinct from `debug` on purpose — a
    # future prod deployment could conceivably want debug=false while
    # still being on http during a first manual smoke test.
    session_cookie_secure: bool = False

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
    # --- AI Cat Portrait Studio (Phase 14) ---
    # Pinned to a specific, real, current OpenAI image model that
    # supports image-conditioned edits (a reference photo + a prompt) —
    # not a guess. Override via .env if a different model is preferred;
    # check https://platform.openai.com/docs/models before changing it.
    image_generation_model: str = "gpt-image-1"
    image_generation_timeout_seconds: float = 60.0
    # Server-side ceilings (spec §25 "cost control") — never exposed as
    # raw provider parameters to the frontend, which only ever picks a
    # style + optional short customization string.
    portrait_output_size: str = "1024x1024"
    portrait_max_bytes: int = 15 * 1024 * 1024
    # Tighter than the general AI-endpoint limit (rate_limit_per_minute)
    # — a real image generation call is meaningfully more expensive than
    # a text completion. See app/core/rate_limit.py.
    portrait_generation_rate_limit_per_minute: int = 5

    cors_origins: list[str] = ["http://localhost:3000"]

    max_upload_size_mb: int = 10

    # Applied to POST /api/v1/analyses and the story endpoint (both can
    # call a paid external API) via app/core/rate_limit.py.
    rate_limit_per_minute: int = 20
    # Tighter limit for register/login specifically — brute-forcing
    # passwords or spamming account creation is a different threat
    # model than "don't hammer the AI endpoints." Per-IP, same as above.
    auth_rate_limit_per_minute: int = 10
    # In-memory, per-process, per-client-IP — fine for a single-instance
    # deployment. `app/core/rate_limit.py` is written behind a small
    # RateLimiter interface specifically so a Redis-backed
    # implementation can be swapped in later without touching call
    # sites, for when multi-instance deployment is on the table.
    rate_limit_backend: str = "memory"

    # Breed classifier weights/class list. If either file is missing, the
    # pipeline runs in demo mode instead of failing — see app/ml/breed_classifier.py.
    breed_classifier_weights_path: str = "ml/models/breed_classifier.pt"
    breed_classifier_class_names_path: str = "ml/models/class_names.json"

    # --- Image storage (Phase 9) ---
    # Behind ImageStorageProvider (app/storage/) so a future S3-compatible
    # backend is a drop-in swap — see app/storage/base.py.
    image_storage_provider: str = "local"
    image_storage_dir: str = "uploads"

    # --- Visual similarity (Phase 11) ---
    # Persisted FAISS index file — see app/similarity/vector_index.py.
    # Write-through (rewritten on every add/remove) so it always
    # survives a restart without needing a clean-shutdown hook.
    similarity_index_path: str = "data/similarity_index.faiss"
    # How many candidates to pull from FAISS before privacy filtering,
    # self-exclusion, and optional breed/rarity/favorite filters are
    # applied — must be > k so enough *eligible* results remain after
    # filtering. See app/services/similarity_service.py.
    similarity_candidate_oversample: int = 10
    similarity_max_k: int = 20


@lru_cache
def get_settings() -> Settings:
    return Settings()
