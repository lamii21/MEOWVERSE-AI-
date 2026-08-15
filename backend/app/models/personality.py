import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CatPersonalityModel(Base):
    """The deterministic structured half of a Phase 13 personality —
    trait scores and the selected archetype. Unique on
    `(analysis_id, personality_engine_version)`: this IS the caching
    contract (spec §20) — a second request for the same analysis under
    the same engine version reuses this row; a bumped
    `PERSONALITY_ENGINE_VERSION` (a real scoring-rule change) simply
    won't match any existing row, so a fresh, correctly-versioned one
    gets computed automatically. No explicit "invalidate the old ones"
    step needed, same self-resolving-staleness pattern as Phase 11's
    embedding versioning and Phase 12's explanation caching.

    `traits` (JSONB) stores the full
    `{trait: {score, level, label, description}}` dict computed by
    `app/services/personality_scoring.py` — cheap to compute, but
    storing it means a page load never re-runs the scoring engine
    just to re-render the same numbers.
    """

    __tablename__ = "cat_personalities"
    __table_args__ = (
        UniqueConstraint(
            "analysis_id", "personality_engine_version", name="uq_cat_personality_cache_key"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("cat_analyses.id", ondelete="CASCADE"), index=True
    )
    personality_engine_version: Mapped[str] = mapped_column(String(20))
    archetype_id: Mapped[str] = mapped_column(String(40))
    traits: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class CatPersonalityInterpretationModel(Base):
    """The creative (LLM or demo-fallback) half — deliberately
    *separate* from `CatPersonalityModel` and deliberately allows
    multiple rows per `personality_id` (no unique constraint), the
    exact same "regenerate inserts a new row, `get_latest` returns the
    most recent" pattern `StoryModel` already established (Phase 7) —
    regenerating the creative text must never touch, and can never
    touch, the structured scores it points at (spec §14/§20: "if only
    the creative text changes, numeric personality scores should
    remain identical").
    """

    __tablename__ = "personality_interpretations"
    __table_args__ = (
        Index("ix_personality_interpretations_personality_id", "personality_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    personality_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("cat_personalities.id", ondelete="CASCADE"), index=True
    )
    interpretation_mode: Mapped[str] = mapped_column(String(20))  # "generated" | "demo"
    interpretation_model: Mapped[str | None] = mapped_column(String(30), nullable=True)
    interpretation_version: Mapped[str] = mapped_column(String(20))

    headline: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(String(400))
    catchphrase: Mapped[str] = mapped_column(String(140))
    secret_talent: Mapped[str] = mapped_column(String(140))
    fictional_job: Mapped[str] = mapped_column(String(100))
    fun_fact: Mapped[str] = mapped_column(String(200))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
