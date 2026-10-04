"""Weather fetched when a question needs it and kept for FRESH_FOR — all the tiles of a question
in one request to Open-Meteo."""

import logging
from collections.abc import Sequence
from datetime import datetime, timedelta

from psycopg import Connection

from grzyby_server.fetch import GetJson
from grzyby_server.lasy.model import Tile
from grzyby_server.pogoda import sources, store

log = logging.getLogger("uvicorn.error")

FRESH_FOR = timedelta(hours=3)
# Any constant will do; it keeps two refreshes from writing the same tiles at once.
WEATHER_LOCK = 0x706F_676F  # "pogo"


def ensure(conn: Connection, get_json: GetJson, tiles: Sequence[Tile], now: datetime) -> bool:
    """Refreshes the tiles' weather older than FRESH_FOR. False when Open-Meteo could not be
    reached — the weather already stored, if any, stays."""
    with conn.transaction():
        conn.execute("SELECT pg_advisory_xact_lock(%s)", (WEATHER_LOCK,))
        fetched = store.fetched_at(conn, tiles)
        stale = [t for t in tiles if t not in fetched or now - fetched[t] >= FRESH_FOR]
        if not stale:
            return True
        try:
            by_tile = sources.fetch_dni(get_json, stale)
        except (OSError, ValueError, KeyError, TypeError) as error:
            log.warning("weather not fetched for %d tiles: %r", len(stale), error)
            return False
        for tile, dni in by_tile.items():
            store.replace_weather(conn, tile, dni, now)
    return True
