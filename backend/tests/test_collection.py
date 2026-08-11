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


class TestCollectionEndpoint:
    def test_requires_authentication(self, client):
        assert client.get("/api/v1/me/collection").status_code == 401

    def test_empty_collection_for_a_new_user(self, client, register_user):
        register_user()
        response = client.get("/api/v1/me/collection")
        assert response.status_code == 200
        body = response.json()
        assert body["items"] == []
        assert body["total"] == 0

    def test_only_shows_the_current_users_own_cats(self, client, register_user):
        register_user(display_name="A")
        _upload(client)
        _upload(client)
        client.post("/api/v1/auth/logout")

        register_user(display_name="B")
        _upload(client)

        response = client.get("/api/v1/me/collection")
        assert response.json()["total"] == 1

    def test_favorites_only_filter(self, client, register_user):
        register_user()
        cat1 = _upload(client)
        _upload(client)
        client.post(f"/api/v1/analyses/{cat1['id']}/favorite")

        response = client.get("/api/v1/me/collection", params={"favorites_only": True})
        body = response.json()
        assert body["total"] == 1
        assert body["items"][0]["id"] == cat1["id"]

    def test_search_matches_breed_or_cat_name(self, client, register_user):
        register_user()
        cat = _upload(client)
        breed = cat["breed"]["label"]

        response = client.get("/api/v1/me/collection", params={"search": breed[:4]})
        assert response.json()["total"] >= 1

        no_match = client.get("/api/v1/me/collection", params={"search": "zzzznomatchzzzz"})
        assert no_match.json()["total"] == 0

    def test_rarity_filter(self, client, register_user):
        register_user()
        cat = _upload(client)
        rarity = cat["profile"]["rarity"]

        matching = client.get("/api/v1/me/collection", params={"rarity": rarity})
        assert matching.json()["total"] >= 1

        other_rarities = {"Common", "Uncommon", "Rare", "Epic", "Legendary", "Mythical"} - {rarity}
        for other in other_rarities:
            response = client.get("/api/v1/me/collection", params={"rarity": other})
            for item in response.json()["items"]:
                assert item["profile"]["rarity"] == other

    def test_sort_newest_orders_by_created_at_descending(self, client, register_user):
        register_user()
        first = _upload(client)
        second = _upload(client)

        response = client.get("/api/v1/me/collection", params={"sort": "newest"})
        ids = [item["id"] for item in response.json()["items"]]
        assert ids.index(second["id"]) < ids.index(first["id"])

    def test_pagination_page_size(self, client, register_user):
        register_user()
        for _ in range(3):
            _upload(client)

        response = client.get("/api/v1/me/collection", params={"page": 1, "page_size": 2})
        body = response.json()
        assert len(body["items"]) == 2
        assert body["total"] == 3


class TestStats:
    def test_requires_authentication(self, client):
        assert client.get("/api/v1/me/stats").status_code == 401

    def test_stats_reflect_real_data_not_fabricated(self, client, register_user):
        register_user()
        assert client.get("/api/v1/me/stats").json()["total_cats"] == 0

        _upload(client)
        _upload(client)

        stats = client.get("/api/v1/me/stats").json()
        assert stats["total_cats"] == 2
        assert stats["favorite_breed"] is not None
        assert stats["most_common_color"] is not None
        assert stats["favorites_count"] == 0
        assert stats["stories_created"] == 0

    def test_stats_never_count_unowned_guest_analyses(self, client, register_user):
        _upload(client)  # guest, unowned
        _upload(client)  # guest, unowned

        register_user()
        assert client.get("/api/v1/me/stats").json()["total_cats"] == 0

    def test_favorites_count_reflects_real_favorites(self, client, register_user):
        register_user()
        cat = _upload(client)
        _upload(client)
        client.post(f"/api/v1/analyses/{cat['id']}/favorite")

        assert client.get("/api/v1/me/stats").json()["favorites_count"] == 1


class TestAchievements:
    def test_requires_authentication(self, client):
        assert client.get("/api/v1/me/achievements").status_code == 401

    def test_all_achievements_locked_for_a_new_user(self, client, register_user):
        register_user()
        achievements = client.get("/api/v1/me/achievements").json()
        assert len(achievements) >= 5
        assert all(a["unlocked"] is False for a in achievements)

    def test_first_meow_unlocks_after_first_saved_cat(self, client, register_user):
        register_user()
        _upload(client)

        achievements = {a["key"]: a for a in client.get("/api/v1/me/achievements").json()}
        assert achievements["first_meow"]["unlocked"] is True
        assert achievements["first_meow"]["unlocked_at"] is not None
        assert achievements["cat_explorer"]["unlocked"] is False

    def test_cat_explorer_unlocks_after_five_cats(self, client, register_user):
        register_user()
        for _ in range(5):
            _upload(client)

        achievements = {a["key"]: a for a in client.get("/api/v1/me/achievements").json()}
        assert achievements["cat_explorer"]["unlocked"] is True

    def test_achievements_never_unlock_from_other_users_activity(self, client, register_user):
        register_user(display_name="Prolific")
        for _ in range(5):
            _upload(client)
        client.post("/api/v1/auth/logout")

        register_user(display_name="NewUser")
        achievements = {a["key"]: a for a in client.get("/api/v1/me/achievements").json()}
        assert achievements["first_meow"]["unlocked"] is False
        assert achievements["cat_explorer"]["unlocked"] is False
