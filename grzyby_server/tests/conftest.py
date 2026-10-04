"""A real PostgreSQL for the tests that need one.

The tests get a database of their own, created afresh for every run next to the development
one, so running them never touches data you made by hand. Locally a missing server skips
those tests with a hint; in CI (where `CI` is set) it fails them, because there it must exist.
"""

import os
from collections.abc import Iterator

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg import Connection, sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo
from psycopg_pool import ConnectionPool

from grzyby_server import db
from grzyby_server.app import app

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "postgresql://grzyby:grzyby@localhost:5443/grzyby_test")


@pytest.fixture(scope="session")
def database_url() -> str:
    name = str(conninfo_to_dict(TEST_DATABASE_URL)["dbname"])
    try:
        with psycopg.connect(make_conninfo(TEST_DATABASE_URL, dbname="postgres"), autocommit=True, connect_timeout=3) as admin:
            admin.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(name)))
            admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    except psycopg.OperationalError as error:
        if os.environ.get("CI"):
            pytest.fail(f"PostgreSQL unavailable in CI: {error}")
        pytest.skip(f"PostgreSQL unavailable — start it with `just db up` ({error})")
    with psycopg.connect(TEST_DATABASE_URL) as conn:
        db.migrate(conn)
    return TEST_DATABASE_URL


@pytest.fixture(scope="session")
def pool(database_url: str) -> Iterator[ConnectionPool]:
    pool: ConnectionPool = ConnectionPool(database_url, min_size=1, max_size=4)
    with pool:
        yield pool


@pytest.fixture
def conn(pool: ConnectionPool) -> Iterator[Connection]:
    """A connection whose changes are all rolled back at the end, so tests leave no rows behind.
    Code under test may open its own transactions; they nest as savepoints."""
    with pool.connection() as conn, conn.transaction():
        yield conn
        # Ends the transaction by rolling it back; psycopg swallows this exception.
        raise psycopg.Rollback


@pytest.fixture
def client(pool: ConnectionPool) -> Iterator[TestClient]:
    """The app on the test database. A feature's tests empty its tables here first."""

    def test_connection() -> Iterator[Connection]:
        with pool.connection() as conn:
            yield conn

    app.dependency_overrides[db.connection] = test_connection
    yield TestClient(app)
    app.dependency_overrides.clear()
