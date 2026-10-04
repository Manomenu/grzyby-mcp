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

from psycopg import Connection, sql

from grzyby_server.lasy.model import Obszar, ObszarKind, Wydzielenie
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


def replace_obszary(conn: Connection, kind: ObszarKind, features: Iterable[Feature]) -> int:
    """Replaces the protected areas of one kind (a park or a reserve; bans have replace_zakazy)."""
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


# How much the map's outlines are simplified, in degrees (about 13 m north-south, 22 m east-west
# here): invisible at the zooms the widget shows, a fifth off the size.
SHAPE_TOLERANCE = 0.0002

# The outline of `{geom}` as the map widget draws it: simplified, then each ring an encoded
# polyline (Google's format, 5 decimals), grouped by polygon — [[outer, hole, …], …]. About a
# quarter of GeoJSON's size, which keeps an area's stands under what a chatbot passes on to the
# widget (docs/mcp-apps.md). Written into each query, not a SQL function: as a function PostgreSQL
# plans it anew for every row, 100 times slower.
SHAPE = sql.SQL("""
    (SELECT json_agg(parts.rings ORDER BY parts.part)
     FROM (
         SELECT polygon.path[1] AS part,
                json_agg(ST_AsEncodedPolyline(ST_ExteriorRing(ring.geom), 5) ORDER BY ring.path[1]) AS rings
         FROM ST_Dump(ST_SimplifyPreserveTopology({geom}, %(tolerance)s)) AS polygon, ST_DumpRings(polygon.geom) AS ring
         GROUP BY polygon.path[1]
     ) AS parts)
""")


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
    dlat, dlon = _box(lat, radius_m)
    rows = conn.execute(
        sql.SQL("""
        WITH point AS (SELECT ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326) AS g)
        SELECT w.adres_lesny, w.gatunek, w.wiek, w.siedlisko, w.powierzchnia_ha, w.data_year,
               ST_Y(s.p), ST_X(s.p), ST_Distance(s.p::geography, point.g::geography),
               {shape}
        FROM point, wydzielenia w, LATERAL (SELECT ST_PointOnSurface(w.geom) AS p) s
        WHERE w.geom && ST_Expand(point.g, %(dlon)s, %(dlat)s)
          AND ST_DWithin(w.geom::geography, point.g::geography, %(radius)s)
          AND w.funkcja IS DISTINCT FROM 'REZ'
          AND NOT EXISTS (SELECT 1 FROM obszary_chronione o WHERE ST_Intersects(o.geom, w.geom))
          AND NOT EXISTS (SELECT 1 FROM zakazy_wstepu z WHERE ST_Intersects(z.geom, w.geom))
        """).format(shape=SHAPE.format(geom=sql.SQL("w.geom"))),
        {"lat": lat, "lon": lon, "dlat": dlat, "dlon": dlon, "radius": radius_m, "tolerance": SHAPE_TOLERANCE},
    ).fetchall()
    return [Wydzielenie(*row) for row in rows]


def obszary_within(conn: Connection, lat: float, lon: float, radius_m: float) -> list[Obszar]:
    """Parks, reserves and entry bans reaching within `radius_m` of the point — what the map
    greys out, so it is clear why no stand there is offered."""
    dlat, dlon = _box(lat, radius_m)
    rows = conn.execute(
        sql.SQL("""
        WITH point AS (SELECT ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326) AS g),
        areas AS (
            SELECT kind, name, geom FROM obszary_chronione
            UNION ALL
            SELECT %(zakaz)s, 'zakaz wstępu' || coalesce(' do ' || valid_until, ''), geom FROM zakazy_wstepu
        )
        SELECT a.kind, a.name, {shape}
        FROM point, areas a
        WHERE a.geom && ST_Expand(point.g, %(dlon)s, %(dlat)s)
          AND ST_DWithin(a.geom::geography, point.g::geography, %(radius)s)
        ORDER BY a.kind, a.name
        """).format(shape=SHAPE.format(geom=sql.SQL("a.geom"))),
        {
            "lat": lat,
            "lon": lon,
            "dlat": dlat,
            "dlon": dlon,
            "radius": radius_m,
            "tolerance": SHAPE_TOLERANCE,
            "zakaz": ObszarKind.ZAKAZ_WSTEPU.value,
        },
    ).fetchall()
    return [Obszar(ObszarKind(kind), name, shape) for kind, name, shape in rows]


def _box(lat: float, radius_m: float) -> tuple[float, float]:
    """Half the size of a box around a point, in degrees (latitude, longitude), so the spatial
    index narrows the search before the exact distance on the sphere is taken; a little wider
    than the circle to be safe."""
    return radius_m / 110_000 * 1.05, radius_m / (111_320 * math.cos(math.radians(lat))) * 1.05


def _geojson(feature: Feature) -> str:
    return json.dumps(feature["geometry"])


def _strip(value: str | None) -> str | None:
    # BDL pads its text fields to a fixed width: "Białowieża                    ".
    return value.strip() if value else value
