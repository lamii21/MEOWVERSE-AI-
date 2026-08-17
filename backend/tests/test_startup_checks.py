import importlib.util

import pytest

from app.core.config import Settings
from app.core.startup_checks import StartupCheckError, run_startup_checks

_ML_DEPS_AVAILABLE = all(
    importlib.util.find_spec(mod) is not None
    for mod in ("torch", "torchvision", "cv2", "faiss", "sklearn")
)
_requires_ml_deps = pytest.mark.skipif(
    not _ML_DEPS_AVAILABLE, reason="requirements-ml.txt not installed in this environment"
)


def _settings(**overrides) -> Settings:
    return Settings(**overrides)


def test_require_ml_models_without_ml_deps_installed_fails_fast_and_names_the_gap():
    if _ML_DEPS_AVAILABLE:
        pytest.skip("this environment has the ML deps installed — see the other tests")

    with pytest.raises(StartupCheckError, match="ML dependency is not installed"):
        run_startup_checks(_settings(require_ml_models=True))


def test_default_settings_pass_without_requiring_ml_models():
    run_startup_checks(_settings())


def test_production_with_wildcard_cors_fails_fast():
    settings = _settings(environment="production", cors_origins=["*"])

    with pytest.raises(StartupCheckError, match="cors_origins"):
        run_startup_checks(settings)


def test_production_with_a_real_origin_passes():
    settings = _settings(environment="production", cors_origins=["https://meowverse.example.com"])

    run_startup_checks(settings)


@_requires_ml_deps
def test_require_ml_models_with_missing_weights_fails_fast():
    settings = _settings(
        require_ml_models=True,
        breed_classifier_weights_path="does/not/exist.pt",
    )

    with pytest.raises(StartupCheckError, match="weights are missing"):
        run_startup_checks(settings)


@_requires_ml_deps
def test_require_ml_models_with_a_tampered_checksum_fails_fast(tmp_path):
    weights = tmp_path / "breed_classifier.pt"
    weights.write_bytes(b"not the real weights")
    (tmp_path / "breed_classifier.pt.sha256").write_text("0" * 64)
    class_names = tmp_path / "class_names.json"
    class_names.write_text("[]")

    settings = _settings(
        require_ml_models=True,
        breed_classifier_weights_path=str(weights),
        breed_classifier_class_names_path=str(class_names),
    )

    with pytest.raises(StartupCheckError, match="integrity"):
        run_startup_checks(settings)
