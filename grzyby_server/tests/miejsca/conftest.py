from collections.abc import Iterator

import pytest
from psycopg_pool import ConnectionPool

from grzyby_server.miejsca import geocoding


@pytest.fixture(autouse=True)
def no_waiting_for_nominatim(monkeypatch: pytest.MonkeyPatch) -> None:
    """The fake Nominatim needs no second between questions; tests of the throttle make their own."""
    monkeypatch.setattr(geocoding, "NOMINATIM_TURNS", geocoding.Throttle(0, max_wait=0))


@pytest.fixture
def clean_tables(pool: ConnectionPool) -> Iterator[None]:
    """For tests that go through the server's own connection, which commits (the MCP tools, the
    web API): empty the feature's tables afterwards, so other tests find them as they expect."""
    yield
    with pool.connection() as conn:
        conn.execute(
            "TRUNCATE wydzielenia, obszary_chronione, fetched_tiles, geocoding_cache, fetches, zakazy_wstepu, pogoda, weather_fetches,"
            " answer_cache"
        )
