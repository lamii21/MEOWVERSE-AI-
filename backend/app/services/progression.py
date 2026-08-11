"""XP and level formula (Phase 10 spec §15-16). These are game
mechanics — flavor for a collection game — never scientific or
statistical claims about anything real.

XP is awarded exclusively server-side, one event at a time, via
`app/services/gamification.py`. Nothing here accepts or trusts a
client-supplied XP value.
"""

import math

# XP awarded per gamification event (spec §15). Keep these as the one
# place these numbers live — everything else imports them.
XP_VALUES: dict[str, int] = {
    "CAT_DISCOVERED": 100,
    "CAT_FAVORITED": 10,
    "STORY_GENERATED": 25,
    "CAT_SHARED": 15,
    "ACHIEVEMENT_UNLOCKED": 50,
}

# Level N requires xp >= LEVEL_XP_STEP * (N-1)^2 — a quadratic curve,
# gentle at first (100 XP for level 2, one cat discovery) and steeper
# later, capped at MAX_LEVEL so progress stays a small, legible number
# rather than growing without bound. Change LEVEL_XP_STEP/MAX_LEVEL
# here to retune the whole curve; nothing else encodes it.
LEVEL_XP_STEP = 100
MAX_LEVEL = 20

# Flavor titles for level bands — purely cosmetic labels, not a
# mechanical tier. Deliberately short (5 bands) rather than one title
# per level, per spec §16 ("do not create hundreds of meaningless
# levels").
_LEVEL_TITLES: list[tuple[int, str]] = [
    (1, "Meow Explorer"),
    (5, "Cat Whisperer"),
    (9, "Whisker Sage"),
    (13, "Star Chaser"),
    (17, "MeowVerse Legend"),
]


def xp_required_for_level(level: int) -> int:
    """Total cumulative XP needed to *reach* `level`. Level 1 requires 0."""
    if level <= 1:
        return 0
    return LEVEL_XP_STEP * (level - 1) ** 2


def level_for_xp(xp: int) -> int:
    """The single source of truth for level: always derived from xp,
    never stored separately, so the two can never drift apart."""
    if xp <= 0:
        return 1
    level = math.isqrt(xp // LEVEL_XP_STEP) + 1
    return min(level, MAX_LEVEL)


def title_for_level(level: int) -> str:
    title = _LEVEL_TITLES[0][1]
    for threshold, name in _LEVEL_TITLES:
        if level >= threshold:
            title = name
    return title


class LevelProgress:
    """Everything the profile/progress UI needs to render an XP bar,
    computed once from a single `xp` value."""

    def __init__(self, xp: int) -> None:
        self.xp = xp
        self.level = level_for_xp(xp)
        self.title = title_for_level(self.level)
        self.xp_for_current_level = xp_required_for_level(self.level)
        self.xp_for_next_level: int | None = (
            None if self.level >= MAX_LEVEL else xp_required_for_level(self.level + 1)
        )
        self.xp_into_level = xp - self.xp_for_current_level
        if self.xp_for_next_level is None:
            self.xp_needed_for_level = 0
            self.progress_ratio = 1.0
        else:
            self.xp_needed_for_level = self.xp_for_next_level - self.xp_for_current_level
            self.progress_ratio = (
                self.xp_into_level / self.xp_needed_for_level
                if self.xp_needed_for_level > 0
                else 1.0
            )
