import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserAchievementModel(Base):
    """An unlocked achievement for a user (Phase 9). Achievement
    *definitions* (key, label, emoji, unlock criteria) are static and
    code-defined in `app/services/achievements.py` — same pattern as
    `STORY_STYLE_LABELS` — rather than a second DB table, since they
    never change per-request. Only the unlock *event* is persisted.
    """

    __tablename__ = "user_achievements"
    __table_args__ = (UniqueConstraint("user_id", "achievement_key", name="uq_user_achievement"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    achievement_key: Mapped[str] = mapped_column(String(50))
    unlocked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
