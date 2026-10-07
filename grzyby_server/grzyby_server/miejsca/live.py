"""The real outside services, checked once a day from where production runs — the chart's CronJob
(templates/live-check.yaml). The only check that notices BDL, GDOŚ, Open-Meteo or Nominatim
changing their answers' shape, or turning us away; every test answers from a fake. GitHub's
runners cannot do it: in October 2026 BDL or GDOŚ began refusing them (403) while answering us.

It asks what users ask — a search near Suwałki, and the days ahead — through the production code
and database, inside a transaction that is rolled back: first the database forgets what it knows
of the place, so every service is asked anew; at the end nothing of it stays. Problems go to the
project's Discord channel; without a webhook (a laptop) to the log and the exit code only.

The load is a first question about a new area, once a day: ~4 tiles of BDL stands and GDOŚ areas
(a small circle), the country's bans (which production fetches every 4 hours anyway), one Nominatim
lookup and one Open-Meteo call — the second question reuses all of it. No retry when it fails.

By hand on the cluster: kubectl -n grzyby create job --from=cronjob/grzyby-live-check grzyby-live-check-now
Locally the same check is the live tests (tests/live, scripts/.internal/live-check.sh).
"""

import json
import logging
import sys
from datetime import UTC, datetime
from urllib.request import Request, urlopen

import psycopg
from psycopg import Connection

from grzyby_server.fetch import USER_AGENT, GetJson, get_json
from grzyby_server.lasy import zakazy
from grzyby_server.lasy.importer import BENCHMARK, BENCHMARK_RADIUS_M
from grzyby_server.lasy.model import tiles_around
from grzyby_server.miejsca.best_day import best_day
from grzyby_server.miejsca.model import Grzyb
from grzyby_server.miejsca.search import Query, search
from grzyby_server.settings import settings

log = logging.getLogger(__name__)

PLACE = "Suwałki"  # a benchmark area (lasy/importer.py): forests, a national park, a town
RADIUS_KM = 8  # small, to keep the load on the services light: ~4 tiles
# The notes an answer carries when a service failed, anywhere in the sentence.
FAILURES = ("nie udało się", "nie znalazłem")


def forget(conn: Connection) -> None:
    """Makes the next search ask every service anew about PLACE. Only ever inside the check's
    transaction, which is rolled back: other requests keep seeing the stored data meanwhile."""
    lat, lon = BENCHMARK[PLACE]
    tiles = [tile.id for tile in tiles_around(lat, lon, BENCHMARK_RADIUS_M)]
    conn.execute("DELETE FROM answer_cache")
    conn.execute("DELETE FROM geocoding_cache WHERE query = %s", (PLACE.lower(),))
    conn.execute("DELETE FROM fetches WHERE source = %s", (zakazy.SOURCE,))
    conn.execute("DELETE FROM fetched_tiles WHERE tile = ANY(%s)", (tiles,))
    conn.execute("DELETE FROM weather_fetches WHERE tile = ANY(%s)", (tiles,))


def check(conn: Connection, get_json: GetJson, now: datetime) -> list[str]:
    """What is wrong with the services, in words; empty when all is well."""
    problems: list[str] = []
    answer = search(conn, get_json, Query(PLACE, [Grzyb.PODGRZYBEK, Grzyb.BOROWIK], RADIUS_KM, 3), now)
    if answer.szukano_wokol is None or PLACE not in answer.szukano_wokol:
        problems.append(f"Nominatim: nie znalazł „{PLACE}” ({answer.szukano_wokol})")
    problems += [f"uwaga w odpowiedzi: {uwaga}" for uwaga in answer.uwagi if any(f in uwaga.lower() for f in FAILURES)]
    mapa = answer.mapa
    if mapa is None:
        problems.append("brak mapy w odpowiedzi")
    else:
        # The town itself: ~20 stands within 4 km, many more within 8.
        if len(mapa.drzewostany.wiek) <= 10:
            problems.append(f"BDL: tylko {len(mapa.drzewostany.wiek)} drzewostanów w {RADIUS_KM} km od {PLACE}")
        if not mapa.pogoda:
            problems.append("Open-Meteo: brak pogody na mapie")
        # The Wigierski Park Narodowy reaches within 8 km — and its buffer zone is not kept.
        if not any("Wigierski" in o.nazwa for o in mapa.obszary):
            problems.append("GDOŚ: brak Wigierskiego Parku Narodowego")
        if any("otulina" in o.nazwa.lower() for o in mapa.obszary):
            problems.append("GDOŚ: otulina parku wśród obszarów")
    forecast = best_day(conn, get_json, Query(PLACE, [Grzyb.PODGRZYBEK], 4), now)
    if len(forecast.dni) != 6 or any(d.pogoda == "pogoda nieznana" for d in forecast.dni):
        problems.append("Open-Meteo: prognoza na 6 dni niepełna")
    return problems


def message(problems: list[str]) -> str:
    """The Discord message: what broke, within Discord's 2000 characters."""
    text = ":x: **grzyby** — kontrola usług z klastra: BDL, GDOŚ, Open-Meteo albo Nominatim odpowiadają inaczej niż zwykle\n"
    text += "\n".join(f"- {p}" for p in problems)
    return text if len(text) <= 1900 else text[:1899] + "…"


def tell_discord(webhook: str, text: str) -> None:
    body = json.dumps({"content": text}).encode()
    # Discord's edge refuses Python's default User-Agent.
    request = Request(webhook, data=body, headers={"Content-Type": "application/json", "User-Agent": USER_AGENT})  # noqa: S310 — the webhook is an https URL from our own Secret
    with urlopen(request, timeout=20):  # noqa: S310 — as above
        pass


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    try:
        with psycopg.connect(settings.database_url) as conn, conn.transaction(force_rollback=True):
            forget(conn)
            problems = check(conn, get_json, datetime.now(UTC))
    except Exception as error:  # noqa: BLE001 — a crash is one more problem to report, not a traceback nobody reads
        problems = [f"kontrola się wywróciła: {error!r}"]
    for problem in problems:
        log.warning("%s", problem)
    if problems and settings.discord_webhook:
        tell_discord(settings.discord_webhook, message(problems))
    log.info("services: %s", "problems" if problems else "ok")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
