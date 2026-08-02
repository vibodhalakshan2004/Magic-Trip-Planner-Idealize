from __future__ import annotations

import math
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from app.services.google_maps import google_maps_service

# National Transport Commission normal-service fare stages effective
# 2026-07-06. The NTC defines an average fare-stage length of 2 km on
# low-country/valley routes and 1.7 km on hill-country routes. Using the
# midpoint keeps this fallback conservative when the exact bus route number
# and its official stage endpoints are unavailable.
NTC_NORMAL_BUS_FARE_EFFECTIVE_DATE = "2026-07-06"
NTC_AVERAGE_STAGE_DISTANCE_KM = 1.85
NTC_NORMAL_FARE_ANCHORS: tuple[tuple[int, float], ...] = (
    (1, 34),
    (2, 44),
    (3, 56),
    (4, 69),
    (5, 82),
    (6, 95),
    (7, 108),
    (8, 115),
    (44, 391),
    (88, 758),
    (132, 1133),
    (176, 1492),
    (220, 1845),
    (264, 2199),
    (308, 2554),
    (350, 2902),
)


@dataclass(frozen=True)
class TransportCostEstimate:
    total_lkr: float
    source: str
    per_person_lkr: float | None = None
    passenger_count: int = 1
    fare_is_live: bool = False


def _interpolate_fare(stage_number: int) -> float:
    stage = max(int(stage_number), 1)

    if stage > NTC_NORMAL_FARE_ANCHORS[-1][0]:
        last_stage, last_fare = NTC_NORMAL_FARE_ANCHORS[-1]
        previous_stage, previous_fare = NTC_NORMAL_FARE_ANCHORS[-2]
        slope = (last_fare - previous_fare) / (last_stage - previous_stage)
        return round(last_fare + ((stage - last_stage) * slope))

    for index, (upper_stage, upper_fare) in enumerate(NTC_NORMAL_FARE_ANCHORS):
        if stage == upper_stage:
            return upper_fare
        if stage < upper_stage:
            lower_stage, lower_fare = NTC_NORMAL_FARE_ANCHORS[index - 1]
            fraction = (stage - lower_stage) / (upper_stage - lower_stage)
            return round(lower_fare + ((upper_fare - lower_fare) * fraction))

    return NTC_NORMAL_FARE_ANCHORS[-1][1]


def estimate_normal_bus_fare_per_person(distance_km: float | None) -> float:
    distance = max(float(distance_km or 0), 0)
    if distance <= 0:
        return 0

    fare_stages = max(math.ceil(distance / NTC_AVERAGE_STAGE_DISTANCE_KM), 1)
    return float(_interpolate_fare(fare_stages))


def estimate_third_class_train_fare_per_person(distance_km: float | None) -> float:
    """Estimate an ordinary third-class ticket using Sri Lanka Railways zones."""
    remaining = max(float(distance_km or 0), 0)
    if remaining <= 0:
        return 0

    total = 0.0
    for zone_length, rate_per_km in (
        (10, 2.60),
        (40, 2.40),
        (50, 1.70),
        (100, 1.40),
        (float("inf"), 1.10),
    ):
        distance_in_zone = min(remaining, zone_length)
        total += distance_in_zone * rate_per_km
        remaining -= distance_in_zone
        if remaining <= 0:
            break

    return float(max(math.ceil(total), 20))


