import uuid
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import ColorSwatch
from app.schemas.profile import CatProfile, ProfileModeLiteral

__all__ = ["AnalysisResult", "BreedPrediction", "ColorSwatch"]


class BreedPrediction(BaseModel):
    label: str
    confidence: float = Field(ge=0.0, le=1.0)


class AnalysisResult(BaseModel):
    """Structured result of the full pipeline: real CV signals plus the
    AI-generated creative layer on top of them.

    Each signal carries its own `*_mode`, rather than one result-wide
    mode, because signals go real independently across phases (breed
    in Phase 4, fur color in Phase 5, ...). Conflating them into a
    single flag would mean a `"trained"` result could still contain a
    demo-mode fur palette presented as if it were real — exactly what
    this product is not supposed to do. See ARCHITECTURE.md section 4
    and PROJECT_STATUS.md for the demo-mode contract.

    `profile_mode` deliberately uses different values (`"demo" |
    "generated"`) than `breed_mode`/`colors_mode` (`"demo" | "trained"`)
    — the profile is never a "prediction," real or otherwise, so it
    must never be labeled with vocabulary that implies it is one.

    `id` is set only if persistence succeeded (Phase 7) — the analyses
    endpoint stays usable even if the database is unreachable, it just
    can't offer story generation for that particular analysis (which
    needs a stable id to reference). Never `None` when the DB is up.
    """

    id: uuid.UUID | None = None
    detected: bool
    breed: BreedPrediction | None = None
    breed_mode: Literal["demo", "trained"]
    colors: list[ColorSwatch] = Field(default_factory=list)
    colors_mode: Literal["demo", "trained"]
    embedding_available: bool = False
    profile: CatProfile
    profile_mode: ProfileModeLiteral
    # Phase 8: whether the Cat Card has been explicitly shared — see
    # POST /api/v1/analyses/{id}/share. Always False for a freshly
    # created analysis; sharing is always a separate, explicit act.
    is_public: bool = False
