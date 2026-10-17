
"""Tests for Parvathi's Decision Engine."""

import sys
from pathlib import Path

import pytest

# Make the backend app importable when pytest runs from the project root.
BACKEND_DIR = str(Path(__file__).resolve().parents[1])
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.services.decision_service import (
    classify_risk,
    make_decision,
    recommend_actions,
)


@pytest.mark.parametrize(
    ("probability", "expected"),
    [
        (0.0, "LOW"),
        (0.29, "LOW"),
        (0.30, "MEDIUM"),
        (0.59, "MEDIUM"),
        (0.60, "HIGH"),
        (0.84, "HIGH"),
        (0.85, "CRITICAL"),
        (1.0, "CRITICAL"),
    ],
)
def test_classify_risk_boundaries(probability, expected):
    assert classify_risk(probability) == expected


@pytest.mark.parametrize("probability", [-0.01, 1.01, -1, 2, True, "0.9", None])
def test_rejects_invalid_probability(probability):
    with pytest.raises(ValueError):
        classify_risk(probability)


def test_custom_thresholds():
    thresholds = {"medium": 0.20, "high": 0.50, "critical": 0.80}

    assert classify_risk(0.25, thresholds) == "MEDIUM"
    assert classify_risk(0.55, thresholds) == "HIGH"
    assert classify_risk(0.85, thresholds) == "CRITICAL"


def test_rejects_invalid_threshold_order():
    thresholds = {"medium": 0.70, "high": 0.60, "critical": 0.85}

    with pytest.raises(ValueError):
        classify_risk(0.50, thresholds)


def test_rejects_unknown_threshold():
    with pytest.raises(ValueError):
        classify_risk(0.50, {"urgent": 0.90})


@pytest.mark.parametrize("risk_level", ["LOW", "MEDIUM", "HIGH", "CRITICAL"])
def test_recommendations_are_returned_for_each_risk(risk_level):
    actions = recommend_actions(risk_level)

    assert isinstance(actions, list)
    assert len(actions) > 0
    assert all(isinstance(action, str) for action in actions)


def test_critical_recommendations_require_operator_approval():
    actions = recommend_actions("CRITICAL")

    assert any("urgent alert" in action.lower() for action in actions)
    assert any("operator approval" in action.lower() for action in actions)


def test_probable_causes_are_included():
    actions = recommend_actions("HIGH", ["database latency"])

    assert any("database latency" in action for action in actions)


def test_rejects_unknown_risk_level():
    with pytest.raises(ValueError):
        recommend_actions("UNKNOWN")


def test_make_decision_returns_expected_structure():
    result = make_decision(
        "payment-api",
        0.91,
        ["database latency"],
    )

    assert result["service_name"] == "payment-api"
    assert result["failure_probability"] == 0.91
    assert result["risk_level"] == "CRITICAL"
    assert result["recommendations"]
    assert result["automatic_action_executed"] is False
    assert any(
        "database latency" in action
        for action in result["recommendations"]
    )


def test_make_decision_rejects_blank_service_name():
    with pytest.raises(ValueError):
        make_decision("  ", 0.50)
