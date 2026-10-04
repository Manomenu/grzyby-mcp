"""How promising a stand is for the mushrooms asked about, and why — a plain formula, no AI.

For each mushroom the score is the product of its factors from grzyby.py — trees, site, age,
month — and of the weather over the stand's tile (weather_factor), times two minor ones of the
stand itself, size and distance. One zero rules a stand out for that mushroom. Asked about
several, a stand has a score for each and their average — the map shows either, and each has
its own best spots.
"""

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from grzyby_server.lasy.model import Wydzielenie
from grzyby_server.miejsca import grzyby
from grzyby_server.miejsca.model import Grzyb, Miesiac, ProfilGrzyba
from grzyby_server.pogoda.model import Warunki

MIN_SPACING_M = 1000  # the spots offered should be different walks, not neighbouring stands

# The weather factor (weather_factor). Measured, for the borowik near Bielefeld (Brejon
# Lamartinière & Hoffman 2025): the response to the 5-day mean temperature is quadratic around an
# optimum (grzyby.py), most fruiting between 7 and 19 °C; above 17.5 °C with under 1 mm of rain a
# day there was none at all; below that, fruit bodies came even without rain. Estimates: the
# rest of the numbers here.
TEMPERATURE_SPAN = 9.0  # °C from the optimum to a factor of 0; 6 °C off still gives ~0.55
HOT = 17.5  # °C, the 5-day mean above which a dry spell stops fruiting (measured)
DRY = 1.0  # mm a day, the 5-day mean below which it counts as dry (measured)
SOAKING = 25.0  # mm of rain 3 to 14 days back that counts as the ground well soaked
SOIL_DRY, SOIL_WET = 0.12, 0.28  # m³/m³ at 3 to 9 cm, Open-Meteo's model
DRY_FLOOR = 0.3  # what dryness leaves when it is not also hot: fruiting slows, does not stop
FROST_RECENT, FROST_WEEK = 0.2, 0.6  # after frost 0 to 3 days ago, 4 to 7 days ago


@dataclass(frozen=True)
class Score:
    wydzielenie: Wydzielenie
    per_grzyb: dict[Grzyb, float]
    name: str
    facts: list[str]  # the stand in words: trees, site, age — the same for every mushroom
    reasons: dict[Grzyb, list[str]]  # why it scores as it does for each mushroom

    @property
    def points(self) -> float:
        """The average over the mushrooms asked about — how the map's "all" view and its spots
        rank stands; for one mushroom, its own score."""
        return sum(self.per_grzyb.values()) / len(self.per_grzyb)


def score(w: Wydzielenie, wanted: Sequence[Grzyb], month: Miesiac, radius_m: float, warunki: Warunki | None) -> Score:
    """`wanted` is not empty; `warunki` is the weather over the stand's tile, None when unknown
    (the score is then left without it)."""
    tree = species(w.gatunek) or ""
    tree_name, adjective = grzyby.DRZEWA.get(tree, grzyby.INNE_DRZEWO)
    group, site_name = grzyby.SIEDLISKA.get(w.siedlisko or "", (None, "siedlisko nieznane"))
    age_class = age_class_of(w.wiek)
    age_name = f"{grzyby.KLASY_WIEKU[age_class][1]} ({age_text(w.wiek)})"
    # Minor factors, no sentence of their own: a bigger stand is more forest to walk, a nearer one
    # a shorter drive. Neither can take more than a fifth / a third off.
    size = 0.8 + 0.2 * min(1.0, w.powierzchnia_ha / 5)
    nearness = 1 - 0.3 * min(1.0, w.distance_m / radius_m)

    def factors(profile: ProfilGrzyba) -> tuple[float, float, float, float, float]:
        site = profile.siedliska.get(group, 0) if group else grzyby.NIEZNANE_SIEDLISKO
        weather = weather_factor(profile, warunki)[0] if warunki else 1.0
        return profile.drzewa.get(tree, 0), site, profile.wiek[age_class], profile.sezon.get(month, 0), weather

    def reasons(profile: ProfilGrzyba) -> list[str]:
        tree_f, site_f, age_f, _season, _weather = factors(profile)  # season and weather say their own words
        return [
            f"{tree_name} — {opinion(tree_f)} dla {profile.dopelniacz}",
            f"{site_name} — {opinion(site_f)}",
            f"{age_name} — {opinion(age_f)}",
            f"{month.nazwa}: {season_text(profile, month)}",
            weather_factor(profile, warunki)[1] if warunki else "pogoda: brak danych, ocena bez niej",
        ]

    return Score(
        wydzielenie=w,
        per_grzyb={g: math.prod(factors(grzyby.PROFILE[g])) * size * nearness for g in wanted},
        name=f"Las {adjective}, {age_text(w.wiek)}, {w.powierzchnia_ha:g} ha".replace(".", ","),
        facts=[tree_name, site_name, age_name],
        reasons={g: reasons(grzyby.PROFILE[g]) for g in wanted},
    )


