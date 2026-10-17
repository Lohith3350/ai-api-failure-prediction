"""Incident management API routes."""

from fastapi import APIRouter
from typing import Dict, Any, List
from datetime import datetime, timezone
from backend.app.services.prediction_service import get_all_predictions
from backend.app.services.root_cause_service import get_cluster_diagnosis, analyze_root_cause

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.get("")
@router.get("/")
def list_incidents() -> Dict[str, Any]:
    """List active microservice degradation alerts, diagnosed root causes, and runbook actions."""
    predictions = get_all_predictions()
    diagnosis = get_cluster_diagnosis()

    incidents: List[Dict[str, Any]] = []

    for pred in predictions:
        svc = pred["service_name"]
        risk = pred["risk_level"]
        prob = pred["failure_probability"]

        if risk in ("MEDIUM", "HIGH", "CRITICAL") or prob >= 0.30:
            root_diag = analyze_root_cause(svc)
            incidents.append({
                "id": f"inc-{svc}-{int(datetime.now(timezone.utc).timestamp())}",
                "service_name": svc,
                "severity": risk,
                "failure_probability": prob,
                "anomaly_score": pred.get("anomaly_score", 0.0),
                "timestamp": pred.get("timestamp") or datetime.now(timezone.utc).isoformat(),
                "title": f"Predicted Failure Risk on {svc}",
                "description": f"Failure probability is {prob*100:.1f}%. Model flagged anomalous degradation.",
                "root_cause_service": diagnosis.get("primary_root_cause") or svc,
                "confidence": diagnosis.get("confidence", 0.8),
                "reasons": pred.get("reasons", []),
                "recommended_actions": pred.get("recommended_actions", []),
                "affected_downstream": root_diag.get("affected_services", []),
            })

    return {
        "active_incident_count": len(incidents),
        "primary_root_cause": diagnosis.get("primary_root_cause"),
        "incidents": incidents,
    }
