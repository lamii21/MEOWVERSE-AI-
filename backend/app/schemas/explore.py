from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from app.schemas.analysis import BreedPrediction, ColorSwatch

ExploreSort = Literal["newest", "oldest", "rarity", "most_discovered", "name_asc", "name_desc"]
"""Only sorts backed by real, persisted data (spec §9: "do not invent
metrics"). `most_discovered` is real too — it orders by a count of real
CAT_EXPLORED gamification events (distinct authenticated users who have
opened this cat's page), introduced in this same phase. Deliberately
excludes "most collected"/"most shared"/"most liked" from the spec's
suggestion list: this schema has no per-cat "times saved by other
users," "share count," or public like mechanism (a cat is shared or
not — a boolean, not a count; favorites are a private per-owner flag,
never a public tally) — inventing one would violate the same spec
section's explicit instruction not to fabricate a metric that isn't
reliably persisted."""


class DiscoveryCatOut(BaseModel):
    """One public cat's card on `/explore` — deliberately a distinct
    shape from `AnalysisResult`, not a reused/overloaded version of it:
    every field here is safe to show to a stranger by construction
    (no `owned`, no `is_favorite`, no owner identity), and it carries
    fields `AnalysisResult` doesn't (archetype, public-scoped story/
    portrait indicators) that would be meaningless or privacy-risky on
    the owner-facing shape.
    """

    analysis_id: UUID
    cat_name: str
    breed: BreedPrediction | None
    rarity: str
    colors: list[ColorSwatch]
    image_url: str | None
    archetype_id: str
    archetype_name: str
    archetype_emoji: str
    has_public_story: bool
    has_public_portrait: bool
    created_at: datetime


class ExploreCatsPage(BaseModel):
    items: list[DiscoveryCatOut]
    total: int
    page: int
    page_size: int


class FeaturedCatsResponse(BaseModel):
    cats: list[DiscoveryCatOut]


class BreedExplorerOut(BaseModel):
    breed: str
    public_count: int
    examples: list[DiscoveryCatOut]


class PersonalityArchetypeExplorerOut(BaseModel):
    id: str
    name: str
    emoji: str
    short_description: str
    long_description: str
    theme_token: str
    public_count: int
    examples: list[DiscoveryCatOut]
    disclaimer: str = (
        "Personality archetypes are an AI-inspired interpretation of visual signals, "
        "not a scientific classification of your cat's actual behavior."
    )


class ColorExplorerOut(BaseModel):
    color_name: str
    hex: str
    public_count: int
    examples: list[DiscoveryCatOut]
