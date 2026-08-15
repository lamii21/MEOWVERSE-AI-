"""The `PersonalityScoringEngine` (Phase 13) — a deterministic,
documented, rule-based algorithm that turns MeowVerse's existing real
signals (breed, breed confidence, fur colors) plus a per-analysis
entropy seed into 8 bounded "AI-inspired" personality trait scores and
a matching archetype.

THIS IS NOT A BEHAVIORAL MEASUREMENT. Nothing in this module claims to
detect a cat's actual personality — see the module-level disclaimer
text in `app/schemas/personality.py` and every prompt/UI surface that
displays these numbers. This file exists to make that claim
*true*: every number here is a documented, reproducible function of
real inputs, never a random guess and never something an LLM invented
(the LLM only ever receives these already-final numbers as creative
inspiration — see `app/services/personality_interpretation_service.py`).

## What legitimately feeds the score, and what deliberately does not

- **`breed_confidence`** (real CV output) modulates *how far* every
  trait is allowed to move from the neutral midpoint (50) — a photo
  the classifier was less sure about gets a personality pulled closer
  to "Balanced" across the board. This is not a claim that uncertain
  photos belong to boring cats; it's honest about the underlying
  signal itself being less distinct.
- **`breed_label`** contributes a small, fixed, fully-documented offset
  per trait (`_BREED_TRAIT_OFFSETS` below) — explicitly a playful,
  "AI-inspired association" with each breed's popular-culture
  reputation (never a scientific claim that breed determines
  personality — spec §7/§33). An unrecognized breed label (demo mode,
  or a future retrained model with different classes) gets an
  all-zero offset — no favoritism for breeds outside the fixed table.
- **`colors`** (real CV output, this specific photo's actual analyzed
  fur palette) contributes two real, computed, documented signals:
  color *diversity* (how many distinct swatches) and the dominant
  swatch's *warmth* (a real RGB-derived heuristic, not a claim that
  "orange cats are confident" — a literal function of that one photo's
  measured pixel values).
- **A per-analysis entropy seed** (`sha256(str(analysis_id))`) supplies
  a small, bounded, fully deterministic offset purely so that two
  different cats of the same breed with similar colors don't produce
  an identical personality — explicitly NOT a real signal, documented
  as existing purely for product variety.
- **Rarity is deliberately excluded from this file entirely** (spec
  §9) — it may only influence the archetype's *decorative theme* and
  story-flavor context downstream, never a trait score.
- **Grad-CAM is deliberately excluded from this file entirely** (spec
  §8) — it explains the breed *prediction*, not behavior; using it
  here would be exactly the "the model looked at the face therefore
  the cat is affectionate" fallacy the spec forbids.

No random numbers anywhere in this module — `random`/`np.random` are
never imported here. The same analysis always produces the same
traits and the same archetype, forever, for a given
`PERSONALITY_ENGINE_VERSION`.
"""

import hashlib
from dataclasses import dataclass

PERSONALITY_ENGINE_VERSION = "1.0"

TRAITS: list[str] = [
    "curiosity",
    "playfulness",
    "calmness",
    "cuddliness",
    "confidence",
    "mischief",
    "elegance",
    "adventurousness",
]

_TRAIT_LABELS: dict[str, str] = {
    "curiosity": "Curious Explorer",
    "playfulness": "Playful Spirit",
    "calmness": "Calm Presence",
    "cuddliness": "Cuddle Enthusiast",
    "confidence": "Confident Charmer",
    "mischief": "Mischief Maker",
    "elegance": "Elegant Soul",
    "adventurousness": "Adventurous Heart",
}

_TRAIT_DESCRIPTIONS: dict[str, str] = {
    "curiosity": "An AI-inspired read on how exploration-driven this cat's visual profile feels.",
    "playfulness": "An AI-inspired read on how playful this cat's visual profile feels.",
    "calmness": "An AI-inspired read on how relaxed this cat's visual profile feels.",
    "cuddliness": "An AI-inspired read on how affectionate this cat's visual profile feels.",
    "confidence": "An AI-inspired read on how self-assured this cat's visual profile feels.",
    "mischief": "An AI-inspired read on how impish this cat's visual profile feels.",
    "elegance": "An AI-inspired read on how graceful this cat's visual profile feels.",
    "adventurousness": "An AI-inspired read on how bold this cat's visual profile feels.",
}


