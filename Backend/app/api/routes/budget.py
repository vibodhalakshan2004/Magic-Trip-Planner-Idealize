from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agents.budget_agent import BudgetAgent
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.budget_estimate import BudgetEstimate
from app.models.route_plan import RoutePlan
from app.models.selected_hotel import SelectedHotel
from app.models.selected_place import SelectedPlace
from app.models.user import User
from app.schemas.budget import (
    BudgetAgentResponse,
    BudgetCalculateRequest,
    SavedBudgetEstimateResponse,
)
from app.services.trip_access import require_trip_access

router = APIRouter(
    prefix="/budget",
    tags=["Budget Agent"],
)


@router.post(
    "/trips/{trip_id}/calculate",
    response_model=BudgetAgentResponse,
)
def calculate_budget_for_trip(
    trip_id: UUID,
    request: BudgetCalculateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    trip = require_trip_access(db, trip_id, current_user.id, write=True)

    selected_places = (
        db.query(SelectedPlace)
        .filter(
            SelectedPlace.trip_id == trip.id,
        )
        .all()
    )

    if not selected_places:
        raise HTTPException(
            status_code=400,
            detail="Please select at least one place before calculating budget.",
        )

    selected_hotels = (
        db.query(SelectedHotel)
        .filter(
            SelectedHotel.trip_id == trip.id,
        )
        .all()
    )

    try:
        agent = BudgetAgent()
        route_plan = (
            db.query(RoutePlan)
            .filter(
                RoutePlan.trip_id == trip.id,
                RoutePlan.route_status == "confirmed",
            )
            .order_by(RoutePlan.created_at.desc())
            .first()
        )

        result = agent.calculate_budget(
            trip=trip,
            selected_places=selected_places,
            selected_hotels=selected_hotels,
            request=request,
            route_plan=route_plan,
        )

        if route_plan:
            required_hotel_days = max((len(route_plan.days or []) - 1), 0)
            selected_day_numbers = {
                hotel.day_number for hotel in selected_hotels if hotel.day_number is not None
            }
            if len(selected_day_numbers) < required_hotel_days:
                result.warnings.append(
                    "Hotel selections are incomplete. The last day can go directly home, but earlier overnight stays may need hotels."
                )

        db.query(BudgetEstimate).filter(
            BudgetEstimate.trip_id == trip.id
        ).delete(synchronize_session=False)

        budget_estimate = BudgetEstimate(
            trip_id=trip.id,
            days=result.days,
            nights=result.nights,
            travelers=result.travelers,
            budget_min_lkr=result.budget_min_lkr,
            budget_max_lkr=result.budget_max_lkr,
            selected_places_cost_lkr=result.selected_places_cost_lkr,
            hotel_cost_lkr=result.hotel_cost_lkr,
            food_cost_lkr=result.food_cost_lkr,
            transport_cost_lkr=result.transport_cost_lkr,
            other_cost_lkr=result.other_cost_lkr,
            subtotal_lkr=result.subtotal_lkr,
            buffer_lkr=result.buffer_lkr,
            total_estimated_cost_lkr=result.total_estimated_cost_lkr,
            remaining_budget_lkr=result.remaining_budget_lkr,
            over_budget_amount_lkr=result.over_budget_amount_lkr,
            budget_status=result.budget_status,
            breakdown=[
                item.model_dump(mode="json")
                for item in result.breakdown
            ],
            warnings=result.warnings,
            suggestions=result.suggestions,
            summary=result.summary,
        )

        db.add(budget_estimate)
        trip.updated_at = datetime.utcnow()
        db.commit()

        return result

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Unable to calculate the budget right now.",
        )


@router.get(
    "/trips/{trip_id}/latest",
    response_model=SavedBudgetEstimateResponse,
)
def get_latest_budget_for_trip(
    trip_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    trip = require_trip_access(db, trip_id, current_user.id)

    budget_estimate = (
        db.query(BudgetEstimate)
        .filter(BudgetEstimate.trip_id == trip.id)
        .order_by(BudgetEstimate.created_at.desc())
        .first()
    )

    if not budget_estimate:
        raise HTTPException(
            status_code=404,
            detail="Budget estimate not found",
        )

    return {
        "id": budget_estimate.id,
        "trip_id": budget_estimate.trip_id,
        "destination": trip.destination,
        "days": budget_estimate.days,
        "nights": budget_estimate.nights,
        "travelers": budget_estimate.travelers,
        "budget_min_lkr": budget_estimate.budget_min_lkr,
        "budget_max_lkr": budget_estimate.budget_max_lkr,
        "selected_places_cost_lkr": budget_estimate.selected_places_cost_lkr,
        "hotel_cost_lkr": budget_estimate.hotel_cost_lkr,
        "food_cost_lkr": budget_estimate.food_cost_lkr,
        "transport_cost_lkr": budget_estimate.transport_cost_lkr,
        "other_cost_lkr": budget_estimate.other_cost_lkr,
        "subtotal_lkr": budget_estimate.subtotal_lkr,
        "buffer_lkr": budget_estimate.buffer_lkr,
        "total_estimated_cost_lkr": budget_estimate.total_estimated_cost_lkr,
        "remaining_budget_lkr": budget_estimate.remaining_budget_lkr,
        "over_budget_amount_lkr": budget_estimate.over_budget_amount_lkr,
        "budget_status": budget_estimate.budget_status,
        "breakdown": budget_estimate.breakdown,
        "warnings": budget_estimate.warnings,
        "suggestions": budget_estimate.suggestions,
        "summary": budget_estimate.summary,
    }
