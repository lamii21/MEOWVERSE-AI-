"""MeowVerse Cat Universe — public discovery (Phase 15). The single
place `/explore`'s listing, featured selection, and breed/personality/
color explorer logic live (spec §32: "do not put logic directly inside
API routes," same convention as similarity/personality/portrait's own
service layers).

Every function here operates ONLY on rows the repository layer has
already filtered to `is_public = True` in SQL (spec §28) — nothing in
this module re-derives or second-guesses visibility; it composes
already-safe rows into response shapes.
"""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import CatAnalysisModel
from app.repositories import analysis_repository
from app.repositories.portrait_repository import get_analysis_ids_with_public_portraits
from app.repositories.story_repository import get_analysis_ids_with_public_stories
from app.schemas.analysis import BreedPrediction, ColorSwatch
from app.schemas.explore import (
    BreedExplorerOut,
    ColorExplorerOut,
    DiscoveryCatOut,
    ExploreCatsPage,
    ExploreSort,
    FeaturedCatsResponse,
    PersonalityArchetypeExplorerOut,
)
from app.services.personality_scoring import ARCHETYPES, compute_traits, select_archetype

_EXAMPLES_PER_GROUP = 6
_FEATURED_COUNT = 8
_RARITY_TIER_INDEX = {
    "Common": 0,
    "Uncommon": 1,
    "Rare": 2,
    "Epic": 3,
    "Legendary": 4,
    "Mythical": 5,
}


def _archetype_for(row: CatAnalysisModel):
    """Reuses Phase 13's deterministic scoring engine directly — never
    a join against `cat_personalities` (which only has rows for cats
    someone has actually opened the Personality card for, an
    incomplete and view-order-dependent source for browse-time
    filtering/display). `compute_traits`/`select_archetype` are pure,
    sub-millisecond functions of columns already loaded on `row` — this
    adds zero additional queries per cat."""
    traits = compute_traits(
        analysis_id=str(row.id),
        breed_label=row.breed_label,
        breed_confidence=row.breed_confidence,
        colors=row.colors,
    )
    return select_archetype(traits)


async def _to_discovery_cats(
    db: AsyncSession, rows: list[CatAnalysisModel]
) -> list[DiscoveryCatOut]:
    """Batched enrichment (spec §30/31: no N+1) — exactly two extra
    queries total for the whole page, regardless of how many rows are
    on it, not one query per cat."""
    ids = [row.id for row in rows]
    story_ids = await get_analysis_ids_with_public_stories(db, ids)
    portrait_ids = await get_analysis_ids_with_public_portraits(db, ids)

    results = []
    for row in rows:
        archetype = _archetype_for(row)
        results.append(
            DiscoveryCatOut(
                analysis_id=row.id,
                cat_name=row.cat_name,
                breed=BreedPrediction(label=row.breed_label, confidence=row.breed_confidence)
                if row.breed_label
                else None,
                rarity=row.rarity,
                colors=[ColorSwatch.model_validate(c) for c in row.colors],
                image_url=row.image_url,
                archetype_id=archetype.id,
                archetype_name=archetype.name,
                archetype_emoji=archetype.emoji,
                has_public_story=row.id in story_ids,
                has_public_portrait=row.id in portrait_ids,
                created_at=row.created_at,
            )
        )
    return results


def _matches_color(row: CatAnalysisModel, color: str) -> bool:
    return any(swatch.get("name") == color for swatch in row.colors)


def _sort_key(sort: ExploreSort):
    if sort == "oldest":
        return lambda r: r.created_at
    if sort == "name_asc":
        return lambda r: r.cat_name.lower()
    if sort == "name_desc":
        return lambda r: r.cat_name.lower()
    if sort == "rarity":
        return lambda r: _RARITY_TIER_INDEX.get(r.rarity, -1)
    # "newest" (default) and "most_discovered" (no per-cat explore
    # count available cheaply without the SQL join path) both fall
    # back to recency here — most_discovered combined with an
    # archetype/color filter is a rare enough combination that this
    # documented simplification is preferable to a second batched
    # count query on every such request.
    return lambda r: r.created_at


