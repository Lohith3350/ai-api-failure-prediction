
"""Decision engine: classify API failure risk and recommend safe actions."""

from typing import Any, Mapping

DEFAULT_THRESHOLDS = {
    "medium": 0.30,
    "high": 0.60,
    "critical": 0.85,
}


def classify_risk(
    failure_probability: float,
    thresholds: Mapping[str, float] | None = None,
) -> str:
    """Convert a failure probability between 0 and 1 into a risk level."""
    if isinstance(failure_probability, bool) or not isinstance(
        failure_probability, (int, float)
    ):
        raise ValueError("failure_probability must be a number between 0 and 1")

    if not 0 <= failure_probability <= 1:
        raise ValueError("failure_probability must be between 0 and 1")

    limits = dict(DEFAULT_THRESHOLDS)
    if thresholds is not None:
        unknown = set(thresholds) - set(limits)
        if unknown:
            raise ValueError(f"Unknown threshold keys: {sorted(unknown)}")
        limits.update(thresholds)

    values = [limits["medium"], limits["high"], limits["critical"]]
    if any(
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not 0 <= value <= 1
        for value in values
    ):
        raise ValueError("Thresholds must be numbers between 0 and 1")

    if not limits["medium"] < limits["high"] < limits["critical"]:
        raise ValueError("Thresholds must satisfy medium < high < critical")

    if failure_probability >= limits["critical"]:
        return "CRITICAL"
    if failure_probability >= limits["high"]:
        return "HIGH"
    if failure_probability >= limits["medium"]:
        return "MEDIUM"
    return "LOW"


def recommend_actions(
    risk_level: str,
    probable_causes: list | None = None,
) -> list[str]:
    """Recommend next steps without executing infrastructure changes."""
    if not isinstance(risk_level, str):
        raise ValueError("risk_level must be a string")

    level = risk_level.strip().upper()

    actions_by_level = {
        "LOW": [
            "Continue routine monitoring",
            "Record the prediction for trend analysis",
        ],
        "MEDIUM": [
            "Issue a warning to the service owner",
            "Increase monitoring of error rates and latency",
            "Review recent telemetry for emerging anomalies",
        ],
        "HIGH": [
            "Alert the service owner",
            "Inspect logs, latency, error rates, and dependency health",
            "Prepare mitigation options and monitor closely",
        ],
        "CRITICAL": [
            "Send an urgent alert to the service owner or on-call team",
            "Investigate the affected service and its dependencies immediately",
            "Review scaling, failover, and traffic-rerouting options",
            "Require authorized operator approval before taking disruptive action",
        ],
    }

    if level not in actions_by_level:
        raise ValueError(
            "risk_level must be LOW, MEDIUM, HIGH, or CRITICAL"
        )

    actions = list(actions_by_level[level])

    if probable_causes:
        causes = [
            str(cause).strip()
            for cause in probable_causes
            if str(cause).strip()
        ]
        if causes:
            actions.append(
                "Investigate probable cause(s): " + ", ".join(causes)
            )

    return actions


def make_decision(
    service_name: str,
    failure_probability: float,
    probable_causes: list | None = None,
    thresholds: Mapping[str, float] | None = None,
) -> dict[str, Any]:
    """Return a structured risk assessment and recommended actions."""
    if not isinstance(service_name, str) or not service_name.strip():
        raise ValueError("service_name must be a non-empty string")

    risk_level = classify_risk(failure_probability, thresholds)
    actions = recommend_actions(risk_level, probable_causes)

    return {
        "service_name": service_name.strip(),
        "failure_probability": float(failure_probability),
        "risk_level": risk_level,
        "recommendations": actions,
        "automatic_action_executed": False,
    }
