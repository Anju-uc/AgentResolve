"""
Evaluation Metrics module for AgentResolve.

Calculates benchmark metrics comparing predicted primary fault attributions against ground-truth:
- Overall Accuracy
- Macro Precision, Macro Recall, Macro F1
- Per-category Precision, Recall, F1
- Confusion Matrix
"""

from typing import List, Dict, Any, Tuple
import numpy as np
from sklearn.metrics import confusion_matrix, classification_report


CANONICAL_CATEGORIES = [
    "USER_AMBIGUITY",
    "AGENT_MISJUDGMENT",
    "MERCHANT_DATA_ERROR",
    "EXTERNAL_CHANGE",
    "USER_POST_PURCHASE_CHANGE",
    "NO_FAULT_DETECTED",
    "INSUFFICIENT_EVIDENCE",
]


def compute_metrics(y_true: List[str], y_pred: List[str]) -> Dict[str, Any]:
    """
    Computes accuracy, macro precision/recall/f1, per-category metrics, and confusion matrix.

    Args:
        y_true: List of ground-truth primary category strings.
        y_pred: List of predicted primary category strings.

    Returns:
        Dictionary containing overall and per-category evaluation metrics.
    """
    labels = [cat for cat in CANONICAL_CATEGORIES if cat in y_true or cat in y_pred]

    # Confusion matrix
    cm = confusion_matrix(y_true, y_pred, labels=labels)

    # Detailed per-category report
    report = classification_report(
        y_true, y_pred, labels=labels, output_dict=True, zero_division=0
    )

    accuracy = float(report.get("accuracy", 0.0))
    macro_avg = report.get("macro avg", {})

    per_category: Dict[str, Dict[str, float]] = {}
    for label in labels:
        if label in report:
            per_category[label] = {
                "precision": float(report[label]["precision"]),
                "recall": float(report[label]["recall"]),
                "f1_score": float(report[label]["f1-score"]),
                "support": int(report[label]["support"]),
            }

    metrics: Dict[str, Any] = {
        "accuracy": round(accuracy, 4),
        "macro_precision": round(float(macro_avg.get("precision", 0.0)), 4),
        "macro_recall": round(float(macro_avg.get("recall", 0.0)), 4),
        "macro_f1": round(float(macro_avg.get("f1-score", 0.0)), 4),
        "per_category": per_category,
        "confusion_matrix": cm.tolist(),
        "labels": labels,
        "total_cases": len(y_true),
    }

    return metrics


def format_confusion_matrix(metrics: Dict[str, Any]) -> str:
    """
    Formats confusion matrix into a human-readable ASCII table.

    Args:
        metrics: Dictionary returned by compute_metrics.

    Returns:
        Formatted ASCII table string.
    """
    labels = metrics["labels"]
    cm = np.array(metrics["confusion_matrix"])

    label_hdr = "True \\ Pred"
    header = f"{label_hdr:<28} " + " ".join([f"{l[:10]:>10}" for l in labels])
    lines = [header, "-" * len(header)]

    for idx, label in enumerate(labels):
        row_str = f"{label:<28} " + " ".join([f"{val:>10}" for val in cm[idx]])
        lines.append(row_str)

    return "\n".join(lines)
