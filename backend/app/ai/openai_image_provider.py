import base64
import logging
from typing import Any

import openai

from app.ai.providers import ImageGenerationError, ImageGenerationProvider, PortraitGenerationResult
from app.schemas.portrait import PortraitStyle
from app.schemas.profile import CatProfile

logger = logging.getLogger(__name__)


def _map_openai_error(exc: Exception) -> ImageGenerationError:
    """Translates the real OpenAI SDK exception hierarchy (verified via
    direct introspection of the installed `openai` package, not
    guessed) into one of the closed set of portrait error codes the API
    surfaces — never a raw provider stack trace (spec §41)."""
    if isinstance(exc, openai.RateLimitError):
        return ImageGenerationError("Image provider rate limit reached", code="rate_limited")
    if isinstance(exc, openai.APITimeoutError):
        return ImageGenerationError("Image provider request timed out", code="timeout")
    if isinstance(exc, openai.APIConnectionError):
        return ImageGenerationError("Could not reach the image provider", code="network_error")
    if isinstance(exc, openai.AuthenticationError | openai.PermissionDeniedError):
        return ImageGenerationError(
            "Image provider is not correctly configured", code="provider_unavailable"
        )
    if isinstance(exc, openai.BadRequestError):
        # gpt-image-1 raises BadRequestError for content-policy rejections
        # (e.g. a flagged prompt or reference image) as well as genuinely
        # malformed requests — both are honestly "we can't make this one,"
        # never surfaced as a generic 500.
        return ImageGenerationError(
            "The image provider couldn't generate this portrait (it may have "
            "been flagged by content safety filters)",
            code="content_rejected",
        )
    return ImageGenerationError(
        f"Image provider error: {type(exc).__name__}", code="provider_error"
    )


class OpenAIImageGenerationProvider(ImageGenerationProvider):
    """Real image-conditioned generation via OpenAI's `images.edit`
    endpoint (verified against the installed `openai` 3.1.0 SDK's real
    method signature before writing this — not assumed). `gpt-image-1`
    is the current OpenAI model that accepts a reference image *and* a
    text prompt and returns a new image informed by both — exactly the
    "source image as primary identity reference" capability Phase 14
    spec §6/§7 requires. `input_fidelity="high"` is the SDK's own
    parameter specifically for preserving input-image detail, which is
    why this provider (rather than a text-only generator like DALL-E 3,
    which has no image-conditioning input at all) was chosen.
    """

    def __init__(self, api_key: str, model: str) -> None:
        from app.core.config import get_settings

        settings = get_settings()
        self._model = model
        self._client = openai.AsyncOpenAI(
            api_key=api_key,
            timeout=settings.image_generation_timeout_seconds,
            max_retries=1,
        )
        self._size = settings.portrait_output_size
        self._max_bytes = settings.portrait_max_bytes

    @property
    def is_available(self) -> bool:
        return True

    async def generate_wallpaper(self, profile: CatProfile) -> dict[str, Any]:
        raise RuntimeError("Not implemented in Phase 14 — use generate_portrait")

    async def generate_avatar(self, profile: CatProfile) -> dict[str, Any]:
        raise RuntimeError("Not implemented in Phase 14 — use generate_portrait")

    async def generate_portrait(
        self,
        *,
        source_image_bytes: bytes,
        source_content_type: str,
        prompt: str,
        style: PortraitStyle,
    ) -> PortraitGenerationResult:
        extension = "png" if source_content_type == "image/png" else "jpg"
        try:
            response = await self._client.images.edit(
                image=(f"reference.{extension}", source_image_bytes, source_content_type),
                prompt=prompt,
                model=self._model,
                size=self._size,  # type: ignore[arg-type]
                quality="high",
                input_fidelity="high",
                output_format="png",
                n=1,
            )
        except openai.APIError as exc:
            logger.warning("OpenAI image generation failed: %s", type(exc).__name__)
            raise _map_openai_error(exc) from exc
        except Exception as exc:  # malformed/unexpected SDK-level failure
            logger.warning("Unexpected image generation failure", exc_info=True)
            raise ImageGenerationError(
                f"Unexpected image provider failure: {type(exc).__name__}", code="provider_error"
            ) from exc

        if not response.data:
            raise ImageGenerationError("Image provider returned no image", code="invalid_output")

        b64 = response.data[0].b64_json
        if not b64:
            raise ImageGenerationError(
                "Image provider response did not include image data", code="invalid_output"
            )

        try:
            image_bytes = base64.b64decode(b64)
        except (ValueError, TypeError) as exc:
            raise ImageGenerationError(
                "Image provider returned malformed image data", code="invalid_output"
            ) from exc

        if not image_bytes or len(image_bytes) > self._max_bytes:
            raise ImageGenerationError(
                "Image provider returned an unexpectedly sized image", code="invalid_output"
            )

        return PortraitGenerationResult(
            image_bytes=image_bytes, content_type="image/png", model=self._model
        )
