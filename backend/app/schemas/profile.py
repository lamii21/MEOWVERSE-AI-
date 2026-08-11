from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import ColorSwatch

Season = Literal["Spring", "Summer", "Autumn", "Winter"]
Rarity = Literal["Common", "Uncommon", "Rare", "Epic", "Legendary", "Mythical"]
ProfileModeLiteral = Literal["demo", "generated"]


class CatSignals(BaseModel):
    """Real signals passed to the LLM as creative inspiration. Every
    field here is either a genuine CV output or explicitly optional and
    unset - the LLM is never given room to invent a "fact" this schema
    doesn't already carry as a real measurement.
    """

    breed: str
    breed_confidence: float = Field(ge=0.0, le=1.0)
    breed_mode: Literal["demo", "trained"]
    colors: list[ColorSwatch]
    colors_mode: Literal["demo", "trained"]
    # Reserved for future signals (Phase "Advanced AI" in the original
    # roadmap) - not produced by any pipeline yet, always None today.
    mood: str | None = None
    age_estimate: str | None = None


class CatProfile(BaseModel):
    """Strictly-validated LLM output. Deliberately has NO fields for
    breed/colors/confidence - the schema itself makes it structurally
    impossible for generated content to overwrite a real CV result,
    not just a prompt instruction hoping the model complies.

    Every field here is playful, AI-generated content - never
    presented as a scientific or veterinary claim (see
    app/ai/anthropic_provider.py system prompt).
    """

    name: str = Field(max_length=40, description="A whimsical name for the cat")
    title: str = Field(max_length=60, description="A magical title, e.g. 'Keeper of Sunbeams'")
    personality: str = Field(max_length=280, description="1-2 sentence playful personality read")
    magic_power: str = Field(max_length=80, description="A short, fun magical ability")
    kingdom: str = Field(max_length=60, description="A whimsical cat kingdom/realm name")
    favorite_activity: str = Field(max_length=80)
    favorite_food: str = Field(max_length=80)
    favorite_season: Season
    rarity: Rarity
    description: str = Field(max_length=400, description="Short flavor-text description")
