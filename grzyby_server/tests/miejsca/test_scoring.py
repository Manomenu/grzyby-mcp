from dataclasses import replace

import pytest

from grzyby_server.lasy.model import Wydzielenie
from grzyby_server.miejsca import scoring

RADIUS_M = 15_000
PINE = Wydzielenie(
    adres_lesny="a", gatunek="SO", wiek=70, siedlisko="BMŚW", powierzchnia_ha=10.0, data_year=2026, lat=54.1, lon=22.9, distance_m=1000
)


def points(w: Wydzielenie) -> float:
    return scoring.score(w, RADIUS_M).points


def test_a_mature_pine_stand_on_fresh_mixed_forest_scores_near_the_top() -> None:
    score = scoring.score(PINE, RADIUS_M)

    assert score.points > 0.9
    assert score.name == "Las sosnowy, 70 lat, 10 ha"
    assert score.reasons[0].startswith("sosna")


def test_a_young_plantation_scores_zero_whatever_else() -> None:
    assert points(replace(PINE, wiek=scoring.MLODNIK - 1)) == 0


def test_an_alder_swamp_scores_far_below_a_pine_forest() -> None:
    assert points(replace(PINE, gatunek="OL", siedlisko="OL")) < points(PINE) / 10


def test_nearer_and_bigger_stands_score_higher() -> None:
    assert points(replace(PINE, distance_m=RADIUS_M)) < points(PINE)
    assert points(replace(PINE, powierzchnia_ha=0.5)) < points(PINE)


def test_a_subspecies_counts_as_its_species_and_unknown_codes_still_score() -> None:
    assert points(replace(PINE, gatunek="BRZ.O")) == points(replace(PINE, gatunek="BRZ"))
    assert points(replace(PINE, gatunek=None, siedlisko=None)) > 0


def test_the_picked_spots_are_the_best_and_at_least_a_kilometre_apart() -> None:
    best = PINE
    neighbour = replace(PINE, adres_lesny="b", lat=PINE.lat + 0.001, distance_m=1100)  # ~110 m from the best, a bit farther out
    elsewhere = replace(PINE, adres_lesny="c", lat=PINE.lat + 0.05, wiek=30)
    young = replace(PINE, adres_lesny="d", lat=PINE.lat - 0.05, wiek=10)

    picked = scoring.pick([scoring.score(w, RADIUS_M) for w in (young, elsewhere, neighbour, best)])

    assert [s.wydzielenie.adres_lesny for s in picked] == ["a", "c"]


@pytest.mark.parametrize(
    ("years", "text"), [(1, "1 rok"), (22, "22 lata"), (12, "12 lat"), (25, "25 lat"), (104, "104 lata"), (113, "113 lat")]
)
def test_ages_read_as_polish(years: int, text: str) -> None:
    assert scoring.age_text(years) == text
