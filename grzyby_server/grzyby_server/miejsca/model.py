from datetime import date
from enum import IntEnum, StrEnum
from typing import Annotated
from urllib.parse import urlencode

from pydantic import BaseModel, ConfigDict, Field

from grzyby_server.lasy.model import ObszarKind


class Grzyb(StrEnum):
    """The mushrooms the tool knows (their profiles: grzyby.py). Values are what the chatbot sends."""

    BOROWIK = "borowik"
    PODGRZYBEK = "podgrzybek"
    KURKA = "kurka"
    KOZLARZ = "kozlarz"
    MASLAK = "maslak"
    RYDZ = "rydz"


class Miesiac(IntEnum):
    """A month, numbered as datetime numbers it, so `Miesiac(now.month)` is this one."""

    STYCZEN = 1
    LUTY = 2
    MARZEC = 3
    KWIECIEN = 4
    MAJ = 5
    CZERWIEC = 6
    LIPIEC = 7
    SIERPIEN = 8
    WRZESIEN = 9
    PAZDZIERNIK = 10
    LISTOPAD = 11
    GRUDZIEN = 12

    @property
    def nazwa(self) -> str:
        return NAZWY_MIESIECY[self - 1]


NAZWY_MIESIECY = (
    "styczeń", "luty", "marzec", "kwiecień", "maj", "czerwiec",
    "lipiec", "sierpień", "wrzesień", "październik", "listopad", "grudzień",
)  # fmt: skip

Czynnik = Annotated[float, Field(ge=0, le=1)]


class ProfilGrzyba(BaseModel):
    """Where and when one mushroom grows, as factors from 0 (never) to 1 (its favourite) — the
    data of the score (scoring.py), and of the map's explanations."""

    model_config = ConfigDict(frozen=True)

    nazwa: str = Field(description="np. „koźlarz”")
    dopelniacz: str = Field(description="np. „koźlarza” — „dobrze dla koźlarza”")
    drzewa: dict[str, Czynnik] = Field(description="Kod gatunku panującego w BDL → czynnik; brak = drzewo nie dla niego")
    siedliska: dict[str, Czynnik] = Field(description="Grupa siedlisk (grzyby.GRUPY_SIEDLISK) → czynnik")
    wiek: tuple[Czynnik, Czynnik, Czynnik, Czynnik] = Field(description="Czynnik dla każdej klasy wieku (grzyby.KLASY_WIEKU)")
    sezon: dict[Miesiac, Czynnik] = Field(description="Miesiąc → czynnik; miesiąca, którego nie ma, grzyb nie rośnie")
    temperatura: float = Field(description="Najlepsza średnia temperatura z 5 dni przed owocnikowaniem, °C")


class Miejsce(BaseModel):
    """One spot worth walking to: a forest stand, why it is promising, and the way there."""

    nazwa: str = Field(description="Krótki opis miejsca, np. „bór sosnowy, 76 lat”")
    lat: float
    lon: float
    dlaczego: str = Field(description="Uzasadnienie po polsku: drzewa, wiek, siedlisko, pogoda")
    trasa: str = Field(description="Link do trasy w Google Maps")
    adres_lesny: str = Field(description="Adres leśny wydzielenia w Banku Danych o Lasach")


class Drzewostany(BaseModel):
    """Every stand on the map, column by column — one list per attribute, all in the same order —
    so the keys go once, not two thousand times. The size limit of a tool result is real
    (docs/mcp-apps.md)."""

    ksztalt: list[list[list[str]]] = Field(description="Wielokąty z pierścieni, każdy pierścień jako encoded polyline")
    wynik: dict[Grzyb, list[int]] = Field(description="Ocena od 0 do 100 dla każdego wybranego grzyba")
    gatunek: list[str | None]
    siedlisko: list[str | None]
    wiek: list[int]


class ObszarNaMapie(BaseModel):
    rodzaj: ObszarKind
    nazwa: str
    ksztalt: list[list[str]]


class Reguly(BaseModel):
    """The tables of the score (grzyby.py) as they are, so the map explains a stand with the same
    words and numbers its score came from."""

    drzewa: dict[str, tuple[str, str]] = Field(description="Kod gatunku → (nazwa, przymiotnik)")
    siedliska: dict[str, tuple[str, str]] = Field(description="Kod typu siedliska → (grupa, opis)")
    grupy_siedlisk: dict[str, str] = Field(description="Grupa → nazwa")
    klasy_wieku: list[tuple[int | None, str]] = Field(description="(poniżej lat, nazwa); ostatnia bez górnej granicy")
    grzyby: dict[Grzyb, ProfilGrzyba] = Field(description="Profile wybranych grzybów")
    miesiac: Miesiac = Field(description="Miesiąc, dla którego liczono ocenę")


class PogodaKwadratu(BaseModel):
    """The weather over one tile of the grid, for the map's weather mode."""

    opad: float = Field(description="Deszcz 3–14 dni temu, mm")
    wilgotnosc_gleby: float | None = Field(description="m³/m³ na głębokości 3–9 cm")
    temperatura: float = Field(description="Średnia z 5 dni, °C")
    wilgoc: float = Field(description="Jak mokro, od 0 do 1 — ten sam wzór, co w ocenie")


