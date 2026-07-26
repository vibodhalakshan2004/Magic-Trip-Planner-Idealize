from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict, model_validator


TransportType = Literal[
    "car",
    "bus",
    "train",
    "taxi",
    "bike",
    "walking",
    "mixed",
]


class TripCreate(BaseModel):
    start_location: str = Field(..., min_length=2)
    destination: str = Field(..., min_length=2)

    start_date: date
    end_date: date

    budget_min: int = Field(..., ge=0)
    budget_max: int = Field(..., gt=0)

    travelers: int = Field(default=1, ge=1, le=20)

    transport_type: TransportType = "car"

    @model_validator(mode="after")
    def validate_trip(self):
        today = date.today()

        if self.start_date < today:
            raise ValueError("start_date cannot be in the past")

        if self.end_date < today:
            raise ValueError("end_date cannot be in the past")

        if self.end_date < self.start_date:
            raise ValueError("end_date must be after or equal to start_date")

        if self.budget_max < self.budget_min:
            raise ValueError("budget_max must be greater than or equal to budget_min")

        return self


class TripResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID

    start_location: str
    destination: str

    start_date: date
    end_date: date

    budget_min: int
    budget_max: int

    travelers: int
    transport_type: TransportType

    created_at: datetime
    updated_at: datetime
