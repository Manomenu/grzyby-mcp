"""The search behind the tool: place name → point → stands around it → the best few.

Everything a failure of an outside service can break ends as a note in the answer, not as an
error: the chatbot can still tell the user what happened and what to check themselves.
"""

import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from psycopg import Connection

from grzyby_server.fetch import GetJson
from grzyby_server.lasy import store, tiles, zakazy
from grzyby_server.lasy.model import Tile, Wydzielenie, tiles_around
from grzyby_server.miejsca import cache, geocoding, grzyby, map_data, scoring
from grzyby_server.miejsca.model import Answer, Grzyb, Miejsce, Miesiac, day_text, route_url
from grzyby_server.pogoda import refresh as weather
from grzyby_server.pogoda import store as weather_store
from grzyby_server.pogoda.conditions import conditions
from grzyby_server.pogoda.model import Dzien, Warunki

POLAND = ZoneInfo("Europe/Warsaw")
# The days a question may be about, relative to today: three back, five ahead — what the weather
# stored covers (pogoda/sources.py: 21 days back, 6 ahead).
MIN_DAY, MAX_DAY = -3, 5
# From this many days ahead the weather is a forecast worth a word of caution.
UNSURE_FROM = 3

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
    ile_miejsc: int = 3
    za_ile_dni: int = 0  # the day to score: 0 today, 1 tomorrow, -1 yesterday


@dataclass(frozen=True)
class Area:
    """A place and everything about it the day does not change: its stands and the weather days
    around it — what both tools (search, best_day) work from."""

    place: geocoding.Place
    radius_m: float
    around: list[Tile]
    candidates: list[Wydzielenie]
    ensured: tiles.Ensured  # tiles whose forest data could not be fetched, or why none were tried
    weather_days: dict[Tile, list[Dzien]]
    weather_ok: bool
    zakazy_at: datetime | None
    today: date  # in Poland


def prepare(conn: Connection, get_json: GetJson, miejscowosc: str, promien_km: int, now: datetime) -> Area | str:
    """The area around `miejscowosc`, or a note for the user when the place cannot be found."""
    try:
        place = geocoding.geocode(conn, get_json, miejscowosc)
    except (OSError, ValueError, KeyError):
        return f"Nie udało się teraz sprawdzić, gdzie leży „{miejscowosc}” — spróbuj za chwilę."
    if place is None:
        return f"Nie znalazłem w Polsce miejscowości „{miejscowosc}”."
    zakazy_at = zakazy.refresh(conn, get_json, now)
    radius_m = promien_km * 1000
    around = tiles_around(place.lat, place.lon, radius_m)
    # A first question about an area brings its forest data in: a few seconds, once.
    ensured = tiles.ensure(conn, get_json, around, now)
    # Poland's calendar: a question at 00:30 on the 1st is about the 1st.
    today = now.astimezone(POLAND).date()
    weather_ok = weather.ensure(conn, get_json, around, now)
    return Area(
        place=place,
        radius_m=radius_m,
        around=around,
        candidates=store.wydzielenia_within(conn, place.lat, place.lon, radius_m),
        ensured=ensured,
        # Enough days for the windows of pogoda/conditions.py on any day the tools may ask about.
        weather_days=weather_store.days(conn, around, today - timedelta(days=15 - MIN_DAY), today + timedelta(days=MAX_DAY)),
        weather_ok=weather_ok,
        zakazy_at=zakazy_at,
        today=today,
    )


def score_day(area: Area, wanted: Sequence[Grzyb], day: date) -> tuple[list[scoring.Score], dict[str, Warunki | None]]:
    """Every stand of the area scored for `day` — the weather of that day, the month of that day."""
    warunki: dict[str, Warunki | None] = {tile.id: conditions(area.weather_days.get(tile, []), day) for tile in area.around}
    month = Miesiac(day.month)
    return [scoring.score(w, wanted, month, area.radius_m, warunki.get(w.tile)) for w in area.candidates], warunki


