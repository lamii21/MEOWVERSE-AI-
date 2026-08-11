import uuid
from unittest.mock import patch

import pytest

from app.ai.providers import LLMProviderError
from app.repositories.analysis_repository import save_analysis
from app.schemas.analysis import AnalysisResult, BreedPrediction
from app.schemas.common import ColorSwatch
from app.schemas.profile import CatProfile
from app.schemas.story import CatStory, StoryStyle
from app.services.story_service import AnalysisNotFoundError, get_or_generate_story


def _sample_analysis_result() -> AnalysisResult:
    return AnalysisResult(
        detected=True,
        breed=BreedPrediction(label="Siamese", confidence=0.9),
        breed_mode="trained",
        colors=[ColorSwatch(name="cream", hex="#F3E5D8", percentage=70.0)],
        colors_mode="trained",
        profile=CatProfile(
            name="Nova",
            title="Star-Chaser",
            personality="Bold.",
            magic_power="Leaps.",
            kingdom="The Comet Trail",
            favorite_activity="Chasing",
            favorite_food="Tuna",
            favorite_season="Autumn",
            rarity="Epic",
            description="Explorer.",
        ),
        profile_mode="demo",
    )


async def _create_analysis(db_session) -> uuid.UUID:
    row = await save_analysis(db_session, _sample_analysis_result())
    return row.id


_VALID_STORY_KWARGS = {
    "title": "Real Story",
    "subtitle": "sub",
    "opening": "op",
    "chapters": [
        {"chapter_number": 1, "title": "a", "text": "b"},
        {"chapter_number": 2, "title": "c", "text": "d"},
        {"chapter_number": 3, "title": "e", "text": "f"},
    ],
    "ending": "end",
    "moral": "moral",
    "quote": "quote",
}


class _FakeUnavailableProvider:
    is_available = False


class _FakeWorkingProvider:
    is_available = True

    def __init__(self):
        self.call_count = 0

    async def generate_story(self, signals, profile, style):
        self.call_count += 1
        return CatStory.model_validate(_VALID_STORY_KWARGS)


class _FakeFailingProvider:
    is_available = True

    async def generate_story(self, signals, profile, style):
        raise LLMProviderError("simulated failure")


@pytest.mark.asyncio
async def test_nonexistent_analysis_raises(db_session):
    with pytest.raises(AnalysisNotFoundError):
        await get_or_generate_story(db_session, uuid.uuid4(), StoryStyle.COZY_WHOLESOME, False)


@pytest.mark.asyncio
@patch("app.services.story_service.get_llm_provider")
async def test_falls_back_to_demo_when_no_provider(mock_get_provider, db_session):
    mock_get_provider.return_value = _FakeUnavailableProvider()
    analysis_id = await _create_analysis(db_session)

    row = await get_or_generate_story(db_session, analysis_id, StoryStyle.COZY_WHOLESOME, False)

    assert row.story_mode == "demo"
    assert row.provider == "demo"
    assert row.model is None
    assert row.story["title"]
    assert row.analysis_id == analysis_id


@pytest.mark.asyncio
@patch("app.services.story_service.get_llm_provider")
async def test_provider_success_persists_generated_story(mock_get_provider, db_session):
    mock_get_provider.return_value = _FakeWorkingProvider()
    analysis_id = await _create_analysis(db_session)

    row = await get_or_generate_story(db_session, analysis_id, StoryStyle.FANTASY_QUEST, False)

    assert row.story_mode == "generated"
    assert row.provider == "anthropic"
    assert row.model is not None
    assert row.story["title"] == "Real Story"


@pytest.mark.asyncio
@patch("app.services.story_service.get_llm_provider")
async def test_provider_failure_falls_back_to_demo(mock_get_provider, db_session):
    mock_get_provider.return_value = _FakeFailingProvider()
    analysis_id = await _create_analysis(db_session)

    row = await get_or_generate_story(db_session, analysis_id, StoryStyle.DREAMY_EMOTIONAL, False)

    assert row.story_mode == "demo"
    assert row.provider == "demo"


@pytest.mark.asyncio
@patch("app.services.story_service.get_llm_provider")
async def test_duplicate_request_returns_existing_without_calling_provider(
    mock_get_provider, db_session
):
    """Cost-control contract: no explicit regenerate = no new LLM call
    if a story already exists for this (analysis_id, style)."""
    provider = _FakeWorkingProvider()
    mock_get_provider.return_value = provider
    analysis_id = await _create_analysis(db_session)

    first = await get_or_generate_story(
        db_session, analysis_id, StoryStyle.MAGICAL_ADVENTURE, False
    )
    second = await get_or_generate_story(
        db_session, analysis_id, StoryStyle.MAGICAL_ADVENTURE, False
    )

    assert first.id == second.id
    assert provider.call_count == 1


@pytest.mark.asyncio
@patch("app.services.story_service.get_llm_provider")
async def test_regenerate_creates_a_new_row_and_calls_provider_again(
    mock_get_provider, db_session
):
    provider = _FakeWorkingProvider()
    mock_get_provider.return_value = provider
    analysis_id = await _create_analysis(db_session)

    first = await get_or_generate_story(
        db_session, analysis_id, StoryStyle.MAGICAL_ADVENTURE, False
    )
    second = await get_or_generate_story(
        db_session, analysis_id, StoryStyle.MAGICAL_ADVENTURE, True
    )

    assert first.id != second.id
    assert provider.call_count == 2


@pytest.mark.asyncio
@patch("app.services.story_service.get_llm_provider")
async def test_regenerate_in_demo_mode_visibly_changes_the_story(mock_get_provider, db_session):
    """Even offline, "Regenerate" must do something rather than silently
    returning the exact same story (see test_story_templates.py for the
    underlying variant-cycling mechanism)."""
    mock_get_provider.return_value = _FakeUnavailableProvider()
    analysis_id = await _create_analysis(db_session)

    first = await get_or_generate_story(db_session, analysis_id, StoryStyle.FUNNY_CHAOTIC, False)
    second = await get_or_generate_story(db_session, analysis_id, StoryStyle.FUNNY_CHAOTIC, True)

    assert first.id != second.id
    assert first.story != second.story


@pytest.mark.asyncio
@patch("app.services.story_service.get_llm_provider")
async def test_different_styles_are_independent(mock_get_provider, db_session):
    mock_get_provider.return_value = _FakeUnavailableProvider()
    analysis_id = await _create_analysis(db_session)

    cozy = await get_or_generate_story(db_session, analysis_id, StoryStyle.COZY_WHOLESOME, False)
    chaotic = await get_or_generate_story(
        db_session, analysis_id, StoryStyle.FUNNY_CHAOTIC, False
    )

    assert cozy.id != chaotic.id
    assert cozy.style == "cozy_wholesome"
    assert chaotic.style == "funny_chaotic"
