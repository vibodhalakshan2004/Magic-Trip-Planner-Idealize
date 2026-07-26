def estimate_segment_transport_cost(
    transport_type: str,
    distance_km: float | None,
    travelers: int,
) -> float:
    transport_type = (transport_type or "mixed").lower()
    distance = float(distance_km or 0)
    travelers = max(int(travelers or 1), 1)

    group_rate_per_km = {
        "car": 90,
        "taxi": 140,
        "mixed": 70,
    }

    per_person_rate_per_km = {
        "bus": 30,
        "train": 24,
        "bike": 18,
        "walking": 0,
    }

    if transport_type in group_rate_per_km:
        return round(group_rate_per_km[transport_type] * distance, 2)

    if transport_type in per_person_rate_per_km:
        return round(per_person_rate_per_km[transport_type] * distance * travelers, 2)

    return round(70 * distance, 2)


def estimate_transport_cost(
    transport_type: str,
    days: int,
    travelers: int,
    route_distance_km: float | None,
    explicit_route_cost_lkr: float | None = None,
) -> float:
    if explicit_route_cost_lkr is not None and explicit_route_cost_lkr > 0:
        return round(float(explicit_route_cost_lkr), 2)

    if route_distance_km and route_distance_km > 0:
        return estimate_segment_transport_cost(
            transport_type=transport_type,
            distance_km=route_distance_km,
            travelers=travelers,
        )

    transport_type = (transport_type or "mixed").lower()
    days = max(int(days or 1), 1)
    travelers = max(int(travelers or 1), 1)

    group_transport_per_day = {
        "car": 8000,
        "taxi": 12000,
        "mixed": 6000,
    }

    per_person_transport_per_day = {
        "bus": 1500,
        "train": 1800,
        "bike": 2500,
        "walking": 500,
    }

    if transport_type in group_transport_per_day:
        return round(group_transport_per_day[transport_type] * days, 2)

    if transport_type in per_person_transport_per_day:
        return round(per_person_transport_per_day[transport_type] * days * travelers, 2)

    return round(6000 * days, 2)
