# Theo Bauer · ChargeRelay
"""
report_mailer.py – Scheduled e-mail report delivery.

Periodically checks report_deliveries (type = 'mail') and sends a CSV charge
report via SMTP when the configured interval (daily / weekly / monthly / yearly)
has elapsed since the last delivery.

SMTP credentials are read from environment variables:
    SMTP_HOST       – mail server hostname          (default: localhost)
    SMTP_PORT       – SMTP port, usually 587 / 465  (default: 587)
    SMTP_USER       – login username
    SMTP_PASSWORD   – login password
    SMTP_FROM       – sender address (falls back to SMTP_USER)
"""
import asyncio
import csv
import io
import logging
import os
import smtplib
from datetime import datetime, timedelta, timezone
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import psycopg2

logger = logging.getLogger("report-mailer")

# ---------------------------------------------------------------------------
# SMTP configuration (from environment)
# ---------------------------------------------------------------------------

SMTP_HOST     = os.environ.get("SMTP_HOST", "localhost")
SMTP_PORT     = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER     = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_FROM     = os.environ.get("SMTP_FROM", "") or SMTP_USER

# How often the background loop wakes up to check for due deliveries.
CHECK_INTERVAL_SECONDS = 300  # 5 minutes

# Timedelta for each named interval.
INTERVAL_DELTAS: dict[str, timedelta] = {
    "daily":   timedelta(days=1),
    "weekly":  timedelta(weeks=1),
    "monthly": timedelta(days=30),
    "yearly":  timedelta(days=365),
}


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _parse_utc(ts: str | None) -> datetime | None:
    if ts is None:
        return None
    dt = datetime.fromisoformat(ts)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


# ---------------------------------------------------------------------------
# ReportMailer
# ---------------------------------------------------------------------------

