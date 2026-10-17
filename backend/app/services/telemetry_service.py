"""Telemetry ingestion, storage, and retrieval service."""

from __future__ import annotations
import csv
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
import collections

# Path to initial synthetic normal telemetry
PROJECT_ROOT = Path(__file__).resolve().parents[3]
NORMAL_CSV = PROJECT_ROOT / "data" / "raw" / "telemetry_normal.csv"
CRITICAL_CSV = PROJECT_ROOT / "data" / "raw" / "telemetry_critical.csv"

# Global in-memory ring buffer (per service)
_SERVICE_HISTORY: Dict[str, collections.deque] = collections.defaultdict(
    lambda: collections.deque(maxlen=100)
)
_INITIALIZED = False


def _parse_row(row: Dict[str, str]) -> Dict[str, Any]:
    def _float(val, default=0.0):
        try:
            return float(val) if val not in (None, "") else default
        except (ValueError, TypeError):
            return default

    def _int(val, default=0):
        try:
            return int(float(val)) if val not in (None, "") else default
        except (ValueError, TypeError):
            return default

    return {
        "timestamp": row.get("timestamp", datetime.now(timezone.utc).isoformat()),
        "service_name": row.get("service_name", "unknown-service"),
        "response_time_ms": _float(row.get("response_time_ms"), 50.0),
        "request_count": _int(row.get("request_count"), 50),
        "error_rate": _float(row.get("error_rate"), 0.0),
        "http_5xx_count": _int(row.get("http_5xx_count"), 0),
        "timeout_count": _int(row.get("timeout_count"), 0),
        "cpu_usage_pct": _float(row.get("cpu_usage_pct"), 30.0),
        "memory_usage_pct": _float(row.get("memory_usage_pct"), 45.0),
        "dependency_latency_ms": _float(row.get("dependency_latency_ms"), 0.0),
    }


def seed_default_data() -> None:
    """Pre-load baseline telemetry so the dashboard displays live charts immediately."""
    global _INITIALIZED
    if _INITIALIZED:
        return

    csv_path = NORMAL_CSV if NORMAL_CSV.exists() else None
    if csv_path and csv_path.exists():
        with open(csv_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = [_parse_row(r) for r in reader]
            # Take up to the last 40 rows per service
            for r in rows:
                _SERVICE_HISTORY[r["service_name"]].append(r)
    else:
        # Fallback synthetic seed
        now = datetime.now(timezone.utc)
        services = [
            ("user-service", 45.0, 25.0, 40.0, 0.0),
            ("order-service", 80.0, 35.0, 48.0, 110.0),
            ("payment-service", 110.0, 45.0, 55.0, 0.0),
        ]
        for step in range(20, 0, -1):
            ts = (now - timedelta(seconds=step * 10)).isoformat()
            for svc, rt, cpu, mem, dep in services:
                _SERVICE_HISTORY[svc].append({
                    "timestamp": ts,
                    "service_name": svc,
                    "response_time_ms": rt + (step % 5) * 1.5,
                    "request_count": 50,
                    "error_rate": 0.005,
                    "http_5xx_count": 0,
                    "timeout_count": 0,
                    "cpu_usage_pct": cpu + (step % 3) * 1.0,
                    "memory_usage_pct": mem,
                    "dependency_latency_ms": dep,
                })

    _INITIALIZED = True


def ingest_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """Ingest a single telemetry record and store it in the ring buffer."""
    seed_default_data()
    svc = record.get("service_name", "unknown")
    parsed = _parse_row(record)
    _SERVICE_HISTORY[svc].append(parsed)
    return {"accepted": True, "service_name": svc, "record": parsed}


def ingest_batch(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Ingest a window/batch of records across services."""
    seed_default_data()
    results = []
    for r in records:
        results.append(ingest_record(r))
    return results


def get_recent_telemetry(service_name: Optional[str] = None, limit: int = 30) -> List[Dict[str, Any]]:
    """Retrieve recent telemetry records sorted by timestamp."""
    seed_default_data()
    if service_name and service_name != "all":
        return list(_SERVICE_HISTORY.get(service_name, []))[-limit:]

    # Combine all services and sort by timestamp
    all_records = []
    for svc, records in _SERVICE_HISTORY.items():
        all_records.extend(list(records)[-limit:])
    all_records.sort(key=lambda r: r.get("timestamp", ""))
    return all_records


def get_latest_records() -> Dict[str, Dict[str, Any]]:
    """Return the single most recent record for each monitored service."""
    seed_default_data()
    latest = {}
    for svc, records in _SERVICE_HISTORY.items():
        if records:
            latest[svc] = records[-1]
    return latest


def reset_telemetry():
    """Reset ring buffers and re-seed clean normal telemetry."""
    global _INITIALIZED
    _SERVICE_HISTORY.clear()
    _INITIALIZED = False
    seed_default_data()
