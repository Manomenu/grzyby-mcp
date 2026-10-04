from grzyby_server.lasy import importer


def test_an_unknown_argument_is_refused_before_anything_is_fetched() -> None:
    assert importer.main(["--everything"]) == 2


def test_the_benchmark_areas_are_the_agreed_ones() -> None:
    # tests/lasy/test_sources.py checks which collections each asks.
    assert set(importer.BENCHMARK) == {"Suwałki", "Chełm", "Gdańsk", "Ponikiew Wielka"}
