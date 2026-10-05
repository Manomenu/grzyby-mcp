import pytest

from grzyby_server.miejsca import geocoding


@pytest.fixture(autouse=True)
def no_waiting_for_nominatim(monkeypatch: pytest.MonkeyPatch) -> None:
    """The fake Nominatim needs no second between questions; tests of the throttle make their own."""
    monkeypatch.setattr(geocoding, "NOMINATIM_TURNS", geocoding.Throttle(0, max_wait=0))