async def list_explore_cats(
    db: AsyncSession,
    *,
    breed: str | None = None,
    rarity: str | None = None,
    archetype: str | None = None,
    color: str | None = None,
    has_public_story: bool = False,
    has_public_portrait: bool = False,
    search: str | None = None,
    sort: ExploreSort = "newest",
    page: int = 1,
    page_size: int = 24,
) -> ExploreCatsPage:
    """The `/explore/cats` listing (spec §3-9). Two paths:

    - No archetype/color filter: pure SQL pagination
      (`analysis_repository.list_public_analyses`) — scales normally.
    - Archetype and/or color filter: every SQL-filterable predicate
      (breed/rarity/story/portrait/search) is still applied in SQL
      first (`list_public_analyses_unpaginated`), then archetype
      (computed, not stored) and color (JSONB array membership, not a
      single indexable column with this schema) are applied in Python,
      followed by Python-side sort + pagination. Still exactly one
      query, not N+1 — see that function's docstring for the documented
      scale tradeoff.
    """
    if archetype is None and color is None:
        rows, total = await analysis_repository.list_public_analyses(
            db,
            breed=breed,
            rarity=rarity,
            has_public_story=has_public_story,
            has_public_portrait=has_public_portrait,
            search=search,
            sort=sort,
            page=page,
            page_size=page_size,
        )
        items = await _to_discovery_cats(db, rows)
        return ExploreCatsPage(items=items, total=total, page=page, page_size=page_size)

    all_rows = await analysis_repository.list_public_analyses_unpaginated(
        db,
        breed=breed,
        rarity=rarity,
        has_public_story=has_public_story,
        has_public_portrait=has_public_portrait,
        search=search,
    )
    if color is not None:
        all_rows = [r for r in all_rows if _matches_color(r, color)]

    reverse = sort not in ("oldest", "name_asc")
    all_rows.sort(key=_sort_key(sort), reverse=reverse)

    if archetype is not None:
        matched = []
        for row in all_rows:
            if _archetype_for(row).id == archetype:
                matched.append(row)
        all_rows = matched

    total = len(all_rows)
    start = (page - 1) * page_size
    page_rows = all_rows[start : start + page_size]
    items = await _to_discovery_cats(db, page_rows)
    return ExploreCatsPage(items=items, total=total, page=page, page_size=page_size)


@dataclass(frozen=True)
class _FeaturedScoreBreakdown:
    rarity_points: int
    portrait_points: int
    story_points: int
    quality_points: int

    @property
    def total(self) -> int:
        return self.rarity_points + self.portrait_points + self.story_points + self.quality_points


def _featured_score(
    row: CatAnalysisModel, *, has_story: bool, has_portrait: bool
) -> _FeaturedScoreBreakdown:
    """The deterministic featured-selection formula (spec §10 —
    explicitly NOT random, documented exactly here):

    - rarity_points = rarity tier index (0-5) * 10 — a Legendary cat
      scores 40 points higher than a Common one.
    - portrait_points = 5 if it has at least one public AI portrait.
    - story_points = 3 if it has a public story.
    - quality_points = 2 for a real (non-demo) breed prediction, +2 for
      a real (non-demo) color analysis — "completeness" (spec §10).

    Ties break on `created_at` descending (newer first), then `id`
    ascending as a final, fully deterministic tiebreak — the same cat
    never reorders between two requests with an unchanged data set,
    satisfying spec §10's "should not jump around unpredictably."
    """
    rarity_points = _RARITY_TIER_INDEX.get(row.rarity, 0) * 10
    portrait_points = 5 if has_portrait else 0
    story_points = 3 if has_story else 0
    quality_points = (2 if row.breed_mode == "trained" else 0) + (
        2 if row.colors_mode == "trained" else 0
    )
    return _FeaturedScoreBreakdown(rarity_points, portrait_points, story_points, quality_points)


