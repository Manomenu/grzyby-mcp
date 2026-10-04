"""The search behind the tool: place name → point → stands around it → the best three.

Everything a failure of an outside service can break ends as a note in the answer, not as an
error: the chatbot can still tell the user what happened and what to check themselves.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from psycopg import Connection

from grzyby_server.fetch import GetJson
from grzyby_server.lasy import importer, store, zakazy
from grzyby_server.miejsca import geocoding, scoring
from grzyby_server.miejsca.model import Answer, Miejsce, route_url

POLAND = ZoneInfo("Europe/Warsaw")


def search(conn: Connection, get_json: GetJson, miejscowosc: str, promien_km: int, now: datetime) -> Answer:
    try:
        place = geocoding.geocode(conn, get_json, miejscowosc)
    except (OSError, ValueError, KeyError):
        return _no_spots(conn, promien_km, f"Nie udało się teraz sprawdzić, gdzie leży „{miejscowosc}” — spróbuj za chwilę.")
    if place is None:
        return _no_spots(conn, promien_km, f"Nie znalazłem w Polsce miejscowości „{miejscowosc}”.")

    zakazy_at = zakazy.refresh(conn, get_json, now)
    radius_m = promien_km * 1000
    candidates = store.wydzielenia_within(conn, place.lat, place.lon, radius_m)
    picked = scoring.pick([scoring.score(w, radius_m) for w in candidates])

    uwagi: list[str] = []
    if not candidates:
        uwagi.append(f"W promieniu {promien_km} km nie mam lasów, do których wolno wejść — na razie znam tylko okolice Suwałk i Wigier.")
    elif not picked:
        uwagi.append("W okolicy są tylko lasy mało obiecujące dla grzybiarza (młodniki).")
    if zakazy_at is None or now - zakazy_at >= zakazy.FRESH_FOR:
        uwagi.append("Nie udało się sprawdzić aktualnych zakazów wstępu do lasu — przed wyjściem zajrzyj na bdl.lasy.gov.pl.")

    miejsca = [
        Miejsce(
            nazwa=s.name,
            lat=s.wydzielenie.lat,
            lon=s.wydzielenie.lon,
            dlaczego="; ".join([*s.reasons, f"{s.wydzielenie.distance_m / 1000:.1f} km od centrum".replace(".", ",")]) + ".",
            trasa=route_url(s.wydzielenie.lat, s.wydzielenie.lon),
            adres_lesny=s.wydzielenie.adres_lesny,
        )
        for s in picked
    ]
    data_year = max((s.wydzielenie.data_year for s in picked), default=None)
    return Answer(
        szukano_wokol=place.name,
        promien_km=promien_km,
        miejsca=miejsca,
        uwagi=uwagi,
        zrodla=attribution(conn, data_year, zakazy_at),
    )


def attribution(conn: Connection, data_year: int | None, zakazy_at: datetime | None) -> str:
    """BDL's terms want the source, when the data was made and when it was fetched;
    OpenStreetMap's licence wants its name next to what Nominatim found."""
    wydzielenia_at = store.fetched_at(conn, importer.STANDS)
    parts = [
        "Drzewostany: Bank Danych o Lasach (bdl.lasy.gov.pl)"
        + (f", stan na {data_year} r." if data_year else "")
        + (f", pobrane {wydzielenia_at.astimezone(POLAND):%d.%m.%Y}" if wydzielenia_at else "")
        + ", licencja CC BY 4.0; na tej podstawie nasze wyliczenia",
        "parki narodowe i rezerwaty: GDOŚ",
        "zakazy wstępu: BDL" + (f", sprawdzone {zakazy_at.astimezone(POLAND):%d.%m.%Y %H:%M}" if zakazy_at else ""),
        "położenie miejscowości: © autorzy OpenStreetMap (Nominatim)",
    ]
    return "; ".join(parts) + "."


def _no_spots(conn: Connection, promien_km: int, uwaga: str) -> Answer:
    return Answer(szukano_wokol=None, promien_km=promien_km, miejsca=[], uwagi=[uwaga], zrodla=attribution(conn, None, None))
