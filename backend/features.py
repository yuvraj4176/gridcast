# -*- coding: utf-8 -*-
"""
Shared feature engineering for GridCast.
This SINGLE function is used in both training and serving to prevent train-serve mismatch.
"""
import numpy as np
import pandas as pd


def build_features(df, include_lags=True):
    """
    Build features from a DataFrame with columns:
      - Timestamp (index, DatetimeIndex)
      - load (target, can have NaN for future rows)
      - temperature, humidity, cloud_cover, wind_speed (weather)
      - is_holiday (0/1)

    Parameters
    ----------
    df : pd.DataFrame
        Must have a DatetimeIndex named 'Timestamp' or be datetime-indexed.
    include_lags : bool
        If True, include lag_24 and lag_168 features (for short-term model).
        If False, only calendar + weather features (for long-term model).

    Returns
    -------
    pd.DataFrame with feature columns added.
    """
    out = df.copy()

    # ── Calendar features ──
    out["hour"] = out.index.hour
    out["day_of_week"] = out.index.dayofweek
    out["month"] = out.index.month
    out["is_weekend"] = (out.index.dayofweek >= 5).astype(int)

    # Cyclic encoding of hour (period=24) and month (period=12)
    out["hour_sin"] = np.sin(2 * np.pi * out["hour"] / 24)
    out["hour_cos"] = np.cos(2 * np.pi * out["hour"] / 24)
    out["month_sin"] = np.sin(2 * np.pi * out["month"] / 12)
    out["month_cos"] = np.cos(2 * np.pi * out["month"] / 12)

    # ── Lag features (strictly causal: at least 24h older) ──
    if include_lags:
        # lag_24 = load from exactly 24 hours ago
        out["lag_24"] = out["load"].shift(24)
        # lag_168 = load from exactly 168 hours (1 week) ago
        out["lag_168"] = out["load"].shift(168)

    return out


# The exact feature column names used by each model type
FEATURE_COLS_SHORT = [
    "hour", "day_of_week", "month", "is_weekend", "is_holiday",
    "hour_sin", "hour_cos", "month_sin", "month_cos",
    "temperature", "humidity", "cloud_cover", "wind_speed",
    "lag_24", "lag_168",
]

FEATURE_COLS_LONG = [
    "hour", "day_of_week", "month", "is_weekend", "is_holiday",
    "hour_sin", "hour_cos", "month_sin", "month_cos",
    "temperature", "humidity", "cloud_cover", "wind_speed",
]

TARGET_COL = "load"
