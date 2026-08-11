import io

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


class TestDiscoveryXP:
    def test_discovering_a_cat_awards_xp_and_may_unlock_first_paw(self, client, register_user):
        register_user()
        cat = _upload(client)

        gam = cat["gamification"]
        assert gam is not None
        # 100 XP for the discovery itself, plus 50 more for the
        # first_meow ("First Paw") achievement unlocking in the same
        # event — see app/services/gamification.py.
        assert gam["xp_awarded"] == 150
        assert gam["total_xp"] == 150
        assert gam["level"] == 2
        assert gam["leveled_up"] is True
        assert any(a["key"] == "first_meow" for a in gam["newly_unlocked"])

        progress = client.get("/api/v1/me/progress").json()
        assert progress["xp"] == 150
        assert progress["level"] == 2

    def test_guest_discovery_awards_no_xp(self, client):
        cat = _upload(client)
        assert cat["gamification"] is None

    def test_new_breed_flag_only_true_on_the_first_occurrence(self, client, register_user):
        register_user()
        first = _upload(client, color=(10, 10, 10))
        second = _upload(client, color=(10, 10, 10))  # same bytes -> same demo breed

        assert first["gamification"]["is_new_breed"] is True
        assert second["gamification"]["is_new_breed"] is False


class TestFavoriteAndShareXP:
    def test_favoriting_grants_xp_exactly_once(self, client, register_user):
        register_user()
        cat = _upload(client)
        xp_after_discovery = cat["gamification"]["total_xp"]

        first = client.post(f"/api/v1/analyses/{cat['id']}/favorite").json()
        assert first["gamification"]["xp_awarded"] > 0
        xp_after_favorite = first["gamification"]["total_xp"]
        assert xp_after_favorite > xp_after_discovery

        # Re-favoriting (already favorited) must not grant XP again.
        second = client.post(f"/api/v1/analyses/{cat['id']}/favorite").json()
        assert second["gamification"]["xp_awarded"] == 0
        assert second["gamification"]["total_xp"] == xp_after_favorite

    def test_unfavorite_then_refavorite_does_not_regrant_xp(self, client, register_user):
        register_user()
        cat = _upload(client)
        first = client.post(f"/api/v1/analyses/{cat['id']}/favorite").json()
        xp_after_first_favorite = first["gamification"]["total_xp"]

        client.post(f"/api/v1/analyses/{cat['id']}/unfavorite")
        second = client.post(f"/api/v1/analyses/{cat['id']}/favorite").json()
        assert second["gamification"]["xp_awarded"] == 0
        assert second["gamification"]["total_xp"] == xp_after_first_favorite

    def test_sharing_grants_xp_exactly_once(self, client, register_user):
        register_user()
        cat = _upload(client)
        first = client.post(f"/api/v1/analyses/{cat['id']}/share").json()
        assert first["gamification"]["xp_awarded"] > 0
        xp_after_share = first["gamification"]["total_xp"]

        second = client.post(f"/api/v1/analyses/{cat['id']}/share").json()
        assert second["gamification"]["xp_awarded"] == 0
        assert second["gamification"]["total_xp"] == xp_after_share


class TestStoryXP:
    def test_story_generation_grants_xp_once_per_cat_not_per_regenerate(
        self, client, register_user
    ):
        register_user()
        cat = _upload(client)

        first = client.post(
            f"/api/v1/analyses/{cat['id']}/story", json={"style": "magical_adventure"}
        ).json()
        assert first["gamification"] is not None
        assert first["gamification"]["xp_awarded"] > 0
        xp_after_first_story = first["gamification"]["total_xp"]

        regenerated = client.post(
            f"/api/v1/analyses/{cat['id']}/story",
            json={"style": "magical_adventure", "regenerate": True},
        ).json()
        assert regenerated["gamification"]["xp_awarded"] == 0
        assert regenerated["gamification"]["total_xp"] == xp_after_first_story

        different_style = client.post(
            f"/api/v1/analyses/{cat['id']}/story", json={"style": "cozy_wholesome"}
        ).json()
        assert different_style["gamification"]["xp_awarded"] == 0

    def test_guest_story_generation_awards_no_xp(self, client):
        cat = _upload(client)  # unowned
        story = client.post(
            f"/api/v1/analyses/{cat['id']}/story", json={"style": "magical_adventure"}
        ).json()
        assert story["gamification"] is None

    def test_generating_a_story_for_someone_elses_cat_awards_no_xp(self, client, register_user):
        register_user(display_name="Owner")
        cat = _upload(client)
        client.post("/api/v1/auth/logout")

        register_user(display_name="Stranger")
        story = client.post(
            f"/api/v1/analyses/{cat['id']}/story", json={"style": "magical_adventure"}
        ).json()
        assert story["gamification"] is None

    def test_dream_keeper_unlocks_only_for_dreamy_style(self, client, register_user):
        register_user()
        cat = _upload(client)

        client.post(f"/api/v1/analyses/{cat['id']}/story", json={"style": "magical_adventure"})
        locked = {a["key"]: a for a in client.get("/api/v1/me/achievements").json()}
        assert locked["dream_keeper"]["unlocked"] is False

        client.post(f"/api/v1/analyses/{cat['id']}/story", json={"style": "dreamy_emotional"})
        unlocked = {a["key"]: a for a in client.get("/api/v1/me/achievements").json()}
        assert unlocked["dream_keeper"]["unlocked"] is True

    def test_storyteller_needs_five_distinct_cats_not_five_regenerates(self, client, register_user):
        register_user()
        cat = _upload(client)
        for _ in range(4):
            client.post(
                f"/api/v1/analyses/{cat['id']}/story",
                json={"style": "magical_adventure", "regenerate": True},
            )

        achievements = {a["key"]: a for a in client.get("/api/v1/me/achievements").json()}
        assert achievements["storyteller"]["unlocked"] is False

        for i in range(4):
            other = _upload(client, color=(i * 30, 50, 80))
            client.post(
                f"/api/v1/analyses/{other['id']}/story", json={"style": "magical_adventure"}
            )

        achievements = {a["key"]: a for a in client.get("/api/v1/me/achievements").json()}
        assert achievements["storyteller"]["unlocked"] is True


