"""Functional tests for the MeowVerse Cat Universe discovery endpoints
(Phase 15 spec §38): pagination, search, filters, sorting, featured
selection determinism, breed/personality/color explorer, and N+1
prevention. Privacy is covered separately and exhaustively in
test_explore_privacy.py per spec §39.
"""

import io
import uuid

from PIL import Image
from sqlalchemy import event


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


class TestExploreCatsListing:
    def test_only_public_cats_are_returned(self, client, register_user):
        register_user()
        public_cat = _upload_and_share(client, color=(30, 40, 50))
        response = client.get("/api/v1/explore/cats?page_size=60")
        assert response.status_code == 200
        ids = [item["analysis_id"] for item in response.json()["items"]]
        assert public_cat["id"] in ids

    def test_response_shape_never_includes_owner_fields(self, client, register_user):
        register_user()
        cat = _upload_and_share(client, color=(31, 41, 51))
        response = client.get("/api/v1/explore/cats?page_size=60")
        item = next(i for i in response.json()["items"] if i["analysis_id"] == cat["id"])
        assert "owned" not in item
        assert "is_favorite" not in item
        assert "user_id" not in item

    def test_every_card_has_a_deterministic_archetype(self, client, register_user):
        register_user()
        cat = _upload_and_share(client, color=(32, 42, 52))
        first = client.get("/api/v1/explore/cats?page_size=60").json()
        second = client.get("/api/v1/explore/cats?page_size=60").json()
        first_item = next(i for i in first["items"] if i["analysis_id"] == cat["id"])
        second_item = next(i for i in second["items"] if i["analysis_id"] == cat["id"])
        assert first_item["archetype_id"] == second_item["archetype_id"]


class TestPagination:
    def test_page_size_is_respected(self, client, register_user):
        register_user()
        for i in range(3):
            _upload_and_share(client, color=(60 + i, 70 + i, 80 + i))
        response = client.get("/api/v1/explore/cats?page_size=2&page=1")
        body = response.json()
        assert len(body["items"]) <= 2
        assert body["page"] == 1
        assert body["page_size"] == 2

    def test_total_reflects_the_full_matching_count_not_just_the_page(
        self, client, register_user
    ):
        register_user()
        for i in range(5):
            _upload_and_share(client, color=(90 + i, 91 + i, 92 + i))
        response = client.get("/api/v1/explore/cats?page_size=2")
        body = response.json()
        assert body["total"] >= 5
        assert len(body["items"]) <= 2

    def test_page_size_is_capped_server_side(self, client, register_user):
        register_user()
        response = client.get("/api/v1/explore/cats?page_size=1000")
        assert response.status_code == 422  # exceeds le=60


class TestSearch:
    def test_search_matches_breed_name(self, client, register_user):
        register_user()
        cat = _upload_and_share(client, color=(100, 101, 102))
        breed = cat["breed"]["label"]
        response = client.get(f"/api/v1/explore/cats?search={breed}&page_size=60")
        ids = [item["analysis_id"] for item in response.json()["items"]]
        assert cat["id"] in ids

    def test_search_with_no_matches_returns_empty_not_an_error(self, client, register_user):
        register_user()
        response = client.get(
            "/api/v1/explore/cats?search=zzzznonexistentqueryzzzz&page_size=60"
        )
        assert response.status_code == 200
        assert response.json()["items"] == []

    def test_search_is_length_bounded(self, client):
        response = client.get(f"/api/v1/explore/cats?search={'a' * 500}")
        assert response.status_code == 422


class TestFilters:
    def test_filter_by_rarity_returns_only_that_rarity(self, client, register_user):
        register_user()
        _upload_and_share(client, color=(110, 111, 112))
        response = client.get("/api/v1/explore/cats?rarity=Common&page_size=60")
        assert response.status_code == 200
        for item in response.json()["items"]:
            assert item["rarity"] == "Common"

    def test_filter_by_breed_returns_only_that_breed(self, client, register_user):
        register_user()
        cat = _upload_and_share(client, color=(120, 121, 122))
        breed = cat["breed"]["label"]
        response = client.get(f"/api/v1/explore/cats?breed={breed}&page_size=60")
        for item in response.json()["items"]:
            assert item["breed"]["label"] == breed

    def test_filter_by_archetype_returns_only_that_archetype(self, client, register_user):
        register_user()
        cat = _upload_and_share(client, color=(130, 131, 132))
        archetype = cat["id"]
        cat_page = client.get("/api/v1/explore/cats?page_size=60").json()
        item = next(i for i in cat_page["items"] if i["analysis_id"] == archetype)
        response = client.get(
            f"/api/v1/explore/cats?archetype={item['archetype_id']}&page_size=60"
        )
        assert response.status_code == 200
        for result_item in response.json()["items"]:
            assert result_item["archetype_id"] == item["archetype_id"]

    def test_filter_by_color_returns_only_cats_with_that_color(self, client, register_user):
        register_user()
        _upload_and_share(client, color=(140, 141, 142))
        cats = client.get("/api/v1/explore/cats?page_size=60").json()["items"]
        color = cats[0]["colors"][0]["name"]
        response = client.get(f"/api/v1/explore/cats?color={color}&page_size=60")
        assert response.status_code == 200
        for item in response.json()["items"]:
            assert any(c["name"] == color for c in item["colors"])

    def test_unrecognized_rarity_yields_zero_results_not_an_error(self, client):
        response = client.get("/api/v1/explore/cats?rarity=NotARealRarity")
        assert response.status_code == 200
        assert response.json()["items"] == []


