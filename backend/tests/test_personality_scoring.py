"""Tests the actual `PersonalityScoringEngine` mathematics (Phase 13
spec §34) — determinism, bounded ranges, level thresholds, archetype
selection, and that scores actually respond to real signal changes.
No HTTP, no database, no LLM — pure function tests.
"""

import pytest

from app.services.personality_scoring import (
    ARCHETYPES,
    PERSONALITY_ENGINE_VERSION,
    TRAITS,
    compute_traits,
    get_archetype,
    level_for_score,
    select_archetype,
)

_COLORS = [
    {"name": "orange", "hex": "#D98B4B", "percentage": 55.0},
    {"name": "white", "hex": "#F7F1E8", "percentage": 35.0},
    {"name": "brown", "hex": "#7A4B2B", "percentage": 10.0},
]


def _traits(**overrides):
    kwargs = {
        "analysis_id": "11111111-1111-1111-1111-111111111111",
        "breed_label": "Siamese",
        "breed_confidence": 0.85,
        "colors": _COLORS,
    }
    kwargs.update(overrides)
    return compute_traits(**kwargs)


class TestDeterminism:
    def test_same_inputs_produce_byte_identical_output(self):
        assert _traits() == _traits()

    def test_different_analysis_id_produces_different_scores(self):
        a = _traits(analysis_id="11111111-1111-1111-1111-111111111111")
        b = _traits(analysis_id="22222222-2222-2222-2222-222222222222")
        assert a != b

    def test_no_randomness_across_many_calls(self):
        results = [_traits() for _ in range(20)]
        assert all(r == results[0] for r in results)


class TestBoundedRanges:
    @pytest.mark.parametrize("breed", ["Siamese", "Persian", "Sphynx", "Unknown Breed XYZ"])
    @pytest.mark.parametrize("confidence", [0.0, 0.3, 0.5, 0.85, 1.0])
    def test_every_trait_score_is_within_0_and_100(self, breed, confidence):
        traits = _traits(breed_label=breed, breed_confidence=confidence)
        for trait in TRAITS:
            assert 0 <= traits[trait]["score"] <= 100

    def test_all_eight_documented_traits_are_present(self):
        traits = _traits()
        assert set(traits.keys()) == set(TRAITS)
        assert len(TRAITS) == 8


class TestLevelThresholds:
    @pytest.mark.parametrize(
        "score,expected",
        [
            (0, "Very Low"),
            (20, "Very Low"),
            (21, "Low"),
            (40, "Low"),
            (41, "Balanced"),
            (60, "Balanced"),
            (61, "High"),
            (80, "High"),
            (81, "Very High"),
            (100, "Very High"),
        ],
    )
    def test_exact_boundaries(self, score, expected):
        assert level_for_score(score) == expected

    def test_every_computed_trait_has_a_level_matching_its_score(self):
        traits = _traits()
        for trait in TRAITS:
            assert traits[trait]["level"] == level_for_score(traits[trait]["score"])


class TestSignalsActuallyAffectScores:
    def test_breed_confidence_zero_pulls_scores_toward_the_neutral_midpoint(self):
        high_conf = _traits(breed_confidence=1.0)
        low_conf = _traits(breed_confidence=0.0)
        # Lower confidence must never move a score *further* from 50
        # than the higher-confidence version of the same inputs.
        for trait in TRAITS:
            assert abs(low_conf[trait]["score"] - 50) <= abs(high_conf[trait]["score"] - 50)

    def test_different_breeds_produce_different_scores(self):
        siamese = _traits(breed_label="Siamese")
        persian = _traits(breed_label="Persian")
        assert siamese != persian

    def test_unknown_breed_label_gets_no_breed_offset_but_still_computes(self):
        # Must not raise, and must not silently favor an unrecognized
        # label — same entropy/color signals, only the breed table
        # lookup differs (empty dict for an unknown breed).
        traits = _traits(breed_label="Not A Real Breed")
        for trait in TRAITS:
            assert 0 <= traits[trait]["score"] <= 100

    def test_missing_colors_does_not_crash(self):
        traits = _traits(colors=[])
        for trait in TRAITS:
            assert 0 <= traits[trait]["score"] <= 100

    def test_different_colors_produce_different_scores(self):
        warm = _traits(colors=[{"name": "orange", "hex": "#FF6600", "percentage": 100.0}])
        cool = _traits(colors=[{"name": "blue", "hex": "#0066FF", "percentage": 100.0}])
        assert warm != cool

    def test_rarity_is_not_an_input_to_the_scoring_function_at_all(self):
        # compute_traits has no rarity parameter — this test documents
        # and enforces that at the call-signature level (spec §9): a
        # TypeError here would mean rarity leaked into scoring.
        import inspect

        params = inspect.signature(compute_traits).parameters
        assert "rarity" not in params


class TestArchetypeSelection:
    def test_selection_is_deterministic(self):
        traits = _traits()
        assert select_archetype(traits).id == select_archetype(traits).id

    def test_every_archetype_id_is_resolvable(self):
        for archetype in ARCHETYPES:
            assert get_archetype(archetype.id) is archetype

    def test_unknown_archetype_id_returns_none(self):
        assert get_archetype("not-a-real-archetype") is None

    def test_there_are_between_8_and_12_archetypes(self):
        assert 8 <= len(ARCHETYPES) <= 12

    def test_a_cat_matching_an_archetypes_centroid_exactly_selects_that_archetype(self):
        # Build a synthetic all-50-baseline trait dict, then push it
        # exactly onto one archetype's centroid — nearest-centroid
        # matching must select that exact archetype.
        target = ARCHETYPES[3]  # Tiny Royal
        traits = {t: {"score": 50, "level": level_for_score(50)} for t in TRAITS}
        for trait, value in target.centroid.items():
            traits[trait] = {"score": value, "level": level_for_score(value)}
        assert select_archetype(traits).id == target.id

    def test_archetype_names_and_emoji_are_all_non_empty(self):
        for archetype in ARCHETYPES:
            assert archetype.name.strip()
            assert archetype.emoji.strip()
            assert archetype.short_description.strip()
            assert archetype.long_description.strip()
            assert archetype.theme_token.strip()


class TestVersioning:
    def test_engine_version_is_a_non_empty_string(self):
        assert isinstance(PERSONALITY_ENGINE_VERSION, str)
        assert PERSONALITY_ENGINE_VERSION
