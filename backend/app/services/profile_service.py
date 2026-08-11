import hashlib
import logging
from typing import Literal

from app.ai.providers import LLMProviderError, get_llm_provider
from app.schemas.profile import CatProfile, CatSignals

logger = logging.getLogger(__name__)

ProfileMode = Literal["demo", "generated"]

# Fixed demo pool, used whenever no LLM provider is configured or the
# real call fails after retrying (see generate_cat_profile below).
# Picked deterministically from the image bytes, same pattern as the
# CV demo fallbacks in analysis_service.py, so a given upload always
# yields the same demo profile.
_DEMO_PROFILES: list[CatProfile] = [
    CatProfile(
        name="Biscuit",
        title="Keeper of Sunbeams",
        personality="A warm, unhurried soul who treats every windowsill like a throne.",
        magic_power="Can locate the single warmest spot in any room within seconds.",
        kingdom="The Sunlit Archives",
        favorite_activity="Supervising naps from a great height",
        favorite_food="Anything that smells like it was meant for someone else",
        favorite_season="Summer",
        rarity="Uncommon",
        description="A gentle spirit who believes most problems can wait until after a nap.",
    ),
    CatProfile(
        name="Whisker Vex",
        title="Duke of the Midnight Zoomies",
        personality="Chaotic and endlessly curious, prone to sudden bursts of pure energy.",
        magic_power="Teleportation, but only ever from one room to a slightly louder one.",
        kingdom="The Hallway Speedway",
        favorite_activity="Knocking things off tables with scientific precision",
        favorite_food="Whatever was just declared off-limits",
        favorite_season="Autumn",
        rarity="Rare",
        description="Runs on a schedule only they understand, usually starting at 3am.",
    ),
    CatProfile(
        name="Professor Marmalade",
        title="Archivist of Forgotten Boxes",
        personality="Dignified, observant, and quietly convinced they run the household.",
        magic_power="Can appear in any cardboard box regardless of size or logic.",
        kingdom="The Cardboard Citadel",
        favorite_activity="Watching the door for reasons never fully explained",
        favorite_food="A small, ceremonious portion of something fancy",
        favorite_season="Winter",
        rarity="Epic",
        description="Carries themselves like royalty in exile, patiently awaiting restoration.",
    ),
    CatProfile(
        name="Clementine",
        title="Herald of the Feather Wand",
        personality="Playful and a little dramatic, with a flair for the theatrical pounce.",
        magic_power="Can summon a toy from anywhere by staring meaningfully at a human.",
        kingdom="The Living Room Colosseum",
        favorite_activity="Ambushing ankles from behind the couch",
        favorite_food="Anything crunchy enough to announce itself",
        favorite_season="Spring",
        rarity="Common",
        description="Treats every day like the opening act of a very small, very fluffy show.",
    ),
    CatProfile(
        name="Sable",
        title="Whisperer of the Air Vents",
        personality="Mysterious and independent, seen mostly at dawn and dusk.",
        magic_power="Can vanish mid-sentence and reappear somewhere entirely unexpected.",
        kingdom="The Shadow Between Rooms",
        favorite_activity="Patrolling the perimeter of absolutely nothing",
        favorite_food="Whatever arrives at 5:58am, not 6:00am",
        favorite_season="Autumn",
        rarity="Legendary",
        description="Answers to no one, keeps their own counsel, occasionally allows affection.",
    ),
]


def _demo_profile(image_bytes: bytes) -> CatProfile:
    digest = hashlib.sha256(image_bytes).digest()
    return _DEMO_PROFILES[digest[2] % len(_DEMO_PROFILES)]


async def generate_cat_profile(
    signals: CatSignals, image_bytes: bytes
) -> tuple[CatProfile, ProfileMode]:
    """Generates the creative profile layer on top of real CV signals.

    Uses the configured LLM provider when available; falls back to a
    deterministic local demo profile on any failure (no key, timeout,
    API error, or a response that never validates) — this must never
    raise and never block the analysis endpoint from returning.
    """
    provider = get_llm_provider()
    if provider.is_available:
        try:
            profile = await provider.generate_profile(signals)
            return profile, "generated"
        except LLMProviderError as exc:
            # Safe to log: LLMProviderError messages only ever contain the
            # exception type/validation summary, never request headers or
            # the API key itself.
            logger.warning("LLM profile generation failed, falling back to demo: %s", exc)

    return _demo_profile(image_bytes), "demo"
