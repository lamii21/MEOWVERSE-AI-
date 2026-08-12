import hashlib
import logging
import time
import uuid

from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from app.ml.embedding_model import get_embedding_model
from app.models.embedding import CatEmbeddingModel
from app.repositories import embedding_repository
from app.similarity.vector_index import get_vector_index

logger = logging.getLogger(__name__)


def hash_image_bytes(image_bytes: bytes) -> str:
    return hashlib.sha256(image_bytes).hexdigest()


async def embed_and_index(
    db: AsyncSession, analysis_id: uuid.UUID, image: Image.Image, image_bytes: bytes
) -> tuple[CatEmbeddingModel | None, float]:
    """Best-effort, same philosophy as image storage and analysis
    persistence (Phases 7/9): if the embedding model or vector index
    isn't available, this returns `(None, 0.0)` rather than raising —
    the analyze endpoint must never fail because visual similarity
    couldn't be computed.

    Returns `(row, latency_seconds)`. `latency_seconds` is 0.0 whenever
    no embedding was actually computed this call (dedup reuse or
    unavailability) — see `app/api/v1/similarity.py`/PROJECT_STATUS.md
    for how real embedding-generation latency is measured and reported
    honestly (never fabricated for a request that skipped inference).
    """
    model = get_embedding_model()
    index = get_vector_index()
    if not model.is_available or not index.is_available:
        return None, 0.0

    content_hash = hash_image_bytes(image_bytes)

    existing = await embedding_repository.get_by_content_hash(
        db, content_hash, model.name, model.version
    )
    if existing is not None:
        # Duplicate image content (Phase 11 spec §10): reuse the
        # existing FAISS vector rather than computing and indexing a
        # second, redundant one. Every analysis still gets its own row
        # (needed to answer "does *this* analysis have an embedding"),
        # they just point at the same vector_id.
        row = await embedding_repository.create(
            db,
            analysis_id=analysis_id,
            vector_id=existing.vector_id,
            content_hash=content_hash,
            embedding_model=model.name,
            embedding_version=model.version,
            embedding_dim=model.dimension,
        )
        return row, 0.0

    start = time.perf_counter()
    try:
        vector = model.predict(image)
    except Exception:
        logger.warning("Embedding generation failed — continuing without one", exc_info=True)
        return None, 0.0
    latency = time.perf_counter() - start

    vector_id = await embedding_repository.next_vector_id(db)
    try:
        index.add(vector_id, vector)
    except Exception:
        logger.warning("Vector index add failed — continuing without an embedding", exc_info=True)
        return None, latency

    row = await embedding_repository.create(
        db,
        analysis_id=analysis_id,
        vector_id=vector_id,
        content_hash=content_hash,
        embedding_model=model.name,
        embedding_version=model.version,
        embedding_dim=model.dimension,
    )
    return row, latency


async def remove_from_index(db: AsyncSession, analysis_id: uuid.UUID) -> None:
    """Reference-counted removal: only actually removes the FAISS
    vector once no other analysis (a duplicate-content upload) still
    references the same `vector_id` — otherwise a shared vector would
    be pulled out from under a still-existing cat. No caller exists yet
    (there's no "delete an analysis" feature — see PROJECT_STATUS.md),
    but the CLI's consistency tooling and any future deletion feature
    both need this to exist and be correct."""
    row = await embedding_repository.delete_by_analysis_id(db, analysis_id)
    if row is None:
        return
    remaining = await embedding_repository.count_rows_for_vector_id(db, row.vector_id)
    if remaining == 0:
        index = get_vector_index()
        if index.is_available:
            index.remove(row.vector_id)
