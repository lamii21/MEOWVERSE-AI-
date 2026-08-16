import hashlib
import io
import logging
import uuid

from PIL import Image, UnidentifiedImageError
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import portrait_prompt
from app.ai.providers import ImageGenerationError, get_image_generation_provider
from app.models.analysis import CatAnalysisModel
from app.models.portrait import CatPortraitModel
from app.repositories import portrait_repository
from app.repositories.analysis_repository import get_owned_analysis, get_public_analysis
from app.schemas.portrait import PORTRAIT_STYLE_LABELS, PortraitOut, PortraitStyle
from app.services.personality_scoring import compute_traits, select_archetype
from app.storage import get_image_storage

logger = logging.getLogger(__name__)

_MIN_OUTPUT_DIMENSION = 256
_MAX_OUTPUT_DIMENSION = 4096


class SourceAnalysisNotVisibleError(Exception):
    """The source analysis doesn't exist, or isn't visible to this
    caller — surfaced by the API layer as 404. Same anti-enumeration
    principle as every other ownership check in this codebase."""


class PortraitNotVisibleError(Exception):
    """The portrait doesn't exist, or isn't visible to this caller —
    surfaced by the API layer as 404."""


def _generation_identity_hash(
    *, analysis_id: uuid.UUID, style: PortraitStyle, customization: str | None, provider: str
) -> str:
    """The full "would this be a duplicate generation" identity (spec
    §23): analysis + style + prompt version + sanitized customization +
    provider/model selection. Two requests that would build the
    identical prompt against the identical provider hash identically,
    so `find_reusable` can serve the existing result instead of paying
    for a new provider call."""
    sanitized = portrait_prompt.sanitize_customization(customization) or ""
    raw = f"{analysis_id}|{style.value}|{portrait_prompt.PROMPT_VERSION}|{sanitized}|{provider}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _archetype_id_for(analysis: CatAnalysisModel) -> str | None:
    """Reuses the exact Phase 13 deterministic scoring engine to learn
    which archetype this cat's real signals already select — never a
    second, separate personality computation, and never the creative
    LLM interpretation (only the archetype id is needed here, purely
    for atmosphere — spec §13/§38). Never persists a CatPersonalityModel
    row; this is a pure, cheap, stateless computation."""
    try:
        traits = compute_traits(
            analysis_id=str(analysis.id),
            breed_label=analysis.breed_label,
            breed_confidence=analysis.breed_confidence,
            colors=analysis.colors,
        )
        return select_archetype(traits).id
    except Exception:
        logger.warning("Could not compute personality archetype for atmosphere", exc_info=True)
        return None


def _to_response(row: CatPortraitModel, *, owned: bool, reused: bool) -> PortraitOut:
    style = PortraitStyle(row.style_id)
    emoji, name, _short = PORTRAIT_STYLE_LABELS[style]
    return PortraitOut(
        id=row.id,
        analysis_id=row.analysis_id,
        style=style,
        style_name=name,
        style_emoji=emoji,
        status=row.status,  # type: ignore[arg-type]
        image_url=row.image_url,
        provider=row.provider,
        model=row.model,
        prompt_version=row.prompt_version,
        error_code=row.error_code,  # type: ignore[arg-type]
        error_message=row.error_message,
        is_public=row.is_public,
        owned=owned,
        reused=reused,
        created_at=row.created_at,
        completed_at=row.completed_at,
    )


async def _resolve_visible_source(
    db: AsyncSession, analysis_id: uuid.UUID, viewer_user_id: uuid.UUID | None
) -> CatAnalysisModel:
    source = await get_public_analysis(db, analysis_id)
    if source is None and viewer_user_id is not None:
        source = await get_owned_analysis(db, analysis_id, viewer_user_id)
    if source is None:
        raise SourceAnalysisNotVisibleError(str(analysis_id))
    return source


