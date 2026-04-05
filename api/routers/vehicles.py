# Theo Bauer · ChargeRelay
"""
routers/vehicles.py – CRUD endpoints for vehicles.

Routes
------
GET    /api/vehicles        Return all vehicles ordered by name.
POST   /api/vehicles        Create a new vehicle.
PUT    /api/vehicles/{id}   Replace a vehicle's data.
DELETE /api/vehicles/{id}   Remove a vehicle.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from database import db, db_write, row_to_dict
from models import VehicleCreate, VehicleUpdate

router = APIRouter(prefix="/api")


# ---------------------------------------------------------------------------
# GET /api/vehicles
# ---------------------------------------------------------------------------

@router.get("/vehicles")
def get_vehicles():
    """Return all vehicles sorted alphabetically by name."""
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

@router.post("/vehicles", status_code=201)
def create_vehicle(body: VehicleCreate):
    """Insert a new vehicle and return the created record."""
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

@router.put("/vehicles/{vehicle_id}")
def update_vehicle(vehicle_id: int, body: VehicleUpdate):
    """Overwrite all mutable fields of an existing vehicle."""
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

@router.delete("/vehicles/{vehicle_id}", status_code=204)
def delete_vehicle(vehicle_id: int):
    """Permanently remove a vehicle; sessions lose their vehicle assignment."""
    with db_write() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM vehicles WHERE id = %s", (vehicle_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Vehicle not found")
