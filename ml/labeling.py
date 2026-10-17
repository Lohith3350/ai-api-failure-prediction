"""
ml/labeling.py — Ground-truth failure labeling with horizon H.

Per-service failure definition:
    failed_now = (response_time_ms >= RT_THR) or
                 (timeout_count >= TO_THR) or
                 (error_rate >= ERROR_RATE_THR)

Prediction target:
    will_fail_h3 = 1 if service fails in any window in (t, t + H] within same scenario
                   0 otherwise
"""
from __future__ import annotations

import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional
from ml.config import (
    SERVICE_THRESHOLDS,
    ERROR_RATE_THR,
    HORIZON_WINDOWS,
    ServiceThresholds,
    load_thresholds,
)


def compute_failed_now(
    df: pd.DataFrame,
    thresholds: Optional[Dict[str, ServiceThresholds]] = None,
) -> pd.Series:
    """
    Compute boolean failed_now for each row based on its service_name thresholds.
    """
    if thresholds is None:
        thresholds = load_thresholds()

    failed = pd.Series(False, index=df.index)

    for svc, t in thresholds.items():
        svc_mask = df["service_name"] == svc
        if not svc_mask.any():
            continue

        svc_failed = (
            (df.loc[svc_mask, "response_time_ms"] >= t.response_time_ms)
            | (df.loc[svc_mask, "timeout_count"] >= t.timeout_count)
            | (df.loc[svc_mask, "error_rate"] >= getattr(t, "error_rate", ERROR_RATE_THR))
        )
        failed.loc[svc_mask] = svc_failed

    return failed


def compute_horizon_labels(
    df: pd.DataFrame,
    horizon: int = HORIZON_WINDOWS,
    thresholds: Optional[Dict[str, ServiceThresholds]] = None,
) -> pd.DataFrame:
    """
    Assign failed_now and will_fail_h{horizon} to df.
    Maintains group boundaries by (scenario_id, service_name).
    """
    df = df.copy()
    df["failed_now"] = compute_failed_now(df, thresholds)

    # Sort to ensure chronological order within group
    if "timestamp" in df.columns:
        df = df.sort_values(["scenario_id", "service_name", "timestamp"]).reset_index(drop=True)

    target_col = f"will_fail_h{horizon}"
    df[target_col] = 0

    # For each (scenario, service), look forward 1..H steps
    for (scenario_id, svc), group_idx in df.groupby(["scenario_id", "service_name"]).groups.items():
        group_failed = df.loc[group_idx, "failed_now"].values
        n = len(group_failed)
        labels = np.zeros(n, dtype=int)
        for i in range(n):
            # Check windows (i + 1) to min(n, i + 1 + horizon)
            forward_window = group_failed[i + 1 : min(n, i + 1 + horizon)]
            if len(forward_window) > 0 and forward_window.any():
                labels[i] = 1
        df.loc[group_idx, target_col] = labels

    return df


def validate_labels(
    df: pd.DataFrame,
    thresholds: Optional[Dict[str, ServiceThresholds]] = None,
) -> dict:
    """
    Run validation checks:
    1. failed_now rate for every scenario/seed (healthy_baseline and normal must be 0%).
    2. positive-label rate per fault type.
    3. Flag any scenario with zero positives.
    4. Check max response times in healthy baseline vs thresholds.
    """
    labeled_df = compute_horizon_labels(df, thresholds=thresholds)

    # 1. failed_now per scenario
    scenario_stats = []
    zero_positive_scenarios = []

    for sc_id, group in labeled_df.groupby("scenario_id"):
        fault = group["fault_type"].iloc[0] if "fault_type" in group.columns else "unknown"
        fn_count = group["failed_now"].sum()
        fn_rate = group["failed_now"].mean()
        pos_count = group[f"will_fail_h{HORIZON_WINDOWS}"].sum()
        pos_rate = group[f"will_fail_h{HORIZON_WINDOWS}"].mean()

        scenario_stats.append({
            "scenario_id": sc_id,
            "fault_type": fault,
            "rows": len(group),
            "failed_now_count": int(fn_count),
            "failed_now_rate": float(fn_rate),
            "positives_h3": int(pos_count),
            "pos_rate_h3": float(pos_rate),
        })

        # Fault scenarios that should have failures but have zero positives:
        if fault not in ("healthy_baseline", "recovery", "false_alarm") and pos_count == 0:
            zero_positive_scenarios.append(sc_id)

    # 2. per fault type aggregation
    stats_df = pd.DataFrame(scenario_stats)
    fault_summary = stats_df.groupby("fault_type").agg(
        scenarios=("scenario_id", "count"),
        total_rows=("rows", "sum"),
        failed_now_rate=("failed_now_rate", "mean"),
        pos_rate_h3=("pos_rate_h3", "mean"),
        total_positives=("positives_h3", "sum"),
    ).reset_index()

    # 3. Healthy baseline check
    hb_df = labeled_df[labeled_df["fault_type"] == "healthy_baseline"]
    hb_max_rt = {}
    if len(hb_df) > 0:
        for svc in hb_df["service_name"].unique():
            hb_max_rt[svc] = float(hb_df[hb_df["service_name"] == svc]["response_time_ms"].max())

    return {
        "scenario_stats": stats_df,
        "fault_summary": fault_summary,
        "zero_positive_scenarios": zero_positive_scenarios,
        "hb_max_rt": hb_max_rt,
        "labeled_df": labeled_df,
    }


if __name__ == "__main__":
    from ml.config import DATA_RAW
    scenarios_csv = DATA_RAW / "telemetry_scenarios.csv"
    if scenarios_csv.exists():
        df = pd.read_csv(scenarios_csv)
        results = validate_labels(df)
        print("=== Fault Type Labeling Summary ===")
        print(results["fault_summary"].to_string(index=False))
        if results["zero_positive_scenarios"]:
            print(f"\n[WARNING] Scenarios with ZERO positives: {results['zero_positive_scenarios']}")
        else:
            print("\n[OK] All fault scenarios have positive failure labels.")
        print("\n=== Healthy Baseline Max RT vs Current Thresholds ===")
        current_thrs = load_thresholds()
        for svc, max_rt in results["hb_max_rt"].items():
            thr = current_thrs[svc].response_time_ms
            status = "OK" if max_rt < thr else "ALERT: EXCEEDED"
            print(f"  {svc}: max={max_rt:.1f} ms, threshold={thr:.1f} ms -> {status}")
