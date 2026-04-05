# Theo Bauer · ChargeRelay
"""
main.py – FastAPI application entry point.

Creates the app, registers CORS middleware, and mounts all routers.
Start with:  uvicorn main:app --host 0.0.0.0 --port 8000
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import reports, sessions, stats, vehicles

# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

app = FastAPI(
    title="ChargeRelay API",
    version="1.0.0",
    description="REST API for the ChargeRelay OCPP charging station management system.",
)

# Allow all origins so the Nuxt frontend can reach the API in any environment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Router registration
# ---------------------------------------------------------------------------

# Each router handles one domain of the API surface.
app.include_router(sessions.router)
app.include_router(vehicles.router)
app.include_router(stats.router)
app.include_router(reports.router)
