from collections import defaultdict
from datetime import datetime, timezone
from statistics import mean


class TelemetryCollector:
    """Aggregate simulated request metrics per service."""

    def __init__(self):
        self.requests = defaultdict(list)

    def record_request(
        self,
        service_name,
        response_time_ms,
        status_code=200,
        timed_out=False,
        cpu_usage_pct=0.0,
        memory_usage_pct=0.0,
        dependency_latency_ms=None,
    ):
        self.requests[service_name].append({
            "response_time_ms": max(0.0, response_time_ms),
            "status_code": status_code,
            "timed_out": timed_out,
            "cpu_usage_pct": max(0.0, min(100.0, cpu_usage_pct)),
            "memory_usage_pct": max(0.0, min(100.0, memory_usage_pct)),
            "dependency_latency_ms": dependency_latency_ms,
        })

    def collect_window(self, timestamp=None):
        timestamp = timestamp or datetime.now(timezone.utc).isoformat()
        records = []

        for service_name, requests in self.requests.items():
            if not requests:
                continue

            count = len(requests)
            errors = sum(
                r["status_code"] >= 500 or r["timed_out"]
                for r in requests
            )
            server_errors = sum(r["status_code"] >= 500 for r in requests)
            timeouts = sum(r["timed_out"] for r in requests)

            dependency_values = [
                r["dependency_latency_ms"]
                for r in requests
                if r["dependency_latency_ms"] is not None
            ]

            records.append({
                "timestamp": timestamp,
                "service_name": service_name,
                "response_time_ms": round(
                    mean(r["response_time_ms"] for r in requests), 2
                ),
                "request_count": count,
                "error_rate": round(errors / count, 4),
                "http_5xx_count": server_errors,
                "timeout_count": timeouts,
                "cpu_usage_pct": round(
                    mean(r["cpu_usage_pct"] for r in requests), 2
                ),
                "memory_usage_pct": round(
                    mean(r["memory_usage_pct"] for r in requests), 2
                ),
                "dependency_latency_ms": (
                    round(mean(dependency_values), 2)
                    if dependency_values else None
                ),
            })

        self.requests.clear()
        return records
