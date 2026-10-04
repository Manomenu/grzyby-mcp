import json
from datetime import date
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from grzyby_server.miejsca.model import Answer, DzienPrognozy, Grzyb, Miejsce, Prognoza, as_text, day_text, forecast_text, route_url


def test_the_route_leads_to_the_point_in_google_maps() -> None:
    url = urlparse(route_url(54.051247, 22.965699))

    assert url.netloc == "www.google.com"
    assert parse_qs(url.query) == {"api": ["1"], "destination": ["54.051247,22.965699"]}


def test_the_text_names_the_place_then_the_spots_then_the_notes_and_sources() -> None:
    spot = Miejsce(nazwa="Las sosnowy", lat=54.1, lon=22.9, dlaczego="sosna.", trasa="https://maps.example", adres_lesny="a")
    answer = Answer(
        szukano_wokol="Suwałki", grzyby=["kurka", "koźlarz"], promien_km=15, miejsca=[spot], uwagi=["zakazy nieaktualne"], zrodla="BDL."
    )

    assert as_text(answer).split("\n\n") == [
        "Lasy w promieniu 15 km od: Suwałki — na: kurka, koźlarz.",
        "**Las sosnowy** — sosna. [Trasa w Google Maps](https://maps.example)",
        "**Uwaga:** zakazy nieaktualne",
        "_BDL._",
    ]


def test_the_widget_tests_answer_is_still_a_valid_answer() -> None:
    # grzyby_web/src/miejsca/mapa.e2e.ts feeds the map widget this file; it must keep up with the
    # model, or the browser test would check the widget against data the server no longer sends.
    fixture = Path(__file__).parents[3] / "grzyby_web" / "src" / "miejsca" / "mapa.answer.json"
    data = json.loads(fixture.read_text(encoding="utf-8"))

    assert Answer.model_validate(data).model_dump(mode="json") == data


def test_with_several_mushrooms_the_text_has_a_section_for_all_and_for_each() -> None:
    spot = Miejsce(nazwa="Las", lat=54.1, lon=22.9, dlaczego="x.", trasa="https://maps.example", adres_lesny="a")
    answer = Answer(
        szukano_wokol="Suwałki",
        grzyby=["kurka", "koźlarz"],
        promien_km=15,
        miejsca=[spot],
        miejsca_na_grzyb={Grzyb.KURKA: [spot], Grzyb.KOZLARZ: []},
        uwagi=[],
        zrodla="BDL.",
    )

    sections = [part for part in as_text(answer).split("\n\n") if part.startswith("###")]

    assert sections == ["### Na wszystkie naraz (średnia ocen)", "### Na: kurka", "### Na: koźlarz"]
    assert "(brak miejsc)" in as_text(answer)


def test_the_forecast_text_lists_the_days_and_names_the_best() -> None:
    days = [
        DzienPrognozy(dzien=date(2026, 10, 4), nazwa="niedziela 4.10", za_ile_dni=0, ocena=30, na_grzyb={Grzyb.KURKA: 30}, pogoda="sucho"),
        DzienPrognozy(
            dzien=date(2026, 10, 5), nazwa="poniedziałek 5.10", za_ile_dni=1, ocena=70, na_grzyb={Grzyb.KURKA: 70}, pogoda="mokro"
        ),
    ]
    forecast = Prognoza(
        szukano_wokol="Suwałki", grzyby=["kurka"], promien_km=15, dni=days, najlepszy=date(2026, 10, 5), uwagi=[], zrodla="BDL."
    )

    text = forecast_text(forecast)

    assert "- **poniedziałek 5.10**: 70/100 — mokro" in text
    assert "**Najlepiej: poniedziałek 5.10.**" in text


def test_days_read_as_polish() -> None:
    assert day_text(date(2026, 10, 10)) == "sobota 10.10"
