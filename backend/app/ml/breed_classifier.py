import json
import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

from app.core.config import get_settings
from app.ml.base_model import BaseModel
from app.schemas.analysis import BreedPrediction

logger = logging.getLogger(__name__)

IMAGE_SIZE = 224
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]

# The Grad-CAM target layer (Phase 12) — verified empirically, not
# assumed: `model.features` is a 13-block Sequential
# (`model.features[0]` .. `model.features[12]`); a forward pass of a
# 224x224 input through the whole `features` Sequential produces a
# (576, 7, 7) tensor — the last point in the network that still has
# *spatial* dimensions before `avgpool` collapses them to (576, 1, 1)
# and the classifier head flattens further to 12 class logits. That
# makes `features[-1]` (== `features[12]`, a `Conv2dNormActivation`
# block) the correct, and only correct, Grad-CAM target for this
# architecture — the classifier head has no spatial structure left to
# explain, and any earlier block would explain lower-level, less
# class-discriminative features. String form kept here (not a live
# layer reference) purely for storage/display in `CatExplanationModel`.
GRAD_CAM_TARGET_LAYER = "features.12"


@dataclass
class GradCamResult:
    """Output of `BreedClassifier.explain()` — real Grad-CAM (Selvaraju
    et al., 2017), computed for one specific target class against this
    exact model's real weights. Nothing here is fabricated: `heatmap`
    comes directly from gradients actually backpropagated through the
    model, `confidence` is the model's own softmax output for
    `target_class_index`, never a guess.
    """

    target_class_index: int
    target_class_label: str
    confidence: float
    """Classification confidence for `target_class_label` — a
    genuinely different concept from Grad-CAM intensity (heatmap
    values). Never conflate the two; see ARCHITECTURE.md §23."""
    heatmap: np.ndarray
    """`(image_height, image_width)`, float32, values in `[0, 1]`,
    already resized to the *original* image's pixel dimensions (not
    the model's 224x224 input size)."""
    image_width: int
    image_height: int


