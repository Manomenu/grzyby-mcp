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
    """At most one call per `interval` seconds, across threads: a caller books the next free turn
    and waits for it — outside the lock, so the queue is a list of turns, not of sleeping
    threads. A caller whose turn is more than `max_wait` away gives up at once (TimeoutError):
    it waits holding a database connection, and the pool is small (db.py)."""

    def __init__(
        self,
        interval: float,
        max_wait: float,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._interval, self._max_wait, self._clock, self._sleep = interval, max_wait, clock, sleep
        self._lock = threading.Lock()
        self._next = float("-inf")

    def wait(self) -> None:
        with self._lock:
            now = self._clock()
            turn = max(now, self._next)
            if turn - now > self._max_wait:
                raise TimeoutError(f"the queue is {turn - now:.0f} s long")
            self._next = turn + self._interval
        if turn > now:
            self._sleep(turn - now)


# For the whole server: in-process, which holds while the chart runs one replica. Ten seconds of
# queue is ten places nobody asked about before; beyond that, "spróbuj za chwilę".
NOMINATIM_TURNS = Throttle(1.0, max_wait=10.0)


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
        # Asked by another question while this one waited? (Seen once that one has committed.)
        row = conn.execute("SELECT lat, lon, display_name FROM geocoding_cache WHERE query = %s", (query,)).fetchone()
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
