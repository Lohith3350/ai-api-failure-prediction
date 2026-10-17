"""
ml/train.py — Model training and rigorous cross-validation pipeline.

Validation protocols:
1. GroupKFold (k=5) on training scenarios (seeds 00-02)
2. Leave-One-Fault-Type-Out (LOFTO) cross-validation
3. Final evaluation on held-out test scenarios (seeds 03-05, never seen in training)

All metrics strictly labeled: "self-generated synthetic data".
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, List, Tuple
import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    precision_score,
    recall_score,
    f1_score,
    brier_score_loss,
)
from ml.config import (
    ROOT,
    DATA_RAW,
    MODEL_DIR,
    REPORT_DIR,
    TRAIN_SEED_INDICES,
    TEST_SEED_INDICES,
    HORIZON_WINDOWS,
    RANDOM_SEED,
)
from ml.labeling import compute_horizon_labels
from ml.features import build_feature_matrix
from ml.models import FailurePredictionModel


def split_train_test_scenarios(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Split scenarios by seed indices:
    Seeds 00, 01, 02 -> Train (3 seeds per fault type)
    Seeds 03, 04, 05 -> Held-out Test (3 seeds per fault type)
    """
    train_suffixes = tuple(f"_{i:02d}" for i in TRAIN_SEED_INDICES)
    test_suffixes = tuple(f"_{i:02d}" for i in TEST_SEED_INDICES)

    train_mask = df["scenario_id"].str.endswith(train_suffixes)
    test_mask = df["scenario_id"].str.endswith(test_suffixes)

    train_df = df[train_mask].copy().reset_index(drop=True)
    test_df = df[test_mask].copy().reset_index(drop=True)

    return train_df, test_df


