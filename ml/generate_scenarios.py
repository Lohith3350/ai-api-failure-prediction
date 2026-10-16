"""
generate_scenarios.py — Multi-scenario synthetic data generator.

Imports and calls the existing simulator functions from simulator/ to produce
varied fault profiles with ramp-ups, recoveries, and false alarms.
Output is clearly labeled as self-generated synthetic data.

Usage:
    python -m ml.generate_scenarios [--output data/raw/telemetry_scenarios.csv]
"""
import sys
import math
import csv
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean
from typing import List, Dict, Any, Optional

# ---------------------------------------------------------------------------
# Import the existing simulator logic
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from simulator.telemetry_collector import TelemetryCollector

# Constants from the existing simulator (kept in sync)
SERVICES = {
    "user-service": {"latency": 45, "cpu": 25, "memory": 40},
    "order-service": {"latency": 80, "cpu": 35, "memory": 48},
    "payment-service": {"latency": 110, "cpu": 45, "memory": 55},
}

MODES = {
    "normal":   {"latency": 1.0, "failure": 0.01, "timeout": 0.005},
    "degraded": {"latency": 2.5, "failure": 0.12, "timeout": 0.08},
    "critical": {"latency": 5.0, "failure": 0.35, "timeout": 0.25},
}


def _simulate_request(service: str, mode_settings: dict, rng: random.Random,
                      payment_state: Optional[dict] = None) -> dict:
    """
    Simulate one request using mode_settings dict (allows interpolated modes).
    This mirrors simulator.run_simulation.simulate_request but accepts a
    continuous settings dict instead of a mode name, so we can produce ramps.
    """
    config = SERVICES[service]
    multiplier = mode_settings["latency"]

    latency = rng.lognormvariate(
        math.log(config["latency"] * multiplier),
        0.35 if multiplier <= 1.2 else 0.65,
    )

    failure_probability = mode_settings["failure"]
    timeout_probability = mode_settings["timeout"]
    dependency_latency = None

    if service == "order-service" and payment_state is not None:
        payment_latency = payment_state["mean_latency_ms"]
        payment_failure_rate = payment_state["failure_rate"]
        latency_inflation = max(
            0.0, payment_latency / SERVICES["payment-service"]["latency"] - 1.0
        )
        cascade_probability = min(
            0.75,
            0.02 + 0.80 * payment_failure_rate + 0.08 * latency_inflation,
        )
        failure_probability = min(0.95, failure_probability + cascade_probability)
        timeout_probability = min(0.95, timeout_probability + 0.50 * cascade_probability)
        latency += 0.35 * payment_latency
        dependency_latency = payment_latency

    failed = rng.random() < failure_probability
    timed_out = rng.random() < timeout_probability
    cpu = min(99.0, config["cpu"] * multiplier + rng.uniform(-5, 8))
    memory = min(99.0, config["memory"] + (multiplier - 1) * 8 + rng.uniform(-3, 5))

    return {
        "response_time_ms": latency,
        "status_code": 503 if failed else 200,
        "timed_out": timed_out,
        "cpu_usage_pct": max(0.0, cpu),
        "memory_usage_pct": max(0.0, memory),
        "dependency_latency_ms": dependency_latency,
    }


def _interpolate_mode(mode_a: str, mode_b: str, t: float) -> dict:
    """Linearly interpolate between two mode settings dicts. t in [0, 1]."""
    a, b = MODES[mode_a], MODES[mode_b]
    return {k: a[k] + t * (b[k] - a[k]) for k in a}


# ---------------------------------------------------------------------------
# Scenario definitions
# ---------------------------------------------------------------------------
# Each scenario is a function that returns a list of mode_settings dicts,
# one per window, for payment-service. Other services derive from this.

