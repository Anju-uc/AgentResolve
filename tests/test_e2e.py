"""
End-to-End Integration Tests (Phase 19).

Verifies full forensic dispute processing pipeline end-to-end:
JSON payload -> Domain Model -> Analyzer -> Scoring -> Preventability -> Counterfactual -> Report
"""

import json
from app.models.transaction import Transaction
from app.engine.analyzer import analyze_transaction
from app.llm.explainer import generate_explanation
from app.reports.report_builder import build_dispute_report
from evaluation.evaluate import load_dataset


def test_full_end_to_end_dispute_pipeline():
    """Verifies complete E2E pipeline for TXN_002, TXN_004, TXN_007, and TXN_011."""
    cases = load_dataset("data/development_cases.json")
    demo_ids = ["TXN_002", "TXN_004", "TXN_007", "TXN_011"]
    demo_cases = [c for c in cases if c.transaction_id in demo_ids]
    
    assert len(demo_cases) == 4
    
    for txn in demo_cases:
        # Step 1: Model validation
        json_data = txn.model_dump()
        parsed_txn = Transaction.model_validate(json_data)
        
        # Step 2: Analyzer execution
        analysis = analyze_transaction(parsed_txn)
        assert analysis.status.value == "ANALYZED"
        
        # Step 3: LLM Explanation
        analysis_with_exp = generate_explanation(analysis)
        assert analysis_with_exp.explanation != ""
        
        # Step 4: Dispute Report assembly
        report = build_dispute_report(analysis_with_exp, parsed_txn)
        assert report["report_metadata"]["transaction_id"] == parsed_txn.transaction_id
        assert report["attribution_summary"]["primary_fault"]["category"] == analysis.primary_fault.category.value
        assert "recorded_facts" in report
        
        # Convert report to JSON string to ensure serializability
        json_str = json.dumps(report)
        assert len(json_str) > 100
