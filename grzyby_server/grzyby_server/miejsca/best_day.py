"""The „when” tool behind kiedy_na_grzyby: the same area scored for today and the days ahead.

Stands, trees, sites and ages stay put from day to day; what changes is the weather (and, at a
month's turn, the season), so the area is prepared once (search.prepare) and only scored again
per day. An area's score for a day is the mean of its best stands — how good the best forests
around are, not an average dragged down by bogs and plantations nobody goes to.
"""

from datetime import datetime, timedelta

from psycopg import Connection

from grzyby_server.fetch import GetJson
from grzyby_server.lasy import store
from grzyby_server.miejsca import grzyby, scoring
from grzyby_server.miejsca.model import DzienPrognozy, Prognoza, day_text
from grzyby_server.miejsca.search import MAX_DAY, UNSURE_FROM, Query, attribution, prepare, score_day
from grzyby_server.pogoda.model import Warunki

TOP = 10  # stands in an area's score for a day
GOOD = 40  # an area score from which a day is worth recommending


def best_day(conn: Connection, get_json: GetJson, query: Query, now: datetime) -> Prognoza:
    """The days from today to MAX_DAY ahead for the place, mushrooms and radius of `query` (its
    other fields are the map's business)."""
    promien_km = query.promien_km
    wanted = list(dict.fromkeys(query.grzyby))
    names = [grzyby.PROFILE[g].nazwa for g in wanted]
    area = prepare(conn, get_json, query.miejscowosc, promien_km, now)
    if isinstance(area, str):
        return Prognoza(
            szukano_wokol=None,
            grzyby=names,
            promien_km=promien_km,
            dni=[],
            najlepszy=None,
            uwagi=[area],
            zrodla=attribution(None, None, None),
        )

    dni: list[DzienPrognozy] = []
    for ahead in range(MAX_DAY + 1):
        day = area.today + timedelta(days=ahead)
        scores, warunki = score_day(area, wanted, day)
        dni.append(
            DzienPrognozy(
                dzien=day,
                nazwa=day_text(day),
                za_ile_dni=ahead,
                ocena=_area_score(scores, lambda s: s.points),
                na_grzyb={g: _area_score(scores, lambda s, g=g: s.per_grzyb[g]) for g in wanted},
                pogoda=_weather_text([w for w in warunki.values() if w is not None]),
            )
        )
    best = max(dni, key=lambda d: d.ocena, default=None)

    uwagi: list[str] = []
    if not area.candidates:
        uwagi.append(f"W promieniu {promien_km} km nie ma lasów państwowych, do których wolno wejść.")
    if not area.weather_ok:
        uwagi.append("Nie udało się teraz pobrać pogody (Open-Meteo) — dni różnią się tylko sezonem; spróbuj za chwilę.")
    uwagi.append(f"Od {UNSURE_FROM}. dnia naprzód to prognoza pogody — im dalej, tym mniej pewna.")
    return Prognoza(
        szukano_wokol=area.place.name,
        grzyby=names,
        promien_km=promien_km,
        dni=dni,
        najlepszy=best.dzien if best and best.ocena >= GOOD else None,
        uwagi=uwagi,
        zrodla=attribution(None, store.oldest_fetch(conn, area.around), area.zakazy_at),
    )


def _area_score(scores: list[scoring.Score], by: scoring.ScoreKey) -> int:
    best = sorted((by(s) for s in scores), reverse=True)[:TOP]
    return round(100 * sum(best) / len(best)) if best else 0


def _weather_text(warunki: list[Warunki]) -> str:
    """The area's weather in a few words — the means over its tiles."""
    if not warunki:
        return "pogoda nieznana"
    n = len(warunki)
    rain = sum(w.opad_3_14_dni for w in warunki) / n
    wet = sum(scoring.wetness(w) for w in warunki) / n
    temperature = sum(w.temperatura_5_dni for w in warunki) / n
    ground = "mokro" if wet >= 0.8 else "wilgotno" if wet >= 0.5 else "lekko wilgotno" if wet >= 0.2 else "sucho"
    frost = ", po przymrozku" if any(w.mroz_dni_temu is not None for w in warunki) else ""
    return f"{rain:.0f} mm deszczu 3–14 dni wcześniej, {ground}, średnio {temperature:.0f} °C{frost}"
