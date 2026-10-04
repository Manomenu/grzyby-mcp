from dataclasses import replace

import pytest

from grzyby_server.lasy.model import Wydzielenie
from grzyby_server.miejsca import scoring
from grzyby_server.miejsca.model import Grzyb, Miesiac

RADIUS_M = 15_000
AUGUST, OCTOBER, JULY, JANUARY, MAY, NOVEMBER = (
    Miesiac.SIERPIEN,
    Miesiac.PAZDZIERNIK,
    Miesiac.LIPIEC,
    Miesiac.STYCZEN,
    Miesiac.MAJ,
    Miesiac.LISTOPAD,
)
PINE = Wydzielenie(
    adres_lesny="a",
    gatunek="SO",
    wiek=70,
    siedlisko="BMŚW",
    powierzchnia_ha=10.0,
    data_year=2026,
    lat=54.1,
    lon=22.9,
    distance_m=1000,
    shape=[],
)


def season(g: Grzyb, month: Miesiac) -> str:
    return scoring.score(PINE, [g], month, RADIUS_M).reasons[g][-1]


def points(w: Wydzielenie, g: Grzyb, month: Miesiac = AUGUST) -> float:
    return scoring.score(w, [g], month, RADIUS_M).points


def test_a_mature_pine_forest_in_august_is_near_the_top_for_a_cep() -> None:
    score = scoring.score(PINE, [Grzyb.BOROWIK], AUGUST, RADIUS_M)

    assert score.points > 0.8
    assert score.name == "Las sosnowy, 70 lat, 10 ha"
    assert score.facts == ["sosna", "bór mieszany świeży", "dojrzały drzewostan (70 lat)"]
    assert score.reasons[Grzyb.BOROWIK] == [
        "sosna — bardzo dobrze dla borowika",
        "bór mieszany świeży — bardzo dobrze",
        "dojrzały drzewostan (70 lat) — bardzo dobrze",
        "sierpień: szczyt sezonu",
    ]


def test_each_mushroom_has_its_trees() -> None:
    birch = replace(PINE, gatunek="BRZ")

    assert points(birch, Grzyb.KOZLARZ) > 3 * points(PINE, Grzyb.KOZLARZ)
    assert points(birch, Grzyb.MASLAK) == 0  # no birch in a maślak's list


def test_young_pine_suits_a_maslak_and_not_a_cep() -> None:
    young = replace(PINE, wiek=12)

    assert points(young, Grzyb.MASLAK, OCTOBER) > 0.7
    assert points(young, Grzyb.BOROWIK) < 0.1


def test_the_month_counts() -> None:
    assert points(replace(PINE, wiek=15), Grzyb.RYDZ, OCTOBER) > 0.8  # a young pine plantation
    assert points(PINE, Grzyb.RYDZ, JULY) == 0  # from August
    assert points(PINE, Grzyb.KURKA, JANUARY) == 0
    assert season(Grzyb.KURKA, NOVEMBER) == "listopad: koniec sezonu"
    assert season(Grzyb.BOROWIK, MAY) == "maj: początek sezonu"
    assert season(Grzyb.RYDZ, JULY) == "lipiec: poza sezonem"


def test_asked_about_several_a_stand_scores_for_each_and_on_average() -> None:
    score = scoring.score(replace(PINE, gatunek="BRZ", siedlisko="LMW", wiek=30), [Grzyb.BOROWIK, Grzyb.KOZLARZ], AUGUST, RADIUS_M)

    assert score.per_grzyb[Grzyb.KOZLARZ] > score.per_grzyb[Grzyb.BOROWIK]
    assert score.points == pytest.approx((score.per_grzyb[Grzyb.KOZLARZ] + score.per_grzyb[Grzyb.BOROWIK]) / 2)
    assert score.reasons[Grzyb.KOZLARZ][0] == "brzoza — bardzo dobrze dla koźlarza"


def test_spots_can_be_picked_for_the_average_or_for_one_mushroom() -> None:
    birch = replace(PINE, adres_lesny="birch", gatunek="BRZ", siedlisko="LMW", wiek=30, lat=PINE.lat + 0.05)
    scores = [scoring.score(w, [Grzyb.BOROWIK, Grzyb.KOZLARZ], AUGUST, RADIUS_M) for w in (PINE, birch)]

    assert [s.wydzielenie.adres_lesny for s in scoring.pick(scores, 1, by=lambda s: s.per_grzyb[Grzyb.KOZLARZ])] == ["birch"]
    assert [s.wydzielenie.adres_lesny for s in scoring.pick(scores, 1, by=lambda s: s.per_grzyb[Grzyb.BOROWIK])] == ["a"]


def test_an_unknown_site_type_or_tree_still_has_a_score() -> None:
    assert points(replace(PINE, siedlisko=None), Grzyb.BOROWIK) > 0
    assert points(replace(PINE, gatunek="XYZ"), Grzyb.BOROWIK) == 0


def test_season_helpers() -> None:
    assert not scoring.in_season([Grzyb.KURKA, Grzyb.RYDZ], JANUARY)
    assert scoring.in_season([Grzyb.KURKA, Grzyb.RYDZ], OCTOBER)
    assert scoring.next_season(Grzyb.KURKA, JANUARY) == 6


def test_the_picked_spots_are_the_best_and_at_least_a_kilometre_apart() -> None:
    best = PINE
    neighbour = replace(PINE, adres_lesny="b", lat=PINE.lat + 0.001, distance_m=1100)  # ~110 m from the best, a bit farther out
    elsewhere = replace(PINE, adres_lesny="c", lat=PINE.lat + 0.05, wiek=30)
    young = replace(PINE, adres_lesny="d", lat=PINE.lat - 0.05, wiek=10)

    picked = scoring.pick([scoring.score(w, [Grzyb.BOROWIK], AUGUST, RADIUS_M) for w in (young, elsewhere, neighbour, best)])

    assert [s.wydzielenie.adres_lesny for s in picked] == ["a", "c", "d"]


@pytest.mark.parametrize(
    ("years", "text"), [(1, "1 rok"), (22, "22 lata"), (12, "12 lat"), (25, "25 lat"), (104, "104 lata"), (113, "113 lat")]
)
def test_ages_read_as_polish(years: int, text: str) -> None:
    assert scoring.age_text(years) == text