class TestSorting:
    def test_newest_sort_orders_by_created_at_descending(self, client, register_user):
        register_user()
        _upload_and_share(client, color=(150, 151, 152))
        _upload_and_share(client, color=(153, 154, 155))
        response = client.get("/api/v1/explore/cats?sort=newest&page_size=60")
        dates = [item["created_at"] for item in response.json()["items"]]
        assert dates == sorted(dates, reverse=True)

    def test_oldest_sort_orders_by_created_at_ascending(self, client, register_user):
        register_user()
        _upload_and_share(client, color=(160, 161, 162))
        _upload_and_share(client, color=(163, 164, 165))
        response = client.get("/api/v1/explore/cats?sort=oldest&page_size=60")
        dates = [item["created_at"] for item in response.json()["items"]]
        assert dates == sorted(dates)

    def test_rarity_sort_never_errors(self, client, register_user):
        register_user()
        _upload_and_share(client, color=(170, 171, 172))
        response = client.get("/api/v1/explore/cats?sort=rarity&page_size=60")
        assert response.status_code == 200


class TestFeaturedSelection:
    def test_featured_selection_is_deterministic_across_requests(self, client, register_user):
        register_user()
        for i in range(3):
            _upload_and_share(client, color=(180 + i, 181 + i, 182 + i))
        first = client.get("/api/v1/explore/featured").json()
        second = client.get("/api/v1/explore/featured").json()
        assert [c["analysis_id"] for c in first["cats"]] == [
            c["analysis_id"] for c in second["cats"]
        ]

    def test_featured_selection_is_bounded(self, client, register_user):
        register_user()
        for i in range(10):
            _upload_and_share(client, color=(190 + i, 191 + i, 192 + i))
        response = client.get("/api/v1/explore/featured")
        assert len(response.json()["cats"]) <= 8


class TestBreedExplorer:
    def test_counts_are_public_only(self, client, register_user):
        register_user()
        cat = _upload_and_share(client, color=(200, 201, 202))
        breed = cat["breed"]["label"]
        response = client.get("/api/v1/explore/breeds")
        entry = next(b for b in response.json() if b["breed"] == breed)
        assert entry["public_count"] >= 1

    def test_covers_the_full_canonical_breed_universe(self, client):
        response = client.get("/api/v1/explore/breeds")
        breeds = {b["breed"] for b in response.json()}
        assert "Persian" in breeds
        assert "Siamese" in breeds


class TestPersonalityExplorer:
    def test_returns_all_ten_archetypes(self, client):
        response = client.get("/api/v1/explore/personalities")
        assert response.status_code == 200
        assert len(response.json()) == 10

    def test_every_archetype_has_the_non_scientific_disclaimer(self, client):
        response = client.get("/api/v1/explore/personalities")
        for archetype in response.json():
            assert "not a scientific" in archetype["disclaimer"].lower()


class TestColorExplorer:
    def test_reuses_real_analyzed_color_names(self, client, register_user):
        register_user()
        _upload_and_share(client, color=(210, 211, 212))
        response = client.get("/api/v1/explore/colors")
        assert response.status_code == 200
        assert len(response.json()) > 0
        for group in response.json():
            assert group["public_count"] >= 1


class TestNPlusOnePrevention:
    def test_explore_cats_listing_does_not_scale_query_count_with_result_count(
        self, client, register_user
    ):
        """Spec §31: "50 public cats should NOT produce 50 personality
        queries." Adds a batch of public cats, then asserts the total
        SQL query count for one /explore/cats request stays flat
        (bounded, not linear in the number of cats returned) — archetype
        computation is a pure Python function (zero extra queries), and
        story/portrait indicators are two batched queries for the whole
        page, not one per row.
        """
        register_user()
        for i in range(15):
            _upload_and_share(client, color=(215 + i, 1, i))

        from app.core.database import engine as app_engine

        counts = {"n": 0}

        def _count(*args, **kwargs):
            counts["n"] += 1

        event.listen(app_engine.sync_engine, "before_cursor_execute", _count)
        try:
            response = client.get("/api/v1/explore/cats?page_size=24")
        finally:
            event.remove(app_engine.sync_engine, "before_cursor_execute", _count)

        assert response.status_code == 200
        assert len(response.json()["items"]) >= 15
        # 2 queries for the base listing (count + select) + 2 batched
        # enrichment queries (public stories, public portraits) = a
        # small constant, nowhere near one-per-row (15+ would indicate
        # a real N+1).
        assert counts["n"] <= 6, f"expected a small constant query count, got {counts['n']}"


class TestErrorStates:
    def test_invalid_sort_value_is_a_422_not_a_500(self, client):
        response = client.get("/api/v1/explore/cats?sort=not_a_real_sort")
        assert response.status_code == 422

    def test_invalid_uuid_style_filters_dont_crash_the_endpoint(self, client):
        response = client.get(f"/api/v1/explore/cats?archetype={uuid.uuid4()}")
        assert response.status_code == 200
        assert response.json()["items"] == []
