# Theo Bauer · ChargeRelay
"""
ocpp_forwarder.py – OCPP relay forwarder.

Forwards every raw OCPP frame received from a charging station to all relay
endpoints configured in report_deliveries (type = 'ocpp').  One persistent
WebSocket connection is maintained per delivery entry; broken connections are
transparently re-established on the next forward call.
"""
import asyncio
import logging

import psycopg2
import websockets

logger = logging.getLogger("ocpp-forwarder")


class OcppForwarder:
    """Maintains WebSocket connections to relay targets and forwards raw OCPP frames."""

    def __init__(self, dsn: str):
        self._dsn = dsn
        # delivery_id -> open WebSocket connection
        self._connections: dict[int, websockets.WebSocketClientProtocol] = {}
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------ helpers

    def _fetch_deliveries(self) -> list[dict]:
        """Return all OCPP relay deliveries that have address + port set."""
        conn = psycopg2.connect(self._dsn)
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT rd.id, rd.address, rd.port, r.name
                FROM   report_deliveries rd
                JOIN   reports r ON r.id = rd.report_id
                WHERE  rd.type    = 'ocpp'
                  AND  rd.address IS NOT NULL
                  AND  rd.port    IS NOT NULL
            """)
            return [
                {
                    "id":          row[0],
                    "address":     row[1],
                    "port":        row[2],
                    "report_name": row[3],
                }
                for row in cur.fetchall()
            ]
        finally:
            conn.close()

    async def _get_connection(
        self, delivery_id: int, address: str, port: int
    ):
        """Return a live WebSocket connection, creating one if necessary."""
        async with self._lock:
            ws = self._connections.get(delivery_id)
            if ws is None or ws.closed:
                uri = f"ws://{address}:{port}"
                try:
                    ws = await websockets.connect(
                        uri,
                        subprotocols=["ocpp1.6"],
                        open_timeout=5,
                        close_timeout=5,
                    )
                    self._connections[delivery_id] = ws
                    logger.info(
                        "OCPP relay connected: %s  (delivery_id=%d)", uri, delivery_id
                    )
                except Exception as exc:
                    logger.warning(
                        "Cannot connect to OCPP relay %s (delivery_id=%d): %s",
                        uri, delivery_id, exc,
                    )
                    return None
            return ws

    # ------------------------------------------------------------------ public

    async def forward(self, cp_id: str, raw_message: str) -> None:
        """Forward *raw_message* (a raw OCPP JSON frame) to every relay endpoint."""
        deliveries = self._fetch_deliveries()
        if not deliveries:
            return

        for d in deliveries:
            ws = await self._get_connection(d["id"], d["address"], d["port"])
            if ws is None:
                continue
            try:
                await ws.send(raw_message)
                logger.debug(
                    "Forwarded to relay delivery_id=%d  cp=%s  msg=%.120s",
                    d["id"], cp_id, raw_message,
                )
            except Exception as exc:
                logger.warning(
                    "Forward failed for delivery_id=%d: %s", d["id"], exc
                )
                # Drop stale connection so the next call reconnects.
                async with self._lock:
                    self._connections.pop(d["id"], None)

    async def close_all(self) -> None:
        """Gracefully close every open relay connection."""
        async with self._lock:
            for ws in self._connections.values():
                try:
                    await ws.close()
                except Exception:
                    pass
            self._connections.clear()
        logger.info("All OCPP relay connections closed.")
