from datetime import UTC, datetime

from psycopg import Connection

from grzyby_server.lasy import sources, store
from grzyby_server.miejsca import geocoding
from grzyby_server.miejsca.model import route_url
from grzyby_server.miejsca.search import search
from tests.fake_web import Answer, FakeWeb, stand

NOW = datetime(2026, 10, 4, 10, 0, tzinfo=UTC)
LAT, LON = 54.10, 22.93
SUWALKI = [{"lat": str(LAT), "lon": str(LON), "display_name": "Suwałki, województwo podlaskie, Polska"}]


def web(nominatim: Answer = SUWALKI, bans: Answer = None) -> FakeWeb:
    return FakeWeb({geocoding.NOMINATIM: nominatim, sources.BDL_BANS: bans if bans is not None else {"features": []}})


def test_the_best_stands_around_the_place_come_with_reasons_routes_and_attribution(conn: Connection) -> None:
    store.replace_wydzielenia(
        conn,
        [
            stand("pine", LON, LAT + 0.02),
            stand("alder", LON, LAT - 0.02, species_cd="OL", site_type="OL"),
            stand("young", LON + 0.05, LAT, spec_age=8),
        ],
    )

    answer = search(conn, web(), "Suwałki", 15, NOW)

    assert answer.szukano_wokol == "Suwałki, województwo podlaskie, Polska"
    assert [m.adres_lesny for m in answer.miejsca] == ["pine", "alder"]
    pine = answer.miejsca[0]
    assert pine.nazwa == "Las sosnowy, 70 lat, 10 ha"
    assert pine.dlaczego.startswith("sosna — borowik")
    assert pine.trasa == route_url(pine.lat, pine.lon)
    assert answer.uwagi == []
    assert "stan na 2026 r." in answer.zrodla
    assert "sprawdzone 04.10.2026 12:00" in answer.zrodla  # Polish time, not UTC


def test_a_place_outside_the_known_forests_says_so(conn: Connection) -> None:
    answer = search(conn, web(), "Suwałki", 15, NOW)

    assert answer.miejsca == []
    assert "okolice Suwałk i Wigier" in answer.uwagi[0]


def test_an_unknown_place_says_so(conn: Connection) -> None:
    answer = search(conn, web(nominatim=[]), "Xyzzy", 15, NOW)

    assert answer.szukano_wokol is None
    assert answer.uwagi == ["Nie znalazłem w Polsce miejscowości „Xyzzy”."]


def test_a_geocoder_that_is_down_is_a_note_not_an_error(conn: Connection) -> None:
    answer = search(conn, web(nominatim=OSError("down")), "Suwałki", 15, NOW)

    assert "spróbuj za chwilę" in answer.uwagi[0]


def test_bans_that_could_not_be_checked_are_a_warning(conn: Connection) -> None:
    store.replace_wydzielenia(conn, [stand("pine", LON, LAT)])

    answer = search(conn, web(bans=OSError("down")), "Suwałki", 15, NOW)

    assert [m.adres_lesny for m in answer.miejsca] == ["pine"]
    assert any("zakazów wstępu" in uwaga for uwaga in answer.uwagi)
