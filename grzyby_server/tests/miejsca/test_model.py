from urllib.parse import parse_qs, urlparse

from grzyby_server.miejsca.model import trasa


def test_trasa_leads_to_the_point_in_google_maps() -> None:
    url = urlparse(trasa(54.051247, 22.965699))

    assert url.netloc == "www.google.com"
    assert parse_qs(url.query) == {"api": ["1"], "destination": ["54.051247,22.965699"]}
