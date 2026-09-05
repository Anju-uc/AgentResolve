"""FastAPI routes for the AgentResolve forensic workstation."""

from typing import Any, Dict
from fastapi import APIRouter, HTTPException

from app.models.transaction import Transaction
from app.engine.analyzer import analyze_transaction
from app.llm.explainer import generate_explanation
from app.reports.report_builder import build_dispute_report
from evaluation.evaluate import load_dataset
from agent.simulator import execute_purchase, PurchaseBlockedError

router = APIRouter()


def _cases():
    dev = load_dataset("data/development_cases.json")
    holdout = load_dataset("data/holdout_cases.json")
    return dev, holdout


@router.get("/health")
def health_check() -> Dict[str, Any]:
    return {"status": "healthy", "service": "AgentResolve Forensic Engine API", "version": "2.3.0"}


@router.get("/cases")
def list_cases() -> Dict[str, Any]:
    dev, holdout = _cases()
    return {"development_cases": [x.transaction_id for x in dev], "holdout_cases": [x.transaction_id for x in holdout], "total_cases": len(dev)+len(holdout)}


@router.get("/cases/{transaction_id}")
def get_case(transaction_id: str) -> Dict[str, Any]:
    dev, holdout = _cases()
    for txn in dev + holdout:
        if txn.transaction_id.upper() == transaction_id.upper():
            return txn.model_dump()
    raise HTTPException(status_code=404, detail=f"Transaction '{transaction_id}' not found in dataset.")


@router.post("/analyze")
def analyze_dispute(txn: Transaction) -> Dict[str, Any]:
    try:
        return build_dispute_report(generate_explanation(analyze_transaction(txn)), txn)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error executing forensic analysis: {exc}")


@router.post("/agent/execute")
def execute_agent(payload: Dict[str, Any]) -> Dict[str, Any]:
    query = str(payload.get("query", "")).strip()
    if not query:
        raise HTTPException(status_code=400, detail="query is required")
    try:
        txn = execute_purchase(
            query,
            str(payload.get("currency") or ("USD" if any(token in query.lower() for token in ("$", "usd", "us dollar", "dollars")) else "INR")),
            allow_constraint_override=bool(payload.get("proceed_without_constraint", False)),
        )
    except PurchaseBlockedError as exc:
        return {
            "status": "NO_COMPLIANT_PRODUCT_FOUND",
            "purchase_blocked": True,
            "message": "No product satisfies the recorded requirements. No authorization, checkout, or payment was executed.",
            "constraints": exc.constraints.model_dump(exclude_none=True),
            "candidates": exc.candidates,
            "requires_explicit_override": True,
        }
    return {"status": "PURCHASE_CREATED", "purchase_blocked": False, "transaction": txn.model_dump(), "execution_trace": [e.model_dump() for e in txn.agent_interpretation.execution_trace]}


@router.get("/transactions/{transaction_id}")
def get_transaction(transaction_id: str) -> Dict[str, Any]:
    return get_case(transaction_id)


@router.post("/disputes")
def create_dispute(payload: Dict[str, Any]) -> Dict[str, Any]:
    transaction_id = str(payload.get("transaction_id", "")).strip()
    claim = str(payload.get("claim", "")).strip()
    if not transaction_id or not claim:
        raise HTTPException(status_code=400, detail="transaction_id and claim are required")
    dev, holdout = _cases()
    txn = next((x for x in dev + holdout if x.transaction_id.upper() == transaction_id.upper()), None)
    if txn is None:
        raise HTTPException(status_code=404, detail="transaction not found")
    # The persistent demo corpus remains read-only; return an investigation preview.
    preview = txn.model_copy(deep=True)
    preview.dispute.user_claim = claim
    analysis = analyze_transaction(preview)
    return {"transaction": preview.model_dump(), "report": build_dispute_report(generate_explanation(analysis), preview)}


@router.get("/investigations/{transaction_id}")
def get_investigation(transaction_id: str) -> Dict[str, Any]:
    txn = Transaction.model_validate(get_case(transaction_id))
    return build_dispute_report(generate_explanation(analyze_transaction(txn)), txn)


@router.get("/investigations")
def list_investigations() -> Dict[str, Any]:
    dev, holdout = _cases()
    items=[]
    for txn in dev + holdout:
        analysis=analyze_transaction(txn)
        items.append({"case":txn.transaction_id,"status":analysis.status.value,"incident":analysis.incident.incident_type.value if analysis.incident else None,"primary_fault":analysis.primary_fault.category.value if analysis.primary_fault else None})
    return {"items":items}
