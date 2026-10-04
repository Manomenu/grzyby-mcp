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


class Answer(BaseModel):
    """What the tool returns: the spots, plus where the data comes from (CC BY 4.0 requires it)."""

    szukano_wokol: str | None = Field(description="Miejscowość, wokół której szukano — pełna nazwa z mapy, do sprawdzenia")
    promien_km: int
    miejsca: list[Miejsce]
    uwagi: list[str] = Field(description="Ostrzeżenia dla użytkownika: brak danych, nieaktualne zakazy wstępu itp.")
    zrodla: str


def as_text(answer: Answer) -> str:
    """The answer as text (Markdown): what the chatbot reads, and all a client without the map shows."""
    head = [f"Lasy w promieniu {answer.promien_km} km od: {answer.szukano_wokol}."] if answer.szukano_wokol else []
    lines = [f"**{m.nazwa}** — {m.dlaczego} [Trasa w Google Maps]({m.trasa})" for m in answer.miejsca]
    notes = [f"**Uwaga:** {uwaga}" for uwaga in answer.uwagi]
    return "\n\n".join([*head, *lines, *notes, f"_{answer.zrodla}_"])


def route_url(lat: float, lon: float) -> str:
    """A Google Maps directions link to the point, from wherever the user is."""
    return "https://www.google.com/maps/dir/?" + urlencode({"api": 1, "destination": f"{lat:.6f},{lon:.6f}"})
