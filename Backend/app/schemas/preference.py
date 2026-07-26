from pydantic import BaseModel, ConfigDict, Field


class PreferenceCreate(BaseModel):

    travel_style: str | None = None

    food_preference: str | None = None

    interests: list[str] = Field(default_factory=list)

    preferred_transport: str | None = None

    preferred_hotel_type: str | None = None

    budget_min: int | None = None

    budget_max: int | None = None


class PreferenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    travel_style: str | None
    food_preference: str | None
    interests: list[str] = Field(default_factory=list)
    preferred_transport: str | None
    preferred_hotel_type: str | None
    budget_min: int | None
    budget_max: int | None


class PreferenceChoicePrompt(BaseModel):
    has_saved_preferences: bool
    message: str
    saved_preferences: PreferenceResponse | None = None


class PreferenceSaveResponse(BaseModel):
    message: str
