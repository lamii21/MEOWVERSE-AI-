import io
import logging
import uuid

from PIL import Image, UnidentifiedImageError
from sqlalchemy.ext.asyncio import AsyncSession

from app.ml.breed_classifier import GRAD_CAM_TARGET_LAYER, get_breed_classifier
from app.ml.heatmap_visualization import render_heatmap_and_overlay
from app.repositories import explanation_repository
from app.repositories.analysis_repository import get_owned_analysis, get_public_analysis
from app.schemas.explanation import CatExplanation
from app.storage import get_image_storage

logger = logging.getLogger(__name__)


class SourceAnalysisNotVisibleError(Exception):
    """The source analysis doesn't exist, or isn't visible to this
    caller (not public, and not owned by them) — surfaced by the API
    layer as 404. Same anti-enumeration principle as every other
    ownership check in this codebase: never distinguishes "doesn't
    exist" from "exists but isn't yours."""


class InvalidTargetClassError(Exception):
    """`target_class` was explicitly requested but isn't one of the
    classifier's known breeds — surfaced as 422, not a 500."""


def _unavailable(reason: str) -> CatExplanation:
    return CatExplanation(mode="unavailable", reason=reason)


def _row_to_explanation(row, *, cached: bool) -> CatExplanation:
    return CatExplanation(
        mode="trained",
        method="grad-cam",
        target_class=row.target_class,
        target_class_index=row.target_class_index,
        confidence=row.confidence,
        target_layer=row.target_layer,
        breed_model_version=row.breed_model_version,
        heatmap_url=row.heatmap_url,
        overlay_url=row.overlay_url,
        image_width=row.image_width,
        image_height=row.image_height,
        created_at=row.created_at,
        cached=cached,
    )


async def get_explanation(
    db: AsyncSession,
    analysis_id: uuid.UUID,
    *,
    viewer_user_id: uuid.UUID | None,
    target_class: str | None = None,
) -> CatExplanation:
    """The one place Grad-CAM generation is orchestrated (Phase 12 spec
    §31: on-demand only, never during analysis). Pipeline: resolve +
    authorize the source analysis → refuse anything not genuinely
    `breed_mode == "trained"` (never a fake explanation for a demo
    prediction) → default `target_class` to the breed actually shown to
    the user (never silently re-predict a *different* breed with
    today's model — spec §5/§2) → check the cache → on a miss, load the
    real stored photo, run real Grad-CAM, render + persist the
    heatmap/overlay, cache the result.

    Every failure path returns `mode: "unavailable"` with an honest
    `reason` rather than raising — except the two genuinely
    exceptional cases (`SourceAnalysisNotVisibleError` for 404,
    `InvalidTargetClassError` for 422), which the API layer maps to
    real HTTP error codes.
    """
    source = await get_public_analysis(db, analysis_id)
    if source is None and viewer_user_id is not None:
        source = await get_owned_analysis(db, analysis_id, viewer_user_id)
    if source is None:
        raise SourceAnalysisNotVisibleError(str(analysis_id))

    if source.breed_mode != "trained":
        return _unavailable("Grad-CAM requires the trained breed model.")

    classifier = get_breed_classifier()
    if not classifier.is_available:
        return _unavailable("The breed classification model is not currently loaded.")

    resolved_target_class = target_class if target_class is not None else source.breed_label
    if resolved_target_class not in classifier.class_names:
        raise InvalidTargetClassError(resolved_target_class)

    cached_row = await explanation_repository.get_cached(
        db, source.id, resolved_target_class, classifier.version
    )
    if cached_row is not None:
        return _row_to_explanation(cached_row, cached=True)

    if not source.image_url:
        return _unavailable("The original photo isn't available for this cat.")

    storage = get_image_storage()
    image_bytes = await storage.load(source.image_url)
    if image_bytes is None:
        return _unavailable("Couldn't load the original photo.")

    try:
        image = Image.open(io.BytesIO(image_bytes))
        image.load()
    except (UnidentifiedImageError, OSError):
        logger.warning("Stored photo for analysis %s is unreadable", source.id, exc_info=True)
        return _unavailable("Couldn't read the stored photo.")

    try:
        result = classifier.explain(image, target_class_label=resolved_target_class)
    except Exception:
        logger.warning("Grad-CAM generation failed for analysis %s", source.id, exc_info=True)
        return _unavailable("Couldn't generate a visual explanation right now.")

    heatmap_image, overlay_image = render_heatmap_and_overlay(image, result.heatmap)
    heatmap_url, overlay_url = await _store_explanation_images(
        storage, source.id, resolved_target_class, heatmap_image, overlay_image
    )

    row = await explanation_repository.create(
        db,
        analysis_id=source.id,
        target_layer=GRAD_CAM_TARGET_LAYER,
        target_class=result.target_class_label,
        target_class_index=result.target_class_index,
        confidence=result.confidence,
        breed_model_version=classifier.version,
        heatmap_url=heatmap_url,
        overlay_url=overlay_url,
        image_width=result.image_width,
        image_height=result.image_height,
    )
    return _row_to_explanation(row, cached=False)


async def _store_explanation_images(
    storage,
    analysis_id: uuid.UUID,
    target_class: str,
    heatmap_image: Image.Image,
    overlay_image: Image.Image,
) -> tuple[str | None, str | None]:
    """Best-effort, same philosophy as the original photo's storage
    (Phase 9): a save failure here doesn't fail the whole explanation —
    the caller still gets real confidence/target_class metadata, it
    just won't have images to render. Reuses the existing
    `ImageStorageProvider`, never a second, unrelated storage system."""
    if not storage.is_available:
        return None, None

    slug = "".join(c if c.isalnum() else "-" for c in target_class.lower())
    heatmap_url = overlay_url = None
    try:
        heatmap_buffer = io.BytesIO()
        heatmap_image.save(heatmap_buffer, format="PNG")
        heatmap_url = await storage.save(
            heatmap_buffer.getvalue(), key=f"{analysis_id}-{slug}-heatmap", content_type="image/png"
        )

        overlay_buffer = io.BytesIO()
        overlay_image.save(overlay_buffer, format="PNG")
        overlay_url = await storage.save(
            overlay_buffer.getvalue(), key=f"{analysis_id}-{slug}-overlay", content_type="image/png"
        )
    except Exception:
        logger.warning(
            "Failed to store explanation images for analysis %s", analysis_id, exc_info=True
        )

    return heatmap_url, overlay_url
