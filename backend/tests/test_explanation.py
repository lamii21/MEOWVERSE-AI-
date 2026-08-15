import io
import uuid

from PIL import Image

from app.models.analysis import CatAnalysisModel


def _make_jpeg_bytes(size=(128, 128), color=(200, 150, 100)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="JPEG")
    return buf.getvalue()


def _upload(client, color=(200, 150, 100)) -> dict:
    files = {"file": ("cat.jpg", _make_jpeg_bytes(color=color), "image/jpeg")}
    response = client.post("/api/v1/analyses", files=files)
    assert response.status_code == 200, response.text
    return response.json()


async def _insert_demo_mode_analysis(db_session) -> uuid.UUID:
    """Directly constructs a `breed_mode="demo"` row, bypassing the
    real analyze pipeline — the only way to exercise the "demo
    prediction, no fake explanation" path in an environment where the
    real trained classifier IS available (so every real upload here
    naturally gets `breed_mode="trained"`)."""
    row = CatAnalysisModel(
        breed_label="Bengal",
        breed_confidence=0.79,
        breed_mode="demo",
        colors=[{"name": "orange", "hex": "#D98B4B", "percentage": 100.0}],
        colors_mode="demo",
        profile={
            "name": "Test",
            "title": "Test",
            "personality": "Test.",
            "magic_power": "Test.",
            "kingdom": "Test",
            "favorite_activity": "Test",
            "favorite_food": "Test",
            "favorite_season": "Summer",
            "rarity": "Common",
            "description": "Test.",
        },
        profile_mode="demo",
        cat_name="Test",
        rarity="Common",
        image_url="/media/does-not-matter.jpg",
    )
    db_session.add(row)
    await db_session.commit()
    await db_session.refresh(row)
    return row.id


class TestExplanationHappyPath:
    def test_trained_analysis_produces_a_real_explanation(self, client, register_user):
        register_user()
        cat = _upload(client)
        assert cat["breed_mode"] == "trained"

        response = client.post(f"/api/v1/analyses/{cat['id']}/explanation")
        assert response.status_code == 200, response.text
        body = response.json()

        assert body["mode"] == "trained"
        assert body["method"] == "grad-cam"
        assert body["target_class"] == cat["breed"]["label"]
        assert body["confidence"] == cat["breed"]["confidence"]
        assert body["target_layer"] == "features.12"
        assert body["breed_model_version"]
        assert body["image_width"] > 0
        assert body["image_height"] > 0
        assert body["cached"] is False

    def test_explanation_images_are_real_reachable_urls(self, client, register_user):
        register_user()
        cat = _upload(client)
        body = client.post(f"/api/v1/analyses/{cat['id']}/explanation").json()

        if body["heatmap_url"]:
            img_response = client.get(body["heatmap_url"])
            assert img_response.status_code == 200
            assert img_response.headers["content-type"].startswith("image/")
        if body["overlay_url"]:
            img_response = client.get(body["overlay_url"])
            assert img_response.status_code == 200
            assert img_response.headers["content-type"].startswith("image/")


class TestExplanationCaching:
    def test_second_request_reuses_the_cached_explanation(self, client, register_user):
        register_user()
        cat = _upload(client)

        first = client.post(f"/api/v1/analyses/{cat['id']}/explanation").json()
        assert first["cached"] is False

        second = client.post(f"/api/v1/analyses/{cat['id']}/explanation").json()
        assert second["cached"] is True
        assert second["heatmap_url"] == first["heatmap_url"]
        assert second["created_at"] == first["created_at"]

    def test_different_target_class_is_not_served_from_the_others_cache(
        self, client, register_user
    ):
        register_user()
        cat = _upload(client)
        first = client.post(f"/api/v1/analyses/{cat['id']}/explanation").json()

        other_class = next(
            c
            for c in ["Abyssinian", "Bengal", "Birman", "Bombay", "British Shorthair"]
            if c != first["target_class"]
        )
        second = client.post(
            f"/api/v1/analyses/{cat['id']}/explanation", json={"target_class": other_class}
        ).json()
        assert second["cached"] is False
        assert second["target_class"] == other_class


class TestExplanationTargetClass:
    def test_invalid_target_class_is_rejected(self, client, register_user):
        register_user()
        cat = _upload(client)
        response = client.post(
            f"/api/v1/analyses/{cat['id']}/explanation", json={"target_class": "Not A Real Breed"}
        )
        assert response.status_code == 422

    def test_default_target_class_matches_the_displayed_breed_never_a_different_one(
        self, client, register_user
    ):
        register_user()
        cat = _upload(client)
        body = client.post(f"/api/v1/analyses/{cat['id']}/explanation").json()
        assert body["target_class"] == cat["breed"]["label"]


