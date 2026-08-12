import io
import uuid

import pytest
from PIL import Image

import app.services.embedding_service as embedding_service_module
from app.ml.embedding_model import EmbeddingModel, get_embedding_model
from app.repositories import embedding_repository
from app.services.embedding_service import embed_and_index, hash_image_bytes


def _make_jpeg(size=(128, 128), color=(200, 150, 100)) -> tuple[Image.Image, bytes]:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="JPEG")
    image_bytes = buf.getvalue()
    return Image.open(io.BytesIO(image_bytes)), image_bytes


@pytest.fixture(autouse=True)
def _skip_if_embedding_model_unavailable():
    if not get_embedding_model().is_available:
        pytest.skip("Embedding model unavailable in this environment (no torch/torchvision).")


class TestHashDeterminism:
    def test_same_bytes_hash_identically(self):
        _, image_bytes = _make_jpeg(color=(1, 2, 3))
        assert hash_image_bytes(image_bytes) == hash_image_bytes(image_bytes)

    def test_different_bytes_hash_differently(self):
        _, a = _make_jpeg(color=(1, 2, 3))
        _, b = _make_jpeg(color=(4, 5, 6))
        assert hash_image_bytes(a) != hash_image_bytes(b)


class TestDuplicateHandling:
    async def test_duplicate_content_reuses_the_same_vector_id(
        self, db_session, client, register_user
    ):
        # Use the real API so each analysis genuinely exists (FK-valid)
        # rather than hand-constructing rows.
        register_user()
        _, image_bytes = _make_jpeg(color=(11, 22, 33))

        first = client.post(
            "/api/v1/analyses", files={"file": ("cat.jpg", image_bytes, "image/jpeg")}
        ).json()
        second = client.post(
            "/api/v1/analyses", files={"file": ("cat.jpg", image_bytes, "image/jpeg")}
        ).json()

        first_row = await embedding_repository.get_by_analysis_id(
            db_session, uuid.UUID(first["id"])
        )
        second_row = await embedding_repository.get_by_analysis_id(
            db_session, uuid.UUID(second["id"])
        )
        assert first_row is not None
        assert second_row is not None
        assert first_row.vector_id == second_row.vector_id

    async def test_distinct_content_gets_distinct_vector_ids(
        self, db_session, client, register_user
    ):
        register_user()
        first = client.post(
            "/api/v1/analyses",
            files={"file": ("a.jpg", _make_jpeg(color=(11, 22, 33))[1], "image/jpeg")},
        ).json()
        second = client.post(
            "/api/v1/analyses",
            files={"file": ("b.jpg", _make_jpeg(color=(200, 100, 50))[1], "image/jpeg")},
        ).json()

        first_row = await embedding_repository.get_by_analysis_id(
            db_session, uuid.UUID(first["id"])
        )
        second_row = await embedding_repository.get_by_analysis_id(
            db_session, uuid.UUID(second["id"])
        )
        assert first_row.vector_id != second_row.vector_id


class TestUnavailableModel:
    async def test_embed_and_index_degrades_gracefully_when_model_unavailable(
        self, db_session, monkeypatch
    ):
        unavailable_model = EmbeddingModel()  # never .load()ed -> is_available False
        monkeypatch.setattr(
            embedding_service_module, "get_embedding_model", lambda: unavailable_model
        )

        image, image_bytes = _make_jpeg()
        row, latency = await embed_and_index(db_session, uuid.uuid4(), image, image_bytes)
        assert row is None
        assert latency == 0.0
