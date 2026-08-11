"""Deterministic offline story templates — used whenever no LLM
provider is configured or a real call fails after retrying (see
story_service.py). These are NOT a single generic paragraph: each
style has multiple structural variants, and every variant interpolates
the cat's actual breed, colors, and generated profile rather than
returning static boilerplate. Always marked `story_mode="demo"` by the
caller — never presented as if it came from Anthropic.
"""

import hashlib

from app.schemas.profile import CatProfile, CatSignals
from app.schemas.story import CatStory, StoryChapter, StoryStyle

_STYLE_OPENERS: dict[StoryStyle, list[str]] = {
    StoryStyle.MAGICAL_ADVENTURE: [
        "The first sparkle appeared just after sunset, hovering by {name}'s whiskers "
        "like it had been waiting all day for permission to shine.",
        "Nobody in the house saw the door to the {kingdom} open — nobody except {name}.",
    ],
    StoryStyle.COZY_WHOLESOME: [
        "The best part of {name}'s day was always the quiet hour before dinner, when "
        "the light turned gold and the whole world seemed to slow down.",
        "{name} had a very important routine, and it began, as always, with finding "
        "the warmest patch of sun in the house.",
    ],
    StoryStyle.FUNNY_CHAOTIC: [
        "It is a truth universally acknowledged that {name} had absolutely no plan, "
        "and yet somehow a plan kept happening anyway.",
        "The trouble started, as it usually did, with a box that was clearly too "
        "small and a cat who was clearly undeterred.",
    ],
    StoryStyle.DREAMY_EMOTIONAL: [
        "In the hush between waking and sleeping, {name} sometimes wandered somewhere "
        "the daylight couldn't quite follow.",
        "There is a particular kind of quiet that only exists at 3am, and {name} knew "
        "it better than anyone.",
    ],
    StoryStyle.FANTASY_QUEST: [
        "Long before the humans woke, {name} had already accepted the quest — not "
        "that anyone had exactly asked.",
        "The map was really just a sunbeam on the floor, but to {name} it pointed "
        "somewhere important.",
    ],
}

_STYLE_ENDINGS: dict[StoryStyle, list[str]] = {
    StoryStyle.MAGICAL_ADVENTURE: [
        "And when the sparkle finally faded, {name} curled up satisfied — after all, "
        "{kingdom} would still be there tomorrow.",
        "{name} returned home with nothing anyone could see, and everything that mattered.",
    ],
    StoryStyle.COZY_WHOLESOME: [
        "By the time the sun had fully set, {name} was exactly where a cat should "
        "be: comfortable, content, and thoroughly unbothered.",
        "It hadn't been an exciting day. It had been a good one, which {name} "
        "privately felt was better.",
    ],
    StoryStyle.FUNNY_CHAOTIC: [
        "In the end, nothing was actually accomplished, but {name} considered it a "
        "resounding success anyway.",
        "The box was, it turned out, exactly the right size after all — for at "
        "least one more minute.",
    ],
    StoryStyle.DREAMY_EMOTIONAL: [
        "{name} blinked awake slowly, already forgetting the details, keeping only "
        "the feeling.",
        "Somewhere between one breath and the next, the quiet folded {name} back "
        "into an ordinary, lovely evening.",
    ],
    StoryStyle.FANTASY_QUEST: [
        "The quest was complete, more or less, and {name} accepted the day's small "
        "victory with appropriate dignity.",
        "{kingdom} was safe for one more night, thanks to a hero nobody else had noticed.",
    ],
}

_MORALS: dict[StoryStyle, str] = {
    StoryStyle.MAGICAL_ADVENTURE: "Even small magic is still magic.",
    StoryStyle.COZY_WHOLESOME: "The quiet moments are the ones worth keeping.",
    StoryStyle.FUNNY_CHAOTIC: "A little chaos never hurt anybody (much).",
    StoryStyle.DREAMY_EMOTIONAL: "Some of the best places are the ones we only visit in dreams.",
    StoryStyle.FANTASY_QUEST: "Every hero's journey starts with a single, confident step.",
}

