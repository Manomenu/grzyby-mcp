from urllib.parse import urlencode

from pydantic import BaseModel, Field

from grzyby_server.lasy.model import ObszarKind


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
    wynik: list[int] = Field(description="Ocena od 0 do 100")
    gatunek: list[str | None]
    siedlisko: list[str | None]
    wiek: list[int]


class ObszarNaMapie(BaseModel):
    rodzaj: ObszarKind
    nazwa: str
    ksztalt: list[list[str]]


class Reguly(BaseModel):
    """The scoring tables (scoring.py) as they are, so the map explains a stand with the same
    words and numbers the score came from."""

    gatunki: dict[str, tuple[float, str, str]] = Field(description="kod → (czynnik, przymiotnik, dlaczego)")
    inny_gatunek: tuple[float, str, str]
    siedliska: dict[str, tuple[float, str]] = Field(description="kod → (czynnik, dlaczego)")
    nieznane_siedlisko: tuple[float, str]
    wiek: list[tuple[int | None, float, str]] = Field(description="(poniżej lat, czynnik, dlaczego), ostatnia klasa bez górnej granicy")


class Mapa(BaseModel):
    """What the widget colours: every stand around the place, the areas one may not enter, and
    the rules behind the colours. Not for the chatbot to read — the text has what it needs."""

    lat: float
    lon: float
    drzewostany: Drzewostany
    pominiete: int = Field(description="Ile najsłabszych drzewostanów nie zmieściło się na mapie")
    obszary: list[ObszarNaMapie]
    reguly: Reguly


class Answer(BaseModel):
    """What the tool returns: the spots, plus where the data comes from (CC BY 4.0 requires it)."""

    szukano_wokol: str | None = Field(description="Miejscowość, wokół której szukano — pełna nazwa z mapy, do sprawdzenia")
    promien_km: int
    miejsca: list[Miejsce]
    uwagi: list[str] = Field(description="Ostrzeżenia dla użytkownika: brak danych, nieaktualne zakazy wstępu itp.")
    zrodla: str
    mapa: Mapa | None = None


def as_text(answer: Answer) -> str:
    """The answer as text (Markdown): what the chatbot reads, and all a client without the map shows."""
    head = [f"Lasy w promieniu {answer.promien_km} km od: {answer.szukano_wokol}."] if answer.szukano_wokol else []
    lines = [f"**{m.nazwa}** — {m.dlaczego} [Trasa w Google Maps]({m.trasa})" for m in answer.miejsca]
    notes = [f"**Uwaga:** {uwaga}" for uwaga in answer.uwagi]
    return "\n\n".join([*head, *lines, *notes, f"_{answer.zrodla}_"])


def route_url(lat: float, lon: float) -> str:
    """A Google Maps directions link to the point, from wherever the user is."""
    return "https://www.google.com/maps/dir/?" + urlencode({"api": 1, "destination": f"{lat:.6f},{lon:.6f}"})
