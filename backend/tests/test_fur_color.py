from pathlib import Path

import pytest
from PIL import Image

from app.ml.fur_color import FurColorAnalyzer, _nearest_color_name

_REAL_TEST_IMAGE_DIR = (
    Path(__file__).resolve().parents[1] / "ml" / "dataset" / "processed" / "test" / "Bengal"
)


def test_is_available_after_load():
    analyzer = FurColorAnalyzer()
    assert analyzer.is_available is False
    analyzer.load()
    assert analyzer.is_available is True


def test_predict_raises_when_unavailable():
    analyzer = FurColorAnalyzer()  # never loaded
    with pytest.raises(RuntimeError):
        analyzer.predict(Image.new("RGB", (64, 64)))


def test_predict_returns_three_swatches_summing_near_100():
    analyzer = FurColorAnalyzer()
    analyzer.load()

    image = Image.new("RGB", (200, 200), (30, 60, 200))
    swatches = analyzer.predict(image)

    assert len(swatches) == 3
    total_pct = sum(s.percentage for s in swatches)
    assert 99.0 <= total_pct <= 101.0
    for s in swatches:
        assert s.hex.startswith("#") and len(s.hex) == 7
        assert 0.0 <= s.percentage <= 100.0


def test_predict_on_solid_color_image_dominant_swatch_matches_hue():
    analyzer = FurColorAnalyzer()
    analyzer.load()

    # A near-black solid image — GrabCut may or may not carve a
    # foreground on a flat image, but either way the dominant cluster
    # should still land near black, not some unrelated hue.
    image = Image.new("RGB", (200, 200), (20, 20, 20))
    swatches = analyzer.predict(image)

    dominant = max(swatches, key=lambda s: s.percentage)
    r = int(dominant.hex[1:3], 16)
    g = int(dominant.hex[3:5], 16)
    b = int(dominant.hex[5:7], 16)
    assert r < 100 and g < 100 and b < 100


def test_nearest_color_name_matches_expected_hues():
    assert _nearest_color_name((250, 250, 248)) == "white"
    assert _nearest_color_name((20, 18, 16)) == "black"
    assert _nearest_color_name((210, 118, 48)) in {"orange", "ginger"}


@pytest.mark.skipif(
    not _REAL_TEST_IMAGE_DIR.exists(), reason="ml/dataset/processed not present in this environment"
)
def test_predict_is_deterministic_on_a_real_photo_across_repeated_calls():
    """Phase 16 regression test for a real, discovered bug: cv2.grabCut
    draws from OpenCV's own global RNG on every call, which
    `KMeans(random_state=42)` has no influence over — confirmed by
    direct measurement to produce a genuinely different foreground mask
    (and therefore different color swatches) across repeated calls on
    byte-identical input, on a *real* textured photo (a flat solid-color
    test image doesn't reliably exercise this, since GrabCut's GMM has
    much less to disagree about on a uniform image). Fixed by
    `cv2.setRNGSeed(42)` immediately before the `grabCut` call — this
    test would have caught the bug before the fix."""
    analyzer = FurColorAnalyzer()
    analyzer.load()

    image_path = next(_REAL_TEST_IMAGE_DIR.iterdir())
    image = Image.open(image_path).convert("RGB")

    results = [analyzer.predict(image) for _ in range(5)]
    assert all(r == results[0] for r in results)
