"""The forest data in PostGIS: writing what the sources send, and the one spatial question asked
of it — which stands near a point may be walked into.

Writers replace a table's contents and leave the transaction to the caller, so a failed fetch
halfway through rolls back to the old data instead of leaving half of it. Geometries go in as
GeoJSON and come out a valid MultiPolygon (`ST_Multi(ST_CollectionExtract(ST_MakeValid(…), 3))`):
the services send Polygons and MultiPolygons, and now and then a ring PostGIS calls invalid.
"""

import json
import math
from collections.abc import Iterable
from datetime import datetime

from psycopg import Connection

from grzyby_server.lasy.model import Wydzielenie
from grzyby_server.lasy.sources import Feature


def replace_wydzielenia(conn: Connection, features: Iterable[Feature]) -> int:
    """Replaces every stand with the real ones (area_type D-STAN) among `features`."""
    conn.execute("DELETE FROM wydzielenia")
    rows = [
        (
            # BDL pads the parts of the address with spaces: "01-12-1-03-226   -a   -00".
            "".join(p["adr_for"].split()),
            p["species_cd"],
            p["spec_age"],
            p["site_type"],
            p["forest_fun"],
            p["sub_area"],
            p["a_year"],
            _geojson(feature),
        )
        for feature in features
        if (p := feature["properties"])["area_type"] == "D-STAN"
    ]
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO wydzielenia
            VALUES (%s, %s, %s, %s, %s, %s, %s, ST_Multi(ST_CollectionExtract(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326)), 3)))
            """,
            rows,
        )
    return len(rows)


def replace_obszary(conn: Connection, kind: str, features: Iterable[Feature]) -> int:
    """Replaces the protected areas of one kind ('park_narodowy', 'rezerwat')."""
    conn.execute("DELETE FROM obszary_chronione WHERE kind = %s", (kind,))
    rows = [(kind, feature["properties"]["nazwa"], _geojson(feature)) for feature in features]
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO obszary_chronione (kind, name, geom)
            VALUES (%s, %s, ST_Multi(ST_CollectionExtract(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326)), 3)))
            """,
            rows,
        )
    return len(rows)


def replace_zakazy(conn: Connection, features: Iterable[Feature]) -> int:
    conn.execute("DELETE FROM zakazy_wstepu")
    rows = [
        (
            feature["properties"]["objectid"],
            _strip(feature["properties"]["nazwa_nadl"]),
            feature["properties"]["data_koncowa"],
            _geojson(feature),
        )
        for feature in features
        if feature["geometry"] is not None
    ]
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO zakazy_wstepu
            VALUES (%s, %s, %s, ST_Multi(ST_CollectionExtract(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326)), 3)))
            """,
            rows,
        )
    return len(rows)


def record_fetch(conn: Connection, source: str, at: datetime) -> None:
    conn.execute(
        "INSERT INTO fetches (source, fetched_at) VALUES (%s, %s) ON CONFLICT (source) DO UPDATE SET fetched_at = excluded.fetched_at",
        (source, at),
    )


def fetched_at(conn: Connection, source: str) -> datetime | None:
    row = conn.execute("SELECT fetched_at FROM fetches WHERE source = %s", (source,)).fetchone()
    return row[0] if row else None


def wydzielenia_within(conn: Connection, lat: float, lon: float, radius_m: float) -> list[Wydzielenie]:
    """Stands with any part within `radius_m` of the point, minus those one may not enter:
    reserves (by BDL's own mark, and GDOŚ's areas), national parks and current entry bans.
    Touching such an area is enough to be left out — better one stand too few than a fine."""
    # A box around the point in degrees, so the spatial index narrows the search before the
    # exact distance on the sphere is taken; a little wider than the circle to be safe.
    dlat = radius_m / 110_000 * 1.05
    dlon = radius_m / (111_320 * math.cos(math.radians(lat))) * 1.05
    rows = conn.execute(
        """
        WITH point AS (SELECT ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326) AS g)
        SELECT w.adres_lesny, w.gatunek, w.wiek, w.siedlisko, w.powierzchnia_ha, w.data_year,
               ST_Y(s.p), ST_X(s.p), ST_Distance(s.p::geography, point.g::geography)
        FROM point, wydzielenia w, LATERAL (SELECT ST_PointOnSurface(w.geom) AS p) s
        WHERE w.geom && ST_Expand(point.g, %(dlon)s, %(dlat)s)
          AND ST_DWithin(w.geom::geography, point.g::geography, %(radius)s)
          AND w.funkcja IS DISTINCT FROM 'REZ'
          AND NOT EXISTS (SELECT 1 FROM obszary_chronione o WHERE ST_Intersects(o.geom, w.geom))
          AND NOT EXISTS (SELECT 1 FROM zakazy_wstepu z WHERE ST_Intersects(z.geom, w.geom))
        """,
        {"lat": lat, "lon": lon, "dlat": dlat, "dlon": dlon, "radius": radius_m},
    ).fetchall()
    return [Wydzielenie(*row) for row in rows]


def _geojson(feature: Feature) -> str:
    return json.dumps(feature["geometry"])


def _strip(value: str | None) -> str | None:
    # BDL pads its text fields to a fixed width: "Białowieża                    ".
    return value.strip() if value else value
