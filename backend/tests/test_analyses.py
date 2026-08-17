import io

from PIL import Image

from app.core.config import get_settings


def _make_jpeg_bytes(size=(128, 128), color=(200, 150, 100)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="JPEG")
    return buf.getvalue()


def test_valid_image_returns_analysis(client):
    """Doesn't assume demo vs trained/generated mode for any signal —
    that depends on whether this machine has trained weights / CV deps
    / an Anthropic API key configured. See tests/test_analysis_service.py
    and tests/test_profile_service.py for isolated, mocked mode-branching
    tests that don't depend on the environment.
    """
    files = {"file": ("cat.jpg", _make_jpeg_bytes(), "image/jpeg")}
    response = client.post("/api/v1/analyses", files=files)

    assert response.status_code == 200
    body = response.json()
    assert body["detected"] is True
    assert body["breed_mode"] in {"demo", "trained"}
    assert body["colors_mode"] in {"demo", "trained"}
    assert body["profile_mode"] in {"demo", "generated"}
    assert body["breed"]["label"]
    assert 0.0 <= body["breed"]["confidence"] <= 1.0
    assert len(body["colors"]) > 0

    profile = body["profile"]
    for field in (
        "name",
        "title",
        "personality",
        "magic_power",
        "kingdom",
        "favorite_activity",
        "favorite_food",
        "favorite_season",
        "rarity",
        "description",
    ):
        assert profile[field]
    assert "breed" not in profile
    assert "colors" not in profile


def test_same_image_yields_same_result(client):
    payload = _make_jpeg_bytes()
    r1 = client.post("/api/v1/analyses", files={"file": ("cat.jpg", payload, "image/jpeg")})
    r2 = client.post("/api/v1/analyses", files={"file": ("cat.jpg", payload, "image/jpeg")})

    assert r1.json()["breed"] == r2.json()["breed"]
    assert r1.json()["colors"] == r2.json()["colors"]
    # Only guaranteed equal in demo mode (deterministic); a real LLM call
    # need not be. Both runs are demo unless an API key is configured.
    if r1.json()["profile_mode"] == "demo":
        assert r1.json()["profile"] == r2.json()["profile"]


def test_rejects_unsupported_content_type(client):
    files = {"file": ("cat.gif", b"not-really-a-gif", "image/gif")}
    response = client.post("/api/v1/analyses", files=files)

    assert response.status_code == 422


def test_rejects_corrupt_image_bytes(client):
    files = {"file": ("cat.jpg", b"this is not an image", "image/jpeg")}
    response = client.post("/api/v1/analyses", files=files)

    assert response.status_code == 422
    assert "valid image" in response.json()["detail"]


def test_rejects_oversized_image(client, monkeypatch):
    monkeypatch.setenv("MAX_UPLOAD_SIZE_MB", "0")
    get_settings.cache_clear()
    try:
        files = {"file": ("cat.jpg", _make_jpeg_bytes(), "image/jpeg")}
        response = client.post("/api/v1/analyses", files=files)
        assert response.status_code == 422
        assert "too large" in response.json()["detail"]
    finally:
        get_settings.cache_clear()


def test_rejects_too_small_image(client):
    files = {"file": ("cat.jpg", _make_jpeg_bytes(size=(10, 10)), "image/jpeg")}
    response = client.post("/api/v1/analyses", files=files)

    assert response.status_code == 422
    assert "too small" in response.json()["detail"]


def test_rejects_too_large_dimensions(client):
    buf = io.BytesIO()
    Image.new("RGB", (8001, 100), (10, 20, 30)).save(buf, format="JPEG")
    files = {"file": ("cat.jpg", buf.getvalue(), "image/jpeg")}
    response = client.post("/api/v1/analyses", files=files)

    assert response.status_code == 422
    assert "too large" in response.json()["detail"]


def test_rejects_decompression_bomb_as_a_clean_422_not_a_500(client):
    """Phase 17 regression test for a real, discovered bug: a crafted
    image declaring extreme dimensions (well within the upload byte-size
    limit, since PNG compresses a solid color very well) made Pillow
    raise its own `DecompressionBombError`, which the endpoint didn't
    catch — it would have surfaced as an unhandled 500 instead of the
    same honest 422 every other malformed upload gets.
    """
    buf = io.BytesIO()
    Image.new("RGB", (20000, 20000), (10, 20, 30)).save(buf, format="PNG")
    files = {"file": ("cat.png", buf.getvalue(), "image/png")}
    response = client.post("/api/v1/analyses", files=files)

    assert response.status_code == 422
    assert "valid image" in response.json()["detail"]


def test_rate_limit_returns_429_after_threshold(client, monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "2")
    get_settings.cache_clear()
    try:
        files = {"file": ("cat.jpg", _make_jpeg_bytes(), "image/jpeg")}
        r1 = client.post("/api/v1/analyses", files=files)
        r2 = client.post("/api/v1/analyses", files=files)
        r3 = client.post("/api/v1/analyses", files=files)

        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r3.status_code == 429
    finally:
        get_settings.cache_clear()


def _create_analysis(client) -> str:
    files = {"file": ("cat.jpg", _make_jpeg_bytes(), "image/jpeg")}
    response = client.post("/api/v1/analyses", files=files)
    assert response.status_code == 200
    analysis_id = response.json()["id"]
    assert analysis_id is not None, "analysis must be persisted for share tests to work at all"
    return analysis_id


def test_fresh_analysis_is_private_by_default(client):
    body = client.post(
        "/api/v1/analyses", files={"file": ("cat.jpg", _make_jpeg_bytes(), "image/jpeg")}
    ).json()
    assert body["is_public"] is False


def test_private_cat_is_not_publicly_accessible(client):
    analysis_id = _create_analysis(client)
    response = client.get(f"/api/v1/analyses/{analysis_id}")
    assert response.status_code == 404


def test_nonexistent_cat_returns_404(client):
    fake_id = "00000000-0000-0000-0000-000000000000"
    assert client.get(f"/api/v1/analyses/{fake_id}").status_code == 404


def test_sharing_a_cat_makes_it_publicly_accessible(client, register_user):
    # Phase 9: sharing now requires the caller to own the cat — see
    # tests/test_ownership.py for the full ownership-enforcement suite;
    # this test just confirms the pre-existing Phase 8 share→public
    # behavior still works end to end for an owner.
    register_user()
    analysis_id = _create_analysis(client)

    share_response = client.post(f"/api/v1/analyses/{analysis_id}/share")
    assert share_response.status_code == 200
    assert share_response.json()["is_public"] is True

    client.post("/api/v1/auth/logout")
    public_response = client.get(f"/api/v1/analyses/{analysis_id}")
    assert public_response.status_code == 200
    assert public_response.json()["id"] == analysis_id
    assert public_response.json()["profile"]["name"]
    assert public_response.json()["breed"]["label"]


def test_sharing_a_cat_is_idempotent(client, register_user):
    register_user()
    analysis_id = _create_analysis(client)

    first = client.post(f"/api/v1/analyses/{analysis_id}/share")
    second = client.post(f"/api/v1/analyses/{analysis_id}/share")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["is_public"] is True
    assert second.json()["is_public"] is True


def test_sharing_a_nonexistent_cat_returns_404(client, register_user):
    register_user()
    fake_id = "00000000-0000-0000-0000-000000000000"
    assert client.post(f"/api/v1/analyses/{fake_id}/share").status_code == 404


def test_sharing_without_authentication_returns_401(client):
    analysis_id = _create_analysis(client)
    assert client.post(f"/api/v1/analyses/{analysis_id}/share").status_code == 401