class ReportMailer:
    """Sends scheduled CSV charge reports via e-mail."""

    def __init__(self, dsn: str):
        self._dsn = dsn

    # ------------------------------------------------------------------ DB helpers

    def _connect(self):
        return psycopg2.connect(self._dsn)

    def _due_deliveries(self) -> list[dict]:
        """Return all mail deliveries whose interval has elapsed."""
        now = datetime.now(timezone.utc)
        conn = self._connect()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT rd.id, rd.report_id, r.name,
                       rd.email, rd.interval, rd.last_sent
                FROM   report_deliveries rd
                JOIN   reports r ON r.id = rd.report_id
                WHERE  rd.type     = 'mail'
                  AND  rd.email    IS NOT NULL
                  AND  rd.interval IS NOT NULL
            """)
            due = []
            for row in cur.fetchall():
                d_id, report_id, report_name, email, interval, last_sent = row
                delta = INTERVAL_DELTAS.get(interval)
                if delta is None:
                    continue  # unknown interval – skip
                last_dt = _parse_utc(last_sent)
                if last_dt is None or (now - last_dt) >= delta:
                    due.append({
                        "id":          d_id,
                        "report_id":   report_id,
                        "report_name": report_name,
                        "email":       email,
                        "interval":    interval,
                    })
            return due
        finally:
            conn.close()

    def _mark_sent(self, delivery_id: int) -> None:
        now = datetime.now(timezone.utc).isoformat()
        conn = self._connect()
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE report_deliveries SET last_sent = %s WHERE id = %s",
                (now, delivery_id),
            )
            conn.commit()
        finally:
            conn.close()

    # ------------------------------------------------------------------ CSV generation

    def _generate_csv(self, report_id: int) -> tuple[str, str]:
        """
        Build a UTF-8 CSV containing all sessions for the vehicles assigned
        to *report_id*.  Returns (csv_text, suggested_filename).
        """
        conn = self._connect()
        try:
            cur = conn.cursor()

            # Vehicle IDs configured for this report
            cur.execute(
                "SELECT vehicle_id FROM report_vehicles WHERE report_id = %s",
                (report_id,),
            )
            vehicle_ids = [r[0] for r in cur.fetchall()]

            buf = io.StringIO()
            writer = csv.writer(buf)
            writer.writerow([
                "session_id",
                "charge_point_id",
                "connector_id",
                "transaction_id",
                "id_tag",
                "vehicle_name",
                "start_time",
                "stop_time",
                "start_meter_wh",
                "stop_meter_wh",
                "energy_kwh",
                "stop_reason",
            ])

            if vehicle_ids:
                placeholders = ",".join(["%s"] * len(vehicle_ids))
                cur.execute(
                    f"""
                    SELECT s.id, s.charge_point_id, s.connector_id, s.transaction_id,
                           s.id_tag, v.name,
                           s.start_time, s.stop_time,
                           s.start_meter_wh, s.stop_meter_wh, s.energy_kwh, s.stop_reason
                    FROM   sessions s
                    LEFT JOIN vehicles v ON v.id = s.vehicle_id
                    WHERE  s.vehicle_id IN ({placeholders})
                    ORDER  BY s.start_time DESC
                    """,
                    vehicle_ids,
                )
            else:
                # No vehicles assigned → export everything
                cur.execute("""
                    SELECT s.id, s.charge_point_id, s.connector_id, s.transaction_id,
                           s.id_tag, v.name,
                           s.start_time, s.stop_time,
                           s.start_meter_wh, s.stop_meter_wh, s.energy_kwh, s.stop_reason
                    FROM   sessions s
                    LEFT JOIN vehicles v ON v.id = s.vehicle_id
                    ORDER  BY s.start_time DESC
                """)

            for row in cur.fetchall():
                writer.writerow(row)

            ts_str   = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            filename = f"ladebericht_{report_id}_{ts_str}.csv"
            return buf.getvalue(), filename

        finally:
            conn.close()

    # ------------------------------------------------------------------ email sending

    @staticmethod
    def _send_email(
        to_address: str,
        report_name: str,
        csv_text: str,
        filename: str,
    ) -> None:
        msg             = MIMEMultipart()
        msg["From"]     = SMTP_FROM
        msg["To"]       = to_address
        msg["Subject"]  = f"Ladebericht: {report_name}"

        now_fmt = datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M")
        body = (
            f"Im Anhang finden Sie den aktuellen Ladebericht für »{report_name}«.\n\n"
            f"Erstellt am: {now_fmt} UTC\n"
        )
        msg.attach(MIMEText(body, "plain", "utf-8"))

        attachment = MIMEBase("text", "csv", charset="utf-8")
        attachment.set_payload(csv_text.encode("utf-8"))
        encoders.encode_base64(attachment)
        attachment.add_header(
            "Content-Disposition", "attachment", filename=filename
        )
        msg.attach(attachment)

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            if SMTP_USER and SMTP_PASSWORD:
                smtp.login(SMTP_USER, SMTP_PASSWORD)
            smtp.sendmail(SMTP_FROM, to_address, msg.as_string())

        logger.info(
            "Report e-mail sent: to=%s  report='%s'  file=%s",
            to_address, report_name, filename,
        )

    # ------------------------------------------------------------------ run loop

    async def _run_once(self) -> None:
        due = self._due_deliveries()
        if not due:
            return
        logger.info("ReportMailer: %d delivery/deliveries due", len(due))

        loop = asyncio.get_event_loop()
        for d in due:
            try:
                csv_text, filename = self._generate_csv(d["report_id"])
                # Run blocking SMTP call in a thread pool to avoid blocking the event loop.
                await loop.run_in_executor(
                    None,
                    self._send_email,
                    d["email"],
                    d["report_name"],
                    csv_text,
                    filename,
                )
                self._mark_sent(d["id"])
            except Exception as exc:
                logger.error(
                    "Failed to send report e-mail to %s (delivery_id=%d): %s",
                    d["email"], d["id"], exc,
                )

    async def run(self) -> None:
        """Infinite background loop – start with asyncio.create_task(mailer.run())."""
        logger.info(
            "ReportMailer started (check interval: %ds, SMTP: %s:%d)",
            CHECK_INTERVAL_SECONDS, SMTP_HOST, SMTP_PORT,
        )
        while True:
            try:
                await self._run_once()
            except Exception as exc:
                logger.error("ReportMailer unexpected error: %s", exc)
            await asyncio.sleep(CHECK_INTERVAL_SECONDS)
