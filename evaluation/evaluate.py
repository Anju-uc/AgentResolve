"""
Evaluation Runner CLI for AgentResolve.

Runs three evaluation layers:

1. Development benchmark
   Existing labelled cases used as regression tests.

2. Holdout benchmark
   Existing labelled cases kept separate from development cases.

3. Adversarial robustness suite
   Explicit challenge transformations built from real holdout records.
   Expected outcomes are declared independently of the analyzer's prediction.

Important:
- The deterministic forensic analyzer remains authoritative.
- Evaluation never modifies engine decisions.
- Adversarial expectations are NOT copied from model output.
- Synthetic evaluation is proof-of-concept evidence, not production validation.

Usage:
    python -m evaluation.evaluate
"""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

from app.engine.analyzer import analyze_transaction
from app.models.result import AnalysisStatus
from app.models.transaction import Transaction
from evaluation.metrics import compute_metrics, format_confusion_matrix


# ---------------------------------------------------------------------------
# Project paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def resolve_project_path(file_path: str) -> str:
    """
    Resolve relative paths from the project root rather than from the
    terminal's current working directory.
    """
    path = Path(file_path)

    if path.is_absolute():
        return str(path)

    return str(PROJECT_ROOT / path)


# ---------------------------------------------------------------------------
# Dataset loading
# ---------------------------------------------------------------------------

def load_dataset(file_path: str) -> List[Transaction]:
    """
    Load transaction cases from JSON and validate them using the
    canonical Transaction schema.
    """
    resolved_path = resolve_project_path(file_path)

    if not os.path.exists(resolved_path):
        raise FileNotFoundError(
            f"Dataset file not found at: {resolved_path}"
        )

    with open(resolved_path, "r", encoding="utf-8") as file:
        raw_data = json.load(file)

    return [
        Transaction.model_validate(item)
        for item in raw_data
    ]


# ---------------------------------------------------------------------------
# Prediction extraction
# ---------------------------------------------------------------------------

def prediction_from_analysis(analysis: Any) -> str:
    """
    Convert the deterministic AnalysisResult into the single label
    used for benchmark comparison.

    This function only extracts the engine's prediction.
    It does not alter or repair it.
    """
    if analysis.status == AnalysisStatus.INSUFFICIENT_EVIDENCE:
        return "INSUFFICIENT_EVIDENCE"

    if analysis.primary_fault:
        return analysis.primary_fault.category.value

    return "NO_FAULT_DETECTED"


# ---------------------------------------------------------------------------
# Standard benchmark evaluation
# ---------------------------------------------------------------------------

def evaluate_dataset(
    transactions: List[Transaction],
) -> Dict[str, Any]:
    """
    Evaluate a labelled transaction dataset.

    Ground truth comes from the recorded case.
    Prediction comes from the deterministic analyzer.
    """
    y_true: List[str] = []
    y_pred: List[str] = []

    for txn in transactions:
        if not txn.ground_truth:
            continue

        y_true.append(str(txn.ground_truth.primary_fault))

        analysis = analyze_transaction(txn)
        y_pred.append(prediction_from_analysis(analysis))

    return compute_metrics(y_true, y_pred)


# ---------------------------------------------------------------------------
# Adversarial robustness suite
# ---------------------------------------------------------------------------

