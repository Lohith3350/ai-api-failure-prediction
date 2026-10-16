from fastapi import APIRouter
from backend.app.schemas import TelemetryRecord

router = APIRouter(prefix="/telemetry", tags=["telemetry"])

@router.post("/")
def ingest_telemetry(record: TelemetryRecord):
    # TODO: validate/store telemetry through the telemetry module.
    return {"accepted": True, "service_name": record.service_name}
