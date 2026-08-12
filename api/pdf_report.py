# Theo Bauer · ChargeRelay
"""Shared PDF builder for charge session reports."""
import io
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# Unicode-capable fonts shipped with the API (needed for German umlauts).
_FONT_DIR = Path(__file__).resolve().parent / "fonts"
pdfmetrics.registerFont(TTFont("DejaVu", str(_FONT_DIR / "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("DejaVu-Bold", str(_FONT_DIR / "DejaVuSans-Bold.ttf")))

_PDF_HEADERS: dict[str, list[str]] = {
    "de": ["Datum", "Start", "Enddatum", "Ende", "Dauer (min)", "Ladestation",
           "Conn.", "Fahrzeug", "RFID-Tag", "Energie (kWh)", "Abbruchgrund"],
    "en": ["Date", "Start", "End Date", "End", "Duration (min)", "Charge Point",
           "Conn.", "Vehicle", "RFID Tag", "Energy (kWh)", "Stop Reason"],
}

_PDF_LABELS: dict[str, dict[str, str]] = {
    "de": {
        "title": "Ladebericht",
        "period": "Zeitraum",
        "sessions": "Ladevorgänge",
        "total_energy": "Gesamtenergie",
        "generated": "Erstellt am",
        "empty": "Keine Ladevorgänge im gewählten Zeitraum.",
    },
    "en": {
        "title": "Charge Report",
        "period": "Period",
        "sessions": "Sessions",
        "total_energy": "Total energy",
        "generated": "Generated at",
        "empty": "No charging sessions in the selected period.",
    },
}


def _fmt_date(dt: datetime, lang: str) -> str:
    return dt.strftime("%d.%m.%Y") if lang == "de" else dt.strftime("%Y-%m-%d")


def _fmt_energy(energy_kwh: float | None, lang: str) -> str:
    if energy_kwh is None:
        return ""
    value = f"{energy_kwh:.3f}"
    return value.replace(".", ",") if lang == "de" else value


def _session_row(r: tuple, lang: str) -> tuple[list[str], float | None]:
    """Format one DB session row for the PDF table. Returns (cells, energy_kwh)."""
    start_time, stop_time, cp_id, model, connector_id, \
        vehicle_name, authorized_tag, id_tag, energy_kwh, stop_reason = r

    try:
        start_dt = datetime.fromisoformat(start_time)
        date_str = _fmt_date(start_dt, lang)
        start_str = start_dt.strftime("%H:%M")
    except Exception:
        date_str = start_time or ""
        start_str = ""
        start_dt = None

    try:
        stop_dt = datetime.fromisoformat(stop_time) if stop_time else None
        if stop_dt:
            end_date_str = _fmt_date(stop_dt, lang)
            stop_str = stop_dt.strftime("%H:%M")
            duration = (
                str(round((stop_dt - start_dt).total_seconds() / 60))
                if start_dt else ""
            )
        else:
            end_date_str = stop_str = duration = ""
    except Exception:
        end_date_str = ""
        stop_str = stop_time or ""
        duration = ""

    cells = [
        date_str,
        start_str,
        end_date_str,
        stop_str,
        duration,
        model or cp_id or "",
        str(connector_id) if connector_id is not None else "",
        vehicle_name or "",
        authorized_tag or id_tag or "",
        _fmt_energy(energy_kwh, lang),
        stop_reason or "",
    ]
    return cells, energy_kwh


def build_report_pdf(
    report_name: str,
    from_date: str,
    to_date: str,
    rows: list[tuple],
    lang: str,
) -> bytes:
    """Build a landscape A4 PDF charge report and return the raw bytes."""
    labels = _PDF_LABELS.get(lang, _PDF_LABELS["de"])
    headers = _PDF_HEADERS.get(lang, _PDF_HEADERS["de"])

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(A4),
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title=f"{labels['title']}: {report_name}",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Heading1"],
        fontName="DejaVu-Bold",
        fontSize=16,
        leading=20,
        alignment=TA_LEFT,
        spaceAfter=2 * mm,
        textColor=colors.HexColor("#1a1a1a"),
    )
    meta_style = ParagraphStyle(
        "ReportMeta",
        parent=styles["Normal"],
        fontName="DejaVu",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#555555"),
        spaceAfter=1 * mm,
    )
    empty_style = ParagraphStyle(
        "ReportEmpty",
        parent=styles["Normal"],
        fontName="DejaVu",
        fontSize=10,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#888888"),
        spaceBefore=10 * mm,
    )
    cell_style = ParagraphStyle(
        "ReportCell",
        parent=styles["Normal"],
        fontName="DejaVu",
        fontSize=7,
        leading=9,
        alignment=TA_LEFT,
    )
    header_cell_style = ParagraphStyle(
        "ReportHeaderCell",
        parent=styles["Normal"],
        fontName="DejaVu-Bold",
        fontSize=7,
        leading=9,
        alignment=TA_LEFT,
        textColor=colors.white,
    )

    story: list = []
    story.append(Paragraph(escape(f"{labels['title']}: {report_name}"), title_style))

    period_from = from_date
    period_to = to_date
    try:
        period_from = _fmt_date(datetime.fromisoformat(from_date), lang)
        period_to = _fmt_date(datetime.fromisoformat(to_date), lang)
    except Exception:
        pass

    total_energy = 0.0
    table_data: list[list] = [
        [Paragraph(escape(h), header_cell_style) for h in headers]
    ]

    for r in rows:
        cells, energy_kwh = _session_row(r, lang)
        if energy_kwh is not None:
            total_energy += float(energy_kwh)
        table_data.append([Paragraph(escape(str(c)), cell_style) for c in cells])

    now_fmt = datetime.now(timezone.utc).strftime(
        "%d.%m.%Y %H:%M UTC" if lang == "de" else "%Y-%m-%d %H:%M UTC"
    )
    energy_fmt = _fmt_energy(total_energy, lang) or ("0,000" if lang == "de" else "0.000")

    story.append(Paragraph(
        f"{labels['period']}: {period_from} – {period_to}  ·  "
        f"{labels['sessions']}: {len(rows)}  ·  "
        f"{labels['total_energy']}: {energy_fmt} kWh",
        meta_style,
    ))
    story.append(Paragraph(f"{labels['generated']}: {now_fmt}", meta_style))
    story.append(Spacer(1, 4 * mm))

    if len(rows) == 0:
        story.append(Paragraph(labels["empty"], empty_style))
    else:
        col_widths = [
            22 * mm,  # Datum
            14 * mm,  # Start
            22 * mm,  # Enddatum
            14 * mm,  # Ende
            18 * mm,  # Dauer
            32 * mm,  # Ladestation
            12 * mm,  # Connector
            28 * mm,  # Fahrzeug
            28 * mm,  # RFID
            22 * mm,  # Energie
            45 * mm,  # Abbruchgrund
        ]
        table = Table(table_data, colWidths=col_widths, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f3a5f")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "DejaVu-Bold"),
            ("FONTNAME", (0, 1), (-1, -1), "DejaVu"),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [colors.white, colors.HexColor("#f3f6fa")]),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#c8d0dc")),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(table)

    doc.build(story)
    return buf.getvalue()
