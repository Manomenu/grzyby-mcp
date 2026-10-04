"""The monthly import: forest stands from BDL, national parks and reserves from GDOŚ.

Run by the chart's CronJob (and `just import` on a laptop):

    python -m grzyby_server.lasy.importer

Stands change once a year and protected areas hardly ever, so once a month is plenty. Entry
bans change daily and are not imported here — zakazy.py fetches them when they are asked for.
"""

import logging
from datetime import UTC, datetime

import psycopg
from psycopg import Connection

from grzyby_server import db
from grzyby_server.fetch import GetJson, get_json
from grzyby_server.lasy import sources, store
from grzyby_server.lasy.model import ObszarKind
from grzyby_server.settings import settings

log = logging.getLogger(__name__)

STANDS = "bdl_wydzielenia"
PROTECTED = "gdos_obszary_chronione"


def import_all(conn: Connection, get_json: GetJson, now: datetime) -> dict[str, int]:
    """Fetches and replaces everything in one transaction: until it commits, the tool goes on
    reading the previous data, and a failure anywhere leaves that data in place."""
    with conn.transaction():
        counts = {
            "wydzielenia": store.replace_wydzielenia(conn, sources.fetch_wydzielenia(get_json)),
            # The park layer has each park's buffer zone (otulina) as a feature of its own; picking
            # is allowed there.
            "parki": store.replace_obszary(
                conn,
                ObszarKind.PARK_NARODOWY,
                [
                    f
                    for f in sources.fetch_obszary_chronione(get_json, "GDOS:ParkiNarodowe")
                    if "otulina" not in f["properties"]["nazwa"].lower()
                ],
            ),
            "rezerwaty": store.replace_obszary(conn, ObszarKind.REZERWAT, sources.fetch_obszary_chronione(get_json, "GDOS:Rezerwaty")),
        }
        store.record_fetch(conn, STANDS, now)
        store.record_fetch(conn, PROTECTED, now)
    return counts


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    with psycopg.connect(settings.database_url) as conn:
        # The job may run before the server has started on a new version; the migrations are
        # idempotent and locked, so either may apply them.
        db.migrate(conn)
        counts = import_all(conn, get_json, datetime.now(UTC))
    log.info("imported %s", ", ".join(f"{name}: {count}" for name, count in counts.items()))


if __name__ == "__main__":
    main()
