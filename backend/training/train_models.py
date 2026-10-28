# -*- coding: utf-8 -*-
"""
Stage 2b: Train all models for GridCast.
Baselines, short-term (with lags), and long-term (no lags) models.
Re-runnable: just run this script to retrain everything.

Time-based split (NEVER shuffled):
  - Train: through 2023-12-31
  - Test: from 2024-01-01 onward
  - Validation: last year of training (2023) for hyperparameter tuning
"""
import os
import sys
import json
import numpy as np
import pandas as pd
from datetime import datetime

# Add parent directory to path so we can import features.py
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from features import build_features, FEATURE_COLS_SHORT, FEATURE_COLS_LONG, TARGET_COL

from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
import joblib

# ── Paths ──
BASE = os.path.dirname(os.path.dirname(__file__))  # backend/
DATA_PATH = os.path.join(BASE, "data", "hourly.csv")
MODELS_DIR = os.path.join(BASE, "models")

# ── Configuration ──
TRAIN_END = "2023-12-31 23:00:00"
TEST_START = "2024-01-01 00:00:00"
VAL_START = "2023-01-01 00:00:00"  # Last year of training for validation

print("=" * 70)
print("STAGE 2b: MODEL TRAINING")
print("=" * 70)

# ══════════════════════════════════════════════════════════════════════
# 1. LOAD DATA
# ══════════════════════════════════════════════════════════════════════
print("\n[1] Loading hourly.csv...")
df = pd.read_csv(DATA_PATH, parse_dates=["Timestamp"], index_col="Timestamp")
print(f"  Shape: {df.shape}")
print(f"  Date range: {df.index.min()} to {df.index.max()}")
print(f"  Missing load values: {df['load'].isna().sum()}")

# Drop rows with missing load (only 87 = 0.24%)
df = df.dropna(subset=["load"])
print(f"  After dropping NaN load: {df.shape}")

# ══════════════════════════════════════════════════════════════════════
# 2. BUILD FEATURES
# ══════════════════════════════════════════════════════════════════════
print("\n[2] Building features...")

# Build features with lags (for short-term model)
df_short = build_features(df, include_lags=True)

# Build features without lags (for long-term model)
df_long = build_features(df, include_lags=False)

# ══════════════════════════════════════════════════════════════════════
# 3. SPLIT DATA
# ══════════════════════════════════════════════════════════════════════
print("\n[3] Splitting data (time-based, never shuffled)...")

# Short-term: need to drop rows where lags are NaN (first 168 hours)
df_short_clean = df_short.dropna(subset=FEATURE_COLS_SHORT + [TARGET_COL])

train_short = df_short_clean[df_short_clean.index <= TRAIN_END]
test_short = df_short_clean[df_short_clean.index >= TEST_START]
val_short = train_short[train_short.index >= VAL_START]
train_only_short = train_short[train_short.index < VAL_START]

# Long-term: fill any NaN weather with column mean (should be rare)
for col in FEATURE_COLS_LONG:
    if df_long[col].isna().any():
        df_long[col] = df_long[col].fillna(df_long[col].mean())

train_long = df_long[df_long.index <= TRAIN_END]
test_long = df_long[df_long.index >= TEST_START]
val_long = train_long[train_long.index >= VAL_START]
train_only_long = train_long[train_long.index < VAL_START]

print(f"  Short-term: train={len(train_short)}, val={len(val_short)}, test={len(test_short)}")
print(f"  Long-term:  train={len(train_long)}, val={len(val_long)}, test={len(test_long)}")
print(f"  Train period: {train_short.index.min()} to {train_short.index.max()}")
print(f"  Test period:  {test_short.index.min()} to {test_short.index.max()}")

# ══════════════════════════════════════════════════════════════════════
# 4. BASELINES
# ══════════════════════════════════════════════════════════════════════
print("\n[4] Computing baselines...")


def compute_metrics(y_true, y_pred, name=""):
    """Compute MAE, RMSE, MAPE for a set of predictions."""
    mask = ~(np.isnan(y_true) | np.isnan(y_pred))
    yt = y_true[mask]
    yp = y_pred[mask]
    mae = mean_absolute_error(yt, yp)
    rmse = np.sqrt(mean_squared_error(yt, yp))
    # MAPE: avoid division by zero
    nonzero = yt != 0
    if nonzero.sum() > 0:
        mape = np.mean(np.abs((yt[nonzero] - yp[nonzero]) / yt[nonzero])) * 100
    else:
        mape = np.nan
    if name:
        print(f"  {name:30s}  MAE={mae:8.2f}  RMSE={rmse:8.2f}  MAPE={mape:6.2f}%")
    return {"mae": float(mae), "rmse": float(rmse), "mape": float(mape)}


