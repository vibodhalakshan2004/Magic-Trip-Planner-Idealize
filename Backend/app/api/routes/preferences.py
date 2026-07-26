from fastapi import APIRouter
from fastapi import Depends

from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user

from app.models.user import User
from app.models.preference import Preference

from app.schemas.preference import (
    PreferenceChoicePrompt,
    PreferenceCreate,
    PreferenceResponse,
    PreferenceSaveResponse,
)

router = APIRouter(
    prefix="/preferences",
    tags=["Preferences"]
)

@router.post("/", response_model=PreferenceSaveResponse)
def save_preferences(
    preference: PreferenceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    existing = (
        db.query(Preference)
        .filter(
            Preference.user_id == current_user.id
        )
        .first()
    )

    if existing:

        existing.travel_style = preference.travel_style
        existing.food_preference = preference.food_preference
        existing.interests = preference.interests
        existing.preferred_transport = preference.preferred_transport
        existing.preferred_hotel_type = preference.preferred_hotel_type
        existing.budget_min = preference.budget_min
        existing.budget_max = preference.budget_max

        db.commit()

        return {
            "message": "Preferences updated"
        }

    new_preference = Preference(
        user_id=current_user.id,
        travel_style=preference.travel_style,
        food_preference=preference.food_preference,
        interests=preference.interests,
        preferred_transport=preference.preferred_transport,
        preferred_hotel_type=preference.preferred_hotel_type,
        budget_min=preference.budget_min,
        budget_max=preference.budget_max
    )

    db.add(new_preference)

    db.commit()

    return {
        "message": "Preferences saved"
    }

@router.get("/", response_model=PreferenceResponse | None)
def get_preferences(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    preference = (
        db.query(Preference)
        .filter(
            Preference.user_id == current_user.id
        )
        .first()
    )

    return preference


@router.get("/choice-prompt", response_model=PreferenceChoicePrompt)
def get_preference_choice_prompt(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    preference = (
        db.query(Preference)
        .filter(
            Preference.user_id == current_user.id
        )
        .first()
    )

    if not preference:
        return PreferenceChoicePrompt(
            has_saved_preferences=False,
            message="No saved preferences found. Collect fresh preferences from the user.",
            saved_preferences=None,
        )

    return PreferenceChoicePrompt(
        has_saved_preferences=True,
        message="Saved preferences found. Ask the user whether to use them or provide new ones.",
        saved_preferences=PreferenceResponse.model_validate(preference),
    )
