from datetime import datetime

from pydantic import BaseModel


class AchievementOut(BaseModel):
    """Its own leaf module (no imports of other app.schemas modules) so
    both schemas/collection.py and schemas/gamification.py can depend
    on it without a cycle — gamification.py needs it for
    `newly_unlocked`, and schemas/analysis.py needs GamificationEvent,
    which would otherwise cycle back through collection.py's import of
    AnalysisResult. See app/schemas/common.py for the earlier instance
    of this same pattern (Phase 3)."""

    key: str
    emoji: str
    label: str
    description: str
    unlocked: bool
    unlocked_at: datetime | None = None
    progress_current: int = 0
    progress_target: int = 1
