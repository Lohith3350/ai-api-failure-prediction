"""
ml/schemas.py — Pydantic schemas for the ML Prediction Module interface.

Strict contract:
- Failure probability: float in [0.0, 1.0]
- Anomaly score: float in [0.0, 1.0]
- Explanations: top contributing features
- NO risk-level thresholds
"""
from __future__ import annotations

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class FeatureAttribution(BaseModel):
    """Single feature contribution attribution."""
    feature: str
    value: float
    model_importance: float


class MLPredictionOutput(BaseModel):
    """Output contract for ML failure prediction on a single service."""
    service_name: str
    timestamp: str
    failure_probability: float = Field(..., ge=0.0, le=1.0, description="P(failure in next H windows)")
    anomaly_score: float = Field(..., ge=0.0, le=1.0, description="Normalized unsupervised anomaly score")
    explanation: List[FeatureAttribution] = Field(default_factory=list, description="Top contributing features")
    model_version: Optional[str] = None


class BatchPredictionOutput(BaseModel):
    """Batch prediction response containing predictions across all services in a window."""
    timestamp: str
    predictions: List[MLPredictionOutput]
