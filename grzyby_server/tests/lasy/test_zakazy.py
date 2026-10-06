from datetime import UTC, datetime, timedelta

from psycopg import Connection

from grzyby_server.lasy import sources, store, zakazy
from tests.fake_web import FakeWeb, ban

NOW = datetime(2026, 10, 4, 12, 0, tzinfo=UTC)


def bans(*features: dict[str, object]) -> FakeWeb:
    return FakeWeb({sources.BDL_BANS: {"features": list(features)}})


def test_bans_never_fetched_are_fetched(conn: Connection) -> None:
    assert zakazy.refresh(conn, bans(ban(1, 23.0, 54.0)), NOW) == NOW
    assert conn.execute("SELECT count(*) FROM zakazy_wstepu").fetchone() == (1,)


def test_fresh_bans_are_not_fetched_again(conn: Connection) -> None:
    zakazy.refresh(conn, bans(ban(1, 23.0, 54.0)), NOW)
    web = bans()

    assert zakazy.refresh(conn, web, NOW + zakazy.FRESH_FOR - timedelta(minutes=1)) == NOW
    assert web.calls == []


def test_stale_bans_are_replaced(conn: Connection) -> None:
    zakazy.refresh(conn, bans(ban(1, 23.0, 54.0)), NOW)
    later = NOW + zakazy.FRESH_FOR

    assert zakazy.refresh(conn, bans(ban(2, 23.0, 54.0)), later) == later
    assert conn.execute("SELECT id FROM zakazy_wstepu").fetchall() == [(2,)]


def test_a_failed_refresh_keeps_the_old_bans_and_says_how_old(conn: Connection) -> None:
    zakazy.refresh(conn, bans(ban(1, 23.0, 54.0)), NOW)
    down = FakeWeb({sources.BDL_BANS: OSError("BDL is down")})

    assert zakazy.refresh(conn, down, NOW + timedelta(days=1)) == NOW
    assert conn.execute("SELECT id FROM zakazy_wstepu").fetchall() == [(1,)]
    assert store.fetched_at(conn, zakazy.SOURCE) == NOW


def test_a_ban_until_further_notice_is_kept(conn: Connection) -> None:
    # BDL leaves data_koncowa out of a ban with no end date; it is a ban all the same.
    open_ended = ban(1, 23.0, 54.0)
    open_ended["properties"] = {"objectid": 1, "nazwa_nadl": "Przedbórz"}

    assert zakazy.refresh(conn, bans(open_ended), NOW) == NOW
    assert conn.execute("SELECT id, valid_until FROM zakazy_wstepu").fetchall() == [(1, None)]


def test_a_ban_of_another_shape_keeps_the_old_bans(conn: Connection) -> None:
    # A field gone from BDL must cost a warning about old bans, not the whole answer.
    zakazy.refresh(conn, bans(ban(1, 23.0, 54.0)), NOW)
    odd = ban(2, 23.0, 54.0)
    odd["properties"] = {"nazwa_nadl": "Przedbórz"}

    assert zakazy.refresh(conn, bans(odd), NOW + zakazy.FRESH_FOR) == NOW
    assert conn.execute("SELECT id FROM zakazy_wstepu").fetchall() == [(1,)]
