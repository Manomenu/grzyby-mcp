from grzyby_server.lasy import importer


def test_an_unknown_argument_is_refused_before_anything_is_fetched() -> None:
    assert importer.main(["--everything"]) == 2


def test_the_benchmark_areas_lie_in_three_rdlps() -> None:
    # Chełm, Suwałki and Gdańsk (tests/lasy/test_sources.py checks which collection each asks).
    assert set(importer.BENCHMARK) == {"Suwałki", "Chełm", "Gdańsk"}
