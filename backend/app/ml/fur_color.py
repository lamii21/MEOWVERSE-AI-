import logging

from PIL import Image

from app.ml.base_model import BaseModel
from app.schemas.analysis import ColorSwatch

logger = logging.getLogger(__name__)

MAX_DIMENSION_PX = 200
N_CLUSTERS = 3

# Named reference colors for fur-tone labeling. Deliberately small and
# fur-relevant (not a general CSS color list) — nearest neighbor in RGB
# space is a defensible approximation for this feature, not a
# perceptually-calibrated color science claim. See ARCHITECTURE.md §4.
_NAMED_COLORS: dict[str, tuple[int, int, int]] = {
    "white": (245, 245, 245),
    "cream": (240, 225, 200),
    "ivory": (230, 220, 195),
    "silver": (196, 196, 196),
    "gray": (140, 140, 140),
    "charcoal": (70, 68, 66),
    "black": (25, 24, 22),
    "caramel": (180, 130, 80),
    "tan": (200, 165, 120),
    "ginger": (200, 110, 50),
    "orange": (210, 120, 50),
    "chocolate": (95, 60, 40),
    "brown": (110, 75, 45),
    "cinnamon": (150, 100, 65),
    "lilac": (190, 175, 175),
    "blue": (110, 115, 125),
    "cream-white": (250, 240, 225),
}


def _nearest_color_name(rgb: tuple[float, float, float]) -> str:
    best_name, best_dist = "unknown", float("inf")
    for name, ref in _NAMED_COLORS.items():
        dist = sum((a - b) ** 2 for a, b in zip(rgb, ref, strict=True))
        if dist < best_dist:
            best_name, best_dist = name, dist
    return best_name


class FurColorAnalyzer(BaseModel):
    """Dominant fur color extraction via GrabCut foreground segmentation
    + K-means clustering (OpenCV + scikit-learn). Unlike BreedClassifier
    there are no weights to download — `is_available` just reflects
    whether the CV dependencies (opencv-python-headless, scikit-learn,
    numpy) are importable, so this still degrades to the demo palette
    on a lean install rather than crashing. See
    app/services/analysis_service.py for the fallback wiring.
    """

    name = "fur_color_analyzer"
    version = "0.1.0"

    def __init__(self) -> None:
        self._available = False

    def load(self) -> None:
        try:
            import cv2  # noqa: F401
            import numpy  # noqa: F401
            from sklearn.cluster import KMeans  # noqa: F401
        except ImportError:
            logger.warning(
                "opencv/numpy/scikit-learn not installed — fur color analysis "
                "running in demo mode."
            )
            return
        self._available = True

    @property
    def is_available(self) -> bool:
        return self._available

    def predict(self, image: Image.Image) -> list[ColorSwatch]:
        if not self.is_available:
            raise RuntimeError("FurColorAnalyzer.predict called while is_available=False")

        import cv2
        import numpy as np
        from sklearn.cluster import KMeans

        rgb_image = image.convert("RGB")
        rgb_image.thumbnail((MAX_DIMENSION_PX, MAX_DIMENSION_PX))
        bgr = cv2.cvtColor(np.array(rgb_image), cv2.COLOR_RGB2BGR)
        h, w = bgr.shape[:2]

        mask = np.zeros((h, w), np.uint8)
        bg_model = np.zeros((1, 65), np.float64)
        fg_model = np.zeros((1, 65), np.float64)
        margin_x, margin_y = int(w * 0.08), int(h * 0.08)
        rect = (margin_x, margin_y, w - 2 * margin_x, h - 2 * margin_y)

        try:
            # Phase 16 finding: cv2.grabCut is NOT deterministic by
            # default on identical input — its internal GMM/EM
            # initialization draws from OpenCV's global RNG, which
            # `KMeans(random_state=42)` below has no influence over.
            # Confirmed via direct measurement: 5 back-to-back calls on
            # byte-identical input produced 3 different foreground
            # masks (28/32/33/32/28 pixels) before this seed call, and
            # 5 identical masks after it. `cv2.setRNGSeed` seeds
            # OpenCV's own RNG (a separate generator from Python's
            # `random`/numpy's, and from scikit-learn's
            # `random_state`), so it has to be set explicitly here
            # rather than relying on any seed already set elsewhere.
            cv2.setRNGSeed(42)
            cv2.grabCut(bgr, mask, rect, bg_model, fg_model, 5, cv2.GC_INIT_WITH_RECT)
            foreground = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 1, 0).astype(
                "uint8"
            )
        except cv2.error:
            logger.warning("GrabCut failed, falling back to full image for color analysis")
            foreground = np.ones((h, w), dtype="uint8")

        rgb_array = np.array(rgb_image)
        pixels = rgb_array[foreground == 1]
        if pixels.shape[0] < N_CLUSTERS * 10:
            # Segmentation degenerated (near-empty mask) — use the whole image.
            pixels = rgb_array.reshape(-1, 3)

        kmeans = KMeans(n_clusters=N_CLUSTERS, n_init=10, random_state=42)
        labels = kmeans.fit_predict(pixels)
        centers = kmeans.cluster_centers_

        counts = np.bincount(labels, minlength=N_CLUSTERS)
        total = counts.sum()

        swatches = []
        for idx in np.argsort(-counts):
            r, g, b = (int(c) for c in centers[idx])
            swatches.append(
                ColorSwatch(
                    name=_nearest_color_name((r, g, b)),
                    hex=f"#{r:02X}{g:02X}{b:02X}",
                    percentage=round(float(counts[idx] / total * 100), 1),
                )
            )
        return swatches


_analyzer: FurColorAnalyzer | None = None


def get_fur_color_analyzer() -> FurColorAnalyzer:
    """Process-wide singleton, loaded lazily on first use."""
    global _analyzer
    if _analyzer is None:
        _analyzer = FurColorAnalyzer()
        _analyzer.load()
    return _analyzer
