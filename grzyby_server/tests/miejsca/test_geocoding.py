import pytest
from psycopg import Connection

from grzyby_server.miejsca import geocoding
from tests.fake_web import FakeWeb

SUWALKI = [{"lat": "54.0990636", "lon": "22.9279363", "display_name": "Suwałki, województwo podlaskie, Polska"}]


def test_a_place_is_asked_for_once_then_comes_from_the_cache(conn: Connection) -> None:
    web = FakeWeb({geocoding.NOMINATIM: SUWALKI})

    first = geocoding.geocode(conn, web, "Suwałki")
    again = geocoding.geocode(conn, web, "  suwałki ")

    assert first == again == geocoding.Place(54.0990636, 22.9279363, "Suwałki, województwo podlaskie, Polska")
    assert web.asked(geocoding.NOMINATIM) == 1
    assert web.calls[0][1]["countrycodes"] == "pl"


def test_a_name_that_finds_nothing_is_remembered_too(conn: Connection) -> None:
    web = FakeWeb({geocoding.NOMINATIM: []})

    assert geocoding.geocode(conn, web, "Xyzzy") is None
    assert geocoding.geocode(conn, web, "Xyzzy") is None
    assert web.asked(geocoding.NOMINATIM) == 1


def test_callers_of_the_throttle_take_turns_one_interval_apart() -> None:
    now = [100.0]
    slept: list[float] = []

    def sleep(seconds: float) -> None:
        slept.append(seconds)
        now[0] += seconds

    throttle = geocoding.Throttle(1.0, clock=lambda: now[0], sleep=sleep)
    throttle.wait()  # the first goes at once
    now[0] += 0.25
    throttle.wait()  # the next waits out the rest of the second
    now[0] += 5
    throttle.wait()  # after a pause, at once again

    assert slept == [0.75]


def test_a_place_from_the_cache_does_not_wait_for_a_turn(conn: Connection, monkeypatch: pytest.MonkeyPatch) -> None:
    waits: list[None] = []
    monkeypatch.setattr(geocoding.NOMINATIM_TURNS, "wait", lambda: waits.append(None))
    web = FakeWeb({geocoding.NOMINATIM: SUWALKI})

    geocoding.geocode(conn, web, "Suwałki")
    geocoding.geocode(conn, web, "Suwałki")

    assert len(waits) == 1
