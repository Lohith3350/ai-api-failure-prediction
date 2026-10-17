"""
End-to-end integration tests for SPECTRA API Failure Prediction Platform.
Validates the complete pipeline:
Telemetry Ingestion -> Streaming ML Inference -> Root Cause Analysis -> Decision Engine -> Incident Alerts
"""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.prediction_service import reset_predictions
from backend.app.services.telemetry_service import reset_telemetry, seed_default_data

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_system_state():
    """Reset telemetry buffers and cached predictions before each test."""
    reset_telemetry()
    reset_predictions()
    yield
    reset_telemetry()
    reset_predictions()


def test_system_health_and_overview():
    """Verify system health, overview, and topology endpoints."""
    res_health = client.get("/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "ok"

    res_overview = client.get("/system/overview")
    assert res_overview.status_code == 200
    ov = res_overview.json()
    assert "status" in ov
    assert "total_services" in ov
    assert ov["total_services"] == 3
    assert "average_cluster_latency_ms" in ov
    assert "peak_failure_probability" in ov

    res_topology = client.get("/system/topology")
    assert res_topology.status_code == 200
    top = res_topology.json()
    assert "nodes" in top
    assert "edges" in top
    assert len(top["nodes"]) >= 3


def test_telemetry_ingest_and_predictions():
    """Verify nominal telemetry ingestion and failure prediction inference."""
    nominal_record = {
        "timestamp": "2026-10-17T12:00:00Z",
        "service_name": "order-service",
        "response_time_ms": 45.0,
        "request_count": 80,
        "error_rate": 0.001,
        "http_5xx_count": 0,
        "timeout_count": 0,
        "cpu_usage_pct": 25.0,
        "memory_usage_pct": 35.0,
        "dependency_latency_ms": 30.0,
    }

    res_post = client.post("/telemetry", json=nominal_record)
    assert res_post.status_code == 200
    assert res_post.json()["accepted"] is True

    res_pred = client.get("/predictions/order-service")
    assert res_pred.status_code == 200
    pred = res_pred.json()
    assert pred["service_name"] == "order-service"
    assert 0.0 <= pred["failure_probability"] <= 1.0
    assert pred["risk_level"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
    assert isinstance(pred["recommended_actions"], list)


def test_failure_escalation_and_decision_mitigation():
    """Verify that severe anomaly injection escalates risk to HIGH or CRITICAL with runbook recommendations."""
    # Inject multiple severe fault records to simulate a deteriorating cascade
    fault_records = [
        {
            "timestamp": f"2026-10-17T12:0{i}:00Z",
            "service_name": "payment-service",
            "response_time_ms": 800.0 + i * 50.0,
            "request_count": 150,
            "error_rate": 0.50 + i * 0.05,
            "http_5xx_count": 20 + i * 5,
            "timeout_count": 10 + i * 2,
            "cpu_usage_pct": 92.0,
            "memory_usage_pct": 89.0,
            "dependency_latency_ms": 450.0,
        }
        for i in range(3)
    ]

    for rec in fault_records:
        res = client.post("/telemetry", json=rec)
        assert res.status_code == 200

    # Check updated prediction
    res_pred = client.get("/predictions/payment-service")
    assert res_pred.status_code == 200
    pred = res_pred.json()
    assert pred["service_name"] == "payment-service"
    assert pred["failure_probability"] >= 0.70
    assert pred["risk_level"] in ("HIGH", "CRITICAL")
    assert len(pred["recommended_actions"]) > 0


def test_incident_detection_and_root_cause_diagnosis():
    """Verify that elevated risk triggers incident alerts with diagnosed root cause."""
    # Inject critical failure telemetry
    critical_record = {
        "timestamp": "2026-10-17T12:15:00Z",
        "service_name": "payment-service",
        "response_time_ms": 980.0,
        "request_count": 200,
        "error_rate": 0.65,
        "http_5xx_count": 35,
        "timeout_count": 15,
        "cpu_usage_pct": 98.0,
        "memory_usage_pct": 95.0,
        "dependency_latency_ms": 600.0,
    }
    client.post("/telemetry", json=critical_record)

    res_inc = client.get("/incidents")
    assert res_inc.status_code == 200
    data = res_inc.json()
    assert "incidents" in data
    assert len(data["incidents"]) >= 1

    incident = next((inc for inc in data["incidents"] if inc["service_name"] == "payment-service"), None)
    assert incident is not None
    assert incident["severity"] in ("HIGH", "CRITICAL")
    assert "root_cause_service" in incident
    assert len(incident["recommended_actions"]) > 0


def test_simulation_workflow():
    """Verify interactive simulation step and reset endpoints."""
    step_res = client.post("/simulation/step", json={"scenario": "latency_ramp"})
    assert step_res.status_code == 200
    step_data = step_res.json()
    assert "scenario" in step_data
    assert "predictions" in step_data
    assert len(step_data["predictions"]) == 3

    reset_res = client.post("/simulation/reset")
    assert reset_res.status_code == 200
    reset_data = reset_res.json()
    assert reset_data.get("status") == "ok"