_QUOTES: dict[StoryStyle, str] = {
    # Plain text, no literal quote marks — the frontend adds its own
    # presentational curly quotes around this field when it renders it.
    StoryStyle.MAGICAL_ADVENTURE: "Wonder is just the world, noticed properly.",
    StoryStyle.COZY_WHOLESOME: "Home is wherever the sunniest spot happens to be.",
    StoryStyle.FUNNY_CHAOTIC: "Plans are optional. Enthusiasm is not.",
    StoryStyle.DREAMY_EMOTIONAL: "Not all who nap are idle.",
    StoryStyle.FANTASY_QUEST: "Fortune favors the well-rested.",
}

STORY_STYLE_TITLE_WORD: dict[StoryStyle, str] = {
    StoryStyle.MAGICAL_ADVENTURE: "Evening Sparkle",
    StoryStyle.COZY_WHOLESOME: "Golden Hour",
    StoryStyle.FUNNY_CHAOTIC: "Cardboard Incident",
    StoryStyle.DREAMY_EMOTIONAL: "Quiet Hour",
    StoryStyle.FANTASY_QUEST: "Small Quest",
}


def _variant_index(image_hash: bytes, offset: int, variant_offset: int, pool_size: int) -> int:
    return (image_hash[offset] + variant_offset) % pool_size


def build_demo_story(
    signals: CatSignals,
    profile: CatProfile,
    style: StoryStyle,
    seed_bytes: bytes,
    variant_offset: int = 0,
) -> CatStory:
    """`seed_bytes` makes the *first* demo story for a given
    analysis+style reproducible (e.g. `str(analysis_id).encode()`).
    `variant_offset` (e.g. how many stories already exist for this
    analysis+style) shifts which template variant is picked, so
    "Regenerate" visibly does something even in demo mode instead of
    silently returning the exact same story every time.
    """
    digest = hashlib.sha256(seed_bytes + style.value.encode()).digest()
    opener = _STYLE_OPENERS[style][
        _variant_index(digest, 0, variant_offset, len(_STYLE_OPENERS[style]))
    ]
    ending = _STYLE_ENDINGS[style][
        _variant_index(digest, 1, variant_offset, len(_STYLE_ENDINGS[style]))
    ]

    ctx = {
        "name": profile.name,
        "breed": signals.breed,
        "kingdom": profile.kingdom,
        "power": profile.magic_power,
        "activity": profile.favorite_activity,
        "food": profile.favorite_food,
    }

    chapters = [
        StoryChapter(
            chapter_number=1,
            title="The Beginning",
            text=opener.format(**ctx)
            + f" As a {ctx['breed']}, {ctx['name']} moved with a certainty that "
            f"only comes from knowing exactly who you are.",
        ),
        StoryChapter(
            chapter_number=2,
            title="The Discovery",
            text=f"It started with {ctx['activity'].lower()}, as it so often did. "
            f"{ctx['name']} paused, ears forward, sensing that today might not be "
            f"an entirely ordinary day.",
        ),
        StoryChapter(
            chapter_number=3,
            title="A Little Magic",
            text=f"{ctx['name']}'s power — {ctx['power'].lower()} — flickered to life, "
            f"the way it always did when it mattered. In {ctx['kingdom']}, even small "
            f"magic gets noticed.",
        ),
        StoryChapter(
            chapter_number=4,
            title="The Resolution",
            text=ending.format(**ctx)
            + f" Later, there would be {ctx['food'].lower()} — there was always "
            f"time for that.",
        ),
    ]

    return CatStory(
        title=f"{profile.name} and the {STORY_STYLE_TITLE_WORD[style]}",
        subtitle=profile.title,
        opening=opener.format(**ctx),
        chapters=chapters,
        ending=ending.format(**ctx),
        moral=_MORALS[style],
        quote=_QUOTES[style],
    )
