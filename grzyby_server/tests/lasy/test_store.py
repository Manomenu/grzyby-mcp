from psycopg import Connection

from grzyby_server.lasy import store
from tests.fake_web import area, ban, stand

# The point asked about; 0.01° is about 1.1 km north-south and 0.65 km east-west here.
LAT, LON = 54.10, 22.93


def found(conn: Connection, radius_m: float = 5000) -> list[str]:
    return sorted(w.adres_lesny for w in store.wydzielenia_within(conn, LAT, LON, radius_m))


def test_stands_within_the_radius_are_found_with_a_point_inside_and_its_distance(conn: Connection) -> None:
    store.replace_wydzielenia(conn, [stand("near", LON, LAT + 0.02), stand("far", LON, LAT + 0.2)])

    [near] = store.wydzielenia_within(conn, LAT, LON, 5000)

    assert near.adres_lesny == "near"
    assert LAT + 0.02 < near.lat < LAT + 0.022
    assert LON < near.lon < LON + 0.002
    assert 2200 < near.distance_m < 2500


def test_stands_one_may_not_enter_are_left_out(conn: Connection) -> None:
    store.replace_wydzielenia(
        conn,
        [
            stand("open", LON, LAT),
            stand("reserve-by-bdl", LON + 0.01, LAT, forest_fun="REZ"),
            stand("in-park", LON + 0.02, LAT),
            stand("in-reserve", LON + 0.04, LAT),
            stand("banned", LON + 0.06, LAT),
        ],
    )
    store.replace_obszary(conn, "park_narodowy", [area("Park", LON + 0.019, LAT - 0.001)])
    store.replace_obszary(conn, "rezerwat", [area("Rezerwat", LON + 0.039, LAT - 0.001)])
    store.replace_zakazy(conn, [ban(1, LON + 0.059, LAT - 0.001)])

    assert found(conn) == ["open"]


def test_entry_bans_keep_the_forest_district_without_padding(conn: Connection) -> None:
    store.replace_zakazy(conn, [ban(7, LON, LAT)])

    assert conn.execute("SELECT id, nadlesnictwo, valid_until FROM zakazy_wstepu").fetchall() == [(7, "Suwałki", "2026-12-31 00:00:00")]
