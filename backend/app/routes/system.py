"""System topology, cluster overview, and simulation orchestration routes."""

from fastapi import APIRouter, Body
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import random

from backend.app.services.telemetry_service import (
    get_latest_records,
    get_recent_telemetry,
    ingest_record,
    reset_telemetry,
)
from backend.app.services.prediction_service import (
    get_all_predictions,
    process_telemetry_window,
    reset_predictions,
)
from backend.app.services.root_cause_service import get_cluster_diagnosis

router = APIRouter(prefix="/system", tags=["system"])
sim_router = APIRouter(prefix="/simulation", tags=["simulation"])

# Simulation step state
_SIM_INDEX = 0


@router.get("/overview")
def system_overview() -> Dict[str, Any]:
    """Retrieve cluster-wide key performance indicators."""
    latest = get_latest_records()
    preds = get_all_predictions()

    all_latencies = [r.get("response_time_ms", 0) for r in latest.values()]
    avg_latency = sum(all_latencies) / len(all_latencies) if all_latencies else 0.0

    max_prob = max([p.get("failure_probability", 0) for p in preds], default=0.0)
    critical_count = sum(1 for p in preds if p.get("risk_level") == "CRITICAL")
    warning_count = sum(1 for p in preds if p.get("risk_level") in ("MEDIUM", "HIGH"))

    diagnosis = get_cluster_diagnosis()

    return {
        "status": "CRITICAL" if critical_count > 0 else ("WARNING" if warning_count > 0 else "HEALTHY"),
        "total_services": len(latest) or 3,
        "healthy_count": len(preds) - (critical_count + warning_count),
        "warning_count": warning_count,
        "critical_count": critical_count,
        "average_cluster_latency_ms": round(avg_latency, 2),
        "peak_failure_probability": round(max_prob, 4),
        "primary_root_cause": diagnosis.get("primary_root_cause"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/topology")
def service_topology() -> Dict[str, Any]:
    """Return the architecture dependency graph with live health indicators."""
    latest = get_latest_records()
    preds = {p["service_name"]: p for p in get_all_predictions()}

    nodes = [
        {
            "id": "user-service",
            "name": "User Service",
            "role": "Edge Gateway",
            "port": 8081,
            "metrics": latest.get("user-service", {}),
            "prediction": preds.get("user-service", {}),
        },
        {
            "id": "order-service",
            "name": "Order Service",
            "role": "Core Business API",
            "port": 8082,
            "metrics": latest.get("order-service", {}),
            "prediction": preds.get("order-service", {}),
        },
        {
            "id": "payment-service",
            "name": "Payment Service",
            "role": "Downstream Settlement",
            "port": 8083,
            "metrics": latest.get("payment-service", {}),
            "prediction": preds.get("payment-service", {}),
        },
    ]

    edges = [
        {
            "source": "user-service",
            "target": "order-service",
            "label": "REST /orders",
            "latency_ms": latest.get("user-service", {}).get("response_time_ms", 45),
            "status": "HEALTHY",
        },
        {
            "source": "order-service",
            "target": "payment-service",
            "label": "gRPC /charge",
            "latency_ms": latest.get("order-service", {}).get("dependency_latency_ms", 110),
            "status": "DEGRADED" if latest.get("order-service", {}).get("dependency_latency_ms", 0) > 300 else "HEALTHY",
        },
    ]

    return {"nodes": nodes, "edges": edges}


@sim_router.post("/step")
def simulation_step(payload: Optional[Dict[str, Any]] = Body(None)) -> Dict[str, Any]:
    """Advance simulation by generating and ingesting the next 10-second telemetry window."""
    global _SIM_INDEX
    _SIM_INDEX += 1
    mode = (payload or {}).get("scenario", "normal")
    now_ts = datetime.now(timezone.utc).isoformat()

    rng = random.Random(_SIM_INDEX)

    if mode == "critical":
        # Severe cascading outage starting in payment-service
        pay_rt = rng.uniform(550.0, 780.0)
        pay_cpu = rng.uniform(94.0, 99.5)
        pay_err = rng.uniform(0.40, 0.65)
        pay_to = rng.randint(10, 22)

        ord_dep = pay_rt + rng.uniform(-30, 40)
        ord_rt = rng.uniform(310.0, 450.0)
        ord_err = rng.uniform(0.75, 0.95)
        ord_to = rng.randint(15, 30)

        usr_rt = rng.uniform(48.0, 68.0)
        usr_err = rng.uniform(0.02, 0.08)

    elif mode == "degraded":
        # Moderate degradation
        pay_rt = rng.uniform(220.0, 320.0)
        pay_cpu = rng.uniform(75.0, 88.0)
        pay_err = rng.uniform(0.15, 0.28)
        pay_to = rng.randint(4, 9)

        ord_dep = pay_rt
        ord_rt = rng.uniform(160.0, 220.0)
        ord_err = rng.uniform(0.20, 0.40)
        ord_to = rng.randint(4, 10)

        usr_rt = rng.uniform(46.0, 55.0)
        usr_err = 0.01

    elif mode == "spike":
        # Sudden traffic burst
        pay_rt = rng.uniform(140.0, 190.0)
        pay_cpu = rng.uniform(70.0, 85.0)
        pay_err = 0.04
        pay_to = 2

        ord_dep = pay_rt
        ord_rt = rng.uniform(110.0, 150.0)
        ord_err = 0.05
        ord_to = 3

        usr_rt = rng.uniform(55.0, 75.0)
        usr_err = 0.02

    else:
        # Pristine normal traffic
        pay_rt = rng.uniform(95.0, 125.0)
        pay_cpu = rng.uniform(35.0, 50.0)
        pay_err = 0.005
        pay_to = 0

        ord_dep = pay_rt
        ord_rt = rng.uniform(70.0, 90.0)
        ord_err = 0.005
        ord_to = 0

        usr_rt = rng.uniform(40.0, 50.0)
        usr_err = 0.001

    window = [
        {
            "timestamp": now_ts,
            "service_name": "user-service",
            "response_time_ms": round(usr_rt, 2),
            "request_count": 50,
            "error_rate": round(usr_err, 4),
            "http_5xx_count": int(usr_err * 50),
            "timeout_count": 0,
            "cpu_usage_pct": round(rng.uniform(22.0, 30.0), 2),
            "memory_usage_pct": round(rng.uniform(38.0, 43.0), 2),
            "dependency_latency_ms": 0.0,
        },
        {
            "timestamp": now_ts,
            "service_name": "order-service",
            "response_time_ms": round(ord_rt, 2),
            "request_count": 50,
            "error_rate": round(ord_err, 4),
            "http_5xx_count": int(ord_err * 50),
            "timeout_count": ord_to,
            "cpu_usage_pct": round(rng.uniform(32.0, 42.0), 2),
            "memory_usage_pct": round(rng.uniform(46.0, 52.0), 2),
            "dependency_latency_ms": round(ord_dep, 2),
        },
        {
            "timestamp": now_ts,
            "service_name": "payment-service",
            "response_time_ms": round(pay_rt, 2),
            "request_count": 50,
            "error_rate": round(pay_err, 4),
            "http_5xx_count": int(pay_err * 50),
            "timeout_count": pay_to,
            "cpu_usage_pct": round(pay_cpu, 2),
            "memory_usage_pct": round(rng.uniform(50.0, 88.0), 2),
            "dependency_latency_ms": 0.0,
        },
    ]

    for rec in window:
        ingest_record(rec)

    predictions = process_telemetry_window(window)

    return {
        "scenario": mode,
        "step_index": _SIM_INDEX,
        "timestamp": now_ts,
        "window_records": window,
        "predictions": predictions,
    }


@sim_router.post("/reset")
def simulation_reset() -> Dict[str, Any]:
    """Reset telemetry buffers and ML inference state back to initial nominal conditions."""
    global _SIM_INDEX
    _SIM_INDEX = 0
    reset_telemetry()
    reset_predictions()
    latest = get_latest_records()
    if latest:
        process_telemetry_window(list(latest.values()))
    return {"status": "ok", "message": "Cluster simulation reset to baseline"}
