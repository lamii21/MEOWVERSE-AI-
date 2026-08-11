import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, String, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CatAnalysisModel(Base):
    """Persisted result of a single analysis request: real CV signals
    (breed, colors) plus the AI-generated creative profile, denormalized
    into one row for now. Splitting into separate cat_analyses/
    cat_profiles/analysis_results tables (per the original product spec)
    is deferred to Phase 9, which adds the full auth/persistence schema
    — this is a real, minimal, working subset built specifically so
    Phase 7's story feature has a stable `analysis_id` to reference, not
    a placeholder.

    No `user_id` yet — there's no auth (Phase 9). Analyses are anonymous
    for now; ownership/access-control is a Phase 9 concern.
    """

    __tablename__ = "cat_analyses"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    breed_label: Mapped[str] = mapped_column(String(100))
    breed_confidence: Mapped[float] = mapped_column(Float)
    breed_mode: Mapped[str] = mapped_column(String(20))

    colors: Mapped[list[dict]] = mapped_column(JSONB)
    colors_mode: Mapped[str] = mapped_column(String(20))

    profile: Mapped[dict] = mapped_column(JSONB)
    profile_mode: Mapped[str] = mapped_column(String(20))

    # Phase 8: backs the public /cat/[id] Cat Card share page, same
    # explicit-share-only pattern as stories.is_public (Phase 7).
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
