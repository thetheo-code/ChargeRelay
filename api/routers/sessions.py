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
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

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
