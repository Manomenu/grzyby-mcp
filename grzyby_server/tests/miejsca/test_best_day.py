from datetime import UTC, date, datetime

from psycopg import Connection

from grzyby_server.miejsca import geocoding
from grzyby_server.miejsca.best_day import best_day
from grzyby_server.miejsca.model import Grzyb, forecast_text
from grzyby_server.miejsca.search import Query
from tests.fake_web import FakeWeb, forest_services, open_meteo, stand

NOW = datetime(2026, 10, 4, 10, 0, tzinfo=UTC)
LAT, LON = 54.10, 22.93
SUWALKI = [{"lat": str(LAT), "lon": str(LON), "display_name": "Suwałki, województwo podlaskie, Polska"}]


def web(rain_days_ago: int) -> FakeWeb:
    weather = open_meteo(date(2026, 10, 4), rain=30, rain_days_ago=rain_days_ago, soil=0.15)
    return FakeWeb({geocoding.NOMINATIM: SUWALKI, **forest_services(stands=[stand("pine", LON, LAT)], weather=weather)})


def test_the_days_ahead_are_scored_and_the_best_named(conn: Connection) -> None:
    # A downpour yesterday: today it has not acted yet, in a few days it has.
    forecast = best_day(conn, web(rain_days_ago=1), Query("Suwałki", [Grzyb.BOROWIK, Grzyb.PODGRZYBEK], 15), NOW)

    assert [d.za_ile_dni for d in forecast.dni] == [0, 1, 2, 3, 4, 5]
    today, later = forecast.dni[0], max(forecast.dni, key=lambda d: d.ocena)
    assert later.ocena > today.ocena
    assert forecast.najlepszy == later.dzien != date(2026, 10, 4)
    assert set(today.na_grzyb) == {Grzyb.BOROWIK, Grzyb.PODGRZYBEK}
    assert "mm deszczu 3–14 dni wcześniej" in today.pogoda
    text = forecast_text(forecast)
    assert f"**Najlepiej: {later.nazwa}.**" in text
    assert any("prognoza pogody" in uwaga for uwaga in forecast.uwagi)


def test_an_unknown_place_says_so(conn: Connection) -> None:
    services = FakeWeb({geocoding.NOMINATIM: [], **forest_services()})

    forecast = best_day(conn, services, Query("Xyzzy", [Grzyb.BOROWIK], 15), NOW)

    assert forecast.dni == []
    assert forecast.uwagi == ["Nie znalazłem w Polsce miejscowości „Xyzzy”."]