async def list_portraits(
    db: AsyncSession, analysis_id: uuid.UUID, *, viewer_user_id: uuid.UUID | None
) -> list[PortraitOut]:
    """`GET /api/v1/analyses/{id}/portraits` — same "public OR owned"
    visibility rule as every other analysis-scoped endpoint. A guest
    viewing a public cat sees only its already-generated, public
    portraits; the owner sees all of theirs regardless of `is_public`.
    """
    source = await _resolve_visible_source(db, analysis_id, viewer_user_id)
    rows = await portrait_repository.list_for_analysis(db, source.id)

    owned = viewer_user_id is not None and source.user_id == viewer_user_id
    if owned:
        visible_rows = rows
    else:
        visible_rows = [r for r in rows if r.is_public and r.status == "succeeded"]
    return [_to_response(r, owned=owned, reused=False) for r in visible_rows]


async def generate_portrait(
    db: AsyncSession,
    analysis_id: uuid.UUID,
    *,
    owner_user_id: uuid.UUID,
    style: PortraitStyle,
    customization: str | None,
    force_new: bool,
) -> PortraitOut:
    """The one place portrait generation is orchestrated (spec §2/§28).
    Owner-only (spec §9: "a public viewer must NOT be able to trigger
    expensive generation for someone else's cat") — unlike personality's
    read endpoint, there is no "public OR owned" variant of this call at
    all, because generation is *always* a mutating, cost-bearing action.

    Pipeline: resolve + authorize the source analysis (owner only) →
    compute the generation identity hash → reuse an existing succeeded
    result if one matches and `force_new` wasn't requested (spec §23) →
    otherwise: build the deterministic prompt, load the real original
    photo (never Grad-CAM, never the similarity embedding, never a
    previous portrait — spec §7/§39/§40), call the provider, validate
    its output, store it, and persist the result — success or honest
    failure, never fabricated, never raised as a generic 500 for an
    expected failure mode.
    """
    source = await get_owned_analysis(db, analysis_id, owner_user_id)
    if source is None:
        raise SourceAnalysisNotVisibleError(str(analysis_id))

    provider = get_image_generation_provider()
    provider_name = "openai" if provider.is_available else "demo"
    identity_hash = _generation_identity_hash(
        analysis_id=source.id, style=style, customization=customization, provider=provider_name
    )

    if not force_new:
        existing = await portrait_repository.find_reusable(
            db, analysis_id=source.id, generation_identity_hash=identity_hash
        )
        if existing is not None:
            return _to_response(existing, owned=True, reused=True)

    row = await portrait_repository.create_pending(
        db,
        analysis_id=source.id,
        user_id=owner_user_id,
        style_id=style.value,
        customization=portrait_prompt.sanitize_customization(customization),
        generation_identity_hash=identity_hash,
        provider=provider_name,
        prompt_version=portrait_prompt.PROMPT_VERSION,
    )

    if not provider.is_available:
        row = await portrait_repository.mark_failed(
            db,
            row,
            error_code="provider_unavailable",
            error_message=(
                "Portrait generation is currently unavailable — no image-generation "
                "provider is configured in this environment."
            ),
        )
        return _to_response(row, owned=True, reused=False)

    if not source.image_url:
        row = await portrait_repository.mark_failed(
            db,
            row,
            error_code="source_image_unavailable",
            error_message="The original photo isn't available for this cat.",
        )
        return _to_response(row, owned=True, reused=False)

    storage = get_image_storage()
    source_bytes = await storage.load(source.image_url)
    if source_bytes is None:
        row = await portrait_repository.mark_failed(
            db,
            row,
            error_code="source_image_unavailable",
            error_message="Couldn't load the original photo.",
        )
        return _to_response(row, owned=True, reused=False)

    try:
        source_image = Image.open(io.BytesIO(source_bytes))
        source_image.load()
        source_content_type = Image.MIME.get(source_image.format or "", "image/jpeg")
    except (UnidentifiedImageError, OSError):
        logger.warning("Stored photo for analysis %s is unreadable", source.id, exc_info=True)
        row = await portrait_repository.mark_failed(
            db,
            row,
            error_code="source_image_unavailable",
            error_message="Couldn't read the stored photo.",
        )
        return _to_response(row, owned=True, reused=False)

    archetype_id = _archetype_id_for(source)
    prompt = portrait_prompt.build_prompt(
        style=style,
        breed_label=source.breed_label,
        breed_confidence=source.breed_confidence,
        breed_mode=source.breed_mode,
        colors=source.colors,
        colors_mode=source.colors_mode,
        archetype_id=archetype_id,
        rarity=source.rarity,
        customization=customization,
    )

    try:
        result = await provider.generate_portrait(
            source_image_bytes=source_bytes,
            source_content_type=source_content_type,
            prompt=prompt,
            style=style,
        )
    except ImageGenerationError as exc:
        row = await portrait_repository.mark_failed(
            db, row, error_code=exc.code, error_message=str(exc)
        )
        return _to_response(row, owned=True, reused=False)

    validity_error = _validate_generated_image(result.image_bytes)
    if validity_error is not None:
        row = await portrait_repository.mark_failed(
            db, row, error_code="invalid_output", error_message=validity_error
        )
        return _to_response(row, owned=True, reused=False)

    if not storage.is_available:
        row = await portrait_repository.mark_failed(
            db,
            row,
            error_code="storage_failed",
            error_message="Couldn't save the generated portrait.",
        )
        return _to_response(row, owned=True, reused=False)

    try:
        image_url = await storage.save(
            result.image_bytes, key=f"portrait-{row.id}", content_type=result.content_type
        )
    except Exception:
        logger.warning("Failed to store generated portrait %s", row.id, exc_info=True)
        row = await portrait_repository.mark_failed(
            db,
            row,
            error_code="storage_failed",
            error_message="Couldn't save the generated portrait.",
        )
        return _to_response(row, owned=True, reused=False)

    row = await portrait_repository.mark_succeeded(
        db, row, image_url=image_url, model=result.model
    )
    return _to_response(row, owned=True, reused=False)


