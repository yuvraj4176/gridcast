# -*- coding: utf-8 -*-
"""Compute feature importance for saved models using permutation importance."""
import os
import sys
import json
import numpy as np
import pandas as pd
import joblib

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from features import build_features, FEATURE_COLS_SHORT, FEATURE_COLS_LONG, TARGET_COL
from sklearn.inspection import permutation_importance

BASE = os.path.dirname(os.path.dirname(__file__))
DATA_PATH = os.path.join(BASE, "data", "hourly.csv")
MODELS_DIR = os.path.join(BASE, "models")
METRICS_PATH = os.path.join(MODELS_DIR, "metrics.json")

TEST_START = "2024-01-01 00:00:00"

print("Computing feature importance via permutation importance...")

# Load data
df = pd.read_csv(DATA_PATH, parse_dates=["Timestamp"], index_col="Timestamp")
df = df.dropna(subset=["load"])

# Build features
df_short = build_features(df, include_lags=True)
df_long = build_features(df, include_lags=False)

# Get test splits
df_short_clean = df_short.dropna(subset=FEATURE_COLS_SHORT + [TARGET_COL])
test_short = df_short_clean[df_short_clean.index >= TEST_START]
test_long = df_long[df_long.index >= TEST_START]

# Fill NaN weather in long-term
for col in FEATURE_COLS_LONG:
    if test_long[col].isna().any():
        test_long[col] = test_long[col].fillna(test_long[col].mean())

# Load models
model_short = joblib.load(os.path.join(MODELS_DIR, "model_short.joblib"))
model_long = joblib.load(os.path.join(MODELS_DIR, "model_long.joblib"))

# Compute permutation importance
print("\nShort-term model:")
result_short = permutation_importance(
    model_short, test_short[FEATURE_COLS_SHORT].values,
    test_short[TARGET_COL].values, n_repeats=10, random_state=42, n_jobs=-1
)
fi_short = result_short.importances_mean
fi_short_pct = (np.abs(fi_short) / np.abs(fi_short).sum() * 100)
fi_short_dict = dict(zip(FEATURE_COLS_SHORT, fi_short_pct.tolist()))
for f, v in sorted(fi_short_dict.items(), key=lambda x: -x[1]):
    print(f"  {f:<20} {v:>6.1f}%")

print("\nLong-term model:")
result_long = permutation_importance(
    model_long, test_long[FEATURE_COLS_LONG].values,
    test_long[TARGET_COL].values, n_repeats=10, random_state=42, n_jobs=-1
)
fi_long = result_long.importances_mean
fi_long_pct = (np.abs(fi_long) / np.abs(fi_long).sum() * 100)
fi_long_dict = dict(zip(FEATURE_COLS_LONG, fi_long_pct.tolist()))
for f, v in sorted(fi_long_dict.items(), key=lambda x: -x[1]):
    print(f"  {f:<20} {v:>6.1f}%")

# Update metrics.json
with open(METRICS_PATH) as f:
    metrics = json.load(f)

for model_key in metrics["models"]:
    if "short_term" in model_key and "Gradient Boosting" in model_key:
        metrics["models"][model_key]["feature_importance"] = fi_short_dict
    elif "long_term" in model_key and "Gradient Boosting" in model_key:
        metrics["models"][model_key]["feature_importance"] = fi_long_dict

with open(METRICS_PATH, "w") as f:
    json.dump(metrics, f, indent=2)

print("\nUpdated metrics.json with feature importance")