def build_adversarial_cases(
    holdout_cases: List[Transaction],
) -> List[Tuple[Transaction, str, str]]:
    """
    Construct explicit robustness challenges from the real holdout corpus.

    Returns:
        (transaction, expected_label, rationale)

    The expected label is declared by the evaluation author and is never
    derived from the analyzer prediction.
    """
    by_id = {
        txn.transaction_id: txn
        for txn in holdout_cases
    }

    required_ids = {
        "TXN_021",
        "TXN_022",
        "TXN_027",
        "TXN_028",
        "TXN_029",
    }

    missing = sorted(
        required_ids - set(by_id)
    )

    if missing:
        raise RuntimeError(
            "Adversarial benchmark requires these holdout cases: "
            + ", ".join(missing)
        )

    cases: List[Tuple[Transaction, str, str]] = []

    # ------------------------------------------------------------------
    # ADV-001
    #
    # Requirement is violated, but a pre-purchase validation event
    # explicitly failed.
    #
    # Expected:
    # NO_FAULT_DETECTED
    #
    # Reason:
    # A failed validation is not equivalent to skipped validation.
    # ------------------------------------------------------------------

    raw = copy.deepcopy(
        by_id["TXN_022"].model_dump()
    )

    raw["transaction_id"] = "ADV_001_FAILED_VALIDATION"

    raw["agent_decision"]["validation_steps_performed"] = []

    raw["agent_interpretation"]["execution_trace"] = [
        {
            "event_id": "ADV001-E1",
            "timestamp": "2026-08-10T10:46:00Z",
            "action": "validate_constraint",
            "tool": "validator",
            "arguments": {
                "field": "ram_gb"
            },
            "result": {
                "field": "ram_gb",
                "passed": False
            },
            "status": "FAILED",
            "content_hash": None,
            "parent_hash": None,
        }
    ]

    cases.append(
        (
            Transaction.model_validate(raw),
            "NO_FAULT_DETECTED",
            (
                "A failed pre-purchase validation does not prove "
                "that validation was skipped."
            ),
        )
    )

    # ------------------------------------------------------------------
    # ADV-002
    #
    # The originally disputed RAM requirement is now satisfied.
    #
    # Expected:
    # NO_FAULT_DETECTED
    #
    # This guards against generating fault merely because a dispute exists.
    # ------------------------------------------------------------------

    raw = copy.deepcopy(
        by_id["TXN_022"].model_dump()
    )

    raw["transaction_id"] = "ADV_002_REQUIREMENT_SATISFIED"

    raw["merchant_snapshot"]["ram_gb"] = 32.0
    raw["merchant_snapshot"]["ram_gb_actual"] = 32.0
    raw["agent_decision"]["purchased_ram_gb"] = 32.0

    cases.append(
        (
            Transaction.model_validate(raw),
            "NO_FAULT_DETECTED",
            (
                "The purchased RAM satisfies the recorded 32GB minimum, "
                "so the dispute alone does not establish a fault."
            ),
        )
    )

    # ------------------------------------------------------------------
    # ADV-003
    #
    # Raw request mentions color, but structured explicit_constraints
    # does not record color.
    #
    # Expected:
    # NO_FAULT_DETECTED
    #
    # This checks the parser/evidence-consistency boundary.
    # ------------------------------------------------------------------

    raw = copy.deepcopy(
        by_id["TXN_021"].model_dump()
    )

    raw["transaction_id"] = "ADV_003_PARSER_INCONSISTENCY"

    raw["user_request"]["raw_text"] = (
        "Buy a 32-inch monitor in White with at least "
        "144Hz refresh rate."
    )

    raw["user_request"]["explicit_constraints"] = {}

    raw["agent_interpretation"]["parsed_constraints"] = {}

    raw["agent_interpretation"]["accessed_constraint_keys"] = []

    raw["dispute"]["disputed_field"] = "color"

    raw["dispute"]["user_claim"] = (
        "I wanted a White monitor."
    )

    cases.append(
        (
            Transaction.model_validate(raw),
            "NO_FAULT_DETECTED",
            (
                "The raw request and structured record are inconsistent, "
                "but that does not establish USER_AMBIGUITY."
            ),
        )
    )

    # ------------------------------------------------------------------
    # ADV-004
    #
    # Seller changes between listing and checkout while the agent also
    # violated the explicit seller requirement.
    #
    # Expected:
    # AGENT_MISJUDGMENT
    #
    # Why:
    # Both rules can fire. The deterministic attribution scoring keeps
    # AGENT_MISJUDGMENT primary while retaining merchant evidence.
    # ------------------------------------------------------------------

    raw = copy.deepcopy(
        by_id["TXN_027"].model_dump()
    )

    raw["transaction_id"] = "ADV_004_CONFLICTING_SIGNALS"

    raw["merchant_snapshot"]["seller_at_checkout"] = (
        "DifferentStore"
    )

    raw["agent_decision"]["purchased_seller"] = (
        "DifferentStore"
    )

    cases.append(
        (
            Transaction.model_validate(raw),
            "AGENT_MISJUDGMENT",
            (
                "The case contains both agent constraint failure and "
                "merchant seller-state change; agent misjudgment remains "
                "the stronger primary attribution."
            ),
        )
    )

    # ------------------------------------------------------------------
    # ADV-005
    #
    # Storage changes between listing and delivery while the purchased
    # storage also violates the explicit 2TB requirement.
    #
    # Expected:
    # AGENT_MISJUDGMENT
    #
    # This checks primary attribution when multiple evidence sources fire.
    # ------------------------------------------------------------------

    raw = copy.deepcopy(
        by_id["TXN_028"].model_dump()
    )

    raw["transaction_id"] = "ADV_005_STORAGE_CONFLICT"

    raw["merchant_snapshot"]["storage_gb_actual"] = 512

    cases.append(
        (
            Transaction.model_validate(raw),
            "AGENT_MISJUDGMENT",
            (
                "The record contains both a violated storage requirement "
                "and a listing-to-delivery mismatch; the stronger "
                "deterministic agent attribution remains primary."
            ),
        )
    )

    # ------------------------------------------------------------------
    # ADV-006
    #
    # Remove the storage evidence entirely from an already
    # insufficient-evidence case.
    #
    # Expected:
    # INSUFFICIENT_EVIDENCE
    # ------------------------------------------------------------------

    raw = copy.deepcopy(
        by_id["TXN_029"].model_dump()
    )

    raw["transaction_id"] = (
        "ADV_006_MISSING_STORAGE_EVIDENCE"
    )

    raw["merchant_snapshot"].pop(
        "storage_gb",
        None,
    )

    raw["merchant_snapshot"].pop(
        "storage_gb_actual",
        None,
    )

    cases.append(
        (
            Transaction.model_validate(raw),
            "INSUFFICIENT_EVIDENCE",
            (
                "The requested storage requirement cannot be established "
                "because the relevant evidence is absent."
            ),
        )
    )

    return cases


