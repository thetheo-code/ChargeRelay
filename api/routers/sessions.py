# Theo Bauer · ChargeRelay
"""
routers/sessions.py – Endpoints for charge sessions.

Routes
------
GET    /api/active                  Return all currently active sessions.
GET    /api/sessions                Return paginated session history.
DELETE /api/sessions/{id}           Delete a session and its meter values.
PUT    /api/sessions/{id}/vehicle   Assign (or unassign) a vehicle to a session.
"""
import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from database import db, db_write, row_to_dict
from models import SessionVehicleUpdate

router = APIRouter(prefix="/api")


# ---------------------------------------------------------------------------
# GET /api/active
# ---------------------------------------------------------------------------

@router.get("/active")
def get_active_sessions():
    """Return every session that has no stop time, enriched with live meter values."""
    with db() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT
                s.id                AS session_id,
                s.connector_id,
                s.transaction_id,
                s.id_tag,
                s.authorized_id_tag,
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
            JOIN  charge_points cp ON cp.id = s.charge_point_id
            LEFT JOIN vehicles  v  ON v.id  = s.vehicle_id
            WHERE s.stop_time IS NULL
            ORDER BY s.start_time DESC
        """)
        sessions = [row_to_dict(cur, r) for r in cur.fetchall()]

        now = datetime.now(timezone.utc)

        for s in sessions:
            # Calculate elapsed seconds since the session started.
            try:
                start = datetime.fromisoformat(s["start_time"])
                if start.tzinfo is None:
                    start = start.replace(tzinfo=timezone.utc)
                s["duration_seconds"] = int((now - start).total_seconds())
            except Exception:
                s["duration_seconds"] = None

            # Attach the most recent meter value for every measurand.
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

            # Compute session energy delta (current meter − start meter).
            energy_mv = next(
                (m for m in s["latest_meter_values"]
                 if m["measurand"] == "Energy.Active.Import.Register"),
                None,
            )
            if energy_mv is not None and s.get("start_meter_wh") is not None:
                raw = float(energy_mv["value"])
                current_wh = raw * 1000 if energy_mv["unit"] == "kWh" else raw
                s["session_energy_kwh"] = max(0.0, (current_wh - s["start_meter_wh"]) / 1000)
            else:
                s["session_energy_kwh"] = None

    return sessions


# ---------------------------------------------------------------------------
# GET /api/sessions
# ---------------------------------------------------------------------------

@router.get("/sessions")
def get_sessions(
    page: int      = Query(1,  ge=1,         description="Page number (starting at 1)"),
    page_size: int = Query(20, ge=1, le=100, description="Number of entries per page"),
):
    """Return a paginated list of all completed and active sessions."""
    offset = (page - 1) * page_size
    with db() as conn:
        cur = conn.cursor()

        # Total count for pagination metadata.
        cur.execute("SELECT COUNT(*) FROM sessions")
        total = cur.fetchone()[0]

        cur.execute("""
            SELECT
                s.id                AS session_id,
                s.connector_id,
                s.transaction_id,
                s.id_tag,
                s.authorized_id_tag,
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
            JOIN  charge_points cp ON cp.id = s.charge_point_id
            LEFT JOIN vehicles  v  ON v.id  = s.vehicle_id
            ORDER BY s.start_time DESC
            LIMIT %s OFFSET %s
        """, (page_size, offset))
        sessions = [row_to_dict(cur, r) for r in cur.fetchall()]

    return {
        "total":     total,
        "page":      page,
        "page_size": page_size,
        "pages":     (total + page_size - 1) // page_size,
        "sessions":  sessions,
    }


# ---------------------------------------------------------------------------
# DELETE /api/sessions/{session_id}
# ---------------------------------------------------------------------------

@router.delete("/sessions/{session_id}", status_code=204)
def delete_session(session_id: int):
    """Delete a session and all meter values that belong to its transaction."""
    with db_write() as conn:
        cur = conn.cursor()

        # Remove associated meter values first (no FK constraint enforces this).
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
# PUT /api/sessions/{session_id}/vehicle
# ---------------------------------------------------------------------------

@router.put("/sessions/{session_id}/vehicle")
def assign_vehicle(session_id: int, body: SessionVehicleUpdate):
    """Assign a vehicle to a session, or clear the assignment when vehicle_id is null."""
    with db_write() as conn:
        cur = conn.cursor()

        # Verify the target vehicle exists before writing.
        if body.vehicle_id is not None:
            cur.execute("SELECT id FROM vehicles WHERE id = %s", (body.vehicle_id,))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Vehicle not found")

        cur.execute(
            "UPDATE sessions SET vehicle_id = %s WHERE id = %s",
            (body.vehicle_id, session_id),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Session not found")

    return {"session_id": session_id, "vehicle_id": body.vehicle_id}


# ---------------------------------------------------------------------------
# GET /api/sessions/download
# ---------------------------------------------------------------------------

_CSV_HEADERS: dict[str, list[str]] = {
    "de": ["Datum", "Start", "Ende", "Dauer (min)", "Ladestation",
           "Connector", "Fahrzeug", "RFID-Tag", "Energie (kWh)", "Abbruchgrund"],
    "en": ["Date", "Start", "End", "Duration (min)", "Charge Point",
           "Connector", "Vehicle", "RFID Tag", "Energy (kWh)", "Stop Reason"],
}


@router.get("/sessions/download")
def download_sessions_csv(
    from_date: str = Query(..., description="Start date inclusive (YYYY-MM-DD)"),
    to_date:   str = Query(..., description="End date inclusive (YYYY-MM-DD)"),
    vehicle_ids: str | None = Query(
        None,
        description="Comma-separated vehicle IDs to filter by. "
                    "Omit to export all sessions.",
    ),
    lang: str = Query("de", description="Column header language: 'de' or 'en'"),
):
    """Return a CSV file of all completed sessions within the given date range."""
    from_dt = f"{from_date}T00:00:00"
    to_dt   = f"{to_date}T23:59:59"

    vid_list: list[int] | None = None
    if vehicle_ids:
        try:
            vid_list = [int(v.strip()) for v in vehicle_ids.split(",") if v.strip()]
        except ValueError:
            raise HTTPException(status_code=422, detail="vehicle_ids must be integers")

    with db() as conn:
        cur = conn.cursor()

        if vid_list:
            cur.execute("""
                SELECT
                    s.start_time, s.stop_time,
                    cp.id AS charge_point_id, cp.model,
                    s.connector_id,
                    v.name  AS vehicle_name,
                    s.authorized_id_tag, s.id_tag,
                    s.energy_kwh, s.stop_reason
                FROM sessions s
                JOIN  charge_points cp ON cp.id = s.charge_point_id
                LEFT JOIN vehicles  v  ON v.id  = s.vehicle_id
                WHERE s.stop_time IS NOT NULL
                  AND s.start_time >= %s
                  AND s.start_time <= %s
                  AND s.vehicle_id = ANY(%s)
                ORDER BY s.start_time ASC
            """, (from_dt, to_dt, vid_list))
        else:
            cur.execute("""
                SELECT
                    s.start_time, s.stop_time,
                    cp.id AS charge_point_id, cp.model,
                    s.connector_id,
                    v.name  AS vehicle_name,
                    s.authorized_id_tag, s.id_tag,
                    s.energy_kwh, s.stop_reason
                FROM sessions s
                JOIN  charge_points cp ON cp.id = s.charge_point_id
                LEFT JOIN vehicles  v  ON v.id  = s.vehicle_id
                WHERE s.stop_time IS NOT NULL
                  AND s.start_time >= %s
                  AND s.start_time <= %s
                ORDER BY s.start_time ASC
            """, (from_dt, to_dt))

        rows = cur.fetchall()

    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";", quoting=csv.QUOTE_MINIMAL)
    writer.writerow(_CSV_HEADERS.get(lang, _CSV_HEADERS["de"]))

    for r in rows:
        start_time, stop_time, cp_id, model, connector_id, \
            vehicle_name, authorized_tag, id_tag, energy_kwh, stop_reason = r

        try:
            start_dt  = datetime.fromisoformat(start_time)
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
    filename = f"ladevorgaenge_{from_date}_{to_date}.csv"

    return StreamingResponse(
        iter([buf.getvalue().encode("utf-8-sig")]),
        media_type="text/csv; charset=utf-8-sig",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
