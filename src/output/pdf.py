import os
from xml.sax.saxutils import escape
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle, HRFlowable)

FONT_CANDIDATES = [
    ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
     "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
]


def _register_font():
    for reg, bold in FONT_CANDIDATES:
        if os.path.exists(reg):
            pdfmetrics.registerFont(TTFont("AppFont", reg))
            if os.path.exists(bold):
                pdfmetrics.registerFont(TTFont("AppFont-Bold", bold))
                return "AppFont", "AppFont-Bold"
            return "AppFont", "AppFont"
    return "Helvetica", "Helvetica-Bold"


def _table_style(base, bold, total_row=False):
    cmds = [
        ("FONTNAME", (0, 0), (-1, -1), base),
        ("FONTNAME", (0, 0), (-1, 0), bold),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f3a5f")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.lightgrey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f5f9")]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if total_row:
        cmds.append(("FONTNAME", (0, -1), (-1, -1), bold))
        cmds.append(("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#dde7f0")))
    return TableStyle(cmds)


def build_trip_pdf(data: dict, out_path: str) -> str:
    base, bold = _register_font()
    styles = getSampleStyleSheet()
    title = ParagraphStyle("T", parent=styles["Title"], fontName=bold, fontSize=20, spaceAfter=6)
    head = ParagraphStyle("H", parent=styles["Heading2"], fontName=bold, fontSize=13,
                          textColor=colors.HexColor("#1f3a5f"), spaceBefore=12, spaceAfter=4)
    body = ParagraphStyle("B", parent=styles["BodyText"], fontName=base, fontSize=10, leading=15)
    small = ParagraphStyle("S", parent=body, fontSize=8, textColor=colors.grey)
    headline = ParagraphStyle("HL", parent=body, fontName=bold, fontSize=11,
                              textColor=colors.HexColor("#0a7a4a"), spaceAfter=8)

    sym = data.get("currency_symbol", "")
    place = data.get("selected_place", "Your Trip")
    story = []

    story.append(Paragraph(f"Trip Plan: {escape(place)}", title))
    if data.get("budget_headline"):
        story.append(Paragraph(escape(data["budget_headline"]), headline))
    story.append(HRFlowable(width="100%", color=colors.lightgrey))

    # route table + booking links
    route = data.get("route", {})
    if route.get("legs"):
        story.append(Paragraph("Getting There", head))
        rows = [["From", "To", "Mode", "Approx cost/person"]]
        for leg in route["legs"]:
            if leg.get("cost_min") is not None:
                unit = "/vehicle" if leg.get("per_vehicle") else "/person"
                leg_cost = f"{sym}{leg['cost_min']}-{sym}{leg['cost_max']}{unit}"
            else:
                leg_cost = leg.get("note") or "verify before booking"
            rows.append([escape(leg["from_place"]), escape(leg["to_place"]),
                         escape(leg["mode"]), escape(leg_cost)])
        t = Table(rows, hAlign="LEFT", colWidths=[4*cm, 4*cm, 2.5*cm, 4.5*cm])
        t.setStyle(_table_style(base, bold))
        story.append(t)
        for leg in route["legs"]:
            links = leg.get("booking_links", [])
            if links:
                parts = [f'<a href="{escape(l["url"])}" color="blue">{escape(l["site"])}</a>'
                         for l in links]
                story.append(Paragraph(
                    f'Book {escape(leg["from_place"])} → {escape(leg["to_place"])}: '
                    + " | ".join(parts), body))

    # hotels
    story.append(Paragraph("Where to Stay", head))
    rc = data.get("room_config", {})
    if rc:
        story.append(Paragraph(f"Rooms: {escape(rc.get('description', ''))} "
                               f"({escape(rc.get('bed_types', ''))})", body))
    for h in data.get("hotels", []):
        price = f" - {sym}{h['per_night_min']}/night" if h.get("per_night_min") else ""
        story.append(Paragraph(f"&bull; {escape(h['name'])}{price}", body))
    h_links = data.get("hotel_booking_links", [])
    if h_links:
        parts = [f'<a href="{escape(l["url"])}" color="blue">{escape(l["site"])}</a>'
                 for l in h_links]
        story.append(Paragraph("Book stays: " + " | ".join(parts), body))

    # itinerary
    story.append(Paragraph("Day-by-Day Itinerary", head))
    for day in data.get("itinerary", []):
        story.append(Paragraph(f"<b>{escape(day['day_label'])}</b> ({escape(day['date'])})", body))
        for a in day["activities"]:
            story.append(Paragraph(f"&nbsp;&nbsp;&bull; {escape(a)}", body))
        story.append(Spacer(1, 4))

    # budget table
    budget = data.get("budget", {})
    if budget.get("items"):
        story.append(Paragraph("Budget Breakdown", head))
        rows = [["Item", "Amount", "Note"]]
        for i in budget["items"]:
            rows.append([escape(i["item"]), f"{sym}{i['amount']}", escape(i.get("note", ""))])
        rows.append(["TOTAL", f"{sym}{budget['total']}", ""])
        t = Table(rows, hAlign="LEFT", colWidths=[5*cm, 3*cm, 7*cm])
        t.setStyle(_table_style(base, bold, total_row=True))
        story.append(t)

    # packing, safety, booking order
    for hdr, key in [("Packing List", "packing_list"),
                     ("Safety & Seasonal Notes", "safety_notes"),
                     ("What to Book First", "booking_order")]:
        if data.get(key):
            story.append(Paragraph(hdr, head))
            for x in data[key]:
                story.append(Paragraph(f"&bull; {escape(x)}", body))

    story.append(Spacer(1, 10))
    if data.get("map_link"):
        story.append(Paragraph(f'<a href="{escape(data["map_link"])}" color="blue">'
                               f'Open {escape(place)} on the map</a>', body))
    story.append(Spacer(1, 6))
    story.append(Paragraph("Costs are estimates - verify fares and hotel prices on the booking "
                           "links before paying. Routes are grounded in live search.", small))

    SimpleDocTemplate(out_path, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm,
                      topMargin=2*cm, bottomMargin=2*cm, title=f"Trip Plan - {place}").build(story)
    return out_path