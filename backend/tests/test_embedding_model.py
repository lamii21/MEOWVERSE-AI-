import io

import numpy as np
import pytest
from PIL import Image

from app.ml.embedding_model import EMBEDDING_DIM, get_embedding_model


def _make_image(size=(128, 128), color=(200, 150, 100)) -> Image.Image:
    return Image.new("RGB", size, color)


def _make_jpeg_bytes(size=(128, 128), color=(200, 150, 100)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture(scope="module")
def model():
    m = get_embedding_model()
    if not m.is_available:
        pytest.skip("Embedding model unavailable in this environment (no torch/torchvision).")
    return m


class TestEmbeddingModel:
    def test_output_has_the_documented_dimension(self, model):
        vector = model.predict(_make_image())
        assert vector.shape == (EMBEDDING_DIM,)

    def test_output_is_l2_normalized(self, model):
        vector = model.predict(_make_image())
        norm = np.linalg.norm(vector)
        assert norm == pytest.approx(1.0, abs=1e-4)

    def test_output_dtype_is_float32(self, model):
        vector = model.predict(_make_image())
        assert vector.dtype == np.float32

    def test_same_image_produces_the_same_embedding(self, model):
        image_bytes = _make_jpeg_bytes(color=(50, 60, 70))
        first = model.predict(Image.open(io.BytesIO(image_bytes)))
        second = model.predict(Image.open(io.BytesIO(image_bytes)))
        np.testing.assert_allclose(first, second, atol=1e-6)

    def test_different_images_produce_different_embeddings(self, model):
        a = model.predict(_make_image(color=(255, 0, 0)))
        b = model.predict(_make_image(color=(0, 0, 255)))
        assert not np.allclose(a, b, atol=1e-3)

    def test_predict_raises_when_called_while_unavailable(self):
        from app.ml.embedding_model import EmbeddingModel

        fresh = EmbeddingModel()  # never .load()ed
        with pytest.raises(RuntimeError):
            fresh.predict(_make_image())
