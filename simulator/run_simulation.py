import argparse
import csv
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean

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


def simulate_request(service, mode, rng, payment_state=None):
    """Simulate one request, optionally propagating payment problems to orders."""
    config = SERVICES[service]
    settings = MODES[mode]
    multiplier = settings["latency"]

    latency = rng.lognormvariate(
        __import__("math").log(config["latency"] * multiplier),
        0.35 if mode == "normal" else 0.65,
    )

    failure_probability = settings["failure"]
    timeout_probability = settings["timeout"]
    dependency_latency = None

    if service == "order-service" and payment_state is not None:
        payment_latency = payment_state["mean_latency_ms"]
        payment_failure_rate = payment_state["failure_rate"]

        # More payment latency and failures cause more order failures.
        latency_inflation = max(
            0.0, payment_latency / SERVICES["payment-service"]["latency"] - 1.0
        )
        cascade_probability = min(
            0.75,
            0.02 + 0.80 * payment_failure_rate
            + 0.08 * latency_inflation,
        )

        failure_probability = min(
            0.95, failure_probability + cascade_probability
        )
        timeout_probability = min(
            0.95,
            timeout_probability + 0.50 * cascade_probability,
        )

        # A slow payment dependency also increases order response time.
        latency += 0.35 * payment_latency
        dependency_latency = payment_latency

    failed = rng.random() < failure_probability
    timed_out = rng.random() < timeout_probability

    # These resource metrics are synthetic, not host measurements.
    cpu = min(
        99.0,
        config["cpu"] * multiplier + rng.uniform(-5, 8),
    )
    memory = min(
        99.0,
        config["memory"] + (multiplier - 1) * 8
        + rng.uniform(-3, 5),
    )

    return {
        "response_time_ms": latency,
        "status_code": 503 if failed else 200,
        "timed_out": timed_out,
        "cpu_usage_pct": max(0.0, cpu),
        "memory_usage_pct": max(0.0, memory),
        "dependency_latency_ms": dependency_latency,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Generate synthetic telemetry with cascading failures."
    )
    parser.add_argument(
        "--mode",
        choices=["normal", "degraded", "critical", "mixed"],
        default="mixed",
        help="Health condition of payment-service",
    )
    parser.add_argument("--windows", type=int, default=30)
    parser.add_argument("--requests", type=int, default=50)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    if args.windows < 1 or args.requests < 1:
        parser.error("--windows and --requests must be positive")

    rng = random.Random(args.seed)
    collector = TelemetryCollector()
    all_records = []
    start = datetime.now(timezone.utc).replace(microsecond=0)

    for window in range(args.windows):
        if args.mode == "mixed":
            payment_mode = ["normal", "degraded", "critical"][window % 3]
        else:
            payment_mode = args.mode

        timestamp = (
            start + timedelta(seconds=window * 10)
        ).isoformat()

        # Simulate payment first to estimate its condition for this window.
        payment_requests = [
            simulate_request("payment-service", payment_mode, rng)
            for _ in range(args.requests)
        ]

        payment_failure_rate = mean(
            r["status_code"] >= 500 or r["timed_out"]
            for r in payment_requests
        )
        payment_mean_latency = mean(
            r["response_time_ms"] for r in payment_requests
        )

        payment_state = {
            "failure_rate": payment_failure_rate,
            "mean_latency_ms": payment_mean_latency,
        }

        # User requests are independent of payment in this demo.
        user_requests = [
            simulate_request("user-service", "normal", rng)
            for _ in range(args.requests)
        ]

        # Order requests depend on the payment condition measured above.
        order_requests = [
            simulate_request(
                "order-service", "normal", rng, payment_state=payment_state
            )
            for _ in range(args.requests)
        ]

        for service, observations in (
            ("user-service", user_requests),
            ("order-service", order_requests),
            ("payment-service", payment_requests),
        ):
            for observation in observations:
                collector.record_request(
                    service_name=service, **observation
                )

        all_records.extend(collector.collect_window(timestamp))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = OUTPUT_DIR / "telemetry.csv"
    jsonl_path = OUTPUT_DIR / "telemetry.jsonl"

    with csv_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=all_records[0].keys())
        writer.writeheader()
        writer.writerows(all_records)

    with jsonl_path.open("w", encoding="utf-8") as file:
        for record in all_records:
            file.write(json.dumps(record) + "\n")

    print(f"Payment-service mode: {args.mode}")
    print(f"Generated {len(all_records)} telemetry rows")
    print(f"Simulated requests: {len(all_records) * args.requests}")
    print(f"CSV: {csv_path}")
    print(f"JSONL: {jsonl_path}")
    print("\nAverage metrics by service:")

    for service in SERVICES:
        service_rows = [
            r for r in all_records if r["service_name"] == service
        ]
        avg_latency = mean(r["response_time_ms"] for r in service_rows)
        avg_errors = mean(r["error_rate"] for r in service_rows)
        print(
            f"  {service}: avg_latency={avg_latency:.1f} ms, "
            f"avg_error_rate={avg_errors:.1%}"
        )


if __name__ == "__main__":
    main()
