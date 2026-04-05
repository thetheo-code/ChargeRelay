# Theo Bauer · ChargeRelay
"""
models.py – Pydantic request/response models for the REST API.

All input validation lives here so routers stay thin and readable.
"""
from typing import Optional

from pydantic import BaseModel, field_validator

# ---------------------------------------------------------------------------
# Allowed values
# ---------------------------------------------------------------------------

DELIVERY_TYPES = {"mail", "ocpp"}
MAIL_INTERVALS = {"daily", "weekly", "monthly", "yearly"}


# ---------------------------------------------------------------------------
# Vehicle models
# ---------------------------------------------------------------------------

class VehicleCreate(BaseModel):
    """Payload for creating a new vehicle."""
    name: str
    id_tag: Optional[str] = None
    image_data: Optional[str] = None   # base64 data URL


class VehicleUpdate(BaseModel):
    """Payload for replacing an existing vehicle's data."""
    name: str
    id_tag: Optional[str] = None
    image_data: Optional[str] = None


class SessionVehicleUpdate(BaseModel):
    """Payload for (re-)assigning a vehicle to a session."""
    vehicle_id: Optional[int] = None


# ---------------------------------------------------------------------------
# Report models
# ---------------------------------------------------------------------------

class DeliveryIn(BaseModel):
    """A single delivery configuration attached to a report."""
    type: str
    # Mail-specific
    email: Optional[str] = None
    interval: Optional[str] = None     # daily | weekly | monthly | yearly
    # OCPP relay-specific
    address: Optional[str] = None
    port: Optional[int] = None

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Reject delivery types that are not supported."""
        if v not in DELIVERY_TYPES:
            raise ValueError(f"type must be one of: {', '.join(sorted(DELIVERY_TYPES))}")
        return v

    @field_validator("interval")
    @classmethod
    def validate_interval(cls, v: Optional[str]) -> Optional[str]:
        """Reject interval strings that are not in the allowed set."""
        if v is not None and v not in MAIL_INTERVALS:
            raise ValueError(f"interval must be one of: {', '.join(sorted(MAIL_INTERVALS))}")
        return v


class ReportCreate(BaseModel):
    """Payload for creating a new report."""
    name: str
    vehicle_ids: list[int]
    deliveries: list[DeliveryIn]


class ReportUpdate(BaseModel):
    """Payload for replacing an existing report's configuration."""
    name: str
    vehicle_ids: list[int]
    deliveries: list[DeliveryIn]