def level_for_score(score: int) -> str:
    """Phase 13 spec §12's exact thresholds — documented here as the
    single source of truth, never re-derived elsewhere."""
    if score <= 20:
        return "Very Low"
    if score <= 40:
        return "Low"
    if score <= 60:
        return "Balanced"
    if score <= 80:
        return "High"
    return "Very High"


# Small, fixed, fully-documented per-breed flavor offsets — a playful
# association with each breed's popular (non-scientific) reputation in
# cat culture, deliberately gentle (max magnitude 10) so no single
# breed dominates a trait outright; combined with color/confidence/
# entropy below, never used alone. Traits not listed for a breed get
# an implicit 0. Breeds not in this table (an unrecognized label, e.g.
# a future retrained model) also get an implicit all-zero offset —
# see `_breed_offsets`.
_BREED_TRAIT_OFFSETS: dict[str, dict[str, int]] = {
    "Abyssinian": {"curiosity": 10, "adventurousness": 8, "playfulness": 5},
    "Bengal": {"playfulness": 9, "mischief": 8, "adventurousness": 9},
    "Birman": {"calmness": 9, "cuddliness": 8, "elegance": 6},
    "Bombay": {"confidence": 9, "elegance": 7, "mischief": 5},
    "British Shorthair": {"calmness": 9, "cuddliness": 6, "confidence": 6},
    "Egyptian Mau": {"adventurousness": 8, "curiosity": 7, "confidence": 6},
    "Maine Coon": {"cuddliness": 9, "calmness": 6, "confidence": 6},
    "Persian": {"elegance": 10, "calmness": 8, "cuddliness": 5},
    "Ragdoll": {"cuddliness": 10, "calmness": 7, "elegance": 4},
    "Russian Blue": {"elegance": 8, "calmness": 6, "curiosity": -4},
    "Siamese": {"curiosity": 8, "playfulness": 7, "mischief": 7},
    "Sphynx": {"mischief": 9, "playfulness": 6, "confidence": 7},
}


def _breed_offsets(breed_label: str) -> dict[str, int]:
    return dict(_BREED_TRAIT_OFFSETS.get(breed_label, {}))


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    value = hex_color.lstrip("#")
    if len(value) != 6:
        return (128, 128, 128)
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))


def _color_offsets(colors: list[dict]) -> dict[str, float]:
    """Two real, computed signals from this specific photo's actual
    analyzed fur palette — never a claim about what any color "means":

    - **Diversity**: `(distinct swatch count - 1) / 2`, clamped to
      `[0, 1]`, scaled to a small +curiosity/+adventurousness nudge —
      a genuinely more visually varied coat gets a slightly more
      "exploratory" flavor. Purely a deterministic function of the
      real palette length, not a behavioral claim about pattern.
    - **Warmth**: `(dominant_red - dominant_blue) / 255`, a standard,
      real RGB-space heuristic in `[-1, 1]`, scaled to a small
      +confidence/+playfulness (warm) or +calmness/+elegance (cool)
      nudge. A literal function of that one photo's measured dominant
      pixel color — not a claim that "orange cats are confident."
    """
    if not colors:
        return {}

    diversity = max(0.0, min(1.0, (len(colors) - 1) / 2))
    dominant = max(colors, key=lambda c: c.get("percentage", 0))
    r, _g, b = _hex_to_rgb(dominant.get("hex", "#808080"))
    warmth = (r - b) / 255  # [-1, 1]

    offsets: dict[str, float] = {
        "curiosity": diversity * 4,
        "adventurousness": diversity * 4,
    }
    if warmth >= 0:
        offsets["confidence"] = offsets.get("confidence", 0) + warmth * 6
        offsets["playfulness"] = offsets.get("playfulness", 0) + warmth * 4
    else:
        offsets["calmness"] = offsets.get("calmness", 0) + (-warmth) * 6
        offsets["elegance"] = offsets.get("elegance", 0) + (-warmth) * 4
    return offsets


