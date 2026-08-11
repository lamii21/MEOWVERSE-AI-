from abc import ABC, abstractmethod
from typing import Any

from PIL import Image


class BaseModel(ABC):
    """Contract every CV model (breed, mood, embedding, ...) must satisfy.

    Concrete models are implemented starting in Phase 4. This interface
    exists now so the pipeline and API layers can be built against a
    stable contract regardless of which model backs them.
    """

    name: str
    version: str

    @abstractmethod
    def load(self) -> None:
        """Load weights. Must be safe to call once at startup."""

    @abstractmethod
    def predict(self, image: Image.Image) -> Any:
        """Run inference on a single preprocessed image."""

    @property
    def is_available(self) -> bool:
        """False if this model has no usable weights (demo mode)."""
        return True