def _validate_generated_image(image_bytes: bytes) -> str | None:
    """Never blindly trusts a provider's response (spec §27): re-decodes
    the returned bytes, checks it's a real, openable image of a
    plausible format and size. Returns an honest reason string on
    failure, None if the image looks valid."""
    try:
        image = Image.open(io.BytesIO(image_bytes))
        image.verify()
        # verify() invalidates the file handle — re-open to read dimensions.
        image = Image.open(io.BytesIO(image_bytes))
        width, height = image.size
        image_format = image.format
    except (UnidentifiedImageError, OSError):
        return "The generated image couldn't be read."

    if image_format not in ("PNG", "JPEG", "WEBP"):
        return f"The generated image had an unexpected format ({image_format})."
    if not (_MIN_OUTPUT_DIMENSION <= width <= _MAX_OUTPUT_DIMENSION):
        return f"The generated image had an unexpected width ({width}px)."
    if not (_MIN_OUTPUT_DIMENSION <= height <= _MAX_OUTPUT_DIMENSION):
        return f"The generated image had an unexpected height ({height}px)."
    return None


async def get_portrait(
    db: AsyncSession, portrait_id: uuid.UUID, *, viewer_user_id: uuid.UUID | None
) -> PortraitOut:
    """Powers the public `/portrait/[id]` share page and an owner
    viewing their own (possibly private) portrait — same "public OR you
    own it" rule as every other single-resource GET in this codebase."""
    row = await portrait_repository.get_public(db, portrait_id)
    if row is not None:
        owned = viewer_user_id is not None and row.user_id == viewer_user_id
        return _to_response(row, owned=owned, reused=False)

    if viewer_user_id is not None:
        row = await portrait_repository.get_owned(db, portrait_id, viewer_user_id)
        if row is not None:
            return _to_response(row, owned=True, reused=False)

    raise PortraitNotVisibleError(str(portrait_id))


async def share_portrait(
    db: AsyncSession, portrait_id: uuid.UUID, *, owner_user_id: uuid.UUID
) -> PortraitOut:
    row = await portrait_repository.set_public(db, portrait_id, owner_user_id)
    if row is None:
        raise PortraitNotVisibleError(str(portrait_id))
    return _to_response(row, owned=True, reused=False)


async def unshare_portrait(
    db: AsyncSession, portrait_id: uuid.UUID, *, owner_user_id: uuid.UUID
) -> PortraitOut:
    row = await portrait_repository.set_private(db, portrait_id, owner_user_id)
    if row is None:
        raise PortraitNotVisibleError(str(portrait_id))
    return _to_response(row, owned=True, reused=False)
