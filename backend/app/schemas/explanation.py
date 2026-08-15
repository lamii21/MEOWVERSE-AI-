from datetime import datetime
from typing import Literal

from pydantic import BaseModel

ExplanationMode = Literal["trained", "unavailable"]


class CatExplanation(BaseModel):
    """Response for `POST /api/v1/analyses/{id}/explanation`. Only
    fields that are genuinely available are populated — every
    `*_url`/`confidence`/`target_layer` field is `None` when
    `mode == "unavailable"`, never a placeholder value standing in for
    a real one.
    """

    mode: ExplanationMode
    """"trained" only when a real Grad-CAM was computed against the
    actual trained classifier for this exact analysis's stored image.
    "unavailable" for every other case (demo-mode analysis, classifier
    not loaded, image not stored, generation failure) — see `reason`."""
    reason: str | None = None
    """Set only when `mode == "unavailable"` — a short, honest,
    user-facing explanation (e.g. "Grad-CAM requires the trained breed
    model."). Never a stack trace."""
    method: Literal["grad-cam"] | None = None
    target_class: str | None = None
    target_class_index: int | None = None
    confidence: float | None = None
    """Classification confidence for `target_class` — NOT Grad-CAM
    intensity. See CatExplanationModel's docstring for why these are
    kept strictly separate."""
    target_layer: str | None = None
    breed_model_version: str | None = None
    heatmap_url: str | None = None
    overlay_url: str | None = None
    image_width: int | None = None
    image_height: int | None = None
    created_at: datetime | None = None
    cached: bool = False
    """True when this response reused a previously-generated
    explanation (Phase 12 spec §13) rather than running Grad-CAM again
    just now."""
