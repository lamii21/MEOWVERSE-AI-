import pytest
from PIL import Image

from app.ml.fur_color import FurColorAnalyzer, _nearest_color_name


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
