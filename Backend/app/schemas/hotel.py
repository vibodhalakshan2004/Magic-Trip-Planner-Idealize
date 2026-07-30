from datetime import date
from typing import List, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

HotelType = Literal[
    "hotel",
    "guest_house",
    "villa",
    "resort",
    "hostel",
    "homestay",
    "apartment",
    "any"
]


HotelSource = Literal[
    "ai_suggested",
    "user_added"
]


class HotelSuggestRequest(BaseModel):
    use_saved_preferences: bool | None = Field(
        default=None,
        description="Set to true to use saved preferences, false to ignore them and use fresh request inputs.",
    )

    hotel_type: HotelType = "any"

    hotel_preference: str | None = Field(
        default=None,
        examples=["Budget friendly hotel close to selected places"]
    )

    rooms: int = Field(default=1, ge=1, le=10)

    max_results: int = Field(default=5, ge=3, le=10)


class HotelRecommendation(BaseModel):
    hotel_key: str | None = None
    name: str = Field(..., min_length=2)
    short_description: str | None = None

    hotel_type: HotelType = "hotel"
    source: HotelSource = "ai_suggested"

    area: str | None = None

    check_in_date: date | None = None
    check_out_date: date | None = None

    nights: int = Field(default=1, ge=1)
    rooms: int = Field(default=1, ge=1)

    estimated_price_per_night_lkr: float = Field(default=0, ge=0)
    total_estimated_price_lkr: float = Field(default=0, ge=0)

    rating_estimate: float | None = Field(default=None, ge=0, le=5)

    latitude: float | None = None
    longitude: float | None = None

    distance_summary: str | None = None
    reason_for_recommendation: str | None = None

    amenities: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

    search_query: str | None = None
    image_url: str | None = None
    priority_score: int = Field(default=5, ge=1, le=10)

    day_number: int | None = Field(default=None, ge=1)
    route_plan_id: UUID | None = None
    transfer_distance_km: float = Field(default=0, ge=0)
    transfer_time_minutes: float = Field(default=0, ge=0)
    transfer_cost_lkr: float = Field(default=0, ge=0)

    @model_validator(mode="after")
    def calculate_total_if_missing(self):
        if self.total_estimated_price_lkr == 0:
            self.total_estimated_price_lkr = (
                self.estimated_price_per_night_lkr * self.nights * self.rooms
            )

        return self


class HotelAgentResponse(BaseModel):
    trip_id: UUID
    destination: str

    nights: int
    rooms: int

    summary: str

    recommended_hotels: List[HotelRecommendation] = Field(
        ...,
        min_length=1,
        max_length=10
    )

    question_for_user: str = "Which hotels would you like to select?"


class SelectHotelsRequest(BaseModel):
    selected_hotels: List[HotelRecommendation] = Field(..., min_length=1)


class SelectedHotelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    trip_id: UUID
    route_plan_id: UUID | None = None
    day_number: int | None = None

    hotel_key: str
    name: str
    short_description: str | None

    hotel_type: str
    source: str

    area: str | None

    check_in_date: date | None
    check_out_date: date | None

    nights: int
    rooms: int

    estimated_price_per_night_lkr: float
    total_estimated_price_lkr: float

    rating_estimate: float | None

    latitude: float | None
    longitude: float | None

    distance_summary: str | None
    transfer_distance_km: float = 0
    transfer_time_minutes: float = 0
    transfer_cost_lkr: float = 0
    reason_for_recommendation: str | None

    amenities: List[str]
    warnings: List[str]

    search_query: str | None
    image_url: str | None


class SelectHotelsResponse(BaseModel):
    trip_id: UUID
    selected_hotels_count: int
    selected_hotels: List[SelectedHotelResponse]
    message: str


class HotelSearchSuggestion(BaseModel):
    hotel_key: str
    name: str
    short_description: str | None = None
    hotel_type: str
    source: str
    area: str | None = None
    estimated_price_per_night_lkr: float
    total_estimated_price_lkr: float
    rating_estimate: float | None = None
    latitude: float | None = None
    longitude: float | None = None
    distance_summary: str | None = None
    reason_for_recommendation: str | None = None
    amenities: List[str]
    warnings: List[str]
    search_query: str | None = None
    image_url: str | None = None
    priority_score: int


class HotelSearchResponse(BaseModel):
    query: str
    destination: str | None = None
    suggestions: List[HotelSearchSuggestion]


class DailyHotelSuggestRequest(BaseModel):
    hotel_type: HotelType = "any"
    hotel_preference: str | None = None
    rooms: int = Field(default=1, ge=1, le=10)
    max_results: int = Field(default=5, ge=3, le=10)
    radius_km: float = Field(default=20, ge=2, le=75)


class DailyHotelSuggestionResponse(BaseModel):
    trip_id: UUID
    day_number: int
    route_plan_id: UUID
    suggestions: List[HotelRecommendation]
    summary: str


class DailyHotelSelectRequest(BaseModel):
    hotel: HotelRecommendation | None = None
    go_home_without_hotel: bool = False


class DailyHotelSelectResponse(BaseModel):
    trip_id: UUID
    day_number: int
    selected_hotel: SelectedHotelResponse | None = None
    message: str
