import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers import LLMProviderError, get_llm_provider
from app.models.analysis import CatAnalysisModel
from app.models.story import StoryModel
from app.repositories import story_repository
from app.repositories.analysis_repository import get_analysis
from app.schemas.common import ColorSwatch
from app.schemas.profile import CatProfile, CatSignals
from app.schemas.story import CatStory, StoryStyle
from app.services.story_templates import build_demo_story

logger = logging.getLogger(__name__)


class AnalysisNotFoundError(Exception):
    """Raised when the given analysis_id has no matching row —
    surfaced by the API layer as 404, never a 500."""


def _signals_and_profile_from_row(row: CatAnalysisModel) -> tuple[CatSignals, CatProfile]:
    signals = CatSignals(
        breed=row.breed_label,
        breed_confidence=row.breed_confidence,
        breed_mode=row.breed_mode,
        colors=[ColorSwatch.model_validate(c) for c in row.colors],
        colors_mode=row.colors_mode,
    )
    profile = CatProfile.model_validate(row.profile)
    return signals, profile


async def get_or_generate_story(
    db: AsyncSession,
    analysis_id: uuid.UUID,
    style: StoryStyle,
    regenerate: bool,
) -> StoryModel:
    """Cost-control contract: if a story already exists for this
    (analysis_id, style) and the caller didn't explicitly ask to
    regenerate, the existing row is returned and the LLM is never
    called. Falls back to a deterministic offline story on any provider
    failure — never raises for that reason, never blocks the request.
    """
    analysis_row = await get_analysis(db, analysis_id)
    if analysis_row is None:
        raise AnalysisNotFoundError(str(analysis_id))

    if not regenerate:
        existing = await story_repository.get_latest_story(db, analysis_id, style)
        if existing is not None:
            return existing

    signals, profile = _signals_and_profile_from_row(analysis_row)
    variant_offset = await story_repository.count_stories(db, analysis_id, style)
    seed_bytes = str(analysis_id).encode()

    provider = get_llm_provider()
    story: CatStory
    story_mode: str
    provider_name: str
    model_name: str | None = None

    if provider.is_available:
        try:
            story = await provider.generate_story(signals, profile, style)
            story_mode = "generated"
            provider_name = "anthropic"
            from app.core.config import get_settings

            model_name = get_settings().anthropic_model
        except LLMProviderError as exc:
            # Safe to log: LLMProviderError messages only ever contain the
            # exception type/validation summary, never the API key.
            logger.warning("Story generation failed, falling back to demo: %s", exc)
            story = build_demo_story(signals, profile, style, seed_bytes, variant_offset)
            story_mode, provider_name = "demo", "demo"
    else:
        story = build_demo_story(signals, profile, style, seed_bytes, variant_offset)
        story_mode, provider_name = "demo", "demo"

    return await story_repository.save_story(
        db,
        analysis_id=analysis_id,
        style=style,
        story=story,
        story_mode=story_mode,
        provider=provider_name,
        model=model_name,
    )
