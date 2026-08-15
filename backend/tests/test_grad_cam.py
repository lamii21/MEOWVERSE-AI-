"""Tests the actual Grad-CAM mathematics (Phase 12 spec §22-24), not
just that an HTTP endpoint returns 200. Uses the real trained breed
classifier and real photos from the Oxford-IIIT Pet dataset already
present in this repo (same dataset the model was trained on) — skips
if the trained weights genuinely aren't available in this environment,
never fakes a result.
"""

import math
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from app.ml.breed_classifier import GRAD_CAM_TARGET_LAYER, get_breed_classifier
from app.ml.heatmap_visualization import render_heatmap_and_overlay

DATASET_DIR = Path(__file__).parent.parent / "ml" / "dataset" / "processed" / "test"


@pytest.fixture(scope="module")
def classifier():
    model = get_breed_classifier()
    if not model.is_available:
        pytest.skip("Trained breed classifier unavailable in this environment.")
    return model


@pytest.fixture(scope="module")
def real_cat_photo():
    candidates = sorted((DATASET_DIR / "British Shorthair").glob("*.jpg"))
    if not candidates:
        pytest.skip("Oxford-IIIT Pet dataset not present in this environment.")
    return Image.open(candidates[0]).convert("RGB")


class TestGradCamMathematics:
    def test_target_layer_constant_matches_the_documented_layer(self):
        assert GRAD_CAM_TARGET_LAYER == "features.12"

    def test_produces_a_heatmap_matching_the_original_image_dimensions(
        self, classifier, real_cat_photo
    ):
        result = classifier.explain(real_cat_photo)
        assert result.heatmap.shape == (result.image_height, result.image_width)
        assert (result.image_width, result.image_height) == real_cat_photo.size

    def test_heatmap_values_are_finite_and_normalized_to_unit_range(
        self, classifier, real_cat_photo
    ):
        result = classifier.explain(real_cat_photo)
        assert np.isfinite(result.heatmap).all()
        assert result.heatmap.min() >= 0.0
        assert result.heatmap.max() <= 1.0 + 1e-6
        # A real photo produces a genuinely discriminative activation —
        # not a degenerate all-zero map.
        assert result.heatmap.max() > 0.0

    def test_relu_is_applied_no_negative_activation_survives(self, classifier, real_cat_photo):
        result = classifier.explain(real_cat_photo)
        assert (result.heatmap >= 0.0).all()

    def test_target_class_defaults_to_the_models_own_top_prediction(
        self, classifier, real_cat_photo
    ):
        prediction = classifier.predict(real_cat_photo)
        explanation = classifier.explain(real_cat_photo)
        assert explanation.target_class_label == prediction.label
        assert explanation.confidence == pytest.approx(prediction.confidence, abs=1e-5)

    def test_explicit_target_class_is_honored_and_not_silently_overridden(
        self, classifier, real_cat_photo
    ):
        # Pick a class that is NOT the model's own top prediction, to
        # prove the explanation actually targets what was asked for.
        prediction = classifier.predict(real_cat_photo)
        other_class = next(c for c in classifier.class_names if c != prediction.label)

        result = classifier.explain(real_cat_photo, target_class_label=other_class)
        assert result.target_class_label == other_class
        assert result.target_class_index == classifier.class_names.index(other_class)

    def test_unknown_target_class_raises(self, classifier, real_cat_photo):
        with pytest.raises(ValueError):
            classifier.explain(real_cat_photo, target_class_label="Not A Real Breed")

    def test_raises_when_model_unavailable(self):
        from app.ml.breed_classifier import BreedClassifier

        fresh = BreedClassifier()  # never .load()ed
        with pytest.raises(RuntimeError):
            fresh.explain(Image.new("RGB", (64, 64), (0, 0, 0)))

    def test_confidence_is_a_real_probability_not_grad_cam_intensity(
        self, classifier, real_cat_photo
    ):
        result = classifier.explain(real_cat_photo)
        # Classification confidence (softmax probability) is a single
        # scalar in [0, 1] — categorically different from the heatmap,
        # which is a full 2D array. Assert they are not conflated.
        assert isinstance(result.confidence, float)
        assert 0.0 <= result.confidence <= 1.0
        assert result.heatmap.ndim == 2


