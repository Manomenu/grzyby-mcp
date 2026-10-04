from collections.abc import Mapping
from typing import Any

from grzyby_server.lasy import sources
from tests.fake_web import FakeWeb, ban, stand


def pages(features: list[dict[str, Any]], offset_param: str, size_param: str) -> Any:
    def answer(params: Mapping[str, str | int]) -> dict[str, Any]:
        offset, size = int(params[offset_param]), int(params[size_param])
        return {"features": features[offset : offset + size]}

    return answer


def test_stands_are_fetched_page_by_page_until_a_short_page() -> None:
    features = [stand(f"a-{i}", 23.0, 54.0) for i in range(sources.PAGE + 3)]
    web = FakeWeb({sources.BDL_STANDS: pages(features, "offset", "limit")})

    fetched = list(sources.fetch_wydzielenia(web))

    assert len(fetched) == sources.PAGE + 3
    assert [params["offset"] for _, params in web.calls] == [0, sources.PAGE]


def test_entry_bans_are_fetched_page_by_page_in_wgs84() -> None:
    features = [ban(i, 23.0, 54.0) for i in range(sources.PAGE)]
    web = FakeWeb({sources.BDL_BANS: pages(features, "resultOffset", "resultRecordCount")})

    fetched = list(sources.fetch_zakazy_wstepu(web))

    # A full page means there may be more: one more request finds the empty one.
    assert len(fetched) == sources.PAGE
    assert web.asked(sources.BDL_BANS) == 2
    assert web.calls[0][1]["outSR"] == 4326


def test_protected_areas_are_asked_for_with_the_box_latitude_first() -> None:
    web = FakeWeb({sources.GDOS_WFS: {"features": []}})

    sources.fetch_obszary_chronione(web, "GDOS:Rezerwaty", (22.85, 53.95, 23.35, 54.20))

    params = web.calls[0][1]
    assert params["typeNames"] == "GDOS:Rezerwaty"
    assert params["bbox"] == "53.95,22.85,54.2,23.35,urn:ogc:def:crs:EPSG::4326"
