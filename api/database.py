# Theo Bauer · ChargeRelay
"""
database.py – Database connection helpers for the REST API.

Provides two context managers (read-only and read-write) and a utility
function for converting psycopg2 rows into plain dictionaries.
"""
import os
from contextlib import contextmanager

import psycopg2
import psycopg2.extras

# ---------------------------------------------------------------------------
# Connection string – assembled from environment variables with safe defaults
# ---------------------------------------------------------------------------

DSN = (
    "host={host} port={port} dbname={dbname} user={user} password={password}"
    .format(
        host=os.environ.get("DB_HOST", "localhost"),
        port=os.environ.get("DB_PORT", "5432"),
        dbname=os.environ.get("DB_NAME", "ocpp"),
        user=os.environ.get("DB_USER", "ocpp"),
        password=os.environ.get("DB_PASSWORD", "ocpp"),
    )
)


# ---------------------------------------------------------------------------
# Context managers
# ---------------------------------------------------------------------------

@contextmanager
def db():
    """Open a read-only database connection and close it when done."""
    conn = psycopg2.connect(DSN)
    conn.set_session(readonly=True, autocommit=True)
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def db_write():
    """Open a read-write connection, commit on success, roll back on error."""
    conn = psycopg2.connect(DSN)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def row_to_dict(cursor, row: tuple) -> dict:
    """Convert a single psycopg2 result row into a column-keyed dictionary."""
    return {col.name: row[i] for i, col in enumerate(cursor.description)}
