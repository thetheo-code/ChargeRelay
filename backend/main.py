# Theo Bauer · ChargeRelay
"""
main.py – OCPP 1.6 WebSocket server entry point.

Starts the WebSocket server, initialises all background services
(OCPP forwarder, e-mail report scheduler), and runs the asyncio event loop.
"""
import asyncio
import logging

import websockets

import charge_point as cp_module
from charge_point import ChargePoint
from database import DSN, init_db
from ocpp_forwarder import OcppForwarder
from report_mailer import ReportMailer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ocpp-server")

HOST = "0.0.0.0"
PORT = 9000


# ---------------------------------------------------------------------------
# WebSocket connection handler
# ---------------------------------------------------------------------------

async def on_connect(websocket, path: str) -> None:
    """Accept a new WebSocket connection and hand it to a ChargePoint handler."""

    # Reject clients that do not speak OCPP 1.6.
    requested = websocket.request_headers.get("Sec-WebSocket-Protocol", "")
    if "ocpp1.6" not in requested:
        logger.warning("Rejected client – missing ocpp1.6 sub-protocol (got: %s)", requested)
        await websocket.close()
        return

    # Derive the charge-point ID from the URL path (e.g. /ocpp/STATION-001).
    cp_id = path.strip("/").split("/")[-1] or "unknown"
    logger.info("Charge point connected: id=%s  remote=%s", cp_id, websocket.remote_address)

    cp = ChargePoint(cp_id, websocket)
    try:
        await cp.start()
    except websockets.exceptions.ConnectionClosedOK:
        logger.info("Charge point disconnected cleanly: id=%s", cp_id)
    except Exception as exc:
        logger.error("Charge point %s error: %s", cp_id, exc)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main() -> None:
    """Initialise the database, start background services, and serve WebSocket clients."""

    init_db()

    # Create the OCPP forwarder and inject it into the charge_point module
    # so every ChargePoint instance can reach it without a circular import.
    forwarder = OcppForwarder(DSN)
    cp_module.forwarder = forwarder

    # Start the e-mail report scheduler as a fire-and-forget background task.
    mailer = ReportMailer(DSN)
    asyncio.create_task(mailer.run())

    logger.info("OCPP 1.6 server listening on ws://%s:%d", HOST, PORT)
    async with websockets.serve(
        on_connect,
        HOST,
        PORT,
        subprotocols=["ocpp1.6"],
    ):
        await asyncio.Future()   # run forever


if __name__ == "__main__":
    asyncio.run(main())
