"""Tests the actual similarity mathematics (Phase 11 spec §28), not
just HTTP responses — controlled, hand-built vectors with known
relationships, so every assertion has a known-correct expected value.
"""

import numpy as np
import pytest

from app.similarity.vector_index import FAISSVectorIndex


def _unit(vector: list[float]) -> np.ndarray:
    array = np.asarray(vector, dtype=np.float32)
    return array / np.linalg.norm(array)


@pytest.fixture
def index(tmp_path):
    return FAISSVectorIndex(dimension=4, index_path=str(tmp_path / "test.faiss"))


class TestCosineSimilarityMath:
    def test_identical_vectors_have_maximal_similarity(self, index):
        v = _unit([1.0, 2.0, 3.0, 4.0])
        index.add(1, v)
        results = index.search(v, k=1)
        assert results[0][0] == 1
        assert results[0][1] == pytest.approx(1.0, abs=1e-5)

    def test_orthogonal_vectors_have_zero_similarity(self, index):
        a = _unit([1.0, 0.0, 0.0, 0.0])
        b = _unit([0.0, 1.0, 0.0, 0.0])
        index.add(1, a)
        results = index.search(b, k=1)
        assert results[0][1] == pytest.approx(0.0, abs=1e-5)

    def test_opposite_vectors_have_negative_similarity(self, index):
        a = _unit([1.0, 0.0, 0.0, 0.0])
        b = _unit([-1.0, 0.0, 0.0, 0.0])
        index.add(1, a)
        results = index.search(b, k=1)
        assert results[0][1] == pytest.approx(-1.0, abs=1e-5)

    def test_closer_vector_ranks_above_farther_vector(self, index):
        query = _unit([1.0, 0.0, 0.0, 0.0])
        close = _unit([0.95, 0.05, 0.0, 0.0])  # small angle from query
        far = _unit([0.1, 0.9, 0.3, 0.2])  # large angle from query
        index.add(1, close)
        index.add(2, far)

        results = index.search(query, k=2)
        ids_in_order = [vector_id for vector_id, _ in results]
        assert ids_in_order == [1, 2]
        assert results[0][1] > results[1][1]


class TestVectorIndexOperations:
    def test_search_on_empty_index_returns_nothing(self, index):
        assert index.search(_unit([1.0, 0.0, 0.0, 0.0]), k=5) == []

    def test_k_is_capped_at_index_size(self, index):
        index.add(1, _unit([1.0, 0.0, 0.0, 0.0]))
        index.add(2, _unit([0.0, 1.0, 0.0, 0.0]))
        results = index.search(_unit([1.0, 0.0, 0.0, 0.0]), k=50)
        assert len(results) == 2

    def test_remove_makes_a_vector_unfindable(self, index):
        index.add(1, _unit([1.0, 0.0, 0.0, 0.0]))
        index.add(2, _unit([0.0, 1.0, 0.0, 0.0]))
        index.remove(1)
        results = index.search(_unit([1.0, 0.0, 0.0, 0.0]), k=5)
        assert 1 not in [vector_id for vector_id, _ in results]

    def test_size_reflects_real_vector_count(self, index):
        assert index.size == 0
        index.add(1, _unit([1.0, 0.0, 0.0, 0.0]))
        assert index.size == 1
        index.add(2, _unit([0.0, 1.0, 0.0, 0.0]))
        assert index.size == 2
        index.remove(1)
        assert index.size == 1

    def test_get_vector_reconstructs_a_previously_added_vector(self, index):
        original = _unit([1.0, 2.0, 3.0, 4.0])
        index.add(1, original)
        reconstructed = index.get_vector(1)
        assert reconstructed is not None
        np.testing.assert_allclose(reconstructed, original, atol=1e-5)

    def test_get_vector_returns_none_for_unknown_id(self, index):
        assert index.get_vector(999) is None

    def test_rebuild_replaces_all_contents(self, index):
        index.add(1, _unit([1.0, 0.0, 0.0, 0.0]))
        index.rebuild([(2, _unit([0.0, 1.0, 0.0, 0.0])), (3, _unit([0.0, 0.0, 1.0, 0.0]))])
        assert index.size == 2
        assert index.get_vector(1) is None
        assert index.get_vector(2) is not None


class TestPersistence:
    def test_index_survives_a_reload_from_the_same_path(self, tmp_path):
        path = str(tmp_path / "persist.faiss")
        first = FAISSVectorIndex(dimension=4, index_path=path)
        vector = _unit([1.0, 2.0, 3.0, 4.0])
        first.add(42, vector)

        second = FAISSVectorIndex(dimension=4, index_path=path)
        assert second.size == 1
        reconstructed = second.get_vector(42)
        assert reconstructed is not None
        np.testing.assert_allclose(reconstructed, vector, atol=1e-5)

    def test_a_fresh_path_starts_as_an_empty_but_available_index(self, tmp_path):
        idx = FAISSVectorIndex(dimension=4, index_path=str(tmp_path / "brand_new.faiss"))
        assert idx.is_available is True
        assert idx.size == 0

    def test_corrupt_index_file_is_reported_unavailable_not_crashed(self, tmp_path):
        path = tmp_path / "corrupt.faiss"
        path.write_bytes(b"not a real faiss index file")
        idx = FAISSVectorIndex(dimension=4, index_path=str(path))
        assert idx.is_available is False
        assert idx.size == 0

    def test_dimension_mismatch_is_reported_unavailable_not_silently_wrong(self, tmp_path):
        path = str(tmp_path / "dim_test.faiss")
        FAISSVectorIndex(dimension=4, index_path=path).add(1, _unit([1.0, 0.0, 0.0, 0.0]))

        mismatched = FAISSVectorIndex(dimension=8, index_path=path)
        assert mismatched.is_available is False
