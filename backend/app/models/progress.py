import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserProgressModel(Base):
    """One row per user, keyed directly on `user_id` (no surrogate id —
    this is a genuine 1:1). `xp` is the single source of truth for
    level: level is *derived* from xp on every read (see
    app/services/gamification.py's `level_for_xp`) rather than stored
    redundantly, so the two can never drift apart.

    All XP changes happen server-side only, via
    `app/services/gamification.py`'s idempotent event recording — never
    accept an XP value from the client (Phase 10 spec §15).
    """

    __tablename__ = "user_progress"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    xp: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
