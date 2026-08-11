import io
import uuid
from unittest.mock import patch

import pytest
from PIL import Image

from app.schemas.analysis import BreedPrediction, ColorSwatch
from app.services.analysis_service import analyze_image


def _make_jpeg_bytes(size=(128, 128), color=(200, 150, 100)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="JPEG")
    return buf.getvalue()


class _FakeUnavailableModel:
    is_available = False


class _FakeTrainedClassifier:
    is_available = True

    def predict(self, image):
        return BreedPrediction(label="Bengal", confidence=0.97)


class _FakeTrainedColorAnalyzer:
    is_available = True

    def predict(self, image):
        return [ColorSwatch(name="cobalt", hex="#123456", percentage=100.0)]


@pytest.mark.asyncio
@patch("app.services.profile_service.get_llm_provider")
@patch("app.services.analysis_service.get_fur_color_analyzer")
@patch("app.services.analysis_service.get_breed_classifier")
async def test_both_fall_back_to_demo_when_unavailable(
    mock_get_classifier, mock_get_colors, mock_get_llm, db_session
):
    mock_get_classifier.return_value = _FakeUnavailableModel()
    mock_get_colors.return_value = _FakeUnavailableModel()
    mock_get_llm.return_value = _FakeUnavailableModel()

    result = await analyze_image(_make_jpeg_bytes(), "image/jpeg", db_session)

    assert result.breed_mode == "demo"
    assert result.colors_mode == "demo"
    assert result.profile_mode == "demo"
    assert result.breed.label
    assert len(result.colors) > 0
    assert result.profile.name


@pytest.mark.asyncio
@patch("app.services.profile_service.get_llm_provider")
@patch("app.services.analysis_service.get_fur_color_analyzer")
@patch("app.services.analysis_service.get_breed_classifier")
async def test_breed_real_colors_demo_are_independent(
    mock_get_classifier, mock_get_colors, mock_get_llm, db_session
):
    """The two CV signals must vary independently — real breed doesn't
    imply real colors, and vice versa (this is the whole point of
    splitting mode per-signal instead of one result-wide flag)."""
    mock_get_classifier.return_value = _FakeTrainedClassifier()
    mock_get_colors.return_value = _FakeUnavailableModel()
    mock_get_llm.return_value = _FakeUnavailableModel()

    result = await analyze_image(_make_jpeg_bytes(), "image/jpeg", db_session)

    assert result.breed_mode == "trained"
    assert result.breed == BreedPrediction(label="Bengal", confidence=0.97)
    assert result.colors_mode == "demo"
    assert len(result.colors) > 0


@pytest.mark.asyncio
@patch("app.services.profile_service.get_llm_provider")
@patch("app.services.analysis_service.get_fur_color_analyzer")
@patch("app.services.analysis_service.get_breed_classifier")
async def test_colors_real_breed_demo_are_independent(
    mock_get_classifier, mock_get_colors, mock_get_llm, db_session
):
    mock_get_classifier.return_value = _FakeUnavailableModel()
    mock_get_colors.return_value = _FakeTrainedColorAnalyzer()
    mock_get_llm.return_value = _FakeUnavailableModel()

    result = await analyze_image(_make_jpeg_bytes(), "image/jpeg", db_session)

    assert result.breed_mode == "demo"
    assert result.breed.label
    assert result.colors_mode == "trained"
    assert result.colors == [ColorSwatch(name="cobalt", hex="#123456", percentage=100.0)]


@pytest.mark.asyncio
@patch("app.services.profile_service.get_llm_provider")
@patch("app.services.analysis_service.get_fur_color_analyzer")
@patch("app.services.analysis_service.get_breed_classifier")
async def test_both_cv_signals_real_when_both_available(
    mock_get_classifier, mock_get_colors, mock_get_llm, db_session
):
    mock_get_classifier.return_value = _FakeTrainedClassifier()
    mock_get_colors.return_value = _FakeTrainedColorAnalyzer()
    mock_get_llm.return_value = _FakeUnavailableModel()

    result = await analyze_image(_make_jpeg_bytes(), "image/jpeg", db_session)

    assert result.breed_mode == "trained"
    assert result.colors_mode == "trained"


@pytest.mark.asyncio
@patch("app.services.profile_service.get_llm_provider")
@patch("app.services.analysis_service.get_fur_color_analyzer")
@patch("app.services.analysis_service.get_breed_classifier")
async def test_profile_never_overwrites_real_cv_signals(
    mock_get_classifier, mock_get_colors, mock_get_llm, db_session
):
    """Requirement: the LLM must not be able to alter breed/colors —
    verified structurally (CatProfile has no such fields) and here
    behaviorally: real CV output survives unchanged regardless of the
    (demo) profile generated alongside it."""
    mock_get_classifier.return_value = _FakeTrainedClassifier()
    mock_get_colors.return_value = _FakeTrainedColorAnalyzer()
    mock_get_llm.return_value = _FakeUnavailableModel()

    result = await analyze_image(_make_jpeg_bytes(), "image/jpeg", db_session)

    assert result.breed == BreedPrediction(label="Bengal", confidence=0.97)
    assert result.colors == [ColorSwatch(name="cobalt", hex="#123456", percentage=100.0)]
    assert not hasattr(result.profile, "breed")
    assert not hasattr(result.profile, "colors")


@pytest.mark.asyncio
@patch("app.services.profile_service.get_llm_provider")
@patch("app.services.analysis_service.get_fur_color_analyzer")
@patch("app.services.analysis_service.get_breed_classifier")
async def test_result_is_persisted_and_gets_a_real_id(
    mock_get_classifier, mock_get_colors, mock_get_llm, db_session
):
    """Phase 7: analyze_image must persist the result and return a real,
    retrievable id — the story endpoint depends on this."""
    mock_get_classifier.return_value = _FakeTrainedClassifier()
    mock_get_colors.return_value = _FakeTrainedColorAnalyzer()
    mock_get_llm.return_value = _FakeUnavailableModel()

    result = await analyze_image(_make_jpeg_bytes(), "image/jpeg", db_session)

    assert result.id is not None
    assert isinstance(result.id, uuid.UUID)

    from app.repositories.analysis_repository import get_analysis

    row = await get_analysis(db_session, result.id)
    assert row is not None
    assert row.breed_label == "Bengal"
    assert row.profile["name"]


@pytest.mark.asyncio
@patch("app.services.profile_service.get_llm_provider")
@patch("app.services.analysis_service.get_fur_color_analyzer")
@patch("app.services.analysis_service.get_breed_classifier")
async def test_analysis_still_succeeds_when_db_is_unavailable(
    mock_get_classifier, mock_get_colors, mock_get_llm
):
    """Persistence is best-effort — analyze_image must not raise even
    if the database is completely unusable (here: passing None instead
    of a session, which fails inside save_analysis with an
    AttributeError, caught by the deliberately broad except)."""
    mock_get_classifier.return_value = _FakeTrainedClassifier()
    mock_get_colors.return_value = _FakeTrainedColorAnalyzer()
    mock_get_llm.return_value = _FakeUnavailableModel()

    result = await analyze_image(_make_jpeg_bytes(), "image/jpeg", None)

    assert result.id is None
    assert result.breed == BreedPrediction(label="Bengal", confidence=0.97)
