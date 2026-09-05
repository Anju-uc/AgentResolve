"""Compact, robust AgentResolve forensic PDF packet generator."""
from __future__ import annotations

from io import BytesIO
from typing import Any, Dict, List

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import LongTable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

PAGE_W, _PAGE_H = A4
MARGIN = 15 * mm
CONTENT_W = PAGE_W - 2 * MARGIN
INK = colors.HexColor("#17212B")
MUTED = colors.HexColor("#5B6670")
LINE = colors.HexColor("#D6DCE2")
SOFT = colors.HexColor("#F5F7F9")
GREEN = colors.HexColor("#0B6E63")
GREEN_SOFT = colors.HexColor("#E7F4F1")
RED = colors.HexColor("#9F1D2E")
RED_SOFT = colors.HexColor("#FBECEF")
AMBER = colors.HexColor("#855900")
AMBER_SOFT = colors.HexColor("#FFF4D9")


def _safe(v: Any) -> str:
    if v is None or v == "":
        return "Not recorded"
    if hasattr(v, "value"):
        v = v.value
    if isinstance(v, dict):
        return "; ".join(f"{k}: {_safe(x)}" for k, x in v.items())
    if isinstance(v, (list, tuple, set)):
        return ", ".join(_safe(x) for x in v) or "None"
    if isinstance(v, bool):
        return "Yes" if v else "No"
    return str(v)


def _esc(v: Any) -> str:
    return _safe(v).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _styles() -> Dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("ar_title", parent=base["Title"], fontName="Helvetica-Bold", fontSize=18, leading=21, textColor=INK, alignment=TA_LEFT, spaceAfter=3),
        "sub": ParagraphStyle("ar_sub", parent=base["Normal"], fontName="Helvetica", fontSize=8, leading=10, textColor=MUTED, spaceAfter=8),
        "h": ParagraphStyle("ar_h", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=11, leading=13, textColor=INK, spaceBefore=7, spaceAfter=4),
        "body": ParagraphStyle("ar_body", parent=base["BodyText"], fontName="Helvetica", fontSize=8.2, leading=11, textColor=INK),
        "small": ParagraphStyle("ar_small", parent=base["BodyText"], fontName="Helvetica", fontSize=7, leading=9, textColor=MUTED),
        "th": ParagraphStyle("ar_th", parent=base["BodyText"], fontName="Helvetica-Bold", fontSize=6.6, leading=8, textColor=colors.white),
        "td": ParagraphStyle("ar_td", parent=base["BodyText"], fontName="Helvetica", fontSize=6.9, leading=8.8, textColor=INK),
        "tdb": ParagraphStyle("ar_tdb", parent=base["BodyText"], fontName="Helvetica-Bold", fontSize=6.9, leading=8.8, textColor=INK),
    }


def _p(v: Any, style: ParagraphStyle) -> Paragraph:
    return Paragraph(_esc(v), style)


def _footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setStrokeColor(LINE)
    canvas.line(MARGIN, 9 * mm, PAGE_W - MARGIN, 9 * mm)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(MUTED)
    canvas.drawString(MARGIN, 5.5 * mm, "AgentResolve | Forensic Evidence Packet")
    canvas.drawRightString(PAGE_W - MARGIN, 5.5 * mm, f"Page {doc.page}")
    canvas.restoreState()


