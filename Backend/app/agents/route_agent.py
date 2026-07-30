import logging
import math
import re
from datetime import datetime, time, timedelta
from typing import Any, List, Optional

from app.schemas.route import (
    Coordinate,
    DayRoutePlan,
    ItineraryStop,
    RoutePlanRequest,
    RoutePlanResponse,
    RouteSegment,
)
from app.services.geocoder import GeocoderService
from app.services.osrm_router import OSRMRouterService
from app.services.transport_cost import estimate_segment_transport_cost

logger = logging.getLogger(__name__)


class RouteAgent:

    def __init__(self):
        self.geocoder = GeocoderService()
        self.router = OSRMRouterService()

    def _trip_dates(self, trip: Any) -> List:
        dates = []
        current_date = trip.start_date

        while current_date <= trip.end_date:
            dates.append(current_date)
            current_date = current_date + timedelta(days=1)

        if not dates:
            dates.append(trip.start_date)

        return dates

    def _time_to_string(self, value: datetime) -> str:
        return value.strftime("%H:%M")

    def _distance_km_between(self, origin: dict, destination: dict) -> float:
        latitude_1 = math.radians(origin["latitude"])
        longitude_1 = math.radians(origin["longitude"])
        latitude_2 = math.radians(destination["latitude"])
        longitude_2 = math.radians(destination["longitude"])

        delta_latitude = latitude_2 - latitude_1
        delta_longitude = longitude_2 - longitude_1

        value = (
            math.sin(delta_latitude / 2) ** 2
            + math.cos(latitude_1)
            * math.cos(latitude_2)
            * math.sin(delta_longitude / 2) ** 2
        )

        return 6371 * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value))

    def _parse_start_time(self, value: str) -> time:
        try:
            hour, minute = value.split(":")
            return time(hour=int(hour), minute=int(minute))

        except Exception:
            return time(hour=8, minute=0)

    def _best_hour(self, best_time: Optional[str]) -> int:
        best_time = (best_time or "flexible").lower()

        mapping = {
            "sunrise": 6,
            "morning": 8,
            "afternoon": 13,
            "evening": 16,
            "sunset": 17,
            "flexible": 9,
        }

        return mapping.get(best_time, 9)

    def _make_place_query(self, place: Any, trip: Any) -> str:
        if getattr(place, "search_query", None):
            return place.search_query

        return f"{place.name}, {trip.destination}, Sri Lanka"

    def _place_queries(self, place: Any, trip: Any) -> list[str]:
        queries = []

        if getattr(place, "search_query", None):
            queries.append(place.search_query)

        queries.append(f"{place.name}, {trip.destination}, Sri Lanka")
        queries.append(f"{place.name}, Sri Lanka")

        unique_queries = []

        for query in queries:
            if query and query not in unique_queries:
                unique_queries.append(query)

        return unique_queries

    def _make_hotel_query(self, hotel: Any, trip: Any) -> str:
        if getattr(hotel, "search_query", None):
            return hotel.search_query

        return f"{hotel.name}, {trip.destination}, Sri Lanka"

    def _hotel_queries(self, hotel: Any, trip: Any) -> list[str]:
        queries = []

        if getattr(hotel, "search_query", None):
            queries.append(hotel.search_query)

        queries.append(f"{hotel.name}, {trip.destination}, Sri Lanka")
        queries.append(f"{hotel.name} {trip.destination} Sri Lanka")
        queries.append(f"{hotel.name}, Sri Lanka")

        cleaned_name = " ".join(
            re.sub(r"[^A-Za-z0-9 ]+", " ", hotel.name).split()
        )

        if cleaned_name and cleaned_name != hotel.name:
            queries.append(f"{cleaned_name}, {trip.destination}, Sri Lanka")
            queries.append(f"{cleaned_name} {trip.destination} Sri Lanka")

        unique_queries = []

        for query in queries:
            if query and query not in unique_queries:
                unique_queries.append(query)

        return unique_queries

    def _make_start_location_query(self, trip: Any) -> str:
        return f"{trip.start_location}, Sri Lanka"

    def _point_from_place(self, place: Any, trip: Any) -> dict | None:
        latitude = getattr(place, "latitude", None)
        longitude = getattr(place, "longitude", None)

        if latitude is None or longitude is None:
            geocoded = self.geocoder.geocode_candidates(
                self._place_queries(place, trip)
            )

            if not geocoded:
                # Skip unresolvable places instead of crashing the entire route
                return None

            latitude = geocoded["latitude"]
            longitude = geocoded["longitude"]
            # SelectedPlace instances are attached to the request/worker
            # session. Saving recovered coordinates prevents repeated lookups
            # when the route is regenerated with hotels.
            place.latitude = latitude
            place.longitude = longitude

        return {
            "place_key": place.place_key,
            "name": place.name,
            "category": place.category,
            "best_time_to_visit": getattr(place, "best_time_to_visit", None),
            "opening_hours": getattr(place, "opening_hours", None),
            "availability_warnings": list(getattr(place, "availability_warnings", None) or []),
            "visit_duration_hours": float(
                getattr(place, "estimated_visit_duration_hours", 1.0) or 1.0
            ),
            "priority_score": int(getattr(place, "priority_score", 5) or 5),
            "latitude": float(latitude),
            "longitude": float(longitude),
        }

    def _point_from_hotel(self, hotel: Any, trip: Any) -> dict:
        latitude = getattr(hotel, "latitude", None)
        longitude = getattr(hotel, "longitude", None)

        if latitude is None or longitude is None:
            geocoded = self.geocoder.geocode_candidates(
                self._hotel_queries(hotel, trip)
            )

            if not geocoded:
                destination_point = self._destination_point(trip)
                latitude = destination_point["latitude"]
                longitude = destination_point["longitude"]

            else:
                latitude = geocoded["latitude"]
                longitude = geocoded["longitude"]
                hotel.latitude = latitude
                hotel.longitude = longitude

        return {
            "name": hotel.name,
            "latitude": float(latitude),
            "longitude": float(longitude),
            "day_number": getattr(hotel, "day_number", None),
            "check_in_date": getattr(hotel, "check_in_date", None),
            "check_out_date": getattr(hotel, "check_out_date", None),
        }

    def _destination_point(self, trip: Any) -> dict:
        query = f"{trip.destination}, Sri Lanka"
        geocoded = self.geocoder.geocode(query)

        if not geocoded:
            raise ValueError(f"Could not find coordinates for destination: {trip.destination}")

        return {
            "name": trip.destination,
            "latitude": geocoded["latitude"],
            "longitude": geocoded["longitude"],
            "check_in_date": None,
            "check_out_date": None,
        }

    def _start_location_point(self, trip: Any) -> dict:
        geocoded = self.geocoder.geocode(self._make_start_location_query(trip))

        if not geocoded:
            raise ValueError(
                f"Could not find coordinates for start location: {trip.start_location}"
            )

        return {
            "name": trip.start_location,
            "latitude": geocoded["latitude"],
            "longitude": geocoded["longitude"],
            "check_in_date": None,
            "check_out_date": None,
        }

    def _hotel_for_date(
        self,
        date_value,
        hotel_points: List[dict],
        fallback_point: dict,
    ) -> dict:

        for hotel in hotel_points:
            check_in = hotel.get("check_in_date")
            check_out = hotel.get("check_out_date")

            if check_in and check_out:
                if check_in <= date_value < check_out:
                    return hotel

        if hotel_points:
            return hotel_points[0]

        return fallback_point

    def _hotel_for_day_number(
        self,
        day_number: int,
        hotel_points: List[dict],
    ) -> dict | None:
        for hotel in hotel_points:
            if hotel.get("day_number") == day_number:
                return hotel

        return None

    def _group_places_by_day(
        self,
        place_points: List[dict],
        dates: List,
    ) -> List[List[dict]]:

        grouped = [[] for _ in dates]
        day_loads = [0.0 for _ in dates]

        sorted_places = sorted(
            place_points,
            key=lambda place: place["priority_score"],
            reverse=True,
        )

        for place in sorted_places:
            lightest_day_index = day_loads.index(min(day_loads))

            grouped[lightest_day_index].append(place)
            day_loads[lightest_day_index] += place["visit_duration_hours"]

        return grouped

    def _best_time_slot(self, place: dict) -> int:
        best_hour = self._best_hour(place.get("best_time_to_visit"))

        if best_hour <= 10:
            return 0

        if best_hour <= 15:
            return 1

        return 2

    def _optimize_day_places(
        self,
        start_point: dict,
        places: List[dict],
    ) -> List[dict]:
        ordered_places = []
        current_point = start_point

        slot_map: dict[int, List[dict]] = {
            0: [],
            1: [],
            2: [],
        }

        for place in places:
            slot_map[self._best_time_slot(place)].append(place)

        for slot in [0, 1, 2]:
            remaining_places = sorted(
                slot_map[slot],
                key=lambda place: (-place["priority_score"], place["name"]),
            )

            while remaining_places:
                next_place = min(
                    remaining_places,
                    key=lambda place: (
                        self._distance_km_between(current_point, place),
                        self._best_hour(place.get("best_time_to_visit")),
                        -place["priority_score"],
                    ),
                )

                ordered_places.append(next_place)
                current_point = next_place
                remaining_places.remove(next_place)

        return ordered_places

    def _opening_hours_warnings(
        self,
        place: dict,
        visit_start_datetime: datetime,
    ) -> list[str]:
        warnings = list(place.get("availability_warnings") or [])
        opening_hours = place.get("opening_hours")

        if not opening_hours:
            return warnings

        normalized = opening_hours.strip().lower()

        if normalized in {"24/7", "24 hours"}:
            return warnings

        match = re.search(r"(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})", opening_hours)

        if not match:
            message = "Opening hours are available but could not be automatically validated for this visit time."
            if message not in warnings:
                warnings.append(message)
            return warnings

        start_hour, start_minute, end_hour, end_minute = [int(value) for value in match.groups()]
        visit_time = visit_start_datetime.time()
        open_time = time(hour=start_hour, minute=start_minute)
        close_time = time(hour=end_hour, minute=end_minute)

        if not (open_time <= visit_time <= close_time):
            message = f"Planned visit starts outside listed opening hours ({opening_hours})."
            if message not in warnings:
                warnings.append(message)

        return warnings

    def _combine_polylines(self, segments: List[RouteSegment]) -> List[Coordinate]:
        points = []

        for segment in segments:
            for coordinate in segment.path_coordinates:
                if points:
                    last = points[-1]

                    if (
                        last.latitude == coordinate.latitude
                        and last.longitude == coordinate.longitude
                    ):
                        continue

                points.append(coordinate)

        return points

    def _encode_combined_polyline(self, coordinates: List[Coordinate]) -> str:
        points = [
            {
                "latitude": coordinate.latitude,
                "longitude": coordinate.longitude,
            }
            for coordinate in coordinates
        ]

        return self.router._encode_polyline(points)

    def _schedule_day(
        self,
        trip: Any,
        request: RoutePlanRequest,
        day_number: int,
        date_value,
        places: List[dict],
        start_point: dict,
        return_point: Optional[dict],
    ) -> DayRoutePlan:

        start_time = self._parse_start_time(request.day_start_time)

        if places:
            earliest_best_hour = min(
                self._best_hour(place.get("best_time_to_visit"))
                for place in places
            )

            if earliest_best_hour < start_time.hour:
                start_time = time(hour=earliest_best_hour, minute=0)

        current_datetime = datetime.combine(date_value, start_time)
        day_start_datetime = current_datetime

        current_point = start_point

        stops = []
        segments = []

        total_distance = 0.0
        total_travel_time = 0.0

        for place in places:
            route = self.router.route_between(
                origin=current_point,
                destination=place,
                transport_type=trip.transport_type,
            )

            travel_minutes = route["duration_minutes"]
            travel_distance = route["distance_km"]
            segment_cost = estimate_segment_transport_cost(
                transport_type=trip.transport_type,
                distance_km=travel_distance,
                travelers=getattr(trip, "travelers", 1),
            )

            route_start_time = current_datetime
            arrival_datetime = current_datetime + timedelta(minutes=travel_minutes)

            best_hour = self._best_hour(place.get("best_time_to_visit"))
            preferred_datetime = datetime.combine(
                date_value,
                time(hour=best_hour, minute=0),
            )

            visit_start_datetime = arrival_datetime

            manual_start_time = place.get("manual_start_time")

            if manual_start_time:
                visit_start_datetime = datetime.combine(
                    date_value,
                    self._parse_start_time(manual_start_time),
                )

            elif place.get("best_time_to_visit") not in [None, "flexible"]:
                if arrival_datetime < preferred_datetime:
                    visit_start_datetime = preferred_datetime

            visit_end_datetime = visit_start_datetime + timedelta(
                hours=place["visit_duration_hours"]
            )

            segment = RouteSegment(
                from_name=current_point["name"],
                to_name=place["name"],
                start_time=self._time_to_string(route_start_time),
                end_time=self._time_to_string(arrival_datetime),
                distance_km=travel_distance,
                duration_minutes=travel_minutes,
                transport_cost_lkr=segment_cost,
                encoded_polyline=route["encoded_polyline"],
                path_coordinates=[
                    Coordinate(**coordinate)
                    for coordinate in route["path_coordinates"]
                ],
                instructions=route["instructions"],
            )

            stop = ItineraryStop(
                place_key=place["place_key"],
                name=place["name"],
                category=place["category"],
                date=date_value,
                day_number=day_number,
                arrival_time=self._time_to_string(arrival_datetime),
                start_time=self._time_to_string(visit_start_datetime),
                end_time=self._time_to_string(visit_end_datetime),
                best_time_to_visit=place.get("best_time_to_visit"),
                opening_hours=place.get("opening_hours"),
                availability_warnings=self._opening_hours_warnings(place, visit_start_datetime),
                visit_duration_hours=place["visit_duration_hours"],
                latitude=place["latitude"],
                longitude=place["longitude"],
                travel_time_from_previous_minutes=travel_minutes,
                travel_distance_from_previous_km=travel_distance,
                note="Time adjusted based on preferred visit time.",
            )

            segments.append(segment)
            stops.append(stop)

            total_distance += travel_distance
            total_travel_time += travel_minutes
            

            current_datetime = visit_end_datetime
            current_point = place

        if return_point and places:
            route = self.router.route_between(
                origin=current_point,
                destination=return_point,
                transport_type=trip.transport_type,
            )

            route_start_time = current_datetime
            route_end_time = current_datetime + timedelta(
                minutes=route["duration_minutes"]
            )
            segment_cost = estimate_segment_transport_cost(
                transport_type=trip.transport_type,
                distance_km=route["distance_km"],
                travelers=getattr(trip, "travelers", 1),
            )

            segment = RouteSegment(
                from_name=current_point["name"],
                to_name=return_point["name"],
                start_time=self._time_to_string(route_start_time),
                end_time=self._time_to_string(route_end_time),
                distance_km=route["distance_km"],
                duration_minutes=route["duration_minutes"],
                transport_cost_lkr=segment_cost,
                encoded_polyline=route["encoded_polyline"],
                path_coordinates=[
                    Coordinate(**coordinate)
                    for coordinate in route["path_coordinates"]
                ],
                instructions=route["instructions"],
            )

            segments.append(segment)

            total_distance += route["distance_km"]
            total_travel_time += route["duration_minutes"]
            current_datetime = route_end_time
            current_point = return_point

        day_path_coordinates = self._combine_polylines(segments)
        day_transport_cost = sum(segment.transport_cost_lkr for segment in segments)

        day_encoded_polyline = self._encode_combined_polyline(
            day_path_coordinates
        )

        return DayRoutePlan(
            day_number=day_number,
            date=date_value,
            start_time=self._time_to_string(day_start_datetime),
            end_time=self._time_to_string(current_datetime),
            start_point_name=start_point["name"],
            end_point_name=current_point["name"],
            stops=stops,
            segments=segments,
            day_distance_km=round(total_distance, 2),
            day_travel_time_minutes=round(total_travel_time, 1),
            day_transport_cost_lkr=round(day_transport_cost, 2),
            day_encoded_polyline=day_encoded_polyline,
            day_path_coordinates=day_path_coordinates,
        )

    def generate_route_plan(
        self,
        trip: Any,
        selected_places: List[Any],
        selected_hotels: List[Any],
        request: RoutePlanRequest,
    ) -> RoutePlanResponse:

        dates = self._trip_dates(trip)

        place_points = []
        missing_places = []

        for place in selected_places:
            point = self._point_from_place(place, trip)
            if point is None:
                missing_places.append(getattr(place, "name", "Unknown place"))
                logger.warning(
                    "Selected place could not be geocoded for trip %s: %s",
                    getattr(trip, "id", "unknown"),
                    getattr(place, "name", "Unknown place"),
                )
                continue

            place_points.append(point)

        if not place_points:
            raise ValueError(
                "Could not geocode any of the selected places. "
                "Please check your destination and try selecting places again."
            )

        if missing_places:
            raise ValueError(
                "Some selected places could not be located and were not routed: "
                + ", ".join(missing_places)
                + ". Please remove or re-add them with a valid map location."
            )

        start_location_point = self._start_location_point(trip)

        hotel_points = [
            self._point_from_hotel(hotel, trip)
            for hotel in selected_hotels
        ]

        destination_point = self._destination_point(trip)

        manual_schedule = request.manual_schedule or []
        manual_by_key = {
            item.place_key: item
            for item in manual_schedule
        }

        if manual_by_key:
            ordered_place_points = []

            for item in manual_schedule:
                for place in place_points:
                    if place["place_key"] == item.place_key and place not in ordered_place_points:
                        if item.visit_duration_hours:
                            place["visit_duration_hours"] = float(item.visit_duration_hours)
                        if item.start_time:
                            place["manual_start_time"] = item.start_time
                        ordered_place_points.append(place)
                        break

            for place in place_points:
                if place not in ordered_place_points:
                    ordered_place_points.append(place)

            grouped_places = [[] for _ in dates]

            for place in ordered_place_points:
                manual = manual_by_key.get(place["place_key"])
                day_index = 0

                if manual:
                    day_index = min(max(manual.day_number - 1, 0), len(dates) - 1)

                grouped_places[day_index].append(place)

        else:
            grouped_places = self._group_places_by_day(
                place_points=place_points,
                dates=dates,
            )

        days = []

        total_distance = 0.0
        total_travel_time = 0.0
        total_transport_cost = 0.0

        for index, date_value in enumerate(dates):
            day_number = index + 1
            current_day_hotel = self._hotel_for_day_number(day_number, hotel_points)
            previous_day_hotel = self._hotel_for_day_number(day_number - 1, hotel_points)

            start_point = previous_day_hotel or destination_point

            if index == 0:
                start_point = start_location_point

            return_point = None

            if request.return_to_hotel and current_day_hotel:
                return_point = current_day_hotel

            if request.return_to_start_location and index == len(dates) - 1:
                return_point = start_location_point

            if manual_by_key:
                ordered_places = grouped_places[index]
            else:
                ordered_places = self._optimize_day_places(
                    start_point=start_point,
                    places=grouped_places[index],
                )

            day_plan = self._schedule_day(
                trip=trip,
                request=request,
                day_number=day_number,
                date_value=date_value,
                places=ordered_places,
                start_point=start_point,
                return_point=return_point,
            )

            days.append(day_plan)

            total_distance += day_plan.day_distance_km
            total_travel_time += day_plan.day_travel_time_minutes
            total_transport_cost += day_plan.day_transport_cost_lkr

        all_coordinates = []

        for day in days:
            for coordinate in day.day_path_coordinates:
                all_coordinates.append(coordinate)

        full_encoded_polyline = self._encode_combined_polyline(all_coordinates)

        provider = self.router.provider_label
        summary = (
            f"Final route generated with selected places, selected hotels, trip dates, preferred visit times, and {provider} routing."
            if selected_hotels
            else f"Route plan generated using selected places, trip dates, preferred visit times, and {provider} routing. Hotel stays are selected after route confirmation."
        )

        return RoutePlanResponse(
            trip_id=trip.id,
            destination=trip.destination,
            start_date=trip.start_date,
            end_date=trip.end_date,
            transport_type=trip.transport_type,
            total_distance_km=round(total_distance, 2),
            total_travel_time_minutes=round(total_travel_time, 1),
            total_transport_cost_lkr=round(total_transport_cost, 2),
            full_encoded_polyline=full_encoded_polyline,
            days=days,
            map_provider=provider,
            route_status="draft",
            summary=summary,
        )
