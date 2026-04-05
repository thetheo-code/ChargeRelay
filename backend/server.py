"""
OCPP 1.6 Charging Station Server
Logs: which car (RFID), when, how long, how much kWh
"""
import asyncio
import logging
import os
from contextlib import contextmanager
from datetime import datetime, timezone

import psycopg2
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

from ocpp_forwarder import OcppForwarder
from report_mailer import ReportMailer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ocpp-server")

DSN = (
    "host={host} port={port} dbname={dbname} user={user} password={password}"
    .format(
        host=os.environ.get("DB_HOST", "localhost"),
        port=os.environ.get("DB_PORT", "5432"),
        dbname=os.environ.get("DB_NAME", "ocpp"),
        user=os.environ.get("DB_USER", "ocpp"),
        password=os.environ.get("DB_PASSWORD", "ocpp"),
    )
)


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

@contextmanager
def db():
    """Context manager: yields a psycopg2 connection that auto-commits/rollbacks."""
    conn = psycopg2.connect(DSN)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with db() as conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS charge_points (
                id          TEXT PRIMARY KEY,
                model       TEXT,
                vendor      TEXT,
                firmware    TEXT,
                last_seen   TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id              SERIAL PRIMARY KEY,
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
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS meter_values (
                id              SERIAL PRIMARY KEY,
                charge_point_id TEXT NOT NULL,
                transaction_id  INTEGER,
                timestamp       TEXT,
                measurand       TEXT,
                value           TEXT,
                unit            TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS vehicles (
                id          SERIAL PRIMARY KEY,
                name        TEXT NOT NULL,
                id_tag      TEXT UNIQUE,
                image_data  TEXT,
                created_at  TEXT
            )
        """)
        cur.execute("""
            ALTER TABLE sessions ADD COLUMN IF NOT EXISTS vehicle_id INTEGER REFERENCES vehicles(id)
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id          SERIAL PRIMARY KEY,
                name        TEXT NOT NULL,
                created_at  TEXT NOT NULL
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS report_vehicles (
                report_id   INTEGER NOT NULL REFERENCES reports(id)  ON DELETE CASCADE,
                vehicle_id  INTEGER NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
                PRIMARY KEY (report_id, vehicle_id)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS report_deliveries (
                id          SERIAL PRIMARY KEY,
                report_id   INTEGER NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
                type        TEXT    NOT NULL,
                email       TEXT,
                interval    TEXT,
                address     TEXT,
                port        INTEGER
            )
        """)
        # Migration: add last_sent column if it doesn't exist yet
        cur.execute("""
            ALTER TABLE report_deliveries ADD COLUMN IF NOT EXISTS last_sent TEXT
        """)
    logger.info("Database initialised")


# ---------------------------------------------------------------------------
# Global services (initialised in main())
# ---------------------------------------------------------------------------

forwarder: OcppForwarder | None = None


# ---------------------------------------------------------------------------
# ChargePoint handler
# ---------------------------------------------------------------------------

class ChargePoint(CP):

    def __init__(self, cp_id, websocket):
        super().__init__(cp_id, websocket)
        self._cp_id = cp_id
        # Maps connector_id -> pending session row id
        self._active_sessions: dict[int, int] = {}

    # --- Message forwarding -------------------------------------------------

    async def route_message(self, raw_msg):
        """Intercept every incoming OCPP frame and forward it to relay targets."""
        if forwarder is not None:
            asyncio.ensure_future(forwarder.forward(self._cp_id, raw_msg))
        return await super().route_message(raw_msg)

    # --- BootNotification ---------------------------------------------------

    @on(Action.BootNotification)
    async def on_boot_notification(self, charge_point_model, charge_point_vendor,
                                   firmware_version=None, **kwargs):
        now = datetime.now(timezone.utc).isoformat()
        with db() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO charge_points (id, model, vendor, firmware, last_seen)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT(id) DO UPDATE SET
                    model=EXCLUDED.model,
                    vendor=EXCLUDED.vendor,
                    firmware=EXCLUDED.firmware,
                    last_seen=EXCLUDED.last_seen
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
            cur = conn.cursor()
            cur.execute("UPDATE charge_points SET last_seen=%s WHERE id=%s",
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
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO sessions
                    (charge_point_id, connector_id, id_tag,
                     start_time, start_meter_wh)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """, (self._cp_id, connector_id, id_tag,
                  timestamp, meter_start))
            session_id = cur.fetchone()[0]
            transaction_id = session_id  # re-use row id as transaction id
            cur.execute("UPDATE sessions SET transaction_id=%s WHERE id=%s",
                        (transaction_id, session_id))

            # Auto-assign vehicle by id_tag
            cur.execute("SELECT id FROM vehicles WHERE id_tag = %s", (id_tag,))
            vehicle_row = cur.fetchone()
            if vehicle_row:
                cur.execute("UPDATE sessions SET vehicle_id = %s WHERE id = %s",
                            (vehicle_row[0], session_id))

        self._active_sessions[connector_id] = session_id

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
            cur = conn.cursor()
            cur.execute(
                "SELECT id, connector_id, start_meter_wh FROM sessions WHERE transaction_id=%s",
                (transaction_id,)
            )
            row = cur.fetchone()

            if row:
                session_id, connector_id, start_wh = row
                energy_kwh = (meter_stop - start_wh) / 1000.0
                cur.execute("""
                    UPDATE sessions
                    SET stop_time=%s, stop_meter_wh=%s,
                        energy_kwh=%s, stop_reason=%s
                    WHERE id=%s
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
                cur = conn.cursor()
                cur.executemany("""
                    INSERT INTO meter_values
                        (charge_point_id, transaction_id, timestamp,
                         measurand, value, unit)
                    VALUES (%s, %s, %s, %s, %s, %s)
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
    global forwarder

    init_db()

    # Initialise OCPP forwarder
    forwarder = OcppForwarder(DSN)

    # Start e-mail report scheduler as background task
    mailer = ReportMailer(DSN)
    asyncio.create_task(mailer.run())

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
