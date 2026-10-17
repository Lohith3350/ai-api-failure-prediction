# Machine Learning Failure Prediction Pipeline

> [!IMPORTANT]
> **Data Disclosure**: All evaluation metrics, cross-validation scores, and performance figures reported below were measured on **self-generated synthetic data** produced by the multi-scenario generator. Kishor's `telemetry_critical.csv` is used strictly as an offline replay demonstration and is **not** included in any metric.

---

## 1. Overview & Architecture

This module predicts cascading microservice failures *before* they occur in a 3-tier architecture:
`user-service` $\rightarrow$ `order-service` $\rightarrow$ `payment-service`

- **Horizon $H=3$**: Predicts failure probability within the next 30 seconds ($3 \times 10\text{s}$ windows).
- **Outputs**:
  - `failure_probability` ($[0.0, 1.0]$): Calibrated probability from XGBoost.
  - `anomaly_score` ($[0.0, 1.0]$): Unsupervised deviation score from Isolation Forest.
  - `explanation`: Top-3 feature attributions explaining *why* the score is elevated.
- **Strict Decoupling**: Contains **zero** risk-level thresholds (`LOW`, `MEDIUM`, `CRITICAL`), leaving risk policy to the downstream Decision Engine.

---

## 2. Directory Structure

```
ml/
├── config.py              # Central configuration & config-driven threshold CLI
├── generate_scenarios.py  # Multi-scenario generator (7 fault types, 6 seeds each)
├── labeling.py            # Ground truth labeling (H=3 horizon) & validation suite
├── features.py            # Rolling windows (W=3, 5), slopes, and cross-service lags
├── models.py              # Calibrated XGBoost + Isolation Forest + Explainer
├── train.py               # GroupKFold (k=5) + Leave-One-Fault-Type-Out + Test evaluation
├── inference.py           # Real-time streaming buffer & batch inference engine
├── evaluate.py            # Precision-Recall & ROC plotting and per-fault analysis
├── replay_demo.py         # Kishor's critical CSV replay demo (timeline visualization)
├── thresholds.json        # Calibrated per-service thresholds
├── models/                # Saved model weights and metadata
└── reports/               # Plots and JSON metric summaries
```

---

## 3. Threshold Configuration & Derivation

Thresholds are config-driven and can be re-derived from any normal CSV with a single command:

```bash
# Re-derive thresholds from Kishor's normal CSV
python -m ml.config --derive-from data/raw/telemetry_normal.csv

# Inspect active thresholds
python -m ml.config --show
```

### Calibrated Per-Service Thresholds
| Service | Response Time (`RT_THR`) | Timeouts (`TO_THR`) | Error Rate (`ERROR_THR`) |
|---|---|---|---|
| `user-service` | **70 ms** | **4** | **0.20** |
| `order-service` | **160 ms** *(widened for cascade noise)* | **8** | **0.30** |
| `payment-service` | **150 ms** | **5** | **0.20** |

*Validated against all 6 healthy baseline seeds: 0.00% false positive rate across 2,160 rows.*

---

## 4. Evaluation Results *(self-generated synthetic data)*

Evaluated strictly on **held-out test scenarios (seeds 03, 04, 05)** with **no tuning** on test data.

### Overall Held-Out Test Metrics
| Metric | Value |
|---|---|
| **ROC-AUC** | **0.9910** |
| **PR-AUC** | **0.9853** |
| **Precision** | **0.9689** |
| **Recall** | **0.9515** |
| **F1-Score** | **0.9601** |
| **Brier Score** | **0.0199** |
| **Mean Early Warning Lead Time** | **33.3 seconds** (3.3 windows advance warning) |
| **Healthy Baseline False Alarms** | **0 / 1,080 rows (0.00%)** |

### Cross-Validation Generalization
- **GroupKFold (k=5, grouped by scenario_id)**: Mean ROC-AUC = `0.9913`, Mean PR-AUC = `0.9850`
- **Leave-One-Fault-Type-Out (LOFTO)**:
  - `latency_ramp`: ROC-AUC `0.9926`, PR-AUC `0.9937`
  - `memory_leak`: ROC-AUC `0.9851`, PR-AUC `0.9773`
  - `recovery`: ROC-AUC `0.9939`, PR-AUC `0.9940`
  - `db_overload`: ROC-AUC `0.9916`, PR-AUC `0.9878`
  - `healthy_baseline`: ROC-AUC `1.0000`, PR-AUC `1.0000`

---

## 5. Replay Demo on Kishor's Critical CSV

To run the offline replay demonstration:
```bash
python -m ml.replay_demo
```
This feeds `telemetry_critical.csv` window-by-window through the `RealTimeInferenceEngine`, demonstrating `payment-service` failure probability reaching 98.6% and triggering cascading elevated probabilities in `order-service` (89.6%–99.5%), while `user-service` remains unaffected (0.0%).

---

## 6. Real-Time Inference Contract (For Lohith / FastAPI)

```python
from ml.inference import RealTimeInferenceEngine

engine = RealTimeInferenceEngine()

# As each window arrives from telemetry collector:
window_telemetry = [
    {"service_name": "payment-service", "timestamp": "...", "response_time_ms": 280, ...},
    {"service_name": "order-service",   "timestamp": "...", "response_time_ms": 195, ...},
    {"service_name": "user-service",    "timestamp": "...", "response_time_ms": 45,  ...},
]

predictions = engine.ingest_window(window_telemetry)
for p in predictions:
    print(p["service_name"])
    print(f"  P(Fail in 30s): {p['failure_probability'] * 100:.1f}%")
    print(f"  Anomaly Score:  {p['anomaly_score']:.2f}")
    print(f"  Top Features:   {p['explanation']}")
```