def evaluate_adversarial_cases(
    cases: List[Tuple[Transaction, str, str]],
) -> Dict[str, Any]:
    """
    Evaluate the explicitly specified adversarial cases.

    Expected labels are supplied by build_adversarial_cases() and are
    never taken from analyzer output.
    """
    y_true: List[str] = []
    y_pred: List[str] = []

    case_results: List[Dict[str, Any]] = []

    for txn, expected, rationale in cases:
        analysis = analyze_transaction(txn)

        predicted = prediction_from_analysis(
            analysis
        )

        y_true.append(expected)
        y_pred.append(predicted)

        case_results.append(
            {
                "transaction_id": txn.transaction_id,
                "expected": expected,
                "predicted": predicted,
                "correct": expected == predicted,
                "rationale": rationale,
            }
        )

    metrics = compute_metrics(
        y_true,
        y_pred,
    )

    metrics["case_results"] = case_results

    return metrics


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def print_standard_metrics(
    name: str,
    metrics: Dict[str, Any],
    case_count: int,
) -> None:
    """Print standard benchmark metrics."""
    print(f"\n[{name}: {case_count} cases]")

    print(
        f"Accuracy:        "
        f"{metrics['accuracy'] * 100:.2f}%"
    )

    print(
        f"Macro Precision: "
        f"{metrics['macro_precision'] * 100:.2f}%"
    )

    print(
        f"Macro Recall:    "
        f"{metrics['macro_recall'] * 100:.2f}%"
    )

    print(
        f"Macro F1 Score:  "
        f"{metrics['macro_f1'] * 100:.2f}%"
    )

    print("\nConfusion Matrix:")
    print(
        format_confusion_matrix(metrics)
    )