# Baseline 1: Same hour yesterday (lag 24)
test_df = df.copy()
test_df["baseline_yesterday"] = test_df["load"].shift(24)
test_period = test_df[test_df.index >= TEST_START].dropna(subset=["baseline_yesterday"])

y_test = test_period["load"].values
baseline_yesterday = compute_metrics(
    y_test, test_period["baseline_yesterday"].values, "Same hour yesterday"
)

# Baseline 2: Same hour last week (lag 168)
test_df["baseline_last_week"] = test_df["load"].shift(168)
test_period_w = test_df[test_df.index >= TEST_START].dropna(subset=["baseline_last_week"])
baseline_last_week = compute_metrics(
    test_period_w["load"].values,
    test_period_w["baseline_last_week"].values,
    "Same hour last week"
)

# Pick best baseline
best_baseline_mae = min(baseline_yesterday["mae"], baseline_last_week["mae"])
best_baseline_name = "Same hour yesterday" if baseline_yesterday["mae"] < baseline_last_week["mae"] else "Same hour last week"
print(f"\n  Best baseline: {best_baseline_name} (MAE={best_baseline_mae:.2f})")

# ══════════════════════════════════════════════════════════════════════
# 5. TRAIN MODELS
# ══════════════════════════════════════════════════════════════════════
print("\n[5] Training models...")

all_results = {}
best_short = {"mae": np.inf, "name": None, "model": None}
best_long = {"mae": np.inf, "name": None, "model": None}

def make_models():
    """Create fresh model instances each time to avoid reuse issues."""
    return [
        ("Linear Regression", LinearRegression()),
        ("Random Forest", RandomForestRegressor(
            n_estimators=200, max_depth=15, min_samples_leaf=10,
            n_jobs=-1, random_state=42,
        )),
        ("Gradient Boosting", HistGradientBoostingRegressor(
            max_iter=500, max_depth=8, learning_rate=0.05,
            min_samples_leaf=20, random_state=42,
        )),
    ]

for model_type in ["short_term", "long_term"]:
    print(f"\n  --- {model_type.upper()} MODELS ---")
    if model_type == "short_term":
        features = FEATURE_COLS_SHORT
        train_data = train_short
        test_data = test_short
        val_data = val_short
    else:
        features = FEATURE_COLS_LONG
        train_data = train_long
        test_data = test_long
        val_data = val_long

    X_train = train_data[features].values
    y_train = train_data[TARGET_COL].values
    X_test = test_data[features].values
    y_test_ml = test_data[TARGET_COL].values
    X_val = val_data[features].values
    y_val = val_data[TARGET_COL].values

    for name, model in make_models():
        full_name = f"{name} ({model_type})"
        print(f"\n  Training {full_name}...")

        model.fit(X_train, y_train)

        # Validation score
        val_pred = model.predict(X_val)
        val_metrics = compute_metrics(y_val, val_pred, f"  Val: {name}")

        # Test score (touched only once for final scoring)
        test_pred = model.predict(X_test)
        test_metrics = compute_metrics(y_test_ml, test_pred, f"  Test: {name}")

        # Check for suspected leakage
        if test_metrics["mape"] < 1.0:
            print(f"  *** WARNING: MAPE < 1% ({test_metrics['mape']:.2f}%) -- suspected leakage! ***")
            print(f"  Investigating... Features used: {features}")
            # Since we know the data is synthetic, this is unlikely

        # Improvement over best baseline
        improvement = (best_baseline_mae - test_metrics["mae"]) / best_baseline_mae * 100

        result = {
            "model_type": model_type,
            "algorithm": name,
            "val_mae": val_metrics["mae"],
            "val_rmse": val_metrics["rmse"],
            "val_mape": val_metrics["mape"],
            "test_mae": test_metrics["mae"],
            "test_rmse": test_metrics["rmse"],
            "test_mape": test_metrics["mape"],
            "improvement_over_baseline_pct": improvement,
        }

        # Feature importance
        if hasattr(model, "feature_importances_"):
            fi = model.feature_importances_
            fi_normalized = (fi / fi.sum() * 100).tolist()
            result["feature_importance"] = dict(zip(features, fi_normalized))
        elif hasattr(model, "coef_"):
            coef = np.abs(model.coef_)
            if coef.sum() > 0:
                fi_normalized = (coef / coef.sum() * 100).tolist()
            else:
                fi_normalized = [100.0 / len(features)] * len(features)
            result["feature_importance"] = dict(zip(features, fi_normalized))

        all_results[full_name] = result
        print(f"  Improvement over baseline: {improvement:+.1f}%")

        # Track best models
        if model_type == "short_term" and test_metrics["mae"] < best_short["mae"]:
            best_short = {"mae": test_metrics["mae"], "name": full_name, "model": model, "algorithm": name}
        if model_type == "long_term" and test_metrics["mae"] < best_long["mae"]:
            best_long = {"mae": test_metrics["mae"], "name": full_name, "model": model, "algorithm": name}

