import io

from PIL import Image


def _make_jpeg_bytes(size=(128, 128), color=(200, 150, 100)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="JPEG")
    return buf.getvalue()


def _upload(client) -> dict:
    files = {"file": ("cat.jpg", _make_jpeg_bytes(), "image/jpeg")}
    response = client.post("/api/v1/analyses", files=files)
    assert response.status_code == 200
    return response.json()


class TestGuestVsAuthenticatedCreation:
    def test_guest_analysis_is_unowned(self, client):
        body = _upload(client)
        assert body["owned"] is False
        assert body["id"] is not None  # still persisted — just unclaimed

    def test_authenticated_analysis_is_auto_owned(self, client, register_user):
        register_user()
        body = _upload(client)
        assert body["owned"] is True


class TestPrivateAccessControl:
    def test_guest_cannot_view_someone_elses_private_cat(self, client, register_user):
        register_user()
        owned = _upload(client)

        client.post("/api/v1/auth/logout")
        response = client.get(f"/api/v1/analyses/{owned['id']}")
        assert response.status_code == 404

    def test_owner_can_view_their_own_private_cat(self, client, register_user):
        register_user()
        owned = _upload(client)

        response = client.get(f"/api/v1/analyses/{owned['id']}")
        assert response.status_code == 200
        assert response.json()["owned"] is True

    def test_a_different_user_cannot_view_someone_elses_private_cat(self, client, register_user):
        register_user(display_name="Owner")
        owned = _upload(client)
        client.post("/api/v1/auth/logout")

        register_user(display_name="Intruder")
        response = client.get(f"/api/v1/analyses/{owned['id']}")
        assert response.status_code == 404

    def test_nonexistent_analysis_returns_404_not_a_crash(self, client, register_user):
        register_user()
        fake_id = "00000000-0000-0000-0000-000000000000"
        assert client.get(f"/api/v1/analyses/{fake_id}").status_code == 404


class TestSaveClaimFlow:
    def test_guest_can_claim_their_analysis_after_registering(self, client, register_user):
        guest_result = _upload(client)
        assert guest_result["owned"] is False

        register_user()
        response = client.post(f"/api/v1/analyses/{guest_result['id']}/save")
        assert response.status_code == 200
        assert response.json()["owned"] is True

        # And it now shows as owned on a fresh fetch too.
        assert client.get(f"/api/v1/analyses/{guest_result['id']}").json()["owned"] is True

    def test_save_requires_authentication(self, client):
        guest_result = _upload(client)
        response = client.post(f"/api/v1/analyses/{guest_result['id']}/save")
        assert response.status_code == 401

    def test_cannot_claim_an_already_owned_analysis(self, client, register_user):
        register_user(display_name="Owner")
        owned = _upload(client)
        client.post("/api/v1/auth/logout")

        register_user(display_name="Claimant")
        response = client.post(f"/api/v1/analyses/{owned['id']}/save")
        assert response.status_code == 409

    def test_cannot_claim_own_analysis_twice(self, client, register_user):
        register_user()
        owned = _upload(client)  # already auto-owned
        response = client.post(f"/api/v1/analyses/{owned['id']}/save")
        assert response.status_code == 409

    def test_claiming_a_nonexistent_analysis_returns_404(self, client, register_user):
        register_user()
        fake_id = "00000000-0000-0000-0000-000000000000"
        assert client.post(f"/api/v1/analyses/{fake_id}/save").status_code == 404


class TestFavorites:
    def test_favorite_and_unfavorite_round_trip(self, client, register_user):
        register_user()
        owned = _upload(client)

        fav_response = client.post(f"/api/v1/analyses/{owned['id']}/favorite")
        assert fav_response.status_code == 200
        assert fav_response.json()["is_favorite"] is True

        unfav_response = client.post(f"/api/v1/analyses/{owned['id']}/unfavorite")
        assert unfav_response.status_code == 200
        assert unfav_response.json()["is_favorite"] is False

    def test_favorite_requires_authentication(self, client):
        guest_result = _upload(client)
        assert client.post(f"/api/v1/analyses/{guest_result['id']}/favorite").status_code == 401

    def test_cannot_favorite_someone_elses_cat(self, client, register_user):
        register_user(display_name="Owner")
        owned = _upload(client)
        client.post("/api/v1/auth/logout")

        register_user(display_name="Stranger")
        response = client.post(f"/api/v1/analyses/{owned['id']}/favorite")
        assert response.status_code == 404


class TestSharingRespectsOwnership:
    def test_share_requires_authentication(self, client):
        guest_result = _upload(client)
        assert client.post(f"/api/v1/analyses/{guest_result['id']}/share").status_code == 401

    def test_cannot_share_someone_elses_cat(self, client, register_user):
        register_user(display_name="Owner")
        owned = _upload(client)
        client.post("/api/v1/auth/logout")

        register_user(display_name="Stranger")
        response = client.post(f"/api/v1/analyses/{owned['id']}/share")
        assert response.status_code == 404

    def test_owner_can_share_and_unshare(self, client, register_user):
        register_user()
        owned = _upload(client)

        share_response = client.post(f"/api/v1/analyses/{owned['id']}/share")
        assert share_response.status_code == 200
        assert share_response.json()["is_public"] is True

        # A guest can now see it publicly.
        client.post("/api/v1/auth/logout")
        public_response = client.get(f"/api/v1/analyses/{owned['id']}")
        assert public_response.status_code == 200

    def test_unshare_requires_ownership(self, client, register_user):
        register_user(display_name="Owner")
        owned = _upload(client)
        client.post(f"/api/v1/analyses/{owned['id']}/share")
        client.post("/api/v1/auth/logout")

        register_user(display_name="Stranger")
        response = client.post(f"/api/v1/analyses/{owned['id']}/unshare")
        assert response.status_code == 404

    def test_public_view_never_exposes_favorite_or_owned_status(self, client, register_user):
        """Regression test for a real bug caught during Phase 9
        development: the public /cat/[id] response must never leak the
        owner's private favorite flag or an "owned" signal a careless
        frontend could render as if it belonged to the (anonymous)
        viewer."""
        register_user()
        owned = _upload(client)
        client.post(f"/api/v1/analyses/{owned['id']}/favorite")
        client.post(f"/api/v1/analyses/{owned['id']}/share")
        client.post("/api/v1/auth/logout")

        public_response = client.get(f"/api/v1/analyses/{owned['id']}")
        assert public_response.status_code == 200
        assert public_response.json()["is_favorite"] is False
        assert public_response.json()["owned"] is False

    def test_public_response_never_includes_owner_email_or_user_id(self, client, register_user):
        register_user()
        owned = _upload(client)
        client.post(f"/api/v1/analyses/{owned['id']}/share")
        client.post("/api/v1/auth/logout")

        body = client.get(f"/api/v1/analyses/{owned['id']}").json()
        serialized = str(body)
        assert "@" not in serialized  # no email address anywhere in the payload
        assert "user_id" not in body
