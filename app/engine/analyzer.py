"""
Core Forensic Analyzer module for AgentResolve.

Orchestrates the complete deterministic analysis pipeline for a disputed transaction:
1. Validate schema & required objects
2. Check evidence completeness
3. Execute all five fault rules independently
4. Handle payment data flags
5. Calculate normalized attribution scores
6. Rank primary fault and contributing factors
7. Determine preventability rating
8. Generate counterfactual replay
9. Assemble final AnalysisResult
"""

from typing import List

from app.models.transaction import Transaction
from app.models.result import (
    AnalysisResult,
    AnalysisStatus,
    PreventabilityRating,
    RuleResult,
    EvidenceItem,
)
from app.engine.rules import run_all_rules
from app.engine.scoring import calculate_attribution_scores
from app.engine.preventability import determine_preventability
from app.engine.counterfactual import simulate_counterfactual
from app.engine.incidents import classify_incident
from app.engine.helpers import constraint_exists
from app.engine.evidence_score import (
    evidence_breakdown,
    calculate_forensic_score,
    forensic_score_breakdown,
)
from app.engine.drift import detect_dispute_drift
from app.engine.provenance import verify_event_chain
from app.models.forensics import EvidenceProvenance



def _event_matches_evidence(event, evidence: EvidenceItem) -> bool:
    """Return True only when a recorded event explicitly names the evidence field.

    This intentionally avoids fuzzy semantic matching: provenance should point to
    a concrete recorded event, not merely a transaction-level source.
    """
    field = str(evidence.field or "").strip().lower()
    if not field:
        return False
    aliases = {field}
    aliases.update({
        field.replace("_gb", ""),
        field.replace("_usd", ""),
        field.replace("merchant_snapshot.", ""),
        field.replace("agent_decision.", ""),
        field.replace("fulfillment.", ""),
        field.replace("payment.", ""),
        field.replace("inventory.", ""),
    })
    for source in (getattr(event, "arguments", {}) or {}, getattr(event, "result", {}) or {}):
        event_field = str(source.get("field", "") or "").strip().lower()
        if event_field in aliases:
            return True
    return False


def _find_evidence_event(txn: Transaction, evidence: EvidenceItem):
    """Find the exact recorded event that names an evidence field, if any."""
    lifecycle_events = []
    if txn.lifecycle:
        lifecycle_events.extend(txn.lifecycle.event_log or [])
    for raw in lifecycle_events:
        event = raw
        field = str(evidence.field or "").strip().lower()
        args = raw.get("arguments", {}) if isinstance(raw, dict) else getattr(raw, "arguments", {})
        result = raw.get("result", {}) if isinstance(raw, dict) else getattr(raw, "result", {})
        for source in (args or {}, result or {}):
            if str(source.get("field", "") or "").strip().lower() == field:
                return raw

    for event in getattr(getattr(txn, "agent_interpretation", None), "execution_trace", []) or []:
        if _event_matches_evidence(event, evidence):
            return event
    return None


def _event_value(event, key, default=None):
    if isinstance(event, dict):
        return event.get(key, default)
    return getattr(event, key, default)

