from abc import ABC, abstractmethod
from typing import Any

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

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """False when no API key/config is present."""


class ImageGenerationProvider(ABC):
    """Generates creative image assets (wallpaper, avatar, sticker).
    Implemented starting in Phase 13.
    """

    @abstractmethod
    async def generate_wallpaper(self, profile: CatProfile) -> dict[str, Any]: ...

    @abstractmethod
    async def generate_avatar(self, profile: CatProfile) -> dict[str, Any]: ...

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


class NullImageGenerationProvider(ImageGenerationProvider):
    @property
    def is_available(self) -> bool:
        return False

    async def generate_wallpaper(self, profile: CatProfile) -> dict[str, Any]:
        raise RuntimeError("No image generation provider configured")

    async def generate_avatar(self, profile: CatProfile) -> dict[str, Any]:
        raise RuntimeError("No image generation provider configured")


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
    return NullImageGenerationProvider()
