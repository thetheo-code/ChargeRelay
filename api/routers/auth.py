# Theo Bauer · ChargeRelay
"""
routers/auth.py – UI password-gate endpoints.

When UI_PASSWORD is set in the environment, the frontend will show a login
screen before granting access.  The API itself is not token-protected –
this is an intentional choice for a private home-network deployment where
the UI gate is sufficient.

Routes
------
GET  /api/auth/status   Tell the frontend whether a password is required.
POST /api/auth/verify   Verify the submitted password (200 OK or 401).
"""
import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/auth")

# Read the password once at startup; empty string means no protection.
_UI_PASSWORD: str = os.environ.get("UI_PASSWORD", "").strip()


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class VerifyRequest(BaseModel):
    """Body for the password verification request."""
    password: str


# ---------------------------------------------------------------------------
# GET /api/auth/status
# ---------------------------------------------------------------------------

@router.get("/status")
def auth_status():
    """Return whether a UI password has been configured."""
    return {"required": bool(_UI_PASSWORD)}


# ---------------------------------------------------------------------------
# POST /api/auth/verify
# ---------------------------------------------------------------------------

@router.post("/verify")
def verify_password(body: VerifyRequest):
    """Check the submitted password and return 200 on success, 401 on failure."""
    if not _UI_PASSWORD:
        # No password configured – always grant access.
        return {"ok": True}

    if body.password != _UI_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid password")

    return {"ok": True}
