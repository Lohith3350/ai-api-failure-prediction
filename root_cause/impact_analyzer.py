"""Estimate which dependent services may be affected by a service failure."""

from .config import DEFAULT_DEPENDENCIES
from .dependency_graph import get_dependents, normalise_dependency_graph


def find_affected_services(
    service_name: str,
    dependency_graph: dict | None = None,
    transitive: bool = True,
) -> list[str]:
    """Return dependent services that may be affected by this service."""
    graph = normalise_dependency_graph(
        dependency_graph if dependency_graph is not None else DEFAULT_DEPENDENCIES
    )
    return get_dependents(service_name, graph, transitive=transitive)
