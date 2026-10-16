"""
ml/inference.py — Real-time and batch inference engine.

Requirements:
- Predicts failure_probability (0.0 to 1.0)
- Predicts anomaly_score (0.0 to 1.0)
- Provides top-K feature attribution explanation
- Maintains in-memory buffer of last N windows for real-time streaming
- ZERO risk-level thresholds (delegated to decision engine)
"""
from __future__ import annotations

import collections
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from ml.config import (
    MODEL_DIR,
    INFERENCE_BUFFER_SIZE,
    CROSS_SERVICE_SOURCE,
    CROSS_SERVICE_METRICS,
)
from ml.models import FailurePredictionModel
from ml.features import extract_rolling_features, add_cross_service_features


class RealTimeInferenceEngine:
    """
    Streaming inference engine that maintains a rolling history buffer per service
    and produces failure predictions as new telemetry windows arrive.
    """

    def __init__(self, model_dir: Optional[Path] = None, buffer_size: int = INFERENCE_BUFFER_SIZE):
        self.model_dir = model_dir or MODEL_DIR
        self.model = FailurePredictionModel.load(self.model_dir)
        self.buffer_size = buffer_size
        # service_name -> deque of dict records
        self._buffer: Dict[str, collections.deque] = collections.defaultdict(
            lambda: collections.deque(maxlen=self.buffer_size)
        )
        # Store payment service history for cross-service dependency lookups
        self._payment_history: collections.deque = collections.deque(maxlen=self.buffer_size)

    def reset(self):
        """Clear all rolling buffers."""
        self._buffer.clear()
        self._payment_history.clear()

    def ingest_window(
        self,
        service_records: List[Dict[str, Any]],
        scenario_id: str = "live_stream",
    ) -> List[Dict[str, Any]]:
        """
        Process a window of telemetry records (one per active service).
        Returns prediction outputs for each service:
            {
                "service_name": str,
                "timestamp": str,
                "failure_probability": float,
                "anomaly_score": float,
                "explanation": list of top features,
            }
        """
        # 1. Update internal buffers
        for rec in service_records:
            svc = rec["service_name"]
            item = dict(rec)
            item["scenario_id"] = scenario_id
            self._buffer[svc].append(item)
            if svc == CROSS_SERVICE_SOURCE:
                self._payment_history.append(item)

        results = []

        # 2. For each service, construct feature vector from buffer and predict
        for rec in service_records:
            svc = rec["service_name"]
            history = list(self._buffer[svc])
            df_history = pd.DataFrame(history)

            # Compute rolling features on history
            feat_history = extract_rolling_features(df_history)
            latest_row = feat_history.iloc[[-1]].copy()

            # Add payment cross-service features from latest payment state
            latest_payment = self._payment_history[-1] if self._payment_history else None
            for m in CROSS_SERVICE_METRICS:
                col = f"dep_payment_{m}"
                val = latest_payment.get(m, 0.0) if latest_payment else 0.0
                latest_row[col] = float(val)

            # Interaction features
            pay_rt = float(latest_row["dep_payment_response_time_ms"].iloc[0]) if "dep_payment_response_time_ms" in latest_row else 0.0
            cur_rt = float(latest_row["response_time_ms"].iloc[0])
            pay_cpu = float(latest_row["dep_payment_cpu_usage_pct"].iloc[0]) if "dep_payment_cpu_usage_pct" in latest_row else 0.0
            latest_row["rt_to_payment_rt_ratio"] = float(cur_rt / (pay_rt + 1e-3))
            latest_row["dep_payment_is_elevated"] = float(pay_rt >= 140.0 or pay_cpu >= 70.0)

            # Service one-hot
            for s in ["order-service", "payment-service", "user-service"]:
                latest_row[f"svc_{s.replace('-', '_')}"] = float(svc == s)

            # Align columns to model's feature set
            for col in self.model.feature_names:
                if col not in latest_row.columns:
                    latest_row[col] = 0.0

            X = latest_row[self.model.feature_names]

            # Predictions
            fail_prob = float(self.model.predict_proba(X)[0])
            anom_score = float(self.model.score_anomaly(X)[0])
            explanation = self.model.explain_sample(latest_row.iloc[0], top_k=3)

            results.append({
                "service_name": svc,
                "timestamp": rec.get("timestamp", ""),
                "failure_probability": round(fail_prob, 4),
                "anomaly_score": round(anom_score, 4),
                "explanation": explanation,
            })

        return results
