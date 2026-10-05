"""Finished answers for an hour: the same question again — same place, mushrooms, radius and number
of spots, the same day — is read back instead of worked out again.

Only complete answers are kept (search.py decides): one with a note about a service that did not
answer would repeat that note for an hour after the service is back.
"""

from datetime import datetime, timedelta

from psycopg import Connection

from grzyby_server.miejsca.model import Answer

FRESH_FOR = timedelta(hours=1)


def get(conn: Connection, query: str, now: datetime) -> Answer | None:
    row: tuple[str] | None = conn.execute(
        "SELECT answer FROM answer_cache WHERE query = %s AND created_at > %s", (query, now - FRESH_FOR)
    ).fetchone()
    return Answer.model_validate_json(row[0]) if row else None


def put(conn: Connection, query: str, answer: Answer, now: datetime) -> None:
    # Stale answers go on every write, so the table holds about an hour of questions.
    conn.execute("DELETE FROM answer_cache WHERE created_at <= %s", (now - FRESH_FOR,))
    conn.execute(
        "INSERT INTO answer_cache (query, answer, created_at) VALUES (%s, %s, %s)"
        " ON CONFLICT (query) DO UPDATE SET answer = excluded.answer, created_at = excluded.created_at",
        (query, answer.model_dump_json(), now),
    )
