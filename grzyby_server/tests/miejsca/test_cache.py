from datetime import UTC, datetime, timedelta

from psycopg import Connection

from grzyby_server.miejsca import cache
from grzyby_server.miejsca.model import Answer

NOW = datetime(2026, 10, 4, 10, 0, tzinfo=UTC)
ANSWER = Answer(szukano_wokol="Suwałki", grzyby=["borowik"], promien_km=15, miejsca=[], uwagi=["uwaga"], zrodla="BDL")


def test_an_answer_is_read_back_for_an_hour(conn: Connection) -> None:
    cache.put(conn, "q", ANSWER, NOW)

    assert cache.get(conn, "q", NOW + cache.FRESH_FOR - timedelta(seconds=1)) == ANSWER
    assert cache.get(conn, "q", NOW + cache.FRESH_FOR) is None
    assert cache.get(conn, "other", NOW) is None


def test_stale_answers_are_dropped_and_a_new_one_replaces_the_old(conn: Connection) -> None:
    cache.put(conn, "old", ANSWER, NOW)
    cache.put(conn, "q", ANSWER, NOW)
    newer = ANSWER.model_copy(update={"uwagi": []})

    cache.put(conn, "q", newer, NOW + cache.FRESH_FOR)

    assert conn.execute("SELECT query FROM answer_cache").fetchall() == [("q",)]
    assert cache.get(conn, "q", NOW + cache.FRESH_FOR) == newer
