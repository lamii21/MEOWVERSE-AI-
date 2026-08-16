from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class AchievementDefinition:
    key: str
    emoji: str
    label: str
    description: str
    # Given the same `stats` dict `collection_service.get_user_stats`
    # builds (real counts from the DB — never demo data, since
    # unclaimed/guest analyses have no user_id and so never enter these
    # queries at all), returns whether the achievement should be unlocked.
    is_unlocked: Callable[[dict], bool]
    # (current, target) for a progress bar — e.g. (3, 5) for "3 of 5
    # cats discovered." Threshold/boolean achievements (has the user
    # ever gotten a Rare+ cat, at all) report (1, 1) once satisfied and
    # (0, 1) otherwise, so every achievement can share one progress-bar
    # renderer on the frontend.
    progress: Callable[[dict], tuple[int, int]]


# Phase 9 introduced first_meow/cat_explorer/collector/rainbow_collector/
# legendary_hunter with these exact `key`s, already unlocked in the DB
# for existing users — keys are never renamed (that would silently
# "re-lock" something a user already earned). Phase 10 renames only the
# *display* label/emoji on a few of them to match the spec's naming
# ("Cozy Collector", "Royal Encounter", "Color Collector"), which
# changes nothing about who has unlocked what.
ACHIEVEMENTS: list[AchievementDefinition] = [
    AchievementDefinition(
        key="first_meow",
        emoji="🐾",
        label="First Paw",
        description="Discover your first cat.",
        is_unlocked=lambda stats: stats["total_cats"] >= 1,
        progress=lambda stats: (min(stats["total_cats"], 1), 1),
    ),
    AchievementDefinition(
        key="cat_explorer",
        emoji="🌸",
        label="Cozy Collector",
        description="Discover 5 cats.",
        is_unlocked=lambda stats: stats["total_cats"] >= 5,
        progress=lambda stats: (min(stats["total_cats"], 5), 5),
    ),
    AchievementDefinition(
        key="collector",
        emoji="💎",
        label="Collector",
        description="Discover 15 cats.",
        is_unlocked=lambda stats: stats["total_cats"] >= 15,
        progress=lambda stats: (min(stats["total_cats"], 15), 15),
    ),
    AchievementDefinition(
        key="rare_hunter",
        emoji="💎",
        label="Rare Hunter",
        description="Discover a Rare cat (or rarer).",
        is_unlocked=lambda stats: stats["rare_count"] >= 1,
        progress=lambda stats: (min(stats["rare_count"], 1), 1),
    ),
    AchievementDefinition(
        key="legendary_hunter",
        emoji="👑",
        label="Royal Encounter",
        description="Discover a Legendary cat (or rarer).",
        is_unlocked=lambda stats: stats["legendary_count"] >= 1,
        progress=lambda stats: (min(stats["legendary_count"], 1), 1),
    ),
    AchievementDefinition(
        key="rainbow_collector",
        emoji="🌈",
        label="Color Collector",
        description="Discover cats spanning 5 distinct fur colors.",
        is_unlocked=lambda stats: stats["distinct_colors"] >= 5,
        progress=lambda stats: (min(stats["distinct_colors"], 5), 5),
    ),
    AchievementDefinition(
        key="storyteller",
        emoji="📖",
        label="Storyteller",
        description="Generate stories for 5 different cats.",
        is_unlocked=lambda stats: stats["distinct_story_cats"] >= 5,
        progress=lambda stats: (min(stats["distinct_story_cats"], 5), 5),
    ),
    AchievementDefinition(
        key="dream_keeper",
        emoji="🌙",
        label="Dream Keeper",
        description="Generate a Dreamy & Emotional story.",
        is_unlocked=lambda stats: stats["has_dreamy_story"],
        progress=lambda stats: (1 if stats["has_dreamy_story"] else 0, 1),
    ),
    AchievementDefinition(
        key="cat_home",
        emoji="🏡",
        label="Cat Home",
        description="Save your first favorite.",
        is_unlocked=lambda stats: stats["favorites_count"] >= 1,
        progress=lambda stats: (min(stats["favorites_count"], 1), 1),
    ),
    AchievementDefinition(
        key="first_portrait",
        emoji="🎨",
        label="First Portrait",
        description="Create your first AI cat portrait.",
        is_unlocked=lambda stats: stats["total_portraits"] >= 1,
        progress=lambda stats: (min(stats["total_portraits"], 1), 1),
    ),
    AchievementDefinition(
        key="style_collector",
        emoji="🖼️",
        label="Style Collector",
        description="Create portraits in 5 different styles.",
        is_unlocked=lambda stats: stats["distinct_portrait_styles"] >= 5,
        progress=lambda stats: (min(stats["distinct_portrait_styles"], 5), 5),
    ),
]

ACHIEVEMENTS_BY_KEY = {a.key: a for a in ACHIEVEMENTS}
