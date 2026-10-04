"""The search behind the tool: place name → point → stands around it → the best few.

Everything a failure of an outside service can break ends as a note in the answer, not as an
error: the chatbot can still tell the user what happened and what to check themselves.
"""

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from psycopg import Connection

from grzyby_server.fetch import GetJson
from grzyby_server.lasy import store, tiles, zakazy
from grzyby_server.lasy.model import tiles_around
from grzyby_server.miejsca import cache, geocoding, grzyby, map_data, scoring
from grzyby_server.miejsca.model import Answer, Grzyb, Miejsce, Miesiac, route_url
from grzyby_server.pogoda import refresh as weather
from grzyby_server.pogoda import store as weather_store
from grzyby_server.pogoda.conditions import conditions
from grzyby_server.pogoda.model import Warunki

POLAND = ZoneInfo("Europe/Warsaw")

REFUSED = {
    tiles.Refusal.DAILY_LIMIT: (
        "Na dziś wyczerpałem limit pobierania nowych okolic z Banku Danych o Lasach, a tej okolicy jeszcze nie znam "
        "(albo znam tylko jej część) — wyniki i mapa mogą być puste lub niepełne. Spróbuj jutro; okolice, o które "
        "już pytano, działają normalnie."
    ),
    tiles.Refusal.BUSY: (
        "Pobieram teraz dane kilku innych nowych okolic naraz, a tej jeszcze nie znam (albo znam tylko jej część) — "
        "wyniki i mapa mogą być puste lub niepełne. Spróbuj za minutę."
    ),
}


@dataclass(frozen=True)
class Query:
    """What the user asked — the tool's parameters, as they came."""

    miejscowosc: str
    grzyby: list[Grzyb]
    promien_km: int
    ile_miejsc: int


def search(conn: Connection, get_json: GetJson, query: Query, now: datetime) -> Answer:
    miejscowosc, promien_km = query.miejscowosc, query.promien_km
    wanted = list(dict.fromkeys(query.grzyby))  # in the order asked, each once
    # The day and month in Poland's time: a question at 00:30 on the 1st is next month's.
    today = now.astimezone(POLAND).date()
    # The day is in the key: the season and the weather's days change at midnight.
    cache_key = json.dumps([" ".join(miejscowosc.split()).lower(), wanted, promien_km, query.ile_miejsc, today.isoformat()])
    if (cached := cache.get(conn, cache_key, now)) is not None:
        return cached
    try:
        place = geocoding.geocode(conn, get_json, miejscowosc)
    except (OSError, ValueError, KeyError):
        return _no_spots(wanted, promien_km, f"Nie udało się teraz sprawdzić, gdzie leży „{miejscowosc}” — spróbuj za chwilę.")
    if place is None:
        return _no_spots(wanted, promien_km, f"Nie znalazłem w Polsce miejscowości „{miejscowosc}”.")

    zakazy_at = zakazy.refresh(conn, get_json, now)
    radius_m = promien_km * 1000
    around = tiles_around(place.lat, place.lon, radius_m)
    # A first question about an area brings its forest data in: a few seconds, once.
    ensured = tiles.ensure(conn, get_json, around, now)
    candidates = store.wydzielenia_within(conn, place.lat, place.lon, radius_m)
    month = Miesiac(today.month)
    weather_ok = weather.ensure(conn, get_json, around, now)
    days = weather_store.days(conn, around, today - timedelta(days=15), today)
    warunki: dict[str, Warunki | None] = {tile.id: conditions(days.get(tile, []), today) for tile in around}
    scores = [scoring.score(w, wanted, month, radius_m, warunki.get(w.tile)) for w in candidates]
    # Spots for all the mushrooms at once (their average) and, asked about several, for each on
    # its own — usually different places, as they should be.
    picked = scoring.pick(scores, query.ile_miejsc)
    per_grzyb = {g: scoring.pick(scores, query.ile_miejsc, by=lambda s, g=g: s.per_grzyb[g]) for g in wanted} if len(wanted) > 1 else {}
    obszary = store.obszary_within(conn, place.lat, place.lon, radius_m)
    mapa = map_data.build_map(scores, obszary, (place.lat, place.lon), map_data.rules(wanted, month), warunki)

    uwagi: list[str] = []
    if not scoring.in_season(wanted, month):
        uwagi.append(
            f"{month.nazwa.capitalize()} to nie sezon na: {_names(wanted)}. "
            + "; ".join(f"{grzyby.PROFILE[g].nazwa} — od: {scoring.next_season(g, month).nazwa}" for g in wanted)
            + "."
        )
    elif ensured.refused is not None:
        # The area is not known yet, so no claim about its forests — the refusal says why.
        uwagi.append(REFUSED[ensured.refused])
    elif not candidates:
        uwagi.append(
            f"W promieniu {promien_km} km nie ma lasów państwowych, do których wolno wejść — znam tylko Lasy Państwowe "
            "(Bank Danych o Lasach); lasy prywatne i gminne są poza moją wiedzą. Spróbuj większego promienia."
        )
    elif not picked:
        uwagi.append(f"W okolicy nie ma lasów, w których rośnie: {_names(wanted)}.")
    if ensured.failed:
        uwagi.append(
            "Części okolicy nie udało się teraz pobrać z Banku Danych o Lasach — wyniki i mapa mogą być niepełne; spróbuj za chwilę."
        )
    if mapa.pominiete:
        uwagi.append(f"Mapa pokazuje {len(mapa.drzewostany.wiek)} najlepszych drzewostanów; {mapa.pominiete} słabszych się nie zmieściło.")
    weather_missing = not weather_ok or not any(warunki.values())
    if weather_missing:
        uwagi.append("Nie udało się teraz pobrać pogody (Open-Meteo) — ocena bez niej; spróbuj za chwilę.")
    zakazy_stale = zakazy_at is None or now - zakazy_at >= zakazy.FRESH_FOR
    if zakazy_stale:
        uwagi.append("Nie udało się sprawdzić aktualnych zakazów wstępu do lasu — przed wyjściem zajrzyj na bdl.lasy.gov.pl.")

    # One mushroom: its own reasons; several: the average and how it is made up.
    together = wanted[0] if len(wanted) == 1 else None
    data_year = max((s.wydzielenie.data_year for s in [*picked, *(s for ss in per_grzyb.values() for s in ss)]), default=None)
    answer = Answer(
        szukano_wokol=place.name,
        grzyby=[grzyby.PROFILE[g].nazwa for g in wanted],
        promien_km=promien_km,
        miejsca=[_spot(s, together) for s in picked],
        miejsca_na_grzyb={g: [_spot(s, g) for s in spots] for g, spots in per_grzyb.items()},
        uwagi=uwagi,
        zrodla=attribution(data_year, store.oldest_fetch(conn, around), zakazy_at),
        mapa=mapa,
    )
    # Only a complete answer is kept: a note about a service that did not answer must not outlive it.
    if not (ensured.refused or ensured.failed or weather_missing or zakazy_stale):
        cache.put(conn, cache_key, answer, now)
    return answer