class TestGradCamGenuinelyDependsOnGradients:
    """Phase 12 spec §23: a controlled test proving the heatmap actually
    comes from backpropagated gradients, not some gradient-independent
    image-processing trick wearing a Grad-CAM costume."""

    def test_different_target_classes_produce_different_heatmaps(self, classifier, real_cat_photo):
        # If Grad-CAM genuinely backpropagates a *specific* class
        # logit, explaining two different classes on the same image
        # must generally produce different channel-importance weights
        # (different gradients) and therefore a different heatmap. A
        # fake/gradient-independent "heatmap" (e.g. plain saliency from
        # pixel intensity, or a decorative fixed pattern) would produce
        # the *same* map regardless of which class was requested.
        class_a, class_b = classifier.class_names[0], classifier.class_names[1]
        heatmap_a = classifier.explain(real_cat_photo, target_class_label=class_a).heatmap
        heatmap_b = classifier.explain(real_cat_photo, target_class_label=class_b).heatmap
        assert not np.allclose(heatmap_a, heatmap_b, atol=1e-4)

    def test_heatmap_is_deterministic_for_the_same_class_and_image(
        self, classifier, real_cat_photo
    ):
        prediction = classifier.predict(real_cat_photo)
        first = classifier.explain(real_cat_photo, target_class_label=prediction.label).heatmap
        second = classifier.explain(real_cat_photo, target_class_label=prediction.label).heatmap
        np.testing.assert_allclose(first, second, atol=1e-5)


class TestHeatmapVisualization:
    def test_heatmap_and_overlay_are_valid_images_matching_source_dimensions(
        self, classifier, real_cat_photo
    ):
        result = classifier.explain(real_cat_photo)
        heatmap_image, overlay_image = render_heatmap_and_overlay(real_cat_photo, result.heatmap)

        assert heatmap_image.size == real_cat_photo.size
        assert overlay_image.size == real_cat_photo.size
        assert heatmap_image.mode == "RGB"
        assert overlay_image.mode == "RGB"

        heatmap_array = np.array(heatmap_image)
        overlay_array = np.array(overlay_image)
        assert np.isfinite(heatmap_array).all()
        assert np.isfinite(overlay_array).all()
        assert heatmap_array.min() >= 0 and heatmap_array.max() <= 255
        assert overlay_array.min() >= 0 and overlay_array.max() <= 255

    def test_overlay_alpha_is_capped_original_image_remains_recognizable(self):
        # Fully "hot" (all-1.0) heatmap over a solid-color image: even
        # at maximum importance everywhere, the overlay must still be a
        # blend, not a pure heatmap copy — proves the alpha cap works.
        original = Image.new("RGB", (32, 32), (100, 150, 200))
        heatmap = np.ones((32, 32), dtype=np.float32)
        _, overlay_image = render_heatmap_and_overlay(original, heatmap, max_overlay_alpha=0.6)
        overlay_array = np.array(overlay_image).astype(np.float32)
        original_array = np.array(original).astype(np.float32)
        # At most 60% blended toward the heatmap color — some of the
        # original pixel value must still be present.
        contribution_from_original = np.abs(overlay_array - original_array).mean()
        assert contribution_from_original < np.abs(255 - original_array).mean()

    def test_zero_heatmap_overlay_equals_the_original_image(self):
        original = Image.new("RGB", (16, 16), (30, 60, 90))
        heatmap = np.zeros((16, 16), dtype=np.float32)
        _, overlay_image = render_heatmap_and_overlay(original, heatmap)
        np.testing.assert_array_equal(np.array(overlay_image), np.array(original.convert("RGB")))


