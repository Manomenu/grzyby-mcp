from dataclasses import replace

import pytest

from grzyby_server.lasy.model import Obszar, ObszarKind, Wydzielenie
from grzyby_server.miejsca import map_data, scoring
from grzyby_server.miejsca.model import Grzyb, Miesiac
from grzyby_server.pogoda.model import Warunki

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
    tile="541_152",
)
WANTED = [Grzyb.BOROWIK, Grzyb.KOZLARZ]


def scores(*stands: Wydzielenie) -> list[scoring.Score]:
    return [scoring.score(w, WANTED, Miesiac.SIERPIEN, 15_000, None) for w in stands]


def test_the_stands_go_column_by_column_best_first_with_a_score_per_mushroom() -> None:
    weak = replace(STAND, adres_lesny="weak", wiek=150)

    mapa = map_data.build_map(
        scores(weak, STAND),
        [Obszar(ObszarKind.PARK_NARODOWY, "Park", [["abc"]])],
        (54.1, 22.9),
        map_data.rules(WANTED, Miesiac.SIERPIEN),
        {},
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

    mapa = map_data.build_map(scores(*stands), [], (54.1, 22.9), map_data.rules(WANTED, Miesiac.SIERPIEN), {})

    # The 130-year-old stand is the weakest for both mushrooms; it is the one left out.
    assert sorted(mapa.drzewostany.wiek) == [30, 70]
    assert mapa.pominiete == 1


def test_the_weather_of_each_tile_goes_to_the_map() -> None:
    wet = Warunki(temperatura_5_dni=12.0, opad_5_dni=1.0, opad_3_14_dni=30.0, wilgotnosc_gleby=0.28, mroz_dni_temu=None)

    mapa = map_data.build_map(scores(STAND), [], (54.1, 22.9), map_data.rules(WANTED, Miesiac.SIERPIEN), {"541_152": wet, "541_153": None})

    assert set(mapa.pogoda) == {"541_152"}  # a tile without weather is left out
    assert mapa.pogoda["541_152"].opad == 30
    assert mapa.pogoda["541_152"].wilgoc == 1
    assert mapa.kwadrat == (0.1, 0.15)
