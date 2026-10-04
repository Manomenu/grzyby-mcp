from datetime import date, timedelta

import pytest

from grzyby_server.pogoda.conditions import conditions
from grzyby_server.pogoda.model import Dzien

TODAY = date(2026, 10, 4)


def days(
    rain: dict[int, float] | None = None, temperature: float = 12.0, low: float = 5.0, frost_days_ago: int | None = None
) -> list[Dzien]:
    """Three weeks up to today; `rain` maps days-ago to mm."""
    rain = rain or {}
    return [
        Dzien(TODAY - timedelta(days=k), rain.get(k, 0.0), temperature, -3.0 if k == frost_days_ago else low, 0.2 if k == 0 else 0.1)
        for k in range(21)
    ]


def test_the_windows_are_five_days_and_three_to_fourteen_days_back() -> None:
    w = conditions(days(rain={0: 50, 2: 7, 3: 10, 14: 5, 15: 99}), TODAY)

    assert w is not None
    assert w.opad_5_dni == pytest.approx((50 + 7 + 10) / 5)  # today and the four days before
    assert w.opad_3_14_dni == 10 + 5  # the rain that had time to act; today's and yesterday's not yet
    assert w.temperatura_5_dni == 12
    assert w.wilgotnosc_gleby == 0.2  # today's
    assert w.mroz_dni_temu is None


def test_a_frost_within_a_week_is_counted_in_days() -> None:
    w = conditions(days(frost_days_ago=5), TODAY)

    assert w is not None
    assert w.mroz_dni_temu == 5


def test_missing_days_mean_no_conditions() -> None:
    assert conditions(days()[:10], TODAY) is None
