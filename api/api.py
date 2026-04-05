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

  GET    /api/reports                  – alle Reports
  POST   /api/reports                  – Report anlegen
  GET    /api/reports/{id}             – einzelnen Report abrufen
  PUT    /api/reports/{id}             – Report aktualisieren
  DELETE /api/reports/{id}             – Report löschen
"""
import os
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional

import psycopg2
import psycopg2.extras
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

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


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

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
# Pydantic models – Vehicles
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
# Pydantic models – Reports
# ---------------------------------------------------------------------------

DELIVERY_TYPES = {"mail", "ocpp"}
MAIL_INTERVALS = {"daily", "weekly", "monthly", "yearly"}


class DeliveryIn(BaseModel):
    """Lieferweg-Definition beim Anlegen / Aktualisieren."""
    type: str
    # Mail-spezifisch
    email: Optional[str] = None
    interval: Optional[str] = None   # daily | weekly | monthly | yearly
    # OCPP-spezifisch
    address: Optional[str] = None
    port: Optional[int] = None

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in DELIVERY_TYPES:
            raise ValueError(f"type must be one of: {', '.join(sorted(DELIVERY_TYPES))}")
        return v

    @field_validator("interval")
    @classmethod
    def validate_interval(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in MAIL_INTERVALS:
            raise ValueError(f"interval must be one of: {', '.join(sorted(MAIL_INTERVALS))}")
        return v


class ReportCreate(BaseModel):
    name: str
    vehicle_ids: list[int]
    deliveries: list[DeliveryIn]


class ReportUpdate(BaseModel):
    name: str
    vehicle_ids: list[int]
    deliveries: list[DeliveryIn]


# ---------------------------------------------------------------------------
# Report helper – vollständigen Report aus DB lesen
# ---------------------------------------------------------------------------

def _fetch_report(cur, report_id: int) -> dict:
    """Liest einen Report mit Fahrzeugen und Lieferwegen aus der DB."""
    cur.execute(
        "SELECT id, name, created_at FROM reports WHERE id = %s",
        (report_id,)
    )
    row = cur.fetchone()
    if not row:
        return None

    report = {"id": row[0], "name": row[1], "created_at": row[2]}

    cur.execute("""
        SELECT v.id, v.name
        FROM report_vehicles rv
        JOIN vehicles v ON v.id = rv.vehicle_id
        WHERE rv.report_id = %s
        ORDER BY v.name
    """, (report_id,))
    report["vehicles"] = [{"id": r[0], "name": r[1]} for r in cur.fetchall()]

    cur.execute("""
        SELECT id, type, email, interval, address, port
        FROM report_deliveries
        WHERE report_id = %s
        ORDER BY id
    """, (report_id,))
    report["deliveries"] = [
        {"id": r[0], "type": r[1], "email": r[2],
         "interval": r[3], "address": r[4], "port": r[5]}
        for r in cur.fetchall()
    ]

    return report


def _validate_vehicle_ids(cur, vehicle_ids: list[int]):
    """Wirft HTTPException wenn ein vehicle_id nicht existiert."""
    if not vehicle_ids:
        raise HTTPException(status_code=422, detail="vehicle_ids darf nicht leer sein")
    cur.execute(
        "SELECT id FROM vehicles WHERE id = ANY(%s)",
        (vehicle_ids,)
    )
    found = {r[0] for r in cur.fetchall()}
    missing = set(vehicle_ids) - found
    if missing:
        raise HTTPException(
            status_code=404,
            detail=f"Fahrzeuge nicht gefunden: {sorted(missing)}"
        )


def _validate_deliveries(deliveries: list[DeliveryIn]):
    """Prüft typ-spezifische Pflichtfelder."""
    for d in deliveries:
        if d.type == "mail":
            if not d.email:
                raise HTTPException(status_code=422, detail="Mail-Lieferweg benötigt 'email'")
            if not d.interval:
                raise HTTPException(status_code=422, detail="Mail-Lieferweg benötigt 'interval'")
        elif d.type == "ocpp":
            if not d.address:
                raise HTTPException(status_code=422, detail="OCPP-Lieferweg benötigt 'address'")
            if d.port is None:
                raise HTTPException(status_code=422, detail="OCPP-Lieferweg benötigt 'port'")


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
# DELETE /api/sessions/{session_id}
# ---------------------------------------------------------------------------

@app.delete("/api/sessions/{session_id}", status_code=204)
def delete_session(session_id: int):
    with db_write() as conn:
        cur = conn.cursor()
        # Zugehörige Messwerte mitlöschen (kein FK-Constraint vorhanden)
        cur.execute("""
            DELETE FROM meter_values
            WHERE transaction_id = (
                SELECT transaction_id FROM sessions WHERE id = %s
            )
        """, (session_id,))
        cur.execute("DELETE FROM sessions WHERE id = %s", (session_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Session not found")


# ---------------------------------------------------------------------------
# GET /api/stats
# ---------------------------------------------------------------------------

@app.get("/api/stats")
def get_stats(days: int = Query(14, ge=7, le=90)):
    today = datetime.now(timezone.utc).date()
    since_n    = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    since_30   = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()

    with db() as conn:
        cur = conn.cursor()

        # Energie pro Tag – fehlende Tage auf 0 auffüllen
        cur.execute("""
            SELECT SUBSTRING(start_time, 1, 10) AS day,
                   COALESCE(SUM(energy_kwh), 0) AS kwh
            FROM sessions
            WHERE start_time >= %s AND energy_kwh IS NOT NULL
            GROUP BY day
            ORDER BY day
        """, (since_n,))
        raw = {r[0]: round(float(r[1]), 2) for r in cur.fetchall()}
        energy_per_day = [
            {"date": (today - timedelta(days=days - 1 - i)).isoformat(),
             "kwh":  raw.get((today - timedelta(days=days - 1 - i)).isoformat(), 0.0)}
            for i in range(days)
        ]

        # Energie pro Fahrzeug (gesamt, Top 8)
        cur.execute("""
            SELECT COALESCE(v.name, s.id_tag, 'Unbekannt') AS name,
                   ROUND(SUM(s.energy_kwh)::numeric, 2)    AS kwh
            FROM sessions s
            LEFT JOIN vehicles v ON v.id = s.vehicle_id
            WHERE s.energy_kwh IS NOT NULL
            GROUP BY COALESCE(v.name, s.id_tag, 'Unbekannt')
            ORDER BY kwh DESC
            LIMIT 8
        """)
        energy_per_vehicle = [
            {"name": r[0], "kwh": float(r[1])} for r in cur.fetchall()
        ]

        # Gesamt-Kacheln (letzte 30 Tage, abgeschlossene Sessions)
        cur.execute("""
            SELECT COUNT(*), COALESCE(SUM(energy_kwh), 0)
            FROM sessions
            WHERE start_time >= %s AND stop_time IS NOT NULL
        """, (since_30,))
        row = cur.fetchone()

    return {
        "days":               days,
        "energy_per_day":     energy_per_day,
        "energy_per_vehicle": energy_per_vehicle,
        "total_sessions":     row[0],
        "total_kwh":          round(float(row[1]), 2),
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


# ---------------------------------------------------------------------------
# GET /api/reports
# ---------------------------------------------------------------------------

@app.get("/api/reports")
def get_reports():
    with db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM reports ORDER BY id")
        ids = [r[0] for r in cur.fetchall()]
        return [_fetch_report(cur, rid) for rid in ids]


# ---------------------------------------------------------------------------
# POST /api/reports
# ---------------------------------------------------------------------------

@app.post("/api/reports", status_code=201)
def create_report(body: ReportCreate):
    _validate_deliveries(body.deliveries)
    now = datetime.now(timezone.utc).isoformat()

    with db_write() as conn:
        cur = conn.cursor()
        _validate_vehicle_ids(cur, body.vehicle_ids)

        # Report anlegen
        cur.execute(
            "INSERT INTO reports (name, created_at) VALUES (%s, %s) RETURNING id",
            (body.name, now)
        )
        report_id = cur.fetchone()[0]

        # Fahrzeuge verknüpfen
        cur.executemany(
            "INSERT INTO report_vehicles (report_id, vehicle_id) VALUES (%s, %s)",
            [(report_id, vid) for vid in body.vehicle_ids]
        )

        # Lieferwege anlegen
        cur.executemany(
            """INSERT INTO report_deliveries
                   (report_id, type, email, interval, address, port)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            [(report_id, d.type, d.email, d.interval, d.address, d.port)
             for d in body.deliveries]
        )

    with db() as conn:
        return _fetch_report(conn.cursor(), report_id)


