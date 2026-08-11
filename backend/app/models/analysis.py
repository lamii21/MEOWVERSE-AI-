import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, String, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CatAnalysisModel(Base):
    """Persisted result of a single analysis request: real CV signals
    (breed, colors) plus the AI-generated creative profile, denormalized
    into one row. `profile` (JSONB) remains the source of truth for the
    full `CatProfile`; `cat_name`/`rarity` are denormalized copies of
    `profile["name"]`/`profile["rarity"]` added in Phase 9 purely so the
    collection endpoint can filter/sort/search with plain indexed
    columns instead of JSONB predicates — they're written once at
    creation and never diverge from `profile` since a profile is never
    edited after generation.

    Splitting into separate cat_analyses/cat_profiles/analysis_results
    tables (the original aspirational schema in early ARCHITECTURE.md
    drafts) was deliberately *not* done in Phase 9 either — the
    single-table shape has been working, tested, and depended on by
    every service since Phase 6, and Phase 9's actual brief ("do not
    blindly create duplicate tables," "preserve existing data") argues
    against a risky full normalization for no functional gain right
    now. Revisit only if a real requirement needs it.

    `user_id` is nullable: an anonymous/guest analysis has no owner
    (created via the auth-optional POST /api/v1/analyses) until
    explicitly claimed via POST /api/v1/analyses/{id}/save — see
    ARCHITECTURE.md's ownership model. An authenticated request auto-owns
    its analysis immediately, no separate claim step needed.
    """

    __tablename__ = "cat_analyses"
    __table_args__ = (
        Index("ix_cat_analyses_user_id_created_at", "user_id", "created_at"),
        Index("ix_cat_analyses_user_id_rarity", "user_id", "rarity"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )

    breed_label: Mapped[str] = mapped_column(String(100))
    breed_confidence: Mapped[float] = mapped_column(Float)
    breed_mode: Mapped[str] = mapped_column(String(20))

    colors: Mapped[list[dict]] = mapped_column(JSONB)
    colors_mode: Mapped[str] = mapped_column(String(20))

    profile: Mapped[dict] = mapped_column(JSONB)
    profile_mode: Mapped[str] = mapped_column(String(20))

    # Denormalized from `profile` — see class docstring.
    cat_name: Mapped[str] = mapped_column(String(40))
    rarity: Mapped[str] = mapped_column(String(20))

    # Phase 9: the uploaded photo, persisted via ImageStorageProvider
    # (app/storage/) so it survives a page refresh / a later login —
    # None if storage failed (best-effort, same philosophy as the rest
    # of this row's persistence) or for rows created before Phase 9.
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    # Phase 8: backs the public /cat/[id] Cat Card share page, same
    # explicit-share-only pattern as stories.is_public (Phase 7).
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
