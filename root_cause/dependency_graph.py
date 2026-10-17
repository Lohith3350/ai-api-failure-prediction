"""Dependency graph utilities.

Graph convention: ``service -> [dependencies]``.
If order-service calls payment-service, use:
    {"order-service": ["payment-service"], "payment-service": []}
"""

from collections import deque
from typing import Iterable


def normalise_dependency_graph(graph: dict | None) -> dict[str, list[str]]:
    """Return a clean graph with all referenced services represented."""
    cleaned: dict[str, list[str]] = {}
    if not isinstance(graph, dict):
        graph = {}

    for service, dependencies in graph.items():
        if not isinstance(service, str) or not service.strip():
            continue
        if isinstance(dependencies, (list, tuple, set)):
            cleaned[service] = sorted({
                dep for dep in dependencies
                if isinstance(dep, str) and dep.strip() and dep != service
            })
        else:
            cleaned[service] = []

    for dependencies in list(cleaned.values()):
        for dependency in dependencies:
            cleaned.setdefault(dependency, [])

    return cleaned


def get_dependencies(
    service_name: str,
    graph: dict[str, list[str]],
    transitive: bool = True,
) -> list[str]:
    """Return services that the requested service depends on."""
    graph = normalise_dependency_graph(graph)
    found: list[str] = []
    visited = {service_name}
    queue = deque(graph.get(service_name, []))

    while queue:
        current = queue.popleft()
        if current in visited:
            continue
        visited.add(current)
        found.append(current)
        if transitive:
            queue.extend(graph.get(current, []))

    return found


def get_dependents(
    service_name: str,
    graph: dict[str, list[str]],
    transitive: bool = True,
) -> list[str]:
    """Return services that depend on the requested service.

    This traverses the reverse of the stored graph, so it can estimate
    downstream services at risk if this service fails.
    """
    graph = normalise_dependency_graph(graph)
    reverse: dict[str, list[str]] = {name: [] for name in graph}
    for service, dependencies in graph.items():
        for dependency in dependencies:
            reverse.setdefault(dependency, []).append(service)

    found: list[str] = []
    visited = {service_name}
    queue = deque(sorted(reverse.get(service_name, [])))

    while queue:
        current = queue.popleft()
        if current in visited:
            continue
        visited.add(current)
        found.append(current)
        if transitive:
            queue.extend(sorted(reverse.get(current, [])))

    return found
