import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.embedding import CatEmbeddingModel


async def get_by_analysis_id(db: AsyncSession, analysis_id: uuid.UUID) -> CatEmbeddingModel | None:
    stmt = select(CatEmbeddingModel).where(CatEmbeddingModel.analysis_id == analysis_id)
    return (await db.execute(stmt)).scalar_one_or_none()


async def get_by_content_hash(
    db: AsyncSession, content_hash: str, embedding_model: str, embedding_version: str
) -> CatEmbeddingModel | None:
    """The duplicate-image dedup lookup (Phase 11 spec §10): finds any
    existing embedding for this exact image content, produced by the
    *current* model/version — an old row from a since-superseded model
    version deliberately doesn't count as a match, since its vector
    isn't comparable to what the current model would produce."""
    stmt = (
        select(CatEmbeddingModel)
        .where(
            CatEmbeddingModel.content_hash == content_hash,
            CatEmbeddingModel.embedding_model == embedding_model,
            CatEmbeddingModel.embedding_version == embedding_version,
        )
        .order_by(CatEmbeddingModel.created_at.asc())
        .limit(1)
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def create(
    db: AsyncSession,
    *,
    analysis_id: uuid.UUID,
    vector_id: int,
    content_hash: str,
    embedding_model: str,
    embedding_version: str,
    embedding_dim: int,
) -> CatEmbeddingModel:
    row = CatEmbeddingModel(
        analysis_id=analysis_id,
        vector_id=vector_id,
        content_hash=content_hash,
        embedding_model=embedding_model,
        embedding_version=embedding_version,
        embedding_dim=embedding_dim,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def get_by_vector_ids(db: AsyncSession, vector_ids: list[int]) -> list[CatEmbeddingModel]:
    """Reverse mapping used by `SimilarityService`: FAISS returns
    `vector_id`s, this resolves them back to the `analysis_id`(s) that
    reference each one — plural, deliberately, since duplicate-content
    images share one `vector_id` across multiple analysis rows."""
    if not vector_ids:
        return []
    stmt = select(CatEmbeddingModel).where(CatEmbeddingModel.vector_id.in_(vector_ids))
    return list((await db.execute(stmt)).scalars().all())


async def count_rows_for_vector_id(db: AsyncSession, vector_id: int) -> int:
    """How many analyses currently share `vector_id` (duplicate-content
    images) — used to decide whether removing one analysis's row may
    also safely remove the underlying FAISS vector (only when this
    reaches zero), so a shared vector is never pulled out from under a
    still-existing duplicate."""
    stmt = select(func.count()).where(CatEmbeddingModel.vector_id == vector_id)
    return (await db.execute(stmt)).scalar_one()


async def next_vector_id(db: AsyncSession) -> int:
    """A simple monotonic counter derived from the table itself rather
    than a DB sequence — correct here because FastAPI+asyncio runs this
    (synchronous, non-yielding) read-then-decide sequence without any
    concurrent request interleaving within a single process; see
    ARCHITECTURE.md §22 for the documented single-process-instance
    limitation this shares with the in-memory rate limiter."""
    stmt = select(func.max(CatEmbeddingModel.vector_id))
    current_max = (await db.execute(stmt)).scalar_one()
    return 0 if current_max is None else current_max + 1


async def list_all(db: AsyncSession) -> list[CatEmbeddingModel]:
    """Unfiltered — CLI/consistency-check use only, never a request
    handler (see `app/cli/similarity_index.py`)."""
    return list((await db.execute(select(CatEmbeddingModel))).scalars().all())


async def delete_by_analysis_id(
    db: AsyncSession, analysis_id: uuid.UUID
) -> CatEmbeddingModel | None:
    row = await get_by_analysis_id(db, analysis_id)
    if row is None:
        return None
    await db.delete(row)
    await db.commit()
    return row
