"""Parvathi: map risk and context to safe recommendations."""

def recommend_actions(risk_level: str, probable_causes: list | None = None) -> list:
    # TODO: recommendations only by default; do not execute infrastructure changes.
    if risk_level == "CRITICAL":
        return ["Notify the service owner", "Review scaling or traffic-rerouting options"]
    if risk_level == "HIGH":
        return ["Alert the service owner", "Increase monitoring"]
    if risk_level == "MEDIUM":
        return ["Issue a warning", "Continue monitoring"]
    return ["Continue monitoring"]
