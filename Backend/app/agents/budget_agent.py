from typing import Any, List

from app.schemas.budget import (
    BudgetAgentResponse,
    BudgetBreakdownItem,
    BudgetCalculateRequest,
)
from app.services.transport_cost import (
    estimate_saved_route_transport_cost,
    estimate_transport_cost,
)


class BudgetAgent:

    def _calculate_days(self, trip: Any) -> int:
        days = (trip.end_date - trip.start_date).days + 1

        if days <= 0:
            days = 1

        return days

    def _calculate_nights(self, trip: Any) -> int:
        nights = (trip.end_date - trip.start_date).days

        if nights <= 0:
            nights = 1

        return nights

    def _round_amount(self, value: float) -> float:
        return round(float(value or 0), 2)

    def _calculate_place_cost(
        self,
        selected_places: List[Any],
        travelers: int,
    ) -> float:
        total = 0

        for place in selected_places:
            cost_per_person = getattr(
                place,
                "estimated_cost_lkr_per_person",
                0
            ) or 0

            total += cost_per_person * travelers

        return total

    def _calculate_hotel_cost(
        self,
        selected_hotels: List[Any],
    ) -> float:
        total = 0

        for hotel in selected_hotels:
            hotel_total = getattr(
                hotel,
                "total_estimated_price_lkr",
                0
            ) or 0

            total += hotel_total

        return total

    def _calculate_auto_buffer_percent(
        self,
        subtotal: float,
    ) -> float:
        if subtotal <= 50000:
            return 15

        if subtotal <= 150000:
            return 10

        return 7

    def _route_segment_names(self, route_plan: Any | None) -> set[str]:
        names: set[str] = set()

        if route_plan is None:
            return names

        for day in list(getattr(route_plan, "days", None) or []):
            segments = day.get("segments", []) if isinstance(day, dict) else getattr(day, "segments", [])
            for segment in segments or []:
                if isinstance(segment, dict):
                    values = [segment.get("from_name"), segment.get("to_name")]
                else:
                    values = [getattr(segment, "from_name", None), getattr(segment, "to_name", None)]
                for value in values:
                    if value:
                        names.add(" ".join(str(value).lower().split()))

        return names

    def _hotel_transfer_cost_not_in_route(
        self,
        selected_hotels: List[Any],
        route_plan: Any | None,
    ) -> float:
        routed_names = self._route_segment_names(route_plan)
        total = 0.0

        for hotel in selected_hotels:
            hotel_name = " ".join(str(getattr(hotel, "name", "")).lower().split())
            if hotel_name and hotel_name in routed_names:
                continue
            total += float(getattr(hotel, "transfer_cost_lkr", 0) or 0)

        return total

    def _get_budget_status(
        self,
        total_cost: float,
        budget_max: float,
    ) -> str:
        if total_cost > budget_max:
            return "over_budget"

        if total_cost >= budget_max * 0.9:
            return "near_limit"

        return "within_budget"

    def _build_warnings(
        self,
        total_cost: float,
        budget_max: float,
        hotel_cost: float,
        transport_cost: float,
        route_distance_km: float | None,
        transport_source: str,
    ) -> List[str]:
        warnings = []

        if total_cost > budget_max:
            warnings.append(
                "The estimated trip cost is higher than the maximum budget."
            )

        if total_cost >= budget_max * 0.9 and total_cost <= budget_max:
            warnings.append(
                "The trip is close to the maximum budget. Keep extra cash for unexpected costs."
            )

        if hotel_cost > budget_max * 0.6:
            warnings.append(
                "Hotel cost takes a large part of the budget."
            )

        if transport_cost > budget_max * 0.3:
            warnings.append(
                "Transport cost is a significant part of the budget."
            )

        if route_distance_km and route_distance_km > 0:
            warnings.append(
                f"Transport uses each saved origin-to-destination route leg. Source: {transport_source}. Real-world fares can still vary."
            )
        else:
            warnings.append(
                "Transport cost is using fallback per-day estimates because no saved route plan is available yet."
            )

        return warnings

    def _build_suggestions(
        self,
        budget_status: str,
    ) -> List[str]:
        if budget_status == "over_budget":
            return [
                "Choose a cheaper hotel or reduce hotel nights.",
                "Use bus, train, or mixed transport instead of taxi if possible.",
                "Reduce paid activities or expensive food stops.",
                "Increase the budget if these choices are important to the user.",
            ]

        if budget_status == "near_limit":
            return [
                "Avoid adding expensive activities after this point.",
                "Check hotel prices again before final booking.",
                "Keep some extra cash for ticket price changes and transport delays.",
            ]

        return [
            "The trip looks safe within the selected budget.",
            "Keep the automatic emergency buffer for price changes, food, tickets, and transport delays.",
        ]

    def calculate_budget(
        self,
        trip: Any,
        selected_places: List[Any],
        selected_hotels: List[Any],
        request: BudgetCalculateRequest,
        route_plan: Any | None = None,
    ) -> BudgetAgentResponse:

        days = self._calculate_days(trip)
        nights = self._calculate_nights(trip)
        travelers = trip.travelers

        selected_places_cost = self._calculate_place_cost(
            selected_places=selected_places,
            travelers=travelers,
        )

        hotel_cost = self._calculate_hotel_cost(
            selected_hotels=selected_hotels,
        )

        food_cost = (
            request.food_cost_per_person_per_day_lkr
            * days
            * travelers
        )

        route_distance_km = None
        route_transport_estimate = None

        if route_plan is not None:
            route_distance_km = getattr(route_plan, "total_distance_km", None)
            route_transport_estimate = estimate_saved_route_transport_cost(
                route_plan=route_plan,
                transport_type=trip.transport_type,
                travelers=travelers,
            )

        hotel_transfer_cost = self._hotel_transfer_cost_not_in_route(
            selected_hotels=selected_hotels,
            route_plan=route_plan,
        )

        explicit_route_cost_lkr = (
            route_transport_estimate.total_lkr
            if route_transport_estimate is not None
            else None
        )

        transport_cost = estimate_transport_cost(
            transport_type=trip.transport_type,
            days=days,
            travelers=travelers,
            route_distance_km=route_distance_km,
            explicit_route_cost_lkr=explicit_route_cost_lkr,
        ) + hotel_transfer_cost
        transport_source = (
            route_transport_estimate.source
            if route_transport_estimate is not None
            else (
                "selected transport fallback based on route distance"
                if route_distance_km
                else "fallback daily estimate because no route is saved"
            )
        )
        if hotel_transfer_cost > 0:
            transport_source += "; unrouted hotel transfer estimate included"

        other_cost = request.shopping_other_cost_lkr

        subtotal = (
            selected_places_cost
            + hotel_cost
            + food_cost
            + transport_cost
            + other_cost
        )

        buffer_percent = self._calculate_auto_buffer_percent(
            subtotal=subtotal,
        )

        buffer_amount = subtotal * (buffer_percent / 100)

        total_estimated_cost = subtotal + buffer_amount

        remaining_budget = trip.budget_max - total_estimated_cost

        over_budget_amount = 0

        if total_estimated_cost > trip.budget_max:
            over_budget_amount = total_estimated_cost - trip.budget_max

        budget_status = self._get_budget_status(
            total_cost=total_estimated_cost,
            budget_max=trip.budget_max,
        )

        breakdown = [
            BudgetBreakdownItem(
                category="selected_places",
                description="Estimated entrance fees and activity costs for selected places.",
                amount_lkr=self._round_amount(selected_places_cost),
            ),
            BudgetBreakdownItem(
                category="hotels",
                description="Total estimated cost of selected hotels.",
                amount_lkr=self._round_amount(hotel_cost),
            ),
            BudgetBreakdownItem(
                category="food",
                description="Estimated food cost based on travelers and trip days.",
                amount_lkr=self._round_amount(food_cost),
            ),
            BudgetBreakdownItem(
                category="transport",
                description=(
                    f"{trip.transport_type.title()} cost calculated "
                    f"{'per saved route leg' if route_distance_km else 'from a conservative daily fallback'}. "
                    f"Public tickets are per person; private vehicle fares are per group. "
                    f"Source: {transport_source}."
                ),
                amount_lkr=self._round_amount(transport_cost),
            ),
            BudgetBreakdownItem(
                category="other",
                description="Shopping, extra activities, and other user-defined costs.",
                amount_lkr=self._round_amount(other_cost),
            ),
            BudgetBreakdownItem(
                category="emergency_buffer",
                description=f"Automatic emergency buffer of {buffer_percent}% based on subtotal.",
                amount_lkr=self._round_amount(buffer_amount),
            ),
        ]

        warnings = self._build_warnings(
            total_cost=total_estimated_cost,
            budget_max=trip.budget_max,
            hotel_cost=hotel_cost,
            transport_cost=transport_cost,
            route_distance_km=route_distance_km,
            transport_source=transport_source,
        )

        suggestions = self._build_suggestions(
            budget_status=budget_status,
        )

        if budget_status == "over_budget":
            summary = (
                "The trip is estimated to exceed the user's maximum budget."
            )

        elif budget_status == "near_limit":
            summary = (
                "The trip is within budget, but it is close to the maximum limit."
            )

        else:
            summary = (
                "The trip is estimated to stay within the user's budget."
            )

        return BudgetAgentResponse(
            trip_id=trip.id,
            destination=trip.destination,
            days=days,
            nights=nights,
            travelers=travelers,
            budget_min_lkr=self._round_amount(trip.budget_min),
            budget_max_lkr=self._round_amount(trip.budget_max),
            selected_places_cost_lkr=self._round_amount(selected_places_cost),
            hotel_cost_lkr=self._round_amount(hotel_cost),
            food_cost_lkr=self._round_amount(food_cost),
            transport_cost_lkr=self._round_amount(transport_cost),
            other_cost_lkr=self._round_amount(other_cost),
            subtotal_lkr=self._round_amount(subtotal),
            buffer_lkr=self._round_amount(buffer_amount),
            total_estimated_cost_lkr=self._round_amount(total_estimated_cost),
            remaining_budget_lkr=self._round_amount(remaining_budget),
            over_budget_amount_lkr=self._round_amount(over_budget_amount),
            budget_status=budget_status,
            breakdown=breakdown,
            warnings=warnings,
            suggestions=suggestions,
            summary=summary,
        )
