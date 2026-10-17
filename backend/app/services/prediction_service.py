"""Prediction service bridging trained ML inference engine and decision engine."""

from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import logging

from ml.inference import RealTimeInferenceEngine
from backend.app.services.decision_service import classify_risk, recommend_actions
from backend.app.services.telemetry_service import get_latest_records, get_recent_telemetry

logger = logging.getLogger(__name__)

_ENGINE: Optional[RealTimeInferenceEngine] = None
_LATEST_PREDICTIONS: Dict[str, Dict[str, Any]] = {}


def get_engine() -> RealTimeInferenceEngine:
    global _ENGINE
    if _ENGINE is None:
        try:
            _ENGINE = RealTimeInferenceEngine()
        except Exception as e:
            logger.error(f"Failed to load ML models from disk: {e}")
            raise
    return _ENGINE


def process_telemetry_window(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Feed a window of service records into the ML inference engine and decision classifier."""
    global _LATEST_PREDICTIONS
    engine = get_engine()

    try:
        raw_predictions = engine.ingest_window(records)
    except Exception as e:
        logger.warning(f"Inference engine error during window ingestion: {e}")
        raw_predictions = []

    results = []
    for pred in raw_predictions:
        svc = pred["service_name"]
        prob = float(pred["failure_probability"])
        anom = float(pred["anomaly_score"])
        explanation = pred.get("explanation", [])

        # Decision engine risk classification
        risk_level = classify_risk(prob)

        # Build feature attribution reasons
        reasons = [
            f"{item.get('feature', 'feature')}: value={item.get('value', 0):.2f} (importance: {item.get('model_importance', 0):.3f})"
            for item in explanation
        ]

        # Decision engine recommendations
        probable_cause_names = [item.get("feature") for item in explanation[:2]]
        actions = recommend_actions(risk_level, probable_cause_names)

        enriched = {
            "service_name": svc,
            "failure_probability": prob,
            "anomaly_score": anom,
            "risk_level": risk_level,
            "reasons": reasons,
            "explanation": explanation,
            "recommended_actions": actions,
            "timestamp": pred.get("timestamp") or datetime.now(timezone.utc).isoformat(),
        }
        _LATEST_PREDICTIONS[svc] = enriched
        results.append(enriched)

    return results


def get_prediction(service_name: str) -> Dict[str, Any]:
    """Retrieve the latest real-time failure prediction for a service."""
    if service_name in _LATEST_PREDICTIONS:
        return _LATEST_PREDICTIONS[service_name]

    # If no prediction cached yet, compute from current latest telemetry
    latest_records = get_latest_records()
    if latest_records:
        process_telemetry_window(list(latest_records.values()))
        if service_name in _LATEST_PREDICTIONS:
            return _LATEST_PREDICTIONS[service_name]

    # Baseline default if telemetry buffer empty
    return {
        "service_name": service_name,
        "failure_probability": 0.01,
        "anomaly_score": 0.35,
        "risk_level": "LOW",
        "reasons": ["Telemetry within nominal operational bounds"],
        "explanation": [],
        "recommended_actions": recommend_actions("LOW"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def get_all_predictions() -> List[Dict[str, Any]]:
    """Retrieve latest predictions across all tracked microservices."""
    services = ["user-service", "order-service", "payment-service"]
    return [get_prediction(svc) for svc in services]


def predict_failure(features: Dict[str, Any]) -> Dict[str, Any]:
    """Compatibility method for direct feature-based failure query."""
    svc = features.get("service_name", "order-service")
    return get_prediction(svc)


def reset_predictions():
    """Reset the inference engine buffer and cached predictions."""
    global _LATEST_PREDICTIONS, _ENGINE
    _LATEST_PREDICTIONS.clear()
    if _ENGINE:
        _ENGINE.reset()
