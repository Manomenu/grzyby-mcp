"""The public services the forest data comes from, as GeoJSON features in WGS84.

Each function pages through its service and yields features; storing them is store.py's job.
"""

from collections.abc import Iterator
from typing import Any

from grzyby_server.fetch import GetJson

type Feature = dict[str, Any]

# The pilot area: Suwałki and Wigry (lon_min, lat_min, lon_max, lat_max). Growing beyond it means
# a bigger box here and, outside RDLP Białystok, the other RDLP collections of BDL.
PILOT_BBOX = (22.85, 53.95, 23.35, 54.20)

BDL_STANDS = "https://ogcapi.bdl.lasy.gov.pl/collections/RDLP_Bialystok_wydzielenia/items"
GDOS_WFS = "https://sdi.gdos.gov.pl/wfs"
BDL_BANS = "https://mapserver.bdl.lasy.gov.pl/ArcGIS/rest/services/WMS_zakazy_wstepu_do_lasu/MapServer/0/query"

# The largest page BDL's OGC API serves; the ban service allows 2000.
PAGE = 1000


def fetch_wydzielenia(get_json: GetJson, bbox: tuple[float, float, float, float] = PILOT_BBOX) -> Iterator[Feature]:
    """Every BDL subdivision (stands, but also bogs, clearings, meadows) touching the box."""
    offset = 0
    while True:
        page = get_json(BDL_STANDS, {"f": "json", "bbox": ",".join(map(str, bbox)), "limit": PAGE, "offset": offset})
        features: list[Feature] = page["features"]
        yield from features
        if len(features) < PAGE:
            return
        offset += PAGE


def fetch_obszary_chronione(get_json: GetJson, layer: str, bbox: tuple[float, float, float, float] = PILOT_BBOX) -> list[Feature]:
    """One GDOŚ layer (GDOS:ParkiNarodowe, GDOS:Rezerwaty) within the box. A handful of features,
    so one request. WFS 2.0 with an EPSG URN takes the box latitude first."""
    lon_min, lat_min, lon_max, lat_max = bbox
    page = get_json(
        GDOS_WFS,
        {
            "service": "WFS",
            "version": "2.0.0",
            "request": "GetFeature",
            "typeNames": layer,
            "srsName": "EPSG:4326",
            "bbox": f"{lat_min},{lon_min},{lat_max},{lon_max},urn:ogc:def:crs:EPSG::4326",
            "outputFormat": "application/json",
        },
    )
    features: list[Feature] = page["features"]
    return features


def fetch_zakazy_wstepu(get_json: GetJson) -> Iterator[Feature]:
    """Every current entry ban in the country (a few hundred; 1.6 MB in October 2026)."""
    offset = 0
    while True:
        page = get_json(
            BDL_BANS,
            {
                "where": "1=1",
                "outFields": "objectid,nazwa_nadl,data_koncowa",
                "outSR": 4326,
                "orderByFields": "objectid",
                "resultOffset": offset,
                "resultRecordCount": PAGE,
                "f": "geojson",
            },
        )
        features: list[Feature] = page["features"]
        yield from features
        if len(features) < PAGE:
            return
        offset += PAGE
