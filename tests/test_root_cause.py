
from root_cause.dependency_graph import (
    get_dependencies,
    get_dependents,
    normalise_dependency_graph,
)
from root_cause.telemetry_analyzer import analyse_telemetry


def test_high_error_rate_is_detected():
    telemetry = {
        "service_name": "payment-service",
        "error_rate": 0.5,
        "response_time_ms": 100,
        "http_5xx_count": 0,
        "timeout_count": 0,
        "cpu_usage_pct": 30,
        "memory_usage_pct": 40,
        "dependency_latency_ms": 50,
    }

    result = analyse_telemetry(telemetry)

    assert result["is_anomalous"] is True
    assert result["anomaly_score"] > 0
    assert any("error_rate" in reason for reason in result["reasons"])


def test_normal_telemetry_is_not_anomalous():
    telemetry = {
        "service_name": "payment-service",
        "error_rate": 0.01,
        "response_time_ms": 100,
        "http_5xx_count": 0,
        "timeout_count": 0,
        "cpu_usage_pct": 30,
        "memory_usage_pct": 40,
        "dependency_latency_ms": 50,
    }

    result = analyse_telemetry(telemetry)

    assert result["is_anomalous"] is False
    assert result["anomaly_score"] == 0


def test_get_dependencies():
    graph = {
        "checkout-service": ["order-service"],
        "order-service": ["payment-service"],
        "payment-service": [],
    }

    dependencies = get_dependencies("checkout-service", graph)

    assert "order-service" in dependencies
    assert "payment-service" in dependencies


def test_get_dependents():
    graph = {
        "checkout-service": ["order-service"],
        "order-service": ["payment-service"],
        "payment-service": [],
    }

    dependents = get_dependents("payment-service", graph)

    assert "order-service" in dependents
    assert "checkout-service" in dependents


def test_graph_includes_referenced_services():
    graph = {"order-service": ["payment-service"]}

    cleaned = normalise_dependency_graph(graph)

    assert "payment-service" in cleaned
    assert cleaned["payment-service"] == []
