import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SessionModel(Base):
    """A DB-backed login session (Phase 9) — see ARCHITECTURE.md for why
    this project uses opaque session tokens in an httpOnly cookie rather
    than JWT. Only `token_hash` (SHA-256 of the raw token) is stored;
    the raw token itself only ever exists in the client's cookie and in
    memory for the single request that creates/verifies it, mirroring
    the same "never store the secret itself" principle as password
    hashing. Deleting a row is a real, immediate logout — unlike a
    stateless JWT, there is nothing left anywhere that would still
    validate.
    """

    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)  # sha256 hex

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
