"""Entry bans, fetched when the tool needs them and kept for 4 hours.

A ban can start any day (fire risk in summer), so the monthly import is too slow for them. The
whole country is a few hundred polygons, so the refresh takes them all and the spatial check
stays in SQL (store.wydzielenia_within).
"""

import logging
from datetime import datetime, timedelta

from psycopg import Connection

from grzyby_server.fetch import GetJson
from grzyby_server.lasy import sources, store

log = logging.getLogger("uvicorn.error")

SOURCE = "bdl_zakazy_wstepu"
FRESH_FOR = timedelta(hours=4)
# Any constant will do; it only has to be the same in every process that refreshes.
REFRESH_LOCK = 0x7A_616B_617A  # "zakaz"


def refresh(conn: Connection, get_json: GetJson, now: datetime) -> datetime | None:
    """Refreshes the bans when older than FRESH_FOR and returns when the stored ones were fetched
    (None: never). A failed fetch keeps the previous bans — the caller tells the user they may be
    out of date rather than failing the whole answer."""
    with conn.transaction():
        # One refresh at a time; whoever waited finds the bans fresh and skips the fetch.
        conn.execute("SELECT pg_advisory_xact_lock(%s)", (REFRESH_LOCK,))
        fetched = store.fetched_at(conn, SOURCE)
        if fetched is not None and now - fetched < FRESH_FOR:
            return fetched
        try:
            count = store.replace_zakazy(conn, sources.fetch_zakazy_wstepu(get_json))
        except (OSError, ValueError, KeyError) as error:
            # OSError covers the network (URLError, timeouts), ValueError a body that is not JSON,
            # KeyError JSON of another shape — in the page or in a ban's fields; replace_zakazy
            # reads them all before it deletes anything.
            log.warning("entry bans not refreshed, keeping those from %s: %r", fetched, error)
            return fetched
        store.record_fetch(conn, SOURCE, now)
    log.info("entry bans refreshed: %d", count)
    return now
