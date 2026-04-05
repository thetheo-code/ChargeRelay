# Theo Bauer · ChargeRelay
"""
routers/reports.py – CRUD endpoints for charge reports.

Routes
------
GET    /api/reports        Return all reports with their vehicles and deliveries.
POST   /api/reports        Create a new report.
GET    /api/reports/{id}   Return a single report.
PUT    /api/reports/{id}   Replace a report's configuration.
DELETE /api/reports/{id}   Delete a report and all its deliveries.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from database import db, db_write
from models import DeliveryIn, ReportCreate, ReportUpdate

router = APIRouter(prefix="/api")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _fetch_report(cur, report_id: int) -> dict | None:
    """Load a full report (including vehicles and deliveries) from the database."""
    cur.execute(
        "SELECT id, name, created_at FROM reports WHERE id = %s",
        (report_id,),
    )
    row = cur.fetchone()
    if not row:
        return None

    report = {"id": row[0], "name": row[1], "created_at": row[2]}

    # Attach all vehicles linked to this report.
    cur.execute("""
        SELECT v.id, v.name
        FROM report_vehicles rv
        JOIN vehicles v ON v.id = rv.vehicle_id
        WHERE rv.report_id = %s
        ORDER BY v.name
    """, (report_id,))
    report["vehicles"] = [{"id": r[0], "name": r[1]} for r in cur.fetchall()]

    # Attach all delivery configurations for this report.
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


def _validate_vehicle_ids(cur, vehicle_ids: list[int]) -> None:
    """Raise HTTP 404 if any of the given vehicle IDs do not exist in the database."""
    if not vehicle_ids:
        raise HTTPException(status_code=422, detail="vehicle_ids must not be empty")
    cur.execute("SELECT id FROM vehicles WHERE id = ANY(%s)", (vehicle_ids,))
    found   = {r[0] for r in cur.fetchall()}
    missing = set(vehicle_ids) - found
    if missing:
        raise HTTPException(
            status_code=404,
            detail=f"Vehicles not found: {sorted(missing)}",
        )


def _validate_deliveries(deliveries: list[DeliveryIn]) -> None:
    """Raise HTTP 422 if any delivery is missing its type-specific required fields."""
    for d in deliveries:
        if d.type == "mail":
            if not d.email:
                raise HTTPException(status_code=422, detail="Mail delivery requires 'email'")
            if not d.interval:
                raise HTTPException(status_code=422, detail="Mail delivery requires 'interval'")
        elif d.type == "ocpp":
            if not d.address:
                raise HTTPException(status_code=422, detail="OCPP delivery requires 'address'")
            if d.port is None:
                raise HTTPException(status_code=422, detail="OCPP delivery requires 'port'")


# ---------------------------------------------------------------------------
# GET /api/reports
# ---------------------------------------------------------------------------

@router.get("/reports")
def get_reports():
    """Return all reports, each with their full vehicle and delivery lists."""
    with db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM reports ORDER BY id")
        ids = [r[0] for r in cur.fetchall()]
        return [_fetch_report(cur, rid) for rid in ids]


# ---------------------------------------------------------------------------
# POST /api/reports
# ---------------------------------------------------------------------------

@router.post("/reports", status_code=201)
def create_report(body: ReportCreate):
    """Create a new report with vehicles and delivery configurations."""
    _validate_deliveries(body.deliveries)
    now = datetime.now(timezone.utc).isoformat()

    with db_write() as conn:
        cur = conn.cursor()
        _validate_vehicle_ids(cur, body.vehicle_ids)

        # Insert the report record.
        cur.execute(
            "INSERT INTO reports (name, created_at) VALUES (%s, %s) RETURNING id",
            (body.name, now),
        )
        report_id = cur.fetchone()[0]

        # Link the selected vehicles.
        cur.executemany(
            "INSERT INTO report_vehicles (report_id, vehicle_id) VALUES (%s, %s)",
            [(report_id, vid) for vid in body.vehicle_ids],
        )

        # Insert all delivery configurations.
        cur.executemany(
            """INSERT INTO report_deliveries
                   (report_id, type, email, interval, address, port)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            [(report_id, d.type, d.email, d.interval, d.address, d.port)
             for d in body.deliveries],
        )

    # Re-fetch and return the fully assembled report.
    with db() as conn:
        return _fetch_report(conn.cursor(), report_id)


# ---------------------------------------------------------------------------
# GET /api/reports/{report_id}
# ---------------------------------------------------------------------------

@router.get("/reports/{report_id}")
def get_report(report_id: int):
    """Return a single report by ID."""
    with db() as conn:
        report = _fetch_report(conn.cursor(), report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


# ---------------------------------------------------------------------------
# PUT /api/reports/{report_id}
# ---------------------------------------------------------------------------

@router.put("/reports/{report_id}")
def update_report(report_id: int, body: ReportUpdate):
    """Replace all mutable fields of a report (name, vehicles, deliveries)."""
    _validate_deliveries(body.deliveries)

    with db_write() as conn:
        cur = conn.cursor()

        # Ensure the report exists before modifying anything.
        cur.execute("SELECT id FROM reports WHERE id = %s", (report_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Report not found")

        _validate_vehicle_ids(cur, body.vehicle_ids)

        cur.execute("UPDATE reports SET name = %s WHERE id = %s", (body.name, report_id))

        # Replace the vehicle list by removing and re-inserting.
        cur.execute("DELETE FROM report_vehicles WHERE report_id = %s", (report_id,))
        cur.executemany(
            "INSERT INTO report_vehicles (report_id, vehicle_id) VALUES (%s, %s)",
            [(report_id, vid) for vid in body.vehicle_ids],
        )

        # Replace all delivery entries.
        cur.execute("DELETE FROM report_deliveries WHERE report_id = %s", (report_id,))
        cur.executemany(
            """INSERT INTO report_deliveries
                   (report_id, type, email, interval, address, port)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            [(report_id, d.type, d.email, d.interval, d.address, d.port)
             for d in body.deliveries],
        )

    with db() as conn:
        return _fetch_report(conn.cursor(), report_id)


# ---------------------------------------------------------------------------
# DELETE /api/reports/{report_id}
# ---------------------------------------------------------------------------

@router.delete("/reports/{report_id}", status_code=204)
def delete_report(report_id: int):
    """Delete a report and cascade-remove all its vehicles and deliveries."""
    with db_write() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM reports WHERE id = %s", (report_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Report not found")