def print_adversarial_metrics(
    metrics: Dict[str, Any],
) -> None:
    """Print adversarial results with case-level audit."""
    case_results = metrics.get(
        "case_results",
        [],
    )

    print(
        f"\n[Adversarial Robustness Suite: "
        f"{len(case_results)} cases]"
    )

    print(
        f"Accuracy:        "
        f"{metrics['accuracy'] * 100:.2f}%"
    )

    print(
        f"Macro Precision: "
        f"{metrics['macro_precision'] * 100:.2f}%"
    )

    print(
        f"Macro Recall:    "
        f"{metrics['macro_recall'] * 100:.2f}%"
    )

    print(
        f"Macro F1 Score:  "
        f"{metrics['macro_f1'] * 100:.2f}%"
    )

    print("\nCase-level adversarial audit:")

    for result in case_results:
        status = (
            "PASS"
            if result["correct"]
            else "FAIL"
        )

        print(
            f"  [{status}] "
            f"{result['transaction_id']}: "
            f"expected={result['expected']} "
            f"predicted={result['predicted']}"
        )

        print(
            f"         {result['rationale']}"
        )

    print("\nConfusion Matrix:")
    print(
        format_confusion_matrix(metrics)
    )


# ---------------------------------------------------------------------------
# Main evaluation
# ---------------------------------------------------------------------------

def run_evaluation(
    dev_path: str = "data/development_cases.json",
    holdout_path: str = "data/holdout_cases.json",
) -> Dict[str, Any]:
    """
    Run development, holdout and adversarial evaluation.
    """
    print("=" * 80)
    print(" AgentResolve Forensic Engine — Evaluation")
    print("=" * 80)

    # ---------------------------------------------------------------
    # Development
    # ---------------------------------------------------------------

    dev_cases = load_dataset(
        dev_path
    )

    dev_metrics = evaluate_dataset(
        dev_cases
    )

    print_standard_metrics(
        "Development Dataset",
        dev_metrics,
        len(dev_cases),
    )

    # ---------------------------------------------------------------
    # Holdout
    # ---------------------------------------------------------------

    holdout_cases = load_dataset(
        holdout_path
    )

    holdout_metrics = evaluate_dataset(
        holdout_cases
    )

    print_standard_metrics(
        "Holdout Dataset",
        holdout_metrics,
        len(holdout_cases),
    )

    # ---------------------------------------------------------------
    # Adversarial robustness
    # ---------------------------------------------------------------

    adversarial_cases = (
        build_adversarial_cases(
            holdout_cases
        )
    )

    adversarial_metrics = (
        evaluate_adversarial_cases(
            adversarial_cases
        )
    )

    print_adversarial_metrics(
        adversarial_metrics
    )

    # ---------------------------------------------------------------
    # Interpretation
    # ---------------------------------------------------------------

    print("\n" + "=" * 80)
    print(" Evaluation Interpretation")
    print("=" * 80)

    print(
        "\nDevelopment and holdout results are "
        "synthetic labelled regression benchmarks."
    )

    print(
        "The adversarial suite applies explicit "
        "challenge transformations to real holdout "
        "records and compares them with pre-declared "
        "policy expectations."
    )

    print(
        "These synthetic suites demonstrate "
        "proof-of-concept behavior; they are not "
        "production statistical validation."
    )

    print(
        "\nThe deterministic analyzer remains "
        "authoritative. The evaluation layer does "
        "not alter engine decisions."
    )

    print("=" * 80)

    return {
        "development": dev_metrics,
        "holdout": holdout_metrics,
        "adversarial": adversarial_metrics,
    }


if __name__ == "__main__":
    run_evaluation()