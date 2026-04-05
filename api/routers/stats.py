# Theo Bauer · ChargeRelay
"""
routers/stats.py – Aggregated statistics endpoint.

Routes
------
GET /api/stats   Return energy-per-day, energy-per-vehicle, and total counters.
"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Query

from database import db

router = APIRouter(prefix="/api")


# ---------------------------------------------------------------------------
# GET /api/stats
# ---------------------------------------------------------------------------

@router.get("/stats")
def get_stats(days: int = Query(14, ge=7, le=90)):
    """
    Return three aggregates for the dashboard:

    energy_per_day      – kWh per calendar day for the last *days* days,
                          with gaps filled as 0.
    energy_per_vehicle  – top-8 vehicles by total kWh (all time).
    total_sessions /
    total_kwh           – summary counters for the last 30 days.
    """
    today    = datetime.now(timezone.utc).date()
    since_n  = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    since_30 = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()

    with db() as conn:
        cur = conn.cursor()

        # Build a dense day series – days missing from the table become 0 kWh.
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
            {
                "date": (today - timedelta(days=days - 1 - i)).isoformat(),
                "kwh":  raw.get((today - timedelta(days=days - 1 - i)).isoformat(), 0.0),
            }
            for i in range(days)
        ]

        # Top 8 vehicles by all-time energy consumption.
        cur.execute("""
            SELECT COALESCE(v.name, s.id_tag, 'Unknown') AS name,
                   ROUND(SUM(s.energy_kwh)::numeric, 2)  AS kwh
            FROM sessions s
            LEFT JOIN vehicles v ON v.id = s.vehicle_id
            WHERE s.energy_kwh IS NOT NULL
            GROUP BY COALESCE(v.name, s.id_tag, 'Unknown')
            ORDER BY kwh DESC
            LIMIT 8
        """)
        energy_per_vehicle = [
            {"name": r[0], "kwh": float(r[1])} for r in cur.fetchall()
        ]

        # Total sessions and kWh for the rolling 30-day window.
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
