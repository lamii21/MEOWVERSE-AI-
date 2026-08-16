"""Phase 15 spec §39's explicit, mandatory privacy regression test:
User A owns a private Cat A. User B (or a guest) must NEVER see Cat A
via /explore, similarity search, or the public cat detail endpoint —
and must never see User A's private fields (email, user_id) anywhere
these public-facing endpoints touch.
"""

import io

from PIL import Image


def _make_jpeg_bytes(size=(256, 256), color=(200, 150, 100)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="JPEG")
    return buf.getvalue()


def _upload(client, color=(200, 150, 100)) -> dict:
    files = {"file": ("cat.jpg", _make_jpeg_bytes(color=color), "image/jpeg")}
    response = client.post("/api/v1/analyses", files=files)
    assert response.status_code == 200, response.text
    return response.json()


class TestExplorePrivacyRegression:
    def test_a_private_cat_never_appears_in_explore_cats(self, client, register_user):
        user_a = register_user(display_name="Owner A")
        private_cat = _upload(client, color=(11, 222, 133))
        # Deliberately never shared — stays private.
        client.post("/api/v1/auth/logout")

        register_user(display_name="Stranger B")
        response = client.get("/api/v1/explore/cats?page_size=60")
        assert response.status_code == 200
        ids = [item["analysis_id"] for item in response.json()["items"]]
        assert private_cat["id"] not in ids
        assert user_a["email"] not in response.text

    def test_a_private_cat_never_appears_in_explore_featured(self, client, register_user):
        register_user(display_name="Owner A")
        private_cat = _upload(client, color=(12, 223, 134))
        client.post("/api/v1/auth/logout")

        register_user(display_name="Stranger B")
        response = client.get("/api/v1/explore/featured")
        assert response.status_code == 200
        ids = [item["analysis_id"] for item in response.json()["cats"]]
        assert private_cat["id"] not in ids

    def test_a_private_cat_never_appears_via_breed_explorer_examples(
        self, client, register_user
    ):
        register_user(display_name="Owner A")
        private_cat = _upload(client, color=(13, 224, 135))
        breed = private_cat["breed"]["label"]
        client.post("/api/v1/auth/logout")

        register_user(display_name="Stranger B")
        response = client.get("/api/v1/explore/breeds")
        assert response.status_code == 200
        entry = next((b for b in response.json() if b["breed"] == breed), None)
        if entry is not None:
            example_ids = [c["analysis_id"] for c in entry["examples"]]
            assert private_cat["id"] not in example_ids

    def test_a_private_cat_never_appears_via_similarity_search(self, client, register_user):
        register_user(display_name="Owner A")
        private_cat = _upload(client, color=(14, 225, 136))
        public_cat = _upload(client, color=(200, 150, 100))
        client.post(f"/api/v1/analyses/{public_cat['id']}/share")
        client.post("/api/v1/auth/logout")

        register_user(display_name="Stranger B")
        response = client.get(f"/api/v1/analyses/{public_cat['id']}/similar?k=20")
        assert response.status_code == 200
        similar_ids = [c["analysis_id"] for c in response.json()["similar_cats"]]
        assert private_cat["id"] not in similar_ids

    def test_strangers_similarity_request_against_a_private_source_cat_is_404(
        self, client, register_user
    ):
        register_user(display_name="Owner A")
        private_cat = _upload(client, color=(15, 226, 137))
        client.post("/api/v1/auth/logout")

        register_user(display_name="Stranger B")
        response = client.get(f"/api/v1/analyses/{private_cat['id']}/similar")
        assert response.status_code == 404

    def test_a_strangers_public_cat_detail_view_never_leaks_owner_email_or_id(
        self, client, register_user
    ):
        owner = register_user(display_name="Owner A")
        public_cat = _upload(client, color=(16, 227, 138))
        client.post(f"/api/v1/analyses/{public_cat['id']}/share")
        client.post("/api/v1/auth/logout")

        register_user(display_name="Stranger B")
        response = client.get(f"/api/v1/analyses/{public_cat['id']}")
        assert response.status_code == 200
        assert owner["email"] not in response.text
        assert "user_id" not in response.json()
        assert "owner" not in response.json()

    def test_a_guest_never_sees_a_private_cat_in_explore_cats(self, client, register_user):
        register_user(display_name="Owner A")
        private_cat = _upload(client, color=(17, 228, 139))
        client.post("/api/v1/auth/logout")

        response = client.get("/api/v1/explore/cats?page_size=60")
        assert response.status_code == 200
        ids = [item["analysis_id"] for item in response.json()["items"]]
        assert private_cat["id"] not in ids

    def test_a_private_cat_never_appears_via_personality_explorer_examples(
        self, client, register_user
    ):
        register_user(display_name="Owner A")
        private_cat = _upload(client, color=(18, 229, 140))
        client.post("/api/v1/auth/logout")

        register_user(display_name="Stranger B")
        response = client.get("/api/v1/explore/personalities")
        assert response.status_code == 200
        for archetype in response.json():
            example_ids = [c["analysis_id"] for c in archetype["examples"]]
            assert private_cat["id"] not in example_ids

    def test_a_private_cat_never_appears_via_color_explorer_examples(
        self, client, register_user
    ):
        register_user(display_name="Owner A")
        private_cat = _upload(client, color=(19, 230, 141))
        client.post("/api/v1/auth/logout")

        register_user(display_name="Stranger B")
        response = client.get("/api/v1/explore/colors")
        assert response.status_code == 200
        for group in response.json():
            example_ids = [c["analysis_id"] for c in group["examples"]]
            assert private_cat["id"] not in example_ids

    def test_unsharing_a_cat_removes_it_from_explore_immediately(self, client, register_user):
        register_user(display_name="Owner A")
        cat = _upload(client, color=(20, 231, 142))
        client.post(f"/api/v1/analyses/{cat['id']}/share")

        visible = client.get("/api/v1/explore/cats?page_size=60")
        assert cat["id"] in [item["analysis_id"] for item in visible.json()["items"]]

        client.post(f"/api/v1/analyses/{cat['id']}/unshare")
        hidden = client.get("/api/v1/explore/cats?page_size=60")
        assert cat["id"] not in [item["analysis_id"] for item in hidden.json()["items"]]
