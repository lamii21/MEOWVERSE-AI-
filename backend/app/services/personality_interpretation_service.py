"""The creative layer on top of the deterministic
`PersonalityScoringEngine` (Phase 13) — mirrors
`app/services/profile_service.py`'s exact fallback contract: try the
configured `LLMProvider`, fall back to a deterministic local template
on any failure (no key, timeout, API error, invalid schema). Never
raises, never blocks the personality endpoint.

The demo pool is keyed **per archetype** (not one generic pool) so
even offline/no-API-key personalities feel tailored rather than
interchangeable — spec §27's "do NOT make every cat sound identical"
applies just as much to the honest fallback path as to the real one.
"""

import logging

from app.ai.providers import LLMProviderError, get_llm_provider
from app.schemas.personality import InterpretationMode, PersonalityInterpretation
from app.schemas.profile import CatSignals
from app.services.personality_scoring import PersonalityArchetype

logger = logging.getLogger(__name__)

INTERPRETATION_VERSION = "1.0"

_DEMO_INTERPRETATIONS: dict[str, PersonalityInterpretation] = {
    "dreamy_explorer": PersonalityInterpretation(
        headline="A wanderer with moonlight in their eyes",
        description=(
            "Every unopened door is an invitation. This one moves through the "
            "world unhurried, chasing whatever catches their attention next."
        ),
        catchphrase="I heard a sound three rooms away and I must investigate.",
        secret_talent="Finding the one dust mote worth staring at for twenty minutes.",
        fictional_job="Chief Field Researcher, Department of Unexplained Noises.",
        fun_fact="Has a personal theory about where the sun goes at night.",
    ),
    "cozy_cuddlebug": PersonalityInterpretation(
        headline="Professionally soft, unprofessionally clingy",
        description=(
            "Warm laps are a birthright, not a privilege. This one considers "
            "personal space a concept invented by people who've never met them."
        ),
        catchphrase="You were about to get up. I have decided you were not.",
        secret_talent="Turning any lap into a permanent legal residence.",
        fictional_job="Director of Blanket Affairs.",
        fun_fact="Has never once regretted a nap.",
    ),
    "magical_mischief_maker": PersonalityInterpretation(
        headline="Chaos, but make it charming",
        description=(
            "Knocks things off tables with the confidence of someone who has "
            "never once faced consequences. Statistically, they probably haven't."
        ),
        catchphrase="That was already broken. I improved it.",
        secret_talent="Turning absolutely nothing into a dramatic event.",
        fictional_job="Chief Inspector of Suspicious Cardboard Boxes.",
        fun_fact="Once stared at a wall for eleven minutes for reasons unknown.",
    ),
    "tiny_royal": PersonalityInterpretation(
        headline="Runs the household. Has always run the household",
        description=(
            "Carries themselves like visiting nobility. Everything in this "
            "home belongs to them; you are simply permitted to live here too."
        ),
        catchphrase="I was definitely not on the table five seconds ago.",
        secret_talent="Making an empty box look like a throne.",
        fictional_job="Minister of Household Affairs (self-appointed).",
        fun_fact="Has never apologized for anything, on principle.",
    ),
    "gentle_soul": PersonalityInterpretation(
        headline="A soft heart in a soft coat",
        description=(
            "Quiet, warm, and easy to love. Prefers sunbeams, slow mornings, "
            "and being near their favorite person without making a fuss."
        ),
        catchphrase="I would simply like to be near you. That's all.",
        secret_talent="Making any room feel calmer just by being in it.",
        fictional_job="Resident Sunbeam Consultant.",
        fun_fact="Purrs before they even realize they're doing it.",
    ),
    "chaos_bean": PersonalityInterpretation(
        headline="Zero to feral in one heartbeat",
        description=(
            "Operates on a schedule only they understand, usually starting at "
            "3am. Every room is a racetrack; every object is a toy."
        ),
        catchphrase="It is 3am. This is the correct time for zoomies.",
        secret_talent="Achieving full sprint speed from a dead sleep.",
        fictional_job="Head of Nighttime Operations.",
        fun_fact="Has never met a paper bag they didn't immediately attack.",
    ),
    "mystic_whisker": PersonalityInterpretation(
        headline="Knows things. Won't say how",
        description=(
            "Watches from doorways with an unreadable expression, as if privy "
            "to secrets the rest of the household will never understand."
        ),
        catchphrase="I sense you are about to open the treat cupboard.",
        secret_talent="Staring at an empty corner with deep, unexplained focus.",
        fictional_job="Keeper of Unspoken Household Knowledge.",
        fun_fact="Always seems to know five minutes before dinner time.",
    ),
    "calm_wanderer": PersonalityInterpretation(
        headline="Unbothered, in motion, at peace",
        description=(
            "Explores at their own unhurried pace, entirely unbothered by "
            "whatever anyone else thinks the schedule should be."
        ),
        catchphrase="We will get there. There is no rush.",
        secret_talent="Making a slow stroll across the room look like a ceremony.",
        fictional_job="Ambassador of Taking It Easy.",
        fun_fact="Has a favorite windowsill for every hour of daylight.",
    ),
    "confident_adventurer": PersonalityInterpretation(
        headline="Fears nothing. Questions less",
        description=(
            "Walks into unfamiliar rooms like they own the deed — the "
            "bravest resident of any household, by a wide margin."
        ),
        catchphrase="New box. Mine now.",
        secret_talent="Making every new environment feel instantly conquered.",
        fictional_job="Senior Vice President of Fearless Exploration.",
        fun_fact="Has never backed down from a vacuum cleaner. Not once.",
    ),
    "velvet_charmer": PersonalityInterpretation(
        headline="Effortlessly the main character",
        description=(
            "Turns every entrance into an event. Playful, polished, and "
            "never quite doing anything by accident."
        ),
        catchphrase="Yes, I meant to do that. I always mean to do that.",
        secret_talent="Making a simple stretch look like a runway moment.",
        fictional_job="Creative Director, Department of Looking Fabulous.",
        fun_fact="Has strong, well-documented opinions about lighting.",
    ),
}

_DEFAULT_DEMO_ARCHETYPE_ID = "gentle_soul"


def _demo_interpretation(archetype_id: str) -> PersonalityInterpretation:
    return _DEMO_INTERPRETATIONS.get(
        archetype_id, _DEMO_INTERPRETATIONS[_DEFAULT_DEMO_ARCHETYPE_ID]
    )


async def generate_interpretation(
    *,
    signals: CatSignals,
    archetype: PersonalityArchetype,
    trait_levels: dict[str, str],
    rarity: str,
) -> tuple[PersonalityInterpretation, InterpretationMode, str | None]:
    """Returns `(interpretation, mode, model)`. `mode` is `"generated"`
    only when a real LLM call actually produced this specific text —
    never set to that just because a provider is configured; a
    provider failure still yields `"demo"` honestly."""
    provider = get_llm_provider()
    if provider.is_available:
        try:
            interpretation = await provider.generate_personality_interpretation(
                signals,
                archetype_name=archetype.name,
                archetype_short_description=archetype.short_description,
                trait_levels=trait_levels,
                rarity=rarity,
            )
            return interpretation, "generated", "anthropic"
        except LLMProviderError as exc:
            # Safe to log: LLMProviderError messages only ever contain the
            # exception type/validation summary, never the API key.
            logger.warning(
                "LLM personality interpretation failed, falling back to demo: %s", exc
            )

    return _demo_interpretation(archetype.id), "demo", "demo"
