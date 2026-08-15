"""Composable prompt pieces for personality creative interpretation
(Phase 13) — same reasoning as `app/ai/story_prompt.py`: kept separate
from the provider module so each piece is independently testable.

The LLM is given the ALREADY-FINAL, already-computed trait scores and
archetype (from `app/services/personality_scoring.py`) purely as
creative inspiration — the system prompt is explicit that it must
never restate them as if it measured them, and the response schema
(`PersonalityInterpretation`) structurally has no fields for scores or
an archetype choice, so there's nothing for the model to overwrite
even if it tried.
"""

from app.schemas.profile import CatSignals


def build_system_prompt() -> str:
    return (
        "You are the personality voice of MeowVerse AI, a playful app that "
        "turns a cat photo's real computer-vision analysis into a fun, "
        "collectible personality profile.\n\n"
        "You will be given an ALREADY-COMPUTED personality archetype and a "
        "set of ALREADY-COMPUTED trait levels — produced by a deterministic "
        "scoring algorithm, not by you. Your job is to write ONLY the "
        "creative, playful text that brings that already-decided result to "
        "life. You must NOT invent a different archetype, restate the trait "
        "scores as numbers, or claim to have measured or detected anything "
        "yourself.\n\n"
        "Rules:\n"
        "- Call the generate_personality_interpretation tool exactly once "
        "with a complete, valid interpretation.\n"
        "- Never claim this is a scientific or behavioral measurement — "
        "everything you write is explicitly fictional, playful flavor text.\n"
        "- Never make medical, veterinary, or health claims of any kind.\n"
        "- Keep the tone cute, warm, and a little funny — never mean, "
        "scary, or mocking. Avoid copyrighted characters or real brand "
        "names.\n"
        "- Make the writing feel specific to THIS cat's real breed and "
        "colors, not generic boilerplate that could describe any cat."
    )


def build_user_prompt(
    *,
    signals: CatSignals,
    archetype_name: str,
    archetype_short_description: str,
    trait_levels: dict[str, str],
    rarity: str,
) -> str:
    colors_desc = ", ".join(f"{c.name} ({c.percentage:.0f}%)" for c in signals.colors) or "unknown"
    traits_desc = ", ".join(f"{trait}: {level}" for trait, level in trait_levels.items())
    return (
        "Real signals (computer vision — treat as true facts about the photo):\n"
        f"- Breed: {signals.breed} (confidence: {signals.breed_confidence:.0%})\n"
        f"- Fur colors: {colors_desc}\n\n"
        "Already-computed personality result (from a deterministic scoring "
        "algorithm — do not change, restate as numbers, or contradict):\n"
        f"- Archetype: {archetype_name} — {archetype_short_description}\n"
        f"- Trait levels: {traits_desc}\n\n"
        "Fictional flavor (from the cat's existing collectible profile, for "
        f"story-world context only): rarity tier {rarity}\n\n"
        "Now call generate_personality_interpretation with a complete, "
        "specific, cute interpretation for THIS cat."
    )
