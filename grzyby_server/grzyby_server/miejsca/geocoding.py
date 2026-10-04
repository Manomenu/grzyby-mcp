"""A place name to coordinates, through OpenStreetMap's Nominatim, remembered in the database.

Nominatim's usage policy: at most one request a second (NOMINATIM_TURNS), an identifying
User-Agent (fetch.py), results cached, and "© OpenStreetMap contributors" in the attribution
(search.attribution). The cache keeps every answer for good — also "not found" — so a name is
asked about once.
"""

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

from psycopg import Connection

from grzyby_server.fetch import GetJson

NOMINATIM = "https://nominatim.openstreetmap.org/search"


class Throttle:
    """At most one call per `interval` seconds, across threads: a caller waits for its turn."""

    def __init__(self, interval: float, clock: Callable[[], float] = time.monotonic, sleep: Callable[[float], None] = time.sleep) -> None:
        self._interval, self._clock, self._sleep = interval, clock, sleep
        self._lock = threading.Lock()
        self._last: float | None = None

    def wait(self) -> None:
        # The lock is held while sleeping, so callers queue up one interval apart.
        with self._lock:
            if self._last is not None and (left := self._last + self._interval - self._clock()) > 0:
                self._sleep(left)
            self._last = self._clock()


# For the whole server: in-process, which holds while the chart runs one replica.
NOMINATIM_TURNS = Throttle(1.0)


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
        NOMINATIM_TURNS.wait()
        results = get_json(NOMINATIM, {"q": query, "countrycodes": "pl", "format": "jsonv2", "limit": 1, "accept-language": "pl"})
        row = (float(results[0]["lat"]), float(results[0]["lon"]), results[0]["display_name"]) if results else (None, None, None)
        conn.execute(
            "INSERT INTO geocoding_cache (query, lat, lon, display_name) VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING", (query, *row)
        )
    lat, lon, display_name = row
    if lat is None or lon is None or display_name is None:
        return None
    return Place(lat, lon, display_name)