class TestExplanationOwnership:
    def test_requires_the_analysis_to_exist(self, client, register_user):
        register_user()
        response = client.post(f"/api/v1/analyses/{uuid.uuid4()}/explanation")
        assert response.status_code == 404

    def test_stranger_cannot_request_explanation_for_a_private_analysis(
        self, client, register_user
    ):
        register_user(display_name="Owner")
        cat = _upload(client)
        client.post("/api/v1/auth/logout")

        register_user(display_name="Stranger")
        response = client.post(f"/api/v1/analyses/{cat['id']}/explanation")
        assert response.status_code == 404

    def test_guest_cannot_request_explanation_for_a_private_analysis(self, client, register_user):
        register_user()
        cat = _upload(client)
        client.post("/api/v1/auth/logout")

        response = client.post(f"/api/v1/analyses/{cat['id']}/explanation")
        assert response.status_code == 404

    def test_public_analysis_explanation_is_accessible_to_a_guest(self, client, register_user):
        register_user()
        cat = _upload(client)
        client.post(f"/api/v1/analyses/{cat['id']}/share")
        client.post("/api/v1/auth/logout")

        response = client.post(f"/api/v1/analyses/{cat['id']}/explanation")
        assert response.status_code == 200
        assert response.json()["mode"] == "trained"

    def test_guest_can_request_explanation_for_their_own_unowned_analysis(self, client):
        cat = _upload(client)  # guest, unowned but visible to this same session
        response = client.post(f"/api/v1/analyses/{cat['id']}/explanation")
        # Guest-created analyses aren't "owned" by anyone yet and aren't
        # public either — same visibility rule as GET /analyses/{id}:
        # a guest can't re-fetch its own unclaimed analysis by id any
        # more than an explanation can, so this honestly 404s too.
        assert response.status_code == 404


class TestExplanationDemoMode:
    async def test_demo_mode_analysis_never_produces_a_fake_explanation(
        self, client, register_user, db_session
    ):
        register_user()
        analysis_id = await _insert_demo_mode_analysis(db_session)

        response = client.post(f"/api/v1/analyses/{analysis_id}/explanation")
        assert response.status_code == 404  # not owned by this session's user

    async def test_demo_mode_owned_analysis_reports_unavailable_honestly(
        self, client, register_user, db_session
    ):
        user = register_user()
        row = CatAnalysisModel(
            user_id=uuid.UUID(user["id"]),
            breed_label="Bengal",
            breed_confidence=0.79,
            breed_mode="demo",
            colors=[{"name": "orange", "hex": "#D98B4B", "percentage": 100.0}],
            colors_mode="demo",
            profile={
                "name": "Test",
                "title": "Test",
                "personality": "Test.",
                "magic_power": "Test.",
                "kingdom": "Test",
                "favorite_activity": "Test",
                "favorite_food": "Test",
                "favorite_season": "Summer",
                "rarity": "Common",
                "description": "Test.",
            },
            profile_mode="demo",
            cat_name="Test",
            rarity="Common",
            image_url="/media/does-not-matter.jpg",
        )
        db_session.add(row)
        await db_session.commit()
        await db_session.refresh(row)

        response = client.post(f"/api/v1/analyses/{row.id}/explanation")
        assert response.status_code == 200
        body = response.json()
        assert body["mode"] == "unavailable"
        assert body["reason"] == "Grad-CAM requires the trained breed model."
        assert body["heatmap_url"] is None
        assert body["overlay_url"] is None
        assert body["confidence"] is None

    async def test_missing_stored_photo_reports_unavailable_honestly(
        self, client, register_user, db_session
    ):
        user = register_user()
        row = CatAnalysisModel(
            user_id=uuid.UUID(user["id"]),
            breed_label="Bengal",
            breed_confidence=0.79,
            breed_mode="trained",
            colors=[{"name": "orange", "hex": "#D98B4B", "percentage": 100.0}],
            colors_mode="trained",
            profile={
                "name": "Test",
                "title": "Test",
                "personality": "Test.",
                "magic_power": "Test.",
                "kingdom": "Test",
                "favorite_activity": "Test",
                "favorite_food": "Test",
                "favorite_season": "Summer",
                "rarity": "Common",
                "description": "Test.",
            },
            profile_mode="demo",
            cat_name="Test",
            rarity="Common",
            image_url=None,  # never persisted (e.g. storage was down at analyze time)
        )
        db_session.add(row)
        await db_session.commit()
        await db_session.refresh(row)

        response = client.post(f"/api/v1/analyses/{row.id}/explanation")
        assert response.status_code == 200
        body = response.json()
        assert body["mode"] == "unavailable"
        assert body["reason"] == "The original photo isn't available for this cat."
