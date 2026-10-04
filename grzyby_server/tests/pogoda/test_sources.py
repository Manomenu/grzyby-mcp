from datetime import date

from grzyby_server.lasy.model import Tile
from grzyby_server.pogoda import sources
from tests.fake_web import FakeWeb, open_meteo

TODAY = date(2026, 10, 4)


def test_several_tiles_come_in_one_request_at_their_centres() -> None:
    web = FakeWeb({sources.OPEN_METEO: open_meteo(TODAY, rain=12, rain_days_ago=4, soil=0.2)})

    by_tile = sources.fetch_dni(web, [Tile(541, 152), Tile(541, 153)])

    assert web.asked(sources.OPEN_METEO) == 1
    assert web.calls[0][1]["latitude"] == "54.1500,54.1500"
    assert web.calls[0][1]["longitude"] == "22.8750,23.0250"
    days = by_tile[Tile(541, 153)]
    assert len(days) == sources.PAST_DAYS + sources.FORECAST_DAYS
    rainy = next(d for d in days if d.opad)
    assert (rainy.dzien, rainy.opad, rainy.wilgotnosc_gleby) == (date(2026, 9, 30), 12, 0.2)


def test_one_tile_comes_back_as_one_object() -> None:
    by_tile = sources.fetch_dni(FakeWeb({sources.OPEN_METEO: open_meteo(TODAY)}), [Tile(541, 153)])

    assert list(by_tile) == [Tile(541, 153)]


def test_a_day_without_soil_moisture_keeps_the_rest() -> None:
    by_tile = sources.fetch_dni(FakeWeb({sources.OPEN_METEO: open_meteo(TODAY, soil=None)}), [Tile(541, 153)])

    assert all(d.wilgotnosc_gleby is None for d in by_tile[Tile(541, 153)])
