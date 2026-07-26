from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


ExpenseCategory = Literal[
    "accommodation",
    "food",
    "transport",
    "activities",
    "shopping",
    "other",
]


class ChecklistItem(BaseModel):
    id: str = Field(min_length=1, max_length=80)
    label: str = Field(min_length=1, max_length=160)
    completed: bool = False


class TripExpense(BaseModel):
    id: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=160)
    amount_lkr: float = Field(gt=0, le=100_000_000)
    category: ExpenseCategory = "other"
    paid_by: str = Field(default="Shared", min_length=1, max_length=100)
    expense_date: date | None = None


class TripToolkitUpdate(BaseModel):
    traveler_notes: str = Field(default="", max_length=5_000)
    emergency_contact: str = Field(default="", max_length=500)
    checklist: list[ChecklistItem] = Field(default_factory=list, max_length=50)
    expenses: list[TripExpense] = Field(default_factory=list, max_length=200)


class TripToolkitResponse(TripToolkitUpdate):
    trip_id: str
    total_expenses_lkr: float

