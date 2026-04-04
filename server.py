"""
OCPP 1.6 Charging Station Server
Logs: which car (RFID), when, how long, how much kWh
"""
import asyncio
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import websockets
from ocpp.routing import on
from ocpp.v16 import ChargePoint as CP
from ocpp.v16 import call_result
from ocpp.v16.enums import (
    Action,
    AuthorizationStatus,
    ChargePointStatus,
    RegistrationStatus,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ocpp-server")

DB_PATH = Path("/data/charging.db")


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS charge_points (
            id          TEXT PRIMARY KEY,
            model       TEXT,
            vendor      TEXT,
            firmware    TEXT,
            last_seen   TEXT
        );

        CREATE TABLE IF NOT EXISTS sessions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            charge_point_id TEXT NOT NULL,
            connector_id    INTEGER NOT NULL,
            transaction_id  INTEGER,
            id_tag          TEXT,
            start_time      TEXT,
            stop_time       TEXT,
            start_meter_wh  INTEGER,
            stop_meter_wh   INTEGER,
            energy_kwh      REAL,
            stop_reason     TEXT
        );

        CREATE TABLE IF NOT EXISTS meter_values (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            charge_point_id TEXT NOT NULL,
            transaction_id  INTEGER,
            timestamp       TEXT,
            measurand       TEXT,
            value           TEXT,
            unit            TEXT
        );
    """)
    conn.commit()
    conn.close()
    logger.info("Database initialised at %s", DB_PATH)


def db():
    """Return a new DB connection (not thread-safe, but fine for asyncio)."""
    return sqlite3.connect(DB_PATH)


# ---------------------------------------------------------------------------
# ChargePoint handler
# ---------------------------------------------------------------------------

class ChargePoint(CP):

    def __init__(self, cp_id, websocket):
        super().__init__(cp_id, websocket)
        self._cp_id = cp_id
        # Maps connector_id -> pending session row id
        self._active_sessions: dict[int, int] = {}

    # --- BootNotification ---------------------------------------------------

    @on(Action.BootNotification)
    async def on_boot_notification(self, charge_point_model, charge_point_vendor,
                                   firmware_version=None, **kwargs):
        now = datetime.now(timezone.utc).isoformat()
        with db() as conn:
            conn.execute("""
                INSERT INTO charge_points (id, model, vendor, firmware, last_seen)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    model=excluded.model,
                    vendor=excluded.vendor,
                    firmware=excluded.firmware,
                    last_seen=excluded.last_seen
            """, (self._cp_id, charge_point_model, charge_point_vendor,
                  firmware_version, now))
        logger.info("[%s] Boot: vendor=%s model=%s firmware=%s",
                    self._cp_id, charge_point_vendor,
                    charge_point_model, firmware_version)
        return call_result.BootNotificationPayload(
            current_time=now,
            interval=30,
            status=RegistrationStatus.accepted,
        )

    # --- Heartbeat ----------------------------------------------------------

    @on(Action.Heartbeat)
    async def on_heartbeat(self, **kwargs):
        now = datetime.now(timezone.utc).isoformat()
        with db() as conn:
            conn.execute("UPDATE charge_points SET last_seen=? WHERE id=?",
                         (now, self._cp_id))
        return call_result.HeartbeatPayload(current_time=now)

    # --- Authorize ----------------------------------------------------------

    @on(Action.Authorize)
    async def on_authorize(self, id_tag, **kwargs):
        logger.info("[%s] Authorize request: id_tag=%s", self._cp_id, id_tag)
        # Accept all tags – extend here to check against a whitelist
        return call_result.AuthorizePayload(
            id_tag_info={"status": AuthorizationStatus.accepted}
        )

    # --- StartTransaction ---------------------------------------------------

    @on(Action.StartTransaction)
    async def on_start_transaction(self, connector_id, id_tag,
                                   meter_start, timestamp,
                                   reservation_id=None, **kwargs):
        with db() as conn:
            cur = conn.execute("""
                INSERT INTO sessions
                    (charge_point_id, connector_id, id_tag,
                     start_time, start_meter_wh)
                VALUES (?, ?, ?, ?, ?)
            """, (self._cp_id, connector_id, id_tag,
                  timestamp, meter_start))
            session_id = cur.lastrowid

        self._active_sessions[connector_id] = session_id
        transaction_id = session_id  # re-use row id as transaction id

        # Write transaction_id back
        with db() as conn:
            conn.execute("UPDATE sessions SET transaction_id=? WHERE id=?",
                         (transaction_id, session_id))

        logger.info("[%s] StartTransaction: connector=%d id_tag=%s meter=%d Wh  "
                    "-> transaction_id=%d",
                    self._cp_id, connector_id, id_tag,
                    meter_start, transaction_id)

        return call_result.StartTransactionPayload(
            transaction_id=transaction_id,
            id_tag_info={"status": AuthorizationStatus.accepted},
        )

    # --- StopTransaction ----------------------------------------------------

    @on(Action.StopTransaction)
    async def on_stop_transaction(self, transaction_id, meter_stop,
                                  timestamp, reason=None,
                                  id_tag=None, **kwargs):
        with db() as conn:
            row = conn.execute(
                "SELECT id, connector_id, start_meter_wh FROM sessions WHERE transaction_id=?",
                (transaction_id,)
            ).fetchone()

            if row:
                session_id, connector_id, start_wh = row
                energy_kwh = (meter_stop - start_wh) / 1000.0
                conn.execute("""
                    UPDATE sessions
                    SET stop_time=?, stop_meter_wh=?,
                        energy_kwh=?, stop_reason=?
                    WHERE id=?
                """, (timestamp, meter_stop, energy_kwh, reason, session_id))
                self._active_sessions.pop(connector_id, None)

                logger.info(
                    "[%s] StopTransaction: transaction=%d id_tag=%s "
                    "energy=%.3f kWh  reason=%s",
                    self._cp_id, transaction_id, id_tag,
                    energy_kwh, reason,
                )
            else:
                logger.warning("[%s] StopTransaction: unknown transaction_id=%d",
                               self._cp_id, transaction_id)

        return call_result.StopTransactionPayload()

    # --- MeterValues --------------------------------------------------------

    @on(Action.MeterValues)
    async def on_meter_values(self, connector_id, meter_value,
                              transaction_id=None, **kwargs):
        rows = []
        for mv in meter_value:
            ts = mv.get("timestamp")
            for sv in mv.get("sampled_value", []):
                rows.append((
                    self._cp_id,
                    transaction_id,
                    ts,
                    sv.get("measurand", "Energy.Active.Import.Register"),
                    sv.get("value"),
                    sv.get("unit", "Wh"),
                ))

        if rows:
            with db() as conn:
                conn.executemany("""
                    INSERT INTO meter_values
                        (charge_point_id, transaction_id, timestamp,
                         measurand, value, unit)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, rows)
            logger.info("[%s] MeterValues: %d sample(s) for transaction %s",
                        self._cp_id, len(rows), transaction_id)

        return call_result.MeterValuesPayload()

    # --- StatusNotification -------------------------------------------------

    @on(Action.StatusNotification)
    async def on_status_notification(self, connector_id, error_code,
                                     status, **kwargs):
        logger.info("[%s] Status: connector=%d  status=%s  error=%s",
                    self._cp_id, connector_id, status, error_code)
        return call_result.StatusNotificationPayload()


