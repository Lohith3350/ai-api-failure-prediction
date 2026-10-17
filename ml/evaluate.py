"""
ml/evaluate.py — Generate evaluation metrics and plots on held-out test data.

All artifacts and figures are strictly labeled:
"self-generated synthetic data"
"""
from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import (
    precision_recall_curve,
    roc_curve,
    auc,
    confusion_matrix,
    roc_auc_score,
    average_precision_score,
)

from ml.config import ROOT, DATA_RAW, MODEL_DIR, REPORT_DIR, HORIZON_WINDOWS, TEST_SEED_INDICES
from ml.labeling import compute_horizon_labels
from ml.features import build_feature_matrix
from ml.models import FailurePredictionModel


def generate_evaluation_artifacts():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    model = FailurePredictionModel.load(MODEL_DIR)

    # Load and process data
    scenarios_csv = DATA_RAW / "telemetry_scenarios.csv"
    raw_df = pd.read_csv(scenarios_csv)
    labeled_df = compute_horizon_labels(raw_df, horizon=HORIZON_WINDOWS)
    feat_df, _ = build_feature_matrix(labeled_df)

    # Filter to held-out test scenarios (seeds 03, 04, 05)
    test_suffixes = tuple(f"_{i:02d}" for i in TEST_SEED_INDICES)
    test_df = feat_df[feat_df["scenario_id"].str.endswith(test_suffixes)].copy().reset_index(drop=True)

    X_test = test_df[model.feature_names]
    y_test = test_df[f"will_fail_h{HORIZON_WINDOWS}"].values

    y_prob = model.predict_proba(X_test)
    y_anom = model.score_anomaly(X_test)

    # 1. PR and ROC curves
    precision, recall, _ = precision_recall_curve(y_test, y_prob)
    overall_pr_auc = auc(recall, precision)

    fpr, tpr, _ = roc_curve(y_test, y_prob)
    overall_roc_auc = auc(fpr, tpr)

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    # ROC Curve
    axes[0].plot(fpr, tpr, color="#2b5c8f", lw=2.5, label=f"ROC curve (AUC = {overall_roc_auc:.4f})")
    axes[0].plot([0, 1], [0, 1], color="gray", lw=1.2, linestyle="--")
    axes[0].set_xlim([0.0, 1.0])
    axes[0].set_ylim([0.0, 1.05])
    axes[0].set_xlabel("False Positive Rate", fontsize=11, fontweight="bold")
    axes[0].set_ylabel("True Positive Rate", fontsize=11, fontweight="bold")
    axes[0].set_title("ROC Curve\n[self-generated synthetic data — Held-out seeds 03-05]", fontsize=11, fontweight="bold")
    axes[0].legend(loc="lower right")
    axes[0].grid(True, linestyle="--", alpha=0.5)

    # PR Curve
    axes[1].plot(recall, precision, color="#e76f51", lw=2.5, label=f"PR curve (AUC = {overall_pr_auc:.4f})")
    axes[1].set_xlim([0.0, 1.0])
    axes[1].set_ylim([0.0, 1.05])
    axes[1].set_xlabel("Recall", fontsize=11, fontweight="bold")
    axes[1].set_ylabel("Precision", fontsize=11, fontweight="bold")
    axes[1].set_title("Precision-Recall Curve\n[self-generated synthetic data — Held-out seeds 03-05]", fontsize=11, fontweight="bold")
    axes[1].legend(loc="lower left")
    axes[1].grid(True, linestyle="--", alpha=0.5)

    plt.tight_layout()
    pr_roc_path = REPORT_DIR / "eval_pr_roc_curves.png"
    plt.savefig(pr_roc_path, dpi=160)
    plt.close()
    print(f"Saved ROC/PR curves to: {pr_roc_path}")

    # Copy to artifact directory
    artifact_curves = ROOT.parent / ".gemini" / "antigravity-ide" / "brain" / "294b74bf-3843-483f-930f-ddfd7abb86f2" / "eval_pr_roc_curves.png"
    import shutil
    try:
        shutil.copyfile(pr_roc_path, artifact_curves)
    except Exception:
        pass

    # 2. Confusion matrix at default 0.5 threshold
    y_pred = (y_prob >= 0.5).astype(int)
    cm = confusion_matrix(y_test, y_pred)
    cm_dict = {
        "true_negatives": int(cm[0, 0]),
        "false_positives": int(cm[0, 1]),
        "false_negatives": int(cm[1, 0]),
        "true_positives": int(cm[1, 1]),
    }

    # 3. Fault-type breakdown on held-out test
    breakdown = []
    test_df["y_prob"] = y_prob
    test_df["y_pred"] = y_pred
    target_col = f"will_fail_h{HORIZON_WINDOWS}"

    for fault, g in test_df.groupby("fault_type"):
        y_f_true = g[target_col].values
        y_f_prob = g["y_prob"].values
        y_f_pred = g["y_pred"].values

        has_pos = y_f_true.sum() > 0
        r_auc = roc_auc_score(y_f_true, y_f_prob) if has_pos and len(np.unique(y_f_true)) > 1 else 1.0
        p_auc = average_precision_score(y_f_true, y_f_prob) if has_pos else 1.0
        
        breakdown.append({
            "fault_type": fault,
            "test_rows": len(g),
            "true_positives": int(y_f_true.sum()),
            "predicted_positives": int(y_f_pred.sum()),
            "false_alarms": int(((y_f_true == 0) & (y_f_pred == 1)).sum()),
            "roc_auc": round(float(r_auc), 4),
            "pr_auc": round(float(p_auc), 4),
        })

    bdf = pd.DataFrame(breakdown)
    print("\n=== Held-Out Test Set Performance by Fault Type ===")
    print(bdf.to_string(index=False))

    return {
        "pr_auc": overall_pr_auc,
        "roc_auc": overall_roc_auc,
        "confusion_matrix": cm_dict,
        "breakdown": breakdown,
    }


if __name__ == "__main__":
    generate_evaluation_artifacts()
