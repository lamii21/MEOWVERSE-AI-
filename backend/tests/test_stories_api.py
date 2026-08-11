import io

from PIL import Image

from app.core.config import get_settings


def _make_jpeg_bytes(size=(128, 128), color=(200, 150, 100)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="JPEG")
    return buf.getvalue()


def _create_analysis(client) -> str:
    files = {"file": ("cat.jpg", _make_jpeg_bytes(), "image/jpeg")}
    response = client.post("/api/v1/analyses", files=files)
    assert response.status_code == 200
    analysis_id = response.json()["id"]
    assert analysis_id is not None, "analysis must be persisted for story tests to work at all"
    return analysis_id


def test_full_flow_analysis_to_story(client):
    analysis_id = _create_analysis(client)

    response = client.post(
        f"/api/v1/analyses/{analysis_id}/story", json={"style": "cozy_wholesome"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["analysis_id"] == analysis_id
    assert body["style"] == "cozy_wholesome"
    assert body["story_mode"] in {"demo", "generated"}
    assert body["provider"] in {"demo", "anthropic"}
    assert body["story"]["title"]
    assert 3 <= len(body["story"]["chapters"]) <= 5
    assert body["id"]
    assert body["created_at"]


def test_default_style_is_magical_adventure_when_body_omitted(client):
    analysis_id = _create_analysis(client)

    response = client.post(f"/api/v1/analyses/{analysis_id}/story")

    assert response.status_code == 200
    assert response.json()["style"] == "magical_adventure"


def test_every_style_is_accepted(client):
    analysis_id = _create_analysis(client)
    for style in [
        "magical_adventure",
        "cozy_wholesome",
        "funny_chaotic",
        "dreamy_emotional",
        "fantasy_quest",
    ]:
        response = client.post(f"/api/v1/analyses/{analysis_id}/story", json={"style": style})
        assert response.status_code == 200, style
        assert response.json()["style"] == style


def test_rejects_unknown_style(client):
    analysis_id = _create_analysis(client)
    response = client.post(
        f"/api/v1/analyses/{analysis_id}/story", json={"style": "not_a_real_style"}
    )
    assert response.status_code == 422


def test_nonexistent_analysis_returns_404(client):
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = client.post(f"/api/v1/analyses/{fake_id}/story")
    assert response.status_code == 404


def test_duplicate_request_returns_same_story_id(client):
    analysis_id = _create_analysis(client)

    first = client.post(
        f"/api/v1/analyses/{analysis_id}/story", json={"style": "dreamy_emotional"}
    )
    second = client.post(
        f"/api/v1/analyses/{analysis_id}/story", json={"style": "dreamy_emotional"}
    )

    assert first.json()["id"] == second.json()["id"]


def test_regenerate_returns_a_different_story_id(client):
    analysis_id = _create_analysis(client)

    first = client.post(f"/api/v1/analyses/{analysis_id}/story", json={"style": "fantasy_quest"})
    second = client.post(
        f"/api/v1/analyses/{analysis_id}/story",
        json={"style": "fantasy_quest", "regenerate": True},
    )

    assert first.json()["id"] != second.json()["id"]


def test_private_story_is_not_publicly_accessible(client):
    """Stand-in for "unauthorized access": there's no user/auth system
    yet (Phase 9 concern), but the one access-control rule that does
    exist today — a story is private unless explicitly made public — is
    enforced and tested here. A freshly generated story is private by
    default, so the public GET endpoint must 404 for it, not leak it."""
    analysis_id = _create_analysis(client)
    story_response = client.post(f"/api/v1/analyses/{analysis_id}/story")
    story_id = story_response.json()["id"]
    assert story_response.json()["is_public"] is False

    response = client.get(f"/api/v1/stories/{story_id}")

    assert response.status_code == 404


def test_nonexistent_story_returns_404(client):
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = client.get(f"/api/v1/stories/{fake_id}")
    assert response.status_code == 404


def test_sharing_a_story_makes_it_publicly_accessible(client, register_user):
    # Phase 9: sharing a story now requires owning its parent analysis
    # (previously unauthenticated, Phase 7) — see tests/test_ownership.py
    # for the cat-card equivalent of this ownership enforcement.
    register_user()
    analysis_id = _create_analysis(client)
    story_response = client.post(f"/api/v1/analyses/{analysis_id}/story")
    story_id = story_response.json()["id"]

    share_response = client.post(f"/api/v1/stories/{story_id}/share")
    assert share_response.status_code == 200
    assert share_response.json()["is_public"] is True

    client.post("/api/v1/auth/logout")
    public_response = client.get(f"/api/v1/stories/{story_id}")
    assert public_response.status_code == 200
    assert public_response.json()["id"] == story_id
    assert public_response.json()["story"]["title"]


def test_sharing_is_idempotent(client, register_user):
    register_user()
    analysis_id = _create_analysis(client)
    story_response = client.post(f"/api/v1/analyses/{analysis_id}/story")
    story_id = story_response.json()["id"]

    first = client.post(f"/api/v1/stories/{story_id}/share")
    second = client.post(f"/api/v1/stories/{story_id}/share")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["is_public"] is True
    assert second.json()["is_public"] is True


def test_sharing_a_nonexistent_story_returns_404(client, register_user):
    register_user()
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = client.post(f"/api/v1/stories/{fake_id}/share")
    assert response.status_code == 404


def test_sharing_a_story_without_authentication_returns_401(client):
    analysis_id = _create_analysis(client)
    story_response = client.post(f"/api/v1/analyses/{analysis_id}/story")
    story_id = story_response.json()["id"]
    assert client.post(f"/api/v1/stories/{story_id}/share").status_code == 401


def test_cannot_share_someone_elses_story(client, register_user):
    register_user(display_name="Owner")
    analysis_id = _create_analysis(client)
    story_id = client.post(f"/api/v1/analyses/{analysis_id}/story").json()["id"]
    client.post("/api/v1/auth/logout")

    register_user(display_name="Stranger")
    response = client.post(f"/api/v1/stories/{story_id}/share")
    assert response.status_code == 404


def test_story_endpoint_is_rate_limited(client, monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "2")
    get_settings.cache_clear()
    try:
        analysis_id = _create_analysis(client)  # itself counts against the limit

        responses = [
            client.post(
                f"/api/v1/analyses/{analysis_id}/story", json={"style": "cozy_wholesome"}
            ),
            client.post(f"/api/v1/analyses/{analysis_id}/story", json={"style": "funny_chaotic"}),
            client.post(
                f"/api/v1/analyses/{analysis_id}/story", json={"style": "dreamy_emotional"}
            ),
        ]

        assert 429 in [r.status_code for r in responses]
    finally:
        get_settings.cache_clear()
