"""API-level tests for the AI Cat Portrait Studio (Phase 14 spec
§46-47): ownership, privacy, DB persistence, sharing, and rate
limiting, against the real HTTP endpoints. Runs against this dev
environment's real (unconfigured) image-generation provider, so
generation genuinely exercises the honest "unavailable" fallback path
— never a fake image — which is itself the behavior spec §42 requires
and this file verifies directly.
"""

import io
import uuid
from unittest.mock import patch

from PIL import Image

from app.ai.providers import PortraitGenerationResult


def _make_jpeg_bytes(size=(256, 256), color=(200, 150, 100)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="JPEG")
    return buf.getvalue()


def _upload(client, color=(200, 150, 100)) -> dict:
    files = {"file": ("cat.jpg", _make_jpeg_bytes(color=color), "image/jpeg")}
    response = client.post("/api/v1/analyses", files=files)
    assert response.status_code == 200, response.text
    return response.json()


class _FakeWorkingProvider:
    is_available = True

    async def generate_portrait(self, **kwargs):
        buf = io.BytesIO()
        Image.new("RGB", (512, 512), (10, 200, 120)).save(buf, format="PNG")
        return PortraitGenerationResult(
            image_bytes=buf.getvalue(), content_type="image/png", model="gpt-image-1"
        )


def _mock_provider():
    return patch(
        "app.services.portrait_service.get_image_generation_provider",
        return_value=_FakeWorkingProvider(),
    )


