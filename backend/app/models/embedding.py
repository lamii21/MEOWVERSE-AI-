import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CatEmbeddingModel(Base):
    """Maps one `cat_analyses` row to its FAISS vector — deliberately
    NOT the vector's 576 floats themselves (Phase 11 spec §33: "do not
    dump large vectors into PostgreSQL without considering storage
    implications"). The actual vector lives only in the FAISS index
    file (`app/similarity/vector_index.py`); this table is the
    small, cheap, queryable metadata Postgres is good at: which
    analysis has an embedding, which FAISS `vector_id` it maps to, and
    which model/version produced it.

    `vector_id` is intentionally NOT unique — see `content_hash` below,
    duplicate-content analyses share one underlying vector.

    `content_hash` (sha256 of the raw uploaded image bytes) is how
    duplicate images are detected before ever calling the embedding
    model again (Phase 11 spec §10): analyzing the exact same photo
    twice reuses the first analysis's `vector_id` instead of adding a
    second, redundant vector to the index. Indexed for that lookup.

    `embedding_model`/`embedding_version`/`embedding_dim` are recorded
    per-row, not assumed globally constant, specifically so a future
    model upgrade (Phase 11 spec §34-35: "embedding model v1 → v2")
    can tell old vectors apart from new ones without guessing — the
    `similarity_index verify` CLI command flags any row whose
    model/version doesn't match the currently-configured one.
    """

    __tablename__ = "cat_embeddings"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("cat_analyses.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    vector_id: Mapped[int] = mapped_column(BigInteger, index=True)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    embedding_model: Mapped[str] = mapped_column(String(50))
    embedding_version: Mapped[str] = mapped_column(String(20))
    embedding_dim: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
