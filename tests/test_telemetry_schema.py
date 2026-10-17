import csv
import unittest
from datetime import datetime
from pathlib import Path

from backend.app.schemas import TelemetryRecord

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "raw" / "telemetry.csv"


class TestTelemetrySchema(unittest.TestCase):
    def test_telemetry_schema(self):
        with CSV_PATH.open(newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            self.assertEqual(
                set(reader.fieldnames),
                set(TelemetryRecord.model_fields.keys()),
            )
            rows = list(reader)

        self.assertGreater(len(rows), 0)

        for row in rows:
            record_data = {
                key: (None if value == "" else value)
                for key, value in row.items()
            }
            record = TelemetryRecord(**record_data)

            datetime.fromisoformat(record.timestamp)
            self.assertGreaterEqual(record.response_time_ms, 0)
            self.assertGreaterEqual(record.request_count, 1)
            self.assertGreaterEqual(record.error_rate, 0)
            self.assertLessEqual(record.error_rate, 1)
            self.assertGreaterEqual(record.http_5xx_count, 0)
            self.assertGreaterEqual(record.timeout_count, 0)

            for value in (
                record.cpu_usage_pct,
                record.memory_usage_pct,
            ):
                if value is not None:
                    self.assertGreaterEqual(value, 0)
                    self.assertLessEqual(value, 100)

            if record.dependency_latency_ms is not None:
                self.assertGreaterEqual(
                    record.dependency_latency_ms, 0
                )


if __name__ == "__main__":
    unittest.main()
