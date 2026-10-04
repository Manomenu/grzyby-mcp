"""How promising a stand is for the mushrooms asked about, and why — a plain formula, no AI.

For each mushroom the score is the product of its factors from grzyby.py — trees, site, age,
month — times two minor ones of the stand itself, size and distance. One zero rules a stand out
for that mushroom. Asked about several, a stand has a score for each and their average — the
map shows either, and each has its own best spots. Weather joins the factors next (TODO,
stage 1).
"""

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from grzyby_server.lasy.model import Wydzielenie
from grzyby_server.miejsca import grzyby
from grzyby_server.miejsca.model import Grzyb, Miesiac, ProfilGrzyba

MIN_SPACING_M = 1000  # the spots offered should be different walks, not neighbouring stands


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


def score(w: Wydzielenie, wanted: Sequence[Grzyb], month: Miesiac, radius_m: float) -> Score:
    """`wanted` is not empty."""
    tree = species(w.gatunek) or ""
    tree_name, adjective = grzyby.DRZEWA.get(tree, grzyby.INNE_DRZEWO)
    group, site_name = grzyby.SIEDLISKA.get(w.siedlisko or "", (None, "siedlisko nieznane"))
    age_class = age_class_of(w.wiek)
    age_name = f"{grzyby.KLASY_WIEKU[age_class][1]} ({age_text(w.wiek)})"
    # Minor factors, no sentence of their own: a bigger stand is more forest to walk, a nearer one
    # a shorter drive. Neither can take more than a fifth / a third off.
    size = 0.8 + 0.2 * min(1.0, w.powierzchnia_ha / 5)
    nearness = 1 - 0.3 * min(1.0, w.distance_m / radius_m)

    def factors(profile: ProfilGrzyba) -> tuple[float, float, float, float]:
        site = profile.siedliska.get(group, 0) if group else grzyby.NIEZNANE_SIEDLISKO
        return profile.drzewa.get(tree, 0), site, profile.wiek[age_class], profile.sezon.get(month, 0)

    def reasons(profile: ProfilGrzyba) -> list[str]:
        tree_f, site_f, age_f, _season = factors(profile)  # the season goes into words by season_text
        return [
            f"{tree_name} — {opinion(tree_f)} dla {profile.dopelniacz}",
            f"{site_name} — {opinion(site_f)}",
            f"{age_name} — {opinion(age_f)}",
            f"{month.nazwa}: {season_text(profile, month)}",
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
