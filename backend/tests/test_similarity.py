import io

import pytest
from PIL import Image

from app.ml.embedding_model import get_embedding_model


def _make_jpeg_bytes(size=(128, 128), color=(200, 150, 100)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="JPEG")
    return buf.getvalue()


def _upload(client, color=(200, 150, 100)) -> dict:
    files = {"file": ("cat.jpg", _make_jpeg_bytes(color=color), "image/jpeg")}
    response = client.post("/api/v1/analyses", files=files)
    assert response.status_code == 200, response.text
    return response.json()


@pytest.fixture(autouse=True)
def _skip_if_embedding_model_unavailable():
    if not get_embedding_model().is_available:
        pytest.skip("Embedding model unavailable in this environment (no torch/torchvision).")


def _similar(client, analysis_id, **params):
    response = client.get(f"/api/v1/analyses/{analysis_id}/similar", params=params)
    assert response.status_code == 200, response.text
    return response.json()


class TestBasicSearch:
    def test_analysis_not_found_is_404(self, client, register_user):
        register_user()
        response = client.get(
            "/api/v1/analyses/00000000-0000-0000-0000-000000000000/similar"
        )
        assert response.status_code == 404

    def test_search_mode_is_embedding_when_the_model_and_index_are_available(
        self, client, register_user
    ):
        register_user()
        cat = _upload(client)
        assert cat["embedding_available"] is True
        result = _similar(client, cat["id"])
        assert result["search_mode"] == "embedding"
        assert result["embedding_model"] is not None

    def test_source_cat_never_appears_in_its_own_results(self, client, register_user):
        register_user()
        cat = _upload(client, color=(10, 20, 30))
        for i in range(3):
            _upload(client, color=(10, 20, 30 + i * 40))
        result = _similar(client, cat["id"], k=20)
        ids = [c["analysis_id"] for c in result["similar_cats"]]
        assert cat["id"] not in ids

    def test_k_limits_the_number_of_results(self, client, register_user):
        register_user()
        cat = _upload(client, color=(10, 20, 30))
        for i in range(5):
            _upload(client, color=(10 + i * 5, 20, 30))
        result = _similar(client, cat["id"], k=2)
        assert len(result["similar_cats"]) <= 2

    def test_k_is_capped_at_20_even_if_a_larger_value_is_requested(self, client, register_user):
        register_user()
        cat = _upload(client)
        response = client.get(f"/api/v1/analyses/{cat['id']}/similar", params={"k": 9999})
        assert response.status_code == 422  # Query(le=20) rejects it outright

    def test_results_are_ordered_by_similarity_descending(self, client, register_user):
        register_user()
        cat = _upload(client, color=(10, 20, 30))
        for i in range(4):
            _upload(client, color=(10, 20, 30 + i * 20))
        result = _similar(client, cat["id"], k=10)
        scores = [c["visual_similarity"] for c in result["similar_cats"]]
        assert scores == sorted(scores, reverse=True)

    def test_a_brand_new_user_with_no_favorites_gets_an_empty_but_valid_result(
        self, client, register_user
    ):
        # The FAISS index and cat_analyses table both accumulate across
        # the whole test session (same accepted pattern as every other
        # test file in this suite — see conftest.py's `db_session`
        # docstring), so "not enough indexed cats" can't be produced
        # deterministically by just uploading one cat: other tests'
        # public/shared cats may already be visually close to it. A
        # `favorites_only` filter on a brand-new user *is* deterministic
        # regardless of accumulated global state, since it can only ever
        # match cats this specific user has both discovered AND
        # favorited — impossible immediately after registering.
        register_user()
        cat = _upload(client)
        result = _similar(client, cat["id"], favorites_only=True)
        assert result["search_mode"] == "embedding"
        assert result["similar_cats"] == []


class TestDuplicateImages:
    def test_identical_image_analyzed_twice_finds_a_near_perfect_match(self, client, register_user):
        register_user()
        first = _upload(client, color=(77, 88, 99))
        second = _upload(client, color=(77, 88, 99))  # identical bytes

        result = _similar(client, first["id"], k=5)
        assert result["similar_cats"], "expected at least the duplicate to be found"
        top = result["similar_cats"][0]
        assert top["analysis_id"] == second["id"]
        assert top["visual_similarity"] == pytest.approx(1.0, abs=1e-4)


class TestPrivacy:
    def test_guest_cannot_search_from_a_private_analysis(self, client, register_user):
        register_user()
        cat = _upload(client)
        client.post("/api/v1/auth/logout")

        response = client.get(f"/api/v1/analyses/{cat['id']}/similar")
        assert response.status_code == 404

    def test_private_cats_never_appear_in_another_users_results(self, client, register_user):
        register_user(display_name="Owner")
        owner_cat = _upload(client, color=(1, 2, 3))
        client.post("/api/v1/auth/logout")

        register_user(display_name="Stranger")
        stranger_cat = _upload(client, color=(1, 2, 4))  # visually close on purpose

        result = _similar(client, stranger_cat["id"], k=20)
        ids = [c["analysis_id"] for c in result["similar_cats"]]
        assert owner_cat["id"] not in ids

    def test_public_cats_are_visible_to_other_users(self, client, register_user):
        register_user(display_name="Owner")
        owner_cat = _upload(client, color=(1, 2, 3))
        client.post(f"/api/v1/analyses/{owner_cat['id']}/share")
        client.post("/api/v1/auth/logout")

        register_user(display_name="Searcher")
        searcher_cat = _upload(client, color=(1, 2, 4))

        result = _similar(client, searcher_cat["id"], k=20)
        ids = [c["analysis_id"] for c in result["similar_cats"]]
        assert owner_cat["id"] in ids

    def test_a_strangers_favorite_status_is_never_leaked(self, client, register_user):
        register_user(display_name="Owner")
        owner_cat = _upload(client, color=(1, 2, 3))
        client.post(f"/api/v1/analyses/{owner_cat['id']}/favorite")
        client.post(f"/api/v1/analyses/{owner_cat['id']}/share")
        client.post("/api/v1/auth/logout")

        register_user(display_name="Searcher")
        searcher_cat = _upload(client, color=(1, 2, 4))
        result = _similar(client, searcher_cat["id"], k=20)
        matches = [c for c in result["similar_cats"] if c["analysis_id"] == owner_cat["id"]]
        assert matches and matches[0]["is_favorite"] is False

    def test_guest_search_only_returns_public_cats(self, client, register_user):
        register_user(display_name="Owner")
        private_cat = _upload(client, color=(5, 6, 7))
        public_cat = _upload(client, color=(5, 6, 8))
        client.post(f"/api/v1/analyses/{public_cat['id']}/share")
        client.post("/api/v1/auth/logout")

        result = _similar(client, public_cat["id"], k=20)
        ids = [c["analysis_id"] for c in result["similar_cats"]]
        assert private_cat["id"] not in ids


class TestFilters:
    def test_rarity_filter_is_applied_after_retrieval(self, client, register_user):
        register_user()
        cat = _upload(client, color=(9, 9, 9))
        other = _upload(client, color=(9, 9, 10))

        result = _similar(client, cat["id"], k=20, rarity=other["profile"]["rarity"])
        for candidate in result["similar_cats"]:
            assert candidate["rarity"] == other["profile"]["rarity"]

    def test_unrecognized_rarity_filter_yields_no_match_not_an_error(self, client, register_user):
        register_user()
        cat = _upload(client)
        _upload(client, color=(9, 9, 10))
        result = _similar(client, cat["id"], k=20, rarity="NotARealRarity")
        assert result["similar_cats"] == []