class TestHonestUnavailableFallback:
    def test_generation_without_a_configured_provider_returns_honest_unavailable_state(
        self, client, register_user
    ):
        # This dev environment has no image-generation provider
        # configured (spec §42) — verifies the real, unmocked default
        # behavior end to end: never a fake or placeholder image.
        register_user()
        cat = _upload(client)

        response = client.post(
            f"/api/v1/analyses/{cat['id']}/portraits", json={"style": "royal"}
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["status"] == "failed"
        assert body["error_code"] == "provider_unavailable"
        assert body["image_url"] is None

    def test_the_rest_of_the_app_keeps_working_when_portraits_are_unavailable(
        self, client, register_user
    ):
        register_user()
        cat = _upload(client)
        client.post(f"/api/v1/analyses/{cat['id']}/portraits", json={"style": "royal"})

        # Unrelated endpoints must be entirely unaffected.
        response = client.get(f"/api/v1/analyses/{cat['id']}")
        assert response.status_code == 200


class TestGenerateOwnership:
    def test_owner_can_generate(self, client, register_user):
        with _mock_provider():
            register_user()
            cat = _upload(client)
            response = client.post(
                f"/api/v1/analyses/{cat['id']}/portraits", json={"style": "cosmic"}
            )
            assert response.status_code == 200, response.text
            assert response.json()["status"] == "succeeded"

    def test_guest_cannot_generate(self, client):
        cat = _upload(client)  # unauthenticated upload — unowned
        response = client.post(
            f"/api/v1/analyses/{cat['id']}/portraits", json={"style": "royal"}
        )
        assert response.status_code == 401

    def test_non_owner_cannot_generate_even_on_a_public_cat(self, client, register_user):
        register_user(display_name="Owner")
        cat = _upload(client)
        client.post(f"/api/v1/analyses/{cat['id']}/share")
        client.post("/api/v1/auth/logout")

        register_user(display_name="Stranger")
        response = client.post(
            f"/api/v1/analyses/{cat['id']}/portraits", json={"style": "royal"}
        )
        assert response.status_code == 404

    def test_generate_requires_the_analysis_to_exist(self, client, register_user):
        register_user()
        response = client.post(
            f"/api/v1/analyses/{uuid.uuid4()}/portraits", json={"style": "royal"}
        )
        assert response.status_code == 404

    def test_invalid_style_is_rejected_with_422(self, client, register_user):
        register_user()
        cat = _upload(client)
        response = client.post(
            f"/api/v1/analyses/{cat['id']}/portraits", json={"style": "not_a_real_style"}
        )
        assert response.status_code == 422

    def test_customization_over_120_chars_is_rejected_with_422(self, client, register_user):
        register_user()
        cat = _upload(client)
        response = client.post(
            f"/api/v1/analyses/{cat['id']}/portraits",
            json={"style": "royal", "customization": "x" * 200},
        )
        assert response.status_code == 422


class TestListAndMultiplePortraits:
    def test_a_cat_can_have_multiple_portraits_across_styles(self, client, register_user):
        with _mock_provider():
            register_user()
            cat = _upload(client)
            client.post(f"/api/v1/analyses/{cat['id']}/portraits", json={"style": "royal"})
            client.post(f"/api/v1/analyses/{cat['id']}/portraits", json={"style": "cosmic"})
            client.post(f"/api/v1/analyses/{cat['id']}/portraits", json={"style": "watercolor"})

            response = client.get(f"/api/v1/analyses/{cat['id']}/portraits")
            assert response.status_code == 200
            portraits = response.json()["portraits"]
            assert len(portraits) == 3
            styles = {p["style"] for p in portraits}
            assert styles == {"royal", "cosmic", "watercolor"}

    def test_previous_portraits_are_never_overwritten_by_a_new_style(self, client, register_user):
        with _mock_provider():
            register_user()
            cat = _upload(client)
            first = client.post(
                f"/api/v1/analyses/{cat['id']}/portraits", json={"style": "royal"}
            ).json()
            client.post(f"/api/v1/analyses/{cat['id']}/portraits", json={"style": "cosmic"})

            still_there = client.get(f"/api/v1/portraits/{first['id']}")
            assert still_there.status_code == 200
            assert still_there.json()["style"] == "royal"

    def test_owner_sees_failed_attempts_in_the_list_too(self, client, register_user):
        register_user()
        cat = _upload(client)
        client.post(f"/api/v1/analyses/{cat['id']}/portraits", json={"style": "royal"})

        response = client.get(f"/api/v1/analyses/{cat['id']}/portraits")
        portraits = response.json()["portraits"]
        assert len(portraits) == 1
        assert portraits[0]["status"] == "failed"

    def test_guest_viewing_a_public_cat_never_sees_failed_or_private_portraits(
        self, client, register_user
    ):
        register_user()
        cat = _upload(client)
        client.post(f"/api/v1/analyses/{cat['id']}/portraits", json={"style": "royal"})
        client.post(f"/api/v1/analyses/{cat['id']}/share")
        client.post("/api/v1/auth/logout")

        response = client.get(f"/api/v1/analyses/{cat['id']}/portraits")
        assert response.status_code == 200
        assert response.json()["portraits"] == []


class TestSharingAndPrivacy:
    def test_share_makes_a_succeeded_portrait_publicly_viewable(self, client, register_user):
        with _mock_provider():
            register_user()
            cat = _upload(client)
            portrait = client.post(
                f"/api/v1/analyses/{cat['id']}/portraits", json={"style": "royal"}
            ).json()

            share_response = client.post(f"/api/v1/portraits/{portrait['id']}/share")
            assert share_response.status_code == 200
            assert share_response.json()["is_public"] is True

            client.post("/api/v1/auth/logout")
            guest_view = client.get(f"/api/v1/portraits/{portrait['id']}")
            assert guest_view.status_code == 200

    def test_unshared_portrait_is_not_visible_to_a_guest(self, client, register_user):
        with _mock_provider():
            register_user()
            cat = _upload(client)
            portrait = client.post(
                f"/api/v1/analyses/{cat['id']}/portraits", json={"style": "royal"}
            ).json()
            client.post("/api/v1/auth/logout")

            response = client.get(f"/api/v1/portraits/{portrait['id']}")
            assert response.status_code == 404

    def test_a_strangers_email_is_never_leaked_on_the_public_portrait_view(
        self, client, register_user
    ):
        with _mock_provider():
            user = register_user()
            cat = _upload(client)
            portrait = client.post(
                f"/api/v1/analyses/{cat['id']}/portraits", json={"style": "royal"}
            ).json()
            client.post(f"/api/v1/portraits/{portrait['id']}/share")
            client.post("/api/v1/auth/logout")

            response = client.get(f"/api/v1/portraits/{portrait['id']}")
            assert user["email"] not in response.text
            assert "email" not in response.json()
            assert "user_id" not in response.json()

    def test_only_the_owner_can_share(self, client, register_user):
        with _mock_provider():
            register_user(display_name="Owner")
            cat = _upload(client)
            portrait = client.post(
                f"/api/v1/analyses/{cat['id']}/portraits", json={"style": "royal"}
            ).json()
            client.post("/api/v1/auth/logout")

            register_user(display_name="Stranger")
            response = client.post(f"/api/v1/portraits/{portrait['id']}/share")
            assert response.status_code == 404

    def test_unshare_makes_it_private_again(self, client, register_user):
        with _mock_provider():
            register_user()
            cat = _upload(client)
            portrait = client.post(
                f"/api/v1/analyses/{cat['id']}/portraits", json={"style": "royal"}
            ).json()
            client.post(f"/api/v1/portraits/{portrait['id']}/share")
            unshare_response = client.post(f"/api/v1/portraits/{portrait['id']}/unshare")
            assert unshare_response.status_code == 200
            assert unshare_response.json()["is_public"] is False

            client.post("/api/v1/auth/logout")
            response = client.get(f"/api/v1/portraits/{portrait['id']}")
            assert response.status_code == 404

    def test_getting_a_nonexistent_portrait_is_a_404(self, client, register_user):
        register_user()
        response = client.get(f"/api/v1/portraits/{uuid.uuid4()}")
        assert response.status_code == 404


class TestGamification:
    def test_a_new_succeeded_portrait_awards_xp(self, client, register_user):
        with _mock_provider():
            register_user()
            cat = _upload(client)
            response = client.post(
                f"/api/v1/analyses/{cat['id']}/portraits", json={"style": "royal"}
            )
            body = response.json()
            assert body["gamification"] is not None
            assert body["gamification"]["xp_awarded"] > 0

    def test_a_reused_generation_never_re_awards_xp(self, client, register_user):
        with _mock_provider():
            register_user()
            cat = _upload(client)
            client.post(f"/api/v1/analyses/{cat['id']}/portraits", json={"style": "royal"})
            second = client.post(
                f"/api/v1/analyses/{cat['id']}/portraits", json={"style": "royal"}
            ).json()
            assert second["reused"] is True
            assert second["gamification"] is None

    def test_first_portrait_achievement_unlocks(self, client, register_user):
        with _mock_provider():
            register_user()
            cat = _upload(client)
            client.post(f"/api/v1/analyses/{cat['id']}/portraits", json={"style": "royal"})

            achievements = client.get("/api/v1/me/achievements").json()
            first_portrait = next(a for a in achievements if a["key"] == "first_portrait")
            assert first_portrait["unlocked"] is True

    def test_style_collector_needs_five_distinct_styles(self, client, register_user):
        with _mock_provider():
            register_user()
            cat = _upload(client)
            for style in ["royal", "cosmic", "watercolor", "sticker"]:
                client.post(f"/api/v1/analyses/{cat['id']}/portraits", json={"style": style})

            achievements = client.get("/api/v1/me/achievements").json()
            style_collector = next(a for a in achievements if a["key"] == "style_collector")
            assert style_collector["unlocked"] is False
            assert style_collector["progress_current"] == 4

            client.post(f"/api/v1/analyses/{cat['id']}/portraits", json={"style": "anime"})
            achievements = client.get("/api/v1/me/achievements").json()
            style_collector = next(a for a in achievements if a["key"] == "style_collector")
            assert style_collector["unlocked"] is True


class TestRateLimiting:
    def test_portrait_generation_has_its_own_stricter_rate_limit(self, client, register_user):
        # Default portrait_generation_rate_limit_per_minute is 5 — the
        # 6th request in the same minute from the same client must 429,
        # enforced server-side regardless of provider availability.
        register_user()
        cat = _upload(client)
        statuses = [
            client.post(
                f"/api/v1/analyses/{cat['id']}/portraits", json={"style": "royal"}
            ).status_code
            for _ in range(6)
        ]
        assert statuses[:5] == [200, 200, 200, 200, 200]
        assert statuses[5] == 429
