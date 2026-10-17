"""Configurable initial thresholds for telemetry anomaly detection.

These are starter thresholds, not production-calibrated values. Tune them
against the simulator's normal and critical scenarios.
"""

THRESHOLDS = {
    "response_time_ms": 1000.0,
    "error_rate": 0.20,
    "http_5xx_count": 5,
    "timeout_count": 5,
    "cpu_usage_pct": 90.0,
    "memory_usage_pct": 90.0,
    "dependency_latency_ms": 500.0,
}

# Dependency convention: service -> services it calls/depends on.
# This graph is an initial example; update it to match the simulator.
DEFAULT_DEPENDENCIES = {
    "user-service": [],
    "order-service": ["payment-service"],
    "payment-service": [],
}

# Higher score means a stronger telemetry warning. The score is heuristic,
# not a statistically calibrated probability.
ANOMALY_WEIGHTS = {
    "response_time_ms": 1,
    "error_rate": 2,
    "http_5xx_count": 2,
    "timeout_count": 2,
    "cpu_usage_pct": 1,
    "memory_usage_pct": 1,
    "dependency_latency_ms": 1,
}
