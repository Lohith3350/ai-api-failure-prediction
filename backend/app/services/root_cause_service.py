"""Root cause analysis and cascade impact analysis service."""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from root_cause.root_cause_analyzer import analyze_probable_causes
from root_cause.impact_analyzer import find_affected_services
from root_cause.config import DEFAULT_DEPENDENCIES
from backend.app.services.telemetry_service import get_latest_records


def analyze_root_cause(service_name: str, telemetry: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Diagnose probable root causes and impacted services for a given service."""
    if telemetry is None:
        telemetry = {"services": get_latest_records()}

    causes = analyze_probable_causes(
        service_name=service_name,
        telemetry=telemetry,
        dependency_graph=DEFAULT_DEPENDENCIES,
    )
    affected = find_affected_services(
        service_name=service_name,
        dependency_graph=DEFAULT_DEPENDENCIES,
        transitive=True,
    )

    return {
        "service_name": service_name,
        "probable_causes": causes,
        "affected_services": affected,
    }


def get_cluster_diagnosis() -> Dict[str, Any]:
    """Perform a holistic cluster diagnosis to identify originating faults vs cascades."""
    latest = get_latest_records()
    services = ["payment-service", "order-service", "user-service"]

    all_diagnoses = {}
    suspicious_services = []

    for svc in services:
        diag = analyze_root_cause(svc, telemetry={"services": latest})
        all_diagnoses[svc] = diag
        if diag.get("probable_causes"):
            top = diag["probable_causes"][0]
            if top.get("anomaly_score", 0) > 0:
                suspicious_services.append((svc, top["anomaly_score"], top.get("reasons", [])))

    # Sort to determine highest anomaly
    suspicious_services.sort(key=lambda x: x[1], reverse=True)

    root_cause_candidate = suspicious_services[0][0] if suspicious_services else None
    confidence = 0.85 if root_cause_candidate else 0.0

    # If payment-service has high anomalies, it is the root of the cascade
    payment_anom = latest.get("payment-service", {}).get("cpu_usage_pct", 0)
    if payment_anom > 80:
        root_cause_candidate = "payment-service"
        confidence = 0.94

    return {
        "primary_root_cause": root_cause_candidate,
        "confidence": confidence,
        "diagnoses": all_diagnoses,
        "dependency_graph": DEFAULT_DEPENDENCIES,
    }
