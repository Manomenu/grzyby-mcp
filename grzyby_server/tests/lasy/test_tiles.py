import threading
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta

import pytest
from psycopg import Connection

from grzyby_server.lasy import sources, store, tiles
from grzyby_server.lasy.model import Tile, tiles_around
from tests.fake_web import FakeWeb, area, forest_services, stand

NOW = datetime(2026, 10, 4, 12, 0, tzinfo=UTC)
LAT, LON = 54.15, 23.02  # inside tile 541_153 (22.95-23.10 E), away from its edges
TILE = Tile(541, 153)


def adresy(conn: Connection) -> list[str]:
    return [a for (a,) in conn.execute("SELECT adres_lesny FROM wydzielenia ORDER BY adres_lesny")]


def test_a_tile_asked_about_comes_in_once(conn: Connection) -> None:
    def reserves(params: Mapping[str, str | int]) -> dict[str, object]:
        return {"features": [area("Rezerwat", LON + 0.02, LAT)] if params["typeNames"] == "GDOS:Rezerwaty" else []}

    web = FakeWeb(forest_services(stands=[stand("01-12-1-03-226   -a   -00", LON, LAT)], protected=reserves))

    assert tiles.ensure(conn, web, [TILE], NOW) == tiles.Ensured([])
    assert tiles.ensure(conn, web, [TILE], NOW) == tiles.Ensured([])

    assert adresy(conn) == ["01-12-1-03-226-a-00"]
    assert conn.execute("SELECT name FROM obszary_chronione").fetchall() == [("Rezerwat",)]
    # One BDL query (RDLP Białystok) and one per GDOŚ layer — and nothing the second time.
    assert web.asked(sources.BDL_STANDS.format(rdlp="Bialystok")) == 1
    assert web.asked(sources.GDOS_WFS) == 2
    assert store.oldest_fetch(conn, [TILE]) == NOW


def test_buffer_zones_of_parks_and_reserves_are_not_kept(conn: Connection) -> None:
    def gdos(params: Mapping[str, str | int]) -> dict[str, object]:
        name = "Wigierski Park Narodowy" if params["typeNames"] == "GDOS:ParkiNarodowe" else "Ptasi Raj"
        return {"features": [area(name, LON, LAT), area(f"{name} - otulina", LON, LAT)]}

    tiles.ensure(conn, FakeWeb(forest_services(protected=gdos)), [TILE], NOW)

    # Both GDOŚ layers carry buffer zones (seen by Gdańsk: "Ptasi Raj - otulina"); picking is
    # allowed there, so neither is kept.
    assert conn.execute("SELECT kind, name FROM obszary_chronione ORDER BY kind").fetchall() == [
        ("park_narodowy", "Wigierski Park Narodowy"),
        ("rezerwat", "Ptasi Raj"),
    ]


def test_a_stand_across_two_tiles_is_kept_once_in_the_tile_of_its_inner_point(conn: Connection) -> None:
    # The square reaches from tile 541_153 into 541_154 (east of 23.10°), mostly in the first.
    edge = stand("edge", 23.0985, LAT)
    web = FakeWeb(forest_services(stands=[edge]))

    tiles.ensure(conn, web, [TILE, Tile(541, 154)], NOW)

    assert conn.execute("SELECT adres_lesny, tile FROM wydzielenia").fetchall() == [("edge", "541_153")]


def test_a_refresh_replaces_a_tiles_stands(conn: Connection) -> None:
    tiles.ensure(conn, FakeWeb(forest_services(stands=[stand("old", LON, LAT)])), [TILE], NOW)

    tiles.load(conn, FakeWeb(forest_services(stands=[stand("new", LON, LAT)])), store.fetched_tiles(conn), NOW + timedelta(days=30))

    assert adresy(conn) == ["new"]
    assert store.oldest_fetch(conn, [TILE]) == NOW + timedelta(days=30)


def test_a_tile_that_fails_keeps_its_data_and_stops_no_other(conn: Connection) -> None:
    tiles.ensure(conn, FakeWeb(forest_services(stands=[stand("old", LON, LAT)])), [TILE], NOW)
    down = FakeWeb(forest_services(stands=OSError("BDL is down")))

    failed = tiles.load(conn, down, [TILE], NOW + timedelta(days=30))

    assert failed == [TILE]
    assert adresy(conn) == ["old"]
    assert store.oldest_fetch(conn, [TILE]) == NOW


def test_the_tiles_of_a_question_are_fetched_in_parallel_and_all_written(conn: Connection) -> None:
    around = tiles_around(54.10, 22.93, 15_000)

    assert tiles.ensure(conn, FakeWeb(forest_services()), around, NOW) == tiles.Ensured([])

    assert set(store.fetched_tiles(conn)) == set(around)


def test_new_tiles_past_the_daily_limit_wait_for_the_next_day(conn: Connection, monkeypatch: pytest.MonkeyPatch) -> None:
    # A day in Poland's calendar: NOW is 14:00 there; 23:00 is the same day, 00:30 the next.
    monkeypatch.setattr(tiles, "DAILY_LIMIT", 2)
    web = FakeWeb(forest_services())
    tiles.ensure(conn, web, [TILE, Tile(541, 154)], NOW)
    asked = len(web.calls)

    refused = tiles.ensure(conn, web, [Tile(541, 155)], NOW + timedelta(hours=9))
    assert len(web.calls) == asked
    next_day = tiles.ensure(conn, web, [Tile(541, 155)], NOW + timedelta(hours=10, minutes=30))

    assert refused == tiles.Ensured([], tiles.Refusal.DAILY_LIMIT)
    assert next_day == tiles.Ensured([])
    assert Tile(541, 155) in store.fetched_tiles(conn)


def test_an_area_is_fetched_whole_or_not_at_all(conn: Connection, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tiles, "DAILY_LIMIT", 2)
    web = FakeWeb(forest_services())

    # Three new tiles do not fit in a limit of two; none is fetched, not two of them.
    assert tiles.ensure(conn, web, [TILE, Tile(541, 154), Tile(541, 155)], NOW).refused == tiles.Refusal.DAILY_LIMIT
    assert web.calls == []


def test_the_monthly_refresh_does_not_count_against_the_daily_limit(conn: Connection, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tiles, "DAILY_LIMIT", 1)
    tiles.ensure(conn, FakeWeb(forest_services()), [TILE], NOW)
    later = NOW + timedelta(days=30)
    tiles.load(conn, FakeWeb(forest_services()), [TILE], later)

    assert tiles.ensure(conn, FakeWeb(forest_services()), [Tile(541, 154)], later + timedelta(hours=1)) == tiles.Ensured([])


def test_a_new_area_waits_while_enough_others_are_being_fetched(conn: Connection, monkeypatch: pytest.MonkeyPatch) -> None:
    busy = threading.BoundedSemaphore(1)
    busy.acquire()
    monkeypatch.setattr(tiles, "_areas", busy)
    web = FakeWeb(forest_services())

    assert tiles.ensure(conn, web, [TILE], NOW) == tiles.Ensured([], tiles.Refusal.BUSY)
    assert web.calls == []
    # Once a slot is free it comes in; an area already known needs no slot at all.
    busy.release()
    assert tiles.ensure(conn, web, [TILE], NOW) == tiles.Ensured([])
    busy.acquire()
    assert tiles.ensure(conn, web, [TILE], NOW) == tiles.Ensured([])
