"""Gamification tests for public cat discovery (Phase 15 spec §25/§26):
CAT_EXPLORED XP idempotency, and the four new achievements. Every event
here reuses the existing collection_events idempotent insert-or-skip
mechanism — no new anti-farming logic, no new table.
"""

import io

from PIL import Image


def _make_jpeg_bytes(size=(256, 256), color=(200, 150, 100)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="JPEG")
    return buf.getvalue()


def _upload_and_share(client, color=(200, 150, 100)) -> dict:
    files = {"file": ("cat.jpg", _make_jpeg_bytes(color=color), "image/jpeg")}
    response = client.post("/api/v1/analyses", files=files)
    assert response.status_code == 200, response.text
    cat = response.json()
    share = client.post(f"/api/v1/analyses/{cat['id']}/share")
    assert share.status_code == 200
    return share.json()


class TestCatExploredXp:
    def test_viewing_a_strangers_public_cat_grants_xp_once(self, client, register_user):
        register_user(display_name="Owner")
        cat = _upload_and_share(client, color=(40, 41, 42))
        client.post("/api/v1/auth/logout")

        register_user(display_name="Explorer")
        first = client.get(f"/api/v1/analyses/{cat['id']}")
        assert first.json()["gamification"]["xp_awarded"] > 0

        second = client.get(f"/api/v1/analyses/{cat['id']}")
        assert second.json()["gamification"]["xp_awarded"] == 0

    def test_viewing_your_own_public_cat_never_grants_explore_xp(self, client, register_user):
        register_user()
        cat = _upload_and_share(client, color=(43, 44, 45))
        response = client.get(f"/api/v1/analyses/{cat['id']}")
        # The owner viewing their own cat should not trigger the
        # "discovering someone else's cat" event at all.
        gam = response.json()["gamification"]
        assert gam is None or gam["xp_awarded"] == 0

    def test_a_guest_viewing_a_public_cat_never_grants_xp(self, client, register_user):
        register_user(display_name="Owner")
        cat = _upload_and_share(client, color=(46, 47, 48))
        client.post("/api/v1/auth/logout")

        response = client.get(f"/api/v1/analyses/{cat['id']}")
        assert response.status_code == 200
        assert response.json()["gamification"] is None

    def test_exploring_multiple_distinct_cats_each_grants_xp_once(self, client, register_user):
        register_user(display_name="Owner")
        cat_a = _upload_and_share(client, color=(50, 51, 52))
        cat_b = _upload_and_share(client, color=(53, 54, 55))
        client.post("/api/v1/auth/logout")

        register_user(display_name="Explorer")
        r1 = client.get(f"/api/v1/analyses/{cat_a['id']}")
        r2 = client.get(f"/api/v1/analyses/{cat_b['id']}")
        assert r1.json()["gamification"]["xp_awarded"] > 0
        assert r2.json()["gamification"]["xp_awarded"] > 0


class TestExploreAchievements:
    def test_first_explorer_unlocks_on_first_public_cat_view(self, client, register_user):
        register_user(display_name="Owner")
        cat = _upload_and_share(client, color=(60, 61, 62))
        client.post("/api/v1/auth/logout")

        register_user(display_name="Explorer")
        client.get(f"/api/v1/analyses/{cat['id']}")

        achievements = client.get("/api/v1/me/achievements").json()
        first_explorer = next(a for a in achievements if a["key"] == "first_explorer")
        assert first_explorer["unlocked"] is True

    def test_curious_whiskers_needs_ten_distinct_public_cats(self, client, register_user):
        register_user(display_name="Owner")
        cats = [_upload_and_share(client, color=(70 + i, 71 + i, 72 + i)) for i in range(10)]
        client.post("/api/v1/auth/logout")

        register_user(display_name="Explorer")
        for cat in cats[:9]:
            client.get(f"/api/v1/analyses/{cat['id']}")

        achievements = client.get("/api/v1/me/achievements").json()
        curious = next(a for a in achievements if a["key"] == "curious_whiskers")
        assert curious["unlocked"] is False
        assert curious["progress_current"] == 9

        client.get(f"/api/v1/analyses/{cats[9]['id']}")
        achievements = client.get("/api/v1/me/achievements").json()
        curious = next(a for a in achievements if a["key"] == "curious_whiskers")
        assert curious["unlocked"] is True

    def test_revisiting_the_same_cat_never_inflates_curious_whiskers_progress(
        self, client, register_user
    ):
        register_user(display_name="Owner")
        cat = _upload_and_share(client, color=(80, 81, 82))
        client.post("/api/v1/auth/logout")

        register_user(display_name="Explorer")
        for _ in range(5):
            client.get(f"/api/v1/analyses/{cat['id']}")

        achievements = client.get("/api/v1/me/achievements").json()
        curious = next(a for a in achievements if a["key"] == "curious_whiskers")
        assert curious["progress_current"] == 1

    def test_breed_seeker_needs_five_distinct_explored_breeds(self, client, register_user):
        # Demo-mode-safe: uses whatever breeds this env's real/demo
        # classifier actually assigns to varied fixture colors — we
        # only assert the achievement responds to real, distinct
        # breed_labels among explored cats, not any specific breed name.
        register_user(display_name="Owner")
        cats = [_upload_and_share(client, color=(90 + i * 10, 40, 200 - i * 10)) for i in range(8)]
        client.post("/api/v1/auth/logout")

        register_user(display_name="Explorer")
        distinct_breeds = set()
        for cat in cats:
            client.get(f"/api/v1/analyses/{cat['id']}")
            distinct_breeds.add(cat["breed"]["label"])

        achievements = client.get("/api/v1/me/achievements").json()
        breed_seeker = next(a for a in achievements if a["key"] == "breed_seeker")
        assert breed_seeker["progress_current"] == min(len(distinct_breeds), 5)
        assert breed_seeker["unlocked"] == (len(distinct_breeds) >= 5)

    def test_color_hunter_progress_reflects_distinct_explored_colors(
        self, client, register_user
    ):
        register_user(display_name="Owner")
        cats = [_upload_and_share(client, color=(100 + i, 5, 5)) for i in range(3)]
        client.post("/api/v1/auth/logout")

        register_user(display_name="Explorer")
        for cat in cats:
            client.get(f"/api/v1/analyses/{cat['id']}")

        achievements = client.get("/api/v1/me/achievements").json()
        color_hunter = next(a for a in achievements if a["key"] == "color_hunter")
        assert color_hunter["progress_current"] >= 1
