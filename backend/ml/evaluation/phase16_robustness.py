"""Phase 16 robustness validation: non-cat images and image edge cases
run through the REAL production pipeline (`_load_and_validate_image`,
`BreedClassifier.predict`, `FurColorAnalyzer.predict`) — not a
simulation. Every prediction/confidence/error recorded here is a real
model output or a real, reproduced exception, never invented.

Usage (from backend/, with the venv active, KMP_DUPLICATE_LIB_OK=TRUE):
    python -m ml.evaluation.phase16_robustness
"""

import io
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # backend/ on sys.path

from app.ml.breed_classifier import get_breed_classifier  # noqa: E402
from app.ml.fur_color import get_fur_color_analyzer  # noqa: E402
from app.services.analysis_service import InvalidImageError, _load_and_validate_image  # noqa: E402

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parents[1]
VENV_SITE_PACKAGES = BACKEND_DIR / ".venv" / "Lib" / "site-packages"
RAW_PET_IMAGES = BACKEND_DIR / "ml" / "dataset" / "raw" / "oxford-iiit-pet" / "images"

# A real cat photo (from the held-out test split) used as the base for
# synthetic edge-case transforms (tiny/huge/grayscale/etc.) — the
# transform is synthetic, the underlying photo content is real.
BASE_CAT_PHOTO = BACKEND_DIR / "ml" / "dataset" / "processed" / "test" / "Persian" / next(
    p.name for p in (BACKEND_DIR / "ml" / "dataset" / "processed" / "test" / "Persian").iterdir()
)


def _run_case(name: str, image_bytes: bytes | None, classifier, color_analyzer) -> dict:
    result = {"case": name}
    try:
        if image_bytes is None:
            raise ValueError("no bytes provided")
        image = _load_and_validate_image(image_bytes)
        result["validation"] = "accepted"
        result["dimensions"] = f"{image.width}x{image.height}"
        result["mode"] = image.mode

        breed = classifier.predict(image)
        result["breed_prediction"] = breed.label
        result["breed_confidence"] = breed.confidence

        colors = color_analyzer.predict(image)
        result["color_prediction"] = [c.name for c in colors]
        result["status"] = "ok"
    except InvalidImageError as exc:
        result["status"] = "rejected_by_validation"
        result["error"] = str(exc)
    except Exception as exc:  # noqa: BLE001 - deliberately broad: this IS the crash probe
        result["status"] = "CRASH"
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def _jpeg_bytes(image: Image.Image) -> bytes:
    buf = io.BytesIO()
    image.convert("RGB").save(buf, format="JPEG")
    return buf.getvalue()


def main() -> None:
    import os

    os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

    classifier = get_breed_classifier()
    color_analyzer = get_fur_color_analyzer()
    if not classifier.is_available:
        raise SystemExit("Breed classifier not available — run training first.")
    if not color_analyzer.is_available:
        raise SystemExit("Fur color analyzer not available.")

    base_cat = Image.open(BASE_CAT_PHOTO).convert("RGB")

    cases: dict[str, bytes | None] = {}

    # --- Non-cat real photos ---
    person_path = (
        VENV_SITE_PACKAGES / "matplotlib" / "mpl-data" / "sample_data" / "grace_hopper.jpg"
    )
    landscape_path = VENV_SITE_PACKAGES / "sklearn" / "datasets" / "images" / "china.jpg"
    flower_path = VENV_SITE_PACKAGES / "sklearn" / "datasets" / "images" / "flower.jpg"
    dog_beagle_path = RAW_PET_IMAGES / "beagle_1.jpg"
    dog_boxer_path = RAW_PET_IMAGES / "boxer_1.jpg"
    for label, path in [
        ("non_cat_person", person_path),
        ("non_cat_landscape_building", landscape_path),
        ("non_cat_flower", flower_path),
        ("non_cat_dog_beagle", dog_beagle_path),
        ("non_cat_dog_boxer", dog_boxer_path),
    ]:
        cases[label] = path.read_bytes() if path.exists() else None

    # --- Synthetic edge cases, built from a real cat photo ---
    cases["edge_tiny_32x32"] = _jpeg_bytes(base_cat.resize((32, 32)))  # below MIN_DIMENSION_PX(64)
    cases["edge_small_80x80"] = _jpeg_bytes(base_cat.resize((80, 80)))
    cases["edge_huge_4000x4000"] = _jpeg_bytes(base_cat.resize((4000, 4000)))
    cases["edge_extremely_wide_2000x100"] = _jpeg_bytes(base_cat.resize((2000, 100)))
    cases["edge_extremely_tall_100x2000"] = _jpeg_bytes(base_cat.resize((100, 2000)))
    cases["edge_grayscale"] = _jpeg_bytes(base_cat.convert("L").convert("RGB"))

    rgba_buf = io.BytesIO()
    base_cat.convert("RGBA").save(rgba_buf, format="PNG")
    cases["edge_rgba_png"] = rgba_buf.getvalue()

    cases["edge_corrupted_truncated"] = _jpeg_bytes(base_cat)[:200]  # truncated mid-file
    cases["edge_corrupted_garbage"] = b"this is not an image at all, just bytes"
    cases["edge_empty_bytes"] = b""

    # low-light / backlit: real brightness manipulation of a real photo
    from PIL import ImageEnhance

    cases["edge_low_light"] = _jpeg_bytes(ImageEnhance.Brightness(base_cat).enhance(0.15))
    cases["edge_backlit_overexposed"] = _jpeg_bytes(ImageEnhance.Brightness(base_cat).enhance(3.5))

    # partially visible: crop to a corner (top-left quarter)
    w, h = base_cat.size
    cases["edge_partially_visible_crop"] = _jpeg_bytes(base_cat.crop((0, 0, w // 2, h // 2)))

    results = [_run_case(name, data, classifier, color_analyzer) for name, data in cases.items()]

    # --- Cases honestly not tested (no real image available) ---
    not_tested = [
        {
            "case": "multiple_cats_in_frame",
            "status": "NOT VERIFIED",
            "reason": "No real multi-cat photo available in this environment's image "
            "sources (held-out test set is single-cat-per-image by dataset "
            "construction; no second real multi-cat image source was available "
            "to fetch). Not simulated.",
        },
        {
            "case": "cat_far_away_or_close_up",
            "status": "NOT VERIFIED",
            "reason": "No real photo with these specific framing characteristics was "
            "available in this environment beyond the standard dataset crops "
            "already covered by the held-out evaluation set.",
        },
    ]

    summary = {
        "evaluation_date": datetime.now(UTC).isoformat(),
        "model_version": classifier.version,
        "cases": results,
        "not_tested": not_tested,
        "crash_count": sum(1 for r in results if r["status"] == "CRASH"),
        "rejected_by_validation_count": sum(
            1 for r in results if r["status"] == "rejected_by_validation"
        ),
        "ok_count": sum(1 for r in results if r["status"] == "ok"),
    }

    out_path = SCRIPT_DIR / "robustness_results.json"
    out_path.write_text(json.dumps(summary, indent=2))

    print(json.dumps(summary, indent=2))
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