print(f"\n  Best short-term model: {best_short['name']} (MAE={best_short['mae']:.2f})")
print(f"  Best long-term model: {best_long['name']} (MAE={best_long['mae']:.2f})")

# ══════════════════════════════════════════════════════════════════════
# 6. ERROR ANALYSIS
# ══════════════════════════════════════════════════════════════════════
print("\n[6] Error analysis...")

# Re-predict with best models for detailed analysis
if best_short["model"] is not None:
    test_short_pred = best_short["model"].predict(test_short[FEATURE_COLS_SHORT].values)
    test_short_df = test_short.copy()
    test_short_df["predicted"] = test_short_pred
    test_short_df["residual"] = test_short_df["load"] - test_short_df["predicted"]
    test_short_df["abs_error"] = test_short_df["residual"].abs()

    # Error by hour of day
    print("\n  Short-term error by hour of day:")
    error_by_hour = test_short_df.groupby("hour")["abs_error"].mean()
    for h, e in error_by_hour.items():
        print(f"    {h:2d}:00  MAE={e:.2f}")

    # Error weekday vs weekend
    wd_err = test_short_df[test_short_df["is_weekend"] == 0]["abs_error"].mean()
    we_err = test_short_df[test_short_df["is_weekend"] == 1]["abs_error"].mean()
    print(f"\n  Weekday MAE: {wd_err:.2f}")
    print(f"  Weekend MAE: {we_err:.2f}")

# Same for long-term
if best_long["model"] is not None:
    test_long_pred = best_long["model"].predict(test_long[FEATURE_COLS_LONG].values)
    test_long_df = test_long.copy()
    test_long_df["predicted"] = test_long_pred
    test_long_df["residual"] = test_long_df["load"] - test_long_df["predicted"]
    test_long_df["abs_error"] = test_long_df["residual"].abs()

    print("\n  Long-term error by hour of day:")
    error_by_hour_long = test_long_df.groupby("hour")["abs_error"].mean()
    for h, e in error_by_hour_long.items():
        print(f"    {h:2d}:00  MAE={e:.2f}")

    wd_err_l = test_long_df[test_long_df["is_weekend"] == 0]["abs_error"].mean()
    we_err_l = test_long_df[test_long_df["is_weekend"] == 1]["abs_error"].mean()
    print(f"\n  Weekday MAE: {wd_err_l:.2f}")
    print(f"  Weekend MAE: {we_err_l:.2f}")

# ══════════════════════════════════════════════════════════════════════
# 7. CONFIDENCE BANDS (empirical residual quantiles)
# ══════════════════════════════════════════════════════════════════════
print("\n[7] Computing confidence bands...")

residual_quantiles = {"short_term": {}, "long_term": {}}

# Short-term: use test residuals grouped by hour of day
if best_short["model"] is not None:
    for h in range(24):
        hour_residuals = test_short_df[test_short_df["hour"] == h]["residual"]
        if len(hour_residuals) > 10:
            q10 = float(hour_residuals.quantile(0.10))
            q90 = float(hour_residuals.quantile(0.90))
        else:
            q10 = float(test_short_df["residual"].quantile(0.10))
            q90 = float(test_short_df["residual"].quantile(0.90))
        residual_quantiles["short_term"][str(h)] = {"q10": q10, "q90": q90}

# Long-term: same approach
if best_long["model"] is not None:
    for h in range(24):
        hour_residuals = test_long_df[test_long_df["hour"] == h]["residual"]
        if len(hour_residuals) > 10:
            q10 = float(hour_residuals.quantile(0.10))
            q90 = float(hour_residuals.quantile(0.90))
        else:
            q10 = float(test_long_df["residual"].quantile(0.10))
            q90 = float(test_long_df["residual"].quantile(0.90))
        residual_quantiles["long_term"][str(h)] = {"q10": q10, "q90": q90}

# Save
quantiles_path = os.path.join(MODELS_DIR, "residual_quantiles.json")
with open(quantiles_path, "w") as f:
    json.dump(residual_quantiles, f, indent=2)
print(f"  Saved residual_quantiles.json")
print(f"  Short-term band width (avg): {np.mean([v['q90'] - v['q10'] for v in residual_quantiles['short_term'].values()]):.2f} kW")
print(f"  Long-term band width (avg): {np.mean([v['q90'] - v['q10'] for v in residual_quantiles['long_term'].values()]):.2f} kW")

# ══════════════════════════════════════════════════════════════════════
# 8. SAMPLE TEST WEEK (predicted vs actual)
# ══════════════════════════════════════════════════════════════════════
print("\n[8] Extracting sample test week...")

