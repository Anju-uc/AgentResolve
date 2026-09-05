"""
Report Builder module for AgentResolve.

Builds a complete case report while keeping:
- recorded transaction facts separate from forensic findings
- customer-facing monetary display separate from canonical engine storage
- counterfactual simulation separate from deterministic attribution
- LLM output strictly explanation-only

Monetary values remain canonical in USD inside the deterministic engine.
For presentation, the report uses the currency explicitly stated by the
customer. When the customer does not state a currency, INR is used.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

from app.models.transaction import Transaction
from app.models.result import AnalysisResult
from app.engine.evidence_score import evidence_breakdown, calculate_forensic_score


_CURRENCY_RATES_TO_USD = {
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

_CURRENCY_SYMBOLS = {
    "INR": "₹",
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
    "AED": "د.إ",
    "SGD": "S$",
    "AUD": "A$",
    "CAD": "C$",
    "JPY": "¥",
}


def _request_currency(raw_text: str) -> str:
    """Use USD only when the customer explicitly states dollars; otherwise use INR."""
    text = (raw_text or "").lower()
    if any(token in text for token in ("$", "usd", "us dollar", "dollars")):
        return "USD"
    return "INR"


def _display_money(value_usd: Any, currency: str) -> str:
    """Convert canonical USD to the customer's display currency."""
    if value_usd is None:
        return "Not recorded"

    code = (currency or "INR").upper()
    rate = _CURRENCY_RATES_TO_USD.get(
        code,
        _CURRENCY_RATES_TO_USD["INR"],
    )
    symbol = _CURRENCY_SYMBOLS.get(code, "₹")

    try:
        amount = float(value_usd) / rate
        return f"{symbol}{amount:,.2f}"
    except (TypeError, ValueError, ZeroDivisionError):
        return str(value_usd)


def _display_constraint(
    constraints: Dict[str, Any],
    currency: str,
) -> Optional[str]:
    value = constraints.get("price_usd")

    if value is None:
        return None

    operator = constraints.get(
        "price_usd_operator",
        "at most",
    )

    return f"{operator} {_display_money(value, currency)}"


def _dump(value: Any) -> Any:
    if value is None: return None
    if hasattr(value, "model_dump"): return value.model_dump(mode="json")
    if hasattr(value, "value"): return value.value
    if isinstance(value, dict): return {str(k): _dump(v) for k,v in value.items()}
    if isinstance(value, (list,tuple)): return [_dump(v) for v in value]
    return value


def _rule_payload(rule: Any) -> Dict[str, Any]:
    return {"category": _dump(getattr(rule,"category",None)),"fired":bool(getattr(rule,"fired",False)),"raw_points":int(getattr(rule,"raw_points",0) or 0),"evidence_factors":list(getattr(rule,"evidence_factors",[]) or []),"evidence":[{"field":getattr(e,"field",""),"statement":getattr(e,"evidence_statement",""),"expected":_dump(getattr(e,"expected_value",None)),"actual":_dump(getattr(e,"actual_value",None)),"provenance":_dump(getattr(e,"provenance",None))} for e in (getattr(rule,"evidence",[]) or [])]}


def build_dispute_report(
    analysis: AnalysisResult,
    txn: Optional[Transaction] = None,
) -> Dict[str, Any]:
    """
    Build a portable case-specific forensic report.

    Canonical engine monetary fields remain unchanged. Presentation fields
    are additionally supplied in the customer's request currency so the
    report never silently mixes customer-facing INR/USD representations.
    """

    display_currency = (
        _request_currency(txn.user_request.raw_text)
        if txn is not None
        else "INR"
    )

    report: Dict[str, Any] = {
        "report_metadata": {
            "engine": "AgentResolve Forensic Engine v2.3",
            "transaction_id": analysis.transaction_id,
            "status": analysis.status.value,
            "evidence_boundary": analysis.evidence_status,
            "incident_type": (
                analysis.incident.incident_type.value
                if analysis.incident
                else None
            ),
            "economic_harm": analysis.economic_harm,
            "harm_currency": analysis.harm_currency,
            "display_currency": display_currency,
        },
        "attribution_summary": {
            "primary_fault": (
                {
                    "category": analysis.primary_fault.category.value,
                    "score": analysis.primary_fault.score,
                    "display": (
                        f"{analysis.primary_fault.category.value} — "
                        f"{analysis.primary_fault.score}/100 "
                        "based on available evidence"
                    ),
                }
                if analysis.primary_fault
                else None
            ),
            "contributing_factors": [
                {
                    "category": c.category.value,
                    "score": c.score,
                    "display": f"{c.category.value} — {c.score}/100",
                }
                for c in analysis.contributing_factors
            ],
            "preventability": analysis.preventability.value,
            "data_flags": analysis.data_flags,
            "recorded_responsibility": (
                analysis.incident.recorded_responsibility.value
                if analysis.incident
                else "UNKNOWN"
            ),
        },
        "rule_ledger": [_rule_payload(r) for r in (analysis.all_rule_results or [])],
        "evidence_coverage": evidence_breakdown(txn, analysis) if txn is not None else {},
        "forensic_score": int(getattr(analysis, "forensic_score", 0) or 0) if txn is not None else 0,
        "evidence_trace": [
            {
                "field": e.field,
                "statement": e.evidence_statement,
                "expected": e.expected_value,
                "actual": e.actual_value,
                "provenance": (
                    e.provenance.model_dump()
                    if e.provenance
                    else None
                ),
            }
            for e in analysis.evidence
        ],
        "counterfactual_replay": (
            {
                "applicable": analysis.counterfactual.applicable,
                "action": analysis.counterfactual.action,
                "expected": analysis.counterfactual.expected,
                "actual": analysis.counterfactual.actual,
                "result": analysis.counterfactual.result,
                "narrative": analysis.counterfactual.narrative,
            }
            if analysis.counterfactual
            else None
        ),
        "explanation": {
            "text": analysis.explanation,
            "status": analysis.explanation_status,
            "disclaimer": (
                "LLM output is explanation-only and does not mutate "
                "deterministic findings."
            ),
        },
    }

    if txn is not None:
        constraints = txn.user_request.explicit_constraints.model_dump()

        report["forensic_signals"] = {
            "dispute_drift": (
                analysis.dispute_drift.model_dump()
                if analysis.dispute_drift
                else None
            ),
            "incident": (
                analysis.incident.model_dump()
                if analysis.incident
                else None
            ),
        }

        report["recorded_facts"] = {
            "display_currency": display_currency,
            "user_request": {
                "text": txn.user_request.raw_text,
                "constraints": constraints,
                "customer_price_display": _display_constraint(
                    constraints,
                    display_currency,
                ),
            },
            "merchant_snapshot": txn.merchant_snapshot.model_dump(),
            "agent_decision": {
                **txn.agent_decision.model_dump(),
                "purchased_price_display": _display_money(
                    txn.agent_decision.purchased_price,
                    display_currency,
                ),
            },
            "merchant_price_display": {
                "listed_price": _display_money(
                    txn.merchant_snapshot.price,
                    display_currency,
                ),
                "checkout_price": _display_money(
                    txn.merchant_snapshot.price_at_checkout,
                    display_currency,
                ),
            },
            "dispute": txn.dispute.model_dump(),
            "lifecycle": (
                txn.lifecycle.model_dump()
                if txn.lifecycle
                else None
            ),
            "direct_financial_harm": txn.direct_financial_harm,
            "harm_currency": txn.harm_currency,
        }

    return report
