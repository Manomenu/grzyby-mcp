"""PostgreSQL: the connection pool and the schema migrations.

Migrations are numbered SQL files in `migrations/`, applied in name order. Each one runs once
and is recorded in `schema_migrations` with a checksum; the server applies the missing ones
when it starts. A migration is never edited after it ran somewhere: the change goes into a
new file. An edited or deleted one stops the server, because databases that ran the old text
and databases that would run the new one would quietly differ.
"""

import hashlib
from collections.abc import Iterator
from pathlib import Path

from psycopg import Connection
from psycopg_pool import ConnectionPool

from grzyby_server.settings import settings

MIGRATIONS = Path(__file__).with_name("migrations")

# Any constant will do; it only has to be the same in every process that migrates.
MIGRATION_LOCK = 0x6D79_6170  # "myap"

# Opened by the app's lifespan, so importing the app needs no database.
pool = ConnectionPool(settings.database_url, open=False, min_size=1, max_size=5)


class MigrationChangedError(RuntimeError):
    """A migration this database already ran no longer matches its file."""


def connection() -> Iterator[Connection]:
    """FastAPI dependency: a pooled connection, one transaction per request."""
    with pool.connection() as conn:
        yield conn


def checksum(file: Path) -> str:
    return hashlib.sha256(file.read_bytes()).hexdigest()


def migrate(conn: Connection, directory: Path = MIGRATIONS) -> list[str]:
    """Checks the applied migrations against their files, applies the new ones and returns
    their names.

    Everything runs in one transaction under an advisory lock, so two server processes
    starting at once neither apply a migration twice nor see one half applied."""
    files = {file.name: file for file in sorted(directory.glob("*.sql"))}
    with conn.transaction():
        conn.execute("SELECT pg_advisory_xact_lock(%s)", (MIGRATION_LOCK,))
        conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations (name text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())")
        # Databases migrated before checksums existed get theirs recorded on the next start.
        conn.execute("ALTER TABLE schema_migrations ADD COLUMN IF NOT EXISTS checksum text")
        applied: dict[str, str | None] = dict(conn.execute("SELECT name, checksum FROM schema_migrations").fetchall())

        for name, recorded in applied.items():
            file = files.get(name)
            if file is None:
                raise MigrationChangedError(f"migration {name} ran on this database, but its file is gone")
            if recorded is None:
                conn.execute("UPDATE schema_migrations SET checksum = %s WHERE name = %s", (checksum(file), name))
            elif recorded != checksum(file):
                raise MigrationChangedError(f"migration {name} was edited after it ran on this database; put the change in a new migration")

        new = [file for name, file in files.items() if name not in applied]
        for file in new:
            # Bytes, not str: the file may hold several statements and psycopg's typing only
            # accepts literal strings as SQL.
            conn.execute(file.read_bytes())
            conn.execute("INSERT INTO schema_migrations (name, checksum) VALUES (%s, %s)", (file.name, checksum(file)))
    return [file.name for file in new]
