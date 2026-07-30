from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.models.budget_estimate import BudgetEstimate
from app.models.route_plan import RoutePlan
from app.models.selected_hotel import SelectedHotel
from app.models.selected_place import SelectedPlace
from app.models.trip import Trip
from app.models.trip_version import TripVersion


def _json_value(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def _row_data(row: Any, *, omit: set[str] | None = None) -> dict[str, Any]:
    omitted = omit or set()
    return {
        attribute.key: _json_value(getattr(row, attribute.key))
        for attribute in inspect(type(row)).column_attrs
        if attribute.key not in omitted
    }


def capture_trip_version(db: Session, trip: Trip, label: str) -> TripVersion:
    latest_route = (
        db.query(RoutePlan)
        .filter(RoutePlan.trip_id == trip.id)
        .order_by(RoutePlan.created_at.desc())
        .first()
    )
    latest_budget = (
        db.query(BudgetEstimate)
        .filter(BudgetEstimate.trip_id == trip.id)
        .order_by(BudgetEstimate.created_at.desc())
        .first()
    )
    snapshot = {
        "trip": _row_data(trip, omit={"id", "user_id", "created_at", "updated_at"}),
        "places": [
            _row_data(row, omit={"id", "trip_id", "created_at"})
            for row in db.query(SelectedPlace).filter(SelectedPlace.trip_id == trip.id).all()
        ],
        "hotels": [
            _row_data(row, omit={"id", "trip_id", "route_plan_id", "created_at"})
            for row in db.query(SelectedHotel).filter(SelectedHotel.trip_id == trip.id).all()
        ],
        "route": _row_data(latest_route, omit={"id", "trip_id", "created_at"}) if latest_route else None,
        "budget": _row_data(latest_budget, omit={"id", "trip_id", "created_at"}) if latest_budget else None,
    }
    next_number = (
        db.query(TripVersion.version_number)
        .filter(TripVersion.trip_id == trip.id)
        .order_by(TripVersion.version_number.desc())
        .limit(1)
        .scalar()
        or 0
    ) + 1
    version = TripVersion(
        trip_id=trip.id,
        user_id=trip.user_id,
        version_number=next_number,
        label=label,
        snapshot=snapshot,
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    return version


def _coerce_dates(model, values: dict[str, Any]) -> dict[str, Any]:
    date_columns = set()
    for column in inspect(model).columns:
        try:
            python_type = column.type.python_type
        except (AttributeError, NotImplementedError):
            continue
        if python_type in {date, datetime}:
            date_columns.add(column.key)
    result = dict(values)
    for key in date_columns:
        value = result.get(key)
        if isinstance(value, str):
            result[key] = datetime.fromisoformat(value) if "T" in value else date.fromisoformat(value)
    return result


def restore_trip_version(db: Session, trip: Trip, version: TripVersion) -> None:
    snapshot = version.snapshot
    for key, value in _coerce_dates(Trip, snapshot.get("trip", {})).items():
        setattr(trip, key, value)

    db.query(SelectedHotel).filter(SelectedHotel.trip_id == trip.id).delete(synchronize_session=False)
    db.query(BudgetEstimate).filter(BudgetEstimate.trip_id == trip.id).delete(synchronize_session=False)
    db.query(RoutePlan).filter(RoutePlan.trip_id == trip.id).delete(synchronize_session=False)
    db.query(SelectedPlace).filter(SelectedPlace.trip_id == trip.id).delete(synchronize_session=False)
    db.flush()

    for values in snapshot.get("places", []):
        db.add(SelectedPlace(trip_id=trip.id, **_coerce_dates(SelectedPlace, values)))

    route = None
    if snapshot.get("route"):
        route = RoutePlan(trip_id=trip.id, **_coerce_dates(RoutePlan, snapshot["route"]))
        db.add(route)
        db.flush()

    for values in snapshot.get("hotels", []):
        db.add(
            SelectedHotel(
                trip_id=trip.id,
                route_plan_id=route.id if route else None,
                **_coerce_dates(SelectedHotel, values),
            )
        )

    if snapshot.get("budget"):
        db.add(BudgetEstimate(trip_id=trip.id, **_coerce_dates(BudgetEstimate, snapshot["budget"])))

    trip.updated_at = datetime.utcnow()
    db.commit()
