import hashlib
import logging
from pathlib import Path

from app.core.config import Settings

logger = logging.getLogger(__name__)


class StartupCheckError(RuntimeError):
    """A REQUIRED production dependency is missing or invalid — startup
    must not continue (Phase 17 §7: "do not make startup silently
    succeed while core AI functionality is broken")."""


def _verify_weights_checksum(weights_path: Path) -> None:
    checksum_path = weights_path.with_name(weights_path.name + ".sha256")
    if not checksum_path.exists():
        logger.warning(
            "No checksum file at %s — skipping model artifact integrity verification.",
            checksum_path,
        )
        return

    expected = checksum_path.read_text().strip()
    digest = hashlib.sha256()
    with weights_path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    actual = digest.hexdigest()

    if actual != expected:
        raise StartupCheckError(
            f"Breed classifier weights at {weights_path} failed integrity "
            f"verification (expected sha256 {expected}, got {actual}) — refusing "
            "to start with a possibly corrupted or unexpected model artifact."
        )


def run_startup_checks(settings: Settings) -> None:
    """Runs once at process startup (see app/main.py's lifespan).

    Two independent things are checked here, both REQUIRED-vs-OPTIONAL
    distinctions the phase spec asks to make explicit:

    1. CORS: a production environment must never resolve to a wildcard
       origin (spec §15) — checked unconditionally, regardless of
       `require_ml_models`, since it's a real security property, not an
       ML concern.
    2. AI/ML dependencies: OPTIONAL by default (missing weights/deps
       degrade to demo mode, exactly as every prior phase documented
       and tested) — becomes REQUIRED, and startup fails fast and
       loudly instead of silently degrading, only when a deployment has
       explicitly opted in via `require_ml_models=True`.

    The Anthropic/OpenAI providers are deliberately never checked here:
    they are, and remain, OPTIONAL in every environment — the product
    has always been designed to run fully functionally on their
    Null-provider fallback (see ARCHITECTURE.md §5/§29), never a
    "required" dependency the way the CV pipeline can be told to be.
    """
    if settings.environment == "production" and "*" in settings.cors_origins:
        raise StartupCheckError(
            "cors_origins contains '*' in a production environment — set "
            "CORS_ORIGINS to the actual frontend origin(s) instead."
        )

    if not settings.require_ml_models:
        logger.info(
            "require_ml_models=False — breed/color/embedding/similarity/Grad-CAM "
            "are OPTIONAL in this environment; a missing weight file or ML "
            "dependency degrades to demo mode rather than failing startup."
        )
        return

    logger.info("require_ml_models=True — verifying REQUIRED AI/ML dependencies...")

    try:
        import cv2  # noqa: F401
        import faiss  # noqa: F401
        import sklearn  # noqa: F401
        import torch  # noqa: F401
        import torchvision  # noqa: F401
    except ImportError as exc:
        raise StartupCheckError(
            "require_ml_models=True but a required ML dependency is not "
            f"installed ({exc}). Build the backend image with requirements-ml.txt "
            "installed, or set REQUIRE_ML_MODELS=false to run in demo mode."
        ) from exc

    weights_path = Path(settings.breed_classifier_weights_path)
    class_names_path = Path(settings.breed_classifier_class_names_path)

    if not weights_path.exists():
        raise StartupCheckError(
            f"require_ml_models=True but breed classifier weights are missing "
            f"at {weights_path}. See README.md for how production obtains the "
            "model artifact."
        )
    if not class_names_path.exists():
        raise StartupCheckError(
            f"require_ml_models=True but {class_names_path} is missing."
        )

    _verify_weights_checksum(weights_path)

    logger.info(
        "REQUIRED AI/ML dependencies verified: torch/torchvision/opencv/faiss/"
        "scikit-learn importable, breed classifier weights present"
        + (
            " and checksum-verified."
            if weights_path.with_name(weights_path.name + ".sha256").exists()
            else " (no checksum file to verify against)."
        )
    )
