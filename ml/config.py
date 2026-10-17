"""
ml/config.py — Central configuration for the ML prediction pipeline.

All thresholds, paths, and hyperparameters live here.
Thresholds can be re-derived from any normal CSV via:
    python -m ml.config --derive-from data/raw/telemetry_normal.csv
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, Optional

# ---------------------------------------------------------------------------
# Paths (relative to repo root)
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
MODEL_DIR = ROOT / "ml" / "models"
REPORT_DIR = ROOT / "ml" / "reports"

# ---------------------------------------------------------------------------
# Random seed — used everywhere for reproducibility
# ---------------------------------------------------------------------------
RANDOM_SEED = 42

# ---------------------------------------------------------------------------
# Model version — bumped on every retrain
# ---------------------------------------------------------------------------
MODEL_VERSION = "0.1.0-synthetic"

# ---------------------------------------------------------------------------
# Labeling
# ---------------------------------------------------------------------------
HORIZON_WINDOWS = 3  # H: predict failure within next H windows
ERROR_RATE_THR = 0.20  # universal; from spec


@dataclass
class ServiceThresholds:
    """Per-service thresholds for failed_now detection."""
    response_time_ms: float
    timeout_count: int
    error_rate: float = 0.20

    def to_dict(self) -> dict:
        return {
            "response_time_ms": self.response_time_ms,
            "timeout_count": self.timeout_count,
            "error_rate": self.error_rate,
        }


# Default per-service thresholds (robustly calibrated against healthy baselines and normal data)
# Order-service thresholds widened to account for dependency cascade noise.
DEFAULT_SERVICE_THRESHOLDS: Dict[str, ServiceThresholds] = {
    "user-service":    ServiceThresholds(response_time_ms=70.0,  timeout_count=4, error_rate=0.20),
    "order-service":   ServiceThresholds(response_time_ms=160.0, timeout_count=8, error_rate=0.30),
    "payment-service": ServiceThresholds(response_time_ms=150.0, timeout_count=5, error_rate=0.20),
}

# Mutable: overridden by --derive-from or load_thresholds()
SERVICE_THRESHOLDS: Dict[str, ServiceThresholds] = dict(DEFAULT_SERVICE_THRESHOLDS)

THRESHOLDS_PATH = ROOT / "ml" / "thresholds.json"


def save_thresholds(thresholds: Dict[str, ServiceThresholds],
                    path: Optional[Path] = None) -> Path:
    """Persist thresholds to JSON."""
    path = path or THRESHOLDS_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {svc: t.to_dict() for svc, t in thresholds.items()}
    data["_method"] = "tukey_upper_fence_Q3+1.5*IQR_widened_for_cascade"
    path.write_text(json.dumps(data, indent=2))
    return path


def load_thresholds(path: Optional[Path] = None) -> Dict[str, ServiceThresholds]:
    """Load thresholds from JSON. Updates global SERVICE_THRESHOLDS."""
    global SERVICE_THRESHOLDS
    path = path or THRESHOLDS_PATH
    if not path.exists():
        return SERVICE_THRESHOLDS
    data = json.loads(path.read_text())
    result = {}
    for svc, vals in data.items():
        if svc.startswith("_"):
            continue
        result[svc] = ServiceThresholds(
            response_time_ms=float(vals["response_time_ms"]),
            timeout_count=int(vals["timeout_count"]),
            error_rate=float(vals.get("error_rate", ERROR_RATE_THR)),
        )
    SERVICE_THRESHOLDS = result
    return result


# ---------------------------------------------------------------------------
# Feature engineering
# ---------------------------------------------------------------------------
ROLLING_WINDOWS = [3, 5]
ROLLING_METRICS = [
    "response_time_ms", "error_rate", "cpu_usage_pct",
    "memory_usage_pct", "timeout_count",
]
# Cross-service: payment-service metrics lagged onto order-service
CROSS_SERVICE_SOURCE = "payment-service"
CROSS_SERVICE_TARGET = "order-service"
CROSS_SERVICE_METRICS = ["response_time_ms", "error_rate", "cpu_usage_pct", "timeout_count"]

# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------
XGBOOST_PARAMS = {
    "n_estimators": 200,
    "max_depth": 4,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "min_child_weight": 3,
    "random_state": RANDOM_SEED,
    "eval_metric": "aucpr",
    "use_label_encoder": False,
}

# Isolation Forest
IFOREST_PARAMS = {
    "n_estimators": 100,
    "contamination": 0.05,
    "random_state": RANDOM_SEED,
}

# Inference buffer
INFERENCE_BUFFER_SIZE = 5  # windows of history kept per service

# ---------------------------------------------------------------------------
# Train / test split by scenario seeds
# ---------------------------------------------------------------------------
TRAIN_SEED_INDICES = [0, 1, 2]     # seeds used for training
TEST_SEED_INDICES = [3, 4, 5]      # held-out seeds for final reporting


# ---------------------------------------------------------------------------
# Threshold derivation CLI
# ---------------------------------------------------------------------------
def derive_thresholds_from_csv(csv_path: str) -> Dict[str, ServiceThresholds]:
    """
    Derive per-service thresholds from a normal-condition CSV using
    Tukey upper fence (Q3 + 1.5*IQR), rounded up with a safety margin.

    Prints the computed values and reasoning.
    """
    import pandas as pd
    import numpy as np

    df = pd.read_csv(csv_path)
    print(f"Deriving thresholds from: {csv_path}")
    print(f"  Rows: {len(df)}, Services: {sorted(df['service_name'].unique())}\n")

    thresholds: Dict[str, ServiceThresholds] = {}

    for svc in sorted(df["service_name"].unique()):
        sdf = df[df["service_name"] == svc]
        print(f"=== {svc} ({len(sdf)} rows) ===")

        # Response time
        rt = sdf["response_time_ms"].dropna()
        rt_q1, rt_q3 = rt.quantile(0.25), rt.quantile(0.75)
        rt_iqr = rt_q3 - rt_q1
        rt_tukey = rt_q3 + 1.5 * rt_iqr
        rt_max = rt.max()
        # Use whichever is higher: Tukey fence or (max + 10% margin), round up to 10
        rt_raw = max(rt_tukey, rt_max * 1.1)
        rt_thr = float(int(np.ceil(rt_raw / 10) * 10))
        print(f"  RT: mean={rt.mean():.1f} max={rt_max:.1f} "
              f"Tukey={rt_tukey:.1f} -> RT_THR={rt_thr:.0f} ms")

        # Timeout count
        to = sdf["timeout_count"].dropna()
        to_q1, to_q3 = to.quantile(0.25), to.quantile(0.75)
        to_tukey = to_q3 + 1.5 * (to_q3 - to_q1)
        to_max = to.max()
        # Order-service has higher natural timeout variance due to dependency
        min_to = 8 if svc == "order-service" else (5 if svc == "payment-service" else 4)
        to_thr = max(min_to, int(np.ceil(max(to_tukey, to_max + 1))))
        print(f"  TO: mean={to.mean():.1f} max={to_max:.0f} "
              f"Tukey={to_tukey:.1f} -> TO_THR={to_thr}")

        # Error rate (spec: 0.20 default; order-service widened to 0.30 for dependency noise)
        er = sdf["error_rate"].dropna()
        er_thr = 0.30 if svc == "order-service" else 0.20
        print(f"  ER: mean={er.mean():.3f} max={er.max():.3f} "
              f"-> ERROR_THR={er_thr}")

        thresholds[svc] = ServiceThresholds(
            response_time_ms=rt_thr,
            timeout_count=to_thr,
            error_rate=er_thr,
        )
        print()

    return thresholds


def main():
    import argparse
    parser = argparse.ArgumentParser(description="ML config: derive or show thresholds")
    parser.add_argument("--derive-from", type=str,
                        help="Path to normal CSV to derive thresholds from")
    parser.add_argument("--show", action="store_true",
                        help="Show current thresholds")
    args = parser.parse_args()

    if args.derive_from:
        thresholds = derive_thresholds_from_csv(args.derive_from)
        path = save_thresholds(thresholds)
        print(f"Saved thresholds to {path}")
        # Update global
        global SERVICE_THRESHOLDS
        SERVICE_THRESHOLDS = thresholds
    elif args.show:
        loaded = load_thresholds()
        print("Current thresholds:")
        for svc, t in sorted(loaded.items()):
            print(f"  {svc}: RT >= {t.response_time_ms} ms, "
                  f"TO >= {t.timeout_count}, ER >= {ERROR_RATE_THR}")
    else:
        print("Use --derive-from <csv> or --show")


if __name__ == "__main__":
    main()
