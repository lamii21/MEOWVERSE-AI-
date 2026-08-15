import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

PersonalityLevel = Literal["Very Low", "Low", "Balanced", "High", "Very High"]
InterpretationMode = Literal["generated", "demo"]


class PersonalityTraitScore(BaseModel):
    """One trait's result from the deterministic
    `PersonalityScoringEngine` (app/services/personality_scoring.py) —
    `score` is never shown to the user as a raw percentage implying a
    measurement ("87% curious"); the frontend always pairs it with the
    "AI-inspired" framing. See that module's docstring for exactly how
    `score` is computed and why `level` is a discrete label, not a
    disguised precision claim."""

    score: int = Field(ge=0, le=100)
    level: PersonalityLevel
    label: str
    description: str


class PersonalityArchetypeOut(BaseModel):
    id: str
    name: str
    emoji: str
    short_description: str
    long_description: str
    theme_token: str
    """A CSS/design-token identifier (e.g. `"dreamy"`) the frontend maps
    to a color treatment — never a raw hex/arbitrary color invented
    outside the existing design system."""


class PersonalityInterpretation(BaseModel):
    """The creative, LLM-authored (or demo-fallback) layer on top of the
    deterministic scores — same honesty contract as `CatProfile`/
    `CatStory`: structurally has NO fields for trait scores or the
    archetype itself, so generated text can never overwrite or restate
    those as if re-measuring them. Every field is playful, bounded, and
    never a scientific/behavioral claim.
    """

    headline: str = Field(max_length=80, description="A short, punchy personality headline")
    description: str = Field(max_length=400, description="1-2 sentence playful personality read")
    catchphrase: str = Field(max_length=140, description="Something this cat would 'say'")
    secret_talent: str = Field(max_length=140)
    fictional_job: str = Field(max_length=100)
    fun_fact: str = Field(max_length=200)


class CatPersonalityResponse(BaseModel):
    """`GET /api/v1/analyses/{id}/personality`'s full response —
    deliberately bundles the deterministic structured result and its
    (possibly demo-mode) creative interpretation together, since the
    frontend always renders them as one experience. The two halves stay
    independently cacheable/regenerable server-side (see
    ARCHITECTURE.md's Phase 13 section) even though they travel
    together here.
    """

    id: uuid.UUID
    analysis_id: uuid.UUID
    personality_engine_version: str
    archetype: PersonalityArchetypeOut
    traits: dict[str, PersonalityTraitScore]
    created_at: datetime

    interpretation_mode: InterpretationMode
    interpretation_model: str | None
    interpretation_version: str
    interpretation: PersonalityInterpretation
    interpretation_created_at: datetime
    interpretation_cached: bool

    disclaimer: str = (
        "Personality is an AI-inspired interpretation of visual signals, "
        "not a scientific assessment of your cat's behavior."
    )


class PersonalityRegenerateRequest(BaseModel):
    """Empty today — a placeholder body so the endpoint can grow
    (e.g. a tone/style hint) without a breaking route change, same
    convention as `StoryRequest`."""
