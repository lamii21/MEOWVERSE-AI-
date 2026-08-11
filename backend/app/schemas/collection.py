from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.achievement import AchievementOut
from app.schemas.analysis import AnalysisResult

__all__ = [
    "AchievementOut",
    "BreedDiscoveryOut",
    "CollectionPage",
    "CollectionStats",
    "ProgressOut",
]


class CollectionPage(BaseModel):
    items: list[AnalysisResult]
    total: int
    page: int
    page_size: int


class CollectionStats(BaseModel):
    total_cats: int
    favorite_breed: str | None
    most_common_color: str | None
    legendary_count: int
    # Phase 10:
    rare_count: int = 0
    """Cats of Rare rarity or higher (Rare/Epic/Legendary/Mythical) —
    a superset of legendary_count, same tiered-threshold convention."""
    favorites_count: int
    stories_created: int
    unique_breeds_discovered: int = 0
    """COUNT(DISTINCT breed_label) restricted to the canonical breed
    universe (app/services/breed_catalog.py) — the numerator of
    `completion_percentage`. See that module's docstring for why this
    differs from "any breed_label ever seen"."""
    total_supported_breeds: int = 0
    completion_percentage: float = 0.0
    """`round(100 * unique_breeds_discovered / total_supported_breeds, 1)`
    — see app/services/collection_service.py. 0.0 if the breed catalog
    itself is empty (never divides by zero)."""
    unique_colors_discovered: int = 0
    rarity_distribution: dict[str, int] = Field(default_factory=dict)
    """Zero-filled across all six tiers — see
    analysis_repository.get_rarity_distribution."""


class BreedDiscoveryOut(BaseModel):
    breed: str
    discovered: bool
    count: int
    best_confidence: float | None
    latest_discovery: datetime | None


class ProgressOut(BaseModel):
    xp: int
    level: int
    level_title: str
    xp_into_level: int
    xp_needed_for_level: int
    """0 once the user has hit MAX_LEVEL (nothing more to earn toward
    the next level)."""
    xp_for_next_level: int | None
    """None once the user has hit MAX_LEVEL."""
    progress_ratio: float
    """0.0-1.0, how far into the current level the user is. Always 1.0
    at MAX_LEVEL."""