def _spot(s: scoring.Score, g: Grzyb | None) -> Miejsce:
    """A spot as the answer gives it: why it suits mushroom `g`, or (None) all of them on average."""
    if g is not None:
        why = s.reasons[g]
    else:
        parts = ", ".join(f"{grzyby.PROFILE[k].nazwa} {round(v * 100)}" for k, v in s.per_grzyb.items())
        why = [f"średnio {round(s.points * 100)}/100: {parts}", *s.facts]
    distance = f"{s.wydzielenie.distance_m / 1000:.1f} km od centrum".replace(".", ",")
    return Miejsce(
        nazwa=s.name,
        lat=s.wydzielenie.lat,
        lon=s.wydzielenie.lon,
        dlaczego="; ".join([*why, distance]) + ".",
        trasa=route_url(s.wydzielenie.lat, s.wydzielenie.lon),
        adres_lesny=s.wydzielenie.adres_lesny,
    )


def attribution(data_year: int | None, wydzielenia_at: datetime | None, zakazy_at: datetime | None) -> str:
    """BDL's terms want the source, when the data was made and when it was fetched;
    OpenStreetMap's licence wants its name next to what Nominatim found."""
    parts = [
        "Drzewostany: Bank Danych o Lasach (bdl.lasy.gov.pl)"
        + (f", stan na {data_year} r." if data_year else "")
        + (f", pobrane {wydzielenia_at.astimezone(POLAND):%d.%m.%Y}" if wydzielenia_at else "")
        + ", licencja CC BY 4.0; na tej podstawie nasze wyliczenia",
        "parki narodowe i rezerwaty: GDOŚ",
        "zakazy wstępu: BDL" + (f", sprawdzone {zakazy_at.astimezone(POLAND):%d.%m.%Y %H:%M}" if zakazy_at else ""),
        "pogoda: Open-Meteo (open-meteo.com), licencja CC BY 4.0",
        "położenie miejscowości: © autorzy OpenStreetMap (Nominatim)",
    ]
    return "; ".join(parts) + "."


def _no_spots(wanted: list[Grzyb], promien_km: int, uwaga: str) -> Answer:
    names = [grzyby.PROFILE[g].nazwa for g in wanted]
    return Answer(szukano_wokol=None, grzyby=names, promien_km=promien_km, miejsca=[], uwagi=[uwaga], zrodla=attribution(None, None, None))


def _names(wanted: list[Grzyb]) -> str:
    return ", ".join(grzyby.PROFILE[g].nazwa for g in wanted)
