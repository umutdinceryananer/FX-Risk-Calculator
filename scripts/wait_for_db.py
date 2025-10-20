from __future__ import annotations

import os
import sys
import time
from urllib.parse import urlparse

import psycopg2

TIMEOUT_SECONDS = int(os.getenv("DB_WAIT_TIMEOUT", "30"))
SLEEP_SECONDS = float(os.getenv("DB_WAIT_INTERVAL", "1"))


def parse_database_url(url: str) -> dict[str, int | str]:
    parsed = urlparse(url)
    if parsed.scheme not in {"postgresql", "postgresql+psycopg2", "postgres"}:
        raise ValueError(f"Unsupported database scheme: {parsed.scheme}")

    if parsed.path and parsed.path != "/":
        db_name: str = parsed.path.lstrip("/")
    else:
        db_name = "postgres"

    if parsed.hostname is None:
        host: str = "localhost"
    else:
        host = parsed.hostname

    if parsed.port is None:
        port: int = 5432
    else:
        port = parsed.port

    conn_info: dict[str, int | str] = {
        "dbname": db_name,
        "host": host,
        "port": port,
    }
    if parsed.username is not None:
        conn_info["user"] = parsed.username
    if parsed.password is not None:
        conn_info["password"] = parsed.password
    return conn_info


def wait_for_db() -> None:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        return

    try:
        conn_info = parse_database_url(database_url)
    except ValueError as error:
        print(f"Invalid DATABASE_URL: {error}", file=sys.stderr)
        sys.exit(1)

    deadline = time.time() + TIMEOUT_SECONDS
    while time.time() < deadline:
        try:
            with psycopg2.connect(**conn_info) as connection:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
            print("Database is available.")
            return
        except psycopg2.OperationalError as exc:
            print(f"Database not ready ({exc}); retrying in {SLEEP_SECONDS}s...")
            time.sleep(SLEEP_SECONDS)

    print("Timed out waiting for the database to become available.", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    wait_for_db()
