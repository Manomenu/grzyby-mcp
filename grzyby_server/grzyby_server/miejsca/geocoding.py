"""A place name to coordinates, through OpenStreetMap's Nominatim, remembered in the database.

Nominatim's usage policy: at most one request a second, an identifying User-Agent (fetch.py),
results cached, and "© OpenStreetMap contributors" in the attribution (search.attribution). The
cache keeps every answer for good — also "not found" — so a name is asked about once.
"""

from dataclasses import dataclass

from psycopg import Connection

from grzyby_server.fetch import GetJson

NOMINATIM = "https://nominatim.openstreetmap.org/search"


@dataclass(frozen=True)
class Place:
    lat: float
    lon: float
    name: str  # Nominatim's full name ("Suwałki, powiat suwalski, …"), shown so a user can spot a wrong village


def geocode(conn: Connection, get_json: GetJson, name: str) -> Place | None:
    """The place in Poland called `name`, or None when there is none. Network errors are
    left to the caller."""
    query = " ".join(name.split()).lower()
    row: tuple[float | None, float | None, str | None] | None = conn.execute(
        "SELECT lat, lon, display_name FROM geocoding_cache WHERE query = %s", (query,)
    ).fetchone()
    if row is None:
        results = get_json(NOMINATIM, {"q": query, "countrycodes": "pl", "format": "jsonv2", "limit": 1, "accept-language": "pl"})
        row = (float(results[0]["lat"]), float(results[0]["lon"]), results[0]["display_name"]) if results else (None, None, None)
        conn.execute(
            "INSERT INTO geocoding_cache (query, lat, lon, display_name) VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING", (query, *row)
        )
    lat, lon, display_name = row
    if lat is None or lon is None or display_name is None:
        return None
    return Place(lat, lon, display_name)
