from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest
from psycopg import Connection
from psycopg_pool import ConnectionPool

from grzyby_server import db
from grzyby_server.db import MigrationChangedError, checksum, migrate


@pytest.fixture
def scratch(pool: ConnectionPool) -> Iterator[Connection]:
    """A connection whose every change lands in a throwaway schema and is rolled back."""
    with pool.connection() as conn, conn.transaction():
        conn.execute("CREATE SCHEMA migration_probe")
        conn.execute("SET LOCAL search_path TO migration_probe")
        yield conn
        # Ends the transaction by rolling it back; psycopg swallows this exception.
        raise psycopg.Rollback


def write(directory: Path, name: str, sql: str) -> Path:
    file = directory / name
    file.write_text(sql)
    return file


def test_new_migrations_run_once_and_are_recorded(scratch: Connection, tmp_path: Path) -> None:
    first = write(tmp_path, "001_a.sql", "CREATE TABLE a (x int);")

    assert migrate(scratch, tmp_path) == ["001_a.sql"]
    assert migrate(scratch, tmp_path) == []
    assert scratch.execute("SELECT checksum FROM schema_migrations").fetchall() == [(checksum(first),)]


def test_an_edited_migration_stops_the_server(scratch: Connection, tmp_path: Path) -> None:
    write(tmp_path, "001_a.sql", "CREATE TABLE a (x int);")
    migrate(scratch, tmp_path)
    write(tmp_path, "001_a.sql", "CREATE TABLE a (x int, y int);")

    with pytest.raises(MigrationChangedError, match=r"001_a\.sql was edited"):
        migrate(scratch, tmp_path)


def test_a_deleted_migration_stops_the_server(scratch: Connection, tmp_path: Path) -> None:
    file = write(tmp_path, "001_a.sql", "CREATE TABLE a (x int);")
    migrate(scratch, tmp_path)
    file.unlink()

    with pytest.raises(MigrationChangedError, match=r"001_a\.sql ran on this database, but its file is gone"):
        migrate(scratch, tmp_path)


def test_migrations_from_before_checksums_get_theirs_recorded(scratch: Connection, tmp_path: Path) -> None:
    file = write(tmp_path, "001_a.sql", "CREATE TABLE a (x int);")
    migrate(scratch, tmp_path)
    scratch.execute("UPDATE schema_migrations SET checksum = NULL")

    assert migrate(scratch, tmp_path) == []
    assert scratch.execute("SELECT checksum FROM schema_migrations").fetchall() == [(checksum(file),)]


def test_a_failing_migration_leaves_nothing_behind(scratch: Connection, tmp_path: Path) -> None:
    write(tmp_path, "001_a.sql", "CREATE TABLE a (x int);")
    write(tmp_path, "002_broken.sql", "CREATE TABLE b (x nonexistent_type);")

    with pytest.raises(psycopg.errors.UndefinedObject):
        migrate(scratch, tmp_path)


def test_the_pool_replaces_a_connection_the_database_killed(database_url: str) -> None:
    # What a database restart (e.g. a new image) does to every idle connection in the pool. The
    # server's pool must hand out a working one, not the dead one — or the next request is a 500.
    with db.new_pool(database_url, max_size=1) as pool:
        with pool.connection() as conn:
            victim = conn.info.backend_pid
        with psycopg.connect(database_url, autocommit=True) as admin:
            admin.execute("SELECT pg_terminate_backend(%s)", (victim,))

        with pool.connection() as conn:
            assert conn.execute("SELECT 1").fetchone() == (1,)
            assert conn.info.backend_pid != victim
