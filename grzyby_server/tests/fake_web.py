"""A stand-in for fetch.get_json: answers from what a test gave it, remembers what was asked."""

from collections.abc import Callable, Mapping
from datetime import date, timedelta
from typing import Any

from grzyby_server.lasy import sources
from grzyby_server.pogoda import sources as weather_sources

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
    """A GDOŚ park or reserve; its gid made from the name, so the same area keeps its id."""
    return {"type": "Feature", "properties": {"gid": sum(map(ord, nazwa)), "nazwa": nazwa}, "geometry": square(lon, lat, size)}


def ban(objectid: int, lon: float, lat: float) -> dict[str, Any]:
    """A BDL entry ban."""
    return {
        "type": "Feature",
        "properties": {"objectid": objectid, "nazwa_nadl": "Suwałki                       ", "data_koncowa": "2026-12-31 00:00:00"},
        "geometry": square(lon, lat, 0.01),
    }


def open_meteo(today: date, *, rain: float = 20.0, rain_days_ago: int = 7, temperature: float = 13.0, soil: float | None = 0.24) -> Answer:
    """Open-Meteo's answer for as many points as asked: dry days around one rain of `rain` mm
    `rain_days_ago` days before `today`, the same temperature every day (nights 7 °C colder),
    soil moisture `soil`.
    Days from three weeks back to five ahead, as sources.fetch_dni asks."""

    def answer(params: Mapping[str, str | int]) -> Any:
        days = [today + timedelta(days=k) for k in range(-weather_sources.PAST_DAYS, weather_sources.FORECAST_DAYS)]
        point = {
            "daily": {
                "time": [d.isoformat() for d in days],
                "precipitation_sum": [rain if d == today - timedelta(days=rain_days_ago) else 0.0 for d in days],
                "temperature_2m_mean": [temperature for _ in days],
                "temperature_2m_min": [temperature - 7 for _ in days],
            },
            "hourly": {
                "time": [f"{d.isoformat()}T{h:02d}:00" for d in days for h in (0, 12)],
                "soil_moisture_3_to_9cm": [soil for _ in days for _ in (0, 12)],
            },
        }
        points = len(str(params["latitude"]).split(","))
        return point if points == 1 else [point] * points

    return answer


def forest_services(stands: Answer = None, protected: Answer = None, bans: Answer = None, weather: Answer = None) -> dict[str, Answer]:
    """The outside services as a search sees them (FakeWeb answers): every RDLP collection gives
    `stands` (a list) whatever the box — or raises, when given an exception — GDOŚ the
    `protected` areas for both layers, the ban service `bans`, Open-Meteo the `weather`. Unset:
    nothing anywhere, and a good autumn week."""

    def wrap(answer: Answer) -> Answer:
        return answer if isinstance(answer, BaseException) or callable(answer) else {"features": answer or []}

    answers: dict[str, Answer] = {sources.BDL_STANDS.format(rdlp=rdlp): wrap(stands) for rdlp in sources.RDLP_BBOX}
    answers[sources.GDOS_WFS] = wrap(protected)
    answers[sources.BDL_BANS] = wrap(bans)
    # A good autumn week by default: rain a week ago, 13 °C, damp ground (dated 4.10.2026).
    answers[weather_sources.OPEN_METEO] = weather if weather is not None else open_meteo(date(2026, 10, 4))
    return answers


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