async def get_featured_cats(db: AsyncSession) -> FeaturedCatsResponse:
    all_rows = await analysis_repository.list_public_analyses_unpaginated(db)
    ids = [row.id for row in all_rows]
    story_ids = await get_analysis_ids_with_public_stories(db, ids)
    portrait_ids = await get_analysis_ids_with_public_portraits(db, ids)

    scored = [
        (
            row,
            _featured_score(
                row, has_story=row.id in story_ids, has_portrait=row.id in portrait_ids
            ),
        )
        for row in all_rows
    ]
    scored.sort(key=lambda pair: (pair[1].total, pair[0].created_at, str(pair[0].id)), reverse=True)
    top_rows = [row for row, _ in scored[:_FEATURED_COUNT]]
    return FeaturedCatsResponse(cats=await _to_discovery_cats(db, top_rows))


async def get_breed_explorer(db: AsyncSession) -> list[BreedExplorerOut]:
    """Breed Explorer (spec §12) — public-cat counts only, explicitly
    documented as such in the response field name (`public_count`, not
    a bare `count` that could be confused with Phase 10's owner-scoped
    breed stats)."""
    from app.services.breed_catalog import get_supported_breeds

    counts = await analysis_repository.get_public_breed_counts(db)
    results = []
    for breed in get_supported_breeds():
        public_count = counts.get(breed, 0)
        examples: list[DiscoveryCatOut] = []
        if public_count > 0:
            rows, _ = await analysis_repository.list_public_analyses(
                db, breed=breed, sort="rarity", page=1, page_size=_EXAMPLES_PER_GROUP
            )
            examples = await _to_discovery_cats(db, rows)
        results.append(BreedExplorerOut(breed=breed, public_count=public_count, examples=examples))
    return results


async def get_personality_explorer(db: AsyncSession) -> list[PersonalityArchetypeExplorerOut]:
    """Personality Explorer (spec §13) — every public cat is classified
    once (one query, then a cheap Python pass, same as the main listing's
    archetype path) and grouped by archetype; never claims these are a
    scientific classification (spec §13, `PersonalityArchetypeExplorerOut`'s
    disclaimer field)."""
    all_rows = await analysis_repository.list_public_analyses_unpaginated(db)
    by_archetype: dict[str, list[CatAnalysisModel]] = {a.id: [] for a in ARCHETYPES}
    for row in all_rows:
        by_archetype[_archetype_for(row).id].append(row)

    results = []
    for a in ARCHETYPES:
        rows = by_archetype[a.id]
        examples = await _to_discovery_cats(db, rows[:_EXAMPLES_PER_GROUP])
        results.append(
            PersonalityArchetypeExplorerOut(
                id=a.id,
                name=a.name,
                emoji=a.emoji,
                short_description=a.short_description,
                long_description=a.long_description,
                theme_token=a.theme_token,
                public_count=len(rows),
                examples=examples,
            )
        )
    return results


async def get_color_explorer(db: AsyncSession) -> list[ColorExplorerOut]:
    """Color Explorer (spec §14) — groups public cats by their
    dominant (highest-percentage) fur color swatch, reusing Phase 5's
    real analyzed color names/hex values verbatim (never a second,
    invented color-classification system)."""
    all_rows = await analysis_repository.list_public_analyses_unpaginated(db)
    by_color: dict[str, list[CatAnalysisModel]] = {}
    hex_by_color: dict[str, str] = {}
    for row in all_rows:
        if not row.colors:
            continue
        dominant = max(row.colors, key=lambda c: c.get("percentage", 0))
        name = dominant.get("name")
        if not name:
            continue
        by_color.setdefault(name, []).append(row)
        hex_by_color.setdefault(name, dominant.get("hex", "#808080"))

    results = []
    for name, rows in sorted(by_color.items(), key=lambda pair: len(pair[1]), reverse=True):
        examples = await _to_discovery_cats(db, rows[:_EXAMPLES_PER_GROUP])
        results.append(
            ColorExplorerOut(
                color_name=name, hex=hex_by_color[name], public_count=len(rows), examples=examples
            )
        )
    return results