def check_evidence_completeness(txn: Transaction) -> List[str]:
    """Require enough field evidence to evaluate the recorded dispute."""
    missing: List[str] = []

    m = txn.merchant_snapshot
    d = txn.agent_decision
    c = txn.user_request.explicit_constraints
    disputed = str(txn.dispute.disputed_field or "").strip().lower()

    standard = {
        "ram_gb": (
            getattr(m, "ram_gb", None),
            getattr(d, "purchased_ram_gb", None),
        ),
        "price_usd": (
            getattr(m, "price", None),
            getattr(d, "purchased_price", None),
        ),
        "seller": (
            getattr(m, "seller", None),
            getattr(d, "purchased_seller", None),
        ),
        "storage_gb": (
            getattr(m, "storage_gb", None),
            getattr(m, "storage_gb_actual", None),
        ),
        "delivery_days": (
            getattr(m, "delivery_days", None),
            getattr(d, "purchased_delivery_days", None),
        ),
        "color": (
            getattr(m, "color", None)
            or getattr(m, "color_at_checkout", None)
            or getattr(m, "color_actual", None)
            or (getattr(m, "specs", {}) or {}).get("color"),
            getattr(d, "purchased_color", None),
        ),
    }

    for field, (primary, alternate) in standard.items():
        if (
            constraint_exists(c, field)
            or disputed == field
            or (field == "price_usd" and disputed == "price")
        ):
            if primary is None and alternate is None:
                missing.append(f"merchant_snapshot.{field}")

    if disputed == "condition":
        specs = getattr(m, "specs", {}) or {}
        attrs = getattr(d, "attributes", {}) or {}

        if specs.get("condition") is None and attrs.get("condition") is None:
            missing.append("condition evidence")

    custom = getattr(c, "custom_attributes", {}) or {}

    for field in custom:
        if not constraint_exists(c, field):
            continue

        item = (getattr(m, "attributes", {}) or {}).get(field)

        observed = None

        if item is not None:
            observed = (
                getattr(item, "delivered", None)
                or getattr(item, "checkout", None)
                or getattr(item, "advertised", None)
            )

        if observed is None:
            observed = (getattr(m, "specs", {}) or {}).get(field)

        if observed is None and disputed == field:
            missing.append(f"merchant_snapshot.attributes.{field}")

    return missing


