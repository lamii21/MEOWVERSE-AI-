from app.schemas.common import ColorSwatch
from app.schemas.profile import CatProfile, CatSignals
from app.schemas.story import CatStory, StoryStyle
from app.services.story_templates import build_demo_story


def _signals() -> CatSignals:
    return CatSignals(
        breed="Siamese",
        breed_confidence=0.9,
        breed_mode="trained",
        colors=[ColorSwatch(name="cream", hex="#F3E5D8", percentage=70.0)],
        colors_mode="trained",
    )


def _profile() -> CatProfile:
    return CatProfile(
        name="Nova",
        title="Star-Chaser",
        personality="Bold.",
        magic_power="Leaps between sunbeams.",
        kingdom="The Comet Trail",
        favorite_activity="Chasing laser dots",
        favorite_food="Tuna",
        favorite_season="Autumn",
        rarity="Epic",
        description="A tiny explorer.",
    )


def test_same_seed_and_offset_is_deterministic():
    story1 = build_demo_story(_signals(), _profile(), StoryStyle.COZY_WHOLESOME, b"seed-a", 0)
    story2 = build_demo_story(_signals(), _profile(), StoryStyle.COZY_WHOLESOME, b"seed-a", 0)
    assert story1 == story2


def test_different_variant_offset_changes_output():
    """This is what makes "Regenerate" mean something even with no LLM
    configured — the offset (how many stories already exist for this
    analysis+style) shifts which template variant is used."""
    story_v0 = build_demo_story(_signals(), _profile(), StoryStyle.FUNNY_CHAOTIC, b"seed-a", 0)
    story_v1 = build_demo_story(_signals(), _profile(), StoryStyle.FUNNY_CHAOTIC, b"seed-a", 1)
    assert story_v0 != story_v1


def test_output_is_a_valid_catstory_using_real_profile_fields():
    story = build_demo_story(_signals(), _profile(), StoryStyle.FANTASY_QUEST, b"seed-b", 0)

    assert isinstance(story, CatStory)
    assert "Nova" in story.title
    assert 3 <= len(story.chapters) <= 5
    # The story must actually incorporate the real cat, not be generic
    # boilerplate — spot check a couple of real signals/profile fields
    # appear somewhere in the assembled text.
    full_text = " ".join(
        [story.opening, story.ending] + [c.text for c in story.chapters]
    )
    assert "Nova" in full_text
    assert "Siamese" in full_text


def test_every_style_produces_a_valid_story():
    for style in StoryStyle:
        story = build_demo_story(_signals(), _profile(), style, b"seed-c", 0)
        assert isinstance(story, CatStory)
        assert story.moral
        assert story.quote