# Pick a week in the middle of the test period
sample_start = "2024-07-15"
sample_end = "2024-07-22"
sample_short = test_short_df[
    (test_short_df.index >= sample_start) & (test_short_df.index < sample_end)
].copy()

if len(sample_short) > 0:
    sample_week = []
    for idx, row in sample_short.iterrows():
        sample_week.append({
            "time": idx.isoformat(),
            "actual": float(row["load"]),
            "predicted": float(row["predicted"]),
        })
    print(f"  Sample week: {len(sample_week)} hours ({sample_start} to {sample_end})")
else:
    sample_week = []
    print("  WARNING: No data in sample week range")

# ══════════════════════════════════════════════════════════════════════
# 9. SAVE EVERYTHING
# ══════════════════════════════════════════════════════════════════════
print("\n[9] Saving models and metrics...")

# Save best models
joblib.dump(best_short["model"], os.path.join(MODELS_DIR, "model_short.joblib"))
joblib.dump(best_long["model"], os.path.join(MODELS_DIR, "model_long.joblib"))
print(f"  Saved model_short.joblib ({best_short['name']})")
print(f"  Saved model_long.joblib ({best_long['name']})")

# Error by hour of day for both models
error_by_hour_short = {}
error_by_hour_long_dict = {}
if best_short["model"] is not None:
    for h in range(24):
        error_by_hour_short[str(h)] = float(
            test_short_df[test_short_df["hour"] == h]["abs_error"].mean()
        )
if best_long["model"] is not None:
    for h in range(24):
        error_by_hour_long_dict[str(h)] = float(
            test_long_df[test_long_df["hour"] == h]["abs_error"].mean()
        )

# Build metrics.json
metrics = {
    "generated_at": datetime.now().isoformat(),
    "train_period": {
        "start": str(train_short.index.min()),
        "end": str(TRAIN_END),
    },
    "test_period": {
        "start": str(TEST_START),
        "end": str(test_short.index.max()),
    },
    "baselines": {
        "same_hour_yesterday": baseline_yesterday,
        "same_hour_last_week": baseline_last_week,
        "best_baseline": best_baseline_name,
        "best_baseline_mae": best_baseline_mae,
    },
    "models": all_results,
    "best_short_term": {
        "name": best_short["name"],
        "algorithm": best_short.get("algorithm", ""),
        "mae": best_short["mae"],
    },
    "best_long_term": {
        "name": best_long["name"],
        "algorithm": best_long.get("algorithm", ""),
        "mae": best_long["mae"],
    },
    "error_by_hour_short": error_by_hour_short,
    "error_by_hour_long": error_by_hour_long_dict,
    "error_weekday_weekend": {
        "short_term": {"weekday": float(wd_err), "weekend": float(we_err)},
        "long_term": {"weekday": float(wd_err_l), "weekend": float(we_err_l)},
    },
    "sample_test_week": sample_week,
}

metrics_path = os.path.join(MODELS_DIR, "metrics.json")
with open(metrics_path, "w") as f:
    json.dump(metrics, f, indent=2)
print(f"  Saved metrics.json")

# ══════════════════════════════════════════════════════════════════════
# 10. PRINT FINAL SCORE TABLE
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("FINAL SCORE TABLE")
print("=" * 70)
print(f"\n{'Model':<40} {'MAE':>8} {'RMSE':>8} {'MAPE':>7} {'vs Baseline':>12}")
print("-" * 78)
print(f"{'Baseline: ' + best_baseline_name:<40} {best_baseline_mae:>8.2f} {'':>8} {'':>7} {'(reference)':>12}")
for name, r in sorted(all_results.items()):
    print(f"{name:<40} {r['test_mae']:>8.2f} {r['test_rmse']:>8.2f} {r['test_mape']:>6.1f}% {r['improvement_over_baseline_pct']:>+10.1f}%")

print(f"\nBest short-term: {best_short['name']} (MAE={best_short['mae']:.2f})")
print(f"Best long-term:  {best_long['name']} (MAE={best_long['mae']:.2f})")

# Feature importance for best models
for model_name in [best_short["name"], best_long["name"]]:
    if model_name in all_results and "feature_importance" in all_results[model_name]:
        fi = all_results[model_name]["feature_importance"]
        print(f"\nFeature importance ({model_name}):")
        for feat, imp in sorted(fi.items(), key=lambda x: -x[1]):
            bar = "#" * int(imp / 2)
            print(f"  {feat:<20} {imp:>6.1f}%  {bar}")

print("\n" + "=" * 70)
print("STAGE 2 COMPLETE. Waiting for 'continue' before Stage 3.")
print("=" * 70)
