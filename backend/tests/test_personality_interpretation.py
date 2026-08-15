from unittest.mock import patch

import pytest

from app.ai.providers import LLMProviderError
from app.schemas.common import ColorSwatch
from app.schemas.personality import PersonalityInterpretation
from app.schemas.profile import CatSignals
from app.services.personality_interpretation_service import (
    _DEMO_INTERPRETATIONS,
    generate_interpretation,
)
from app.services.personality_scoring import ARCHETYPES, TRAITS, get_archetype

VALID_INTERPRETATION = PersonalityInterpretation(
    headline="A star among cats",
    description="Bold and curious, always chasing the next adventure.",
    catchphrase="Onward, to the next sunbeam.",
    secret_talent="Finding the one warm spot in any room.",
    fictional_job="Chief Sunbeam Officer",
    fun_fact="Has never once regretted a nap.",
)


def _signals() -> CatSignals:
    return CatSignals(
        breed="Siamese",
        breed_confidence=0.85,
        breed_mode="trained",
        colors=[ColorSwatch(name="cream", hex="#F3E5D8", percentage=70.0)],
        colors_mode="demo",
    )


def _archetype():
    return get_archetype("dreamy_explorer")


def _trait_levels():
    return {t: "High" for t in TRAITS}


class _FakeUnavailableProvider:
    is_available = False


class _FakeWorkingProvider:
    is_available = True

    async def generate_personality_interpretation(self, signals, **kwargs):
        return VALID_INTERPRETATION


class _FakeFailingProvider:
    is_available = True

    async def generate_personality_interpretation(self, signals, **kwargs):
        raise LLMProviderError("simulated failure")


class TestFallback:
    @pytest.mark.asyncio
    @patch("app.services.personality_interpretation_service.get_llm_provider")
    async def test_no_provider_configured_falls_back_to_demo(self, mock_get_provider):
        mock_get_provider.return_value = _FakeUnavailableProvider()

        interpretation, mode, model = await generate_interpretation(
            signals=_signals(), archetype=_archetype(), trait_levels=_trait_levels(), rarity="Rare"
        )

        assert mode == "demo"
        assert model == "demo"
        assert interpretation == _DEMO_INTERPRETATIONS["dreamy_explorer"]

    @pytest.mark.asyncio
    @patch("app.services.personality_interpretation_service.get_llm_provider")
    async def test_provider_success_returns_generated(self, mock_get_provider):
        mock_get_provider.return_value = _FakeWorkingProvider()

        interpretation, mode, model = await generate_interpretation(
            signals=_signals(), archetype=_archetype(), trait_levels=_trait_levels(), rarity="Rare"
        )

        assert mode == "generated"
        assert model == "anthropic"
        assert interpretation == VALID_INTERPRETATION

    @pytest.mark.asyncio
    @patch("app.services.personality_interpretation_service.get_llm_provider")
    async def test_provider_failure_falls_back_to_demo_without_raising(self, mock_get_provider):
        mock_get_provider.return_value = _FakeFailingProvider()

        interpretation, mode, model = await generate_interpretation(
            signals=_signals(), archetype=_archetype(), trait_levels=_trait_levels(), rarity="Rare"
        )

        assert mode == "demo"
        assert interpretation == _DEMO_INTERPRETATIONS["dreamy_explorer"]

    @pytest.mark.asyncio
    @patch("app.services.personality_interpretation_service.get_llm_provider")
    async def test_demo_interpretation_is_archetype_specific_not_generic(self, mock_get_provider):
        mock_get_provider.return_value = _FakeUnavailableProvider()

        cozy, _, _ = await generate_interpretation(
            signals=_signals(),
            archetype=get_archetype("cozy_cuddlebug"),
            trait_levels=_trait_levels(),
            rarity="Rare",
        )
        chaos, _, _ = await generate_interpretation(
            signals=_signals(),
            archetype=get_archetype("chaos_bean"),
            trait_levels=_trait_levels(),
            rarity="Rare",
        )
        assert cozy != chaos

    def test_every_archetype_has_its_own_demo_interpretation(self):
        for archetype in ARCHETYPES:
            assert archetype.id in _DEMO_INTERPRETATIONS


class TestCreativeOutputCannotAlterStructuredResult:
    """Phase 13 spec §35: creative output cannot modify personality
    scores or the archetype — enforced structurally, not by convention:
    `PersonalityInterpretation` has no fields for either, so there's
    nothing an LLM (or a malformed provider response) could put a
    score/archetype into even if it wanted to."""

    def test_interpretation_schema_has_no_trait_score_fields(self):
        fields = set(PersonalityInterpretation.model_fields.keys())
        assert fields == {
            "headline",
            "description",
            "catchphrase",
            "secret_talent",
            "fictional_job",
            "fun_fact",
        }
        for trait in TRAITS:
            assert trait not in fields

    def test_interpretation_schema_has_no_archetype_field(self):
        fields = set(PersonalityInterpretation.model_fields.keys())
        assert "archetype" not in fields
        assert "archetype_id" not in fields
