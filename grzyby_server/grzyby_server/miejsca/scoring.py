"""How promising a stand is for mushrooms, and why — a plain formula, no AI.

Each factor is a number from 0 to 1 with a sentence for the answer; the score is their product,
so one bad factor (a young plantation, an alder swamp) sinks a stand however good the rest is.
Today the factors are what the stand *is* — trees, age, site, size, distance. Weather comes next
(TODO, stage 1); the weights get corrected after walks in the forest (stage 2).
"""

import math
from dataclasses import dataclass

from grzyby_server.lasy.model import Wydzielenie

# Dominant species → (factor, adjective for the stand's name, why). Codes as BDL writes them; a
# suffix after the dot is the subspecies (BRZ.O — downy birch, DB.S — pedunculate oak).
GATUNKI: dict[str, tuple[float, str, str]] = {
    "SO": (1.0, "sosnowy", "sosna — borowik, podgrzybek, kurka, maślak"),
    "ŚW": (0.9, "świerkowy", "świerk — borowik, podgrzybek, kurka"),
    "BK": (0.75, "bukowy", "buk — borowik, kurka"),
    "DB": (0.75, "dębowy", "dąb — borowik, kurka, koźlarz"),
    "BRZ": (0.7, "brzozowy", "brzoza — koźlarz, borowik"),
    "MD": (0.6, "modrzewiowy", "modrzew — maślak modrzewiowy"),
    "OS": (0.6, "osikowy", "osika — koźlarz czerwony"),
    "GB": (0.4, "grabowy", "grab — niewiele grzybów jadalnych"),
    "LP": (0.4, "lipowy", "lipa — niewiele grzybów jadalnych"),
    "OL": (0.2, "olszowy", "olsza — mokro, mało grzybów jadalnych"),
}
INNY_GATUNEK = (0.3, "liściasty", "rzadki gatunek — mało wiadomo o grzybach")

# Forest site type → (factor, why).
SIEDLISKA: dict[str, tuple[float, str]] = {
    "BŚW": (1.0, "bór świeży — ulubione siedlisko borowika, podgrzybka i kurki"),
    "BMŚW": (1.0, "bór mieszany świeży — ulubione siedlisko borowika, podgrzybka i kurki"),
    "LMŚW": (0.85, "las mieszany świeży — żyzny, wiele gatunków grzybów"),
    "LŚW": (0.7, "las świeży — żyzny, liściasty"),
    "BS": (0.6, "bór suchy — grzyby dopiero po obfitych deszczach"),
    "BW": (0.6, "bór wilgotny — grzyby także w suchszym okresie"),
    "BMW": (0.6, "bór mieszany wilgotny — grzyby także w suchszym okresie"),
    "LMW": (0.55, "las mieszany wilgotny"),
    "LW": (0.5, "las wilgotny"),
    "BB": (0.3, "bór bagienny — mokro, trudno przejść"),
    "BMB": (0.3, "bór mieszany bagienny — mokro, trudno przejść"),
    "LMB": (0.3, "las mieszany bagienny — mokro, trudno przejść"),
    "OL": (0.2, "ols — bagno, mało grzybów jadalnych"),
    "OLJ": (0.2, "ols jesionowy — mokro, mało grzybów jadalnych"),
    "LŁ": (0.2, "las łęgowy — zalewany, mało grzybów jadalnych"),
}
NIEZNANE_SIEDLISKO = (0.5, "siedlisko nieznane")

# Age of the dominant species → (below this many years, factor, why). Stands under 20 are dense
# plantations: few mushrooms, no way through. The last class has no upper bound.
WIEK: list[tuple[int | None, float, str]] = [
    (20, 0.0, "młodnik — gęsto, mało grzybów"),
    (40, 0.6, "młody drzewostan — grzyby już są, ale mniej"),
    (121, 1.0, "dojrzały drzewostan — najlepszy wiek"),
    (None, 0.8, "stary drzewostan"),
]
MIN_SPACING_M = 1000  # the spots offered should be different walks, not three neighbouring stands


@dataclass(frozen=True)
class Score:
    wydzielenie: Wydzielenie
    points: float
    name: str
    reasons: list[str]


def score(w: Wydzielenie, radius_m: float) -> Score:
    gatunek, adjective, gatunek_why = GATUNKI.get(species(w.gatunek) or "", INNY_GATUNEK)
    siedlisko, siedlisko_why = SIEDLISKA.get(w.siedlisko or "", NIEZNANE_SIEDLISKO)
    wiek, wiek_why = next((factor, why) for below, factor, why in WIEK if below is None or w.wiek < below)
    # Minor factors, no sentence of their own: a bigger stand is more forest to walk, a nearer one
    # a shorter drive. Neither can take more than a fifth / a third off.
    size = 0.8 + 0.2 * min(1.0, w.powierzchnia_ha / 5)
    nearness = 1 - 0.3 * min(1.0, w.distance_m / radius_m)
    return Score(
        wydzielenie=w,
        points=gatunek * siedlisko * wiek * size * nearness,
        name=f"Las {adjective}, {age_text(w.wiek)}, {w.powierzchnia_ha:g} ha".replace(".", ","),
        reasons=[gatunek_why, siedlisko_why, f"{wiek_why} ({age_text(w.wiek)})"],
    )


def species(code: str | None) -> str | None:
    """BDL's species code without the subspecies: BRZ.O → BRZ."""
    return code.split(".")[0] if code else None


def pick(scores: list[Score], count: int = 3) -> list[Score]:
    """The best `count` with points above zero, each at least MIN_SPACING_M from those before it."""
    picked: list[Score] = []
    for candidate in sorted(scores, key=lambda s: s.points, reverse=True):
        if candidate.points <= 0 or len(picked) == count:
            break
        if all(distance_m(candidate.wydzielenie, p.wydzielenie) >= MIN_SPACING_M for p in picked):
            picked.append(candidate)
    return picked


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
