"""
ml/replay_demo.py — Replay demo on Kishor's telemetry_critical.csv.

Strict requirement from user:
- Report Kishor's critical CSV ONLY as a replay demo, NOT in any evaluation metric.
- Feeds telemetry_critical.csv window-by-window through RealTimeInferenceEngine.
- Demonstrates payment-service failure probability rising, cascading to order-service.
- Generates a visual timeline plot saved to artifacts/reports.
"""
from __future__ import annotations

from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from ml.config import DATA_RAW, REPORT_DIR, ROOT
from ml.inference import RealTimeInferenceEngine


def run_replay_demo(csv_path: Optional[Path] = None, plot_output: Optional[Path] = None):
    csv_path = csv_path or (DATA_RAW / "telemetry_critical.csv")
    plot_output = plot_output or (REPORT_DIR / "critical_replay_demo.png")
    plot_output.parent.mkdir(parents=True, exist_ok=True)

    print(f"\n=================================================================")
    print(f"REPLAY DEMO: {csv_path.name}")
    print(f"NOTE: For demonstration only. NOT included in evaluation metrics.")
    print(f"=================================================================\n")

    df = pd.read_csv(csv_path)
    engine = RealTimeInferenceEngine()
    engine.reset()

    # Group by timestamp (chronological windows)
    timestamps = sorted(df["timestamp"].unique())
    replay_records = []

    print(f"Replaying {len(timestamps)} windows through RealTimeInferenceEngine...\n")
    print(f"{'Window':<7} | {'Service':<16} | {'Fail Prob':<10} | {'Anomaly':<8} | {'Top Explanations'}")
    print("-" * 75)

    for w_idx, ts in enumerate(timestamps):
        window_rows = df[df["timestamp"] == ts].to_dict(orient="records")
        preds = engine.ingest_window(window_rows, scenario_id="replay_critical")

        for p in preds:
            top_feats = ", ".join(f"{f['feature']}={f['value']}" for f in p["explanation"][:2])
            replay_records.append({
                "window": w_idx + 1,
                "timestamp": ts,
                "service_name": p["service_name"],
                "failure_probability": p["failure_probability"],
                "anomaly_score": p["anomaly_score"],
                "top_explanation": top_feats,
            })
            if w_idx < 6 or w_idx >= len(timestamps) - 3 or p["failure_probability"] > 0.8:
                print(f"W{w_idx+1:02d}    | {p['service_name']:<16} | {p['failure_probability']*100:5.1f}%    | {p['anomaly_score']:5.2f}   | {top_feats}")

    rdf = pd.DataFrame(replay_records)

    # Plot replay trajectory
    fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
    palette = {
        "payment-service": "#e63946",
        "order-service": "#f4a261",
        "user-service": "#2a9d8f",
    }

    for svc in ["payment-service", "order-service", "user-service"]:
        s_data = rdf[rdf["service_name"] == svc]
        axes[0].plot(
            s_data["window"],
            s_data["failure_probability"] * 100,
            label=svc,
            color=palette.get(svc, "#333"),
            linewidth=2.5 if svc != "user-service" else 1.5,
            marker="o",
            markersize=4,
        )
        axes[1].plot(
            s_data["window"],
            s_data["anomaly_score"],
            label=svc,
            color=palette.get(svc, "#333"),
            linewidth=2.5 if svc != "user-service" else 1.5,
            marker="s",
            markersize=4,
        )

    axes[0].set_ylabel("Failure Probability (%)", fontsize=11, fontweight="bold")
    axes[0].set_title(
        "Replay Demo: Kishor's telemetry_critical.csv\n(Payment-service failure cascading to Order-service; User-service normal)",
        fontsize=12,
        fontweight="bold",
    )
    axes[0].grid(True, linestyle="--", alpha=0.5)
    axes[0].legend(loc="upper left")
    axes[0].set_ylim(-5, 105)

    axes[1].set_ylabel("Anomaly Score [0..1]", fontsize=11, fontweight="bold")
    axes[1].set_xlabel("Window Index (10s intervals)", fontsize=11, fontweight="bold")
    axes[1].grid(True, linestyle="--", alpha=0.5)
    axes[1].legend(loc="upper left")
    axes[1].set_ylim(-0.05, 1.05)

    plt.tight_layout()
    plt.savefig(plot_output, dpi=160)
    plt.close()
    print(f"\nSaved Replay Demo visualization to: {plot_output}")

    # Copy to artifact directory
    artifact_plot = ROOT.parent / ".gemini" / "antigravity-ide" / "brain" / "294b74bf-3843-483f-930f-ddfd7abb86f2" / "critical_replay_demo.png"
    import shutil
    try:
        shutil.copyfile(plot_output, artifact_plot)
    except Exception:
        pass

    return rdf


if __name__ == "__main__":
    run_replay_demo()
