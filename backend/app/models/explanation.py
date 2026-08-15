import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CatExplanationModel(Base):
    """One generated Grad-CAM explanation for one (analysis, target
    class) pair, on-demand (Phase 12 spec §31 — never generated
    automatically during analysis, only when a user opens "Why this
    breed?"). Never created for a `cat_analyses` row whose
    `breed_mode` wasn't `"trained"` at analysis time — see
    `explanation_service.py`.

    **Caching key**: unique on `(analysis_id, target_class,
    breed_model_version)`. Requesting the same analysis + same target
    class again, with the *same* classifier version, reuses this row
    instead of recomputing Grad-CAM. If the classifier is later
    retrained (`BreedClassifier.version` bumped), a lookup with the new
    version simply won't find this row — the old explanation becomes
    naturally unreachable (never presented as if it came from the
    current model) without needing an explicit invalidation step.

    `confidence` here is intentionally the *classification* confidence
    for `target_class` (the model's own softmax probability) —
    genuinely different from Grad-CAM intensity, which lives only in
    the heatmap pixels themselves, never as a stored scalar (there is
    no single "Grad-CAM confidence number" — that would be exactly the
    kind of fabricated metric the spec forbids).
    """

    __tablename__ = "cat_explanations"
    __table_args__ = (
        UniqueConstraint(
            "analysis_id",
            "target_class",
            "breed_model_version",
            name="uq_cat_explanation_cache_key",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("cat_analyses.id", ondelete="CASCADE"), index=True
    )

    method: Mapped[str] = mapped_column(String(30), default="grad-cam", server_default="grad-cam")
    target_layer: Mapped[str] = mapped_column(String(50))
    """Human-readable identifier of the layer Grad-CAM hooked into —
    e.g. `"features.12"` — recorded for auditability (spec §14), not a
    live reference."""
    target_class: Mapped[str] = mapped_column(String(60))
    target_class_index: Mapped[int] = mapped_column(Integer)
    confidence: Mapped[float] = mapped_column(Float)
    breed_model_version: Mapped[str] = mapped_column(String(20))

    heatmap_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    overlay_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    image_width: Mapped[int] = mapped_column(Integer)
    image_height: Mapped[int] = mapped_column(Integer)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