# ---------------------------------------------------------------------------
# WebSocket server
# ---------------------------------------------------------------------------

async def on_connect(websocket, path):
    """Handle a new WebSocket connection from a charge point."""
    # OCPP sub-protocol negotiation
    requested = websocket.request_headers.get("Sec-WebSocket-Protocol", "")
    if "ocpp1.6" not in requested:
        logger.warning("Client did not request ocpp1.6 (got: %s) – rejecting", requested)
        await websocket.close()
        return

    # Extract charge point ID from URL path  e.g. /ocpp/STATION-001
    cp_id = path.strip("/").split("/")[-1] or "unknown"
    logger.info("Charge point connected: id=%s  remote=%s",
                cp_id, websocket.remote_address)

    cp = ChargePoint(cp_id, websocket)
    try:
        await cp.start()
    except websockets.exceptions.ConnectionClosedOK:
        logger.info("Charge point disconnected cleanly: id=%s", cp_id)
    except Exception as exc:
        logger.error("Charge point %s error: %s", cp_id, exc)


async def main():
    init_db()
    host = "0.0.0.0"
    port = 9000
    logger.info("OCPP 1.6 server listening on ws://%s:%d", host, port)
    async with websockets.serve(
        on_connect,
        host,
        port,
        subprotocols=["ocpp1.6"],
    ):
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())
