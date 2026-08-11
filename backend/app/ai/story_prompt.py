"""Composable prompt pieces for story generation, kept separate from
app/ai/anthropic_provider.py so each piece is independently
unit-testable and the provider module isn't one giant prompt string.
"""

from app.schemas.profile import CatProfile, CatSignals
from app.schemas.story import STORY_STYLE_LABELS, StoryStyle


def build_system_instructions() -> str:
    return (
        "You are the storyteller voice of MeowVerse AI, a playful app that "
        "turns a cat photo's real computer-vision analysis into a magical "
        "collectible profile and a short illustrated-style story."
    )


def build_story_rules() -> str:
    return (
        "Story rules:\n"
        "- Call the generate_cat_story tool exactly once with a complete, "
        "valid story.\n"
        "- The story must have 3 to 5 short chapters, each under roughly "
        "180 words.\n"
        "- The whole story should read naturally in about 400-700 words "
        "total — do not pad chapters just to hit a length.\n"
        "- Weave the cat's real breed and fur colors, and its generated "
        "personality/magic power/kingdom, naturally into the narrative. "
        "Do NOT simply list the profile fields — show them through what "
        "the cat does and how the world reacts.\n"
        "- Treat the personality, magic power, kingdom, and rarity as "
        "FICTIONAL story elements the cat 'has' within the tale — never "
        "imply they were measured or scientifically detected."
    )


def build_safety_rules() -> str:
    return (
        "Safety rules — the story must always be:\n"
        "- Wholesome, cute, non-violent in tone, and appropriate for all "
        "ages.\n"
        "Never include: sexual content, graphic violence, hate speech, "
        "dangerous instructions, medical or veterinary claims (this is a "
        "playful story, not health advice), or political persuasion.\n"
        "Never imitate copyrighted characters, franchises, or living "
        "authors' distinctive styles — invent original settings."
    )


def build_system_prompt() -> str:
    return "\n\n".join(
        [build_system_instructions(), build_story_rules(), build_safety_rules()]
    )


def build_style_instructions(style: StoryStyle) -> str:
    _, display_name, description = STORY_STYLE_LABELS[style]
    tone_by_style = {
        StoryStyle.MAGICAL_ADVENTURE: (
            "Sparkling, wonder-filled, a little epic — the cat discovers "
            "something magical and rises to a gentle challenge."
        ),
        StoryStyle.COZY_WHOLESOME: (
            "Warm, slow, comforting — small everyday moments treated as "
            "precious. Low stakes, high heart."
        ),
        StoryStyle.FUNNY_CHAOTIC: (
            "Silly, energetic, a little absurd — mishaps and comic timing, "
            "but always good-natured, never mean."
        ),
        StoryStyle.DREAMY_EMOTIONAL: (
            "Soft, wistful, dreamlike — gentle imagery, a touch of quiet "
            "longing that resolves warmly."
        ),
        StoryStyle.FANTASY_QUEST: (
            "Adventurous and quest-shaped — a small journey with a clear "
            "beginning, obstacle, and triumphant (but cozy-scaled) end."
        ),
    }
    return (
        f"Requested style: {display_name} ({description})\n"
        f"Tone guidance: {tone_by_style[style]}"
    )


def build_cat_context(signals: CatSignals, profile: CatProfile) -> str:
    colors_desc = ", ".join(f"{c.name} ({c.percentage:.0f}%)" for c in signals.colors) or "unknown"
    return (
        "Real signals (computer vision — treat as true facts about the "
        "photo):\n"
        f"- Breed: {signals.breed} (confidence: {signals.breed_confidence:.0%})\n"
        f"- Fur colors: {colors_desc}\n\n"
        "Fictional profile (AI-generated — treat as the cat's story-world "
        "identity, not a measured fact):\n"
        f"- Name: {profile.name}\n"
        f"- Title: {profile.title}\n"
        f"- Personality: {profile.personality}\n"
        f"- Magic power: {profile.magic_power}\n"
        f"- Kingdom: {profile.kingdom}\n"
        f"- Favorite activity: {profile.favorite_activity}\n"
        f"- Favorite food: {profile.favorite_food}\n"
        f"- Rarity: {profile.rarity}"
    )


def build_user_prompt(signals: CatSignals, profile: CatProfile, style: StoryStyle) -> str:
    return "\n\n".join(
        [
            build_cat_context(signals, profile),
            build_style_instructions(style),
            "Now call generate_cat_story with a complete story for this cat.",
        ]
    )