def _live_public_transport_fare(
    transport_type: str,
    origin: dict[str, Any] | None,
    destination: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not origin or not destination:
        return None

    try:
        return google_maps_service.transit_fare(
            origin=origin,
            destination=destination,
            transit_mode="train" if transport_type == "train" else "bus",
        )
    except Exception:  # noqa: BLE001 - provider failures intentionally use the fare fallback
        # Live transit coverage and fare data are incomplete in Sri Lanka.
        # A provider failure must not prevent route or budget generation.
        return None


def estimate_segment_transport_cost_details(
    transport_type: str,
    distance_km: float | None,
    travelers: int,
    origin: dict[str, Any] | None = None,
    destination: dict[str, Any] | None = None,
) -> TransportCostEstimate:
    mode = (transport_type or "mixed").strip().lower()
    mode = {
        "public transport": "bus",
        "public_transport": "bus",
        "walk": "walking",
        "bicycle": "bike",
        "cycling": "bike",
        "motorbike": "motorcycle",
    }.get(mode, mode)
    distance = max(float(distance_km or 0), 0)
    passengers = max(int(travelers or 1), 1)

    if distance <= 0:
        return TransportCostEstimate(
            total_lkr=0,
            source="No transport charge",
            passenger_count=passengers,
        )

    if mode in {"bus", "train"}:
        live = _live_public_transport_fare(mode, origin, destination)
        if live and float(live.get("fare_lkr") or 0) > 0:
            per_person = round(float(live["fare_lkr"]), 2)
            return TransportCostEstimate(
                total_lkr=round(per_person * passengers, 2),
                source=f"Live Google transit {mode} fare",
                per_person_lkr=per_person,
                passenger_count=passengers,
                fare_is_live=True,
            )

        if mode == "bus":
            per_person = estimate_normal_bus_fare_per_person(distance)
            source = (
                "NTC normal-bus fare-stage estimate "
                f"(effective {NTC_NORMAL_BUS_FARE_EFFECTIVE_DATE})"
            )
        else:
            per_person = estimate_third_class_train_fare_per_person(distance)
            source = "Sri Lanka Railways ordinary third-class zone estimate"

        return TransportCostEstimate(
            total_lkr=round(per_person * passengers, 2),
            source=source,
            per_person_lkr=round(per_person, 2),
            passenger_count=passengers,
        )

    if mode == "mixed":
        # Long intercity legs normally use public transport; short local legs
        # use one tuk-tuk/local vehicle for the group. This avoids pricing the
        # entire intercity journey as a private taxi.
        if distance >= 25:
            live = _live_public_transport_fare("bus", origin, destination)
            if live and float(live.get("fare_lkr") or 0) > 0:
                per_person = round(float(live["fare_lkr"]), 2)
                return TransportCostEstimate(
                    total_lkr=round(per_person * passengers, 2),
                    source="Mixed mode: live intercity public-bus fare",
                    per_person_lkr=per_person,
                    passenger_count=passengers,
                    fare_is_live=True,
                )

            per_person = estimate_normal_bus_fare_per_person(distance)
            return TransportCostEstimate(
                total_lkr=round(per_person * passengers, 2),
                source=(
                    "Mixed mode: NTC intercity bus fare-stage estimate "
                    f"(effective {NTC_NORMAL_BUS_FARE_EFFECTIVE_DATE})"
                ),
                per_person_lkr=round(per_person, 2),
                passenger_count=passengers,
            )

        return TransportCostEstimate(
            total_lkr=round(max(distance * 100, 150), 2),
            source="Mixed mode: local tuk-tuk/group transfer estimate",
            passenger_count=passengers,
        )

    group_rate_per_km = {
        "car": 80,
        "taxi": 130,
        "motorcycle": 35,
    }

    if mode in group_rate_per_km:
        labels = {
            "car": "Private car group operating-cost estimate",
            "taxi": "Taxi group fare estimate",
            "motorcycle": "Motorcycle operating-cost estimate",
        }
        return TransportCostEstimate(
            total_lkr=round(group_rate_per_km[mode] * distance, 2),
            source=labels[mode],
            passenger_count=passengers,
        )

    if mode in {"bike", "walking"}:
        return TransportCostEstimate(
            total_lkr=0,
            source="No ticket or vehicle fare",
            passenger_count=passengers,
        )

    return estimate_segment_transport_cost_details(
        transport_type="mixed",
        distance_km=distance,
        travelers=passengers,
        origin=origin,
        destination=destination,
    )


def estimate_segment_transport_cost(
    transport_type: str,
    distance_km: float | None,
    travelers: int,
    origin: dict[str, Any] | None = None,
    destination: dict[str, Any] | None = None,
) -> float:
    return estimate_segment_transport_cost_details(
        transport_type=transport_type,
        distance_km=distance_km,
        travelers=travelers,
        origin=origin,
        destination=destination,
    ).total_lkr


def _item_value(item: Any, key: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


def _segment_endpoints(segment: Any) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    coordinates = list(_item_value(segment, "path_coordinates", []) or [])
    if len(coordinates) < 2:
        return None, None

    first = coordinates[0]
    last = coordinates[-1]
    origin = {
        "name": _item_value(segment, "from_name", "Origin"),
        "latitude": float(_item_value(first, "latitude")),
        "longitude": float(_item_value(first, "longitude")),
    }
    destination = {
        "name": _item_value(segment, "to_name", "Destination"),
        "latitude": float(_item_value(last, "latitude")),
        "longitude": float(_item_value(last, "longitude")),
    }
    return origin, destination


def reprice_saved_route_transport(
    route_plan: Any,
    transport_type: str,
    travelers: int,
) -> tuple[list[Any], TransportCostEstimate] | None:
    days = deepcopy(list(_item_value(route_plan, "days", []) or []))
    total = 0.0
    sources: set[str] = set()
    fare_is_live = False
    segment_count = 0

    for day in days:
        day_total = 0.0
        for segment in list(_item_value(day, "segments", []) or []):
            distance = float(_item_value(segment, "distance_km", 0) or 0)
            origin, destination = _segment_endpoints(segment)
            estimate = estimate_segment_transport_cost_details(
                transport_type=transport_type,
                distance_km=distance,
                travelers=travelers,
                origin=origin,
                destination=destination,
            )
            total += estimate.total_lkr
            day_total += estimate.total_lkr
            sources.add(estimate.source)
            fare_is_live = fare_is_live or estimate.fare_is_live
            segment_count += 1
            if isinstance(segment, dict):
                segment["transport_cost_lkr"] = estimate.total_lkr
                segment["transport_cost_source"] = estimate.source
                segment["fare_per_person_lkr"] = estimate.per_person_lkr
                segment["passenger_count"] = estimate.passenger_count
                segment["fare_is_live"] = estimate.fare_is_live

        if isinstance(day, dict):
            day["day_transport_cost_lkr"] = round(day_total, 2)

    if segment_count == 0:
        return None

    if len(sources) == 1:
        source = next(iter(sources))
    elif fare_is_live:
        source = "Live transit fares where available, with Sri Lankan fare-table estimates for remaining legs"
    else:
        source = "Sri Lankan segment-by-segment public and private transport estimates"

    return (
        days,
        TransportCostEstimate(
            total_lkr=round(total, 2),
            source=source,
            passenger_count=max(int(travelers or 1), 1),
            fare_is_live=fare_is_live,
        ),
    )


def estimate_saved_route_transport_cost(
    route_plan: Any,
    transport_type: str,
    travelers: int,
) -> TransportCostEstimate | None:
    repriced = reprice_saved_route_transport(
        route_plan=route_plan,
        transport_type=transport_type,
        travelers=travelers,
    )
    return repriced[1] if repriced is not None else None


def estimate_transport_cost(
    transport_type: str,
    days: int,
    travelers: int,
    route_distance_km: float | None,
    explicit_route_cost_lkr: float | None = None,
) -> float:
    if explicit_route_cost_lkr is not None and explicit_route_cost_lkr >= 0:
        return round(float(explicit_route_cost_lkr), 2)

    if route_distance_km and route_distance_km > 0:
        return estimate_segment_transport_cost(
            transport_type=transport_type,
            distance_km=route_distance_km,
            travelers=travelers,
        )

    mode = (transport_type or "mixed").strip().lower()
    trip_days = max(int(days or 1), 1)
    passengers = max(int(travelers or 1), 1)

    group_transport_per_day = {
        "car": 5500,
        "taxi": 8000,
        "motorcycle": 2000,
        "mixed": 1500,
    }
    per_person_transport_per_day = {
        "bus": 400,
        "public_transport": 400,
        "train": 500,
    }

    if mode in group_transport_per_day:
        return round(group_transport_per_day[mode] * trip_days, 2)
    if mode in per_person_transport_per_day:
        return round(per_person_transport_per_day[mode] * trip_days * passengers, 2)
    if mode in {"bike", "bicycle", "walking", "walk"}:
        return 0

    return round(group_transport_per_day["mixed"] * trip_days, 2)
