from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict
from datetime import date

from pydantic import Field


class ReviewCreate(BaseModel):

    place_name: str

    place_type: str

    rating: int = Field(
        ge=1,
        le=5
    )

    review_text: str

    visit_date: date | None = None


class ReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    place_name: str
    place_type: str
    rating: int
    review_text: str
    visit_date: date | None = None


class ReviewCreateResponse(BaseModel):
    message: str
    review_id: str
