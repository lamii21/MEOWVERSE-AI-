import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CatPortraitModel(Base):
    """One AI-generated (or attempted) cat portrait (Phase 14). Multiple
    rows can exist per `analysis_id` — a cat can have many portraits
    across different styles, and "Generate Again" (spec §23) creates a
    new row rather than overwriting a previous one. `status` covers the
    full lifecycle so a failed attempt is still a real, persisted,
    honest record rather than silently discarded (spec §47:
    "failed generation persistence").

    `user_id` is a denormalized copy of the parent analysis's owner
    (same pattern as `CatAnalysisModel.cat_name`/`rarity`, Phase 9) —
    written once at creation, purely so achievement/stats queries can
    filter on `cat_portraits.user_id` directly instead of joining
    through `cat_analyses` every time.

    No hard unique constraint on `(analysis_id, style_id, ...)`:
    duplicate-generation avoidance (spec §23) is a soft, service-layer
    lookup (`portrait_repository.find_reusable`) keyed on
    `generation_identity_hash`, not a DB constraint — because an
    explicit "Generate Again" must be allowed to create a genuine
    duplicate on purpose. The index below makes that lookup cheap.
    """

    __tablename__ = "cat_portraits"
    __table_args__ = (
        Index("ix_cat_portraits_analysis_id_created_at", "analysis_id", "created_at"),
        Index(
            "ix_cat_portraits_identity_hash",
            "analysis_id",
            "generation_identity_hash",
            "status",
        ),
        Index("ix_cat_portraits_user_id", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("cat_analyses.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )

    style_id: Mapped[str] = mapped_column(String(30))
    customization: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # sha256 of (analysis_id, style_id, prompt_version, customization,
    # provider, model) — the full "duplicate generation" identity (spec
    # §23). Two requests that would produce the identical prompt against
    # the identical provider/model hash to the same value.
    generation_identity_hash: Mapped[str] = mapped_column(String(64), index=True)

    provider: Mapped[str] = mapped_column(String(30))  # "openai" | "demo"
    model: Mapped[str | None] = mapped_column(String(60), nullable=True)
    prompt_version: Mapped[str] = mapped_column(String(20))

    status: Mapped[str] = mapped_column(String(20))  # "pending" | "succeeded" | "failed"
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(300), nullable=True)

    is_public: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
