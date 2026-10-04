"""A stand-in for fetch.get_json: answers from what a test gave it, remembers what was asked."""

from collections.abc import Callable, Mapping
from typing import Any

type Answer = Any | Callable[[Mapping[str, str | int]], Any]


class FakeWeb:
    def __init__(self, answers: dict[str, Answer]) -> None:
        # URL → the JSON to return, or a function of the query parameters (for paging), or an
        # exception to raise (a service that is down).
        self.answers = answers
        self.calls: list[tuple[str, dict[str, str | int]]] = []

    def __call__(self, url: str, params: Mapping[str, str | int]) -> Any:
        self.calls.append((url, dict(params)))
        answer = self.answers[url]
        if isinstance(answer, BaseException):
            raise answer
        return answer(params) if callable(answer) else answer

    def asked(self, url: str) -> int:
        return sum(1 for called, _ in self.calls if called == url)


def square(lon: float, lat: float, size: float = 0.002) -> dict[str, Any]:
    """A GeoJSON square with its south-west corner at the point (0.002° ≈ 130 to 220 m)."""
    ring = [[lon, lat], [lon + size, lat], [lon + size, lat + size], [lon, lat + size], [lon, lat]]
    return {"type": "Polygon", "coordinates": [ring]}


def stand(adr_for: str, lon: float, lat: float, **properties: Any) -> dict[str, Any]:
    """A BDL subdivision as the OGC API sends it: a pine stand on fresh mixed forest unless told otherwise."""
    defaults = {
        "adr_for": adr_for,
        "area_type": "D-STAN",
        "species_cd": "SO",
        "spec_age": 70,
        "site_type": "BMŚW",
        "forest_fun": "GOSP",
        "sub_area": 10.0,
        "a_year": 2026,
    }
    return {"type": "Feature", "properties": defaults | properties, "geometry": square(lon, lat)}


def area(nazwa: str, lon: float, lat: float, size: float = 0.01) -> dict[str, Any]:
    """A GDOŚ park or reserve."""
    return {"type": "Feature", "properties": {"nazwa": nazwa}, "geometry": square(lon, lat, size)}


def ban(objectid: int, lon: float, lat: float) -> dict[str, Any]:
    """A BDL entry ban."""
    return {
        "type": "Feature",
        "properties": {"objectid": objectid, "nazwa_nadl": "Suwałki                       ", "data_koncowa": "2026-12-31 00:00:00"},
        "geometry": square(lon, lat, 0.01),
    }


def decode_polyline(encoded: str) -> list[tuple[float, float]]:
    """Google's encoded polyline back to (lat, lon) points — what the map widget does in JS."""
    points: list[tuple[float, float]] = []
    index = lat = lon = 0
    while index < len(encoded):
        deltas: list[int] = []
        for _ in range(2):
            shift = result = 0
            while True:
                byte = ord(encoded[index]) - 63
                index += 1
                result |= (byte & 0x1F) << shift
                shift += 5
                if byte < 0x20:
                    break
            deltas.append(~(result >> 1) if result & 1 else result >> 1)
        lat += deltas[0]
        lon += deltas[1]
        points.append((lat / 1e5, lon / 1e5))
    return points
