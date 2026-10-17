"""
ml/data_loader.py — Telemetry dataset loader and validator.

Loads, validates, and cleans telemetry datasets for both offline training
and streaming inference pipelines.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Union, List
import pandas as pd
import numpy as np

REQUIRED_COLUMNS = [
    "timestamp",
    "service_name",
    "response_time_ms",
    "request_count",
    "error_rate",
    "http_5xx_count",
    "timeout_count",
]

OPTIONAL_NUMERIC_COLUMNS = [
    "cpu_usage_pct",
    "memory_usage_pct",
    "dependency_latency_ms",
]


def load_telemetry_csv(
    file_path: Union[str, Path],
    assign_default_scenario: bool = True,
) -> pd.DataFrame:
    """
    Load a raw telemetry CSV and ensure standard columns and types.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Telemetry file not found: {path}")

    df = pd.read_csv(path)

    # Check required columns
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Telemetry CSV missing required columns: {missing}")

    # Ensure numeric columns are floats/ints
    for col in ["response_time_ms", "error_rate"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    for col in ["request_count", "http_5xx_count", "timeout_count"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    for col in OPTIONAL_NUMERIC_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # If scenario_id not present, generate a default one
    if "scenario_id" not in df.columns and assign_default_scenario:
        df["scenario_id"] = path.stem

    if "fault_type" not in df.columns:
        df["fault_type"] = "unknown"

    # Sort chronologically by (scenario_id, service_name, timestamp)
    df = df.sort_values(["scenario_id", "service_name", "timestamp"]).reset_index(drop=True)

    return df


def validate_telemetry_df(df: pd.DataFrame) -> bool:
    """
    Perform sanity checks on a telemetry DataFrame.
    """
    if df.empty:
        raise ValueError("DataFrame is empty")

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    if (df["error_rate"] < 0).any() or (df["error_rate"] > 1.0).any():
        raise ValueError("error_rate must be between 0.0 and 1.0")

    if (df["response_time_ms"] < 0).any():
        raise ValueError("response_time_ms cannot be negative")

    return True
