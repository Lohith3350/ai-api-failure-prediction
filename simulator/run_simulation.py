import argparse
import csv
import json
import math
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

from simulator.telemetry_collector import TelemetryCollector


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "data" / "raw"

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


def simulate_request(service, mode, rng):
    config = SERVICES[service]
    settings = MODES[mode]
    multiplier = settings["latency"]

    response_time = rng.lognormvariate(
        math.log(config["latency"] * multiplier),
        0.35 if mode == "normal" else 0.65,
    )

    failed = rng.random() < settings["failure"]
    timed_out = rng.random() < settings["timeout"]

    # Dependency latency is simulated; user-service has no dependency.
    dependency_latency = (
        rng.uniform(5, 25) * multiplier
        if service != "user-service"
        else None
    )

    return {
        "response_time_ms": response_time,
        "status_code": 503 if failed else 200,
        "timed_out": timed_out,
        "cpu_usage_pct": min(
            99.0, config["cpu"] * multiplier + rng.uniform(-5, 8)
        ),
        "memory_usage_pct": min(
            99.0, config["memory"] + (multiplier - 1) * 8
            + rng.uniform(-3, 5)
        ),
        "dependency_latency_ms": dependency_latency,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Generate synthetic API telemetry."
    )
    parser.add_argument(
        "--mode",
        choices=["normal", "degraded", "critical", "mixed"],
        default="mixed",
    )
    parser.add_argument("--windows", type=int, default=30)
    parser.add_argument("--requests", type=int, default=50)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    if args.windows < 1 or args.requests < 1:
        parser.error("--windows and --requests must be positive")

    rng = random.Random(args.seed)
    collector = TelemetryCollector()
    records = []
    start = datetime.now(timezone.utc).replace(microsecond=0)

    for window in range(args.windows):
        if args.mode == "mixed":
            mode = ["normal", "degraded", "critical"][window % 3]
        else:
            mode = args.mode

        timestamp = (
            start + timedelta(seconds=window * 10)
        ).isoformat()

        for service in SERVICES:
            for _ in range(args.requests):
                collector.record_request(
                    service_name=service,
                    **simulate_request(service, mode, rng),
                )

        records.extend(collector.collect_window(timestamp))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    csv_path = OUTPUT_DIR / "telemetry.csv"
    jsonl_path = OUTPUT_DIR / "telemetry.jsonl"

    with csv_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(records)

    with jsonl_path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record) + "\n")

    print(f"Mode: {args.mode}")
    print(f"Generated {len(records)} telemetry rows")
    print(f"Simulated requests: {len(records) * args.requests}")
    print(f"CSV: {csv_path}")
    print(f"JSONL: {jsonl_path}")


if __name__ == "__main__":
    main()
