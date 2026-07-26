from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class DestinationSuggestRequest(BaseModel):
    use_saved_preferences: bool | None = Field(
        default=None,
        description="Set to true to use saved preferences, false to ignore them and use fresh request inputs.",
    )

    interests: List[str] = Field(
        default_factory=list,
        examples=[["nature", "hiking", "photography"]],
    )

    trip_style: Optional[
        Literal["relaxed", "balanced", "packed"]
    ] = Field(
        default=None,
        examples=["balanced"],
    )

    special_notes: Optional[str] = Field(
        default=None,
        examples=["I prefer scenic places and less crowded locations."],
    )


class SuggestedPlace(BaseModel):

    place_key: str = Field(..., examples=["little_adams_peak"])

    name: str = Field(..., examples=["Little Adam's Peak"])

    source: str = "ai_suggested"

    category: Literal[
        "nature",
        "culture",
        "food",
        "adventure",
        "religious",
        "viewpoint",
        "beach",
        "shopping",
        "historical",
        "other",
    ]

    short_description: str

    reason_for_recommendation: str

    best_time_to_visit: Literal[
        "sunrise",
        "morning",
        "afternoon",
        "evening",
        "sunset",
        "flexible",
    ]

    estimated_visit_duration_hours: float = Field(..., gt=0, le=12)

    estimated_cost_lkr_per_person: float = Field(..., ge=0)

    priority_score: int = Field(..., ge=1, le=10)

    suitable_for: List[str] = Field(default_factory=list)

    warnings: List[str] = Field(default_factory=list)

    search_query: str = Field(
        ...,
        examples=["Little Adam's Peak Ella Sri Lanka"],
    )

    weather_summary: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    image_url: str | None = None
    opening_hours: str | None = None
    availability_warnings: List[str] = Field(default_factory=list)


class DestinationAgentResponse(BaseModel):

    trip_id: str

    destination: str

    summary: str

    suggested_places: List[SuggestedPlace] = Field(
        ...,
        min_length=3,
        max_length=10,
    )

    question_for_user: str = "Which places would you like to add to your trip?"


class PlaceSearchSuggestion(BaseModel):
    place_key: str
    name: str
    display_name: str
    category: str
    source: str
    short_description: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    image_url: str | None = None
    opening_hours: str | None = None
    availability_warnings: List[str] = Field(default_factory=list)
    osm_type: str | None = None
    osm_id: int | None = None
    search_query: str | None = None


class PlaceSearchResponse(BaseModel):
    query: str
    destination: str | None = None
    suggestions: List[PlaceSearchSuggestion]