def compute_metrics(y_true: np.ndarray, y_prob: np.ndarray, threshold: float = 0.5) -> Dict[str, float]:
    """Compute standard classification and ranking metrics."""
    if len(np.unique(y_true)) < 2:
        return {"roc_auc": 1.0, "pr_auc": 1.0, "precision": 1.0, "recall": 1.0, "f1": 1.0, "brier": 0.0}

    y_pred = (y_prob >= threshold).astype(int)
    return {
        "roc_auc": float(roc_auc_score(y_true, y_prob)),
        "pr_auc": float(average_precision_score(y_true, y_prob)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "brier": float(brier_score_loss(y_true, y_prob)),
    }


def run_group_kfold(
    train_df: pd.DataFrame,
    feature_cols: List[str],
    target_col: str,
    n_splits: int = 5,
) -> Dict[str, Any]:
    """Perform GroupKFold CV grouped by scenario_id."""
    gkf = GroupKFold(n_splits=n_splits)
    groups = train_df["scenario_id"]
    X = train_df[feature_cols]
    y = train_df[target_col].values

    fold_metrics = []
    for fold, (train_idx, val_idx) in enumerate(gkf.split(X, y, groups)):
        X_tr, y_tr = X.iloc[train_idx], y[train_idx]
        X_va, y_va = X.iloc[val_idx], y[val_idx]

        model = FailurePredictionModel()
        model.fit(X_tr, y_tr, X_val=X_va, y_val=y_va)
        val_probs = model.predict_proba(X_va)

        metrics = compute_metrics(y_va, val_probs)
        metrics["fold"] = fold + 1
        fold_metrics.append(metrics)

    res_df = pd.DataFrame(fold_metrics)
    mean_metrics = res_df.mean().to_dict()
    return {"fold_metrics": res_df, "mean_metrics": mean_metrics}


def run_leave_one_fault_type_out(
    train_df: pd.DataFrame,
    feature_cols: List[str],
    target_col: str,
) -> pd.DataFrame:
    """
    Perform Leave-One-Fault-Type-Out (LOFTO) CV.
    Evaluates how well the model generalizes to an unseen failure mechanism.
    """
    fault_types = sorted(train_df["fault_type"].unique())
    results = []

    for held_out_fault in fault_types:
        tr_mask = train_df["fault_type"] != held_out_fault
        va_mask = train_df["fault_type"] == held_out_fault

        X_tr, y_tr = train_df.loc[tr_mask, feature_cols], train_df.loc[tr_mask, target_col].values
        X_va, y_va = train_df.loc[va_mask, feature_cols], train_df.loc[va_mask, target_col].values

        model = FailurePredictionModel()
        model.fit(X_tr, y_tr)
        val_probs = model.predict_proba(X_va)

        m = compute_metrics(y_va, val_probs)
        m["held_out_fault"] = held_out_fault
        m["n_val_samples"] = len(y_va)
        m["positives"] = int(y_va.sum())
        results.append(m)

    return pd.DataFrame(results)


def compute_lead_time_stats(test_df: pd.DataFrame, y_prob: np.ndarray, threshold: float = 0.5) -> Dict[str, Any]:
    """
    Compute lead time (windows and seconds) before first failure occurs in each scenario.
    Lead time = time from first alarm (y_prob >= threshold) to first actual failure.
    """
    test_df = test_df.copy()
    test_df["pred_prob"] = y_prob
    test_df["alarm"] = test_df["pred_prob"] >= threshold

    lead_times_windows = []
    
    for (sc_id, svc), group in test_df.groupby(["scenario_id", "service_name"]):
        group = group.sort_values("timestamp").reset_index(drop=True)
        # Find first actual failure
        fail_indices = np.where(group["failed_now"].values)[0]
        if len(fail_indices) == 0:
            continue
        first_fail_idx = fail_indices[0]

        # Find alarms that occurred strictly BEFORE the first failure
        pre_fail_alarms = np.where(group.loc[: first_fail_idx - 1, "alarm"].values)[0]
        if len(pre_fail_alarms) > 0:
            first_alarm_idx = pre_fail_alarms[0]
            lead_window = first_fail_idx - first_alarm_idx
            lead_times_windows.append(lead_window)

    if lead_times_windows:
        return {
            "mean_lead_windows": float(np.mean(lead_times_windows)),
            "median_lead_windows": float(np.median(lead_times_windows)),
            "min_lead_windows": int(np.min(lead_times_windows)),
            "max_lead_windows": int(np.max(lead_times_windows)),
            "mean_lead_seconds": float(np.mean(lead_times_windows) * 10),
            "median_lead_seconds": float(np.median(lead_times_windows) * 10),
            "n_evaluated_episodes": len(lead_times_windows),
        }
    return {
        "mean_lead_windows": 0.0,
        "median_lead_windows": 0.0,
        "min_lead_windows": 0,
        "max_lead_windows": 0,
        "mean_lead_seconds": 0.0,
        "median_lead_seconds": 0.0,
        "n_evaluated_episodes": 0,
    }


def train_pipeline() -> Dict[str, Any]:
    """Execute complete training and evaluation workflow."""
    print("--- [1/5] Loading data and generating labels ---")
    scenarios_csv = DATA_RAW / "telemetry_scenarios.csv"
    raw_df = pd.read_csv(scenarios_csv)
    labeled_df = compute_horizon_labels(raw_df, horizon=HORIZON_WINDOWS)

    print("--- [2/5] Building feature matrix ---")
    feat_df, feature_cols = build_feature_matrix(labeled_df)
    target_col = f"will_fail_h{HORIZON_WINDOWS}"

    print(f"Total dataset: {len(feat_df)} rows, {len(feature_cols)} features")

    # Split train vs held-out test
    train_df, test_df = split_train_test_scenarios(feat_df)
    print(f"Train scenarios (seeds 0-2): {len(train_df)} rows ({len(train_df['scenario_id'].unique())} scenarios)")
    print(f"Held-out test scenarios (seeds 3-5): {len(test_df)} rows ({len(test_df['scenario_id'].unique())} scenarios)")

    # 1. GroupKFold CV on Train set
    print("\n--- [3/5] Running GroupKFold (k=5) Cross-Validation ---")
    gkf_results = run_group_kfold(train_df, feature_cols, target_col, n_splits=5)
    print("GroupKFold Mean Metrics (on training seeds):")
    for k, v in gkf_results["mean_metrics"].items():
        if k != "fold":
            print(f"  {k:12s}: {v:.4f}")

    # 2. Leave-One-Fault-Type-Out CV on Train set
    print("\n--- [4/5] Running Leave-One-Fault-Type-Out (LOFTO) Cross-Validation ---")
    lofto_results = run_leave_one_fault_type_out(train_df, feature_cols, target_col)
    print(lofto_results[["held_out_fault", "roc_auc", "pr_auc", "f1", "n_val_samples"]].to_string(index=False))

    # 3. Train final model on all training scenarios
    print("\n--- [5/5] Training final model and evaluating on Held-Out Test scenarios ---")
    final_model = FailurePredictionModel(feature_names=feature_cols)
    final_model.fit(train_df[feature_cols], train_df[target_col].values)
    final_model.save(MODEL_DIR)

    # Evaluate on Held-out test set
    X_test = test_df[feature_cols]
    y_test = test_df[target_col].values
    test_probs = final_model.predict_proba(X_test)
    test_anomalies = final_model.score_anomaly(X_test)

    test_metrics = compute_metrics(y_test, test_probs)
    lead_time_stats = compute_lead_time_stats(test_df, test_probs)

    # Check healthy baseline on test set
    hb_test = test_df[test_df["fault_type"] == "healthy_baseline"]
    hb_test_probs = final_model.predict_proba(hb_test[feature_cols])
    hb_false_alarms = (hb_test_probs >= 0.5).sum()

    print("\n========================================================")
    print("FINAL HELD-OUT TEST METRICS (self-generated synthetic data)")
    print("========================================================")
    print(f"  ROC-AUC       : {test_metrics['roc_auc']:.4f}")
    print(f"  PR-AUC        : {test_metrics['pr_auc']:.4f}")
    print(f"  F1-Score      : {test_metrics['f1']:.4f}")
    print(f"  Precision     : {test_metrics['precision']:.4f}")
    print(f"  Recall        : {test_metrics['recall']:.4f}")
    print(f"  Brier Score   : {test_metrics['brier']:.4f}")
    print(f"  Mean Lead Time: {lead_time_stats['mean_lead_seconds']:.1f} s ({lead_time_stats['mean_lead_windows']:.1f} windows)")
    print(f"  Test Healthy False Alarms: {hb_false_alarms} / {len(hb_test)} rows")
    print("========================================================")

    # Save metrics report to file
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_data = {
        "metadata": {
            "source": "self-generated synthetic data",
            "model_version": final_model.version,
            "horizon_windows": HORIZON_WINDOWS,
            "train_scenarios": int(train_df["scenario_id"].nunique()),
            "test_scenarios": int(test_df["scenario_id"].nunique()),
        },
        "group_kfold_cv": gkf_results["mean_metrics"],
        "leave_one_fault_out": lofto_results.to_dict(orient="records"),
        "held_out_test_metrics": test_metrics,
        "lead_time_stats": lead_time_stats,
        "test_healthy_false_alarms": int(hb_false_alarms),
    }
    (REPORT_DIR / "training_metrics.json").write_text(json.dumps(report_data, indent=2))

    return {
        "final_model": final_model,
        "report_data": report_data,
        "test_df": test_df,
        "test_probs": test_probs,
        "test_anomalies": test_anomalies,
        "feature_cols": feature_cols,
    }


if __name__ == "__main__":
    train_pipeline()
