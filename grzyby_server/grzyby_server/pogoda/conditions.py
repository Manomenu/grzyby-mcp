"""The days before a day, summed up the way the score needs them.

The windows follow what is known: a fruit body takes about five days to develop, so temperature
and recent rain are means over the last five days (Brejon Lamartinière & Hoffman 2025, Boletus
edulis, Bielefeld); rain acts with a delay of days, so the wetting rain is the rain 3 to 14
days back (that window is an estimate).
"""

from collections.abc import Sequence
from datetime import date, timedelta

from grzyby_server.pogoda.model import Dzien, Warunki

FROST = -1.0  # °C at night that harms fruit bodies


def conditions(dni: Sequence[Dzien], day: date) -> Warunki | None:
    """None when the days around `day` are missing."""
    by_day = {d.dzien: d for d in dni}
    last_5 = [by_day.get(day - timedelta(days=k)) for k in range(5)]
    wetting = [by_day.get(day - timedelta(days=k)) for k in range(3, 15)]
    if any(d is None for d in last_5) or any(d is None for d in wetting):
        return None
    last_5_days = [d for d in last_5 if d is not None]
    frost = next((k for k in range(8) if (d := by_day.get(day - timedelta(days=k))) and d.temperatura_min < FROST), None)
    return Warunki(
        temperatura_5_dni=sum(d.temperatura for d in last_5_days) / 5,
        opad_5_dni=sum(d.opad for d in last_5_days) / 5,
        opad_3_14_dni=sum(d.opad for d in wetting if d is not None),
        wilgotnosc_gleby=last_5_days[0].wilgotnosc_gleby,
        mroz_dni_temu=frost,
    )
