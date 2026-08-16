import uuid
from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.gamification import GamificationEvent


class PortraitStyle(str, Enum):
    ROYAL = "royal"
    MAGICAL_GUARDIAN = "magical_guardian"
    FANTASY_WIZARD = "fantasy_wizard"
    COSMIC = "cosmic"
    COZY_CAFE = "cozy_cafe"
    STORYBOOK = "storybook"
    WATERCOLOR = "watercolor"
    STICKER = "sticker"
    ANIME = "anime"
    MEDIEVAL = "medieval"


# style -> (emoji, display name, short description) — same tuple shape
# and purpose as Phase 7's STORY_STYLE_LABELS: one small, controlled,
# hand-authored catalog (spec §10: "8-10 polished styles," not 50).
# The actual prompt text lives in app/ai/portrait_prompt.py, not here —
# this is UI-facing metadata only.
PORTRAIT_STYLE_LABELS: dict[PortraitStyle, tuple[str, str, str]] = {
    PortraitStyle.ROYAL: ("👑", "Royal Portrait", "Regal robes, a gilded frame, quiet dignity."),
    PortraitStyle.MAGICAL_GUARDIAN: (
        "🌙",
        "Magical Guardian",
        "Moonlit and mystical, wrapped in soft protective light.",
    ),
    PortraitStyle.FANTASY_WIZARD: (
        "🧙",
        "Fantasy Wizard",
        "A pointed hat, a glowing staff, a hint of spellcraft.",
    ),
    PortraitStyle.COSMIC: ("🪐", "Cosmic Cat", "Adrift among stars, nebulae, and stardust."),
    PortraitStyle.COZY_CAFE: (
        "☕",
        "Cozy Café",
        "A warm window seat, a cup of something hot, soft afternoon light.",
    ),
    PortraitStyle.STORYBOOK: (
        "📚",
        "Storybook Illustration",
        "Hand-drawn and whimsical, like a page from a children's book.",
    ),
    PortraitStyle.WATERCOLOR: (
        "🌸",
        "Watercolor",
        "Soft washes of color and loose, painterly edges.",
    ),
    PortraitStyle.STICKER: (
        "🎀",
        "Cute Sticker",
        "Bold outline, flat colors, a die-cut sticker look.",
    ),
    PortraitStyle.ANIME: ("✨", "Anime-Inspired", "Clean linework and expressive anime shading."),
    PortraitStyle.MEDIEVAL: (
        "🏰",
        "Medieval Portrait",
        "Oil-painted and formal, like an old castle's gallery.",
    ),
}

PortraitStatus = Literal["pending", "succeeded", "failed"]
PortraitErrorCode = Literal[
    "provider_unavailable",
    "timeout",
    "rate_limited",
    "content_rejected",
    "invalid_output",
    "storage_failed",
    "network_error",
    "source_image_unavailable",
    "provider_error",
]


class PortraitGenerateRequest(BaseModel):
    style: PortraitStyle
    # An optional, short, user-supplied creative idea (spec §15) — an
    # artistic preference only, never able to override identity/privacy/
    # system rules (spec §16). Sanitized and bounded server-side in
    # app/ai/portrait_prompt.py, never interpolated unsanitized.
    customization: str | None = Field(default=None, max_length=120)
    # Explicit "Generate Again" (spec §23) — bypasses the reuse-existing
    # lookup and always creates a new row, distinct from the default
    # dedup-on-identical-request behavior.
    force_new: bool = False


class PortraitOut(BaseModel):
    id: uuid.UUID
    analysis_id: uuid.UUID
    style: PortraitStyle
    style_name: str
    style_emoji: str
    status: PortraitStatus
    image_url: str | None
    provider: str
    model: str | None
    prompt_version: str
    error_code: PortraitErrorCode | None
    error_message: str | None
    is_public: bool
    owned: bool
    reused: bool
    """True when this response reused an existing completed generation
    instead of calling the provider again (spec §23) — lets the
    frontend show "already generated" vs. a fresh result without a
    second, separate API shape."""
    created_at: datetime
    completed_at: datetime | None
    gamification: GamificationEvent | None = None


class PortraitListResponse(BaseModel):
    portraits: list[PortraitOut]
