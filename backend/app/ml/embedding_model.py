import logging

import numpy as np
from PIL import Image

from app.ml.base_model import BaseModel

logger = logging.getLogger(__name__)

# Identical preprocessing constants to app/ml/breed_classifier.py, on
# purpose — same deterministic pipeline (resize shorter-edge-implied
# 224*1.14≈255, center-crop 224, RGB, ImageNet mean/std normalization)
# so both models see the image the same way, and so this file's
# preprocessing behavior is easy to audit against a document that
# already exists in this codebase.
IMAGE_SIZE = 224
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]

# The dimensionality of MobileNetV3-Small's globally-pooled feature
# vector (the input to its classification head, i.e. what we take
# *instead of* running the classification head) — a fixed architectural
# fact of this model, not a config knob. Verified empirically before
# writing this module (see PROJECT_STATUS.md / ARCHITECTURE.md §19).
EMBEDDING_DIM = 576

# Bumped only if the model architecture or weights identity changes in
# a way that makes old vectors mathematically incompatible with new
# ones (Phase 11 spec §34-35) — never for unrelated code changes.
EMBEDDING_MODEL_NAME = "mobilenet_v3_small_imagenet"
EMBEDDING_VERSION = "v1"


class EmbeddingModel(BaseModel):
    """Produces a fixed-dimensional, L2-normalized visual embedding for
    a cat photo — deliberately NOT the breed classifier
    (`app/ml/breed_classifier.py`), and not fine-tuned on this
    project's cat-breed data at all.

    Uses `torchvision.models.mobilenet_v3_small` with its stock
    ImageNet-pretrained weights (`MobileNet_V3_Small_Weights.IMAGENET1K_V1`)
    — a real, general-purpose, pretrained computer-vision backbone,
    reused here purely as a feature extractor: `predict()` runs the
    image through `features` + `avgpool` and stops *before* the
    1000-way ImageNet classification head, returning the 576-dim
    pooled feature vector instead. This is the standard, well-established
    way to get a "visual similarity" embedding from an image classifier
    without training anything new (Phase 11 spec §2: "do not train a
    new model from scratch unless there is a demonstrated need").

    Chosen over the project's *own* fine-tuned breed classifier
    specifically because a breed-fine-tuned backbone's features are
    pulled toward separating the 12 trained breed classes — exactly the
    "similarity from breed labels" shortcut Phase 11 explicitly
    forbids (spec §3). A generic ImageNet backbone's features encode
    broader visual structure (shape, texture, pose, coloring pattern)
    that isn't collapsed toward breed-discriminative dimensions.

    Same honest-fallback contract as every other model in this
    codebase: if torch/torchvision aren't installed, or the pretrained
    weights can't be loaded (no local cache and no network), this
    reports `is_available = False` — the pipeline then skips embedding
    generation entirely for that analysis (`embedding_available: False`
    in the API response) rather than inventing a random or
    demo-mode vector. See ARCHITECTURE.md §19 for why a *fake*
    embedding would be worse than no embedding at all: FAISS distances
    over random vectors are meaningless, and nothing about the response
    shape would tell a caller that.
    """

    name = EMBEDDING_MODEL_NAME
    version = EMBEDDING_VERSION
    dimension = EMBEDDING_DIM

    def __init__(self) -> None:
        self._model = None
        self._transform = None
        self._device = None

    def load(self) -> None:
        try:
            import torch
            from torchvision import transforms
            from torchvision.models import MobileNet_V3_Small_Weights, mobilenet_v3_small
        except ImportError:
            logger.warning(
                "torch/torchvision not installed — visual similarity running unavailable."
            )
            return

        try:
            model = mobilenet_v3_small(weights=MobileNet_V3_Small_Weights.IMAGENET1K_V1)
        except Exception:
            # Broad on purpose: covers "no local torch hub cache and no
            # network," corrupt cache files, and any other download/load
            # failure — none of them should crash the app, all of them
            # mean "similarity is unavailable," never "fabricate a vector."
            logger.warning(
                "Failed to load ImageNet-pretrained MobileNetV3-Small weights — "
                "visual similarity unavailable.",
                exc_info=True,
            )
            return

        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model.to(self._device).eval()
        self._model = model

        self._transform = transforms.Compose(
            [
                transforms.Resize(int(IMAGE_SIZE * 1.14)),
                transforms.CenterCrop(IMAGE_SIZE),
                transforms.ToTensor(),
                transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
            ]
        )
        logger.info("Loaded visual similarity embedding model on %s", self._device)

    @property
    def is_available(self) -> bool:
        return self._model is not None

    def predict(self, image: Image.Image) -> np.ndarray:
        """Returns a `(576,)` float32, L2-normalized embedding — L2
        normalization happens here, once, at the source, so every
        consumer (the vector index, the dedup/reuse logic, any future
        caller) can assume unit-length vectors and use a plain inner
        product as cosine similarity without re-deriving that."""
        if not self.is_available:
            raise RuntimeError("EmbeddingModel.predict called while is_available=False")

        import torch

        tensor = self._transform(image.convert("RGB")).unsqueeze(0).to(self._device)
        with torch.no_grad():
            features = self._model.features(tensor)
            pooled = self._model.avgpool(features)
            vector = torch.flatten(pooled, 1)[0]

        array = vector.cpu().numpy().astype(np.float32)
        norm = np.linalg.norm(array)
        if norm > 0:
            array = array / norm
        return array


_embedding_model: EmbeddingModel | None = None


def get_embedding_model() -> EmbeddingModel:
    """Process-wide singleton, loaded lazily on first use — same
    pattern as `get_breed_classifier()`. Loading is slow (importing
    torch itself, not the weights, is the expensive part — the
    pretrained weights are typically already cached locally by
    torchvision), so this must only ever happen once per process."""
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = EmbeddingModel()
        _embedding_model.load()
    return _embedding_model
