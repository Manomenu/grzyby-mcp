from collections.abc import Mapping
from typing import Any

import pytest

from grzyby_server.lasy import sources
from grzyby_server.lasy.model import tiles_around
from tests.fake_web import FakeWeb, ban, stand

BOX = (22.95, 54.1, 23.1, 54.2)


def pages(features: list[dict[str, Any]], offset_param: str, size_param: str) -> Any:
    def answer(params: Mapping[str, str | int]) -> dict[str, Any]:
        offset, size = int(params[offset_param]), int(params[size_param])
        return {"features": features[offset : offset + size]}

    return answer


# The benchmark areas (importer.BENCHMARK): 15 km around each asks the collections of its RDLP —
# one deep inside an RDLP, three where they meet.
@pytest.mark.parametrize(
    ("lat", "lon", "rdlps"),
    [
        (54.10, 22.93, {"Bialystok"}),
        (51.14, 23.47, {"Lublin"}),
        (54.35, 18.65, {"Gdansk"}),
        (52.92, 21.30, {"Bialystok", "Olsztyn", "Warszawa"}),
    ],
    ids=["Suwałki", "Chełm", "Gdańsk", "Ponikiew Wielka"],
)
def test_the_tiles_of_a_place_ask_the_collections_of_its_rdlps(lat: float, lon: float, rdlps: set[str]) -> None:
    assert {r for tile in tiles_around(lat, lon, 15_000) for r in sources.rdlps_for(tile.bbox)} == rdlps


def test_a_tile_on_a_border_asks_both_collections() -> None:
    # Between RDLP Białystok and RDLP Olsztyn, around 21.7° E.
    assert set(sources.rdlps_for((21.6, 53.8, 21.75, 53.9))) == {"Bialystok", "Olsztyn"}


def test_stands_of_a_box_are_fetched_page_by_page_until_a_short_page() -> None:
    features = [stand(f"a-{i}", 23.0, 54.15) for i in range(sources.PAGE + 3)]
    web = FakeWeb({sources.BDL_STANDS.format(rdlp="Bialystok"): pages(features, "offset", "limit")})

    fetched = sources.fetch_wydzielenia(web, "Bialystok", BOX)

    assert len(fetched) == sources.PAGE + 3
    assert [params["offset"] for _, params in web.calls] == [0, sources.PAGE]
    assert web.calls[0][1]["bbox"] == "22.95,54.1,23.1,54.2"


def test_protected_areas_are_asked_for_with_the_box_latitude_first() -> None:
    web = FakeWeb({sources.GDOS_WFS: {"features": []}})

    sources.fetch_obszary_chronione(web, "GDOS:Rezerwaty", BOX)

    params = web.calls[0][1]
    assert params["typeNames"] == "GDOS:Rezerwaty"
    assert params["bbox"] == "54.1,22.95,54.2,23.1,urn:ogc:def:crs:EPSG::4326"


def test_entry_bans_are_fetched_page_by_page_in_wgs84() -> None:
    features = [ban(i, 23.0, 54.0) for i in range(sources.PAGE)]
    web = FakeWeb({sources.BDL_BANS: pages(features, "resultOffset", "resultRecordCount")})

    fetched = list(sources.fetch_zakazy_wstepu(web))

    # A full page means there may be more: one more request finds the empty one.
    assert len(fetched) == sources.PAGE
    assert web.asked(sources.BDL_BANS) == 2
    assert web.calls[0][1]["outSR"] == 4326
