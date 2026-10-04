from dataclasses import replace

import pytest

from grzyby_server.lasy.model import Obszar, ObszarKind, Wydzielenie
from grzyby_server.miejsca import map_data, scoring

STAND = Wydzielenie(
    adres_lesny="a",
    gatunek="BRZ.O",
    wiek=70,
    siedlisko="BMŚW",
    powierzchnia_ha=10.0,
    data_year=2026,
    lat=54.1,
    lon=22.9,
    distance_m=1000,
    shape=[["_p~iF~ps|U_ulLnnqC_mqNvxq`@"]],
)


def scores(*stands: Wydzielenie) -> list[scoring.Score]:
    return [scoring.score(w, 15_000) for w in stands]


def test_the_stands_go_column_by_column_best_first() -> None:
    weak = replace(STAND, adres_lesny="weak", wiek=25)

    mapa = map_data.build_map(scores(weak, STAND), [Obszar(ObszarKind.PARK_NARODOWY, "Park", [["abc"]])], 54.1, 22.9)

    columns = mapa.drzewostany
    assert columns.wiek == [70, 25]
    assert columns.wynik[0] > columns.wynik[1] > 0
    assert columns.gatunek == ["BRZ", "BRZ"]  # the subspecies dropped, as the rules know it
    assert len(columns.ksztalt) == len(columns.siedlisko) == 2
    assert mapa.pominiete == 0
    assert mapa.obszary[0].rodzaj == "park_narodowy"
    assert "SO" in mapa.reguly.gatunki


def test_the_weakest_stands_are_left_off_when_the_budget_runs_out(monkeypatch: pytest.MonkeyPatch) -> None:
    one = len('[["_p~iF~ps|U_ulLnnqC_mqNvxq`@"]]') + map_data.ATTRIBUTES_SIZE
    monkeypatch.setattr(map_data, "BUDGET", 2 * one)
    stands = [replace(STAND, adres_lesny=str(age), wiek=age) for age in (30, 70, 50)]

    mapa = map_data.build_map(scores(*stands), [], 54.1, 22.9)

    assert mapa.drzewostany.wiek == [70, 50]
    assert mapa.pominiete == 1
