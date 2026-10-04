"""Forest data on demand: a tile of the grid (model.Tile) comes from BDL and GDOŚ the first time
someone asks about a place near it, and the monthly job refreshes only the tiles fetched so far.

Nothing is imported up front: all of Poland would be 2.6 million subdivisions and hours of
downloading for places nobody asks about. The price is the first question about a new area — a
few seconds while its tiles come in, in parallel; every later one reads the database.
"""

import logging
from collections.abc import Iterable, Sequence
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from itertools import batched

from psycopg import Connection

from grzyby_server.fetch import GetJson
from grzyby_server.lasy import sources, store
from grzyby_server.lasy.model import ObszarKind, Tile
from grzyby_server.lasy.sources import Feature

log = logging.getLogger("uvicorn.error")

# Requests at once: a 15 km circle is about 16 tiles of 2 to 3 s; 8 at a time bring them in
# about 7 s, once per area — still a polite client of public services.
WORKERS = 8
# Any constant will do; with the tile it keys the lock that keeps two writers of one tile apart.
TILE_LOCK = 0x7469_6C65  # "tile"
GDOS_KINDS = {"GDOS:ParkiNarodowe": ObszarKind.PARK_NARODOWY, "GDOS:Rezerwaty": ObszarKind.REZERWAT}


def ensure(conn: Connection, get_json: GetJson, wanted: Iterable[Tile], now: datetime) -> list[Tile]:
    """Fetches those of the tiles (model.tiles_around) not fetched yet. Returns those that could
    not be."""
    have = set(store.fetched_tiles(conn))
    return load(conn, get_json, [tile for tile in wanted if tile not in have], now)


def load(conn: Connection, get_json: GetJson, tiles: Sequence[Tile], now: datetime) -> list[Tile]:
    """Fetches the tiles in parallel and writes each in a transaction of its own, so one that
    fails — a service down for a while — keeps its previous data and stops no other. Returns
    the tiles that failed."""
    failed: list[Tile] = []
    with ThreadPoolExecutor(WORKERS) as pool:
        # A window of tiles at a time: fetched together, then written. Memory holds one window,
        # however many tiles the monthly job has to refresh.
        for window in batched(tiles, WORKERS):
            fetches = {tile: pool.submit(_fetch, get_json, tile) for tile in window}
            for tile, fetch in fetches.items():
                try:
                    stands, areas = fetch.result()
                except (OSError, ValueError, KeyError) as error:
                    # One line, not a traceback: the reason is the service, and a dozen tiles fail at once.
                    log.warning("tile %s not fetched, its previous data stays: %r", tile.id, error)
                    failed.append(tile)
                    continue
                with conn.transaction():
                    # Two questions about one new area fetch it twice; their writes take turns.
                    conn.execute("SELECT pg_advisory_xact_lock(%s, hashtext(%s))", (TILE_LOCK, tile.id))
                    count = store.replace_tile(conn, tile, stands, areas, now)
                log.info("tile %s: %d stands", tile.id, count)
    return failed


def _fetch(get_json: GetJson, tile: Tile) -> tuple[list[Feature], list[tuple[ObszarKind, Feature]]]:
    stands = [feature for rdlp in sources.rdlps_for(tile.bbox) for feature in sources.fetch_wydzielenia(get_json, rdlp, tile.bbox)]
    areas = [
        (kind, feature)
        for layer, kind in GDOS_KINDS.items()
        for feature in sources.fetch_obszary_chronione(get_json, layer, tile.bbox)
        # Both layers carry buffer zones (otulina) as areas of their own — of parks and of reserves
        # alike; picking is allowed there.
        if "otulina" not in feature["properties"]["nazwa"].lower()
    ]
    return stands, areas
