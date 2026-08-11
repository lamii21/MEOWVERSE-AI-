import uuid
from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.gamification import GamificationEvent


class StoryStyle(str, Enum):
    MAGICAL_ADVENTURE = "magical_adventure"
    COZY_WHOLESOME = "cozy_wholesome"
    FUNNY_CHAOTIC = "funny_chaotic"
    DREAMY_EMOTIONAL = "dreamy_emotional"
    FANTASY_QUEST = "fantasy_quest"


STORY_STYLE_LABELS: dict[StoryStyle, tuple[str, str, str]] = {
    # style -> (emoji, display name, short description)
    StoryStyle.MAGICAL_ADVENTURE: ("✨", "Magical Adventure", "A sparkling quest full of wonder."),
    StoryStyle.COZY_WHOLESOME: ("🌸", "Cozy & Wholesome", "A gentle, heartwarming little tale."),
    StoryStyle.FUNNY_CHAOTIC: ("😂", "Funny & Chaotic", "Silly antics and delightful chaos."),
    StoryStyle.DREAMY_EMOTIONAL: ("🌙", "Dreamy & Emotional", "A soft, wistful, dreamlike story."),
    StoryStyle.FANTASY_QUEST: ("🧙", "Fantasy Quest", "An epic-feeling adventure in miniature."),
}


class StoryChapter(BaseModel):
    chapter_number: int = Field(ge=1, le=5)
    title: str = Field(max_length=80)
    # ~180 words max, generous character ceiling rather than an exact
    # word-count enforcement.
    text: str = Field(max_length=1200)


class CatStory(BaseModel):
    """Strictly-validated story output — AI-generated creative content,
    same honesty contract as CatProfile (see app/schemas/profile.py):
    never presented as fact, and structurally bounded so a runaway
    generation can't produce an unbounded wall of text.
    """

    title: str = Field(max_length=100)
    subtitle: str = Field(max_length=150)
    opening: str = Field(max_length=800)
    chapters: list[StoryChapter] = Field(min_length=3, max_length=5)
    ending: str = Field(max_length=800)
    moral: str = Field(max_length=300)
    quote: str = Field(max_length=200)


StoryMode = Literal["demo", "generated"]


class StoryRequest(BaseModel):
    style: StoryStyle = StoryStyle.MAGICAL_ADVENTURE
    regenerate: bool = False


class StoryResponse(BaseModel):
    id: uuid.UUID
    analysis_id: uuid.UUID
    style: StoryStyle
    story: CatStory
    story_mode: StoryMode
    provider: str
    is_public: bool
    created_at: datetime
    # Phase 10: set only when the caller is authenticated and owns the
    # analysis this story belongs to — see app/api/v1/stories.py.
    gamification: GamificationEvent | None = None
