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
import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

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


# ---------------------------------------------------------------------------
# GET /api/reports/{report_id}/download
# ---------------------------------------------------------------------------

# CSV column headers indexed by language code.
_CSV_HEADERS: dict[str, list[str]] = {
    "de": ["Datum", "Start", "Ende", "Dauer (min)", "Ladestation",
           "Connector", "Fahrzeug", "RFID-Tag", "Energie (kWh)", "Abbruchgrund"],
    "en": ["Date", "Start", "End", "Duration (min)", "Charge Point",
           "Connector", "Vehicle", "RFID Tag", "Energy (kWh)", "Stop Reason"],
}


@router.get("/reports/{report_id}/download")
def download_report_csv(
    report_id: int,
    from_date: str = Query(..., description="Start date inclusive (YYYY-MM-DD)"),
    to_date:   str = Query(..., description="End date inclusive (YYYY-MM-DD)"),
    vehicle_ids: str | None = Query(
        None,
        description="Comma-separated vehicle IDs to include. "
                    "Defaults to all vehicles in the report.",
    ),
    lang: str = Query("de", description="Column header language: 'de' or 'en'"),
):
    """Return a CSV file containing all completed sessions for the report's
    vehicles within the given date range."""
    with db() as conn:
        cur = conn.cursor()

        # Verify the report exists.
        cur.execute("SELECT id, name FROM reports WHERE id = %s", (report_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Report not found")
        report_name = row[1]

        # Determine which vehicles to include.
        if vehicle_ids:
            try:
                vid_list = [int(v.strip()) for v in vehicle_ids.split(",") if v.strip()]
            except ValueError:
                raise HTTPException(status_code=422, detail="vehicle_ids must be integers")
        else:
            # Default: all vehicles linked to the report.
            cur.execute(
                "SELECT vehicle_id FROM report_vehicles WHERE report_id = %s",
                (report_id,),
            )
            vid_list = [r[0] for r in cur.fetchall()]

        if not vid_list:
            raise HTTPException(status_code=422, detail="No vehicles selected")

        # Extend to_date to end-of-day so the upper bound is inclusive.
        try:
            from_dt = f"{from_date}T00:00:00"
            to_dt   = f"{to_date}T23:59:59"
        except Exception:
            raise HTTPException(status_code=422, detail="Invalid date format, use YYYY-MM-DD")

        # Fetch completed sessions within the date range for the selected vehicles.
        cur.execute("""
            SELECT
                s.start_time,
                s.stop_time,
                cp.id           AS charge_point_id,
                cp.model,
                s.connector_id,
                v.name          AS vehicle_name,
                s.authorized_id_tag,
                s.id_tag,
                s.energy_kwh,
                s.stop_reason
            FROM sessions s
            JOIN  charge_points cp ON cp.id = s.charge_point_id
            LEFT JOIN vehicles  v  ON v.id  = s.vehicle_id
            WHERE s.vehicle_id = ANY(%s)
              AND s.stop_time IS NOT NULL
              AND s.start_time >= %s
              AND s.start_time <= %s
            ORDER BY s.start_time ASC
        """, (vid_list, from_dt, to_dt))
        rows = cur.fetchall()

    # Build CSV in memory.
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";", quoting=csv.QUOTE_MINIMAL)

    headers = _CSV_HEADERS.get(lang, _CSV_HEADERS["de"])
    writer.writerow(headers)

    for r in rows:
        start_time, stop_time, cp_id, model, connector_id, \
            vehicle_name, authorized_tag, id_tag, energy_kwh, stop_reason = r

        # Parse timestamps for clean formatting.
        try:
            start_dt = datetime.fromisoformat(start_time)
            date_str  = start_dt.strftime("%d.%m.%Y") if lang == "de" else start_dt.strftime("%Y-%m-%d")
            start_str = start_dt.strftime("%H:%M")
        except Exception:
            date_str  = start_time or ""
            start_str = ""

        try:
            stop_dt  = datetime.fromisoformat(stop_time) if stop_time else None
            stop_str = stop_dt.strftime("%H:%M") if stop_dt else ""
            duration = str(round((stop_dt - start_dt).total_seconds() / 60)) if stop_dt else ""
        except Exception:
            stop_str = stop_time or ""
            duration = ""

        writer.writerow([
            date_str,
            start_str,
            stop_str,
            duration,
            model or cp_id,
            connector_id,
            vehicle_name or "",
            authorized_tag or id_tag or "",
            f"{energy_kwh:.3f}".replace(".", ",") if energy_kwh is not None else "",
            stop_reason or "",
        ])

    buf.seek(0)
    safe_name = report_name.replace(" ", "_").replace("/", "-")
    filename  = f"{safe_name}_{from_date}_{to_date}.csv"

    return StreamingResponse(
        iter([buf.getvalue().encode("utf-8-sig")]),  # utf-8-sig = BOM for Excel compatibility
        media_type="text/csv; charset=utf-8-sig",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
