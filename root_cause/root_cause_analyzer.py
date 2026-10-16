"""Rank probable root causes using dependency relationships and telemetry."""

from typing import Any
from .config import DEFAULT_DEPENDENCIES
from .dependency_graph import get_dependencies, normalise_dependency_graph
from .telemetry_analyzer import analyse_telemetry


def _records_by_service(telemetry: Any) -> dict[str, dict]:
    """Accept a record, a list of records, or a dict containing records/services."""
    by_service: dict[str, dict] = {}

    if isinstance(telemetry, list):
        for record in telemetry:
            if isinstance(record, dict) and record.get("service_name"):
                name = record["service_name"]
                previous = by_service.get(name)
                if previous is None or str(record.get("timestamp", "")) >= str(previous.get("timestamp", "")):
                    by_service[name] = record
        return by_service

    if not isinstance(telemetry, dict):
        return by_service

    records = telemetry.get("records")
    if isinstance(records, list):
        by_service.update(_records_by_service(records))

    services = telemetry.get("services")
    if isinstance(services, dict):
        for name, value in services.items():
            if isinstance(value, dict):
                by_service[name] = {**value, "service_name": name}
            elif isinstance(value, list):
                by_service.update(_records_by_service([
                    {**record, "service_name": name}
                    for record in value if isinstance(record, dict)
                ]))

    if telemetry.get("service_name"):
        by_service[telemetry["service_name"]] = telemetry

    return by_service


def analyze_probable_causes(
    service_name: str,
    telemetry: Any,
    dependency_graph: dict | None = None,
    thresholds: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    """Rank suspicious target/dependency services by telemetry evidence.

    Only the target and services it depends on are considered. The output is
    a heuristic ranking, not proof of causal responsibility.
    """
    records = _records_by_service(telemetry)
    graph_source = dependency_graph
    if graph_source is None and isinstance(telemetry, dict):
        graph_source = telemetry.get("dependency_graph")
    graph = normalise_dependency_graph(
        graph_source if graph_source is not None else DEFAULT_DEPENDENCIES
    )

    candidates = [service_name]
    candidates.extend(get_dependencies(service_name, graph, transitive=True))

    ranked: list[dict[str, Any]] = []
    for candidate in dict.fromkeys(candidates):
        record = records.get(candidate)
        if not record:
            continue
        assessment = analyse_telemetry(record, thresholds)
        if assessment["is_anomalous"]:
            ranked.append({
                "service_name": candidate,
                "anomaly_score": assessment["anomaly_score"],
                "anomaly_count": assessment["anomaly_count"],
                "reasons": assessment["reasons"],
            })

    ranked.sort(
        key=lambda item: (-item["anomaly_score"], -item["anomaly_count"], item["service_name"])
    )
    return ranked
