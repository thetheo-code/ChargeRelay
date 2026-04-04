"""
OCPP REST API
Endpoints:
  GET /api/active           – aktive Ladevorgänge (stop_time IS NULL)
  GET /api/sessions         – abgeschlossene & laufende Ladevorgänge (paginiert)
"""
import os
from contextlib import contextmanager
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

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

app = FastAPI(title="OCPP API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@contextmanager
def db():
    conn = psycopg2.connect(DSN)
    conn.set_session(readonly=True, autocommit=True)
    try:
        yield conn
    finally:
        conn.close()


def row_to_dict(cursor, row):
    return {col.name: row[i] for i, col in enumerate(cursor.description)}


# ---------------------------------------------------------------------------
# GET /api/active
# ---------------------------------------------------------------------------

@app.get("/api/active")
def get_active_sessions():
    """Alle aktuell laufenden Ladevorgänge mit Charge-Point-Infos und
    letztem Messwert pro Messgröße."""
    with db() as conn:
        cur = conn.cursor()

        cur.execute("""
            SELECT
                s.id                AS session_id,
                s.connector_id,
                s.transaction_id,
                s.id_tag,
                s.start_time,
                s.start_meter_wh,
                cp.id               AS charge_point_id,
                cp.model,
                cp.vendor,
                cp.firmware,
                cp.last_seen
            FROM sessions s
            JOIN charge_points cp ON cp.id = s.charge_point_id
            WHERE s.stop_time IS NULL
            ORDER BY s.start_time DESC
        """)
        sessions = [row_to_dict(cur, r) for r in cur.fetchall()]

        now = datetime.now(timezone.utc)

        for s in sessions:
            # Laufzeit berechnen (Sekunden)
            try:
                start = datetime.fromisoformat(s["start_time"])
                if start.tzinfo is None:
                    start = start.replace(tzinfo=timezone.utc)
                s["duration_seconds"] = int((now - start).total_seconds())
            except Exception:
                s["duration_seconds"] = None

            # Letzten Messwert je Messgröße laden
            if s["transaction_id"] is not None:
                cur.execute("""
                    SELECT DISTINCT ON (measurand)
                        measurand, value, unit, timestamp
                    FROM meter_values
                    WHERE transaction_id = %s
                    ORDER BY measurand, timestamp DESC
                """, (s["transaction_id"],))
                s["latest_meter_values"] = [row_to_dict(cur, r) for r in cur.fetchall()]
            else:
                s["latest_meter_values"] = []

    return sessions


# ---------------------------------------------------------------------------
# GET /api/sessions
# ---------------------------------------------------------------------------

@app.get("/api/sessions")
def get_sessions(
    page: int = Query(1, ge=1, description="Seitennummer (ab 1)"),
    page_size: int = Query(20, ge=1, le=100, description="Einträge pro Seite"),
):
    """Paginierte Liste aller Ladevorgänge (neueste zuerst)."""
    offset = (page - 1) * page_size

    with db() as conn:
        cur = conn.cursor()

        # Gesamtanzahl
        cur.execute("SELECT COUNT(*) FROM sessions")
        total = cur.fetchone()[0]

        cur.execute("""
            SELECT
                s.id                AS session_id,
                s.connector_id,
                s.transaction_id,
                s.id_tag,
                s.start_time,
                s.stop_time,
                s.start_meter_wh,
                s.stop_meter_wh,
                s.energy_kwh,
                s.stop_reason,
                cp.id               AS charge_point_id,
                cp.model,
                cp.vendor,
                cp.firmware
            FROM sessions s
            JOIN charge_points cp ON cp.id = s.charge_point_id
            ORDER BY s.start_time DESC
            LIMIT %s OFFSET %s
        """, (page_size, offset))
        sessions = [row_to_dict(cur, r) for r in cur.fetchall()]

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
        "sessions": sessions,
    }