def analyze_transaction(txn: Transaction) -> AnalysisResult:
    """
    Main entry point for analyzing a disputed transaction.
    """

    missing_fields = check_evidence_completeness(txn)

    # ---------------------------------------------------------
    # INSUFFICIENT EVIDENCE
    # ---------------------------------------------------------
    if missing_fields:
        incident = classify_incident(txn)

        score_breakdown = forensic_score_breakdown(
            txn,
            "INSUFFICIENT_EVIDENCE",
        )

        return AnalysisResult(
            transaction_id=txn.transaction_id,
            status=AnalysisStatus.INSUFFICIENT_EVIDENCE,
            incident=incident,
            dispute_drift=detect_dispute_drift(
                txn.user_request.raw_text,
                txn.dispute.user_claim,
            ),
            missing_fields=missing_fields,
            primary_fault=None,
            contributing_factors=[],
            preventability=PreventabilityRating.NOT_APPLICABLE,
            evidence_status="INCOMPLETE",
            evidence=[],
            counterfactual=simulate_counterfactual(
                txn,
                None,
                is_insufficient_evidence=True,
            ),
            economic_harm=txn.direct_financial_harm,
            harm_currency=txn.harm_currency,
            data_flags=(
                ["DUPLICATE_CHARGE"]
                if txn.duplicate_charge
                else []
            ),
            all_rule_results=[],
            forensic_score=calculate_forensic_score(
                txn,
                "INSUFFICIENT_EVIDENCE",
            ),
            forensic_score_breakdown=score_breakdown,
            explanation=(
                "Analysis halted due to INSUFFICIENT_EVIDENCE. "
                "Missing required evidence fields: "
                + ", ".join(missing_fields)
                + "."
            ),
            explanation_status="SKIPPED",
        )

    # ---------------------------------------------------------
    # RUN ALL RULES
    # ---------------------------------------------------------
    all_rule_results: List[RuleResult] = run_all_rules(txn)

    incident = classify_incident(txn)

    drift = detect_dispute_drift(
        txn.user_request.raw_text,
        txn.dispute.user_claim,
    )

    # ---------------------------------------------------------
    # DATA FLAGS + EVENT CHAIN
    # ---------------------------------------------------------
    data_flags: List[str] = []

    if txn.lifecycle and txn.lifecycle.event_log:
        integrity, missing_hashes = verify_event_chain(
            txn.lifecycle.event_log
        )

        data_flags.append(
            f"EVIDENCE_CHAIN_{integrity}"
        )

    if txn.duplicate_charge:
        data_flags.append("DUPLICATE_CHARGE")

    # ---------------------------------------------------------
    # ATTRIBUTION
    # ---------------------------------------------------------
    primary_fault, contributing_factors = (
        calculate_attribution_scores(
            all_rule_results
        )
    )

    # ---------------------------------------------------------
    # PREVENTABILITY
    # ---------------------------------------------------------
    fired_rules = [
        r for r in all_rule_results
        if r.fired
    ]

    preventability = determine_preventability(
        primary_fault=primary_fault,
        all_fired_rules=fired_rules,
        is_insufficient_evidence=False,
    )

    # ---------------------------------------------------------
    # COUNTERFACTUAL
    # ---------------------------------------------------------
    counterfactual = simulate_counterfactual(
        txn=txn,
        primary_fault=primary_fault,
        is_insufficient_evidence=False,
    )

    # ---------------------------------------------------------
    # COMBINED EVIDENCE
    # ---------------------------------------------------------
    combined_evidence: List[EvidenceItem] = []

    for rule in fired_rules:
        for idx, evidence in enumerate(
            rule.evidence,
            1,
        ):
            if evidence.provenance is None:
                event = _find_evidence_event(txn, evidence)
                event_id = _event_value(event, "event_id") if event is not None else None
                content_hash = _event_value(event, "content_hash") if event is not None else None
                parent_hash = _event_value(event, "parent_hash") if event is not None else None
                event_timestamp = _event_value(event, "timestamp", txn.timestamp) if event is not None else txn.timestamp
                evidence.provenance = EvidenceProvenance(
                    evidence_id=(
                        f"{txn.transaction_id}:"
                        f"{rule.category.value}:"
                        f"{idx}"
                    ),
                    event_id=event_id,
                    source_type=(
                        "LIFECYCLE_EVENT" if txn.lifecycle and txn.lifecycle.event_log and event is not None
                        else "AGENT_EXECUTION_EVENT" if event is not None
                        else "TRANSACTION_RECORD"
                    ),
                    source_reference=(event_id or txn.transaction_id),
                    capture_method=(
                        "RECORDED_EVENT_EVIDENCE" if event is not None
                        else "RECORDED_TRANSACTION_EVIDENCE"
                    ),
                    timestamp=event_timestamp,
                    content_hash=content_hash,
                    parent_hash=parent_hash,
                    integrity_status=(
                        "RECORDED_EVENT" if event is not None
                        else "UNVERIFIED"
                    ),
                )

            combined_evidence.append(evidence)

    # ---------------------------------------------------------
    # EVIDENCE COVERAGE
    # ---------------------------------------------------------
    score_parts = evidence_breakdown(
        txn,
        type(
            "AnalysisView",
            (),
            {
                "all_rule_results": all_rule_results
            },
        )(),
    )

    integrity_value = None

    if data_flags and data_flags[0].startswith(
        "EVIDENCE_CHAIN_"
    ):
        integrity_value = data_flags[0].replace(
            "EVIDENCE_CHAIN_",
            "",
        )

    forensic_score = calculate_forensic_score(
        txn,
        "ANALYZED",
        integrity_value,
    )

    # ---------------------------------------------------------
    # FINAL RESULT
    # ---------------------------------------------------------
    result = AnalysisResult(
        transaction_id=txn.transaction_id,
        status=AnalysisStatus.ANALYZED,
        incident=incident,
        missing_fields=[],
        primary_fault=primary_fault,
        contributing_factors=contributing_factors,
        preventability=preventability,
        economic_harm=(
            txn.direct_financial_harm
            if txn.direct_financial_harm is not None
            else (
                incident.economic_harm
                if incident
                else None
            )
        ),
        harm_currency=(
            txn.harm_currency
            if txn.harm_currency is not None
            else (
                incident.harm_currency
                if incident
                else None
            )
        ),
        dispute_drift=drift,
        evidence_status="COMPLETE",
        evidence=combined_evidence,
        counterfactual=counterfactual,
        data_flags=data_flags,
        all_rule_results=all_rule_results,
        forensic_score=forensic_score,
        forensic_score_breakdown={
            k: v["percent"]
            for k, v in score_parts.items()
        },
        explanation="",
        explanation_status="PENDING",
    )

    return result