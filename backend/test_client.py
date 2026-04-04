"""
OCPP 1.6 – Testclient
Verbindet sich mit ocpp.zick13.com und simuliert eine kurze Ladesession.

Ablauf:
  1. BootNotification
  2. StatusNotification  (Available)
  3. Authorize
  4. StartTransaction
  5. MeterValues  (3x alle 5 Sekunden)
  6. StopTransaction
  7. StatusNotification  (Available)
"""
import asyncio
import logging
from datetime import datetime, timezone

import websockets
from ocpp.v16 import ChargePoint as CP
from ocpp.v16 import call
from ocpp.v16.enums import (
    AuthorizationStatus,
    ChargePointErrorCode,
    ChargePointStatus,
    Measurand,
    ReadingContext,
    UnitOfMeasure,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("test-client")

# ---------------------------------------------------------------------------
# Einstellungen
# ---------------------------------------------------------------------------
SERVER_HOST   = "localhost"
SERVER_PORT   = 9000                # Traefik TLS-Termination → wss://
CP_ID         = "TEST-CP-001"
ID_TAG        = "Hkjskadj"
CONNECTOR_ID  = 1
METER_INTERVAL_SEC = 5             # Sekunden zwischen Messwerten


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# ChargePoint-Client
# ---------------------------------------------------------------------------
class TestChargePoint(CP):

    async def run_session(self):
        # 1. BootNotification
        logger.info(">>> BootNotification")
        response = await self.call(call.BootNotificationPayload(
            charge_point_model="TestCharger-X1",
            charge_point_vendor="Acme GmbH",
            firmware_version="1.0.0",
        ))
        logger.info("<<< BootNotification: status=%s  interval=%s",
                    response.status, response.interval)

        if response.status != "Accepted":
            logger.error("Server hat die Registrierung abgelehnt. Abbruch.")
            return

        # 2. StatusNotification – Available
        await self._status(ChargePointStatus.available)

        # 3. Authorize
        logger.info(">>> Authorize  id_tag=%s", ID_TAG)
        auth = await self.call(call.AuthorizePayload(id_tag=ID_TAG))
        logger.info("<<< Authorize: status=%s", auth.id_tag_info["status"])

        if auth.id_tag_info["status"] != AuthorizationStatus.accepted:
            logger.error("RFID-Tag abgelehnt. Abbruch.")
            return

        # 4. StatusNotification – Preparing
        await self._status(ChargePointStatus.preparing)

        # 5. StartTransaction
        meter_start = 1000  # Wh
        logger.info(">>> StartTransaction  meter_start=%d Wh", meter_start)
        start_resp = await self.call(call.StartTransactionPayload(
            connector_id=CONNECTOR_ID,
            id_tag=ID_TAG,
            meter_start=meter_start,
            timestamp=now_iso(),
        ))
        transaction_id = start_resp.transaction_id
        logger.info("<<< StartTransaction: transaction_id=%d  status=%s",
                    transaction_id, start_resp.id_tag_info["status"])

        # 6. StatusNotification – Charging
        await self._status(ChargePointStatus.charging)

        # 7. MeterValues  (simuliert 3 Messpunkte)
        meter_wh = meter_start
        for i in range(1, 4):
            logger.info("   Warte %d s …", METER_INTERVAL_SEC)
            await asyncio.sleep(METER_INTERVAL_SEC)
            meter_wh += 1500  # +1,5 kWh pro Intervall
            logger.info(">>> MeterValues  [%d/3]  %d Wh", i, meter_wh)
            await self.call(call.MeterValuesPayload(
                connector_id=CONNECTOR_ID,
                transaction_id=transaction_id,
                meter_value=[{
                    "timestamp": now_iso(),
                    "sampled_value": [
                        {
                            "value": str(meter_wh),
                            "measurand": Measurand.energy_active_import_register,
                            "unit": UnitOfMeasure.wh,
                            "context": ReadingContext.sample_periodic,
                        },
                        {
                            "value": "11000",
                            "measurand": Measurand.power_active_import,
                            "unit": UnitOfMeasure.w,
                            "context": ReadingContext.sample_periodic,
                        },
                    ],
                }],
            ))

        # 8. StopTransaction
        logger.info(">>> StopTransaction  meter_stop=%d Wh", meter_wh)
        await self.call(call.StopTransactionPayload(
            meter_stop=meter_wh,
            timestamp=now_iso(),
            transaction_id=transaction_id,
            id_tag=ID_TAG,
            reason="Local",
        ))
        logger.info("<<< StopTransaction  (%.3f kWh geladen)",
                    (meter_wh - meter_start) / 1000)

        # 9. StatusNotification – Available
        await self._status(ChargePointStatus.available)
        logger.info("Session abgeschlossen.")

    # Hilfsmethode
    async def _status(self, status: ChargePointStatus):
        logger.info(">>> StatusNotification  status=%s", status)
        await self.call(call.StatusNotificationPayload(
            connector_id=CONNECTOR_ID,
            error_code=ChargePointErrorCode.no_error,
            status=status,
            timestamp=now_iso(),
        ))


# ---------------------------------------------------------------------------
# Einstiegspunkt
# ---------------------------------------------------------------------------
async def main():
    url = f"ws://{SERVER_HOST}:{SERVER_PORT}/ocpp/{CP_ID}"
    logger.info("Verbinde mit %s …", url)

    async with websockets.connect(
        url,
        subprotocols=["ocpp1.6"],
    ) as ws:
        logger.info("Verbunden!")
        cp = TestChargePoint(CP_ID, ws)
        await asyncio.gather(
            cp.start(),          # OCPP-Nachrichten-Loop
            cp.run_session(),    # unsere Testsequenz
        )


if __name__ == "__main__":
    asyncio.run(main())
