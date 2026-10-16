"""Shared request/response schemas. Keep contracts stable across modules."""

from pydantic import BaseModel
from typing import Optional, List

class TelemetryRecord(BaseModel):
    timestamp: str
    service_name: str
    response_time_ms: float
    request_count: int = 0
    error_rate: float = 0.0
    http_5xx_count: int = 0
    timeout_count: int = 0
    cpu_usage_pct: Optional[float] = None
    memory_usage_pct: Optional[float] = None
    dependency_latency_ms: Optional[float] = None

class PredictionResponse(BaseModel):
    service_name: str
    failure_probability: float
    risk_level: str
    reasons: List[str] = []
    recommended_actions: List[str] = []
