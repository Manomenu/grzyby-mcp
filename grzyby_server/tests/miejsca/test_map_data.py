from dataclasses import replace

import pytest

from grzyby_server.lasy.model import Obszar, ObszarKind, Wydzielenie
from grzyby_server.miejsca import map_data, scoring
from grzyby_server.miejsca.model import Grzyb, Miesiac

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
WANTED = [Grzyb.BOROWIK, Grzyb.KOZLARZ]


def scores(*stands: Wydzielenie) -> list[scoring.Score]:
    return [scoring.score(w, WANTED, Miesiac.SIERPIEN, 15_000) for w in stands]


def test_the_stands_go_column_by_column_best_first_with_a_score_per_mushroom() -> None:
    weak = replace(STAND, adres_lesny="weak", wiek=150)

    mapa = map_data.build_map(
        scores(weak, STAND), [Obszar(ObszarKind.PARK_NARODOWY, "Park", [["abc"]])], (54.1, 22.9), WANTED, Miesiac.SIERPIEN
    )

    columns = mapa.drzewostany
    assert columns.wiek == [70, 150]
    assert set(columns.wynik) == set(WANTED)
    assert columns.wynik[Grzyb.KOZLARZ][0] > columns.wynik[Grzyb.KOZLARZ][1] > 0
    assert columns.gatunek == ["BRZ", "BRZ"]  # the subspecies dropped, as the profiles know it
    assert len(columns.ksztalt) == len(columns.siedlisko) == 2
    assert mapa.pominiete == 0
    assert mapa.obszary[0].rodzaj == "park_narodowy"
    # The rules travel along: only the mushrooms asked about, and the month scored.
    assert set(mapa.reguly.grzyby) == set(WANTED)
    assert mapa.reguly.miesiac == 8


def test_the_weakest_stands_are_left_off_when_the_budget_runs_out(monkeypatch: pytest.MonkeyPatch) -> None:
    one = len('[["_p~iF~ps|U_ulLnnqC_mqNvxq`@"]]') + 16 + 4 * len(WANTED)
    monkeypatch.setattr(map_data, "BUDGET", 2 * one)
    stands = [replace(STAND, adres_lesny=str(age), wiek=age) for age in (130, 70, 30)]

    mapa = map_data.build_map(scores(*stands), [], (54.1, 22.9), WANTED, Miesiac.SIERPIEN)

    # The 130-year-old stand is the weakest for both mushrooms; it is the one left out.
    assert sorted(mapa.drzewostany.wiek) == [30, 70]
    assert mapa.pominiete == 1
