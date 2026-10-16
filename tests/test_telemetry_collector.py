
import unittest

from simulator.telemetry_collector import TelemetryCollector


class TestTelemetryCollector(unittest.TestCase):

    def setUp(self):
        self.collector = TelemetryCollector()

    def test_aggregates_request_metrics(self):
        self.collector.record_request(
            service_name="payment-service",
            response_time_ms=100,
            status_code=200,
            timed_out=False,
            cpu_usage_pct=30,
            memory_usage_pct=40,
            dependency_latency_ms=50,
        )

        self.collector.record_request(
            service_name="payment-service",
            response_time_ms=300,
            status_code=503,
            timed_out=True,
            cpu_usage_pct=50,
            memory_usage_pct=60,
            dependency_latency_ms=150,
        )

        records = self.collector.collect_window(
            "2026-10-16T12:00:00+00:00"
        )

        self.assertEqual(len(records), 1)
        record = records[0]

        self.assertEqual(record["service_name"], "payment-service")
        self.assertEqual(record["request_count"], 2)
        self.assertEqual(record["response_time_ms"], 200.0)
        self.assertEqual(record["http_5xx_count"], 1)
        self.assertEqual(record["timeout_count"], 1)
        self.assertEqual(record["error_rate"], 0.5)
        self.assertEqual(record["cpu_usage_pct"], 40.0)
        self.assertEqual(record["memory_usage_pct"], 50.0)
        self.assertEqual(record["dependency_latency_ms"], 100.0)

    def test_timeout_counts_as_error_without_5xx(self):
        self.collector.record_request(
            service_name="user-service",
            response_time_ms=500,
            status_code=200,
            timed_out=True,
        )

        record = self.collector.collect_window()[0]

        self.assertEqual(record["error_rate"], 1.0)
        self.assertEqual(record["http_5xx_count"], 0)
        self.assertEqual(record["timeout_count"], 1)

    def test_cpu_and_memory_are_bounded(self):
        self.collector.record_request(
            service_name="order-service",
            response_time_ms=100,
            cpu_usage_pct=-10,
            memory_usage_pct=150,
        )

        record = self.collector.collect_window()[0]

        self.assertEqual(record["cpu_usage_pct"], 0.0)
        self.assertEqual(record["memory_usage_pct"], 100.0)

    def test_collection_window_resets_requests(self):
        self.collector.record_request(
            service_name="user-service",
            response_time_ms=100,
        )

        first_window = self.collector.collect_window()
        second_window = self.collector.collect_window()

        self.assertEqual(len(first_window), 1)
        self.assertEqual(first_window[0]["request_count"], 1)
        self.assertEqual(second_window, [])

    def test_services_are_aggregated_separately(self):
        self.collector.record_request(
            service_name="user-service",
            response_time_ms=100,
        )
        self.collector.record_request(
            service_name="payment-service",
            response_time_ms=300,
        )

        records = self.collector.collect_window()
        by_service = {r["service_name"]: r for r in records}

        self.assertEqual(by_service["user-service"]["request_count"], 1)
        self.assertEqual(by_service["payment-service"]["request_count"], 1)
        self.assertEqual(
            by_service["user-service"]["response_time_ms"], 100.0
        )
        self.assertEqual(
            by_service["payment-service"]["response_time_ms"], 300.0
        )


if __name__ == "__main__":
    unittest.main()
