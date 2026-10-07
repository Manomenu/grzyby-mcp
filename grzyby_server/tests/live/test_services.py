"""The real outside services, end to end — the same check the cluster runs every day
(miejsca/live.py, the chart's live-check CronJob), here against the test database: BDL, GDOŚ,
Open-Meteo and Nominatim asked anew about Suwałki and their answers read as production reads them.

Not in the gate (`-m "not live"` in pyproject.toml): it needs the internet and takes ~15 s. By hand
after touching how a service is called: scripts/.internal/live-check.sh.
"""

from datetime import UTC, datetime

import pytest
from psycopg import Connection

from grzyby_server.fetch import get_json
from grzyby_server.miejsca import live

pytestmark = pytest.mark.live


def test_the_services_answer_as_we_read_them(conn: Connection) -> None:
    live.forget(conn)

    assert live.check(conn, get_json, datetime.now(UTC)) == []
