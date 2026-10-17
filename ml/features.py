"""
ml/features.py — Feature engineering for real-time failure prediction.

Features generated:
1. Base metrics: response_time_ms, error_rate, cpu_usage_pct, memory_usage_pct, timeout_count
2. Rolling statistics (W=3, W=5): mean, std, max, delta, trend (slope)
3. Cross-service cascade features: payment-service metrics aligned by timestamp and scenario
4. Service one-hot indicators
"""
from __future__ import annotations

import pandas as pd
import numpy as np
from typing import List, Tuple, Optional, Dict
from ml.config import (
    ROLLING_WINDOWS,
    ROLLING_METRICS,
    CROSS_SERVICE_SOURCE,
    CROSS_SERVICE_METRICS,
)

BASE_METRIC_COLS = [
    "response_time_ms",
    "error_rate",
    "cpu_usage_pct",
    "memory_usage_pct",
    "timeout_count",
    "http_5xx_count",
]


def _compute_slope(series: np.ndarray) -> float:
    """Compute simple linear regression slope over small window."""
    n = len(series)
    if n < 2:
        return 0.0
    x = np.arange(n)
    cov = np.cov(x, series, bias=True)[0, 1]
    var_x = np.var(x)
    return float(cov / var_x) if var_x > 1e-8 else 0.0


def extract_rolling_features(group: pd.DataFrame) -> pd.DataFrame:
    """
    Extract rolling features within a single (scenario_id, service_name) group,
    preserving chronological order.
    """
    group = group.copy().sort_values("timestamp").reset_index(drop=True)
    
    for metric in ROLLING_METRICS:
        if metric not in group.columns:
            continue
        vals = group[metric].values

        for w in ROLLING_WINDOWS:
            # Rolling mean
            roll_mean = group[metric].rolling(window=w, min_periods=1).mean()
            group[f"{metric}_roll{w}_mean"] = roll_mean

            # Rolling std
            roll_std = group[metric].rolling(window=w, min_periods=1).std().fillna(0.0)
            group[f"{metric}_roll{w}_std"] = roll_std

            # Rolling max
            roll_max = group[metric].rolling(window=w, min_periods=1).max()
            group[f"{metric}_roll{w}_max"] = roll_max

            # Delta: current minus mean of past w
            group[f"{metric}_roll{w}_delta"] = group[metric] - roll_mean

            # Trend/slope over window w
            slopes = []
            for i in range(len(vals)):
                start = max(0, i - w + 1)
                slopes.append(_compute_slope(vals[start : i + 1]))
            group[f"{metric}_roll{w}_slope"] = slopes

    return group


def add_cross_service_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add payment-service metrics onto order-service and other services within
    the same scenario_id and timestamp.
    """
    df = df.copy()

    # Extract payment service rows as lookup
    payment_df = df[df["service_name"] == CROSS_SERVICE_SOURCE][
        ["scenario_id", "timestamp"] + CROSS_SERVICE_METRICS
    ].copy()

    # Rename columns to avoid collisions
    rename_map = {m: f"dep_payment_{m}" for m in CROSS_SERVICE_METRICS}
    payment_df = payment_df.rename(columns=rename_map)

    # Merge on scenario_id and timestamp
    merged = pd.merge(
        df,
        payment_df,
        on=["scenario_id", "timestamp"],
        how="left",
    )

    # Fill NaNs for any unaligned rows
    for m in CROSS_SERVICE_METRICS:
        col = f"dep_payment_{m}"
        if col in merged.columns:
            merged[col] = merged[col].fillna(0.0)

    # Add interaction features
    # 1. order to payment latency ratio
    if "dep_payment_response_time_ms" in merged.columns:
        merged["rt_to_payment_rt_ratio"] = (
            merged["response_time_ms"] / (merged["dep_payment_response_time_ms"] + 1e-3)
        )
    # 2. payment degradation indicator (is payment latency > 140 or cpu > 70)
    if "dep_payment_response_time_ms" in merged.columns:
        merged["dep_payment_is_elevated"] = (
            (merged["dep_payment_response_time_ms"] >= 140.0)
            | (merged.get("dep_payment_cpu_usage_pct", 0) >= 70.0)
        ).astype(float)

    return merged


def build_feature_matrix(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """
    Full feature pipeline on a DataFrame.
    Returns (featured_df, feature_names_list).
    """
    # 1. Rolling features per (scenario_id, service_name)
    processed_groups = []
    for _, group in df.groupby(["scenario_id", "service_name"], sort=False):
        processed_groups.append(extract_rolling_features(group))

    featured_df = pd.concat(processed_groups, ignore_index=True)

    # 2. Cross-service dependency features
    featured_df = add_cross_service_features(featured_df)

    # 3. Service one-hot encoding
    for svc in ["order-service", "payment-service", "user-service"]:
        featured_df[f"svc_{svc.replace('-', '_')}"] = (featured_df["service_name"] == svc).astype(float)

    # Exclude metadata and target columns from feature list
    non_feature_cols = {
        "timestamp",
        "service_name",
        "scenario_id",
        "fault_type",
        "data_source",
        "failed_now",
        "will_fail_h3",
        "will_fail_h1",
        "will_fail_h2",
        "will_fail_h5",
    }
    feature_cols = [c for c in featured_df.columns if c not in non_feature_cols]

    return featured_df, feature_cols


if __name__ == "__main__":
    from ml.config import DATA_RAW
    from ml.labeling import compute_horizon_labels
    scenarios_csv = DATA_RAW / "telemetry_scenarios.csv"
    if scenarios_csv.exists():
        df = pd.read_csv(scenarios_csv)
        labeled = compute_horizon_labels(df)
        feat_df, cols = build_feature_matrix(labeled)
        print(f"Built feature matrix: {feat_df.shape[0]} rows, {len(cols)} features")
        print("Sample features:", cols[:10])
