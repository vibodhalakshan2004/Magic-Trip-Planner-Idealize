from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.models.trip import Trip
from app.services.trip_access import require_trip_access


class Query:
    def __init__(self, value):
        self.value = value

    def filter(self, *args):
        return self

    def first(self):
        return self.value


class DB:
    def __init__(self, trip, collaboration):
        self.trip = trip
        self.collaboration = collaboration

    def query(self, model):
        return Query(self.trip if model is Trip else self.collaboration)


def test_viewer_can_read_but_cannot_modify_shared_trip():
    owner_id = uuid4()
    viewer_id = uuid4()
    trip = SimpleNamespace(id=uuid4(), user_id=owner_id)
    db = DB(trip, SimpleNamespace(role="viewer"))

    assert require_trip_access(db, trip.id, viewer_id) is trip
    with pytest.raises(HTTPException) as error:
        require_trip_access(db, trip.id, viewer_id, write=True)
    assert error.value.status_code == 403


def test_editor_can_modify_shared_trip():
    trip = SimpleNamespace(id=uuid4(), user_id=uuid4())
    editor_id = uuid4()
    db = DB(trip, SimpleNamespace(role="editor"))

    assert require_trip_access(db, trip.id, editor_id, write=True) is trip
