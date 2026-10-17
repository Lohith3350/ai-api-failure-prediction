
import contextlib
import csv
import io
import sys
import tempfile
import unittest
from collections import defaultdict
from pathlib import Path
from unittest.mock import patch

import simulator.run_simulation as simulation


class TestCascadeSimulation(unittest.TestCase):

    def run_scenario(self, mode, output_dir):
        args = [
            "run_simulation",
            "--mode", mode,
            "--windows", "30",
            "--requests", "50",
            "--seed", "42",
        ]

        with (
            patch.object(simulation, "OUTPUT_DIR", Path(output_dir)),
            patch.object(sys, "argv", args),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            simulation.main()

        with (Path(output_dir) / "telemetry.csv").open(
            newline="", encoding="utf-8"
        ) as file:
            return list(csv.DictReader(file))

    def average_error_rates(self, records):
        grouped = defaultdict(list)

        for record in records:
            grouped[record["service_name"]].append(
                float(record["error_rate"])
            )

        return {
            service: sum(rates) / len(rates)
            for service, rates in grouped.items()
        }

    def test_critical_payment_causes_order_cascade(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            normal_dir = Path(temp_dir) / "normal"
            critical_dir = Path(temp_dir) / "critical"

            normal_dir.mkdir()
            critical_dir.mkdir()

            normal_records = self.run_scenario("normal", normal_dir)
            critical_records = self.run_scenario("critical", critical_dir)

        normal = self.average_error_rates(normal_records)
        critical = self.average_error_rates(critical_records)

        self.assertEqual(len(normal_records), 90)
        self.assertEqual(len(critical_records), 90)

        # Payment degradation should increase payment failures.
        self.assertGreater(
            critical["payment-service"],
            normal["payment-service"],
        )

        # Payment degradation should cascade to order-service.
        self.assertGreater(
            critical["order-service"],
            normal["order-service"],
        )

        # User-service is independent of payment in this simulation.
        self.assertAlmostEqual(
            critical["user-service"],
            normal["user-service"],
        )

        # Every generated error rate should be a valid fraction.
        for record in normal_records + critical_records:
            rate = float(record["error_rate"])
            self.assertGreaterEqual(rate, 0.0)
            self.assertLessEqual(rate, 1.0)


if __name__ == "__main__":
    unittest.main()
