from pydantic import BaseModel
from typing import List
from typing import Optional
from typing import Dict


class TripState(BaseModel):

    # User Inputs

    start_location: str

    destination: str

    start_date: str

    end_date: str

    budget_min: int

    budget_max: int

    transport_type: str

    # Destination Agent Output

    selected_places: List[str] = []

    # Hotel Agent Output

    selected_hotel: Optional[Dict] = None

    # Budget Agent Output

    transport_cost: float = 0

    hotel_cost: float = 0

    food_cost: float = 0

    activity_cost: float = 0

    total_cost: float = 0

    budget_exceeded: bool = False

    # Future Agents

    weather_alerts: List[str] = []

    road_alerts: List[str] = []

    optimized_route: List[str] = []

    itinerary: List[Dict] = []

    # Future Route Agent

    route_distance: float = 0

    route_duration: float = 0

    route_polyline: str | None = None