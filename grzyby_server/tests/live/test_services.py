"""The real outside services, end to end — what no other test can catch: BDL, GDOŚ, Open-Meteo or
Nominatim changing their answers' shape, or going away. Every other test answers from FakeWeb.

Not in the gate (`-m "not live"` in pyproject.toml): they need the internet and are slow. CI runs
them once a day (.github/workflows/live.yml); by hand: scripts/.internal/live-check.sh. A small
circle at Suwałki, a benchmark area (lasy/importer.py), keeps the load on the services light.
"""

from datetime import UTC, datetime

import pytest
from psycopg import Connection

from grzyby_server.fetch import get_json
from grzyby_server.miejsca.best_day import best_day
from grzyby_server.miejsca.model import Grzyb
from grzyby_server.miejsca.search import Query, search

pytestmark = pytest.mark.live

FAILURES = ("Nie udało się", "nie udało się", "Nie znalazłem")


def test_a_search_near_suwalki_gets_forests_weather_bans_and_a_place(conn: Connection) -> None:
    answer = search(conn, get_json, Query("Suwałki", [Grzyb.PODGRZYBEK, Grzyb.BOROWIK], 8, 3), datetime.now(UTC))

    # Nominatim found the place, BDL sent stands, Open-Meteo the weather, BDL the bans: no note of
    # a service that failed.
    assert answer.szukano_wokol is not None
    assert "Suwałki" in answer.szukano_wokol
    assert not [uwaga for uwaga in answer.uwagi if uwaga.startswith(FAILURES) or "Nie udało się" in uwaga]
    assert answer.mapa is not None
    assert len(answer.mapa.drzewostany.wiek) > 10  # Suwałki itself is a town: ~20 stands within 4 km, many more within 8
    assert answer.mapa.pogoda
    # GDOŚ: the Wigierski Park Narodowy reaches within 8 km of Suwałki — and its buffer zone is not kept.
    assert any("Wigierski" in o.nazwa for o in answer.mapa.obszary)
    assert not any("otulina" in o.nazwa.lower() for o in answer.mapa.obszary)


def test_the_when_tool_gets_real_weather_for_every_day(conn: Connection) -> None:
    forecast = best_day(conn, get_json, Query("Suwałki", [Grzyb.PODGRZYBEK], 4), datetime.now(UTC))

    assert len(forecast.dni) == 6
    assert all(d.pogoda != "pogoda nieznana" for d in forecast.dni)
