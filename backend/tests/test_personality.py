import io
import uuid

from PIL import Image


def _make_jpeg_bytes(size=(128, 128), color=(200, 150, 100)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="JPEG")
    return buf.getvalue()


def _upload(client, color=(200, 150, 100)) -> dict:
    files = {"file": ("cat.jpg", _make_jpeg_bytes(color=color), "image/jpeg")}
    response = client.post("/api/v1/analyses", files=files)
    assert response.status_code == 200, response.text
    return response.json()


class TestPersonalityHappyPath:
    def test_analysis_produces_a_real_personality(self, client, register_user):
        register_user()
        cat = _upload(client)

        response = client.get(f"/api/v1/analyses/{cat['id']}/personality")
        assert response.status_code == 200, response.text
        body = response.json()

        assert body["analysis_id"] == cat["id"]
        assert body["personality_engine_version"]
        assert body["archetype"]["id"]
        assert body["archetype"]["name"]
        assert set(body["traits"].keys()) == {
            "curiosity",
            "playfulness",
            "calmness",
            "cuddliness",
            "confidence",
            "mischief",
            "elegance",
            "adventurousness",
        }
        for trait in body["traits"].values():
            assert 0 <= trait["score"] <= 100
            assert trait["level"] in ("Very Low", "Low", "Balanced", "High", "Very High")
        assert body["interpretation"]["headline"]
        assert body["interpretation_mode"] in ("generated", "demo")
        assert "disclaimer" in body
        assert "AI-inspired" in body["disclaimer"]

    def test_disclaimer_never_claims_scientific_detection(self, client, register_user):
        register_user()
        cat = _upload(client)
        body = client.get(f"/api/v1/analyses/{cat['id']}/personality").json()
        disclaimer = body["disclaimer"].lower()
        assert "not a scientific" in disclaimer

    def test_confidence_score_is_never_relabeled_as_a_percent_claim(self, client, register_user):
        # Structural check: the response has no field literally named to
        # imply a measured behavioral percentage.
        register_user()
        cat = _upload(client)
        body = client.get(f"/api/v1/analyses/{cat['id']}/personality").json()
        assert "behavioral_accuracy" not in body
        assert "personality_confidence" not in body


class TestPersonalityCaching:
    def test_second_request_reuses_the_cached_structured_result_and_interpretation(
        self, client, register_user
    ):
        register_user()
        cat = _upload(client)

        first = client.get(f"/api/v1/analyses/{cat['id']}/personality").json()
        assert first["interpretation_cached"] is False

        second = client.get(f"/api/v1/analyses/{cat['id']}/personality").json()
        assert second["interpretation_cached"] is True
        assert second["id"] == first["id"]
        assert second["archetype"]["id"] == first["archetype"]["id"]
        assert second["traits"] == first["traits"]
        assert second["interpretation"] == first["interpretation"]


class TestPersonalityRegenerate:
    def test_regenerate_creates_a_new_interpretation_but_never_changes_scores(
        self, client, register_user
    ):
        register_user()
        cat = _upload(client)
        first = client.get(f"/api/v1/analyses/{cat['id']}/personality").json()

        response = client.post(f"/api/v1/analyses/{cat['id']}/personality/regenerate")
        assert response.status_code == 200, response.text
        regenerated = response.json()

        assert regenerated["interpretation_cached"] is False
        assert regenerated["archetype"]["id"] == first["archetype"]["id"]
        assert regenerated["traits"] == first["traits"]
        assert regenerated["personality_engine_version"] == first["personality_engine_version"]

    def test_regenerate_requires_authentication(self, client):
        cat = _upload(client)  # guest, unowned
        response = client.post(f"/api/v1/analyses/{cat['id']}/personality/regenerate")
        assert response.status_code == 401

    def test_regenerate_requires_real_ownership_not_just_public_visibility(
        self, client, register_user
    ):
        register_user(display_name="Owner")
        cat = _upload(client)
        client.post(f"/api/v1/analyses/{cat['id']}/share")
        client.post("/api/v1/auth/logout")

        register_user(display_name="Stranger")
        response = client.post(f"/api/v1/analyses/{cat['id']}/personality/regenerate")
        assert response.status_code == 404


class TestPersonalityOwnership:
    def test_requires_the_analysis_to_exist(self, client, register_user):
        register_user()
        response = client.get(f"/api/v1/analyses/{uuid.uuid4()}/personality")
        assert response.status_code == 404

    def test_stranger_cannot_view_a_private_analysis_personality(self, client, register_user):
        register_user(display_name="Owner")
        cat = _upload(client)
        client.post("/api/v1/auth/logout")

        register_user(display_name="Stranger")
        response = client.get(f"/api/v1/analyses/{cat['id']}/personality")
        assert response.status_code == 404

    def test_guest_cannot_view_a_private_analysis_personality(self, client, register_user):
        register_user()
        cat = _upload(client)
        client.post("/api/v1/auth/logout")

        response = client.get(f"/api/v1/analyses/{cat['id']}/personality")
        assert response.status_code == 404

    def test_public_analysis_personality_is_accessible_to_a_guest(self, client, register_user):
        register_user()
        cat = _upload(client)
        client.post(f"/api/v1/analyses/{cat['id']}/share")
        client.post("/api/v1/auth/logout")

        response = client.get(f"/api/v1/analyses/{cat['id']}/personality")
        assert response.status_code == 200
        body = response.json()
        # Public-safe fields only — never private metadata.
        assert "user_id" not in body
        assert "email" not in body
