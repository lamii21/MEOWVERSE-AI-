import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.ml.embedding_model import get_embedding_model
from app.models.analysis import CatAnalysisModel
from app.repositories import embedding_repository
from app.repositories.analysis_repository import (
    get_many_by_ids,
    get_owned_analysis,
    get_public_analysis,
)
from app.schemas.analysis import BreedPrediction
from app.schemas.similarity import SimilarCat, SimilarityResponse, SourceCatSummary
from app.similarity.vector_index import get_vector_index

_UNAVAILABLE = SimilarityResponse(
    source_cat=SourceCatSummary(analysis_id=uuid.UUID(int=0), cat_name="", image_url=None),
    similar_cats=[],
    search_mode="unavailable",
    embedding_model=None,
)


class SourceCatNotVisibleError(Exception):
    """The source analysis doesn't exist, or isn't visible to this
    caller (not public, and not owned by them) — surfaced by the API
    layer as 404, never a 500, and never distinguishing "doesn't exist"
    from "exists but isn't yours" (same anti-enumeration principle as
    every other ownership check in this codebase)."""


def _is_eligible(row: CatAnalysisModel, viewer_user_id: uuid.UUID | None) -> bool:
    """Phase 11 spec §8's privacy policy, stated once, in one place:
    a candidate is searchable by this caller if it's public, OR the
    caller is authenticated and owns it. A guest (`viewer_user_id is
    None`) can only ever see public cats — there's no "OR" clause for
    them at all."""
    if row.is_public:
        return True
    return viewer_user_id is not None and row.user_id == viewer_user_id


def _shared_colors(source: CatAnalysisModel, candidate: CatAnalysisModel) -> list[str]:
    source_names = {c["name"] for c in source.colors}
    candidate_names = {c["name"] for c in candidate.colors}
    return sorted(source_names & candidate_names)


def _to_similar_cat(
    row: CatAnalysisModel, score: float, source: CatAnalysisModel, viewer_user_id: uuid.UUID | None
) -> SimilarCat:
    viewer_owns_this_row = viewer_user_id is not None and row.user_id == viewer_user_id
    return SimilarCat(
        analysis_id=row.id,
        cat_name=row.cat_name,
        image_url=row.image_url,
        breed=BreedPrediction(label=row.breed_label, confidence=row.breed_confidence),
        rarity=row.rarity,
        visual_similarity=max(0.0, min(1.0, score)),
        shared_colors=_shared_colors(source, row),
        is_favorite=row.is_favorite if viewer_owns_this_row else False,
        created_at=row.created_at,
    )


async def find_similar_cats(
    db: AsyncSession,
    analysis_id: uuid.UUID,
    *,
    viewer_user_id: uuid.UUID | None,
    k: int = 5,
    breed: str | None = None,
    rarity: str | None = None,
    favorites_only: bool = False,
) -> SimilarityResponse:
    """The single place similarity search logic lives (Phase 11 spec
    §11: "Do NOT put similarity logic directly inside API routes").

    Pipeline: resolve + authorize the source cat → look up its stored
    embedding → reconstruct the query vector from the FAISS index (the
    vector itself is never stored anywhere but there — see
    CatEmbeddingModel's docstring) → over-fetch candidates from FAISS →
    resolve candidate vector_ids back to analysis rows → apply the
    privacy filter (§8) and self-exclusion → apply optional metadata
    filters (§18, post-retrieval only — they never influence the
    embedding search itself) → truncate to k → build the response.

    Returns a `search_mode: "unavailable"` response (never raises) for
    every "can't actually search" case that isn't "the source cat
    itself is invisible to this caller" — no embedding model, no index,
    no stored embedding for this specific cat. Raises
    `SourceCatNotVisibleError` only for the one case that's genuinely a
    404, not a degraded-but-valid outcome.
    """
    settings = get_settings()
    k = max(1, min(k, settings.similarity_max_k))

    source = await get_public_analysis(db, analysis_id)
    if source is None and viewer_user_id is not None:
        source = await get_owned_analysis(db, analysis_id, viewer_user_id)
    if source is None:
        raise SourceCatNotVisibleError(str(analysis_id))

    source_summary = SourceCatSummary(
        analysis_id=source.id, cat_name=source.cat_name, image_url=source.image_url
    )

    model = get_embedding_model()
    index = get_vector_index()
    source_embedding = await embedding_repository.get_by_analysis_id(db, source.id)
    if not model.is_available or not index.is_available or source_embedding is None:
        return _UNAVAILABLE.model_copy(update={"source_cat": source_summary})

    query_vector = index.get_vector(source_embedding.vector_id)
    if query_vector is None:
        # DB says this analysis has an embedding, but the index doesn't
        # have that vector — a real inconsistency (see
        # `app/cli/similarity_index.py`'s `verify` command), not
        # something to paper over with a fabricated result.
        return _UNAVAILABLE.model_copy(update={"source_cat": source_summary})

    oversample = min(k * settings.similarity_candidate_oversample, index.size)
    raw_results = index.search(query_vector, max(oversample, k))

    embedding_rows = await embedding_repository.get_by_vector_ids(
        db, [vector_id for vector_id, _ in raw_results]
    )
    score_by_vector_id = dict(raw_results)
    analysis_id_to_score: dict[uuid.UUID, float] = {}
    for embedding_row in embedding_rows:
        if embedding_row.analysis_id == source.id:
            continue  # self-exclusion (spec §11/§39)
        score = score_by_vector_id[embedding_row.vector_id]
        # A candidate could in principle appear via more than one
        # vector_id only if it had two embedding rows, which never
        # happens (analysis_id is unique on cat_embeddings) — this is
        # just a plain assignment, not a max()-merge.
        analysis_id_to_score[embedding_row.analysis_id] = score

    candidate_rows = {
        row.id: row for row in await get_many_by_ids(db, list(analysis_id_to_score.keys()))
    }

    ranked = sorted(analysis_id_to_score.items(), key=lambda pair: pair[1], reverse=True)

    similar_cats: list[SimilarCat] = []
    for candidate_id, score in ranked:
        row = candidate_rows.get(candidate_id)
        if row is None or not _is_eligible(row, viewer_user_id):
            continue
        if breed is not None and row.breed_label != breed:
            continue
        if rarity is not None and row.rarity != rarity:
            continue
        if favorites_only and not (
            viewer_user_id is not None and row.user_id == viewer_user_id and row.is_favorite
        ):
            continue
        similar_cats.append(_to_similar_cat(row, score, source, viewer_user_id))
        if len(similar_cats) >= k:
            break

    return SimilarityResponse(
        source_cat=source_summary,
        similar_cats=similar_cats,
        search_mode="embedding",
        embedding_model=f"{model.name}:{model.version}",
    )
