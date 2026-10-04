from collections.abc import Mapping
from datetime import UTC, datetime

from psycopg import Connection

from grzyby_server.miejsca import geocoding
from grzyby_server.miejsca.model import Grzyb, route_url
from grzyby_server.miejsca.search import Query, search
from tests.fake_web import Answer, FakeWeb, area, forest_services, stand

NOW = datetime(2026, 10, 4, 10, 0, tzinfo=UTC)
LAT, LON = 54.10, 22.93
SUWALKI = [{"lat": str(LAT), "lon": str(LON), "display_name": "Suwałki, województwo podlaskie, Polska"}]


def web(nominatim: Answer = SUWALKI, stands: Answer = None, protected: Answer = None, bans: Answer = None) -> FakeWeb:
    """The services a search reaches: Nominatim, and BDL and GDOŚ as the tiles see them."""
    return FakeWeb({geocoding.NOMINATIM: nominatim, **forest_services(stands=stands, protected=protected, bans=bans)})


def test_the_best_stands_around_the_place_come_with_reasons_routes_and_attribution(conn: Connection) -> None:
    stands = [
        stand("pine", LON, LAT + 0.02),
        stand("alder", LON, LAT - 0.02, species_cd="OL", site_type="OL"),
        stand("young", LON + 0.05, LAT, spec_age=8),
    ]

    answer = search(conn, web(stands=stands), Query("Suwałki", [Grzyb.BOROWIK], 15, 3), NOW)

    assert answer.szukano_wokol == "Suwałki, województwo podlaskie, Polska"
    # An alder swamp has no ceps; a young plantation a few. October is still a cep's season.
    assert [m.adres_lesny for m in answer.miejsca] == ["pine", "young"]
    assert answer.grzyby == ["borowik"]
    pine = answer.miejsca[0]
    assert pine.nazwa == "Las sosnowy, 70 lat, 10 ha"
    assert pine.dlaczego.startswith("sosna — bardzo dobrze dla borowika")
    assert "październik: sezon" in pine.dlaczego
    assert pine.trasa == route_url(pine.lat, pine.lon)
    assert answer.uwagi == []
    assert "stan na 2026 r." in answer.zrodla
    assert "sprawdzone 04.10.2026 12:00" in answer.zrodla  # Polish time, not UTC
    # The map has every stand around, including those not picked.
    assert answer.mapa is not None
    assert len(answer.mapa.drzewostany.wiek) == 3


def test_the_map_greys_out_what_one_may_not_enter(conn: Connection) -> None:
    def reserves(params: Mapping[str, str | int]) -> dict[str, object]:
        return {"features": [area("Ostoja bobrów Marycha", LON + 0.01, LAT)] if params["typeNames"] == "GDOS:Rezerwaty" else []}

    answer = search(conn, web(protected=reserves), Query("Suwałki", [Grzyb.BOROWIK], 15, 3), NOW)

    assert answer.mapa is not None
    assert [o.nazwa for o in answer.mapa.obszary] == ["Ostoja bobrów Marycha"]


def test_a_place_outside_the_known_forests_says_so(conn: Connection) -> None:
    answer = search(conn, web(), Query("Suwałki", [Grzyb.BOROWIK], 15, 3), NOW)

    assert answer.miejsca == []
    assert "nie ma lasów państwowych" in answer.uwagi[0]


def test_an_unknown_place_says_so(conn: Connection) -> None:
    answer = search(conn, web(nominatim=[]), Query("Xyzzy", [Grzyb.BOROWIK], 15, 3), NOW)

    assert answer.szukano_wokol is None
    assert answer.uwagi == ["Nie znalazłem w Polsce miejscowości „Xyzzy”."]


def test_a_geocoder_that_is_down_is_a_note_not_an_error(conn: Connection) -> None:
    answer = search(conn, web(nominatim=OSError("down")), Query("Suwałki", [Grzyb.BOROWIK], 15, 3), NOW)

    assert "spróbuj za chwilę" in answer.uwagi[0]


def test_bans_that_could_not_be_checked_are_a_warning(conn: Connection) -> None:
    answer = search(conn, web(stands=[stand("pine", LON, LAT)], bans=OSError("down")), Query("Suwałki", [Grzyb.BOROWIK], 15, 3), NOW)

    assert [m.adres_lesny for m in answer.miejsca] == ["pine"]
    assert any("zakazów wstępu" in uwaga for uwaga in answer.uwagi)


def test_more_spots_can_be_asked_for(conn: Connection) -> None:
    services = web(stands=[stand(f"pine-{i}", LON, LAT + 0.02 * i) for i in range(6)])

    assert len(search(conn, services, Query("Suwałki", [Grzyb.BOROWIK], 15, 3), NOW).miejsca) == 3
    assert len(search(conn, services, Query("Suwałki", [Grzyb.BOROWIK], 15, 5), NOW).miejsca) == 5


def test_a_first_question_brings_the_area_in_and_a_later_one_reads_the_database(conn: Connection) -> None:
    services = web(stands=[stand("pine", LON, LAT)])

    search(conn, services, Query("Suwałki", [Grzyb.BOROWIK], 15, 3), NOW)
    asked = len(services.calls)
    again = search(conn, services, Query("Suwałki", [Grzyb.BOROWIK], 15, 3), NOW)

    assert [m.adres_lesny for m in again.miejsca] == ["pine"]
    assert len(services.calls) == asked  # nothing fetched the second time
    assert "pobrane 04.10.2026" in again.zrodla


def test_an_area_that_could_not_be_fetched_is_a_warning(conn: Connection) -> None:
    answer = search(conn, web(stands=OSError("BDL is down")), Query("Suwałki", [Grzyb.BOROWIK], 15, 3), NOW)

    assert any("nie udało się teraz pobrać" in uwaga.lower() for uwaga in answer.uwagi)


def test_out_of_season_says_when_the_season_comes(conn: Connection) -> None:
    january = datetime(2026, 1, 10, 10, 0, tzinfo=UTC)

    answer = search(conn, web(stands=[stand("pine", LON, LAT)]), Query("Suwałki", [Grzyb.KURKA, Grzyb.RYDZ], 15, 3), january)

    assert answer.miejsca == []
    assert answer.uwagi[0] == "Styczeń to nie sezon na: kurka, rydz. kurka — od: czerwiec; rydz — od: sierpień."


def test_several_mushrooms_have_spots_of_their_own_and_shared_ones(conn: Connection) -> None:
    stands = [stand("pine", LON, LAT + 0.02), stand("birch", LON, LAT - 0.02, species_cd="BRZ", site_type="LMW", spec_age=30)]

    answer = search(conn, web(stands=stands), Query("Suwałki", [Grzyb.BOROWIK, Grzyb.KOZLARZ], 15, 3), NOW)

    # Each mushroom has its own spots, the average its own: here the pine is a cep's, the birch a
    # koźlarz's.
    assert answer.miejsca_na_grzyb[Grzyb.BOROWIK][0].adres_lesny == "pine"
    assert answer.miejsca_na_grzyb[Grzyb.KOZLARZ][0].adres_lesny == "birch"
    assert answer.miejsca[0].dlaczego.startswith("średnio ")
    assert answer.miejsca_na_grzyb[Grzyb.KOZLARZ][0].dlaczego.startswith("brzoza — bardzo dobrze dla koźlarza")
    assert answer.mapa is not None
    assert set(answer.mapa.drzewostany.wynik) == {Grzyb.BOROWIK, Grzyb.KOZLARZ}
