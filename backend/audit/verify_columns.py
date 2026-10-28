# -*- coding: utf-8 -*-
"""Verify correct column choices for ZoneA and Temperature."""
import pandas as pd
import numpy as np
import json

import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR) if os.path.basename(SCRIPT_DIR) == "audit" else SCRIPT_DIR
ROOT_DIR = os.path.dirname(BACKEND_DIR)

def resolve_file(candidates):
    for c in candidates:
        if os.path.exists(c):
            return c
    return candidates[0]

csv_path = resolve_file([
    os.path.join(BACKEND_DIR, "data", "raw", "smart_city_energy_dataset.csv"),
    os.path.join(ROOT_DIR, "smart_city_energy_dataset.csv"),
    "smart_city_energy_dataset.csv",
])
df = pd.read_csv(csv_path)
df["Timestamp"] = pd.to_datetime(df["Timestamp"])

# Use Region/Zone ID and ZoneA
zone_col = "Region/Zone ID"
zone = "ZoneA"
df_zone = df[df[zone_col] == zone].copy()
print(f"ZoneA rows: {len(df_zone):,}")
print(f"Lat: {df_zone['Latitude'].iloc[0]}, Lon: {df_zone['Longitude'].iloc[0]}")

# Check Temperature column
temp_col = "Temperature (\u00b0C)"
humidity_col = "Humidity (%)"
cloud_col = "Cloud Cover (%)"
wind_col = "Wind Speed (m/s)"

# Load Open-Meteo
meteo_path = resolve_file([
    os.path.join(BACKEND_DIR, "data", "raw", "openmeteo_weather.csv"),
    os.path.join(BACKEND_DIR, "openmeteo_weather.csv"),
    "backend/openmeteo_weather.csv",
])
meteo = pd.read_csv(meteo_path, parse_dates=["time"]).set_index("time")

# Resample zone data to hourly
df_sorted = df_zone.sort_values("Timestamp").set_index("Timestamp")
target = "Electricity Load"
cols_to_resample = [target, temp_col, humidity_col, cloud_col, wind_col,
                    "Historical Electricity Load (kW)", "Is Holiday"]
hourly = df_sorted[cols_to_resample].resample("1h").mean()

# Reindex
full_range = pd.date_range(hourly.index.min(), hourly.index.max(), freq="1h")
hourly = hourly.reindex(full_range)
hourly.index.name = "Timestamp"

# Interpolate gaps <= 3h
for col in hourly.columns:
    mask = hourly[col].isna()
    groups = mask.ne(mask.shift()).cumsum()
    gap_sizes = mask.groupby(groups).transform("sum")
    hourly[col] = hourly[col].interpolate(method="linear")
    too_long = mask & (gap_sizes > 3)
    hourly.loc[too_long, col] = np.nan

common = hourly.index.intersection(meteo.index)
print(f"Common timestamps: {len(common)}")

hc = hourly.loc[common]
mc = meteo.loc[common]

# Correct Temperature column
temp_corr = hc[temp_col].corr(mc["meteo_temp"])
temp_me = (hc[temp_col] - mc["meteo_temp"]).mean()
temp_mae = (hc[temp_col] - mc["meteo_temp"]).abs().mean()

humidity_corr = hc[humidity_col].corr(mc["meteo_humidity"])
cloud_corr = hc[cloud_col].corr(mc["meteo_cloud"])
wind_corr = hc[wind_col].corr(mc["meteo_wind"])

print(f"\nTemperature vs Open-Meteo: corr={temp_corr:.4f}, ME={temp_me:.2f}, MAE={temp_mae:.2f}")
print(f"Humidity vs Open-Meteo: corr={humidity_corr:.4f}")
print(f"Cloud Cover vs Open-Meteo: corr={cloud_corr:.4f}")
print(f"Wind Speed vs Open-Meteo: corr={wind_corr:.4f}")

# Temperature-Load correlation
temp_load_corr = hourly[target].corr(hourly[temp_col])
print(f"\nTemperature-Load correlation: {temp_load_corr:.4f}")

