import math
from dataclasses import dataclass
from enum import StrEnum
from typing import Self


@dataclass(frozen=True)
class Wydzielenie:
    """A forest stand near the point asked about — what scoring and the answer need of it."""

    adres_lesny: str
    gatunek: str | None
    wiek: int
    siedlisko: str | None
    powierzchnia_ha: float
    data_year: int
    # A point inside the stand (not its centroid, which a crescent-shaped stand lies outside of):
    # where the map marker and the route go.
    lat: float
    lon: float
    distance_m: float
    # The outline for the map: polygons of rings, each ring an encoded polyline (store.SHAPE).
    shape: list[list[str]]
    tile: str  # the grid tile it belongs to (Tile.id) — where its weather comes from


class ObszarKind(StrEnum):
    """Why an area may not be entered. The values are what the database and the map use."""

    PARK_NARODOWY = "park_narodowy"
    REZERWAT = "rezerwat"
    ZAKAZ_WSTEPU = "zakaz_wstepu"


@dataclass(frozen=True)
class Obszar:
    """An area one may not enter, for the map: a national park, a reserve, an entry ban."""

    kind: ObszarKind
    name: str
    shape: list[list[str]]


# The grid forest data is fetched and refreshed by (lasy/tiles.py): 0.1° of latitude by 0.15° of
# longitude, about 11 by 10 km in Poland — one to three pages of BDL each, and a 15 km circle
# touches about a dozen. store.py assigns stands to tiles in SQL with the same numbers.
TILE_LAT = 0.1
TILE_LON = 0.15


@dataclass(frozen=True)
class Tile:
    row: int
    col: int

    @property
    def id(self) -> str:
        return f"{self.row}_{self.col}"

    @property
    def bbox(self) -> tuple[float, float, float, float]:
        """lon_min, lat_min, lon_max, lat_max."""
        return (self.col * TILE_LON, self.row * TILE_LAT, (self.col + 1) * TILE_LON, (self.row + 1) * TILE_LAT)

    @classmethod
    def parse(cls, tile_id: str) -> Self:
        row, col = tile_id.split("_")
        return cls(int(row), int(col))


def tiles_around(lat: float, lon: float, radius_m: float) -> list[Tile]:
    """The tiles a circle's bounding box touches."""
    dlat = radius_m / 110_000
    dlon = radius_m / (111_320 * math.cos(math.radians(lat)))
    rows = range(math.floor((lat - dlat) / TILE_LAT), math.floor((lat + dlat) / TILE_LAT) + 1)
    cols = range(math.floor((lon - dlon) / TILE_LON), math.floor((lon + dlon) / TILE_LON) + 1)
    return [Tile(row, col) for row in rows for col in cols]
