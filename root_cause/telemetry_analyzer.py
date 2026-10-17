"""Detect telemetry values that exceed configurable warning thresholds."""

from typing import Any
from .config import THRESHOLDS, ANOMALY_WEIGHTS


def analyse_telemetry(
    record: dict,
    thresholds: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Return anomaly evidence and a heuristic score for one telemetry record.

    Missing or non-numeric fields are ignored rather than treated as failures.
    ``error_rate`` is expected to be a fraction between 0 and 1.
    """
    if not isinstance(record, dict):
        record = {}

    configured = dict(THRESHOLDS)
    if thresholds:
        configured.update(thresholds)

    reasons: list[str] = []
    anomalies: list[dict[str, Any]] = []
    score = 0

    for field, threshold in configured.items():
        value = record.get(field)
        if value is None or isinstance(value, bool):
            continue
        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            continue

        if numeric_value > threshold:
            reasons.append(
                f"{field}={numeric_value:g} exceeds threshold {threshold:g}"
            )
            anomalies.append({
                "metric": field,
                "value": numeric_value,
                "threshold": threshold,
            })
            score += ANOMALY_WEIGHTS.get(field, 1)

    return {
        "service_name": record.get("service_name"),
        "is_anomalous": bool(anomalies),
        "anomaly_score": score,
        "anomaly_count": len(anomalies),
        "reasons": reasons,
        "anomalies": anomalies,
    }


def analyse_telemetry_history(
    records: list[dict],
    thresholds: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Analyse a service's records and return the latest record's assessment.

    History is sorted by timestamp when timestamps are strings in ISO-8601
    format. This starter implementation does not perform statistical
    time-series correlation.
    """
    valid = [record for record in records if isinstance(record, dict)]
    if not valid:
        return {
            "service_name": None,
            "is_anomalous": False,
            "anomaly_score": 0,
            "anomaly_count": 0,
            "reasons": [],
            "anomalies": [],
        }
    latest = sorted(valid, key=lambda row: str(row.get("timestamp", "")))[-1]
    return analyse_telemetry(latest, thresholds)