def _entropy_offsets(analysis_id: str) -> dict[str, int]:
    """A deterministic, bounded (±8) per-trait offset derived from the
    analysis id alone — explicitly NOT a real signal about the cat.
    Exists purely so two photos that happen to share a breed and
    similar colors don't produce an identical personality; the same
    `analysis_id` always produces the same offsets, forever."""
    digest = hashlib.sha256(analysis_id.encode("utf-8")).digest()
    return {trait: (digest[i] % 17) - 8 for i, trait in enumerate(TRAITS)}


def compute_traits(
    *, analysis_id: str, breed_label: str, breed_confidence: float, colors: list[dict]
) -> dict[str, dict]:
    """The whole `PersonalityScoringEngine`. Returns
    `{trait: {"score": int, "level": str, "label": str, "description": str}}`
    for all 8 `TRAITS`, every value fully determined by the arguments —
    call it twice with the same arguments and get byte-identical
    output, forever (for this `PERSONALITY_ENGINE_VERSION`).
    """
    breed_offsets = _breed_offsets(breed_label)
    color_offsets = _color_offsets(colors)
    entropy_offsets = _entropy_offsets(analysis_id)
    # Confidence dampens (never redirects) every offset — see module
    # docstring. 0.7 floor so even a very uncertain prediction still
    # carries *some* signal, never a completely flat 50-for-everything.
    confidence_scale = 0.7 + 0.3 * max(0.0, min(1.0, breed_confidence))

    result: dict[str, dict] = {}
    for trait in TRAITS:
        total_offset = (
            breed_offsets.get(trait, 0)
            + color_offsets.get(trait, 0)
            + entropy_offsets.get(trait, 0)
        )
        raw = 50 + confidence_scale * total_offset
        score = max(0, min(100, round(raw)))
        result[trait] = {
            "score": score,
            "level": level_for_score(score),
            "label": _TRAIT_LABELS[trait],
            "description": _TRAIT_DESCRIPTIONS[trait],
        }
    return result


@dataclass(frozen=True)
class PersonalityArchetype:
    id: str
    name: str
    emoji: str
    short_description: str
    long_description: str
    theme_token: str
    centroid: dict[str, int]
    """Target trait-score profile this archetype represents — archetype
    *selection* is nearest-centroid matching against a cat's real
    computed trait scores (see `select_archetype`), never chosen by an
    LLM and never random."""


