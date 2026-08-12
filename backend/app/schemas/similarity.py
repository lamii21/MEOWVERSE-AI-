import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.analysis import BreedPrediction

SearchMode = Literal["embedding", "unavailable"]


class SourceCatSummary(BaseModel):
    """The cat being searched *from* — only the small set of fields the
    "Cats Like This" header needs, not a full `AnalysisResult` (no
    need to re-expose the source's private state to itself here)."""

    analysis_id: uuid.UUID
    cat_name: str
    image_url: str | None


class SimilarCat(BaseModel):
    """One search result. Every field here is either public-safe by
    construction (breed/rarity/name/image are already public on a
    shared Cat Card) or owner-gated the same way `AnalysisResult` is
    (`is_favorite` is only ever the *searching user's own* favorite
    state on a cat *they* own — never a stranger's, see
    `similarity_service.py`'s `_to_similar_cat`)."""

    analysis_id: uuid.UUID
    cat_name: str
    image_url: str | None
    breed: BreedPrediction | None
    rarity: str
    visual_similarity: float = Field(ge=0.0, le=1.0)
    """`max(0, cosine_similarity(query, candidate))` — a 0-1 ratio, not
    a percentage. Clamped at 0 because a negative cosine similarity
    (the two images point in near-opposite directions in the model's
    576-dim feature space) has no meaningful "-40% similar" UI
    presentation; nothing here is invented, only floored. See
    ARCHITECTURE.md §19 for the full mathematical definition."""
    shared_colors: list[str] = Field(default_factory=list)
    """Fur-color names present in both the source and this candidate's
    palettes — informational metadata explaining the result, never
    part of the similarity computation itself (Phase 11 spec §3)."""
    is_favorite: bool = False
    created_at: datetime | None


class SimilarityResponse(BaseModel):
    source_cat: SourceCatSummary
    similar_cats: list[SimilarCat]
    search_mode: SearchMode
    """"embedding" when a real vector search ran (even if it found zero
    eligible results); "unavailable" when the embedding model, the
    vector index, or the source cat's own embedding isn't available —
    never a third value pretending to be one of these two when it
    isn't (Phase 11 spec §26)."""
    embedding_model: str | None
    """The model name that produced the vectors actually searched —
    `None` when `search_mode == "unavailable"`. Exposed because it's
    genuinely useful for understanding the result (a portfolio-quality
    "how this works" detail), never a secret."""