# Open-Meteo temp-Load correlation
meteo_temp_load_corr = hc[target].corr(mc["meteo_temp"])
print(f"Open-Meteo Temp-Load correlation: {meteo_temp_load_corr:.4f}")

# Load autocorrelation
clean = hourly.dropna(subset=[target])
for lag in [1, 24, 168]:
    ac = clean[target].autocorr(lag)
    print(f"Autocorrelation at lag {lag}h: {ac:.4f}")

# Electricity Load vs Historical Electricity Load
load = df_zone["Electricity Load"]
hist = df_zone["Historical Electricity Load (kW)"]
print(f"\nLoad vs Historical:")
print(f"  Identical: {(load == hist).all()}")
print(f"  Correlation: {load.corr(hist):.6f}")
print(f"  Mean abs diff: {(load - hist).abs().mean():.4f}")
print(f"  Load stats: mean={load.mean():.2f}, std={load.std():.2f}, min={load.min():.2f}, max={load.max():.2f}")
print(f"  Hist stats: mean={hist.mean():.2f}, std={hist.std():.2f}, min={hist.min():.2f}, max={hist.max():.2f}")

# Dataset weather stats
print(f"\nDataset temperature stats: mean={hourly[temp_col].mean():.2f}, std={hourly[temp_col].std():.2f}")
print(f"Open-Meteo temp stats: mean={meteo['meteo_temp'].mean():.2f}, std={meteo['meteo_temp'].std():.2f}")

# DECISION
print(f"\n=== WEATHER DECISION ===")
if temp_corr >= 0.9:
    print(f"KEEP dataset weather (corr={temp_corr:.4f} >= 0.9)")
else:
    print(f"USE Open-Meteo weather (corr={temp_corr:.4f} < 0.9)")
    print("Reason: Dataset weather is uncorrelated with real weather at the same coordinates.")
    print("Training on Open-Meteo historical weather ensures consistency with live predictions.")

# Update audit_decision.json
decision_path = resolve_file([
    os.path.join(BACKEND_DIR, "audit", "audit_decision.json"),
    os.path.join(BACKEND_DIR, "audit_decision.json"),
    "backend/audit/audit_decision.json",
    "backend/audit_decision.json",
])
with open(decision_path) as f:
    decision = json.load(f)
decision["zone"] = zone
decision["zone_column"] = zone_col
decision["zone_rows"] = len(df_zone)
decision["temp_col"] = temp_col
decision["temperature_correlation"] = float(temp_corr)
decision["lat"] = float(df_zone["Latitude"].iloc[0])
decision["lon"] = float(df_zone["Longitude"].iloc[0])

# Fix comparisons
decision["comparisons"] = [
    {"variable": "Temperature", "correlation": float(temp_corr), "mean_error": float(temp_me), "mae": float(temp_mae)},
    {"variable": "Humidity", "correlation": float(humidity_corr), "mean_error": float((hc[humidity_col] - mc["meteo_humidity"]).mean()), "mae": float((hc[humidity_col] - mc["meteo_humidity"]).abs().mean())},
    {"variable": "Cloud Cover", "correlation": float(cloud_corr), "mean_error": float((hc[cloud_col] - mc["meteo_cloud"]).mean()), "mae": float((hc[cloud_col] - mc["meteo_cloud"]).abs().mean())},
    {"variable": "Wind Speed", "correlation": float(wind_corr), "mean_error": float((hc[wind_col] - mc["meteo_wind"]).mean()), "mae": float((hc[wind_col] - mc["meteo_wind"]).abs().mean())},
]

with open(decision_path, "w") as f:
    json.dump(decision, f, indent=2)
print("\nUpdated audit_decision.json")

# Missing data summary after hourly resampling  
remaining = hourly[target].isna().sum()
print(f"\nHourly data: {len(hourly)} rows, {remaining} missing target values ({remaining/len(hourly)*100:.2f}%)")
