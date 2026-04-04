"""
OCPP REST API
Endpoints:
  GET    /api/active                   – aktive Ladevorgänge
  GET    /api/sessions                 – alle Ladevorgänge (paginiert)
  GET    /api/vehicles                 – alle Fahrzeuge
  POST   /api/vehicles                 – Fahrzeug anlegen
  PUT    /api/vehicles/{id}            – Fahrzeug aktualisieren
  DELETE /api/vehicles/{id}            – Fahrzeug löschen
  PUT    /api/sessions/{id}/vehicle    – Fahrzeug einer Session zuweisen
"""
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional

import psycopg2
import psycopg2.extras
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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
    allow_methods=["*"],
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


@contextmanager
def db_write():
    conn = psycopg2.connect(DSN)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def row_to_dict(cursor, row):
    return {col.name: row[i] for i, col in enumerate(cursor.description)}


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class VehicleCreate(BaseModel):
    name: str
    id_tag: Optional[str] = None
    image_data: Optional[str] = None  # base64 data URL


class VehicleUpdate(BaseModel):
    name: str
    id_tag: Optional[str] = None
    image_data: Optional[str] = None


class SessionVehicleUpdate(BaseModel):
    vehicle_id: Optional[int] = None


# ---------------------------------------------------------------------------
# GET /api/active
# ---------------------------------------------------------------------------

@app.get("/api/active")
def get_active_sessions():
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
                s.vehicle_id,
                v.name              AS vehicle_name,
                cp.id               AS charge_point_id,
                cp.model,
                cp.vendor,
                cp.firmware,
                cp.last_seen
            FROM sessions s
            JOIN charge_points cp ON cp.id = s.charge_point_id
            LEFT JOIN vehicles v ON v.id = s.vehicle_id
            WHERE s.stop_time IS NULL
            ORDER BY s.start_time DESC
        """)
        sessions = [row_to_dict(cur, r) for r in cur.fetchall()]

        now = datetime.now(timezone.utc)

        for s in sessions:
            try:
                start = datetime.fromisoformat(s["start_time"])
                if start.tzinfo is None:
                    start = start.replace(tzinfo=timezone.utc)
                s["duration_seconds"] = int((now - start).total_seconds())
            except Exception:
                s["duration_seconds"] = None

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
    offset = (page - 1) * page_size
    with db() as conn:
        cur = conn.cursor()
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
                s.vehicle_id,
                v.name              AS vehicle_name,
                cp.id               AS charge_point_id,
                cp.model,
                cp.vendor,
                cp.firmware
            FROM sessions s
            JOIN charge_points cp ON cp.id = s.charge_point_id
            LEFT JOIN vehicles v ON v.id = s.vehicle_id
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


# ---------------------------------------------------------------------------
# GET /api/vehicles
# ---------------------------------------------------------------------------

@app.get("/api/vehicles")
def get_vehicles():
    with db() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, name, id_tag, image_data, created_at
            FROM vehicles
            ORDER BY name
        """)
        return [row_to_dict(cur, r) for r in cur.fetchall()]


# ---------------------------------------------------------------------------
# POST /api/vehicles
# ---------------------------------------------------------------------------

@app.post("/api/vehicles", status_code=201)
def create_vehicle(body: VehicleCreate):
    now = datetime.now(timezone.utc).isoformat()
    with db_write() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO vehicles (name, id_tag, image_data, created_at)
            VALUES (%s, %s, %s, %s)
            RETURNING id, name, id_tag, image_data, created_at
        """, (body.name, body.id_tag or None, body.image_data, now))
        return row_to_dict(cur, cur.fetchone())


# ---------------------------------------------------------------------------
# PUT /api/vehicles/{vehicle_id}
# ---------------------------------------------------------------------------

@app.put("/api/vehicles/{vehicle_id}")
def update_vehicle(vehicle_id: int, body: VehicleUpdate):
    with db_write() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE vehicles
            SET name = %s, id_tag = %s, image_data = %s
            WHERE id = %s
            RETURNING id, name, id_tag, image_data, created_at
        """, (body.name, body.id_tag or None, body.image_data, vehicle_id))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Vehicle not found")
        return row_to_dict(cur, row)


# ---------------------------------------------------------------------------
# DELETE /api/vehicles/{vehicle_id}
# ---------------------------------------------------------------------------

@app.delete("/api/vehicles/{vehicle_id}", status_code=204)
def delete_vehicle(vehicle_id: int):
    with db_write() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM vehicles WHERE id = %s", (vehicle_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Vehicle not found")


# ---------------------------------------------------------------------------
# PUT /api/sessions/{session_id}/vehicle
# ---------------------------------------------------------------------------

@app.put("/api/sessions/{session_id}/vehicle")
def assign_vehicle(session_id: int, body: SessionVehicleUpdate):
    with db_write() as conn:
        cur = conn.cursor()
        if body.vehicle_id is not None:
            cur.execute("SELECT id FROM vehicles WHERE id = %s", (body.vehicle_id,))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Vehicle not found")
        cur.execute("UPDATE sessions SET vehicle_id = %s WHERE id = %s",
                    (body.vehicle_id, session_id))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Session not found")
    return {"session_id": session_id, "vehicle_id": body.vehicle_id}