def search(conn: Connection, get_json: GetJson, query: Query, now: datetime) -> Answer:
    promien_km = query.promien_km
    wanted = list(dict.fromkeys(query.grzyby))  # in the order asked, each once
    # The day asked about is in the key: the season and the weather's days change at midnight.
    day_asked = (now.astimezone(POLAND).date() + timedelta(days=query.za_ile_dni)).isoformat()
    cache_key = json.dumps([" ".join(query.miejscowosc.split()).lower(), wanted, promien_km, query.ile_miejsc, day_asked])
    if (cached := cache.get(conn, cache_key, now)) is not None:
        return cached
    area = prepare(conn, get_json, query.miejscowosc, promien_km, now)
    if isinstance(area, str):
        return _no_spots(wanted, promien_km, area)
    place, candidates = area.place, area.candidates
    day = area.today + timedelta(days=query.za_ile_dni)
    month = Miesiac(day.month)
    scores, warunki = score_day(area, wanted, day)
    # Spots for all the mushrooms at once (their average) and, asked about several, for each on
    # its own — usually different places, as they should be.
    picked = scoring.pick(scores, query.ile_miejsc)
    per_grzyb = {g: scoring.pick(scores, query.ile_miejsc, by=lambda s, g=g: s.per_grzyb[g]) for g in wanted} if len(wanted) > 1 else {}
    obszary = store.obszary_within(conn, place.lat, place.lon, area.radius_m)
    mapa = map_data.build_map(scores, obszary, (place.lat, place.lon), map_data.rules(wanted, month), warunki)

    uwagi: list[str] = []
    if not scoring.in_season(wanted, month):
        uwagi.append(
            f"{month.nazwa.capitalize()} to nie sezon na: {_names(wanted)}. "
            + "; ".join(f"{grzyby.PROFILE[g].nazwa} — od: {scoring.next_season(g, month).nazwa}" for g in wanted)
            + "."
        )
    elif area.ensured.refused is not None:
        # The area is not known yet, so no claim about its forests — the refusal says why.
        uwagi.append(REFUSED[area.ensured.refused])
    elif not candidates:
        uwagi.append(
            f"W promieniu {promien_km} km nie ma lasów państwowych, do których wolno wejść — znam tylko Lasy Państwowe "
            "(Bank Danych o Lasach); lasy prywatne i gminne są poza moją wiedzą. Spróbuj większego promienia."
        )
    elif not picked:
        uwagi.append(f"W okolicy nie ma lasów, w których rośnie: {_names(wanted)}.")
    if area.ensured.failed:
        uwagi.append(
            "Części okolicy nie udało się teraz pobrać z Banku Danych o Lasach — wyniki i mapa mogą być niepełne; spróbuj za chwilę."
        )
    if mapa.pominiete:
        uwagi.append(f"Mapa pokazuje {len(mapa.drzewostany.wiek)} najlepszych drzewostanów; {mapa.pominiete} słabszych się nie zmieściło.")
    weather_missing = not area.weather_ok or not any(warunki.values())
    if weather_missing:
        uwagi.append("Nie udało się teraz pobrać pogody (Open-Meteo) — ocena bez niej; spróbuj za chwilę.")
    elif query.za_ile_dni >= UNSURE_FROM:
        uwagi.append(f"Ocena na {day_text(day)} opiera się na prognozie pogody — im dalej, tym mniej pewnej.")
    zakazy_stale = area.zakazy_at is None or now - area.zakazy_at >= zakazy.FRESH_FOR
    if zakazy_stale:
        uwagi.append("Nie udało się sprawdzić aktualnych zakazów wstępu do lasu — przed wyjściem zajrzyj na bdl.lasy.gov.pl.")

    # One mushroom: its own reasons; several: the average and how it is made up.
    together = wanted[0] if len(wanted) == 1 else None
    data_year = max((s.wydzielenie.data_year for s in [*picked, *(s for ss in per_grzyb.values() for s in ss)]), default=None)
    answer = Answer(
        szukano_wokol=place.name,
        grzyby=[grzyby.PROFILE[g].nazwa for g in wanted],
        promien_km=promien_km,
        dzien=day,
        miejsca=[_spot(s, together) for s in picked],
        miejsca_na_grzyb={g: [_spot(s, g) for s in spots] for g, spots in per_grzyb.items()},
        uwagi=uwagi,
        zrodla=attribution(data_year, store.oldest_fetch(conn, area.around), area.zakazy_at),
        mapa=mapa,
    )
    # Only a complete answer is kept: a note about a service that did not answer must not outlive it.
    if not (area.ensured.refused or area.ensured.failed or weather_missing or zakazy_stale):
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


CC_BY = "CC BY 4.0 (creativecommons.org/licenses/by/4.0)"


def attribution(data_year: int | None, wydzielenia_at: datetime | None, zakazy_at: datetime | None) -> str:
    """What each source's licence asks next to its data (docs/dev/rozpoznanie-danych.md, „Licencje”):
    BDL — the source, when the data was made and fetched, the licence with a link, and that we
    processed it; Open-Meteo — a link to it, the licence, the processing; GDOŚ — the source (no
    conditions in its service); Nominatim — „© OpenStreetMap contributors” with the copyright link.
    Plain text with bare addresses: the map shows it as text, the chatbot as Markdown."""
    parts = [
        "Drzewostany: Bank Danych o Lasach (bdl.lasy.gov.pl)"
        + (f", stan na {data_year} r." if data_year else "")
        + (f", pobrane {wydzielenia_at.astimezone(POLAND):%d.%m.%Y}" if wydzielenia_at else ""),
        "zakazy wstępu: Bank Danych o Lasach" + (f", sprawdzone {zakazy_at.astimezone(POLAND):%d.%m.%Y %H:%M}" if zakazy_at else ""),
        f"oba na licencji {CC_BY}, przetworzone przez nas na ocenę",
        "parki narodowe i rezerwaty: Generalna Dyrekcja Ochrony Środowiska (sdi.gdos.gov.pl)",
        f"pogoda: Open-Meteo (open-meteo.com), licencja {CC_BY}, przetworzona przez nas na ocenę",
        "położenie miejscowości: © autorzy OpenStreetMap (openstreetmap.org/copyright), wyszukiwarka Nominatim",
    ]
    return "; ".join(parts) + "."


def _no_spots(wanted: list[Grzyb], promien_km: int, uwaga: str) -> Answer:
    names = [grzyby.PROFILE[g].nazwa for g in wanted]
    return Answer(
        szukano_wokol=None, grzyby=names, promien_km=promien_km, dzien=None, miejsca=[], uwagi=[uwaga], zrodla=attribution(None, None, None)
    )


def _names(wanted: list[Grzyb]) -> str:
    return ", ".join(grzyby.PROFILE[g].nazwa for g in wanted)