# ---------------------------------------------------------------------------
# GET /api/reports/{report_id}
# ---------------------------------------------------------------------------

@app.get("/api/reports/{report_id}")
def get_report(report_id: int):
    with db() as conn:
        report = _fetch_report(conn.cursor(), report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


# ---------------------------------------------------------------------------
# PUT /api/reports/{report_id}
# ---------------------------------------------------------------------------

@app.put("/api/reports/{report_id}")
def update_report(report_id: int, body: ReportUpdate):
    _validate_deliveries(body.deliveries)

    with db_write() as conn:
        cur = conn.cursor()

        # Existiert der Report?
        cur.execute("SELECT id FROM reports WHERE id = %s", (report_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Report not found")

        _validate_vehicle_ids(cur, body.vehicle_ids)

        # Name aktualisieren
        cur.execute("UPDATE reports SET name = %s WHERE id = %s", (body.name, report_id))

        # Fahrzeuge ersetzen
        cur.execute("DELETE FROM report_vehicles WHERE report_id = %s", (report_id,))
        cur.executemany(
            "INSERT INTO report_vehicles (report_id, vehicle_id) VALUES (%s, %s)",
            [(report_id, vid) for vid in body.vehicle_ids]
        )

        # Lieferwege ersetzen
        cur.execute("DELETE FROM report_deliveries WHERE report_id = %s", (report_id,))
        cur.executemany(
            """INSERT INTO report_deliveries
                   (report_id, type, email, interval, address, port)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            [(report_id, d.type, d.email, d.interval, d.address, d.port)
             for d in body.deliveries]
        )

    with db() as conn:
        return _fetch_report(conn.cursor(), report_id)


# ---------------------------------------------------------------------------
# DELETE /api/reports/{report_id}
# ---------------------------------------------------------------------------

@app.delete("/api/reports/{report_id}", status_code=204)
def delete_report(report_id: int):
    with db_write() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM reports WHERE id = %s", (report_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Report not found")
