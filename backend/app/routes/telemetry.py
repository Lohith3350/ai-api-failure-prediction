"""Telemetry API routes."""

from fastapi import APIRouter, Query
from typing import Optional, List, Dict, Any
from backend.app.schemas import TelemetryRecord
from backend.app.services.telemetry_service import (
    ingest_record,
    get_recent_telemetry,
    get_latest_records,
)
from backend.app.services.prediction_service import process_telemetry_window

router = APIRouter(prefix="/telemetry", tags=["telemetry"])


@router.post("")
@router.post("/")
def ingest(record: TelemetryRecord):
    """Ingest a single telemetry record and trigger streaming inference evaluation."""
    ingest_record(record.model_dump())
    # Immediately evaluate streaming inference for the arriving service
    process_telemetry_window([record.model_dump()])
    return {"accepted": True, "service_name": record.service_name}


@router.post("/batch")
def ingest_batch(records: List[TelemetryRecord]):
    """Ingest a batch of telemetry records and evaluate inference."""
    raw_dicts = [r.model_dump() for r in records]
    for r in raw_dicts:
        ingest_record(r)
    process_telemetry_window(raw_dicts)
    return {"accepted": True, "count": len(records)}


@router.get("/recent")
def recent_telemetry(
    service_name: Optional[str] = Query(None, description="Optional service name filter (or 'all')"),
    limit: int = Query(40, ge=5, le=200, description="Number of points to return"),
):
    """Retrieve historical telemetry data points for charting."""
    records = get_recent_telemetry(service_name=service_name, limit=limit)
    return {"records": records, "count": len(records)}


@router.get("/latest")
def latest_telemetry():
    """Retrieve current latest telemetry metrics per service."""
    return {"services": get_latest_records()}
