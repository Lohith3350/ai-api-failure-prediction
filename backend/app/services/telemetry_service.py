"""Lohith/Kishor: define telemetry ingestion and retrieval interfaces here."""

def ingest_record(record: dict) -> dict:
    # TODO: validate and persist record.
    return {"accepted": True, "service_name": record.get("service_name")}