class BreedClassifier(BaseModel):
    """Cat breed classifier: MobileNetV3-Small, transfer-learned on the
    cat breeds of the Oxford-IIIT Pet dataset (see ml/training/).

    Trained weights are not committed to the repo (see .gitignore) —
    run `python ml/scripts/prepare_dataset.py` then
    `python ml/training/train_breed_classifier.py` to produce them
    locally. If the weights or torch itself aren't available, this
    model reports `is_available = False` and the analysis pipeline
    falls back to demo mode rather than crashing — see
    app/services/analysis_service.py.
    """

    name = "breed_classifier"
    version = "0.1.0"

    def __init__(self) -> None:
        self._model = None
        self._class_names: list[str] | None = None
        self._transform = None
        self._device = None

    def load(self) -> None:
        settings = get_settings()
        weights_path = Path(settings.breed_classifier_weights_path)
        class_names_path = Path(settings.breed_classifier_class_names_path)

        if not weights_path.exists() or not class_names_path.exists():
            logger.warning(
                "Breed classifier weights not found at %s — running in demo mode "
                "until `python ml/training/train_breed_classifier.py` is run.",
                weights_path,
            )
            return

        try:
            import torch
            from torchvision import transforms
            from torchvision.models import mobilenet_v3_small
        except ImportError:
            logger.warning(
                "torch/torchvision not installed — breed classifier running in demo mode."
            )
            return

        self._class_names = json.loads(class_names_path.read_text())
        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        model = mobilenet_v3_small()
        in_features = model.classifier[-1].in_features
        model.classifier[-1] = torch.nn.Linear(in_features, len(self._class_names))
        model.load_state_dict(torch.load(weights_path, map_location=self._device))
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
        logger.info(
            "Loaded breed classifier: %d classes on %s", len(self._class_names), self._device
        )

    @property
    def is_available(self) -> bool:
        return self._model is not None

    @property
    def class_names(self) -> list[str]:
        """Display-normalized (`"_"` → `" "`) breed labels this model
        can predict, in class-index order — `[]` if not loaded. Public
        so callers (e.g. `explanation_service.py`, validating an
        explicit `target_class`) never need to reach into a private
        attribute to ask "is this a known class."""
        if self._class_names is None:
            return []
        return [name.replace("_", " ") for name in self._class_names]

    def predict(self, image: Image.Image) -> BreedPrediction:
        if not self.is_available:
            raise RuntimeError("BreedClassifier.predict called while is_available=False")

        import torch

        tensor = self._transform(image.convert("RGB")).unsqueeze(0).to(self._device)
        with torch.no_grad():
            logits = self._model(tensor)
            probs = torch.softmax(logits, dim=1)[0]
            top_idx = int(torch.argmax(probs).item())

        return BreedPrediction(
            label=self._class_names[top_idx].replace("_", " "),
            confidence=float(probs[top_idx].item()),
        )

    def explain(self, image: Image.Image, target_class_label: str | None = None) -> GradCamResult:
        """Real Grad-CAM against this model's actual trained weights —
        never a decorative/fake heatmap, never random regions, never
        hard-coded locations. Algorithm (Selvaraju et al., 2017):

        1. Forward pass through the full model.
        2. Pick the target class logit (the caller's `target_class_label`
           if given, else this model's own top prediction for `image` —
           computed fresh here, not assumed from an earlier call).
        3. Backward pass from that one logit — gradients of "how much
           would this class's score change" flow back to
           `features[-1]` (the last convolutional block; see
           ARCHITECTURE.md §23 for why this is the correct target
           layer for this specific architecture, verified by inspecting
           real shapes, not assumed).
        4. Global-average-pool the gradients over the spatial
           dimensions → one importance weight per feature channel.
        5. Weight each channel's activation map by that coefficient and
           sum across channels → a single (7, 7) importance map.
        6. ReLU — keep only features that *positively* support the
           target class; a purely inhibitory region isn't "why the
           model predicted this."
        7. Min-max normalize to [0, 1].
        8. Bilinearly resize from the model's internal (7, 7) resolution
           up to the *original* image's actual pixel dimensions.

        Raises `RuntimeError` if the model isn't available, and
        `ValueError` if `target_class_label` isn't one of this model's
        known classes — both are real error conditions the caller
        (`app/services/explanation_service.py`) turns into an honest
        "unavailable" response, never a fabricated result.
        """
        if not self.is_available:
            raise RuntimeError("BreedClassifier.explain called while is_available=False")

        import torch
        import torch.nn.functional as torch_functional

        rgb_image = image.convert("RGB")
        original_width, original_height = rgb_image.size
        tensor = self._transform(rgb_image).unsqueeze(0).to(self._device)

        normalized_names = [name.replace("_", " ") for name in self._class_names]
        target_idx: int | None = None
        if target_class_label is not None:
            if target_class_label not in normalized_names:
                raise ValueError(f"Unknown target class: {target_class_label!r}")
            target_idx = normalized_names.index(target_class_label)

        activations: dict[str, torch.Tensor] = {}
        gradients: dict[str, torch.Tensor] = {}
        target_layer = self._model.features[-1]

        def _capture_activation(_module, _inputs, output):
            activations["value"] = output

        def _capture_gradient(_module, _grad_input, grad_output):
            gradients["value"] = grad_output[0]

        forward_handle = target_layer.register_forward_hook(_capture_activation)
        backward_handle = target_layer.register_full_backward_hook(_capture_gradient)

        try:
            self._model.zero_grad()
            logits = self._model(tensor)
            probs = torch.softmax(logits, dim=1)[0]

            if target_idx is None:
                target_idx = int(torch.argmax(logits, dim=1).item())

            confidence = float(probs[target_idx].item())
            logits[0, target_idx].backward()

            feature_maps = activations["value"][0]  # (C, H, W), real forward activations
            grads = gradients["value"][0]  # (C, H, W), real backpropagated gradients

            channel_weights = grads.mean(dim=(1, 2))  # global-average-pool -> (C,)
            cam = torch.einsum("c,chw->hw", channel_weights, feature_maps)
            cam = torch_functional.relu(cam)

            cam_min = cam.min()
            cam_max = cam.max()
            if (cam_max - cam_min).item() > 1e-8:
                cam = (cam - cam_min) / (cam_max - cam_min)
            else:
                # Degenerate case: no channel had any positive
                # contribution at all — an all-zero heatmap is the
                # honest result, not a fabricated one.
                cam = torch.zeros_like(cam)

            cam = cam.unsqueeze(0).unsqueeze(0)  # (1, 1, h, w) for interpolate
            cam = torch_functional.interpolate(
                cam,
                size=(original_height, original_width),
                mode="bilinear",
                align_corners=False,
            )
            heatmap = cam.squeeze().detach().cpu().numpy().astype(np.float32)
        finally:
            forward_handle.remove()
            backward_handle.remove()

        return GradCamResult(
            target_class_index=target_idx,
            target_class_label=self._class_names[target_idx].replace("_", " "),
            confidence=confidence,
            heatmap=heatmap,
            image_width=original_width,
            image_height=original_height,
        )


_classifier: BreedClassifier | None = None


def get_breed_classifier() -> BreedClassifier:
    """Process-wide singleton, loaded lazily on first use."""
    global _classifier
    if _classifier is None:
        _classifier = BreedClassifier()
        _classifier.load()
    return _classifier
