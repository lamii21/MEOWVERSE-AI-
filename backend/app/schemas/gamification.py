from pydantic import BaseModel, Field

from app.schemas.achievement import AchievementOut


class GamificationEvent(BaseModel):
    """Attached to a mutation response (analysis create/save, favorite,
    share, story-generate) so the frontend can react to *this specific*
    action — show a toast for a level-up or newly-unlocked achievement,
    only when one genuinely just happened, without a second round-trip.

    `xp_awarded` is 0 when the underlying event had already happened
    before (e.g. re-favoriting a cat you've already favorited once) —
    idempotent by design, see CollectionEventModel.
    """

    xp_awarded: int
    total_xp: int
    level: int
    leveled_up: bool
    is_new_breed: bool = False
    is_new_rarity: bool = False
    newly_unlocked: list[AchievementOut] = Field(default_factory=list)
