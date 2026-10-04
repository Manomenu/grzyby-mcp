from urllib.parse import urlencode

from pydantic import BaseModel, Field


class Miejsce(BaseModel):
    """One spot worth walking to: a forest stand, why it is promising, and the way there."""

    nazwa: str = Field(description="Krótki opis miejsca, np. „bór sosnowy, 76 lat”")
    lat: float
    lon: float
    dlaczego: str = Field(description="Uzasadnienie po polsku: drzewa, wiek, siedlisko, pogoda")
    trasa: str = Field(description="Link do trasy w Google Maps")
    adres_lesny: str = Field(description="Adres leśny wydzielenia w Banku Danych o Lasach")


class Odpowiedz(BaseModel):
    """What the tool returns: the spots, plus where the data comes from (CC BY 4.0 requires it)."""

    miejsca: list[Miejsce]
    zrodla: str


def opis(odpowiedz: Odpowiedz) -> str:
    """The answer as text (Markdown): what the chatbot reads, and all a client without the map shows."""
    lines = [f"**{m.nazwa}** — {m.dlaczego} [Trasa w Google Maps]({m.trasa})" for m in odpowiedz.miejsca]
    return "\n\n".join([*lines, f"_{odpowiedz.zrodla}_"])


def trasa(lat: float, lon: float) -> str:
    """A Google Maps directions link to the point, from wherever the user is."""
    return "https://www.google.com/maps/dir/?" + urlencode({"api": 1, "destination": f"{lat:.6f},{lon:.6f}"})