def _box(title: str, body: str, styles: Dict[str, ParagraphStyle], tone: str = "normal") -> Table:
    palette = {
        "normal": (SOFT, LINE, INK),
        "good": (GREEN_SOFT, colors.HexColor("#A5D8CF"), GREEN),
        "alert": (RED_SOFT, colors.HexColor("#E2B4BC"), RED),
        "amber": (AMBER_SOFT, colors.HexColor("#E6C56B"), AMBER),
    }
    bg, border, heading = palette.get(tone, palette["normal"])
    t = Table([[Paragraph(_esc(title), ParagraphStyle("bh", parent=styles["body"], fontName="Helvetica-Bold", textColor=heading, spaceAfter=3))], [Paragraph(_esc(body), styles["body"])]], colWidths=[CONTENT_W])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg), ("BOX", (0, 0), (-1, -1), 0.6, border),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def _table(rows: List[List[Any]], widths: List[float], styles: Dict[str, ParagraphStyle]) -> LongTable:
    data = []
    for i, row in enumerate(rows):
        style = styles["th"] if i == 0 else styles["td"]
        data.append([_p(v, style) for v in row])
    t = LongTable(data, colWidths=widths, repeatRows=1, hAlign="LEFT", splitByRow=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), INK), ("GRID", (0, 0), (-1, -1), 0.35, LINE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SOFT]), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def _summary(meta: Dict[str, Any], attr: Dict[str, Any], styles: Dict[str, ParagraphStyle]) -> Table:
    primary = attr.get("primary_fault") or {}
    score = meta.get("forensic_score", attr.get("forensic_score", "Not recorded"))
    rows = [
        ["Transaction", meta.get("transaction_id")],
        ["Status", meta.get("status")],
        ["Incident", meta.get("incident_type")],
        ["Evidence coverage", f"{_safe(score)} / 100"],
        ["Primary attribution", f"{_safe(primary.get('category'))} · {_safe(primary.get('score'))}/100" if primary else "No supported attribution"],
        ["Preventability", attr.get("preventability")],
        ["Financial harm", f"{_safe(meta.get('economic_harm'))} {meta.get('harm_currency') or ''}".strip()],
    ]
    data = [[_p(k, styles["tdb"]), _p(v, styles["td"])] for k, v in rows]
    t = Table(data, colWidths=[45 * mm, CONTENT_W - 45 * mm], hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), SOFT), ("BOX", (0, 0), (-1, -1), 0.6, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.35, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def _rules(report: Dict[str, Any], styles: Dict[str, ParagraphStyle]) -> LongTable:
    rows = [["Rule", "Result", "Raw points", "Recorded basis"]]
    for item in report.get("rule_ledger") or []:
        details = []
        if item.get("evidence_factors"):
            details.append("Factors: " + ", ".join(map(str, item["evidence_factors"])))
        for e in item.get("evidence") or []:
            statement = e.get("statement") or ""
            if statement:
                details.append(statement)
        rows.append([_safe(item.get("category")), "TRIGGERED" if item.get("fired") else "CLEARED", _safe(item.get("raw_points")), " ".join(details) or "No supporting evidence established."])
    if len(rows) == 1:
        rows.append(["Rule ledger", "UNAVAILABLE", "0", "No canonical rule results were supplied by the report."])
    return _table(rows, [42 * mm, 23 * mm, 18 * mm, CONTENT_W - 83 * mm], styles)


def _evidence(report: Dict[str, Any], styles: Dict[str, ParagraphStyle]) -> LongTable:
    rows = [["Field", "Expected", "Observed", "Finding"]]
    for e in report.get("evidence_trace") or []:
        rows.append([_safe(e.get("field")), _safe(e.get("expected")), _safe(e.get("actual")), _safe(e.get("statement"))])
    if len(rows) == 1:
        rows.append(["None", "Not recorded", "Not recorded", "No positive evidence items were supplied."])
    return _table(rows, [24 * mm, 28 * mm, 29 * mm, CONTENT_W - 81 * mm], styles)


def _request_currency(report: Dict[str, Any]) -> str:
    return str(
        report.get("report_metadata", {}).get("display_currency")
        or report.get("recorded_facts", {}).get("display_currency")
        or "INR"
    ).upper()


def _currency_symbol(code: str) -> str:
    return {
        "INR": "₹",
        "USD": "$",
        "EUR": "€",
        "GBP": "£",
        "AED": "د.إ",
        "SGD": "S$",
        "AUD": "A$",
        "CAD": "C$",
        "JPY": "¥",
    }.get((code or "INR").upper(), "₹")


def _money(value_usd: Any, currency: str) -> str:
    if value_usd is None:
        return "Not recorded"

    rates = {
        "INR": 0.0119,
        "USD": 1.0,
        "EUR": 1.08,
        "GBP": 1.28,
        "AED": 0.2723,
        "SGD": 0.75,
        "AUD": 0.65,
        "CAD": 0.73,
        "JPY": 0.0068,
    }

    code = (currency or "INR").upper()
    rate = rates.get(code, rates["INR"])

    try:
        amount = float(value_usd) / rate
        return f"{_currency_symbol(code)}{amount:,.2f}"
    except (TypeError, ValueError, ZeroDivisionError):
        return _safe(value_usd)


def _facts(report: Dict[str, Any], styles: Dict[str, ParagraphStyle]) -> LongTable:
    facts = report.get("recorded_facts") or {}
    user = facts.get("user_request") or {}
    merchant = facts.get("merchant_snapshot") or {}
    decision = facts.get("agent_decision") or {}
    dispute = facts.get("dispute") or {}
    life = facts.get("lifecycle") or {}

    currency = _request_currency(report)

    constraints = user.get("constraints") or {}
    customer_price = constraints.get("price_usd")
    customer_operator = constraints.get(
        "price_usd_operator",
        "at most",
    )

    rows = [["Recorded fact", "Value"]]

    if user.get("text") is not None:
        rows.append(["User request", user.get("text")])

    if customer_price is not None:
        rows.append(
            [
                "Customer price limit",
                f"{customer_operator} {_money(customer_price, currency)}",
            ]
        )

    rows.extend(
        [
            (
                "Selected item",
                decision.get("selected_item_id"),
            ),
            (
                "Actual purchased price",
                (
                    decision.get("purchased_price_display")
                    or _money(
                        decision.get("purchased_price"),
                        currency,
                    )
                ),
            ),
            (
                "Purchased seller",
                decision.get("purchased_seller"),
            ),
            (
                "Merchant listed price",
                _money(
                    merchant.get("price"),
                    currency,
                ),
            ),
            (
                "Checkout price",
                _money(
                    merchant.get("price_at_checkout"),
                    currency,
                ),
            ),
            (
                "Validation",
                decision.get("validation_steps_performed"),
            ),
            (
                "Disputed field",
                dispute.get("disputed_field"),
            ),
            (
                "User claim",
                dispute.get("user_claim"),
            ),
            (
                "Lifecycle events",
                len(life.get("event_log") or [])
                if isinstance(life, dict)
                else None,
            ),
        ]
    )

    filtered_rows = [rows[0]]
    for key, value in rows[1:]:
        if value is not None and value != "":
            filtered_rows.append([key, _safe(value)])

    return _table(
        filtered_rows,
        [55 * mm, CONTENT_W - 55 * mm],
        styles,
    )


def _what_happened(report: Dict[str, Any]) -> str:
    meta = report.get("report_metadata") or {}
    attr = report.get("attribution_summary") or {}
    primary = attr.get("primary_fault") or {}
    evidence = report.get("evidence_trace") or []
    base = f"The transaction was classified as {_safe(meta.get('incident_type'))}."
    if primary:
        base += f" The strongest supported attribution is {_safe(primary.get('category'))} ({_safe(primary.get('score'))}/100)."
    else:
        base += " No supported primary attribution was established from the recorded evidence."
    if evidence:
        points = [str(e.get("statement")) for e in evidence[:3] if e.get("statement")]
        if points:
            base += " " + " ".join(points)
    return base


def build_forensic_pdf(report: Any) -> bytes:
    """Generate a paginated PDF from the report dictionary or compatible model."""
    if hasattr(report, "model_dump"):
        report = report.model_dump(mode="json")
    report = report if isinstance(report, dict) else {}

    styles = _styles()
    meta = report.get("report_metadata") or {}
    attr = report.get("attribution_summary") or {}
    cf = report.get("counterfactual_replay") or {}
    explanation = report.get("explanation") or {}
    flags = attr.get("data_flags") or []
    score = meta.get("forensic_score", attr.get("forensic_score"))
    primary = attr.get("primary_fault") or {}

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=15 * mm, bottomMargin=14 * mm,
        title=f"AgentResolve - {_safe(meta.get('transaction_id'))}", author="AgentResolve",
    )

    story: List[Any] = [
        Paragraph("AgentResolve — Forensic Evidence Packet", styles["title"]),
        Paragraph("Case-specific post-transaction reconstruction", styles["sub"]),
        _summary(meta, attr, styles), Spacer(1, 7),
        _box("What happened", _what_happened(report), styles, "alert" if primary else "good"),
        Paragraph("Original request", styles["h"]),
        Paragraph(_esc(((report.get("recorded_facts") or {}).get("user_request") or {}).get("text")), styles["body"]),
        Paragraph("Evidence supporting the finding", styles["h"]),
        _evidence(report, styles),
        Paragraph("Rule ledger", styles["h"]),
        Paragraph("All canonical rules available to the analyzer are recorded independently. CLEARED means the trigger conditions were not established by the supplied evidence.", styles["small"]),
        Spacer(1, 2), _rules(report, styles),
        Paragraph("Attribution", styles["h"]),
    ]

    attr_rows = [["Category", "Score", "Role"]]
    if primary:
        attr_rows.append([_safe(primary.get("category")), _safe(primary.get("score")), "Primary attribution"])
    for x in attr.get("contributing_factors") or []:
        attr_rows.append([_safe(x.get("category")), _safe(x.get("score")), "Contributing factor"])
    if len(attr_rows) == 1:
        attr_rows.append(["None", "—", "No supported attribution"])
    story.append(_table(attr_rows, [60 * mm, 25 * mm, CONTENT_W - 85 * mm], styles))

    if score is not None:
        breakdown = report.get("evidence_coverage") or meta.get("forensic_score_breakdown") or {}
        details = ", ".join(f"{str(k).replace('_', ' ').title()}: {_safe(v.get('percent') if isinstance(v, dict) else v)}%" for k, v in breakdown.items())
        story += [
            Paragraph("Evidence coverage", styles["h"]),
            _box(
                "Case-specific evidence coverage",
                f"Overall: {_safe(score)}/100. {details}" if details else f"Overall: {_safe(score)}/100.",
                styles,
            ),
        ]
        if breakdown:
            cov_rows = [["Component", "Coverage", "Recorded basis"]]
            for key, value in breakdown.items():
                if isinstance(value, dict):
                    pct = value.get("percent", value.get("earned", 0))
                    basis = value.get("reason", "Recorded evidence coverage")
                else:
                    pct = value
                    basis = "Recorded evidence coverage"
                cov_rows.append([str(key).replace("_", " ").title(), f"{_safe(pct)}%", _safe(basis)])
            story += [_table(cov_rows, [42 * mm, 22 * mm, CONTENT_W - 64 * mm], styles), Spacer(1, 6)]

    incident = (report.get("forensic_signals") or {}).get("incident") or {}
    if incident:
        rows = [["Field", "Recorded value"]]
        for k, v in incident.items():
            if v is not None:
                rows.append([k.replace("_", " ").title(), _safe(v)])
        story += [Paragraph("Incident record", styles["h"]), _table(rows, [55 * mm, CONTENT_W - 55 * mm], styles)]

    if cf:
        story += [Paragraph("Counterfactual replay", styles["h"]), _box("Replay result", f"Result: {_safe(cf.get('result'))}. Action: {_safe(cf.get('action'))}. Expected: {_safe(cf.get('expected'))}. Observed: {_safe(cf.get('actual'))}.", styles, "amber"), Spacer(1, 3)]
        if cf.get("narrative"):
            story.append(Paragraph(_esc(cf.get("narrative")), styles["body"]))

    story += [Paragraph("Recorded transaction facts", styles["h"]), _facts(report, styles)]

    if explanation.get("text"):
        story += [Paragraph("Explanation", styles["h"]), _box("Explanation-only narrative", _safe(explanation.get("text")), styles)]

    if flags:
        story += [Paragraph("Data quality flags", styles["h"]), _box("Review flags", "; ".join(map(str, flags)), styles, "amber")]

    story += [Spacer(1, 6), _box("Evidence boundary", "This packet reports only what the supplied recorded evidence supports. Missing or conflicting evidence can limit or stop the conclusion. Attribution and evidence-coverage scores are deterministic aids, not probabilities or legal liability findings. LLM text, when present, is explanation-only.", styles)]

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()
