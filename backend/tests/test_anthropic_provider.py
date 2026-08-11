from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import anthropic
import httpx
import pytest

from app.ai.anthropic_provider import AnthropicLLMProvider
from app.ai.providers import LLMProviderError
from app.schemas.common import ColorSwatch
from app.schemas.profile import CatProfile, CatSignals
from app.schemas.story import CatStory, StoryStyle

VALID_PROFILE_DICT = {
    "name": "Biscuit",
    "title": "Keeper of Sunbeams",
    "personality": "Warm and unhurried.",
    "magic_power": "Finds the warmest spot in any room.",
    "kingdom": "The Sunlit Archives",
    "favorite_activity": "Napping",
    "favorite_food": "Salmon",
    "favorite_season": "Summer",
    "rarity": "Rare",
    "description": "A gentle sunbeam-chaser.",
}

VALID_STORY_DICT = {
    "title": "Biscuit and the Sunbeam",
    "subtitle": "A tale of warmth",
    "opening": "It was a quiet afternoon.",
    "chapters": [
        {"chapter_number": 1, "title": "Beginning", "text": "Biscuit found a sunbeam."},
        {"chapter_number": 2, "title": "Middle", "text": "Biscuit napped in it."},
        {"chapter_number": 3, "title": "End", "text": "Biscuit was content."},
    ],
    "ending": "And so the day ended well.",
    "moral": "Rest is its own reward.",
    "quote": '"Sunbeams are for napping."',
}


def _signals() -> CatSignals:
    return CatSignals(
        breed="Bengal",
        breed_confidence=0.9,
        breed_mode="trained",
        colors=[ColorSwatch(name="orange", hex="#D98B4B", percentage=60.0)],
        colors_mode="trained",
    )


def _profile() -> CatProfile:
    return CatProfile.model_validate(VALID_PROFILE_DICT)


def _tool_use_response(input_dict: dict):
    block = SimpleNamespace(type="tool_use", input=input_dict, name="generate_cat_profile")
    return SimpleNamespace(content=[block])


def _text_only_response(text: str = "hello"):
    block = SimpleNamespace(type="text", text=text)
    return SimpleNamespace(content=[block])


def _make_provider() -> AnthropicLLMProvider:
    with patch("app.ai.anthropic_provider.anthropic.AsyncAnthropic"):
        return AnthropicLLMProvider(api_key="sk-test-not-real", model="claude-test")


@pytest.mark.asyncio
async def test_valid_response_returns_profile():
    provider = _make_provider()
    provider._client.messages.create = AsyncMock(
        return_value=_tool_use_response(VALID_PROFILE_DICT)
    )

    profile = await provider.generate_profile(_signals())

    assert isinstance(profile, CatProfile)
    assert profile.name == "Biscuit"
    assert provider._client.messages.create.call_count == 1


@pytest.mark.asyncio
async def test_missing_tool_use_block_retries_then_fails():
    provider = _make_provider()
    provider._client.messages.create = AsyncMock(return_value=_text_only_response())

    with pytest.raises(LLMProviderError):
        await provider.generate_profile(_signals())

    assert provider._client.messages.create.call_count == 2


@pytest.mark.asyncio
async def test_invalid_schema_retries_then_recovers():
    invalid = dict(VALID_PROFILE_DICT)
    invalid["favorite_season"] = "NotASeason"  # violates the Literal
    provider = _make_provider()
    provider._client.messages.create = AsyncMock(
        side_effect=[
            _tool_use_response(invalid),
            _tool_use_response(VALID_PROFILE_DICT),
        ]
    )

    profile = await provider.generate_profile(_signals())

    assert profile.name == "Biscuit"
    assert provider._client.messages.create.call_count == 2


@pytest.mark.asyncio
async def test_invalid_schema_after_retry_raises():
    invalid = dict(VALID_PROFILE_DICT)
    invalid["rarity"] = "SuperDuperRare"  # violates the Literal
    provider = _make_provider()
    provider._client.messages.create = AsyncMock(return_value=_tool_use_response(invalid))

    with pytest.raises(LLMProviderError):
        await provider.generate_profile(_signals())

    assert provider._client.messages.create.call_count == 2


