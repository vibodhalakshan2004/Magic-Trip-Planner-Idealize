from typing import List, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


BudgetStatus = Literal[
    "within_budget",
    "near_limit",
    "over_budget",
]


class BudgetCalculateRequest(BaseModel):
    food_cost_per_person_per_day_lkr: float = Field(
        default=2500,
        ge=0
    )

    shopping_other_cost_lkr: float = Field(
        default=0,
        ge=0
    )


class BudgetBreakdownItem(BaseModel):
    category: str
    description: str
    amount_lkr: float


class BudgetAgentResponse(BaseModel):
    trip_id: UUID
    destination: str

    days: int
    nights: int
    travelers: int

    budget_min_lkr: float
    budget_max_lkr: float

    selected_places_cost_lkr: float
    hotel_cost_lkr: float
    food_cost_lkr: float
    transport_cost_lkr: float
    other_cost_lkr: float

    subtotal_lkr: float
    buffer_lkr: float
    total_estimated_cost_lkr: float

    remaining_budget_lkr: float
    over_budget_amount_lkr: float

    budget_status: BudgetStatus

    breakdown: List[BudgetBreakdownItem]
    warnings: List[str]
    suggestions: List[str]

    summary: str


class SavedBudgetEstimateResponse(BudgetAgentResponse):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    summary: str | None = None
