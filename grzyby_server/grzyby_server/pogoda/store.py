"""Weather in the database: one row per tile and day."""

from collections.abc import Iterable, Sequence
from datetime import date, datetime

from psycopg import Connection

from grzyby_server.lasy.model import Tile
from grzyby_server.pogoda.model import Dzien


def replace_weather(conn: Connection, tile: Tile, dni: Sequence[Dzien], now: datetime) -> None:
    conn.execute("DELETE FROM pogoda WHERE tile = %s", (tile.id,))
    with conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO pogoda (tile, dzien, opad, temperatura, temperatura_min, wilgotnosc_gleby) VALUES (%s, %s, %s, %s, %s, %s)",
            [(tile.id, d.dzien, d.opad, d.temperatura, d.temperatura_min, d.wilgotnosc_gleby) for d in dni],
        )
    conn.execute(
        "INSERT INTO weather_fetches (tile, fetched_at) VALUES (%s, %s) ON CONFLICT (tile) DO UPDATE SET fetched_at = excluded.fetched_at",
        (tile.id, now),
    )


def fetched_at(conn: Connection, tiles: Iterable[Tile]) -> dict[Tile, datetime]:
    rows = conn.execute("SELECT tile, fetched_at FROM weather_fetches WHERE tile = ANY(%s)", ([t.id for t in tiles],)).fetchall()
    return {Tile.parse(tile_id): at for tile_id, at in rows}


def days(conn: Connection, tiles: Iterable[Tile], since: date, until: date) -> dict[Tile, list[Dzien]]:
    rows = conn.execute(
        """
        SELECT tile, dzien, opad, temperatura, temperatura_min, wilgotnosc_gleby FROM pogoda
        WHERE tile = ANY(%s) AND dzien BETWEEN %s AND %s ORDER BY tile, dzien
        """,
        ([t.id for t in tiles], since, until),
    ).fetchall()
    found: dict[Tile, list[Dzien]] = {}
    for tile_id, *day in rows:
        found.setdefault(Tile.parse(tile_id), []).append(Dzien(*day))
    return found