def _latency_ramp(n_windows: int) -> List[dict]:
    """Gradual ramp from normal → degraded → critical over all windows."""
    result = []
    for i in range(n_windows):
        t = i / max(1, n_windows - 1)  # 0..1
        if t <= 0.5:
            settings = _interpolate_mode("normal", "degraded", t * 2)
        else:
            settings = _interpolate_mode("degraded", "critical", (t - 0.5) * 2)
        result.append(settings)
    return result


def _db_overload(n_windows: int) -> List[dict]:
    """Normal for first 40%, then sharp jump to critical (DB overload)."""
    result = []
    ramp_start = int(n_windows * 0.4)
    ramp_end = int(n_windows * 0.55)
    for i in range(n_windows):
        if i < ramp_start:
            result.append(MODES["normal"].copy())
        elif i < ramp_end:
            t = (i - ramp_start) / max(1, ramp_end - ramp_start)
            result.append(_interpolate_mode("normal", "critical", t))
        else:
            result.append(MODES["critical"].copy())
    return result


def _memory_leak(n_windows: int) -> List[dict]:
    """Very slow ramp (simulates memory leak) — stays in degraded territory."""
    result = []
    for i in range(n_windows):
        t = min(1.0, i / max(1, n_windows - 1))
        settings = _interpolate_mode("normal", "degraded", t)
        # Memory leak: extra memory pressure
        settings["_memory_bonus"] = t * 20  # up to +20% memory
        result.append(settings)
    return result


def _error_burst(n_windows: int) -> List[dict]:
    """Normal, then a sudden error spike for 5 windows, then back to normal."""
    result = []
    burst_start = int(n_windows * 0.4)
    burst_end = burst_start + 5
    for i in range(n_windows):
        if burst_start <= i < burst_end:
            result.append(MODES["critical"].copy())
        else:
            result.append(MODES["normal"].copy())
    return result


def _recovery(n_windows: int) -> List[dict]:
    """Start degraded, gradually recover to normal (no failure)."""
    result = []
    for i in range(n_windows):
        t = i / max(1, n_windows - 1)
        result.append(_interpolate_mode("degraded", "normal", t))
    return result


def _false_alarm(n_windows: int) -> List[dict]:
    """Spike to degraded for 2-3 windows then back to normal (should NOT be failure)."""
    result = []
    spike_start = int(n_windows * 0.3)
    spike_end = spike_start + 3
    for i in range(n_windows):
        if spike_start <= i < spike_end:
            result.append(_interpolate_mode("normal", "degraded", 0.7))
        else:
            result.append(MODES["normal"].copy())
    return result


def _healthy_baseline(n_windows: int) -> List[dict]:
    """Pure normal — control scenario."""
    return [MODES["normal"].copy() for _ in range(n_windows)]


SCENARIO_DEFS = {
    "latency_ramp": _latency_ramp,
    "db_overload": _db_overload,
    "memory_leak": _memory_leak,
    "error_burst": _error_burst,
    "recovery": _recovery,
    "false_alarm": _false_alarm,
    "healthy_baseline": _healthy_baseline,
}


