from unittest.mock import patch

import pytest

from app.ai.providers import LLMProviderError
from app.schemas.common import ColorSwatch
from app.schemas.profile import CatProfile, CatSignals
from app.services.profile_service import _DEMO_PROFILES, generate_cat_profile

VALID_PROFILE = CatProfile(
    name="Nova",
    title="Star-Chaser",
    personality="Bold and curious.",
    magic_power="Leaps between sunbeams.",
    kingdom="The Comet Trail",
    favorite_activity="Chasing laser dots",
    favorite_food="Tuna",
    favorite_season="Autumn",
    rarity="Epic",
    description="A tiny explorer with a big destiny.",
)


def _signals() -> CatSignals:
    return CatSignals(
        breed="Siamese",
        breed_confidence=0.85,
        breed_mode="trained",
        colors=[ColorSwatch(name="cream", hex="#F3E5D8", percentage=70.0)],
        colors_mode="demo",
    )


class _FakeUnavailableProvider:
    is_available = False


class _FakeWorkingProvider:
    is_available = True

    async def generate_profile(self, signals):
        return VALID_PROFILE


class _FakeFailingProvider:
    is_available = True

    async def generate_profile(self, signals):
        raise LLMProviderError("simulated failure")


@pytest.mark.asyncio
@patch("app.services.profile_service.get_llm_provider")
async def test_no_provider_configured_falls_back_to_demo(mock_get_provider):
    mock_get_provider.return_value = _FakeUnavailableProvider()

    profile, mode = await generate_cat_profile(_signals(), b"some-image-bytes")

    assert mode == "demo"
    assert profile in _DEMO_PROFILES


@pytest.mark.asyncio
@patch("app.services.profile_service.get_llm_provider")
async def test_provider_success_returns_generated(mock_get_provider):
    mock_get_provider.return_value = _FakeWorkingProvider()

    profile, mode = await generate_cat_profile(_signals(), b"some-image-bytes")

    assert mode == "generated"
    assert profile == VALID_PROFILE


@pytest.mark.asyncio
@patch("app.services.profile_service.get_llm_provider")
async def test_provider_failure_falls_back_to_demo_without_raising(mock_get_provider):
    mock_get_provider.return_value = _FakeFailingProvider()

    profile, mode = await generate_cat_profile(_signals(), b"some-image-bytes")

    assert mode == "demo"
    assert profile in _DEMO_PROFILES


@pytest.mark.asyncio
@patch("app.services.profile_service.get_llm_provider")
async def test_demo_fallback_is_deterministic_per_image(mock_get_provider):
    mock_get_provider.return_value = _FakeUnavailableProvider()

    profile1, _ = await generate_cat_profile(_signals(), b"same-bytes")
    profile2, _ = await generate_cat_profile(_signals(), b"same-bytes")
    profile3, _ = await generate_cat_profile(_signals(), b"different-bytes")

    assert profile1 == profile2
    # Not a hard guarantee different bytes give a different profile (pool
    # is finite), but with 5 entries and these two fixtures it does.
    assert profile1 != profile3
