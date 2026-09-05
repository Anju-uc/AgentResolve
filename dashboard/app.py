"""AgentResolve - Streamlit forensic workstation frontend.

Replace only: dashboard/app.py
Presentation layer only. Uses the existing deterministic AgentResolve engine,
including the strict rules.py replacement, transaction models, simulator,
provenance verifier, report builder and evaluation runner.
"""
from __future__ import annotations

import html
import json
import math
import os
import re
import sys
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DASHBOARD_DIR = os.path.abspath(os.path.dirname(__file__))

if DASHBOARD_DIR in sys.path:
    sys.path.remove(DASHBOARD_DIR)

if ROOT_DIR in sys.path:
    sys.path.remove(ROOT_DIR)

sys.path.insert(0, ROOT_DIR)

from agent.simulator import PurchaseBlockedError, execute_purchase  # noqa: E402
from app.engine.analyzer import analyze_transaction  # noqa: E402
from app.engine.helpers import compare_values  # noqa: E402
from app.engine.provenance import verify_event_chain  # noqa: E402
from app.llm.explainer import generate_explanation  # noqa: E402
from app.models.transaction import Transaction  # noqa: E402
from app.reports.report_builder import build_dispute_report  # noqa: E402
from evaluation.evaluate import load_dataset, run_evaluation  # noqa: E402

try:
    from app.reports.pdf_packet import build_forensic_pdf  # noqa: E402
except Exception:
    build_forensic_pdf = None