class TestBreedExplorer:
    def test_requires_authentication(self, client):
        assert client.get("/api/v1/me/breeds").status_code == 401

    def test_all_breeds_locked_for_a_new_user(self, client, register_user):
        register_user()
        breeds = client.get("/api/v1/me/breeds").json()
        assert len(breeds) > 0
        assert all(b["discovered"] is False for b in breeds)
        assert all(b["count"] == 0 for b in breeds)
        assert all(b["best_confidence"] is None for b in breeds)

    def test_discovery_reflects_in_the_breed_explorer(self, client, register_user):
        register_user()
        cat = _upload(client)
        breed_label = cat["breed"]["label"]

        breeds = {b["breed"]: b for b in client.get("/api/v1/me/breeds").json()}
        if breed_label in breeds:  # only canonical breeds appear in the explorer
            assert breeds[breed_label]["discovered"] is True
            assert breeds[breed_label]["count"] == 1
            assert breeds[breed_label]["best_confidence"] is not None
            assert breeds[breed_label]["latest_discovery"] is not None

    def test_duplicate_breed_does_not_inflate_unique_breed_completion(self, client, register_user):
        register_user()
        _upload(client, color=(5, 5, 5))
        stats_after_one = client.get("/api/v1/me/stats").json()

        _upload(client, color=(5, 5, 5))  # identical bytes -> identical demo breed
        stats_after_two = client.get("/api/v1/me/stats").json()

        assert stats_after_two["total_cats"] == 2
        assert (
            stats_after_two["unique_breeds_discovered"]
            == stats_after_one["unique_breeds_discovered"]
        )

    def test_breeds_never_leak_across_users(self, client, register_user):
        register_user(display_name="A")
        _upload(client)
        client.post("/api/v1/auth/logout")

        register_user(display_name="B")
        breeds = client.get("/api/v1/me/breeds").json()
        assert all(b["discovered"] is False for b in breeds)


class TestCompletionAndDistribution:
    def test_completion_percentage_matches_formula(self, client, register_user):
        register_user()
        _upload(client)
        stats = client.get("/api/v1/me/stats").json()

        expected = round(
            100 * stats["unique_breeds_discovered"] / stats["total_supported_breeds"], 1
        )
        assert stats["completion_percentage"] == expected

    def test_completion_percentage_zero_for_new_user(self, client, register_user):
        register_user()
        stats = client.get("/api/v1/me/stats").json()
        assert stats["completion_percentage"] == 0.0
        assert stats["unique_breeds_discovered"] == 0

    def test_rarity_distribution_is_zero_filled_and_sums_to_total(self, client, register_user):
        register_user()
        empty = client.get("/api/v1/me/stats").json()["rarity_distribution"]
        assert set(empty.keys()) == {"Common", "Uncommon", "Rare", "Epic", "Legendary", "Mythical"}
        assert sum(empty.values()) == 0

        cat = _upload(client)
        rarity = cat["profile"]["rarity"]
        stats = client.get("/api/v1/me/stats").json()
        assert stats["rarity_distribution"][rarity] >= 1
        assert sum(stats["rarity_distribution"].values()) == stats["total_cats"]


class TestProgressEndpoint:
    def test_requires_authentication(self, client):
        assert client.get("/api/v1/me/progress").status_code == 401

    def test_new_user_starts_at_level_one_zero_xp(self, client, register_user):
        register_user()
        progress = client.get("/api/v1/me/progress").json()
        assert progress["xp"] == 0
        assert progress["level"] == 1
        assert progress["level_title"]

    def test_progress_never_leaks_across_users(self, client, register_user):
        register_user(display_name="A")
        _upload(client)
        client.post("/api/v1/auth/logout")

        register_user(display_name="B")
        progress = client.get("/api/v1/me/progress").json()
        assert progress["xp"] == 0
        assert progress["level"] == 1
