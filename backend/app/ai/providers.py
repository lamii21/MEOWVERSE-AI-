from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from app.schemas.personality import PersonalityInterpretation
from app.schemas.portrait import PortraitErrorCode, PortraitStyle
from app.schemas.profile import CatProfile, CatSignals
from app.schemas.story import CatStory, StoryStyle


class LLMProviderError(Exception):
    """Raised by any LLMProvider on an unrecoverable failure (timeout,
    API error, or a response that still doesn't validate after retrying).
    Callers (app/services/profile_service.py) catch this and fall back
    to a clearly-labeled demo profile — never let it crash the request.
    """


class LLMProvider(ABC):
    """Generates the AI-authored parts of a cat profile: personality,
    magic power, etc. Concrete providers (Anthropic, OpenAI, ...) live
    behind this interface so the app never depends on a specific vendor.
    """

    @abstractmethod
    async def generate_profile(self, signals: CatSignals) -> CatProfile:
        """Generate creative profile fields from real CV signals.

        Raises LLMProviderError on any failure — timeout, API error, or
        a response that fails schema validation even after an internal
        retry. Never returns a partially-valid or fabricated result.
        """

    @abstractmethod
    async def generate_story(
        self, signals: CatSignals, profile: CatProfile, style: StoryStyle
    ) -> CatStory:
        """Generate a short story from real CV signals + the (already
        generated) creative profile, in the requested style.

        Raises LLMProviderError on any failure, same contract as
        generate_profile above.
        """

    @abstractmethod
    async def generate_personality_interpretation(
        self,
        signals: CatSignals,
        *,
        archetype_name: str,
        archetype_short_description: str,
        trait_levels: dict[str, str],
        rarity: str,
    ) -> PersonalityInterpretation:
        """Turns an ALREADY-DECIDED archetype + trait levels (from the
        deterministic `PersonalityScoringEngine`, Phase 13) into
        creative flavor text. Must never be asked to choose the
        archetype or trait scores themselves — those are structurally
        absent from `PersonalityInterpretation`.

        Raises LLMProviderError on any failure, same contract as
        generate_profile/generate_story above.
        """

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """False when no API key/config is present."""


class ImageGenerationError(Exception):
    """Raised by any ImageGenerationProvider on a failure. Always
    carries a `code` from the same closed set the portrait API surfaces
    (spec §41) — callers (app/services/portrait_service.py) map this to
    an honest, friendly `CatPortraitModel.error_code`/`error_message`,
    never a raw provider stack trace."""

    def __init__(self, message: str, *, code: PortraitErrorCode) -> None:
        super().__init__(message)
        self.code: PortraitErrorCode = code


@dataclass(frozen=True)
class PortraitGenerationResult:
    image_bytes: bytes
    content_type: str
    model: str


class ImageGenerationProvider(ABC):
    """Generates creative image assets. `generate_portrait` (Phase 14)
    is the one real, implemented capability — it turns a user's real
    source photo plus a backend-built prompt (never frontend-controlled,
    see app/ai/portrait_prompt.py) into a new, artistically restyled
    image via image-conditioned generation. `generate_wallpaper`/
    `generate_avatar` remain Phase-13-era placeholders for a *different*,
    not-yet-built feature (a decorative wallpaper/avatar export, not a
    cat portrait) — deliberately left unimplemented rather than
    repurposed, so "Portrait Studio" doesn't silently redefine what
    those two already-named methods mean.
    """

    @abstractmethod
    async def generate_wallpaper(self, profile: CatProfile) -> dict[str, Any]: ...

    @abstractmethod
    async def generate_avatar(self, profile: CatProfile) -> dict[str, Any]: ...

    @abstractmethod
    async def generate_portrait(
        self,
        *,
        source_image_bytes: bytes,
        source_content_type: str,
        prompt: str,
        style: PortraitStyle,
    ) -> PortraitGenerationResult:
        """Generates one artistic portrait, conditioned on the real
        source photo (the primary identity reference, spec §7) plus the
        already-built, backend-controlled `prompt` (spec §11 — this
        method never sees a style enum's raw scene text or user
        customization directly; the prompt is fully assembled before
        this call). Raises ImageGenerationError on any failure —
        never returns a partial or fabricated result."""

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """False when no API key/config is present."""


