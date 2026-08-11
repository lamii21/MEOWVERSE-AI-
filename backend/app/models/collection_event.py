import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CollectionEventModel(Base):
    """An append-only log of XP-awarding gamification events (Phase 10
    spec §21-22): CAT_DISCOVERED, CAT_FAVORITED, STORY_GENERATED,
    CAT_SHARED, ACHIEVEMENT_UNLOCKED. This is the idempotency mechanism
    that makes XP un-farmable: the unique constraint on
    (user_id, event_type, target_id) means the same real-world moment
    (e.g. "this cat was favorited", "this cat's first story was
    generated") can only ever grant XP once, no matter how many times
    the underlying action is repeated client-side (toggling
    favorite/unfavorite, clicking Regenerate) — see
    app/services/gamification.py's `_grant`, which inserts with
    ON CONFLICT DO NOTHING and only awards XP when the insert actually
    happened.

    `target_id` is a string, not a UUID FK, because it names different
    kinds of things depending on `event_type` (an analysis id for most
    events, an achievement key for ACHIEVEMENT_UNLOCKED) — a real FK
    would only ever apply to some rows.
    """

    __tablename__ = "collection_events"
    __table_args__ = (
        UniqueConstraint("user_id", "event_type", "target_id", name="uq_collection_event"),
        Index("ix_collection_events_user_id_event_type", "user_id", "event_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    event_type: Mapped[str] = mapped_column(String(40))
    target_id: Mapped[str] = mapped_column(String(64))
    xp_awarded: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