def run_scenario(
    scenario_id: str,
    fault_type: str,
    n_windows: int,
    n_requests: int,
    seed: int,
) -> List[Dict[str, Any]]:
    """Run one scenario, return a list of telemetry record dicts with metadata columns."""
    rng = random.Random(seed)
    collector = TelemetryCollector()
    mode_schedule = SCENARIO_DEFS[fault_type](n_windows)

    all_records: List[Dict[str, Any]] = []
    start = datetime(2026, 10, 16, 14, 0, 0, tzinfo=timezone.utc)

    for window_idx in range(n_windows):
        timestamp = (start + timedelta(seconds=window_idx * 10)).isoformat()
        mode_settings = mode_schedule[window_idx]

        # Simulate payment-service with the scheduled mode
        payment_requests = [
            _simulate_request("payment-service", mode_settings, rng)
            for _ in range(n_requests)
        ]

        # Apply memory_leak bonus if present
        mem_bonus = mode_settings.get("_memory_bonus", 0)
        if mem_bonus:
            for r in payment_requests:
                r["memory_usage_pct"] = min(99.0, r["memory_usage_pct"] + mem_bonus)

        payment_failure_rate = mean(
            r["status_code"] >= 500 or r["timed_out"] for r in payment_requests
        )
        payment_mean_latency = mean(
            r["response_time_ms"] for r in payment_requests
        )
        payment_state = {
            "failure_rate": payment_failure_rate,
            "mean_latency_ms": payment_mean_latency,
        }

        # user-service is always normal
        user_requests = [
            _simulate_request("user-service", MODES["normal"], rng)
            for _ in range(n_requests)
        ]

        # order-service depends on payment state (cascade)
        order_requests = [
            _simulate_request("order-service", MODES["normal"], rng,
                              payment_state=payment_state)
            for _ in range(n_requests)
        ]

        for service, observations in (
            ("user-service", user_requests),
            ("order-service", order_requests),
            ("payment-service", payment_requests),
        ):
            for obs in observations:
                collector.record_request(service_name=service, **obs)

        window_records = collector.collect_window(timestamp)

        # Add metadata columns
        for rec in window_records:
            rec["scenario_id"] = scenario_id
            rec["fault_type"] = fault_type
            rec["data_source"] = "synthetic_generated"

        all_records.extend(window_records)

    return all_records


def generate_all_scenarios(
    n_windows: int = 120,
    n_requests: int = 50,
    base_seed: int = 42,
    seeds_per_fault: int = 3,
) -> List[Dict[str, Any]]:
    """
    Generate a multi-scenario dataset.

    Each fault type is run with `seeds_per_fault` different random seeds
    to get variability. Returns all records combined.
    """
    all_records: List[Dict[str, Any]] = []
    scenario_counter = 0

    for fault_type in SCENARIO_DEFS:
        for seed_offset in range(seeds_per_fault):
            seed = base_seed + scenario_counter * 1000 + seed_offset
            scenario_id = f"{fault_type}_{seed_offset:02d}"
            records = run_scenario(
                scenario_id=scenario_id,
                fault_type=fault_type,
                n_windows=n_windows,
                n_requests=n_requests,
                seed=seed,
            )
            all_records.extend(records)
            print(f"  Generated scenario {scenario_id}: {len(records)} rows (seed={seed})")
        scenario_counter += 1

    return all_records


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate multi-scenario synthetic telemetry data."
    )
    parser.add_argument(
        "--output", type=str,
        default=str(ROOT / "data" / "raw" / "telemetry_scenarios.csv"),
        help="Output CSV path",
    )
    parser.add_argument("--windows", type=int, default=120,
                        help="Windows per scenario (default: 120)")
    parser.add_argument("--requests", type=int, default=50,
                        help="Requests per window per service (default: 50)")
    parser.add_argument("--base-seed", type=int, default=42)
    parser.add_argument("--seeds-per-fault", type=int, default=3,
                        help="Number of random seed variants per fault type (default: 3)")
    args = parser.parse_args()

    print(f"Generating scenarios: {list(SCENARIO_DEFS.keys())}")
    print(f"  {args.seeds_per_fault} seeds each, {args.windows} windows, "
          f"{args.requests} requests/window\n")

    records = generate_all_scenarios(
        n_windows=args.windows,
        n_requests=args.requests,
        base_seed=args.base_seed,
        seeds_per_fault=args.seeds_per_fault,
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Deterministic column order
    columns = [
        "timestamp", "service_name", "response_time_ms", "request_count",
        "error_rate", "http_5xx_count", "timeout_count", "cpu_usage_pct",
        "memory_usage_pct", "dependency_latency_ms",
        "scenario_id", "fault_type", "data_source",
    ]

    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)

    total_scenarios = len(set(r["scenario_id"] for r in records))
    print(f"\nDone. {len(records)} rows across {total_scenarios} scenarios")
    print(f"Output: {output_path}")


if __name__ == "__main__":
    main()
