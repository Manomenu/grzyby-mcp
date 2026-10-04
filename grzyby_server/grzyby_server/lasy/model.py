from dataclasses import dataclass


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
