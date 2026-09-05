"""
Integration Tests for FastAPI Routes (Phase 16).
"""

from fastapi.testclient import TestClient
from app.main import app
from evaluation.evaluate import load_dataset

client = TestClient(app)


def test_api_health_endpoint():
    """Test GET /health returns 200 and healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_api_list_cases_endpoint():
    """Test GET /cases returns list of dev and holdout cases."""
    response = client.get("/cases")
    assert response.status_code == 200
    data = response.json()
    assert "development_cases" in data
    assert "holdout_cases" in data
    assert len(data["development_cases"]) == 20
    assert len(data["holdout_cases"]) == 10


def test_api_get_specific_case_endpoint():
    """Test GET /cases/TXN_002 returns case JSON."""
    response = client.get("/cases/TXN_002")
    assert response.status_code == 200
    data = response.json()
    assert data["transaction_id"] == "TXN_002"
    assert data["user_request"]["explicit_constraints"]["ram_gb"] == 16.0


def test_api_analyze_endpoint():
    """Test POST /analyze returns full dispute report."""
    cases = {t.transaction_id: t for t in load_dataset("data/development_cases.json")}
    payload = cases["TXN_002"].model_dump()
    
    response = client.post("/analyze", json=payload)
    assert response.status_code == 200
    report = response.json()
    
    assert report["report_metadata"]["transaction_id"] == "TXN_002"
    assert report["attribution_summary"]["primary_fault"]["category"] == "AGENT_MISJUDGMENT"
    assert report["attribution_summary"]["preventability"] == "HIGH"
    assert len(report["evidence_trace"]) > 0
