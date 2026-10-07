from datetime import UTC, datetime
from typing import Any

import pytest
from psycopg import Connection
from psycopg_pool import ConnectionPool

from grzyby_server.miejsca import geocoding, live
from grzyby_server.miejsca.search import POLAND
from grzyby_server.settings import settings
from tests.fake_web import FakeWeb, area, forest_services, open_meteo, stand

NOW = datetime(2026, 10, 7, 5, 17, tzinfo=UTC)
SUWALKI = [{"lat": "54.10", "lon": "22.93", "display_name": "Suwałki, województwo podlaskie, Polska"}]


def services(stands: list[dict[str, Any]]) -> FakeWeb:
    """The services as they answer on a good day: the town, its forests, the national park next to it."""
    return FakeWeb(
        {
            geocoding.NOMINATIM: SUWALKI,
            **forest_services(
                stands=stands,
                protected=[area("Wigierski Park Narodowy", 23.00, 54.12)],  # ~5 km away, as the real one
                weather=open_meteo(NOW.astimezone(POLAND).date()),
            ),
        }
    )


FORESTS = [stand(f"s{i}", 22.90 + i * 0.004, 54.08 + i * 0.002) for i in range(12)]


def test_services_answering_as_we_read_them_are_no_problem(conn: Connection) -> None:
    assert live.check(conn, services(FORESTS), NOW) == []


def test_a_service_that_changed_is_named(conn: Connection) -> None:
    problems = live.check(conn, services([]), NOW)

    assert any(p.startswith("BDL:") for p in problems)


def test_the_message_fits_discord() -> None:
    text = live.message([f"problem {i}: " + "x" * 100 for i in range(40)])

    assert text.startswith(":x: **grzyby**")
    assert len(text) <= 1900


def test_the_check_leaves_the_database_as_it_found_it(pool: ConnectionPool, database_url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    # What forget() deletes before asking anew must be back afterwards: the check is rolled back.
    with pool.connection() as conn:
        conn.execute("INSERT INTO geocoding_cache (query, lat, lon, display_name) VALUES ('suwałki', 54.1, 22.93, 'Suwałki')")
    told: list[str] = []

    def broken(_conn: Connection, _get_json: object, _now: datetime) -> list[str]:
        return ["BDL: zmiana"]

    def tell(_webhook: str, text: str) -> None:
        told.append(text)

    monkeypatch.setattr(settings, "database_url", database_url)
    monkeypatch.setattr(settings, "discord_webhook", "https://discord.test/hook")
    monkeypatch.setattr(live, "check", broken)
    monkeypatch.setattr(live, "tell_discord", tell)

    try:
        assert live.main() == 1
        assert len(told) == 1
        assert "BDL: zmiana" in told[0]
        with pool.connection() as conn:
            assert conn.execute("SELECT count(*) FROM geocoding_cache WHERE query = 'suwałki'").fetchone() == (1,)
    finally:
        with pool.connection() as conn:
            conn.execute("DELETE FROM geocoding_cache")
