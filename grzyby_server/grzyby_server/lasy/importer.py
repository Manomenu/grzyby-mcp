"""The monthly refresh of forest data: every tile fetched so far, again (lasy/tiles.py).

Stands change once a year and protected areas hardly ever; the tiles come in on demand, so the
job's work grows with the places people ask about, not with Poland. Entry bans change daily and
are not here — zakazy.py fetches them when they are asked for. Run by the chart's CronJob:

    python -m grzyby_server.lasy.importer               # refresh every fetched tile
    python -m grzyby_server.lasy.importer --benchmark   # fetch the benchmark areas (`just import`)
"""

import logging
import sys
from collections.abc import Sequence
from datetime import UTC, datetime

import psycopg

from grzyby_server import db
from grzyby_server.fetch import get_json
from grzyby_server.lasy import store, tiles
from grzyby_server.lasy.model import tiles_around
from grzyby_server.settings import settings

log = logging.getLogger(__name__)

# Areas far apart, in different RDLPs — pine country by Suwałki (Białystok), the south-east by
# Chełm (Lublin), the coast by Gdańsk, and Ponikiew Wielka in northern Mazovia, where three
# RDLPs meet (Białystok, Olsztyn, Warszawa) — what a laptop and the checks work with, 15 km
# around.
BENCHMARK = {"Suwałki": (54.10, 22.93), "Chełm": (51.14, 23.47), "Gdańsk": (54.35, 18.65), "Ponikiew Wielka": (52.92, 21.30)}
BENCHMARK_RADIUS_M = 15_000


def main(argv: Sequence[str] = sys.argv[1:]) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if list(argv) not in ([], ["--benchmark"]):
        log.error("usage: python -m grzyby_server.lasy.importer [--benchmark]")
        return 2
    with psycopg.connect(settings.database_url) as conn:
        # The job may run before the server has started on a new version; the migrations are
        # idempotent and locked, so either may apply them.
        db.migrate(conn)
        if argv:
            wanted = {tile for lat, lon in BENCHMARK.values() for tile in tiles_around(lat, lon, BENCHMARK_RADIUS_M)}
        else:
            wanted = set(store.fetched_tiles(conn))
        failed = tiles.load(conn, get_json, sorted(wanted, key=lambda tile: tile.id), datetime.now(UTC))
    log.info("tiles: %d, failed: %d", len(wanted), len(failed))
    # A failed tile keeps last month's data; the job shows red in the CronJob's history.
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
