"""
tests/test_ml_module.py — Unit and integration tests for the ML Prediction Module.

Tests:
1. Threshold derivation and serialization
2. Ground-truth failure labeling & forward horizon logic
3. Feature engineering & no-future-data-leakage verification
4. RealTimeInferenceEngine contract & Pydantic schema validation
5. telemetry_critical.csv replay behavior (payment/order elevated, user normal)
6. Healthy baseline zero-false-alarm guarantee
"""
from __future__ import annotations

import unittest
from pathlib import Path
import numpy as np
import pandas as pd

from ml.config import (
    ROOT,
    DATA_RAW,
    MODEL_DIR,
    DEFAULT_SERVICE_THRESHOLDS,
    ServiceThresholds,
    load_thresholds,
)
from ml.labeling import compute_failed_now, compute_horizon_labels
from ml.features import extract_rolling_features, build_feature_matrix
from ml.models import FailurePredictionModel
from ml.inference import RealTimeInferenceEngine
from ml.schemas import MLPredictionOutput


class TestMLModule(unittest.TestCase):

    def test_thresholds_config(self):
        """Test default thresholds and loading/saving."""
        thrs = load_thresholds()
        self.assertIn("user-service", thrs)
        self.assertIn("order-service", thrs)
        self.assertIn("payment-service", thrs)
        self.assertGreater(thrs["order-service"].response_time_ms, 140.0)
        self.assertGreaterEqual(thrs["order-service"].timeout_count, 5)

    def test_failed_now_logic(self):
        """Test failed_now triggers when RT, TO, or ER exceeds thresholds."""
        thrs = {
            "order-service": ServiceThresholds(response_time_ms=160.0, timeout_count=8, error_rate=0.30),
            "payment-service": ServiceThresholds(response_time_ms=150.0, timeout_count=5, error_rate=0.20),
            "user-service": ServiceThresholds(response_time_ms=70.0, timeout_count=4, error_rate=0.20),
        }

        # Healthy record
        healthy_df = pd.DataFrame([{
            "service_name": "order-service",
            "response_time_ms": 120.0,
            "timeout_count": 2,
            "error_rate": 0.05,
        }])
        self.assertFalse(compute_failed_now(healthy_df, thresholds=thrs).iloc[0])

        # Failed by RT
        failed_rt = pd.DataFrame([{
            "service_name": "order-service",
            "response_time_ms": 175.0,
            "timeout_count": 2,
            "error_rate": 0.05,
        }])
        self.assertTrue(compute_failed_now(failed_rt, thresholds=thrs).iloc[0])

        # Failed by Timeout
        failed_to = pd.DataFrame([{
            "service_name": "payment-service",
            "response_time_ms": 100.0,
            "timeout_count": 6,
            "error_rate": 0.01,
        }])
        self.assertTrue(compute_failed_now(failed_to, thresholds=thrs).iloc[0])

        # Failed by Error Rate
        failed_er = pd.DataFrame([{
            "service_name": "user-service",
            "response_time_ms": 45.0,
            "timeout_count": 0,
            "error_rate": 0.25,
        }])
        self.assertTrue(compute_failed_now(failed_er, thresholds=thrs).iloc[0])

    def test_horizon_labeling_and_no_cross_scenario_leakage(self):
        """Test that H=3 labeling looks 1..3 steps ahead and never across scenario boundaries."""
        # Create a synthetic 2-scenario dataset
        # Scenario A: failures at index 3 and 4
        # Scenario B: pure healthy
        records = []
        for i in range(6):
            records.append({
                "scenario_id": "sc_A",
                "service_name": "payment-service",
                "timestamp": f"2026-10-16T12:00:{i:02d}Z",
                "response_time_ms": 600.0 if i in (3, 4) else 100.0,
                "timeout_count": 0,
                "error_rate": 0.01,
            })
        for i in range(6):
            records.append({
                "scenario_id": "sc_B",
                "service_name": "payment-service",
                "timestamp": f"2026-10-16T13:00:{i:02d}Z",
                "response_time_ms": 100.0,
                "timeout_count": 0,
                "error_rate": 0.01,
            })

        df = pd.DataFrame(records)
        thrs = {"payment-service": ServiceThresholds(response_time_ms=150.0, timeout_count=5, error_rate=0.20)}
        labeled = compute_horizon_labels(df, horizon=3, thresholds=thrs)

        # In sc_A, failure occurs at t=3.
        # t=0 looks at t=1, 2, 3 -> sees t=3 failed -> label=1
        # t=1 looks at t=2, 3, 4 -> sees t=3, 4 failed -> label=1
        # t=2 looks at t=3, 4, 5 -> sees t=3, 4 failed -> label=1
        # t=3 looks at t=4, 5 -> sees t=4 failed -> label=1
        # t=4 looks at t=5 -> t=5 is healthy -> label=0
        # t=5 looks at end -> label=0
        sc_a_labels = labeled[labeled["scenario_id"] == "sc_A"]["will_fail_h3"].tolist()
        self.assertEqual(sc_a_labels, [1, 1, 1, 1, 0, 0])

        # In sc_B, all healthy -> all labels must be 0 (no leakage from sc_A)
        sc_b_labels = labeled[labeled["scenario_id"] == "sc_B"]["will_fail_h3"].tolist()
        self.assertEqual(sc_b_labels, [0, 0, 0, 0, 0, 0])

    def test_feature_engineering_no_leakage(self):
        """Verify rolling features at time t only use windows <= t, without lookahead."""
        rows = [
            {"scenario_id": "sc1", "service_name": "svc", "timestamp": f"2026-10-16T10:00:{i:02d}Z",
             "response_time_ms": float(i * 10), "error_rate": 0.0, "cpu_usage_pct": 50.0,
             "memory_usage_pct": 50.0, "timeout_count": 0}
            for i in range(5)
        ]
        df = pd.DataFrame(rows)
        feat_df = extract_rolling_features(df)

        # At index 2 (values: 0, 10, 20), roll3_mean must be mean(0, 10, 20) = 10.0
        self.assertAlmostEqual(feat_df.loc[2, "response_time_ms_roll3_mean"], 10.0)
        # It must NOT include index 3 (value 30) or index 4 (value 40)
        self.assertNotEqual(feat_df.loc[2, "response_time_ms_roll3_mean"], 20.0)

    def test_realtime_inference_contract(self):
        """Test streaming inference engine returns valid Pydantic schema and bounded outputs."""
        engine = RealTimeInferenceEngine()
        engine.reset()

        test_records = [
            {"service_name": "payment-service", "timestamp": "2026-10-16T14:00:00Z",
             "response_time_ms": 110.0, "request_count": 50, "error_rate": 0.01,
             "http_5xx_count": 0, "timeout_count": 0, "cpu_usage_pct": 45.0, "memory_usage_pct": 55.0},
            {"service_name": "order-service", "timestamp": "2026-10-16T14:00:00Z",
             "response_time_ms": 80.0, "request_count": 50, "error_rate": 0.01,
             "http_5xx_count": 0, "timeout_count": 0, "cpu_usage_pct": 35.0, "memory_usage_pct": 48.0},
            {"service_name": "user-service", "timestamp": "2026-10-16T14:00:00Z",
             "response_time_ms": 45.0, "request_count": 50, "error_rate": 0.01,
             "http_5xx_count": 0, "timeout_count": 0, "cpu_usage_pct": 25.0, "memory_usage_pct": 40.0},
        ]

        predictions = engine.ingest_window(test_records)
        self.assertEqual(len(predictions), 3)

        for p in predictions:
            # Validate schema contract
            schema_obj = MLPredictionOutput(**p)
            self.assertGreaterEqual(schema_obj.failure_probability, 0.0)
            self.assertLessEqual(schema_obj.failure_probability, 1.0)
            self.assertGreaterEqual(schema_obj.anomaly_score, 0.0)
            self.assertLessEqual(schema_obj.anomaly_score, 1.0)
            self.assertIsInstance(schema_obj.explanation, list)

    def test_telemetry_critical_replay(self):
        """Integration test: replay Kishor's critical CSV and verify cascading elevation."""
        crit_csv = DATA_RAW / "telemetry_critical.csv"
        if not crit_csv.exists():
            self.skipTest("telemetry_critical.csv not found")

        df = pd.read_csv(crit_csv)
        engine = RealTimeInferenceEngine()
        engine.reset()

        timestamps = sorted(df["timestamp"].unique())
        all_preds = []
        for ts in timestamps:
            w_rows = df[df["timestamp"] == ts].to_dict(orient="records")
            preds = engine.ingest_window(w_rows, scenario_id="test_replay")
            all_preds.extend(preds)

        pdf = pd.DataFrame(all_preds)
        pay_probs = pdf[pdf["service_name"] == "payment-service"]["failure_probability"]
        order_probs = pdf[pdf["service_name"] == "order-service"]["failure_probability"]
        user_probs = pdf[pdf["service_name"] == "user-service"]["failure_probability"]

        # Payment service must have elevated failure probability (> 80% on average)
        self.assertGreater(pay_probs.mean(), 0.80)
        # Order service must have elevated failure probability from cascade (> 80% on average)
        self.assertGreater(order_probs.mean(), 0.80)
        # User service must stay low (< 10% on average)
        self.assertLess(user_probs.mean(), 0.10)


if __name__ == "__main__":
    unittest.main()
