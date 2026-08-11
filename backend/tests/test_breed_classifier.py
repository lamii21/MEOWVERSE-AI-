from pathlib import Path

import pytest
from PIL import Image

from app.core.config import get_settings
from app.ml.breed_classifier import BreedClassifier


def test_is_unavailable_when_weights_missing(monkeypatch):
    monkeypatch.setenv("BREED_CLASSIFIER_WEIGHTS_PATH", "does/not/exist.pt")
    monkeypatch.setenv("BREED_CLASSIFIER_CLASS_NAMES_PATH", "does/not/exist.json")
    get_settings.cache_clear()
    try:
        classifier = BreedClassifier()
        classifier.load()
        assert classifier.is_available is False
    finally:
        get_settings.cache_clear()


def test_predict_raises_when_unavailable():
    classifier = BreedClassifier()  # never loaded
    with pytest.raises(RuntimeError):
        classifier.predict(Image.new("RGB", (64, 64)))


_settings = get_settings()
_weights_exist = (
    Path(_settings.breed_classifier_weights_path).exists()
    and Path(_settings.breed_classifier_class_names_path).exists()
)


@pytest.mark.skipif(
    not _weights_exist,
    reason="trained weights not present — run ml/training/train_breed_classifier.py first",
)
def test_predicts_a_known_breed_with_real_weights():
    import json

    classifier = BreedClassifier()
    classifier.load()
    assert classifier.is_available is True

    class_names = json.loads(Path(_settings.breed_classifier_class_names_path).read_text())
    expected_labels = {name.replace("_", " ") for name in class_names}

    image = Image.new("RGB", (300, 300), (180, 140, 100))
    prediction = classifier.predict(image)

    assert prediction.label in expected_labels
    assert 0.0 <= prediction.confidence <= 1.0
