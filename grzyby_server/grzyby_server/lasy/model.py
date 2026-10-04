from dataclasses import dataclass
from enum import StrEnum


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