st.set_page_config(
    page_title="AgentResolve — Transaction Forensics",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    r"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');
:root {
  --bg:#07090e; --sidebar:#0a0d13; --card:#0f131a; --card2:#0b1017;
  --border:#1a2230; --border2:#243044; --text:#f8fafc; --muted:#8493a8; --faint:#475569;
  --green:#10b981; --cyan:#38bdf8; --amber:#f59e0b; --red:#f43f5e; --purple:#a78bfa;
}
* { scrollbar-width: thin; scrollbar-color:#1e293b transparent; }
::-webkit-scrollbar { width:6px; height:6px; }
::-webkit-scrollbar-thumb { background:#1e293b; border-radius:4px; }
html, body, [class*="css"] { font-family:'Plus Jakarta Sans',sans-serif !important; }
.stApp { background:var(--bg); color:var(--text); }
.block-container { max-width:1440px; padding-top:2.6rem !important; padding-bottom:4rem; }
[data-testid="stHeader"] { background:rgba(7,9,14,.96) !important; z-index:1000 !important; }
[data-testid="stDecoration"] { display:none !important; }
[data-testid="stToolbar"] { z-index:1100 !important; }
.ar-topbar { margin-top:.15rem; margin-bottom:1rem; padding:.6rem 0 .85rem; border-bottom:1px solid #141b27; }
section[data-testid="stSidebar"] { background:var(--sidebar)!important; border-right:1px solid var(--border)!important; }
section[data-testid="stSidebar"] .block-container { padding:1rem .85rem!important; }
section[data-testid="stSidebar"] .stButton > button { justify-content:flex-start!important; background:transparent!important; border:1px solid transparent!important; color:#94a3b8!important; border-radius:8px!important; font-weight:600!important; }
section[data-testid="stSidebar"] .stButton > button:hover { background:#111722!important; color:var(--text)!important; }
section[data-testid="stSidebar"] .stButton > button[kind="primary"] { background:#111927!important; border-color:#1d2b42!important; color:#38bdf8!important; }
.stButton > button[kind="primary"] { background:#059669!important; border:1px solid #10b981!important; color:white!important; border-radius:8px!important; font-weight:700!important; }
.stButton > button[kind="primary"]:hover { background:#10b981!important; box-shadow:0 5px 18px rgba(16,185,129,.25)!important; }
[data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea { background:#0c1118!important; border-color:var(--border)!important; color:var(--text)!important; }
[data-baseweb="select"] > div { background:#0c1118!important; border-color:var(--border)!important; }
.ar-card { background:linear-gradient(160deg,var(--card),var(--card2)); border:1px solid var(--border); border-radius:12px; padding:1rem 1.1rem; min-height:100px; }
.ar-card:hover { border-color:var(--border2); }
.ar-label { color:#718096; font-size:.64rem; text-transform:uppercase; letter-spacing:.08em; font-weight:700; }
.ar-value { font-size:1.65rem; font-weight:800; margin-top:.2rem; }
.ar-sub { color:var(--muted); font-size:.72rem; margin-top:.25rem; }
.small-note { color:#66758a; font-size:.68rem; line-height:1.55; }
.badge { display:inline-flex; gap:.35rem; align-items:center; padding:.24rem .6rem; border-radius:999px; font-size:.66rem; font-weight:700; font-family:'JetBrains Mono',monospace; }
.dot { width:6px; height:6px; border-radius:50%; display:inline-block; }
.badge-green { background:rgba(16,185,129,.11); color:#34d399; }.badge-green .dot{background:#34d399;}
.badge-red { background:rgba(244,63,94,.11); color:#fb7185; }.badge-red .dot{background:#fb7185;}
.badge-amber { background:rgba(245,158,11,.11); color:#fbbf24; }.badge-amber .dot{background:#fbbf24;}
.badge-cyan { background:rgba(56,189,248,.11); color:#38bdf8; }.badge-cyan .dot{background:#38bdf8;}
.badge-purple { background:rgba(167,139,250,.11); color:#c4b5fd; }.badge-purple .dot{background:#c4b5fd;}
.ops-table { width:100%; border-collapse:collapse; background:var(--card); border:1px solid var(--border); border-radius:12px; overflow:hidden; }
.ops-table th { background:#0d1117; color:#64748b; text-align:left; padding:.8rem 1rem; font-size:.64rem; letter-spacing:.08em; text-transform:uppercase; border-bottom:1px solid var(--border); }
.ops-table td { padding:.8rem 1rem; color:#cbd5e1; border-bottom:1px solid #131a24; font-size:.78rem; vertical-align:top; }
.ops-table tr:last-child td { border-bottom:none; }
.evidence { background:#0f141b; border:1px solid var(--border); border-radius:10px; padding:.85rem .95rem; margin:.5rem 0; }
.evidence .field { color:#7dd3fc; font:600 .68rem 'JetBrains Mono',monospace; }
.evidence .copy { color:#dbe3ea; font-size:.77rem; line-height:1.55; margin-top:.25rem; }
.evidence .meta { color:#738197; font-size:.64rem; margin-top:.3rem; line-height:1.5; }
.rule { background:#0e1319; border:1px solid var(--border); border-radius:10px; padding:.8rem .9rem; margin:.5rem 0; }
.rule-top { display:flex; justify-content:space-between; align-items:center; gap:1rem; }
.rule-title { font-size:.82rem; font-weight:800; }
.rule-state { font:.68rem 'JetBrains Mono',monospace; font-weight:800; }
.gate { display:grid; grid-template-columns:1.45fr .9fr 3fr; gap:.55rem; padding:.45rem .5rem; border-top:1px solid #18202b; font-size:.7rem; align-items:start; }
.gate:first-child { border-top:0; }
.gate-name { color:#cbd5e1; font-weight:700; }
.gate-pass { color:#34d399; font-weight:800; }.gate-fail{color:#fb7185;font-weight:800}.gate-na{color:#fbbf24;font-weight:800}.gate-neutral{color:#94a3b8;font-weight:800}
.finding { margin-top:.65rem; padding:.7rem .8rem; border-radius:8px; background:#091018; border:1px solid #182537; color:#aab7c7; font-size:.74rem; line-height:1.58; }
.score-shell { background:#0f131a; border:1px solid var(--border); border-radius:12px; padding:1rem; text-align:center; }
.score-breakdown { display:grid; grid-template-columns:1fr 1fr; gap:.45rem; margin-top:.75rem; text-align:left; }
.score-item { background:#0b1017; border:1px solid #172231; border-radius:8px; padding:.45rem .55rem; }
.score-item .k { color:#708096; font-size:.58rem; text-transform:uppercase; letter-spacing:.06em; }
.score-item .v { color:#dbe5ee; font-size:.72rem; font-weight:700; margin-top:.1rem; }
.stepbar { display:grid; grid-template-columns:repeat(8,minmax(0,1fr)); gap:.35rem; margin:.8rem 0 1rem; }
.stepbox { border:1px solid var(--border); background:#0d1218; border-radius:8px; padding:.55rem .5rem; min-height:63px; }
.stepbox .n { color:#64748b; font:600 .58rem 'JetBrains Mono',monospace; }
.stepbox .t { color:#dbe4eb; font-size:.65rem; font-weight:700; margin-top:.2rem; line-height:1.25; }
.stepbox .s { font-size:.58rem; margin-top:.2rem; }
.step-ok { color:#34d399; }.step-warn{color:#fbbf24;}.step-bad{color:#fb7185;}.step-na{color:#94a3b8;}
.summary-grid { display:grid; grid-template-columns:1fr 1fr; gap:.65rem; }
@media (max-width:1000px){ .stepbar{grid-template-columns:repeat(4,minmax(0,1fr));}.summary-grid{grid-template-columns:1fr;} }
</style>
""",
    unsafe_allow_html=True,
)


CURRENCY = {
    "INR": {"symbol": "₹", "label": "Indian Rupee", "usd": 0.0119},
    "USD": {"symbol": "$", "label": "US Dollar", "usd": 1.0},
    "EUR": {"symbol": "€", "label": "Euro", "usd": 1.08},
    "GBP": {"symbol": "£", "label": "British Pound", "usd": 1.28},
    "AED": {"symbol": "د.إ", "label": "UAE Dirham", "usd": 0.2723},
    "SGD": {"symbol": "S$", "label": "Singapore Dollar", "usd": 0.75},
    "AUD": {"symbol": "A$", "label": "Australian Dollar", "usd": 0.65},
    "CAD": {"symbol": "C$", "label": "Canadian Dollar", "usd": 0.73},
    "JPY": {"symbol": "¥", "label": "Japanese Yen", "usd": 0.0068},
}

NAV = [
    ("Overview", "⌂"), ("Investigations", "⌕"), ("Transactions", "▦"),
    ("Disputes", "▤"), ("Evidence", "◈"), ("Test Lab", "⚗"),
    ("Evaluation", "▥"), ("System", "⚙"), ("Shopping Agent", "✦"),
]


def init_state() -> None:
    defaults = {
        "page": "Overview",
        "active_txn": None,
        "currency": "INR",
        "search": "",
        "global_search": "",
        "eval_result": None,
        "show_json_import": False,
        "test_lab_selected": None,
        "shopping_result": None,
        "shopping_query": "",
        "uploaded_txn": None,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


init_state()


def esc(v: Any) -> str:
    return html.escape(str(v)) if v is not None else "—"


def human(v: Any) -> str:
    text = str(getattr(v, "value", v)) if v is not None else "—"
    return text.replace("_", " ").title()


def money(usd_value: Any, display_code: Optional[str] = None) -> str:
    if usd_value is None:
        return "Not recorded"
    code = display_code or st.session_state.currency
    meta = CURRENCY.get(code, CURRENCY["INR"])
    try:
        return f"{meta['symbol']}{float(usd_value) / meta['usd']:,.2f}"
    except (ValueError, TypeError):
        return str(usd_value)


def localize_engine_text(text: str) -> str:
    """Localize only engine-generated $ amounts; explicit user request text remains untouched."""
    if not text:
        return text
    return re.sub(
        r"\$([0-9][0-9,]*(?:\.[0-9]+)?)",
        lambda m: money(float(m.group(1).replace(",", ""))),
        text,
    )


def load_cases() -> Dict[str, Dict[str, Any]]:
    cases: Dict[str, Dict[str, Any]] = OrderedDict()
    for filename, label in (
        ("development_cases.json", "DEV"),
        ("holdout_cases.json", "HOLDOUT"),
        ("incident_cases.json", "OPS"),
    ):
        path = os.path.join(ROOT_DIR, "data", filename)
        if not os.path.exists(path):
            continue
        try:
            for txn in load_dataset(path):
                cases[txn.transaction_id] = {"txn": txn, "label": label}
        except Exception:
            continue
    return cases


def safe_analysis(txn: Transaction):
    result = analyze_transaction(txn)
    try:
        return generate_explanation(result)
    except Exception:
        return result


def set_active(txn: Transaction, page: str = "Investigations") -> None:
    st.session_state.active_txn = txn.model_dump()
    st.session_state.page = page


def active_transaction() -> Optional[Transaction]:
    raw = st.session_state.get("active_txn")
    if not raw:
        return None
    try:
        return Transaction.model_validate(raw)
    except Exception:
        st.session_state.active_txn = None
        return None


# -----------------------------------------------------------------------------
# Dynamic evidence score
# -----------------------------------------------------------------------------
def _constraint_fields(txn: Transaction) -> List[str]:
    c = txn.user_request.explicit_constraints
    fields: List[str] = []
    for field in ("price_usd", "ram_gb", "storage_gb", "seller", "delivery_days", "color", "condition"):
        if getattr(c, field, None) is not None:
            fields.append(field)
    for field, value in (getattr(c, "custom_attributes", {}) or {}).items():
        if value is not None:
            fields.append(field)
    return fields


def _field_label(field: str) -> str:
    return {
        "price_usd": "Price", "ram_gb": "RAM", "storage_gb": "Storage",
        "seller": "Seller", "delivery_days": "Delivery", "color": "Color",
        "condition": "Condition",
    }.get(field, field.replace("_", " ").title())


def _field_target(txn: Transaction, field: str) -> Tuple[Any, Optional[str]]:
    c = txn.user_request.explicit_constraints
    target = getattr(c, field, None)
    op = getattr(c, f"{field}_operator", None)
    if target is None and field in (getattr(c, "custom_attributes", {}) or {}):
        val = (c.custom_attributes or {}).get(field)
        if isinstance(val, dict):
            return val.get("value"), val.get("operator")
        return val, "exactly"
    return target, op


def _field_value(txn: Transaction, field: str) -> Any:
    m = txn.merchant_snapshot
    d = txn.agent_decision
    attrs = getattr(m, "attributes", {}) or {}
    specs = getattr(m, "specs", {}) or {}
    if field == "price_usd":
        return getattr(d, "purchased_price", None) if getattr(d, "purchased_price", None) is not None else getattr(m, "price", None)
    if field == "ram_gb":
        return getattr(d, "purchased_ram_gb", None) if getattr(d, "purchased_ram_gb", None) is not None else getattr(m, "ram_gb_actual", None) or getattr(m, "ram_gb", None)
    if field == "storage_gb":
        return getattr(m, "storage_gb_actual", None) or getattr(m, "storage_gb", None)
    if field == "seller":
        return getattr(d, "purchased_seller", None) or getattr(m, "seller_at_checkout", None) or getattr(m, "seller", None)
    if field == "delivery_days":
        return getattr(d, "purchased_delivery_days", None) or getattr(m, "delivery_days_actual", None) or getattr(m, "delivery_days", None)
    if field == "color":
        da = getattr(d, "attributes", {}) or {}
        return da.get("color") or getattr(m, "color_actual", None) or getattr(m, "color", None) or attrs.get("color") or specs.get("color")
    if field == "condition":
        return specs.get("condition") or attrs.get("condition")
    item = attrs.get(field)
    if item is not None:
        return getattr(item, "delivered", None) or getattr(item, "checkout", None) or getattr(item, "advertised", None)
    return specs.get(field)


def _rule_result_map(analysis: Any) -> Dict[str, Any]:
    return {
        getattr(getattr(rule, "category", None), "value", str(getattr(rule, "category", "RULE"))): rule
        for rule in (getattr(analysis, "all_rule_results", []) or [])
    }


def evidence_score(txn: Transaction, analysis: Any) -> Tuple[int, Dict[str, int]]:
    """Strict, case-specific evidence coverage score.

    This is NOT a fault probability and is NOT derived from the attribution score.
    The score measures whether the record contains enough independent evidence to
    support a serious forensic reconstruction.
    """
    parts: Dict[str, int] = {}
    raw = (txn.user_request.raw_text or "").strip()
    parts["request"] = 10 if raw else 0

    fields = _constraint_fields(txn)
    observed_count = 0
    if fields:
        for field in fields:
            target, _op = _field_target(txn, field)
            observed = _field_value(txn, field)
            if target is not None and observed is not None:
                observed_count += 1
        parts["constraint-evidence"] = round(20 * observed_count / len(fields))
    else:
        parts["constraint-evidence"] = 4 if raw else 0

    trace = list(getattr(txn.agent_interpretation, "execution_trace", []) or [])
    access = getattr(txn.agent_interpretation, "accessed_constraint_keys", []) or []
    if trace:
        # A trace is useful only when it has multiple meaningful execution records.
        meaningful = sum(
            1 for e in trace
            if str(getattr(e, "action", "") or (e.get("action", "") if isinstance(e, dict) else "")).strip()
        )
        parts["agent-evidence"] = 15 if meaningful >= 6 else 11 if meaningful >= 3 else 7
    elif access:
        parts["agent-evidence"] = 5
    else:
        parts["agent-evidence"] = 0

    d = txn.agent_decision
    decision_fields = [
        getattr(d, "selected_item_id", None),
        getattr(d, "purchased_price", None),
        getattr(d, "purchased_seller", None),
        getattr(d, "validation_steps_performed", None),
    ]
    parts["decision"] = round(12 * sum(v not in (None, [], "") for v in decision_fields) / len(decision_fields))

    life = getattr(txn, "lifecycle", None)
    event_log = list(getattr(life, "event_log", []) or []) if life else []
    parts["lifecycle"] = 15 if len(event_log) >= 8 else 11 if len(event_log) >= 4 else 6 if event_log else 0

    dispute = getattr(txn, "dispute", None)
    claim = str(getattr(dispute, "user_claim", "") or "").strip()
    parts["dispute"] = 5 if claim and claim.lower() != "no dispute filed yet" else 1 if dispute else 0

    rules = getattr(analysis, "all_rule_results", []) or []
    parts["rule-audit"] = 10 if len(rules) == 5 else 5 if rules else 0

    integrity_points = 0
    if event_log:
        try:
            integrity, missing = verify_event_chain(event_log)
            integ = str(integrity).upper()
            if integ in {"VALID", "VERIFIED", "RECORDED"} and not missing:
                integrity_points = 8
            elif not missing:
                integrity_points = 5
            else:
                integrity_points = 2
        except Exception:
            integrity_points = 1
    parts["integrity"] = integrity_points

    raw_total = sum(parts.values())
    score = max(0, min(100, raw_total))

    # Critical-evidence ceilings prevent a sparse record from appearing "strong"
    # simply because several easy metadata fields are present.
    if not raw:
        score = min(score, 25)
    if fields and observed_count < len(fields):
        score = min(score, 75)
    if fields and observed_count == 0:
        score = min(score, 45)
    if not trace and not access:
        score = min(score, 60)
    if not event_log:
        score = min(score, 70)
    if not getattr(analysis, "all_rule_results", None):
        score = min(score, 55)
    if not claim and dispute is None:
        score = min(score, 90)

    return int(score), parts

def score_band(score: int) -> Tuple[str, str]:
    if score >= 85: return "STRONG", "badge-green"
    if score >= 70: return "MODERATE", "badge-cyan"
    if score >= 50: return "LIMITED", "badge-amber"
    return "WEAK", "badge-red"


def render_score_meter(score: int, breakdown: Optional[Dict[str, int]] = None, label: str = "Evidence Coverage") -> None:
    pct = max(0, min(100, int(score)))
    radius = 67
    circumference = math.pi * radius
    offset = circumference - (circumference * pct / 100.0)
    band, badge = score_band(pct)
    st.markdown(
        f"""
        <div class="score-shell">
          <svg width="190" height="118" viewBox="0 0 190 118">
            <defs><linearGradient id="scoreGrad_{pct}" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stop-color="#f43f5e"/><stop offset="50%" stop-color="#f59e0b"/><stop offset="100%" stop-color="#10b981"/>
            </linearGradient></defs>
            <path d="M 24 97 A 67 67 0 0 1 166 97" fill="none" stroke="#1a2333" stroke-width="15" stroke-linecap="round"/>
            <path d="M 24 97 A 67 67 0 0 1 166 97" fill="none" stroke="url(#scoreGrad_{pct})" stroke-width="15" stroke-linecap="round" stroke-dasharray="{circumference}" stroke-dashoffset="{offset}"/>
          </svg>
          <div style="margin-top:-78px; position:relative;">
            <div style="font-size:.66rem;color:#8493a8;font-weight:700;letter-spacing:.06em;text-transform:uppercase;">{esc(label)}</div>
            <div style="font-size:1.9rem;font-weight:800;color:#f8fafc;">{pct}%</div>
          </div>
          <div style="margin-top:46px;"><span class="badge {badge}"><span class="dot"></span>{band}</span></div>
          <div class="small-note" style="margin-top:.35rem;">Measures how much independent transaction evidence is actually present. It is not a probability of fault.</div>
          {"<div class='score-breakdown'>" + "".join(f"<div class='score-item'><div class='k'>{esc(k)}</div><div class='v'>+{int(v)}</div></div>" for k,v in breakdown.items()) + "</div>" if breakdown else ""}
        </div>
        """,
        unsafe_allow_html=True,
    )


# -----------------------------------------------------------------------------
# Forensic interpretation
# -----------------------------------------------------------------------------
def operator_text(operator: Any, target: Any) -> str:
    if operator is None:
        return str(target)
    return f"{operator} {target}"



def render_rule_ledger(txn: Transaction, analysis: Any) -> None:
    st.session_state._current_analysis_obj = analysis
    rules = getattr(analysis, "all_rule_results", []) or []
    st.markdown("### Rule Ledger")
    st.caption("Every canonical rule is shown. A trigger requires evidence; a cleared rule explains why it did not fire.")
    if not rules:
        st.warning("No canonical rule results are available because the evidence boundary stopped analysis.")
        return
    for rule in rules:
        category = getattr(getattr(rule, "category", None), "value", str(getattr(rule, "category", "RULE")))
        fired = bool(getattr(rule, "fired", False))
        title = human(category)
        state = "TRIGGERED" if fired else "CLEARED"
        state_cls = "badge-red" if fired else "badge-green"
        st.markdown(
            f"<div class='rule'><div class='rule-top'><div class='rule-title'>{esc(title)}</div><span class='badge {state_cls}'><span class='dot'></span>{state}</span></div>",
            unsafe_allow_html=True,
        )

        evidence_items = getattr(rule, "evidence", []) or []
        factors = getattr(rule, "evidence_factors", []) or []
        if evidence_items:
            for e in evidence_items:
                field = getattr(e, "field", "Evidence")
                statement = getattr(e, "evidence_statement", "Recorded evidence.")
                expected = getattr(e, "expected_value", None)
                actual = getattr(e, "actual_value", None)
                st.markdown(
                    f"<div class='finding'><strong>{esc(field)}</strong><br>{esc(statement)}<br><span class='small-note'>Expected: {esc(expected)} · Observed: {esc(actual)}</span></div>",
                    unsafe_allow_html=True,
                )
        if factors:
            st.markdown("<div class='small-note' style='margin-top:.45rem;'>Evaluation factors:</div>", unsafe_allow_html=True)
            for factor in factors:
                st.markdown(f"<div class='finding'>{esc(factor)}</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    st.session_state._current_analysis_obj = None


def render_evaluation_path(txn: Transaction, analysis: Any) -> None:
    status = getattr(getattr(analysis, "status", None), "value", "")
    has_rules = bool(getattr(analysis, "all_rule_results", []))
    has_trace = bool(getattr(txn.agent_interpretation, "execution_trace", []) or [])
    has_lifecycle = bool(getattr(getattr(txn, "lifecycle", None), "event_log", []) or [])
    has_cf = bool(getattr(analysis, "counterfactual", None))
    steps = [
        ("01", "Evidence boundary", "PASS" if status == "ANALYZED" else "BLOCKED", "step-ok" if status == "ANALYZED" else "step-bad"),
        ("02", "Incident classification", "DONE" if getattr(analysis, "incident", None) else "NOT ESTABLISHED", "step-ok" if getattr(analysis, "incident", None) else "step-warn"),
        ("03", "Agent execution evidence", "RECORDED" if has_trace else "LIMITED", "step-ok" if has_trace else "step-warn"),
        ("04", "Five-rule evaluation", "5 / 5" if len(getattr(analysis, "all_rule_results", []) or []) == 5 else "BLOCKED", "step-ok" if len(getattr(analysis, "all_rule_results", []) or []) == 5 else "step-bad"),
        ("05", "Attribution", "CALCULATED" if getattr(analysis, "primary_fault", None) else "NONE", "step-ok" if getattr(analysis, "primary_fault", None) else "step-na"),
        ("06", "Lifecycle evidence", "RECORDED" if has_lifecycle else "LIMITED", "step-ok" if has_lifecycle else "step-warn"),
        ("07", "Counterfactual", "RUN" if has_cf else "N/A", "step-ok" if has_cf else "step-na"),
        ("08", "Final finding", "READY" if status == "ANALYZED" else "REVIEW", "step-ok" if status == "ANALYZED" else "step-warn"),
    ]
    st.markdown("<div class='stepbar'>" + "".join(f"<div class='stepbox'><div class='n'>{n}</div><div class='t'>{esc(title)}</div><div class='s {cls}'>{esc(state)}</div></div>" for n,title,state,cls in steps) + "</div>", unsafe_allow_html=True)


def render_diff(txn: Transaction) -> None:
    st.markdown("### State Evidence")
    st.caption("User requirement → merchant advertised state → checkout/purchase → delivered/actual state")
    c = txn.user_request.explicit_constraints
    rows = []
    fields = _constraint_fields(txn)
    for field in fields:
        target, op = _field_target(txn, field)
        adv = getattr(txn.merchant_snapshot, field, None)
        chk = getattr(txn.merchant_snapshot, f"{field}_at_checkout", None)
        actual = _field_value(txn, field)
        if field == "price_usd":
            adv = getattr(txn.merchant_snapshot, "price", None)
            chk = getattr(txn.merchant_snapshot, "price_at_checkout", None)
        elif field == "ram_gb":
            chk = getattr(txn.agent_decision, "purchased_ram_gb", None)
        elif field == "storage_gb":
            actual = getattr(txn.merchant_snapshot, "storage_gb_actual", None) or getattr(txn.merchant_snapshot, "storage_gb", None)
        elif field == "delivery_days":
            adv = getattr(txn.merchant_snapshot, "delivery_days", None)
            chk = getattr(txn.agent_decision, "purchased_delivery_days", None)
        elif field == "seller":
            adv = getattr(txn.merchant_snapshot, "seller", None)
            chk = getattr(txn.merchant_snapshot, "seller_at_checkout", None)
        values = [adv, chk, actual]
        consistency = len({str(v).strip().lower() for v in values if v is not None}) <= 1
        state = "CONSISTENT" if consistency else "DRIFT"
        if field == "price_usd":
            target_text, adv_text, chk_text, actual_text = money(target), money(adv), money(chk), money(actual)
        else:
            target_text, adv_text, chk_text, actual_text = operator_text(op, target), adv, chk, actual
        rows.append((field, target_text, adv_text, chk_text, actual_text, state))
    if not rows:
        st.info("No explicitly constrained attributes are recorded.")
        return
    body = []
    for field, target_text, adv, chk, actual, state in rows:
        badge = "badge-red" if state == "DRIFT" else "badge-green"
        body.append(f"<tr><td><strong>{esc(_field_label(field))}</strong></td><td>{esc(target_text)}</td><td>{esc(adv)}</td><td>{esc(chk)}</td><td>{esc(actual)}</td><td><span class='badge {badge}'><span class='dot'></span>{state}</span></td></tr>")
    st.markdown("<table class='ops-table'><thead><tr><th>Attribute</th><th>Requirement</th><th>Advertised</th><th>Checkout / Purchase</th><th>Actual / Delivered</th><th>State</th></tr></thead><tbody>" + "".join(body) + "</tbody></table>", unsafe_allow_html=True)


def render_validation_blackbox(txn: Transaction) -> None:
    fields = _constraint_fields(txn)
    if not fields:
        st.info("No explicit constraints were recorded.")
        return
    trace = getattr(txn.agent_interpretation, "execution_trace", []) or []
    for field in fields:
        target, op = _field_target(txn, field)
        actual = _field_value(txn, field)
        result = compare_values(actual, target, op)
        matching = []
        for event in trace:
            action = str(getattr(event, "action", "")).lower()
            args = getattr(event, "arguments", {}) or {}
            observed = str(args.get("field", "")).lower()
            if "validat" in action and observed in {field.lower(), field.replace("_gb", "").replace("_usd", ""), _field_label(field).lower()}:
                matching.append(event)
        validation = "NOT RECORDED"
        if matching:
            for event in reversed(matching):
                res = getattr(event, "result", {}) or {}
                passed = res.get("passed") if "passed" in res else res.get("valid")
                validation = "PASSED" if passed is True else "FAILED" if passed is False else "RECORDED"
                if passed is not None:
                    break
        elif not trace and field in (getattr(txn.agent_decision, "validation_steps_performed", []) or []):
            validation = "RECORDED"
        badge = "badge-green" if validation == "PASSED" else "badge-red" if validation == "FAILED" else "badge-amber"
        actual_display = money(actual) if field == "price_usd" else actual
        expected_display = operator_text(op, money(target) if field == "price_usd" else target)
        verdict = "SATISFIED" if result is True else "VIOLATED" if result is False else "UNDETERMINED"
        verdict_cls = "badge-green" if result is True else "badge-red" if result is False else "badge-amber"
        st.markdown(
            f"<div class='evidence'><div style='display:flex;justify-content:space-between;gap:1rem;'><div class='field'>{esc(_field_label(field))}</div><div><span class='badge {badge}'><span class='dot'></span>{validation}</span> <span class='badge {verdict_cls}'><span class='dot'></span>{verdict}</span></div></div><div class='copy'>Requirement: <strong>{esc(expected_display)}</strong> · Observed: <strong>{esc(actual_display)}</strong></div><div class='meta'>The validation state is shown from field-level execution evidence when available. A generic success event is not treated as proof that the requirement passed.</div></div>",
            unsafe_allow_html=True,
        )


def render_timeline(txn: Transaction) -> None:
    events = getattr(txn.agent_interpretation, "execution_trace", []) or []
    if not events and getattr(txn, "lifecycle", None):
        events = getattr(txn.lifecycle, "event_log", []) or []
    if not events:
        st.info("No lifecycle or execution event timeline is recorded for this case.")
        return
    for idx, event in enumerate(events, 1):
        if isinstance(event, dict):
            action = event.get("action", "event"); timestamp = event.get("timestamp", "recorded"); status = event.get("status", "RECORDED"); result = event.get("result", {})
        else:
            action = getattr(event, "action", "event"); timestamp = getattr(event, "timestamp", "recorded"); status = getattr(event, "status", "RECORDED"); result = getattr(event, "result", {}) or {}
        st.markdown(
            f"<div class='evidence'><div class='field'>STEP {idx:02d} · {esc(str(action).upper())}</div><div class='copy'>{esc(human(status))} · {esc(json.dumps(result) if result else 'Recorded event')}</div><div class='meta'>{esc(timestamp)}</div></div>",
            unsafe_allow_html=True,
        )


def forensic_summary(txn: Transaction, analysis: Any) -> str:
    if getattr(getattr(analysis, "status", None), "value", "") == "INSUFFICIENT_EVIDENCE":
        missing = ", ".join(getattr(analysis, "missing_fields", []) or []) or "required evidence"
        return f"The investigation stopped at the evidence boundary because {missing} was not sufficiently recorded. AgentResolve does not convert missing evidence into a guessed cause."
    incident = human(getattr(getattr(analysis, "incident", None), "incident_type", None) or "UNCLASSIFIED")
    pf = getattr(analysis, "primary_fault", None)
    if pf:
        fault = human(getattr(pf, "category", None))
        score = getattr(pf, "score", None)
        lead = f"The recorded transaction is classified as {incident}. The strongest supported attribution is {fault} with an attribution score of {score}/100."
    else:
        lead = f"The recorded transaction is classified as {incident}. No canonical fault category is sufficiently supported by the evidence."
    evidence = getattr(analysis, "evidence", []) or []
    detail = " ".join(getattr(e, "evidence_statement", "") for e in evidence[:4]).strip()
    cf = getattr(analysis, "counterfactual", None)
    cf_text = getattr(cf, "narrative", "") if cf else ""
    extra = f" Counterfactual replay: {cf_text}" if cf_text else ""
    return (lead + (f" Key evidence: {detail}" if detail else "") + extra).strip()


def render_case(txn: Transaction) -> None:
    analysis = safe_analysis(txn)
    score, breakdown = evidence_score(txn, analysis)
    st.session_state._current_analysis_obj = analysis
    incident = human(getattr(getattr(analysis, "incident", None), "incident_type", None) or "UNCLASSIFIED")
    fault_obj = getattr(analysis, "primary_fault", None)
    fault = human(getattr(fault_obj, "category", None) or "NO_FAULT_DETECTED")
    prevent = human(getattr(analysis, "preventability", "N/A"))
    status = human(getattr(analysis, "status", "ANALYZED"))

    if st.button("← Back to Investigations"):
        st.session_state.active_txn = None
        st.rerun()
    st.markdown(f"<div class='ar-label'>INVESTIGATION / CASE</div><h2 style='margin:.1rem 0;font-weight:800;'>{esc(txn.transaction_id)}</h2><div class='small-note'>{esc(txn.user_request.raw_text)}</div>", unsafe_allow_html=True)

    render_evaluation_path(txn, analysis)

    left, right = st.columns([1.05, 2.2])
    with left:
        render_score_meter(score, breakdown)
    with right:
        pscore = getattr(fault_obj, "score", None) if fault_obj else None
        pscore_badge = f"<span class='badge badge-red'><span class='dot'></span>Attribution Score · {pscore}/100</span>" if pscore is not None else ""
        st.markdown(
            f"<div class='ar-card'><div class='ar-label'>Forensic Finding</div><div style='font-size:1.3rem;font-weight:800;margin:.25rem 0 .45rem;'>{esc(incident)}</div><div class='small-note'>{esc(forensic_summary(txn, analysis))}</div><div style='margin-top:.75rem;display:flex;gap:.45rem;flex-wrap:wrap;'><span class='badge badge-cyan'><span class='dot'></span>Attribution · {esc(fault)}</span><span class='badge badge-amber'><span class='dot'></span>Preventability · {esc(prevent)}</span><span class='badge badge-purple'><span class='dot'></span>Evidence · {esc(status)}</span>{pscore_badge}</div></div>",
            unsafe_allow_html=True,
        )

    tabs = st.tabs(["What Happened", "State Diff", "Validation", "Rule Ledger", "Lifecycle", "Evidence & Report"])
    with tabs[0]:
        st.markdown("### What happened")
        st.markdown(f"<div class='finding'>{esc(forensic_summary(txn, analysis))}</div>", unsafe_allow_html=True)
        st.markdown("### How AgentResolve evaluated it")
        st.caption("The final finding is assembled from the deterministic analyzer. The LLM, when enabled, is explanation-only and cannot change the rule result.")
        render_evaluation_path(txn, analysis)
        st.markdown("### Why the conclusion is supported")
        evidence = getattr(analysis, "evidence", []) or []
        if evidence:
            for e in evidence:
                st.markdown(f"<div class='evidence'><div class='field'>{esc(getattr(e,'field','Evidence'))}</div><div class='copy'>{esc(getattr(e,'evidence_statement','Recorded evidence.'))}</div><div class='meta'>Expected: {esc(getattr(e,'expected_value',None))} · Observed: {esc(getattr(e,'actual_value',None))}</div></div>", unsafe_allow_html=True)
        else:
            st.info("No positive fault evidence was established.")
        if getattr(analysis, "missing_fields", []):
            st.warning("Missing evidence: " + ", ".join(analysis.missing_fields))
        if getattr(analysis, "data_flags", []):
            st.markdown("### Data flags")
            for flag in analysis.data_flags:
                st.markdown(f"<span class='badge badge-amber'><span class='dot'></span>{esc(flag)}</span>", unsafe_allow_html=True)
        st.markdown("### Engine explanation")
        st.write(localize_engine_text(getattr(analysis, "explanation", "") or "No engine explanation available."))

    with tabs[1]:
        render_diff(txn)

    with tabs[2]:
        render_validation_blackbox(txn)

    with tabs[3]:
        render_rule_ledger(txn, analysis)

    with tabs[4]:
        render_timeline(txn)

    with tabs[5]:
        life = getattr(txn, "lifecycle", None)
        st.markdown("### Evidence provenance & integrity")
        if life and getattr(life, "event_log", None):
            try:
                integrity, missing = verify_event_chain(life.event_log)
                st.markdown(f"<span class='badge {'badge-green' if not missing else 'badge-amber'}'><span class='dot'></span>Event chain · {esc(integrity)}</span>", unsafe_allow_html=True)
                if missing:
                    st.warning("Missing hashes: " + ", ".join(missing))
            except Exception as exc:
                st.warning(f"Integrity verification unavailable: {exc}")
        else:
            st.info("No event-chain integrity metadata supplied.")
        report = build_dispute_report(analysis, txn)
        report_payload = report.model_dump() if hasattr(report, "model_dump") else report

        st.markdown("### Forensic Case Packet")
        st.caption("Export the deterministic investigation report as a portable PDF evidence packet.")
        if build_forensic_pdf:
            try:
                pdf = build_forensic_pdf(report_payload)
                st.download_button(
                    "⬇ Download Forensic PDF",
                    data=pdf,
                    file_name=f"{txn.transaction_id}_forensic.pdf",
                    mime="application/pdf",
                    type="primary",
                    use_container_width=False,
                    key=f"download_pdf_{txn.transaction_id}",
                )
            except Exception as exc:
                st.error(f"PDF generation failed: {exc}")
        else:
            st.warning("PDF packet generator is unavailable. Install the reportlab dependency from requirements.txt.")

        with st.expander("Deterministic forensic report", expanded=False):
            st.json(report_payload)
        with st.expander("Raw transaction JSON", expanded=False):
            st.json(txn.model_dump())
    st.session_state._current_analysis_obj = None


def render_overview(cases: Dict[str, Dict[str, Any]]) -> None:
    st.markdown("<div class='ar-label'>OPERATIONS / OVERVIEW</div><h2 style='margin:.1rem 0;font-weight:800;'>Transaction Forensics</h2><div class='small-note'>Investigate AI-assisted commerce transactions from recorded evidence.</div>", unsafe_allow_html=True)
    if st.button("✦ Run Shopping Agent", type="primary"):
        st.session_state.page = "Shopping Agent"; st.rerun()
    analyses = {k: safe_analysis(v["txn"]) for k,v in cases.items()}
    total=len(cases)
    disputes=sum(1 for p in cases.values() if getattr(p["txn"].dispute,"user_claim","").strip() and p["txn"].dispute.user_claim != "No dispute filed yet")
    insufficient=sum(1 for a in analyses.values() if getattr(getattr(a,"status",None),"value","")=="INSUFFICIENT_EVIDENCE")
    high=sum(1 for a in analyses.values() if getattr(getattr(a,"preventability",None),"value","")=="HIGH" and getattr(a,"primary_fault",None))
    cols=st.columns(4)
    with cols[0]: st.markdown(f"<div class='ar-card'><div class='ar-label'>Investigations</div><div class='ar-value'>{total}</div><div class='ar-sub'>recorded cases</div></div>",unsafe_allow_html=True)
    with cols[1]: st.markdown(f"<div class='ar-card'><div class='ar-label'>Disputes Open</div><div class='ar-value' style='color:#fbbf24'>{disputes}</div><div class='ar-sub'>requires review</div></div>",unsafe_allow_html=True)
    with cols[2]: st.markdown(f"<div class='ar-card'><div class='ar-label'>High-Risk Cases</div><div class='ar-value' style='color:#fb7185'>{high:02d}</div><div class='ar-sub'>high preventability + attribution</div></div>",unsafe_allow_html=True)
    with cols[3]: st.markdown(f"<div class='ar-card'><div class='ar-label'>Insufficient Evidence</div><div class='ar-value'>{insufficient}</div><div class='ar-sub'>engine refused to guess</div></div>",unsafe_allow_html=True)

    st.markdown("<div style='margin:1.2rem 0 .55rem;' class='ar-label'>RECENT INVESTIGATIONS</div>", unsafe_allow_html=True)
    rows=[]
    for cid,p in list(cases.items())[:8]:
        txn=p["txn"]; a=analyses[cid]
        inc=human(getattr(getattr(a,"incident",None),"incident_type",None) or "NORMAL_PURCHASE")
        fault=human(getattr(getattr(a,"primary_fault",None),"category",None) or "NO_FAULT_DETECTED")
        amt=money(getattr(txn.agent_decision,"purchased_price",None))
        score,_=evidence_score(txn,a)
        rows.append(f"<tr><td><code>{esc(cid)}</code></td><td>{esc(inc)}</td><td>{esc(fault)}</td><td>{esc(amt)}</td><td>{score}%</td><td>{esc(getattr(txn.merchant_snapshot,'seller',None) or 'Not recorded')}</td></tr>")
    st.markdown("<table class='ops-table'><thead><tr><th>Transaction</th><th>Incident</th><th>Attribution</th><th>Amount</th><th>Evidence</th><th>Merchant</th></tr></thead><tbody>"+"".join(rows)+"</tbody></table>",unsafe_allow_html=True)


def render_investigations(cases: Dict[str, Dict[str, Any]]) -> None:
    active=active_transaction()
    if active:
        render_case(active); return
    st.markdown("<div class='ar-label'>OPERATIONS / CASE QUEUE</div><h2 style='margin:.1rem 0;font-weight:800;'>Investigations</h2><div class='small-note'>Open any case for field-level evidence reconstruction and deterministic rule-gate analysis.</div>",unsafe_allow_html=True)
    q=st.text_input("Filter",placeholder="transaction, merchant, incident, attribution...",label_visibility="collapsed")
    needle=(q or st.session_state.global_search).lower().strip()
    records=[]
    for cid,p in cases.items():
        txn=p["txn"]; a=safe_analysis(txn)
        text=f"{cid} {txn.merchant_snapshot.seller or ''} {txn.merchant_snapshot.title or ''} {human(getattr(getattr(a,'primary_fault',None),'category',None))} {human(getattr(getattr(a,'incident',None),'incident_type',None))}".lower()
        if needle and needle not in text: continue
        records.append((cid,txn,a))
    st.markdown(f"<div class='small-note' style='margin:.7rem 0;'>{len(records)} records</div>",unsafe_allow_html=True)
    rows=[]
    for cid,txn,a in records:
        score,_=evidence_score(txn,a)
        rows.append(f"<tr><td><code>{esc(cid)}</code></td><td>{esc(human(getattr(getattr(a,'incident',None),'incident_type',None) or '—'))}</td><td>{esc(human(getattr(getattr(a,'primary_fault',None),'category',None) or 'NO_FAULT_DETECTED'))}</td><td>{esc(money(txn.agent_decision.purchased_price))}</td><td>{score}%</td><td>{esc(txn.merchant_snapshot.seller or 'Not recorded')}</td></tr>")
    st.markdown("<table class='ops-table'><thead><tr><th>Transaction</th><th>Incident</th><th>Attribution</th><th>Amount</th><th>Evidence</th><th>Merchant</th></tr></thead><tbody>"+"".join(rows)+"</tbody></table>",unsafe_allow_html=True)
    choices=[r[0] for r in records]
    if choices:
        c1,c2=st.columns([7,2])
        with c1: choice=st.selectbox("Case",choices,label_visibility="collapsed")
        with c2:
            if st.button("Open Case →",type="primary",use_container_width=True): set_active(cases[choice]["txn"]); st.rerun()


def render_transactions(cases: Dict[str, Dict[str, Any]]) -> None:
    st.markdown("<div class='ar-label'>OPERATIONS / TRANSACTIONS</div><h2 style='margin:.1rem 0;font-weight:800;'>Transaction Ledger</h2><div class='small-note'>Recorded commerce lifecycle entries.</div>",unsafe_allow_html=True)
    rows=[]
    for cid,p in cases.items():
        t=p["txn"]
        rows.append(f"<tr><td><code>{esc(cid)}</code></td><td>{esc(t.merchant_snapshot.seller or '—')}</td><td>{esc(t.merchant_snapshot.title or '—')}</td><td>{esc(money(t.agent_decision.purchased_price))}</td><td><span class='badge badge-green'><span class='dot'></span>RECORDED</span></td></tr>")
    st.markdown("<table class='ops-table'><thead><tr><th>Transaction</th><th>Seller</th><th>Product</th><th>Amount</th><th>Status</th></tr></thead><tbody>"+"".join(rows)+"</tbody></table>",unsafe_allow_html=True)


def render_disputes(cases: Dict[str, Dict[str, Any]]) -> None:
    st.markdown("<div class='ar-label'>OPERATIONS / DISPUTES</div><h2 style='margin:.1rem 0;font-weight:800;'>Customer Dispute Triage</h2><div class='small-note'>Claims are starting evidence, not conclusions.</div>",unsafe_allow_html=True)
    found=False
    for cid,p in cases.items():
        claim=getattr(p["txn"].dispute,"user_claim","")
        if not claim.strip() or claim == "No dispute filed yet": continue
        found=True
        a=safe_analysis(p["txn"]); score,_=evidence_score(p["txn"],a)
        st.markdown(f"<div class='ar-card' style='margin:.6rem 0;'><div style='display:flex;justify-content:space-between;'><strong>{esc(cid)}</strong><span class='badge badge-amber'><span class='dot'></span>CLAIM</span></div><div style='margin:.55rem 0;color:#f8fafc;'>“{esc(claim)}”</div><div class='small-note'>Incident: {esc(human(getattr(getattr(a,'incident',None),'incident_type',None)))} · Evidence strength: {score}% · Disputed field: {esc(p['txn'].dispute.disputed_field)}</div></div>",unsafe_allow_html=True)
    if not found: st.info("No active dispute claims are recorded.")


def render_evidence(cases: Dict[str, Dict[str, Any]]) -> None:
    st.markdown("<div class='ar-label'>INVESTIGATIONS / EVIDENCE</div><h2 style='margin:.1rem 0;font-weight:800;'>Evidence Register</h2><div class='small-note'>Compare the constrained attributes across lifecycle stages.</div>",unsafe_allow_html=True)
    keys=list(cases)
    if not keys: st.info("No cases available."); return
    choice=st.selectbox("Case",keys)
    render_diff(cases[choice]["txn"])


def render_test_lab(cases: Dict[str, Dict[str, Any]]) -> None:
    st.markdown("<div class='ar-label'>FORENSIC QA / TEST LAB</div><h2 style='margin:.1rem 0;font-weight:800;'>Test Lab & External Case Audit</h2><div class='small-note'>Upload a completely new Transaction JSON and receive the same forensic reconstruction used for stored cases.</div>",unsafe_allow_html=True)
    up=st.file_uploader("Upload Transaction JSON",type=["json"],key="lab_upload_v2")
    txn=None
    source_label="Stored case"
    if up:
        try:
            payload=json.load(up)
            txn=Transaction.model_validate(payload)
            source_label="External JSON"
            st.success(f"Schema validated · {txn.transaction_id}")
        except Exception as exc:
            st.error(f"Invalid Transaction JSON: {exc}")
            return
    else:
        keys=list(cases)
        if not keys: st.info("No stored cases."); return
        choice=st.selectbox("Stored case",keys,key="lab_stored_case_v2")
        txn=cases[choice]["txn"]
    if not txn: return

    a=safe_analysis(txn)
    score, breakdown=evidence_score(txn,a)
    st.markdown(f"<div class='ar-label' style='margin-top:.5rem;'>{esc(source_label)}</div><h3 style='margin:.1rem 0 .7rem;'>{esc(txn.transaction_id)}</h3>",unsafe_allow_html=True)
    top_left, top_right=st.columns([1.0,2.1])
    with top_left:
        render_score_meter(score,breakdown)
    with top_right:
        st.markdown(f"<div class='ar-card'><div class='ar-label'>Immediate forensic finding</div><div style='font-size:1.18rem;font-weight:800;margin:.25rem 0 .45rem;'>{esc(human(getattr(getattr(a,'incident',None),'incident_type',None) or 'UNCLASSIFIED'))}</div><div class='small-note'>{esc(forensic_summary(txn,a))}</div></div>",unsafe_allow_html=True)

    st.markdown("### Evaluation path")
    render_evaluation_path(txn,a)
    st.markdown("### Case explanation")
    st.markdown(f"<div class='finding'>{esc(forensic_summary(txn,a))}</div>",unsafe_allow_html=True)

    tabs=st.tabs(["Rule Ledger","State Diff","Validation","Lifecycle","Report","Raw JSON"])
    with tabs[0]: render_rule_ledger(txn,a)
    with tabs[1]: render_diff(txn)
    with tabs[2]: render_validation_blackbox(txn)
    with tabs[3]: render_timeline(txn)
    with tabs[4]:
        report=build_dispute_report(a,txn)
        st.json(report.model_dump() if hasattr(report,"model_dump") else report)
        cf=getattr(a,"counterfactual",None)
        if cf:
            st.markdown(f"<div class='finding'><strong>Counterfactual:</strong> {esc(getattr(cf,'result','N/A'))}<br>{esc(getattr(cf,'narrative',''))}</div>",unsafe_allow_html=True)
    with tabs[5]:
        st.json(txn.model_dump())


def _eval_prediction_rows(path: str) -> List[Tuple[str, str, str, bool]]:
    """Re-run each labelled case for transparent case-level evaluation diagnostics."""
    rows: List[Tuple[str, str, str, bool]] = []
    try:
        dataset = load_dataset(path)
    except Exception:
        return rows
    for txn in dataset:
        if not txn.ground_truth:
            continue
        analysis = analyze_transaction(txn)
        if getattr(analysis, "status", None) is not None and getattr(analysis.status, "value", "") == "INSUFFICIENT_EVIDENCE":
            predicted = "INSUFFICIENT_EVIDENCE"
        elif getattr(analysis, "primary_fault", None):
            predicted = analysis.primary_fault.category.value
        else:
            predicted = "NO_FAULT_DETECTED"
        truth = str(txn.ground_truth.primary_fault)
        rows.append((txn.transaction_id, truth, predicted, truth == predicted))
    return rows


def _metric_percent(value: Any) -> str:
    try:
        return f"{float(value) * 100:.1f}%"
    except (TypeError, ValueError):
        return "—"


def render_evaluation() -> None:
    st.markdown(
        "<div class='ar-label'>FORENSIC QA / REGRESSION</div>"
        "<h2 style='margin:.1rem 0;font-weight:800;'>Evaluation</h2>"
        "<div class='small-note'>Measure how consistently the deterministic AgentResolve analyzer reproduces labelled transaction-attribution outcomes.</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class='ar-card' style='margin:.8rem 0 1rem;'>
          <div class='ar-label'>What this evaluation does</div>
          <div style='font-size:.95rem;font-weight:800;margin:.25rem 0 .45rem;'>Replay → Analyze → Compare → Measure</div>
          <div class='small-note' style='line-height:1.65;'>
            AgentResolve loads the labelled Development and Holdout transaction records, runs each record through the same deterministic forensic analyzer used by the investigation workspace, extracts the predicted primary attribution, and compares it with the case's recorded ground truth. It then calculates accuracy, macro precision, macro recall, macro F1, per-category diagnostics and a confusion matrix.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### Evaluation methodology")
    steps = [
        ("01", "Load labelled cases", "Ground-truth transaction records are loaded from the local development and holdout datasets."),
        ("02", "Run the real analyzer", "Each case goes through the same evidence boundary, incident analysis, rule evaluation and attribution pipeline used elsewhere in AgentResolve."),
        ("03", "Extract prediction", "The predicted primary fault is taken from the deterministic analyzer; insufficient evidence remains a separate prediction state."),
        ("04", "Compare to ground truth", "The predicted attribution is compared with the recorded primary_fault for that case."),
        ("05", "Calculate metrics", "Accuracy, macro precision, macro recall, macro F1, category-level metrics and the confusion matrix are reported."),
    ]
    for number, title, detail in steps:
        st.markdown(
            f"<div class='evidence'><div class='field'>{number} · {esc(title)}</div><div class='copy'>{esc(detail)}</div></div>",
            unsafe_allow_html=True,
        )

    st.markdown(
        """
        <div class='ar-card' style='margin:.8rem 0 1rem;'>
          <div class='ar-label'>How to read the results</div>
          <div class='small-note' style='line-height:1.65;'>
            Accuracy = fraction of labelled cases classified exactly correctly.<br>
            Precision = when the engine predicts a category, how often that prediction matches the labelled category.<br>
            Recall = how often cases belonging to a category are correctly recovered.<br>
            Macro F1 = the average F1 across evaluated categories, giving each category equal weight.<br>
            Confusion matrix = which true categories are being confused with which predicted categories.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("Run Evaluation Suite", type="primary"):
        with st.spinner("Replaying labelled cases through AgentResolve..."):
            try:
                st.session_state.eval_result = run_evaluation()
                st.session_state.eval_error = None
            except Exception as exc:
                st.session_state.eval_result = None
                st.session_state.eval_error = str(exc)
            st.rerun()

    if st.session_state.get("eval_error"):
        st.error(f"Evaluation failed: {st.session_state.eval_error}")
        return

    res = st.session_state.get("eval_result")
    if not res:
        st.info("Run the Evaluation Suite to execute the benchmark and populate the metrics below.")
        return

    dev = res.get("development", {}) if isinstance(res, dict) else {}
    hold = res.get("holdout", {}) if isinstance(res, dict) else {}

    st.markdown("### Benchmark result")
    d1, d2, d3, d4 = st.columns(4)
    with d1:
        st.markdown(f"<div class='ar-card'><div class='ar-label'>Development Cases</div><div class='ar-value'>{esc(dev.get('total_cases','—'))}</div><div class='ar-sub'>labelled records evaluated</div></div>", unsafe_allow_html=True)
    with d2:
        st.markdown(f"<div class='ar-card'><div class='ar-label'>Holdout Cases</div><div class='ar-value'>{esc(hold.get('total_cases','—'))}</div><div class='ar-sub'>unseen labelled records</div></div>", unsafe_allow_html=True)
    with d3:
        st.markdown(f"<div class='ar-card'><div class='ar-label'>Holdout Accuracy</div><div class='ar-value' style='color:#34d399'>{_metric_percent(hold.get('accuracy'))}</div><div class='ar-sub'>exact prediction match rate</div></div>", unsafe_allow_html=True)
    with d4:
        st.markdown(f"<div class='ar-card'><div class='ar-label'>Holdout Macro F1</div><div class='ar-value' style='color:#38bdf8'>{_metric_percent(hold.get('macro_f1'))}</div><div class='ar-sub'>balanced category performance</div></div>", unsafe_allow_html=True)

    st.markdown("### Development vs Holdout")
    cols = st.columns(4)
    metrics = [
        ("Accuracy", "accuracy"),
        ("Macro Precision", "macro_precision"),
        ("Macro Recall", "macro_recall"),
        ("Macro F1", "macro_f1"),
    ]
    for col, (label, key) in zip(cols, metrics):
        with col:
            st.markdown(
                f"<div class='ar-card'><div class='ar-label'>{esc(label)}</div><div class='small-note'>Development</div><div style='font-size:1.35rem;font-weight:800;margin:.1rem 0 .35rem;'>{_metric_percent(dev.get(key))}</div><div class='small-note'>Holdout · <strong style='color:#f8fafc'>{_metric_percent(hold.get(key))}</strong></div></div>",
                unsafe_allow_html=True,
            )

    st.markdown("### Per-category diagnostics")
    per_dev = dev.get("per_category", {}) if isinstance(dev, dict) else {}
    per_hold = hold.get("per_category", {}) if isinstance(hold, dict) else {}
    labels = list(dict.fromkeys(list(per_dev.keys()) + list(per_hold.keys())))
    if labels:
        rows = []
        for label in labels:
            d = per_dev.get(label, {})
            h = per_hold.get(label, {})
            rows.append(
                f"<tr><td><strong>{esc(human(label))}</strong></td>"
                f"<td>{_metric_percent(d.get('precision'))}</td><td>{_metric_percent(d.get('recall'))}</td><td>{_metric_percent(d.get('f1_score'))}</td><td>{esc(d.get('support','—'))}</td>"
                f"<td>{_metric_percent(h.get('precision'))}</td><td>{_metric_percent(h.get('recall'))}</td><td>{_metric_percent(h.get('f1_score'))}</td><td>{esc(h.get('support','—'))}</td></tr>"
            )
        st.markdown(
            "<table class='ops-table'><thead><tr><th rowspan='2'>Category</th><th colspan='4'>Development</th><th colspan='4'>Holdout</th></tr><tr><th>Precision</th><th>Recall</th><th>F1</th><th>Cases</th><th>Precision</th><th>Recall</th><th>F1</th><th>Cases</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table>",
            unsafe_allow_html=True,
        )
    else:
        st.info("No per-category metrics were returned by the evaluator.")

    st.markdown("### Confusion matrix")
    cm_labels = hold.get("labels", []) if isinstance(hold, dict) else []
    cm = hold.get("confusion_matrix", []) if isinstance(hold, dict) else []
    if cm_labels and cm:
        header = "<tr><th>True \\ Predicted</th>" + "".join(f"<th>{esc(human(x))}</th>" for x in cm_labels) + "</tr>"
        body = []
        for i, label in enumerate(cm_labels):
            vals = cm[i] if i < len(cm) else []
            cells = "".join(f"<td style='text-align:center;font-weight:700;'>{esc(v)}</td>" for v in vals)
            body.append(f"<tr><td><strong>{esc(human(label))}</strong></td>{cells}</tr>")
        st.markdown("<table class='ops-table'><thead>" + header + "</thead><tbody>" + "".join(body) + "</tbody></table>", unsafe_allow_html=True)
        st.caption("Rows are true labels. Columns are predicted labels. Values on the diagonal are exact matches.")

    # Transparent case-level audit: rerun the exact labelled cases and show mismatches.
    st.markdown("### Case-level audit")
    dev_path = os.path.join(ROOT_DIR, "data", "development_cases.json")
    hold_path = os.path.join(ROOT_DIR, "data", "holdout_cases.json")
    case_rows = _eval_prediction_rows(hold_path)
    correct = sum(1 for _id, _truth, _pred, ok in case_rows if ok)
    total = len(case_rows)
    st.markdown(
        f"<div class='ar-card'><div class='ar-label'>Holdout audit</div><div style='font-size:1.1rem;font-weight:800;margin:.2rem 0;'> {correct} / {total} predictions matched the recorded ground truth.</div><div class='small-note'>This is a case-level replay of the same analyzer, shown so an evaluator can inspect exactly where the benchmark agrees or disagrees.</div></div>",
        unsafe_allow_html=True,
    )
    mismatches = [r for r in case_rows if not r[3]]
    if mismatches:
        st.markdown("#### Mismatched holdout cases")
        rows = []
        for txn_id, truth, pred, _ok in mismatches:
            rows.append(f"<tr><td><code>{esc(txn_id)}</code></td><td>{esc(human(truth))}</td><td style='color:#fb7185'>{esc(human(pred))}</td><td><span class='badge badge-red'><span class='dot'></span>MISMATCH</span></td></tr>")
        st.markdown("<table class='ops-table'><thead><tr><th>Transaction</th><th>Ground Truth</th><th>Prediction</th><th>Status</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>", unsafe_allow_html=True)
    else:
        st.success("Every evaluated holdout case matched its recorded primary attribution.")

    st.markdown("### Dataset boundaries")
    st.markdown(
        """
        <div class='ar-card'>
          <div class='small-note' style='line-height:1.65;'>
            Development and Holdout are regression benchmarks built from labelled transaction records. They are useful for detecting changes in deterministic behavior, but they do not establish real-world forensic accuracy, production coverage, legal liability, or statistical performance on an external population. External JSON cases without ground truth are audited individually and are not assigned benchmark accuracy.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("Raw evaluation payload", expanded=False):
        st.json(res)


def render_system() -> None:
    st.markdown("<div class='ar-label'>CONTROL PLANE / SYSTEM</div><h2 style='margin:.1rem 0;font-weight:800;'>System Status</h2>",unsafe_allow_html=True)
    checks=[
        ("Deterministic engine","Imported and callable","HEALTHY","badge-green"),
        ("Transaction schema","Pydantic validation available","HEALTHY","badge-green"),
        ("Strict rule ledger","Five canonical checks available","HEALTHY","badge-green"),
        ("Report builder","Loaded","HEALTHY","badge-green"),
        ("PDF packet","Available" if build_forensic_pdf else "Optional dependency unavailable","READY" if build_forensic_pdf else "OPTIONAL","badge-green" if build_forensic_pdf else "badge-amber"),
    ]
    for name,desc,status,badge in checks:
        st.markdown(f"<div class='ar-card' style='margin:.55rem 0;display:flex;justify-content:space-between;align-items:center;'><div><strong>{esc(name)}</strong><div class='small-note'>{esc(desc)}</div></div><span class='badge {badge}'><span class='dot'></span>{esc(status)}</span></div>",unsafe_allow_html=True)


def normalize_agent_query_for_currency(query: str, code: str) -> str:
    """Keep raw request text intact while adapting unmarked price phrases for the existing simulator."""
    if not query.strip(): return query
    meta=CURRENCY.get(code,CURRENCY["INR"])
    text=query
    pat=re.compile(r"(under|below|less than|at most|max|maximum|budget(?: of)?)\s*([\d,]+(?:\.\d+)?)",re.I)
    def repl(m):
        window=text[max(0,m.start()-4):min(len(text),m.end()+5)]
        explicit_currency=bool(re.search(r"[₹$€£]|\b(?:inr|usd|eur|gbp|rupees?|rs)\b",window,re.I))
        if explicit_currency: return m.group(0)
        usd=float(m.group(2).replace(",",""))*meta["usd"]
        return f"{m.group(1)} ${usd:.2f}"
    return pat.sub(repl,text)


def render_shopping_agent() -> None:
    st.markdown("<div class='ar-label'>UPSTREAM / SHOPPING AGENT</div><h2 style='margin:.1rem 0;font-weight:800;'>Run Shopping Agent</h2><div class='small-note'>Enter the customer request naturally. The simulator must satisfy every recorded hard requirement before authorization.</div>",unsafe_allow_html=True)
    query=st.text_area("Shopping request",value=st.session_state.shopping_query,height=140,placeholder="Example: I need a black smartphone under ₹50,000 with at least 256GB storage, at least 8GB RAM, and delivery within 3 days. Do not buy anything that fails even one requirement.")
    st.session_state.shopping_query=query
    st.markdown(f"<div class='ar-card' style='margin:.65rem 0;'><div class='ar-label'>Active customer currency</div><div style='font-size:1.05rem;font-weight:800;'>{esc(st.session_state.currency)} · {esc(CURRENCY[st.session_state.currency]['symbol'])}</div><div class='small-note'>INR is the default. An explicit currency written in the request is preserved as request evidence.</div></div>",unsafe_allow_html=True)
    if st.button("✦ Dispatch Agent",type="primary",disabled=not query.strip()):
        execution_query=normalize_agent_query_for_currency(query,st.session_state.currency)
        try:
            txn=execute_purchase(execution_query,st.session_state.currency,allow_constraint_override=False)
            txn.user_request.raw_text=query
            st.session_state.active_txn=txn.model_dump(); st.session_state.page="Investigations"; st.rerun()
        except PurchaseBlockedError as exc:
            st.error("PURCHASE BLOCKED")
            st.markdown(f"<div class='ar-card'><div style='font-weight:800;color:#fb7185;'>No compliant product satisfies the recorded requirements.</div><div class='small-note' style='margin-top:.35rem;'>No authorization, checkout, payment capture or order creation should occur on this path.</div></div>",unsafe_allow_html=True)
            if getattr(exc,"candidates",None):
                st.markdown("### Candidate evidence")
                for p in exc.candidates[:6]:
                    st.markdown(f"<div class='evidence'><strong>{esc(p.get('title'))}</strong><div class='meta'>Price {esc(money(p.get('price')))} · {esc(p.get('category'))} · {esc(p.get('seller'))}</div></div>",unsafe_allow_html=True)
        except Exception as exc:
            st.error(f"Execution error: {exc}")


def render_topbar() -> None:
    a,b,c=st.columns([2.5,5.4,2.1],vertical_alignment="center")
    with a:
        st.markdown("<div style='font-weight:800;font-size:1rem;'>◈ AgentResolve</div><div class='small-note'>FORA / TRANSACTION FORENSICS</div>",unsafe_allow_html=True)
    with b:
        st.session_state.global_search=st.text_input("Search",value=st.session_state.global_search,placeholder="Search transactions, orders, merchants...",label_visibility="collapsed")
    with c:
        st.markdown("<div style='text-align:right;'><span class='badge badge-green'><span class='dot'></span> LOCAL · SIMULATED</span></div>",unsafe_allow_html=True)
    st.markdown("<hr style='border:0;border-top:1px solid #141b27;margin:.7rem 0 1.1rem;'>",unsafe_allow_html=True)


def render_sidebar(cases: Dict[str, Dict[str, Any]]) -> None:
    with st.sidebar:
        st.markdown("<div style='font-weight:800;font-size:1rem;'>◈ AgentResolve</div><div class='small-note'>TRANSACTION FORENSICS WORKSTATION</div>",unsafe_allow_html=True)
        st.markdown("<div style='margin:.8rem 0 1rem;'><span class='badge badge-cyan'><span class='dot'></span> LOCAL · SIMULATED</span></div>",unsafe_allow_html=True)
        for label,icon in NAV:
            active=st.session_state.page==label
            if st.button(f"{'●' if active else icon}  {label}{'  ' + str(len(cases)) if label=='Investigations' else ''}",key=f"nav_{label}",use_container_width=True,type="primary" if active else "secondary"):
                st.session_state.page=label
                if label!="Investigations": st.session_state.active_txn=None
                st.rerun()
        st.divider()
        st.markdown("<div class='ar-label'>Currency</div>",unsafe_allow_html=True)
        selected=st.selectbox("Currency",list(CURRENCY),index=list(CURRENCY).index(st.session_state.currency),format_func=lambda x:f"{x} — {CURRENCY[x]['label']}",label_visibility="collapsed")
        if selected!=st.session_state.currency: st.session_state.currency=selected; st.rerun()
        st.caption("INR is implicit/default. Display currency can be changed explicitly; request text is preserved as evidence.")
        st.divider()
        st.markdown("<div class='ar-label'>Forensic engine</div><div style='font-weight:800;margin:.1rem 0;'>Operational</div><div class='small-note'>Deterministic rules · evidence-first · no guessed intent</div>",unsafe_allow_html=True)


def main() -> None:
    cases=load_cases()
    render_sidebar(cases)
    render_topbar()
    page=st.session_state.page
    if page=="Overview": render_overview(cases)
    elif page=="Investigations": render_investigations(cases)
    elif page=="Transactions": render_transactions(cases)
    elif page=="Disputes": render_disputes(cases)
    elif page=="Evidence": render_evidence(cases)
    elif page=="Test Lab": render_test_lab(cases)
    elif page=="Evaluation": render_evaluation()
    elif page=="System": render_system()
    elif page=="Shopping Agent": render_shopping_agent()
    else: render_overview(cases)


if __name__=="__main__":
    main()
