from app.ai.story_prompt import (
    build_cat_context,
    build_safety_rules,
    build_story_rules,
    build_style_instructions,
    build_system_instructions,
    build_system_prompt,
    build_user_prompt,
)
from app.schemas.common import ColorSwatch
from app.schemas.profile import CatProfile, CatSignals
from app.schemas.story import StoryStyle


def _signals() -> CatSignals:
    return CatSignals(
        breed="British Shorthair",
        breed_confidence=0.95,
        breed_mode="trained",
        colors=[ColorSwatch(name="blue", hex="#726C85", percentage=60.0)],
        colors_mode="trained",
    )


def _profile() -> CatProfile:
    return CatProfile(
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


def test_each_prompt_piece_is_a_nonempty_string():
    assert isinstance(build_system_instructions(), str) and build_system_instructions()
    assert isinstance(build_story_rules(), str) and build_story_rules()
    assert isinstance(build_safety_rules(), str) and build_safety_rules()


def test_safety_rules_mention_required_prohibitions():
    rules = build_safety_rules().lower()
    for term in ["sexual", "violence", "hate", "dangerous", "medical", "political"]:
        assert term in rules, f"safety rules should mention {term!r}"


def test_safety_rules_prohibit_copyrighted_characters():
    rules = build_safety_rules().lower()
    assert "copyrighted" in rules


def test_system_prompt_combines_all_three_pieces():
    system = build_system_prompt()
    assert build_system_instructions() in system
    assert build_story_rules() in system
    assert build_safety_rules() in system


def test_style_instructions_differ_per_style():
    instructions = {style: build_style_instructions(style) for style in StoryStyle}
    # Every style must produce distinct guidance — otherwise the style
    # selector wouldn't actually affect anything.
    assert len(set(instructions.values())) == len(StoryStyle)


def test_style_instructions_name_the_style():
    from app.schemas.story import STORY_STYLE_LABELS

    for style in StoryStyle:
        _, display_name, _ = STORY_STYLE_LABELS[style]
        assert display_name in build_style_instructions(style)


def test_cat_context_includes_real_signals_and_profile_fields():
    context = build_cat_context(_signals(), _profile())
    assert "British Shorthair" in context
    assert "blue" in context
    assert "Nova" in context
    assert "Star-Chaser" in context
    assert "Comet Trail" in context


def test_cat_context_labels_real_vs_fictional():
    context = build_cat_context(_signals(), _profile()).lower()
    assert "real signals" in context or "computer vision" in context
    assert "fictional" in context or "ai-generated" in context


def test_user_prompt_includes_context_and_style_and_instruction_to_call_tool():
    prompt = build_user_prompt(_signals(), _profile(), StoryStyle.MAGICAL_ADVENTURE)
    assert "Nova" in prompt
    assert "Magical Adventure" in prompt
    assert "generate_cat_story" in prompt
