from pydantic import BaseModel, Field


class ColorSwatch(BaseModel):
    name: str
    hex: str
    percentage: float = Field(ge=0.0, le=100.0)
