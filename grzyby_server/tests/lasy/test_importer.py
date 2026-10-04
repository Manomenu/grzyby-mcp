from collections.abc import Mapping
from datetime import UTC, datetime

import pytest
from psycopg import Connection

from grzyby_server.lasy import importer, sources, store
from tests.fake_web import FakeWeb, area, stand

NOW = datetime(2026, 10, 4, 12, 0, tzinfo=UTC)


def gdos(params: Mapping[str, str | int]) -> dict[str, object]:
    if params["typeNames"] == "GDOS:ParkiNarodowe":
        return {"features": [area("Wigierski Park Narodowy", 23.0, 54.0), area("Wigierski Park Narodowy - otulina", 22.9, 54.0)]}
    return {"features": [area("Ostoja bobrów Marycha", 23.2, 54.1)]}


def web_with(*stands: dict[str, object]) -> FakeWeb:
    return FakeWeb({sources.BDL_STANDS: {"features": list(stands)}, sources.GDOS_WFS: gdos})


def test_the_import_keeps_real_stands_and_parks_without_their_buffer_zone(conn: Connection) -> None:
    web = web_with(stand("01-12-1-03-226   -a   -00", 23.0, 54.0), stand("01-12-1-03-226   -b   -00", 23.0, 54.0, area_type="BAGNO"))

    counts = importer.import_all(conn, web, NOW)

    assert counts == {"wydzielenia": 1, "parki": 1, "rezerwaty": 1}
    # The padding BDL puts into forest addresses is gone.
    assert conn.execute("SELECT adres_lesny FROM wydzielenia").fetchall() == [("01-12-1-03-226-a-00",)]
    assert conn.execute("SELECT kind, name FROM obszary_chronione ORDER BY kind").fetchall() == [
        ("park_narodowy", "Wigierski Park Narodowy"),
        ("rezerwat", "Ostoja bobrów Marycha"),
    ]
    assert store.fetched_at(conn, importer.STANDS) == NOW


def test_a_new_import_replaces_the_previous_one(conn: Connection) -> None:
    importer.import_all(conn, web_with(stand("old", 23.0, 54.0)), NOW)
    importer.import_all(conn, web_with(stand("new", 23.0, 54.0)), NOW)

    assert conn.execute("SELECT adres_lesny FROM wydzielenia").fetchall() == [("new",)]
    assert conn.execute("SELECT count(*) FROM obszary_chronione").fetchone() == (2,)


def test_a_failed_import_leaves_the_previous_data(conn: Connection) -> None:
    importer.import_all(conn, web_with(stand("old", 23.0, 54.0)), NOW)
    broken = FakeWeb({sources.BDL_STANDS: {"features": [stand("new", 23.0, 54.0)]}, sources.GDOS_WFS: OSError("GDOŚ is down")})

    with pytest.raises(OSError, match="GDOŚ is down"):
        importer.import_all(conn, broken, NOW)

    assert conn.execute("SELECT adres_lesny FROM wydzielenia").fetchall() == [("old",)]
