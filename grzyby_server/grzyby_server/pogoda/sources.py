"""Open-Meteo: daily weather and hourly soil moisture for many points in one request — free
for non-commercial use, CC BY 4.0, no key (docs/dev/rozpoznanie-danych.md)."""

from collections import defaultdict
from collections.abc import Sequence
from datetime import date
from typing import Any, cast

from grzyby_server.fetch import GetJson
from grzyby_server.lasy.model import TILE_LAT, TILE_LON, Tile
from grzyby_server.pogoda.model import Dzien

OPEN_METEO = "https://api.open-meteo.com/v1/forecast"
# Three weeks back for the windows of conditions.py, six days ahead for questions about them.
PAST_DAYS = 21
FORECAST_DAYS = 6


def fetch_dni(get_json: GetJson, tiles: Sequence[Tile]) -> dict[Tile, list[Dzien]]:
    """The days of each tile, at its centre. Days are in Poland's calendar."""
    centres = [(tile.row * TILE_LAT + TILE_LAT / 2, tile.col * TILE_LON + TILE_LON / 2) for tile in tiles]
    answer = get_json(
        OPEN_METEO,
        {
            "latitude": ",".join(f"{lat:.4f}" for lat, _ in centres),
            "longitude": ",".join(f"{lon:.4f}" for _, lon in centres),
            "daily": "precipitation_sum,temperature_2m_mean,temperature_2m_min",
            "hourly": "soil_moisture_3_to_9cm",
            "past_days": PAST_DAYS,
            "forecast_days": FORECAST_DAYS,
            "timezone": "Europe/Warsaw",
        },
    )
    # One point comes back as an object, several as a list, in the order asked.
    points = cast("list[dict[str, Any]]", answer if isinstance(answer, list) else [answer])
    return {tile: _days(point) for tile, point in zip(tiles, points, strict=True)}


def _days(point: dict[str, Any]) -> list[Dzien]:
    daily: dict[str, list[Any]] = point["daily"]
    hourly: dict[str, list[Any]] = point["hourly"]
    soil: defaultdict[str, list[float]] = defaultdict(list)
    for hour, value in zip(hourly["time"], hourly["soil_moisture_3_to_9cm"], strict=True):
        if value is not None:
            soil[str(hour)[:10]].append(value)
    days: list[Dzien] = []
    for k, day in enumerate(daily["time"]):
        rain, mean, low = daily["precipitation_sum"][k], daily["temperature_2m_mean"][k], daily["temperature_2m_min"][k]
        if rain is None or mean is None or low is None:
            continue  # the model has no value for that day yet
        moist = soil.get(str(day))
        days.append(Dzien(date.fromisoformat(str(day)), rain, mean, low, sum(moist) / len(moist) if moist else None))
    return days
