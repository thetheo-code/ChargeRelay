# Theo Bauer · ChargeRelay
"""
database.py – Database connection and schema initialisation for the OCPP server.

Provides a context manager for safe transactional access to PostgreSQL and
runs all CREATE TABLE / ALTER TABLE statements on startup.
"""
import logging
import os
from contextlib import contextmanager

import psycopg2

logger = logging.getLogger("ocpp-server")

# ---------------------------------------------------------------------------
# Connection string
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
# Context manager
# ---------------------------------------------------------------------------

@contextmanager
def db():
    """Open a database connection, commit on success, roll back on error."""
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
# Schema initialisation
# ---------------------------------------------------------------------------

def init_db() -> None:
    """Create all required tables and run pending column migrations."""
    with db() as conn:
        cur = conn.cursor()

        # Core charge-point registry.
        cur.execute("""
            CREATE TABLE IF NOT EXISTS charge_points (
                id          TEXT PRIMARY KEY,
                model       TEXT,
                vendor      TEXT,
                firmware    TEXT,
                last_seen   TEXT
            )
        """)

        # One row per charging session (start ↔ stop pair).
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id              SERIAL PRIMARY KEY,
                charge_point_id TEXT    NOT NULL,
                connector_id    INTEGER NOT NULL,
                transaction_id  INTEGER,
                id_tag          TEXT,
                start_time      TEXT,
                stop_time       TEXT,
                start_meter_wh  INTEGER,
                stop_meter_wh   INTEGER,
                energy_kwh      REAL,
                stop_reason     TEXT
            )
        """)

        # Periodic meter readings received during a session.
        cur.execute("""
            CREATE TABLE IF NOT EXISTS meter_values (
                id              SERIAL PRIMARY KEY,
                charge_point_id TEXT    NOT NULL,
                transaction_id  INTEGER,
                timestamp       TEXT,
                measurand       TEXT,
                value           TEXT,
                unit            TEXT
            )
        """)

        # Known vehicles identified by their RFID tag.
        cur.execute("""
            CREATE TABLE IF NOT EXISTS vehicles (
                id          SERIAL PRIMARY KEY,
                name        TEXT NOT NULL,
                id_tag      TEXT UNIQUE,
                image_data  TEXT,
                created_at  TEXT
            )
        """)

        # Migration: link sessions to vehicles (added after initial schema).
        cur.execute("""
            ALTER TABLE sessions
            ADD COLUMN IF NOT EXISTS vehicle_id INTEGER REFERENCES vehicles(id)
        """)

        # Reports – named bundles of vehicles with scheduled deliveries.
        cur.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id          SERIAL PRIMARY KEY,
                name        TEXT NOT NULL,
                created_at  TEXT NOT NULL
            )
        """)

        # Many-to-many: which vehicles belong to which report.
        cur.execute("""
            CREATE TABLE IF NOT EXISTS report_vehicles (
                report_id   INTEGER NOT NULL REFERENCES reports(id)  ON DELETE CASCADE,
                vehicle_id  INTEGER NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
                PRIMARY KEY (report_id, vehicle_id)
            )
        """)

        # Delivery configurations attached to a report (mail or OCPP relay).
        cur.execute("""
            CREATE TABLE IF NOT EXISTS report_deliveries (
                id          SERIAL  PRIMARY KEY,
                report_id   INTEGER NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
                type        TEXT    NOT NULL,
                email       TEXT,
                interval    TEXT,
                address     TEXT,
                port        INTEGER,
                last_sent   TEXT
            )
        """)

        # Migration: add last_sent for mail delivery tracking.
        cur.execute("""
            ALTER TABLE report_deliveries
            ADD COLUMN IF NOT EXISTS last_sent TEXT
        """)

    logger.info("Database initialised")
