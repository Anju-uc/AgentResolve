"""
Explanation-only LLM adapter for AgentResolve.

NON-NEGOTIABLE BOUNDARY:
The deterministic forensic engine decides:
- incident
- fault category
- attribution score
- evidence
- preventability
- missing evidence
- counterfactual

The LLM may only rewrite those deterministic findings
into human-readable explanation text.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

import httpx
from dotenv import load_dotenv

from app.models.result import AnalysisResult, AnalysisStatus


logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Load project .env when present.
load_dotenv(PROJECT_ROOT / ".env")


def format_deterministic_fallback_explanation(
    analysis: AnalysisResult,
) -> str:
    """Generate a fully offline deterministic explanation."""
    if analysis.status == AnalysisStatus.INSUFFICIENT_EVIDENCE:
        missing = ", ".join(analysis.missing_fields) or "required evidence"

        return (
            "Forensic Analysis Status: INSUFFICIENT EVIDENCE.\n"
            f"Reason: Required transaction evidence fields ({missing}) "
            "were missing or unrecorded. No fault attribution could be "
            "determined under AgentResolve rules."
        )

    primary = analysis.primary_fault

    primary_text = (
        f"{primary.category.value} "
        f"(Attribution Score: {primary.score}/100)"
        if primary
        else "NO_FAULT_DETECTED"
    )

    contributing_text = ""

    if analysis.contributing_factors:
        factors = [
            f"{item.category.value} ({item.score}/100)"
            for item in analysis.contributing_factors
        ]

        contributing_text = (
            " Contributing factors identified: "
            + ", ".join(factors)
            + "."
        )

    evidence_text = ""

    if analysis.evidence:
        statements = [
            f"- {item.evidence_statement}"
            for item in analysis.evidence
        ]

        evidence_text = (
            "\nKey Recorded Evidence:\n"
            + "\n".join(statements)
        )

    counterfactual_text = ""

    if (
        analysis.counterfactual
        and analysis.counterfactual.applicable
    ):
        counterfactual_text = (
            "\nCounterfactual Simulation: "
            + analysis.counterfactual.narrative
        )

    flags_text = ""

    if analysis.data_flags:
        flags_text = (
            "\nPayment/Data Flags: "
            + ", ".join(analysis.data_flags)
            + "."
        )

    return (
        "Forensic Findings Summary:\n"
        f"Primary Fault: {primary_text}."
        f"{contributing_text}\n"
        f"Preventability Rating: "
        f"{analysis.preventability.value}."
        f"{evidence_text}"
        f"{counterfactual_text}"
        f"{flags_text}"
    )


def generate_explanation(
    analysis: AnalysisResult,
    provider: Optional[str] = None,
    api_key: Optional[str] = None,
) -> AnalysisResult:
    """
    Populate explanation text.

    Deterministic forensic findings always remain authoritative.
    """
    # Evidence failure never needs an external LLM.
    if analysis.status == AnalysisStatus.INSUFFICIENT_EVIDENCE:
        analysis.explanation = (
            format_deterministic_fallback_explanation(analysis)
        )
        analysis.explanation_status = "INSUFFICIENT_EVIDENCE"
        return analysis

    selected_provider = (
        provider
        or os.getenv("LLM_PROVIDER", "mock")
    ).strip().lower()

    # Provider-specific credentials.
    if selected_provider == "openai":
        key = api_key or os.getenv("OPENAI_API_KEY")
    elif selected_provider == "gemini":
        key = api_key or os.getenv("GEMINI_API_KEY")
    else:
        key = None

    # Offline/default mode.
    if selected_provider == "mock" or not key:
        analysis.explanation = (
            format_deterministic_fallback_explanation(analysis)
        )
        analysis.explanation_status = "DETERMINISTIC_FALLBACK"
        return analysis

    if selected_provider not in {"openai", "gemini"}:
        logger.warning(
            "Unknown LLM_PROVIDER=%r; using deterministic fallback.",
            selected_provider,
        )

        analysis.explanation = (
            format_deterministic_fallback_explanation(analysis)
        )
        analysis.explanation_status = "DETERMINISTIC_FALLBACK"
        return analysis

    # Only deterministic findings are sent to the LLM. Compute conditional
    # values before interpolation so the prompt contains the actual findings,
    # not Python expression fragments.
    primary_text = (
        analysis.primary_fault.category.value
        if analysis.primary_fault
        else "NO_FAULT_DETECTED"
    )
    primary_score = (
        f"{analysis.primary_fault.score}/100"
        if analysis.primary_fault
        else "0/100"
    )
    evidence_statements = [
        e.evidence_statement for e in analysis.evidence
    ]
    counterfactual_text = (
        analysis.counterfactual.narrative
        if analysis.counterfactual
        else "None"
    )

    prompt = (
        "You are an explanation-only forensic summary tool.\n"
        "Do NOT determine fault.\n"
        "Do NOT change the category.\n"
        "Do NOT change the score.\n"
        "Do NOT change preventability.\n"
        "Do NOT invent facts.\n"
        "Do NOT speculate about missing evidence.\n"
        "Do NOT make legal-liability claims.\n"
        "Only explain the supplied deterministic findings.\n\n"
        f"Transaction ID: {analysis.transaction_id}\n"
        f"Primary Fault: {primary_text}\n"
        f"Score: {primary_score}\n"
        f"Preventability: {analysis.preventability.value}\n"
        f"Evidence Statements: {evidence_statements}\n"
        f"Counterfactual Replay: {counterfactual_text}"
    )

    try:
        timeout = float(
            os.getenv("LLM_TIMEOUT_SECONDS", "10")
        )

        if selected_provider == "openai":
            model = os.getenv(
                "OPENAI_MODEL",
                "gpt-4o-mini",
            )

            response = httpx.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt,
                        }
                    ],
                    "temperature": 0.2,
                },
                timeout=timeout,
            )

            if response.status_code == 200:
                data = response.json()

                text = (
                    data["choices"][0]["message"]["content"]
                    .strip()
                )

                if text:
                    analysis.explanation = text
                    analysis.explanation_status = (
                        "LLM_GENERATED"
                    )
                    return analysis

            logger.warning(
                "OpenAI request failed with HTTP %s.",
                response.status_code,
            )

        else:
            model = os.getenv(
                "GEMINI_MODEL",
                "gemini-3.8-flash",
            )

            url = (
                "https://generativelanguage.googleapis.com/"
                f"v1beta/models/{model}:generateContent"
            )

            response = httpx.post(
                url,
                headers={
                    "x-goog-api-key": key,
                    "Content-Type": "application/json",
                },
                json={
                    "contents": [
                        {
                            "parts": [
                                {
                                    "text": prompt
                                }
                            ]
                        }
                    ]
                },
                timeout=timeout,
            )

            if response.status_code == 200:
                data = response.json()

                candidates = data.get(
                    "candidates",
                    [],
                )

                if candidates:
                    parts = (
                        candidates[0]
                        .get("content", {})
                        .get("parts", [])
                    )

                    text = "\n".join(
                        str(part.get("text", ""))
                        for part in parts
                    ).strip()

                    if text:
                        analysis.explanation = text
                        analysis.explanation_status = (
                            "LLM_GENERATED"
                        )
                        return analysis

            logger.warning(
                "Gemini request failed with HTTP %s.",
                response.status_code,
            )

    except (
        httpx.HTTPError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        logger.warning(
            "LLM request failed; using deterministic fallback: %s",
            exc,
        )

    # Never let LLM failure break forensic analysis.
    analysis.explanation = (
        format_deterministic_fallback_explanation(analysis)
    )
    analysis.explanation_status = "FALLBACK"

    return analysis