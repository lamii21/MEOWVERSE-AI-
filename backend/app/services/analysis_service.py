import hashlib
import io
import logging
import uuid

from PIL import Image, UnidentifiedImageError
from sqlalchemy.ext.asyncio import AsyncSession

from app.ml.breed_classifier import get_breed_classifier
from app.ml.fur_color import get_fur_color_analyzer
from app.repositories.analysis_repository import save_analysis
from app.schemas.analysis import AnalysisResult, BreedPrediction, ColorSwatch
from app.schemas.profile import CatSignals
from app.services.profile_service import generate_cat_profile
from app.storage import get_image_storage

logger = logging.getLogger(__name__)

MIN_DIMENSION_PX = 64


class InvalidImageError(ValueError):
    pass


# Fixed demo pools, used only as fallbacks when the corresponding real
# model isn't available (missing weights/deps — see app/ml/). Picked
# deterministically from the image bytes so the same upload always
# yields the same demo result. Breed and colors fall back independently.
_DEMO_BREEDS = [
    ("Domestic Shorthair", 0.74),
    ("British Shorthair", 0.91),
    ("Maine Coon", 0.83),
    ("Siamese", 0.88),
    ("Bengal", 0.79),
]
_DEMO_PALETTES = [
    [("cream", "#F3E5D8", 48.0), ("caramel", "#C9A98C", 34.0), ("charcoal", "#4B3A2F", 18.0)],
    [("gray", "#B8B8B8", 62.0), ("white", "#F5F5F5", 30.0), ("black", "#2B2B2B", 8.0)],
    [("orange", "#D98B4B", 55.0), ("white", "#F7F1E8", 35.0), ("brown", "#7A4B2B", 10.0)],
]


def _load_and_validate_image(image_bytes: bytes) -> Image.Image:
    try:
        image = Image.open(io.BytesIO(image_bytes))
        image.verify()
        # verify() leaves the file unusable for further ops; reopen.
        image = Image.open(io.BytesIO(image_bytes))
    except (UnidentifiedImageError, OSError) as exc:
        raise InvalidImageError("MeowVerse needs a valid image.") from exc

    if image.width < MIN_DIMENSION_PX or image.height < MIN_DIMENSION_PX:
        raise InvalidImageError(
            f"Image is too small — minimum {MIN_DIMENSION_PX}x{MIN_DIMENSION_PX}px."
        )
    return image


def _demo_breed(image_bytes: bytes) -> BreedPrediction:
    digest = hashlib.sha256(image_bytes).digest()
    breed_label, confidence = _DEMO_BREEDS[digest[0] % len(_DEMO_BREEDS)]
    return BreedPrediction(label=breed_label, confidence=confidence)


def _demo_palette(image_bytes: bytes) -> list[ColorSwatch]:
    digest = hashlib.sha256(image_bytes).digest()
    palette = _DEMO_PALETTES[digest[1] % len(_DEMO_PALETTES)]
    return [ColorSwatch(name=name, hex=hex_, percentage=pct) for name, hex_, pct in palette]


async def _try_store_image(image_bytes: bytes, content_type: str) -> str | None:
    """Best-effort, same philosophy as analysis persistence below: a
    storage failure (unwritable disk, future network storage outage)
    must never fail the analyze request — it only means the photo won't
    survive a refresh, which is honestly reflected by `image_url` being
    `None` rather than the request failing."""
    try:
        storage = get_image_storage()
        if not storage.is_available:
            return None
        return await storage.save(image_bytes, key=str(uuid.uuid4()), content_type=content_type)
    except Exception:
        logger.warning("Failed to persist cat photo — continuing without image_url", exc_info=True)
        return None


async def analyze_image(
    image_bytes: bytes,
    content_type: str,
    db: AsyncSession,
    user_id: uuid.UUID | None = None,
) -> AnalysisResult:
    """Runs the real breed classifier and fur-color analyzer when each is
    available (falling back to clearly-labeled deterministic demo
    results otherwise — the two are independent, one can be real while
    the other is still demo), then generates the AI creative profile
    layer on top of those real signals.

    Persists the result (needed as of Phase 7 so a story can reference
    it by id) on a best-effort basis: if the database is unreachable,
    this still returns a complete, usable AnalysisResult with `id=None`
    rather than failing the whole request — the analyze/breed/color/
    profile pipeline must not become hard-dependent on the database
    just because story generation now wants one.

    Phase 9: if `user_id` is provided (the request carried a valid
    session), the analysis is auto-owned by that user immediately — no
    separate "Save" step needed, matching the spec's "authenticated
    analyses should be persisted reliably" requirement. A guest
    (`user_id=None`) gets an unowned row that stays invisible to
    everyone until explicitly claimed later via POST .../save.
    """
    image = _load_and_validate_image(image_bytes)

    classifier = get_breed_classifier()
    if classifier.is_available:
        breed = classifier.predict(image)
        breed_mode = "trained"
    else:
        breed = _demo_breed(image_bytes)
        breed_mode = "demo"

    color_analyzer = get_fur_color_analyzer()
    if color_analyzer.is_available:
        colors = color_analyzer.predict(image)
        colors_mode = "trained"
    else:
        colors = _demo_palette(image_bytes)
        colors_mode = "demo"

    signals = CatSignals(
        breed=breed.label,
        breed_confidence=breed.confidence,
        breed_mode=breed_mode,
        colors=colors,
        colors_mode=colors_mode,
    )
    profile, profile_mode = await generate_cat_profile(signals, image_bytes)

    result = AnalysisResult(
        detected=True,
        breed=breed,
        breed_mode=breed_mode,
        colors=colors,
        colors_mode=colors_mode,
        embedding_available=False,
        profile=profile,
        profile_mode=profile_mode,
    )

    image_url = await _try_store_image(image_bytes, content_type)

    try:
        row = await save_analysis(db, result, user_id=user_id, image_url=image_url)
        result.id = row.id
        result.owned = row.user_id is not None
        result.image_url = row.image_url
        result.is_favorite = row.is_favorite
    except Exception:
        # Deliberately broad: this is a best-effort side channel, not the
        # core pipeline. A DB outage can surface as many exception types
        # (connection errors, timeouts, driver-specific errors) that
        # don't all inherit from SQLAlchemyError — none of them should
        # ever take down the analyze endpoint.
        logger.warning("Failed to persist analysis — continuing without an id", exc_info=True)
        try:
            await db.rollback()
        except Exception:
            pass

    return result
