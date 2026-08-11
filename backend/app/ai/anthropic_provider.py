import logging
from typing import TypeVar

import anthropic
from pydantic import BaseModel, ValidationError

from app.ai.providers import LLMProvider, LLMProviderError
from app.ai.story_prompt import build_system_prompt, build_user_prompt
from app.schemas.profile import CatProfile, CatSignals
from app.schemas.story import CatStory, StoryStyle

logger = logging.getLogger(__name__)

PROFILE_TOOL_NAME = "generate_cat_profile"
STORY_TOOL_NAME = "generate_cat_story"
MAX_PROMPT_CHARS = 2000
MAX_STORY_PROMPT_CHARS = 3000
MAX_ATTEMPTS = 2  # 1 initial call + 1 semantic retry on invalid schema

_PROFILE_SYSTEM_PROMPT = """\
You are the creative voice of MeowVerse AI, a playful app that turns a \
cat photo's real computer-vision analysis into a fun, magical profile.

You will be given REAL signals about a cat (breed prediction and fur \
colors, produced by actual computer vision models — not by you). Your \
job is to invent ONLY the whimsical, creative parts of a profile, \
using those real signals as inspiration.

Rules:
- You must call the generate_cat_profile tool exactly once with a \
complete, valid profile.
- Never restate, reinterpret, or contradict the breed or color signals \
as if you were re-measuring them — you were not given fields to output \
them, and must not smuggle them into a text field either.
- Never make medical, veterinary, or health claims of any kind (no \
statements about the cat's health, diet needs, or medical condition) \
- this is a playful collectible profile, not veterinary advice.
- Keep the tone cute, warm, and a little magical — never mean, scary, \
or mocking. Avoid copyrighted characters or real brand names.
- Everything you generate is explicitly presented to the user as \
AI-generated creative content, not a scientific prediction.
"""

T = TypeVar("T", bound=BaseModel)


def _strip_titles(schema: dict) -> dict:
    schema.pop("title", None)
    for prop in schema.get("properties", {}).values():
        if isinstance(prop, dict):
            prop.pop("title", None)
    return schema


def _build_profile_tool_schema() -> dict:
    return {
        "name": PROFILE_TOOL_NAME,
        "description": (
            "Record the creative/playful attributes of a cat's magical "
            "profile. Call this exactly once with every field filled in."
        ),
        "input_schema": _strip_titles(CatProfile.model_json_schema()),
    }


def _build_story_tool_schema() -> dict:
    return {
        "name": STORY_TOOL_NAME,
        "description": (
            "Record a complete, structured magical cat story. Call this "
            "exactly once with every field filled in."
        ),
        "input_schema": _strip_titles(CatStory.model_json_schema()),
    }


def _build_profile_user_prompt(signals: CatSignals) -> str:
    colors_desc = ", ".join(
        f"{c.name} ({c.percentage:.0f}%)" for c in signals.colors
    ) or "unknown"
    lines = [
        f"Breed: {signals.breed} (confidence: {signals.breed_confidence:.0%}, "
        f"source: {signals.breed_mode} model)",
        f"Fur colors: {colors_desc} (source: {signals.colors_mode} analysis)",
    ]
    if signals.mood:
        lines.append(f"Mood: {signals.mood}")
    if signals.age_estimate:
        lines.append(f"Estimated age: {signals.age_estimate}")
    lines.append(
        "\nUsing these real signals as inspiration, call generate_cat_profile "
        "with a complete, playful profile for this cat."
    )
    prompt = "\n".join(lines)

    if len(prompt) > MAX_PROMPT_CHARS:
        # All inputs come from our own CV pipeline (bounded field lengths),
        # never raw user text, so this should be unreachable — but it's a
        # real, enforced ceiling rather than an assumption.
        raise LLMProviderError("Constructed prompt exceeds the maximum allowed size")
    return prompt


class AnthropicLLMProvider(LLMProvider):
    def __init__(self, api_key: str, model: str) -> None:
        from app.core.config import get_settings

        settings = get_settings()
        self._model = model
        self._client = anthropic.AsyncAnthropic(
            api_key=api_key,
            timeout=settings.anthropic_timeout_seconds,
            max_retries=1,
        )
        self._max_tokens = settings.anthropic_max_output_tokens

    @property
    def is_available(self) -> bool:
        return True

    async def _call_tool(
        self,
        *,
        system: str,
        user_prompt: str,
        tool: dict,
        response_model: type[T],
    ) -> T:
        """Shared forced-tool-use call loop: try, and on a missing tool
        call or a response that fails `response_model` validation, ask
        once more with a corrective follow-up message before giving up.
        Transport-level failures (timeout/connection/status) are never
        retried here — they raise immediately so the caller can fall
        back without stacking retries on retries.
        """
        tool_name = tool["name"]
        messages: list[dict] = [{"role": "user", "content": user_prompt}]

        last_error: str = "unknown error"
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                response = await self._client.messages.create(
                    model=self._model,
                    max_tokens=self._max_tokens,
                    system=system,
                    tools=[tool],
                    tool_choice={"type": "tool", "name": tool_name},
                    messages=messages,
                )
            except anthropic.APIError as exc:
                logger.warning("Anthropic API call failed: %s", type(exc).__name__)
                raise LLMProviderError(f"Anthropic API error: {type(exc).__name__}") from exc

            tool_use = next(
                (block for block in response.content if block.type == "tool_use"), None
            )
            if tool_use is None:
                last_error = "model did not call the required tool"
                logger.warning(
                    "Anthropic response missing tool_use block (attempt %d/%d)",
                    attempt,
                    MAX_ATTEMPTS,
                )
                messages.append({"role": "assistant", "content": response.content})
                messages.append(
                    {"role": "user", "content": f"You must call the {tool_name} tool."}
                )
                continue

            try:
                return response_model.model_validate(tool_use.input)
            except ValidationError as exc:
                last_error = str(exc)
                logger.warning(
                    "Anthropic tool response failed schema validation (attempt %d/%d)",
                    attempt,
                    MAX_ATTEMPTS,
                )
                messages.append({"role": "assistant", "content": response.content})
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            f"That didn't match the required schema. Call {tool_name} "
                            "again with valid values for every field."
                        ),
                    }
                )
                continue

        raise LLMProviderError(
            f"Invalid {tool_name} output after {MAX_ATTEMPTS} attempts: {last_error}"
        )

    async def generate_profile(self, signals: CatSignals) -> CatProfile:
        return await self._call_tool(
            system=_PROFILE_SYSTEM_PROMPT,
            user_prompt=_build_profile_user_prompt(signals),
            tool=_build_profile_tool_schema(),
            response_model=CatProfile,
        )

    async def generate_story(
        self, signals: CatSignals, profile: CatProfile, style: StoryStyle
    ) -> CatStory:
        user_prompt = build_user_prompt(signals, profile, style)
        if len(user_prompt) > MAX_STORY_PROMPT_CHARS:
            # Same defensive ceiling as the profile prompt — unreachable
            # in practice since every input is our own bounded CV/profile
            # output, never raw user text.
            raise LLMProviderError("Constructed story prompt exceeds the maximum allowed size")

        return await self._call_tool(
            system=build_system_prompt(),
            user_prompt=user_prompt,
            tool=_build_story_tool_schema(),
            response_model=CatStory,
        )
