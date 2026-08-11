import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class StoryModel(Base):
    """A generated (or demo-fallback) story for one analysis. Multiple
    rows can exist per (analysis_id, style) — regeneration inserts a new
    row rather than overwriting, so history is preserved; the service
    layer decides which one is "current" (the latest by created_at).

    `is_public` defaults to False — sharing a story (Phase 7 §17
    architecture prep only, no UI to flip this yet) must always be an
    explicit act, never automatic.
    """

    __tablename__ = "stories"
    __table_args__ = (Index("ix_stories_analysis_id_style", "analysis_id", "style"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("cat_analyses.id", ondelete="CASCADE"), index=True
    )

    style: Mapped[str] = mapped_column(String(30))
    title: Mapped[str] = mapped_column(String(200))
    story: Mapped[dict] = mapped_column(JSONB)  # full CatStory, model_dump()'d

    story_mode: Mapped[str] = mapped_column(String(20))  # "demo" | "generated"
    provider: Mapped[str] = mapped_column(String(30))  # "anthropic" | "demo"
    model: Mapped[str | None] = mapped_column(String(60), nullable=True)

    is_public: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
