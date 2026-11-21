"""PDF report generation for AgroVision AI.

Only values supplied in the report payload are included. Missing data is
reported as unavailable; this module never fabricates agricultural metrics.
"""
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether
)


def _paragraph(value, style):
    return Paragraph(escape(str(value if value is not None else "—")), style)


def build_agrovision_pdf(payload):
    """Create a downloadable PDF from live API results and saved farm inputs."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, rightMargin=16 * mm, leftMargin=16 * mm,
        topMargin=17 * mm, bottomMargin=17 * mm,
        title="AgroVision AI Agricultural Report",
        author="AgroVision AI"
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="AgroTitle", parent=styles["Title"], fontSize=20,
        leading=25, textColor=colors.HexColor("#174B32"), alignment=TA_CENTER,
        spaceAfter=5 * mm
    ))
    styles.add(ParagraphStyle(
        name="AgroSection", parent=styles["Heading2"], fontSize=13,
        textColor=colors.HexColor("#246342"), spaceBefore=5 * mm,
        spaceAfter=2 * mm
    ))
    styles.add(ParagraphStyle(
        name="AgroSmall", parent=styles["BodyText"], fontSize=8,
        leading=11, textColor=colors.HexColor("#58665E")
    ))

    story = [
        Paragraph("AGROVISION AI", styles["AgroTitle"]),
        Paragraph("Agricultural Intelligence Report", styles["Heading1"]),
        Paragraph(f"Generated: {_paragraph(payload.get('generated_at'), styles['AgroSmall']).getPlainText()}", styles["AgroSmall"]),
        Paragraph(f"Market region: {escape(str(payload.get('state') or 'Not selected'))} · Weather location: {escape(str(payload.get('city') or 'Not selected'))}", styles["AgroSmall"]),
        Spacer(1, 4 * mm),
    ]

    market = payload.get("market")
    story.append(Paragraph("1. Market Intelligence", styles["AgroSection"]))
    if market:
        rows = [
            ["Data provider", str(market.get("source") or "Unknown")],
            ["Data status", str(market.get("status") or "Unknown")],
            ["Retrieved at", str(market.get("fetched_at") or "Not supplied")],
            ["Records included", str(len(market.get("records", [])))],
        ]
        story.append(Table(rows, colWidths=[42 * mm, 130 * mm], style=TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EAF2EC")),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CAD5CC")),
            ("PADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ])))
        records = market.get("records", [])
        if records:
            headers = ["Date", "District", "Mandi", "Commodity", "Modal ₹/q"]
            data = [headers]
            for row in records[:30]:
                data.append([
                    str(row.get("date") or "—"), str(row.get("district") or "—"),
                    str(row.get("market") or "—"), str(row.get("commodity") or "—"),
                    (f"{float(row['modal_price']):,.2f}" if row.get("modal_price") not in (None, "") else "—")
                ])
            story.extend([Spacer(1, 3 * mm), Paragraph("Mandi records (first 30 matching rows)", styles["Heading3"]),
                          Table(data, repeatRows=1, colWidths=[25 * mm, 31 * mm, 38 * mm, 43 * mm, 28 * mm], style=TableStyle([
                              ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#246342")),
                              ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                              ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CFD8D1")),
                              ("FONTSIZE", (0, 0), (-1, -1), 7),
                              ("PADDING", (0, 0), (-1, -1), 4),
                              ("VALIGN", (0, 0), (-1, -1), "TOP"),
                          ]))])
        else:
            story.append(Paragraph("No mandi rows matched the selected filters.", styles["BodyText"]))
        if market.get("warning"):
            story.append(Paragraph(f"Provider note: {escape(str(market['warning']))}", styles["AgroSmall"]))
    else:
        story.append(Paragraph("Market data unavailable; no market figures are included.", styles["BodyText"]))

    weather = payload.get("weather")
    story.append(Paragraph("2. Weather Intelligence", styles["AgroSection"]))
    if weather:
        loc = weather.get("location", {})
        current = weather.get("current", {})
        daily = weather.get("daily", {})
        weather_rows = [
            ["Location", f"{loc.get('name', '—')}, {loc.get('state', '—')}, {loc.get('country', '—')}"],
            ["Temperature", f"{current.get('temperature_2m', '—')} °C"],
            ["Relative humidity", f"{current.get('relative_humidity_2m', '—')}%"],
            ["Current precipitation", f"{current.get('precipitation', '—')} mm"],
            ["Wind speed", f"{current.get('wind_speed_10m', '—')} km/h"],
        ]
        story.append(Table(weather_rows, colWidths=[42 * mm, 130 * mm], style=TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EAF2EC")),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CAD5CC")),
            ("PADDING", (0, 0), (-1, -1), 6),
        ])))
        times = daily.get("time", [])
        if times:
            forecast = [["Date", "Min °C", "Max °C", "Rain mm", "Rain chance %"]]
            for i, day in enumerate(times[:7]):
                def at(key):
                    values = daily.get(key, [])
                    return values[i] if i < len(values) else "—"
                forecast.append([day, at("temperature_2m_min"), at("temperature_2m_max"), at("precipitation_sum"), at("precipitation_probability_max")])
            story.extend([Spacer(1, 3 * mm), Paragraph("7-day forecast", styles["Heading3"]),
                          Table(forecast, repeatRows=1, colWidths=[35 * mm, 30 * mm, 30 * mm, 35 * mm, 42 * mm], style=TableStyle([
                              ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#246342")),
                              ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                              ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CFD8D1")),
                              ("FONTSIZE", (0, 0), (-1, -1), 8),
                              ("PADDING", (0, 0), (-1, -1), 5),
                          ]))])
    else:
        story.append(Paragraph("Weather data unavailable; no weather figures are included.", styles["BodyText"]))

    farm = payload.get("farm")
    story.append(Paragraph("3. Farm Financial Performance", styles["AgroSection"]))
    if farm:
        farm_rows = [
            ["Metric", "Value"],
            ["Crop", str(farm.get("crop", "—"))],
            ["Farm area", f"{farm.get('area_acres', '—')} acres"],
            ["Expected production", f"{farm.get('total_production_quintals', '—')} quintals"],
            ["Total cultivation cost", f"₹{farm.get('total_cultivation_cost', 0):,.2f}"],
            ["Expected revenue", f"₹{farm.get('gross_revenue', 0):,.2f}"],
            ["Estimated net profit/loss", f"₹{farm.get('net_profit', 0):,.2f}"],
            ["ROI", f"{farm.get('roi_percentage')}%" if farm.get("roi_percentage") is not None else "Not available"],
            ["Financial status", str(farm.get("financial_status", "—"))],
        ]
        story.append(Table(farm_rows, repeatRows=1, colWidths=[70 * mm, 102 * mm], style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#246342")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("BACKGROUND", (0, 1), (0, -1), colors.HexColor("#EAF2EC")),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CAD5CC")),
            ("PADDING", (0, 0), (-1, -1), 6),
        ])))
        story.append(Paragraph("Financial values are estimates based on user-entered assumptions, not measured farm outcomes.", styles["AgroSmall"]))
    else:
        story.append(Paragraph("No saved farm simulation was included in this report.", styles["BodyText"]))

    if payload.get("errors"):
        story.append(Paragraph("4. Data Retrieval Notes", styles["AgroSection"]))
        for note in payload["errors"]:
            story.append(Paragraph(f"• {escape(str(note))}", styles["BodyText"]))

    story.extend([
        Spacer(1, 6 * mm),
        Paragraph("Data interpretation", styles["AgroSection"]),
        Paragraph("Mandi prices are provider-reported market records and may be cached if live providers are unavailable. Weather values are Open-Meteo current conditions and forecast output. Farm financial results are calculated from user-entered assumptions. These sections represent different data types and should not be treated as guaranteed outcomes.", styles["AgroSmall"]),
        Spacer(1, 5 * mm),
        Paragraph("AgroVision AI · Agricultural Intelligence", styles["AgroSmall"]),
    ])

    doc.build(story)
    return buffer.getvalue()
