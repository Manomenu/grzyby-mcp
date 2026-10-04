from datetime import UTC, date, datetime, timedelta

from psycopg import Connection

from grzyby_server.lasy.model import Tile
from grzyby_server.pogoda import refresh, sources, store
from tests.fake_web import FakeWeb, open_meteo

NOW = datetime(2026, 10, 4, 10, 0, tzinfo=UTC)
TILES = [Tile(541, 152), Tile(541, 153)]


def web() -> FakeWeb:
    return FakeWeb({sources.OPEN_METEO: open_meteo(date(2026, 10, 4))})


def test_weather_is_fetched_once_and_kept_for_a_while(conn: Connection) -> None:
    services = web()

    assert refresh.ensure(conn, services, TILES, NOW)
    assert refresh.ensure(conn, services, TILES, NOW + refresh.FRESH_FOR - timedelta(minutes=1))

    assert services.asked(sources.OPEN_METEO) == 1
    assert set(store.days(conn, TILES, date(2026, 9, 1), date(2026, 10, 9))) == set(TILES)


def test_stale_weather_is_fetched_again(conn: Connection) -> None:
    refresh.ensure(conn, web(), TILES, NOW)
    services = web()

    refresh.ensure(conn, services, TILES, NOW + refresh.FRESH_FOR)

    assert services.asked(sources.OPEN_METEO) == 1


def test_a_service_that_is_down_keeps_the_old_weather(conn: Connection) -> None:
    refresh.ensure(conn, web(), TILES, NOW)

    assert not refresh.ensure(conn, FakeWeb({sources.OPEN_METEO: OSError("down")}), TILES, NOW + timedelta(days=1))
    assert set(store.days(conn, TILES, date(2026, 9, 1), date(2026, 10, 9))) == set(TILES)