def pick(scores: list[Score], count: int = 3, by: Callable[[Score], float] = lambda s: s.points) -> list[Score]:
    """The best `count` by `by` (the average, or one mushroom's score) above zero, each at least
    MIN_SPACING_M from those before it."""
    picked: list[Score] = []
    for candidate in sorted(scores, key=by, reverse=True):
        if by(candidate) <= 0 or len(picked) == count:
            break
        if all(distance_m(candidate.wydzielenie, p.wydzielenie) >= MIN_SPACING_M for p in picked):
            picked.append(candidate)
    return picked


def weather_factor(profile: ProfilGrzyba, w: Warunki) -> tuple[float, str]:
    """The weather of the days before, as a factor for one mushroom and a sentence."""
    temperature = max(0.0, 1 - ((w.temperatura_5_dni - profile.temperatura) / TEMPERATURE_SPAN) ** 2)
    hot_and_dry = w.temperatura_5_dni > HOT and w.opad_5_dni < DRY
    soil = soil_wetness(w)
    moisture = DRY_FLOOR + (1 - DRY_FLOOR) * wetness(w)
    frost = 1.0 if w.mroz_dni_temu is None else FROST_RECENT if w.mroz_dni_temu <= 3 else FROST_WEEK
    factor = 0.0 if hot_and_dry else temperature * moisture * frost

    ground = "" if soil is None else ", gleba " + ("mokra" if soil >= 0.7 else "wilgotna" if soil >= 0.35 else "sucha")
    words = [f"pogoda: {w.opad_3_14_dni:.0f} mm deszczu 3–14 dni temu{ground}, średnio {w.temperatura_5_dni:.0f} °C"]
    if hot_and_dry:
        words.append("za gorąco i za sucho")
    if w.mroz_dni_temu is not None:
        words.append(f"przymrozek {w.mroz_dni_temu} dni temu" if w.mroz_dni_temu else "przymrozek dziś")
    return factor, ", ".join(words) + f" — {opinion(factor) if factor > 0 else 'teraz nie wyrośnie'}"


def wetness(w: Warunki) -> float:
    """How wet the ground is, 0 to 1: the rain that had time to act, and the soil itself when the
    model has it."""
    rain = min(1.0, w.opad_3_14_dni / SOAKING)
    soil = soil_wetness(w)
    return rain if soil is None else (rain + soil) / 2


def soil_wetness(w: Warunki) -> float | None:
    if w.wilgotnosc_gleby is None:
        return None
    return min(1.0, max(0.0, (w.wilgotnosc_gleby - SOIL_DRY) / (SOIL_WET - SOIL_DRY)))


def in_season(wanted: Sequence[Grzyb], month: Miesiac) -> bool:
    return any(grzyby.PROFILE[g].sezon.get(month, 0) > 0 for g in wanted)


def next_season(g: Grzyb, month: Miesiac) -> Miesiac:
    """The first month after `month` the mushroom grows in at all."""
    later = [*range(month + 1, 13), *range(1, month + 1)]
    return next(Miesiac(m) for m in later if grzyby.PROFILE[g].sezon.get(Miesiac(m), 0) > 0)


def species(code: str | None) -> str | None:
    """BDL's species code without the subspecies: BRZ.O → BRZ."""
    return code.split(".")[0] if code else None


def age_class_of(years: int) -> int:
    return next(i for i, (below, _) in enumerate(grzyby.KLASY_WIEKU) if below is None or years < below)


def opinion(factor: float) -> str:
    """A factor in words."""
    if factor >= 0.85:
        return "bardzo dobrze"
    if factor >= 0.6:
        return "dobrze"
    if factor >= 0.3:
        return "średnio"
    return "słabo" if factor > 0 else "nie rośnie tu"


def season_text(profile: ProfilGrzyba, month: Miesiac) -> str:
    factor = profile.sezon.get(month, 0)
    if factor >= 0.9:
        return "szczyt sezonu"
    if factor >= 0.5:
        return "sezon"
    if factor == 0:
        return "poza sezonem"
    # Early or late: whether the peak is still to come this year.
    return "początek sezonu" if any(f > factor for m, f in profile.sezon.items() if m > month) else "koniec sezonu"


def age_text(years: int) -> str:
    """An age in Polish: 1 rok, 22 lata, 25 lat."""
    if years == 1:
        return "1 rok"
    return f"{years} lata" if years % 10 in (2, 3, 4) and years % 100 not in (12, 13, 14) else f"{years} lat"


def distance_m(a: Wydzielenie, b: Wydzielenie) -> float:
    """Great-circle distance between the two stands' points (haversine; metres)."""
    lat1, lat2 = math.radians(a.lat), math.radians(b.lat)
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(math.radians(b.lon - a.lon) / 2) ** 2
    return 2 * 6_371_000 * math.asin(math.sqrt(h))
