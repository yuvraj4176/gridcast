# -*- coding: utf-8 -*-
"""
Stage 2a: Prepare the hourly dataset for training.
Loads raw CSV, filters to ZoneA, resamples to hourly, merges Open-Meteo weather,
and saves the cleaned hourly.csv for training and serving.
"""
import pandas as pd
import numpy as np
import json
import os

# ── Paths ──
BASE = os.path.dirname(os.path.dirname(__file__))  # backend/
ROOT = os.path.dirname(BASE)

CSV_PATH = os.path.join(BASE, "data", "raw", "smart_city_energy_dataset.csv")
if not os.path.exists(CSV_PATH):
    CSV_PATH = os.path.join(ROOT, "smart_city_energy_dataset.csv")

METEO_PATH = os.path.join(BASE, "data", "raw", "openmeteo_weather.csv")
if not os.path.exists(METEO_PATH):
    METEO_PATH = os.path.join(BASE, "openmeteo_weather.csv")

DECISION_PATH = os.path.join(BASE, "audit", "audit_decision.json")
if not os.path.exists(DECISION_PATH):
    DECISION_PATH = os.path.join(BASE, "audit_decision.json")

OUT_PATH = os.path.join(BASE, "data", "hourly.csv")

print("=" * 70)
print("STAGE 2a: DATA PREPARATION")
print("=" * 70)

# Load audit decisions
with open(DECISION_PATH) as f:
    decisions = json.load(f)

zone_col = decisions["zone_column"]
zone = decisions["zone"]
target_col = decisions["target_col"]
print(f"Zone: {zone} (column: {zone_col})")
print(f"Target: {target_col}")
print(f"Weather source: Open-Meteo (decision: {decisions['weather_decision']})")

# ── Load and filter raw data ──
print("\nLoading CSV...")
df = pd.read_csv(CSV_PATH)
df["Timestamp"] = pd.to_datetime(df["Timestamp"])
df_zone = df[df[zone_col] == zone].copy()
print(f"  ZoneA rows: {len(df_zone):,}")

# ── Resample to hourly means ──
df_sorted = df_zone.sort_values("Timestamp").set_index("Timestamp")
# Keep only the load column from the original data
hourly_load = df_sorted[[target_col]].resample("1h").mean()
hourly_load.columns = ["load"]

# ── Load Open-Meteo weather ──
print("Loading Open-Meteo weather...")
meteo = pd.read_csv(METEO_PATH, parse_dates=["time"]).set_index("time")
meteo.columns = ["temperature", "humidity", "cloud_cover", "wind_speed"]
# Remove duplicate timestamps
meteo = meteo[~meteo.index.duplicated(keep="first")]
print(f"  Open-Meteo records: {len(meteo):,}")

# ── Create complete hourly index ──
full_range = pd.date_range(
    hourly_load.index.min(), hourly_load.index.max(), freq="1h"
)
hourly_load = hourly_load.reindex(full_range)
hourly_load.index.name = "Timestamp"

# ── Interpolate load gaps <= 3 hours ──
mask = hourly_load["load"].isna()
groups = mask.ne(mask.shift()).cumsum()
gap_sizes = mask.groupby(groups).transform("sum")
hourly_load["load"] = hourly_load["load"].interpolate(method="linear")
# Undo interpolation for gaps > 3 hours
too_long = mask & (gap_sizes > 3)
hourly_load.loc[too_long, "load"] = np.nan

remaining_missing = hourly_load["load"].isna().sum()
print(f"  Load after interpolation: {remaining_missing} missing ({remaining_missing/len(hourly_load)*100:.2f}%)")

# ── Merge weather ──
# Align meteo to our hourly index
hourly = hourly_load.join(meteo, how="left")
print(f"  Weather coverage: {hourly['temperature'].notna().sum()}/{len(hourly)} hours")

# Fill any small weather gaps by interpolation (up to 3h)
for col in ["temperature", "humidity", "cloud_cover", "wind_speed"]:
    wmask = hourly[col].isna()
    if wmask.sum() > 0:
        wgroups = wmask.ne(wmask.shift()).cumsum()
        wgap_sizes = wmask.groupby(wgroups).transform("sum")
        hourly[col] = hourly[col].interpolate(method="linear")
        wtoo_long = wmask & (wgap_sizes > 3)
        hourly.loc[wtoo_long, col] = np.nan

# ── Add holiday column ──
# We'll compute holidays for MA (Massachusetts) using the holidays library
try:
    import holidays as holidays_lib
    us_holidays = holidays_lib.US(state="MA", years=range(2021, 2026))
    hourly["is_holiday"] = hourly.index.date
    hourly["is_holiday"] = hourly["is_holiday"].apply(lambda d: 1 if d in us_holidays else 0)
    print(f"  Holidays marked: {hourly['is_holiday'].sum()} hours")
except ImportError:
    print("  WARNING: holidays library not installed, setting is_holiday=0")
    hourly["is_holiday"] = 0

# ── Save ──
hourly.to_csv(OUT_PATH)
print(f"\nSaved hourly.csv: {hourly.shape}")
print(f"  Date range: {hourly.index.min()} to {hourly.index.max()}")
print(f"  Columns: {list(hourly.columns)}")

# ── Also compute and save typical_weather.csv ──
# Mean weather by month and hour, from training period (through 2023-12-31)
train_mask = hourly.index < "2024-01-01"
train_data = hourly[train_mask].dropna(subset=["temperature"])
train_data = train_data.copy()
train_data["month"] = train_data.index.month
train_data["hour"] = train_data.index.hour

typical = train_data.groupby(["month", "hour"])[
    ["temperature", "humidity", "cloud_cover", "wind_speed"]
].mean().reset_index()

typical_path = os.path.join(BASE, "models", "typical_weather.csv")
typical.to_csv(typical_path, index=False)
print(f"\nSaved typical_weather.csv: {typical.shape}")
print(f"  Sample:\n{typical.head()}")

print("\n" + "=" * 70)
print("DATA PREPARATION COMPLETE")
print("=" * 70)
