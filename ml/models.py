"""
ml/models.py — Model architecture: Failure Predictor, Anomaly Scorer, Explainer.

Outputs:
- failure_probability: float in [0.0, 1.0] from Calibrated XGBoost
- anomaly_score: float in [0.0, 1.0] from Isolation Forest (min-max scaled)
- explanation: dict with top contributing features and values

Adheres strictly to constraints:
- NO risk-level thresholds (handled by downstream decision engine)
- Clear separation of probability vs anomaly score
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import pandas as pd
import joblib
from xgboost import XGBClassifier
from sklearn.ensemble import IsolationForest
from sklearn.calibration import CalibratedClassifierCV
from ml.config import XGBOOST_PARAMS, IFOREST_PARAMS, MODEL_DIR, MODEL_VERSION


class FailurePredictionModel:
    """
    Combined failure prediction pipeline:
    1. XGBoost classifier (calibrated) for P(failure in H)
    2. Isolation Forest for unsupervised anomaly score
    3. Feature attribution explanation
    """

    def __init__(
        self,
        xgb_params: Optional[dict] = None,
        iforest_params: Optional[dict] = None,
        feature_names: Optional[List[str]] = None,
    ):
        self.xgb_params = xgb_params or XGBOOST_PARAMS
        self.iforest_params = iforest_params or IFOREST_PARAMS
        self.feature_names = feature_names or []
        self.xgb_model: Optional[XGBClassifier] = None
        self.calibrated_xgb = None
        self.iforest: Optional[IsolationForest] = None
        self.version = MODEL_VERSION

    def fit(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: Optional[pd.DataFrame] = None,
        y_val: Optional[pd.Series] = None,
    ):
        """Fit calibrated XGBoost on all data and Isolation Forest on healthy records."""
        self.feature_names = list(X_train.columns)

        # 1. Fit XGBoost classifier
        raw_xgb = XGBClassifier(**self.xgb_params)
        raw_xgb.fit(X_train, y_train)
        self.xgb_model = raw_xgb

        # Use sigmoid calibration to guarantee well-calibrated probabilities
        if X_val is not None and y_val is not None and len(np.unique(y_val)) > 1:
            calibrator = CalibratedClassifierCV(estimator=raw_xgb, cv="prefit", method="sigmoid")
            calibrator.fit(X_val, y_val)
            self.calibrated_xgb = calibrator
        else:
            self.calibrated_xgb = raw_xgb

        # 2. Fit Isolation Forest on negative / healthy samples
        healthy_mask = (y_train == 0)
        X_healthy = X_train[healthy_mask] if healthy_mask.sum() > 50 else X_train
        self.iforest = IsolationForest(**self.iforest_params)
        self.iforest.fit(X_healthy)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Return failure probability array."""
        if self.calibrated_xgb is None:
            raise RuntimeError("Model is not fitted yet.")
        probs = self.calibrated_xgb.predict_proba(X)
        return probs[:, 1]

    def score_anomaly(self, X: pd.DataFrame) -> np.ndarray:
        """
        Return anomaly score scaled to [0.0, 1.0].
        Isolation Forest decision_function returns negative values for anomalies,
        positive for inliers. We invert and normalize so 1.0 = highly anomalous.
        """
        if self.iforest is None:
            raise RuntimeError("Isolation Forest is not fitted.")
        raw_scores = self.iforest.decision_function(X)
        # Shift and scale: score typically ranges [-0.5, 0.5]
        # Invert: higher means more anomalous
        inverted = -raw_scores
        # Sigmoid normalization for stability: 1 / (1 + exp(-4 * inverted))
        normalized = 1.0 / (1.0 + np.exp(-4.0 * inverted))
        return np.clip(normalized, 0.0, 1.0)

    def explain_sample(
        self,
        sample: pd.Series,
        top_k: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Explain a single observation using feature importance weighted by feature value deviation.
        Returns top_k most significant features for this sample.
        """
        if self.xgb_model is None:
            return []

        importances = self.xgb_model.feature_importances_
        feature_scores = []
        for name, imp in zip(self.feature_names, importances):
            val = float(sample.get(name, 0.0))
            score = imp * abs(val)
            feature_scores.append((score, name, val, float(imp)))

        feature_scores.sort(key=lambda x: x[0], reverse=True)
        top = feature_scores[:top_k]

        return [
            {
                "feature": name,
                "value": round(val, 3),
                "model_importance": round(imp, 4),
            }
            for _, name, val, imp in top
        ]

    def save(self, model_dir: Optional[Path] = None):
        """Save model artifacts to disk."""
        model_dir = model_dir or MODEL_DIR
        model_dir.mkdir(parents=True, exist_ok=True)

        joblib.dump(self.xgb_model, model_dir / "xgboost_raw.joblib")
        joblib.dump(self.calibrated_xgb, model_dir / "xgboost_calibrated.joblib")
        joblib.dump(self.iforest, model_dir / "isolation_forest.joblib")

        meta = {
            "version": self.version,
            "feature_names": self.feature_names,
            "n_features": len(self.feature_names),
        }
        (model_dir / "metadata.json").write_text(json.dumps(meta, indent=2))

    @classmethod
    def load(cls, model_dir: Optional[Path] = None) -> "FailurePredictionModel":
        """Load model artifacts from disk."""
        model_dir = model_dir or MODEL_DIR
        meta_path = model_dir / "metadata.json"
        if not meta_path.exists():
            raise FileNotFoundError(f"No model found at {model_dir}")

        meta = json.loads(meta_path.read_text())
        model = cls(feature_names=meta["feature_names"])
        model.version = meta.get("version", MODEL_VERSION)
        model.xgb_model = joblib.load(model_dir / "xgboost_raw.joblib")
        model.calibrated_xgb = joblib.load(model_dir / "xgboost_calibrated.joblib")
        model.iforest = joblib.load(model_dir / "isolation_forest.joblib")
        return model
