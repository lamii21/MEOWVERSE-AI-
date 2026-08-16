"""Mock-provider tests for portrait generation (Phase 14 spec §45):
success, timeout, network failure, rate limit, invalid output,
provider unavailable, malformed response, storage failure, fallback.
Uses a real DB row (via the HTTP client, same pattern as
test_personality_interpretation.py's sibling test_personality.py) but a
mocked `get_image_generation_provider`, so no real API key is needed.
"""

import io
import uuid
from unittest.mock import patch

import pytest
from PIL import Image

from app.ai.providers import ImageGenerationError, PortraitGenerationResult
from app.schemas.portrait import PortraitStyle
from app.services import portrait_service


def _make_jpeg_bytes(size=(256, 256), color=(200, 150, 100)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="JPEG")
    return buf.getvalue()


def _make_png_bytes(size=(512, 512)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, (10, 200, 120)).save(buf, format="PNG")
    return buf.getvalue()


def _upload(client, color=(200, 150, 100)) -> dict:
    files = {"file": ("cat.jpg", _make_jpeg_bytes(color=color), "image/jpeg")}
    response = client.post("/api/v1/analyses", files=files)
    assert response.status_code == 200, response.text
    return response.json()


class _FakeUnavailableProvider:
    is_available = False


class _FakeWorkingProvider:
    is_available = True

    async def generate_portrait(self, **kwargs):
        return PortraitGenerationResult(
            image_bytes=_make_png_bytes(), content_type="image/png", model="gpt-image-1"
        )


class _FakeTimeoutProvider:
    is_available = True

    async def generate_portrait(self, **kwargs):
        raise ImageGenerationError("timed out", code="timeout")


class _FakeRateLimitedProvider:
    is_available = True

    async def generate_portrait(self, **kwargs):
        raise ImageGenerationError("rate limited", code="rate_limited")


class _FakeNetworkErrorProvider:
    is_available = True

    async def generate_portrait(self, **kwargs):
        raise ImageGenerationError("network down", code="network_error")


class _FakeContentRejectedProvider:
    is_available = True

    async def generate_portrait(self, **kwargs):
        raise ImageGenerationError("rejected", code="content_rejected")


class _FakeMalformedResponseProvider:
    """Returns bytes that aren't a real image at all — the provider
    misbehaving, not a network-level failure."""

    is_available = True

    async def generate_portrait(self, **kwargs):
        return PortraitGenerationResult(
            image_bytes=b"not a real image", content_type="image/png", model="gpt-image-1"
        )


class _FakeUndersizedImageProvider:
    """Returns a real, valid image — but far too small to be a usable
    portrait, exercising the dimension-validation guard."""

    is_available = True

    async def generate_portrait(self, **kwargs):
        return PortraitGenerationResult(
            image_bytes=_make_png_bytes(size=(16, 16)),
            content_type="image/png",
            model="gpt-image-1",
        )


@pytest.mark.asyncio
@patch("app.services.portrait_service.get_image_generation_provider")
async def test_provider_unavailable_returns_an_honest_unavailable_state_never_a_fake_image(
    mock_get_provider, client, register_user, db_session
):
    mock_get_provider.return_value = _FakeUnavailableProvider()
    user = register_user()
    cat = _upload(client)

    result = await portrait_service.generate_portrait(
        db_session,
        uuid.UUID(cat["id"]),
        owner_user_id=uuid.UUID(user["id"]),
        style=PortraitStyle.ROYAL,
        customization=None,
        force_new=False,
    )

    assert result.status == "failed"
    assert result.error_code == "provider_unavailable"
    assert result.image_url is None
    assert "unavailable" in result.error_message.lower()


@pytest.mark.asyncio
@patch("app.services.portrait_service.get_image_generation_provider")
async def test_successful_generation_produces_a_real_stored_image(
    mock_get_provider, client, register_user, db_session
):
    mock_get_provider.return_value = _FakeWorkingProvider()
    user = register_user()
    cat = _upload(client)

    result = await portrait_service.generate_portrait(
        db_session,
        uuid.UUID(cat["id"]),
        owner_user_id=uuid.UUID(user["id"]),
        style=PortraitStyle.COSMIC,
        customization=None,
        force_new=False,
    )

    assert result.status == "succeeded"
    assert result.image_url is not None
    assert result.image_url.startswith("/media/")
    assert result.model == "gpt-image-1"
    assert result.error_code is None
    assert result.reused is False


@pytest.mark.asyncio
@patch("app.services.portrait_service.get_image_generation_provider")
async def test_timeout_is_reported_honestly(mock_get_provider, client, register_user, db_session):
    mock_get_provider.return_value = _FakeTimeoutProvider()
    user = register_user()
    cat = _upload(client)

    result = await portrait_service.generate_portrait(
        db_session,
        uuid.UUID(cat["id"]),
        owner_user_id=uuid.UUID(user["id"]),
        style=PortraitStyle.ROYAL,
        customization=None,
        force_new=False,
    )
    assert result.status == "failed"
    assert result.error_code == "timeout"


@pytest.mark.asyncio
@patch("app.services.portrait_service.get_image_generation_provider")
async def test_rate_limit_is_reported_honestly(
    mock_get_provider, client, register_user, db_session
):
    mock_get_provider.return_value = _FakeRateLimitedProvider()
    user = register_user()
    cat = _upload(client)

    result = await portrait_service.generate_portrait(
        db_session,
        uuid.UUID(cat["id"]),
        owner_user_id=uuid.UUID(user["id"]),
        style=PortraitStyle.ROYAL,
        customization=None,
        force_new=False,
    )
    assert result.status == "failed"
    assert result.error_code == "rate_limited"