class TestRealImageQualitativeBehavior:
    """Phase 12 spec §25-26: real photos, several breeds, not
    cherry-picked. Records observed behavior — does NOT assert a
    "correct" heatmap location, since there is no ground truth for
    that; only asserts the pipeline runs cleanly and produces sane,
    finite output for every breed folder actually present."""

    @pytest.mark.parametrize(
        "breed_folder",
        ["British Shorthair", "Siamese", "Persian", "Bengal", "Sphynx"],
    )
    def test_runs_cleanly_on_real_photos_of_each_breed(self, classifier, breed_folder):
        folder = DATASET_DIR / breed_folder
        photos = sorted(folder.glob("*.jpg"))[:2]
        if not photos:
            pytest.skip(f"No {breed_folder} photos available in this environment.")

        for photo_path in photos:
            image = Image.open(photo_path).convert("RGB")
            prediction = classifier.predict(image)
            result = classifier.explain(image, target_class_label=prediction.label)

            assert np.isfinite(result.heatmap).all()
            assert 0.0 <= result.confidence <= 1.0
            assert result.heatmap.shape == (image.height, image.width)
            # Record (not assert) whether the model's own prediction
            # matched the ground-truth folder — a real, honest signal
            # about this specific photo, not a claim about heatmap
            # quality (which has no automated ground truth at all).
            correct_prediction = prediction.label == breed_folder
            print(
                f"\n[qualitative] {breed_folder}/{photo_path.name}: "
                f"predicted={prediction.label} ({prediction.confidence:.2f}), "
                f"correct_breed_prediction={correct_prediction}, "
                f"heatmap_peak={float(result.heatmap.max()):.3f}, "
                f"heatmap_mean={float(result.heatmap.mean()):.3f}"
            )

    def test_faithfulness_masking_the_top_region_generally_drops_confidence(
        self, classifier
    ):
        """Phase 12 spec §27 (optional faithfulness check, implemented
        since the pipeline made it practical): masks the top 15% of
        each photo's heatmap (replaced with the image's own mean
        color) and re-runs the classifier for the *same* original
        target class. If the heatmap genuinely reflects what the model
        relies on, removing that region should generally reduce
        confidence in that class — a real, if approximate, sanity
        check. This is NOT proof of causality (a masked region also
        changes lighting/context/composition, and CNNs are not
        strictly compositional) — only the aggregate trend across
        several real photos is asserted, specifically to avoid
        over-claiming from any one image; individual results are
        printed for the honest qualitative record (PROJECT_STATUS.md),
        including the one photo that did NOT show a meaningful drop.
        """
        folder = DATASET_DIR / "British Shorthair"
        photos = sorted(folder.glob("*.jpg"))[:5]
        if len(photos) < 3:
            pytest.skip("Not enough real photos available for a faithfulness sample.")

        drops = []
        for photo_path in photos:
            image = Image.open(photo_path).convert("RGB")
            prediction = classifier.predict(image)
            original = classifier.explain(image, target_class_label=prediction.label)

            threshold = np.percentile(original.heatmap, 85)
            mask = original.heatmap >= threshold
            masked_array = np.array(image).copy()
            mean_color = masked_array.reshape(-1, 3).mean(axis=0).astype(np.uint8)
            masked_array[mask] = mean_color
            masked_image = Image.fromarray(masked_array)

            masked_result = classifier.explain(masked_image, target_class_label=prediction.label)
            drop = prediction.confidence - masked_result.confidence
            drops.append(drop)
            print(
                f"\n[faithfulness] {photo_path.name}: "
                f"original={prediction.confidence:.3f} "
                f"masked={masked_result.confidence:.3f} "
                f"drop={drop:+.3f} "
                f"masked_fraction={mask.sum() / mask.size:.2%}"
            )

        mean_drop = float(np.mean(drops))
        print(f"\n[faithfulness] mean confidence drop across {len(drops)} photos: {mean_drop:+.3f}")
        # A real, honest, non-arbitrary bar: on average, masking the
        # region Grad-CAM called "most important" should reduce
        # confidence by *some* meaningful amount — not asserting every
        # individual photo behaves this way (one didn't, in this
        # project's own real run — see PROJECT_STATUS.md).
        assert mean_drop > 0.05

    def test_heatmap_peak_location_is_reported_not_asserted(self, classifier, real_cat_photo):
        # Where the hottest pixel lands is genuinely informative for
        # the qualitative report (PROJECT_STATUS.md) but is NOT a
        # pass/fail correctness criterion — Grad-CAM has no ground
        # truth for "the model should look here." This test only
        # confirms the peak coordinates are well-formed real numbers.
        result = classifier.explain(real_cat_photo)
        peak_y, peak_x = np.unravel_index(np.argmax(result.heatmap), result.heatmap.shape)
        assert 0 <= peak_x < result.image_width
        assert 0 <= peak_y < result.image_height
        assert not math.isnan(float(result.heatmap[peak_y, peak_x]))
