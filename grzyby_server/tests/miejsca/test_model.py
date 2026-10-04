from urllib.parse import parse_qs, urlparse

from grzyby_server.miejsca.model import Answer, Miejsce, as_text, route_url


def test_the_route_leads_to_the_point_in_google_maps() -> None:
    url = urlparse(route_url(54.051247, 22.965699))

    assert url.netloc == "www.google.com"
    assert parse_qs(url.query) == {"api": ["1"], "destination": ["54.051247,22.965699"]}


def test_the_text_names_the_place_then_the_spots_then_the_notes_and_sources() -> None:
    spot = Miejsce(nazwa="Las sosnowy", lat=54.1, lon=22.9, dlaczego="sosna.", trasa="https://maps.example", adres_lesny="a")
    answer = Answer(szukano_wokol="Suwałki", promien_km=15, miejsca=[spot], uwagi=["zakazy nieaktualne"], zrodla="BDL.")

    assert as_text(answer).split("\n\n") == [
        "Lasy w promieniu 15 km od: Suwałki.",
        "**Las sosnowy** — sosna. [Trasa w Google Maps](https://maps.example)",
        "**Uwaga:** zakazy nieaktualne",
        "_BDL._",
    ]