@pytest.mark.asyncio
async def test_api_timeout_raises_llm_provider_error():
    provider = _make_provider()
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    provider._client.messages.create = AsyncMock(
        side_effect=anthropic.APITimeoutError(request=request)
    )

    with pytest.raises(LLMProviderError):
        await provider.generate_profile(_signals())

    # Transport errors are not retried at this layer.
    assert provider._client.messages.create.call_count == 1


@pytest.mark.asyncio
async def test_api_status_error_raises_llm_provider_error():
    provider = _make_provider()
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    response = httpx.Response(500, request=request)
    provider._client.messages.create = AsyncMock(
        side_effect=anthropic.APIStatusError(
            "server error", response=response, body=None
        )
    )

    with pytest.raises(LLMProviderError):
        await provider.generate_profile(_signals())


@pytest.mark.asyncio
async def test_api_connection_error_raises_llm_provider_error():
    provider = _make_provider()
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    provider._client.messages.create = AsyncMock(
        side_effect=anthropic.APIConnectionError(request=request)
    )

    with pytest.raises(LLMProviderError):
        await provider.generate_profile(_signals())


@pytest.mark.asyncio
async def test_generate_story_valid_response():
    provider = _make_provider()
    provider._client.messages.create = AsyncMock(
        return_value=_tool_use_response(VALID_STORY_DICT)
    )

    story = await provider.generate_story(_signals(), _profile(), StoryStyle.COZY_WHOLESOME)

    assert isinstance(story, CatStory)
    assert story.title == "Biscuit and the Sunbeam"
    assert len(story.chapters) == 3
    assert provider._client.messages.create.call_count == 1


@pytest.mark.asyncio
async def test_generate_story_invalid_schema_retries_then_recovers():
    too_few_chapters = dict(VALID_STORY_DICT)
    too_few_chapters["chapters"] = VALID_STORY_DICT["chapters"][:1]  # violates min_length=3
    provider = _make_provider()
    provider._client.messages.create = AsyncMock(
        side_effect=[
            _tool_use_response(too_few_chapters),
            _tool_use_response(VALID_STORY_DICT),
        ]
    )

    story = await provider.generate_story(_signals(), _profile(), StoryStyle.FANTASY_QUEST)

    assert story.title == "Biscuit and the Sunbeam"
    assert provider._client.messages.create.call_count == 2


@pytest.mark.asyncio
async def test_generate_story_api_timeout_raises_llm_provider_error():
    provider = _make_provider()
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    provider._client.messages.create = AsyncMock(
        side_effect=anthropic.APITimeoutError(request=request)
    )

    with pytest.raises(LLMProviderError):
        await provider.generate_story(_signals(), _profile(), StoryStyle.DREAMY_EMOTIONAL)

    assert provider._client.messages.create.call_count == 1


@pytest.mark.asyncio
async def test_generate_story_each_style_produces_a_valid_call():
    """Every StoryStyle must be usable end to end through the provider
    (exercises build_user_prompt/build_style_instructions for each)."""
    provider = _make_provider()
    provider._client.messages.create = AsyncMock(
        return_value=_tool_use_response(VALID_STORY_DICT)
    )

    for style in StoryStyle:
        story = await provider.generate_story(_signals(), _profile(), style)
        assert isinstance(story, CatStory)


def test_missing_api_key_uses_null_provider(monkeypatch):
    from app.ai.providers import NullLLMProvider, get_llm_provider
    from app.core.config import get_settings

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    get_settings.cache_clear()
    try:
        provider = get_llm_provider()
        assert isinstance(provider, NullLLMProvider)
        assert provider.is_available is False
    finally:
        get_settings.cache_clear()


def test_configured_api_key_uses_anthropic_provider(monkeypatch):
    from app.ai.providers import get_llm_provider
    from app.core.config import get_settings

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-not-real")
    get_settings.cache_clear()
    try:
        provider = get_llm_provider()
        assert isinstance(provider, AnthropicLLMProvider)
        assert provider.is_available is True
    finally:
        get_settings.cache_clear()