# 10 archetypes (spec §10: "approximately 8-12"). Each centroid lists
# only its emphasized traits away from the 50 midpoint; every other
# trait implicitly sits at 50 in the centroid, so distance is
# dominated by whichever traits an archetype actually cares about.
ARCHETYPES: list[PersonalityArchetype] = [
    PersonalityArchetype(
        id="dreamy_explorer",
        name="Dreamy Explorer",
        emoji="🌙",
        short_description="Half moonlight, half mischief.",
        long_description=(
            "A wandering spirit who treats every unopened door as an invitation. "
            "Equal parts curious and unhurried about getting there."
        ),
        theme_token="dreamy",
        centroid={"curiosity": 85, "adventurousness": 80, "calmness": 60},
    ),
    PersonalityArchetype(
        id="cozy_cuddlebug",
        name="Cozy Cuddlebug",
        emoji="🎀",
        short_description="Professionally soft, unprofessionally clingy.",
        long_description=(
            "Lives for warm laps and slow blinks. Considers personal space a "
            "concept invented by people who have never met a cuddlebug."
        ),
        theme_token="cozy",
        centroid={"cuddliness": 88, "calmness": 78, "playfulness": 45},
    ),
    PersonalityArchetype(
        id="magical_mischief_maker",
        name="Magical Mischief Maker",
        emoji="🧙",
        short_description="Chaos, but make it charming.",
        long_description=(
            "Knocks things off tables with the confidence of someone who has "
            "never once faced consequences. Probably hasn't."
        ),
        theme_token="mischief",
        centroid={"mischief": 88, "playfulness": 82, "confidence": 60},
    ),
    PersonalityArchetype(
        id="tiny_royal",
        name="Tiny Royal",
        emoji="👑",
        short_description="Runs the household. Has always run the household.",
        long_description=(
            "Carries themselves like visiting nobility. Everything in this home "
            "belongs to them; you're simply allowed to live here too."
        ),
        theme_token="royal",
        centroid={"elegance": 88, "confidence": 82, "calmness": 58},
    ),
    PersonalityArchetype(
        id="gentle_soul",
        name="Gentle Soul",
        emoji="🌸",
        short_description="A soft heart in a soft coat.",
        long_description=(
            "Quiet, warm, and easy to love. Prefers sunbeams, slow mornings, "
            "and being near their favorite person without making a fuss about it."
        ),
        theme_token="gentle",
        centroid={"calmness": 85, "cuddliness": 72, "elegance": 58},
    ),
    PersonalityArchetype(
        id="chaos_bean",
        name="Chaos Bean",
        emoji="⚡",
        short_description="Zero to feral in one heartbeat.",
        long_description=(
            "Operates on a schedule only they understand, usually starting at "
            "3am. Every room is a racetrack; every object is a toy."
        ),
        theme_token="chaos",
        centroid={"mischief": 85, "playfulness": 85, "curiosity": 68, "calmness": 25},
    ),
    PersonalityArchetype(
        id="mystic_whisker",
        name="Mystic Whisker",
        emoji="🔮",
        short_description="Knows things. Won't say how.",
        long_description=(
            "Watches from doorways with an unreadable expression, as if privy "
            "to secrets the rest of the household will never understand."
        ),
        theme_token="mystic",
        centroid={"elegance": 74, "curiosity": 74, "calmness": 68, "confidence": 58},
    ),
    PersonalityArchetype(
        id="calm_wanderer",
        name="Calm Wanderer",
        emoji="🌊",
        short_description="Unbothered, in motion, at peace.",
        long_description=(
            "Explores at their own unhurried pace, entirely unbothered by "
            "whatever anyone else thinks the schedule should be."
        ),
        theme_token="calm",
        centroid={"calmness": 78, "adventurousness": 64, "curiosity": 58},
    ),
    PersonalityArchetype(
        id="confident_adventurer",
        name="Confident Adventurer",
        emoji="🏔️",
        short_description="Fears nothing. Questions less.",
        long_description=(
            "Walks into unfamiliar rooms like they own the deed. The bravest "
            "resident of any household, by a wide margin."
        ),
        theme_token="bold",
        centroid={"confidence": 85, "adventurousness": 78, "playfulness": 55},
    ),
    PersonalityArchetype(
        id="velvet_charmer",
        name="Velvet Charmer",
        emoji="💫",
        short_description="Effortlessly the main character.",
        long_description=(
            "Turns every entrance into an event. Playful, polished, and never "
            "quite doing anything by accident."
        ),
        theme_token="velvet",
        centroid={"elegance": 78, "playfulness": 72, "confidence": 60},
    ),
]

_ARCHETYPES_BY_ID = {a.id: a for a in ARCHETYPES}


def select_archetype(traits: dict[str, dict]) -> PersonalityArchetype:
    """Nearest-centroid classification in 8-dimensional trait space —
    deterministic (fixed centroids, real trait scores, no randomness),
    never chosen by an LLM. Ties resolve to whichever archetype appears
    first in `ARCHETYPES` (stable, deterministic — `min()` keeps the
    first minimum found)."""

    def distance(archetype: PersonalityArchetype) -> float:
        return sum(
            (traits[trait]["score"] - archetype.centroid.get(trait, 50)) ** 2 for trait in TRAITS
        )

    return min(ARCHETYPES, key=distance)


def get_archetype(archetype_id: str) -> PersonalityArchetype | None:
    return _ARCHETYPES_BY_ID.get(archetype_id)
