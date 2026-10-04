"""The public services the forest data comes from, as GeoJSON features in WGS84.

Each function asks for one box (a tile, lasy/tiles.py) and pages through the answer; storing it
is store.py's job.
"""

from collections.abc import Iterator
from typing import Any

from grzyby_server.fetch import GetJson

type Feature = dict[str, Any]
type Bbox = tuple[float, float, float, float]  # lon_min, lat_min, lon_max, lat_max

# BDL publishes the State Forests' stands one collection per RDLP (regional directorate). Their
# bounding boxes, from BDL's own `rdlp` layer (2026), widened by 0.01°, tell which collections a
# box can touch: the real borders are 78 MB, and an extra query that finds nothing takes 0.3 s.
RDLP_BBOX: dict[str, Bbox] = {
    "Bialystok": (21.39, 52.27, 23.96, 54.42),
    "Katowice": (16.90, 49.38, 20.11, 51.20),
    "Krakow": (19.45, 49.17, 21.59, 50.53),
    "Krosno": (21.09, 48.99, 23.54, 50.45),
    "Lublin": (21.39, 50.23, 24.16, 52.42),
    "Lodz": (18.32, 50.88, 20.67, 53.00),
    "Olsztyn": (19.12, 52.69, 21.97, 54.46),
    "Pila": (15.76, 52.57, 17.54, 53.66),
    "Poznan": (15.92, 51.09, 19.13, 52.84),
    "Szczecin": (14.11, 52.25, 16.18, 54.17),
    "Szczecinek": (15.34, 53.28, 17.71, 54.77),
    "Torun": (17.24, 52.43, 19.77, 54.04),
    "Wroclaw": (14.81, 50.09, 17.62, 51.81),
    "Zielona_Gora": (14.58, 51.35, 16.29, 52.42),
    "Gdansk": (17.47, 53.58, 19.73, 54.85),
    "Radom": (19.74, 50.12, 21.88, 52.08),
    "Warszawa": (20.03, 51.60, 22.68, 52.99),
}
BDL_STANDS = "https://ogcapi.bdl.lasy.gov.pl/collections/RDLP_{rdlp}_wydzielenia/items"
GDOS_WFS = "https://sdi.gdos.gov.pl/wfs"
BDL_BANS = "https://mapserver.bdl.lasy.gov.pl/ArcGIS/rest/services/WMS_zakazy_wstepu_do_lasu/MapServer/0/query"

# The largest page BDL's OGC API serves; the ban service allows 2000.
PAGE = 1000


def rdlps_for(bbox: Bbox) -> list[str]:
    """The RDLP collections whose box overlaps `bbox`."""
    lon_min, lat_min, lon_max, lat_max = bbox
    return [rdlp for rdlp, (x0, y0, x1, y1) in RDLP_BBOX.items() if x0 < lon_max and lon_min < x1 and y0 < lat_max and lat_min < y1]


def fetch_wydzielenia(get_json: GetJson, rdlp: str, bbox: Bbox) -> list[Feature]:
    """Every BDL subdivision of one RDLP touching the box — stands, but also bogs, clearings,
    meadows. A tile is one to three pages of 2 to 3 s."""
    features: list[Feature] = []
    while True:
        page = get_json(
            BDL_STANDS.format(rdlp=rdlp), {"f": "json", "bbox": ",".join(map(str, bbox)), "limit": PAGE, "offset": len(features)}
        )
        batch: list[Feature] = page["features"]
        features += batch
        if len(batch) < PAGE:
            return features


def fetch_obszary_chronione(get_json: GetJson, layer: str, bbox: Bbox) -> list[Feature]:
    """One GDOŚ layer (GDOS:ParkiNarodowe, GDOS:Rezerwaty) touching the box: a handful of areas, one request. WFS 2.0
    with an EPSG URN takes the box latitude first."""
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
