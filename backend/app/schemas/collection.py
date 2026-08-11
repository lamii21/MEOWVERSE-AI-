from datetime import datetime

from pydantic import BaseModel

from app.schemas.analysis import AnalysisResult


class CollectionPage(BaseModel):
    items: list[AnalysisResult]
    total: int
    page: int
    page_size: int


class CollectionStats(BaseModel):
    total_cats: int
    favorite_breed: str | None
    most_common_color: str | None
    legendary_count: int
    favorites_count: int
    stories_created: int


class AchievementOut(BaseModel):
    key: str
    emoji: str
    label: str
    description: str
    unlocked: bool
    unlocked_at: datetime | None = None
