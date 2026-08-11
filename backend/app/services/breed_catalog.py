"""The canonical "breed universe" used for Breed Explorer and
collection-completion percentage (Phase 10 spec §9-10).

`ml/models/class_names.json` (the trained breed classifier's label
set, see app/ml/breed_classifier.py) is the canonical list — it's
committed to the repo and always present, unlike the trained weights
themselves, so this never silently falls back to an empty universe.

This is a deliberately different concept from "have I seen this exact
breed_label before" (the discovery-moment check in
app/services/gamification.py, which fires for ANY breed string
including demo-mode-only labels like "Domestic Shorthair"): breed
*completion* is scoped to this fixed, documented list so the
denominator can never silently change size. See PROJECT_STATUS.md for
the honest caveat this creates in demo mode (only 4 of the 5 demo
breeds are members of this list, so a demo-mode-only user can reach at
most 4/12 ≈ 33% breed completion no matter how many cats they analyze
— documented, not hidden).
"""

import json
import logging
from functools import lru_cache
from pathlib import Path

from app.core.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_supported_breeds() -> tuple[str, ...]:
    settings = get_settings()
    path = Path(settings.breed_classifier_class_names_path)
    if not path.exists():
        logger.warning(
            "Breed class names file not found at %s — breed universe is empty.", path
        )
        return ()
    return tuple(json.loads(path.read_text()))