class Mapa(BaseModel):
    """What the widget colours: every stand around the place, the areas one may not enter, and
    the rules behind the colours. Not for the chatbot to read — the text has what it needs."""

    lat: float
    lon: float
    drzewostany: Drzewostany
    pominiete: int = Field(description="Ile najsłabszych drzewostanów nie zmieściło się na mapie")
    obszary: list[ObszarNaMapie]
    reguly: Reguly
    pogoda: dict[str, PogodaKwadratu] = Field(description="Kwadrat siatki (wiersz_kolumna) → pogoda; bez kwadratów bez danych")
    kwadrat: tuple[float, float] = Field(description="Rozmiar kwadratu siatki w stopniach: szerokość, długość")


class Answer(BaseModel):
    """What the tool returns: the spots, plus where the data comes from (CC BY 4.0 requires it)."""

    szukano_wokol: str | None = Field(description="Miejscowość, wokół której szukano — pełna nazwa z mapy, do sprawdzenia")
    grzyby: list[str] = Field(description="Szukane grzyby, po polsku")
    promien_km: int
    dzien: date | None = Field(default=None, description="Dzień, na który liczono ocenę (pogoda i sezon tego dnia)")
    miejsca: list[Miejsce] = Field(
        description="Najlepsze miejsca na wszystkie szukane grzyby naraz (średnia ich ocen); przy jednym grzybie — na niego"
    )
    miejsca_na_grzyb: dict[Grzyb, list[Miejsce]] = Field(
        default_factory=dict[Grzyb, list[Miejsce]],
        description="Przy kilku grzybach: najlepsze miejsca na każdy z osobna — zwykle inne niż wspólne",
    )
    uwagi: list[str] = Field(description="Ostrzeżenia dla użytkownika: brak danych, nieaktualne zakazy wstępu itp.")
    zrodla: str
    mapa: Mapa | None = None


def as_text(answer: Answer) -> str:
    """The answer as text (Markdown): what the chatbot reads, and all a client without the map shows."""
    on_day = f" — {day_text(answer.dzien)}" if answer.dzien else ""
    head = (
        [f"Lasy w promieniu {answer.promien_km} km od: {answer.szukano_wokol} — na: {', '.join(answer.grzyby)}{on_day}."]
        if answer.szukano_wokol
        else []
    )

    def spots(miejsca: list[Miejsce]) -> list[str]:
        return [f"**{m.nazwa}** — {m.dlaczego} [Trasa w Google Maps]({m.trasa})" for m in miejsca]

    lines = spots(answer.miejsca)
    if answer.miejsca_na_grzyb:
        lines = ["### Na wszystkie naraz (średnia ocen)", *lines]
        # Answer.grzyby holds the Polish names in the order the spots are keyed in (search.py).
        for name, miejsca in zip(answer.grzyby, answer.miejsca_na_grzyb.values(), strict=True):
            lines += [f"### Na: {name}", *(spots(miejsca) or ["(brak miejsc)"])]
    notes = [f"**Uwaga:** {uwaga}" for uwaga in answer.uwagi]
    return "\n\n".join([*head, *lines, *notes, f"_{answer.zrodla}_"])


class DzienPrognozy(BaseModel):
    """How good the area is on one day: the best stands' scores with that day's weather."""

    dzien: date
    nazwa: str = Field(description="np. „sobota 10.10”")
    za_ile_dni: int
    ocena: int = Field(description="Ocena okolicy od 0 do 100 — średnia z najlepszych drzewostanów, na wszystkie grzyby naraz")
    na_grzyb: dict[Grzyb, int] = Field(description="To samo dla każdego grzyba z osobna")
    pogoda: str = Field(description="Pogoda okolicy w skrócie: deszcz, wilgoć, temperatura, przymrozki")


class Prognoza(BaseModel):
    """What the „when” tool returns: the area day by day, and the best day."""

    szukano_wokol: str | None
    grzyby: list[str]
    promien_km: int
    dni: list[DzienPrognozy]
    najlepszy: date | None = Field(description="Najlepszy dzień; brak, gdy żaden nie jest dobry")
    uwagi: list[str]
    zrodla: str


def forecast_text(p: Prognoza) -> str:
    """The forecast as text (Markdown) for the chatbot."""
    if not p.szukano_wokol:
        return "\n\n".join([*(f"**Uwaga:** {u}" for u in p.uwagi), f"_{p.zrodla}_"])
    head = f"Kiedy na: {', '.join(p.grzyby)} — lasy w promieniu {p.promien_km} km od: {p.szukano_wokol}."
    lines = [
        f"- **{d.nazwa}**: {d.ocena}/100"
        + (f" ({', '.join(f'{g.value} {v}' for g, v in d.na_grzyb.items())})" if len(d.na_grzyb) > 1 else "")
        + f" — {d.pogoda}"
        for d in p.dni
    ]
    best = next((d for d in p.dni if d.dzien == p.najlepszy), None)
    verdict = f"**Najlepiej: {best.nazwa}.**" if best else "**Żaden z tych dni nie wygląda dobrze.**"
    return "\n\n".join([head, "\n".join(lines), verdict, *(f"**Uwaga:** {u}" for u in p.uwagi), f"_{p.zrodla}_"])


DNI_TYGODNIA = ("poniedziałek", "wtorek", "środa", "czwartek", "piątek", "sobota", "niedziela")


def day_text(day: date) -> str:
    """A day as people say it: „sobota 10.10”."""
    return f"{DNI_TYGODNIA[day.weekday()]} {day.day}.{day.month:02d}"


def route_url(lat: float, lon: float) -> str:
    """A Google Maps directions link to the point, from wherever the user is."""
    return "https://www.google.com/maps/dir/?" + urlencode({"api": 1, "destination": f"{lat:.6f},{lon:.6f}"})
