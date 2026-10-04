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