class NullLLMProvider(LLMProvider):
    """Fallback used whenever no LLM provider is configured. Never called
    in practice — app/services/profile_service.py checks `is_available`
    first and uses its own local demo profile generator instead of
    invoking this provider at all.
    """

    @property
    def is_available(self) -> bool:
        return False

    async def generate_profile(self, signals: CatSignals) -> CatProfile:
        raise LLMProviderError("No LLM provider configured; check is_available first")

    async def generate_story(
        self, signals: CatSignals, profile: CatProfile, style: StoryStyle
    ) -> CatStory:
        raise LLMProviderError("No LLM provider configured; check is_available first")

    async def generate_personality_interpretation(
        self,
        signals: CatSignals,
        *,
        archetype_name: str,
        archetype_short_description: str,
        trait_levels: dict[str, str],
        rarity: str,
    ) -> PersonalityInterpretation:
        raise LLMProviderError("No LLM provider configured; check is_available first")


class NullImageGenerationProvider(ImageGenerationProvider):
    """Fallback used whenever no image-generation provider is
    configured. app/services/portrait_service.py checks `is_available`
    first and returns an honest `unavailable` portrait state instead of
    calling this at all (spec §42: never fake a generated image) — this
    class exists so the ABC is always satisfiable, not as a path meant
    to be exercised in practice."""

    @property
    def is_available(self) -> bool:
        return False

    async def generate_wallpaper(self, profile: CatProfile) -> dict[str, Any]:
        raise RuntimeError("No image generation provider configured")

    async def generate_avatar(self, profile: CatProfile) -> dict[str, Any]:
        raise RuntimeError("No image generation provider configured")

    async def generate_portrait(
        self,
        *,
        source_image_bytes: bytes,
        source_content_type: str,
        prompt: str,
        style: PortraitStyle,
    ) -> PortraitGenerationResult:
        raise ImageGenerationError(
            "No image generation provider configured", code="provider_unavailable"
        )


def get_llm_provider() -> LLMProvider:
    """Factory selecting a provider based on settings. Constructing the
    Anthropic client is cheap (no network call at construction time) so
    this deliberately isn't cached as a singleton — a fresh instance per
    call keeps it trivially consistent with whatever `get_settings()`
    (itself cached, but test-clearable) currently reports.
    """
    from app.core.config import get_settings

    settings = get_settings()
    if settings.llm_provider == "anthropic" and settings.anthropic_api_key:
        from app.ai.anthropic_provider import AnthropicLLMProvider

        return AnthropicLLMProvider(
            api_key=settings.anthropic_api_key,
            model=settings.anthropic_model,
        )
    return NullLLMProvider()


def get_image_generation_provider() -> ImageGenerationProvider:
    """Same factory shape as `get_llm_provider` above: a fresh instance
    per call (cheap to construct, stays consistent with whatever
    `get_settings()` currently reports), NullProvider fallback whenever
    nothing is configured. `image_generation_api_key` is preferred; an
    already-set `openai_api_key` (e.g. reused from LLM configuration)
    is accepted as a fallback so a single OpenAI key configured for
    other purposes doesn't need to be duplicated into a second env var.
    """
    from app.core.config import get_settings

    settings = get_settings()
    api_key = settings.image_generation_api_key or settings.openai_api_key
    if settings.image_generation_provider == "openai" and api_key:
        from app.ai.openai_image_provider import OpenAIImageGenerationProvider

        return OpenAIImageGenerationProvider(api_key=api_key, model=settings.image_generation_model)
    return NullImageGenerationProvider()
