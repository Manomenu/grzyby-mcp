from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Dzien:
    """One day of weather over one tile."""

    dzien: date
    opad: float  # mm
    temperatura: float  # °C, mean
    temperatura_min: float  # °C
    wilgotnosc_gleby: float | None  # m³/m³ at 3 to 9 cm


@dataclass(frozen=True)
class Warunki:
    """The weather of the days before one day, as the score reads it (conditions.py)."""

    temperatura_5_dni: float  # mean of the last 5 days' means
    opad_5_dni: float  # mean daily rain of the last 5 days
    opad_3_14_dni: float  # rain 3 to 14 days before — the rain that had time to act
    wilgotnosc_gleby: float | None  # the day's own
    mroz_dni_temu: int | None  # days since the last night below -1 °C within a week; None: none
