import json
import logging
from pathlib import Path

from PIL import Image

from app.core.config import get_settings
from app.ml.base_model import BaseModel
from app.schemas.analysis import BreedPrediction

logger = logging.getLogger(__name__)

IMAGE_SIZE = 224
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]


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


_classifier: BreedClassifier | None = None


def get_breed_classifier() -> BreedClassifier:
    """Process-wide singleton, loaded lazily on first use."""
    global _classifier
    if _classifier is None:
        _classifier = BreedClassifier()
        _classifier.load()
    return _classifier