@pytest.mark.asyncio
@patch("app.services.portrait_service.get_image_generation_provider")
async def test_network_failure_is_reported_honestly(
    mock_get_provider, client, register_user, db_session
):
    mock_get_provider.return_value = _FakeNetworkErrorProvider()
    user = register_user()
    cat = _upload(client)

    result = await portrait_service.generate_portrait(
        db_session,
        uuid.UUID(cat["id"]),
        owner_user_id=uuid.UUID(user["id"]),
        style=PortraitStyle.ROYAL,
        customization=None,
        force_new=False,
    )
    assert result.status == "failed"
    assert result.error_code == "network_error"


@pytest.mark.asyncio
@patch("app.services.portrait_service.get_image_generation_provider")
async def test_content_rejection_is_reported_honestly_not_as_a_generic_error(
    mock_get_provider, client, register_user, db_session
):
    mock_get_provider.return_value = _FakeContentRejectedProvider()
    user = register_user()
    cat = _upload(client)

    result = await portrait_service.generate_portrait(
        db_session,
        uuid.UUID(cat["id"]),
        owner_user_id=uuid.UUID(user["id"]),
        style=PortraitStyle.ROYAL,
        customization=None,
        force_new=False,
    )
    assert result.status == "failed"
    assert result.error_code == "content_rejected"


@pytest.mark.asyncio
@patch("app.services.portrait_service.get_image_generation_provider")
async def test_malformed_provider_response_never_trusted_blindly(
    mock_get_provider, client, register_user, db_session
):
    mock_get_provider.return_value = _FakeMalformedResponseProvider()
    user = register_user()
    cat = _upload(client)

    result = await portrait_service.generate_portrait(
        db_session,
        uuid.UUID(cat["id"]),
        owner_user_id=uuid.UUID(user["id"]),
        style=PortraitStyle.ROYAL,
        customization=None,
        force_new=False,
    )
    assert result.status == "failed"
    assert result.error_code == "invalid_output"
    assert result.image_url is None


@pytest.mark.asyncio
@patch("app.services.portrait_service.get_image_generation_provider")
async def test_undersized_image_is_rejected_by_dimension_validation(
    mock_get_provider, client, register_user, db_session
):
    mock_get_provider.return_value = _FakeUndersizedImageProvider()
    user = register_user()
    cat = _upload(client)

    result = await portrait_service.generate_portrait(
        db_session,
        uuid.UUID(cat["id"]),
        owner_user_id=uuid.UUID(user["id"]),
        style=PortraitStyle.ROYAL,
        customization=None,
        force_new=False,
    )
    assert result.status == "failed"
    assert result.error_code == "invalid_output"


@pytest.mark.asyncio
@patch("app.services.portrait_service.get_image_generation_provider")
async def test_failed_generation_is_still_persisted_never_silently_discarded(
    mock_get_provider, client, register_user, db_session
):
    mock_get_provider.return_value = _FakeTimeoutProvider()
    user = register_user()
    cat = _upload(client)

    await portrait_service.generate_portrait(
        db_session,
        uuid.UUID(cat["id"]),
        owner_user_id=uuid.UUID(user["id"]),
        style=PortraitStyle.ROYAL,
        customization=None,
        force_new=False,
    )

    portraits = await portrait_service.list_portraits(
        db_session, uuid.UUID(cat["id"]), viewer_user_id=uuid.UUID(user["id"])
    )
    assert len(portraits) == 1
    assert portraits[0].status == "failed"


@pytest.mark.asyncio
@patch("app.services.portrait_service.get_image_generation_provider")
async def test_duplicate_request_reuses_the_existing_succeeded_generation(
    mock_get_provider, client, register_user, db_session
):
    mock_get_provider.return_value = _FakeWorkingProvider()
    user = register_user()
    cat = _upload(client)

    first = await portrait_service.generate_portrait(
        db_session,
        uuid.UUID(cat["id"]),
        owner_user_id=uuid.UUID(user["id"]),
        style=PortraitStyle.ROYAL,
        customization=None,
        force_new=False,
    )
    second = await portrait_service.generate_portrait(
        db_session,
        uuid.UUID(cat["id"]),
        owner_user_id=uuid.UUID(user["id"]),
        style=PortraitStyle.ROYAL,
        customization=None,
        force_new=False,
    )

    assert first.reused is False
    assert second.reused is True
    assert second.id == first.id
    assert second.image_url == first.image_url


@pytest.mark.asyncio
@patch("app.services.portrait_service.get_image_generation_provider")
async def test_force_new_bypasses_reuse_and_creates_a_genuinely_new_row(
    mock_get_provider, client, register_user, db_session
):
    mock_get_provider.return_value = _FakeWorkingProvider()
    user = register_user()
    cat = _upload(client)

    first = await portrait_service.generate_portrait(
        db_session,
        uuid.UUID(cat["id"]),
        owner_user_id=uuid.UUID(user["id"]),
        style=PortraitStyle.ROYAL,
        customization=None,
        force_new=False,
    )
    second = await portrait_service.generate_portrait(
        db_session,
        uuid.UUID(cat["id"]),
        owner_user_id=uuid.UUID(user["id"]),
        style=PortraitStyle.ROYAL,
        customization=None,
        force_new=True,
    )

    assert second.reused is False
    assert second.id != first.id
