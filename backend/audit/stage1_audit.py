"""
Stage 1: Data Audit for GridCast
Loads the ISONE smart city energy dataset and produces a comprehensive audit.
"""
import pandas as pd
import numpy as np
import json
import os
import sys
import requests
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings("ignore")

# ── Paths ──
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR) if os.path.basename(SCRIPT_DIR) == "audit" else SCRIPT_DIR
ROOT_DIR = os.path.dirname(BACKEND_DIR)

csv_candidates = [
    os.path.join(BACKEND_DIR, "data", "raw", "smart_city_energy_dataset.csv"),
    os.path.join(ROOT_DIR, "smart_city_energy_dataset.csv"),
    "smart_city_energy_dataset.csv",
]
CSV_PATH = next((p for p in csv_candidates if os.path.exists(p)), csv_candidates[0])
REPORT_PATH = os.path.join(SCRIPT_DIR, "data_report.md")

print("=" * 70)
print("STAGE 1: DATA AUDIT")
print("=" * 70)

# ══════════════════════════════════════════════════════════════════════
# 1. LOAD AND BASIC AUDIT
# ══════════════════════════════════════════════════════════════════════
print("\n[1] Loading CSV...")
df = pd.read_csv(CSV_PATH)
print(f"  Shape: {df.shape}")
print(f"  Columns ({len(df.columns)}):")
for i, col in enumerate(df.columns):
    print(f"    {i:2d}. {col} ({df[col].dtype})")

# Parse timestamp
ts_col = [c for c in df.columns if 'timestamp' in c.lower()][0]
print(f"\n  Timestamp column: '{ts_col}'")
df['Timestamp'] = pd.to_datetime(df[ts_col])
print(f"  Date range: {df['Timestamp'].min()} to {df['Timestamp'].max()}")
print(f"  Duration: {(df['Timestamp'].max() - df['Timestamp'].min()).days} days")

# Check time intervals
diffs = df['Timestamp'].diff().dropna()
print(f"\n  Time interval stats:")
print(f"    Most common: {diffs.mode().iloc[0]}")
print(f"    Min: {diffs.min()}")
print(f"    Max: {diffs.max()}")
print(f"    Unique intervals: {diffs.nunique()}")

# ══════════════════════════════════════════════════════════════════════
# 2. ZONE ANALYSIS
# ══════════════════════════════════════════════════════════════════════
print("\n[2] Zone analysis...")
zone_cols = [c for c in df.columns if any(x in c.lower() for x in ['zone', 'region', 'substation'])]
print(f"  Zone-related columns: {zone_cols}")

for col in zone_cols:
    vc = df[col].value_counts()
    print(f"\n  '{col}' distribution ({vc.nunique()} unique values):")
    for val, cnt in vc.head(20).items():
        print(f"    {val}: {cnt:,} rows ({cnt/len(df)*100:.1f}%)")

# Determine zone column and pick the largest zone
# Try Region/Zone ID first
zone_col = None
for c in zone_cols:
    if 'zone' in c.lower() or 'region' in c.lower():
        zone_col = c
        break
if zone_col is None and zone_cols:
    zone_col = zone_cols[0]

if zone_col:
    biggest_zone = df[zone_col].value_counts().index[0]
    biggest_count = df[zone_col].value_counts().iloc[0]
    print(f"\n  → Selected zone: '{biggest_zone}' from column '{zone_col}' ({biggest_count:,} rows)")
    df_zone = df[df[zone_col] == biggest_zone].copy()
else:
    print("\n  → No zone column found, using all data")
    df_zone = df.copy()

print(f"  Zone data shape: {df_zone.shape}")

# Get lat/lon for the zone
lat_col = [c for c in df.columns if 'lat' in c.lower()][0] if any('lat' in c.lower() for c in df.columns) else None
lon_col = [c for c in df.columns if 'lon' in c.lower()][0] if any('lon' in c.lower() for c in df.columns) else None
if lat_col and lon_col:
    lat = df_zone[lat_col].iloc[0]
    lon = df_zone[lon_col].iloc[0]
    print(f"  Lat/Lon: {lat}, {lon}")
else:
    lat, lon = None, None
    print("  No Lat/Lon columns found")

# ══════════════════════════════════════════════════════════════════════
# 3. DUPLICATE TIMESTAMPS
# ══════════════════════════════════════════════════════════════════════
print("\n[3] Duplicate timestamps in selected zone...")
dup_ts = df_zone['Timestamp'].duplicated().sum()
print(f"  Duplicate timestamps: {dup_ts}")
if dup_ts > 0:
    print("  (Will need deduplication before resampling)")

# ══════════════════════════════════════════════════════════════════════
# 4. ELECTRICITY LOAD vs HISTORICAL ELECTRICITY LOAD
# ══════════════════════════════════════════════════════════════════════
print("\n[4] Electricity Load vs Historical Electricity Load (kW)...")
load_col = [c for c in df.columns if c.strip().lower() == 'electricity load']
hist_col = [c for c in df.columns if 'historical' in c.lower() and 'load' in c.lower()]

load_col = load_col[0] if load_col else None
hist_col = hist_col[0] if hist_col else None
print(f"  Load column: '{load_col}'")
print(f"  Historical load column: '{hist_col}'")

if load_col and hist_col:
    load = df_zone[load_col]
    hist = df_zone[hist_col]
    
    identical = (load == hist).all()
    corr = load.corr(hist)
    mean_diff = (load - hist).abs().mean()
    
    print(f"  Are they identical? {identical}")
    print(f"  Correlation: {corr:.6f}")
    print(f"  Mean absolute difference: {mean_diff:.4f}")
    
    if not identical:
        print(f"  Load stats:       mean={load.mean():.2f}, std={load.std():.2f}, min={load.min():.2f}, max={load.max():.2f}")
        print(f"  Hist load stats:  mean={hist.mean():.2f}, std={hist.std():.2f}, min={hist.min():.2f}, max={hist.max():.2f}")
        
        # Check if hist is a lag of load
        df_sorted = df_zone.sort_values('Timestamp')
        for lag in [1, 2, 48, 336]:  # 30min, 1hr, 24hr, 1week
            shifted = df_sorted[load_col].shift(lag)
            match = (df_sorted[hist_col] == shifted).sum()
            total = shifted.notna().sum()
            print(f"    Matches load shifted by {lag} rows: {match}/{total} ({match/total*100:.1f}%)")

# ══════════════════════════════════════════════════════════════════════
# 5. MISSING VALUES
# ══════════════════════════════════════════════════════════════════════
print("\n[5] Missing values in selected zone...")
missing = df_zone.isnull().sum()
missing_pct = (missing / len(df_zone) * 100).round(2)
has_missing = missing[missing > 0]
if len(has_missing) > 0:
    print("  Columns with missing values:")
    for col_name in has_missing.index:
        print(f"    {col_name}: {has_missing[col_name]:,} ({missing_pct[col_name]:.2f}%)")
else:
    print("  No missing values!")

# ══════════════════════════════════════════════════════════════════════
# 6. RESAMPLE TO HOURLY
# ══════════════════════════════════════════════════════════════════════
print("\n[6] Resampling to hourly means...")
df_sorted = df_zone.sort_values('Timestamp').copy()
df_sorted = df_sorted.set_index('Timestamp')

# Keep only numeric columns for resampling + key columns
target = load_col
weather_cols = []
for c in df.columns:
    cl = c.lower()
    if 'temperature' in cl and 'c' in cl:
        weather_cols.append(c)
    elif 'humidity' in cl:
        weather_cols.append(c)
    elif 'cloud' in cl and 'cover' in cl:
        weather_cols.append(c)
    elif 'wind' in cl and 'speed' in cl:
        weather_cols.append(c)

print(f"  Weather columns found: {weather_cols}")
print(f"  Target column: {target}")

keep_cols = [target] + weather_cols
if hist_col:
    keep_cols.append(hist_col)
# Add Is Holiday
holiday_col = [c for c in df.columns if 'holiday' in c.lower()]
if holiday_col:
    keep_cols.append(holiday_col[0])
    print(f"  Holiday column: {holiday_col[0]}")

# Keep only columns that exist in df_sorted
keep_cols = [c for c in keep_cols if c in df_sorted.columns]

hourly = df_sorted[keep_cols].resample('1h').mean()
print(f"  Hourly shape: {hourly.shape}")
print(f"  Hourly date range: {hourly.index.min()} to {hourly.index.max()}")

# Check for gaps
full_range = pd.date_range(hourly.index.min(), hourly.index.max(), freq='1h')
missing_hours = full_range.difference(hourly.index)
print(f"  Missing hours in range: {len(missing_hours)}")

# Reindex to get all hours, then interpolate gaps <= 3 hours
hourly = hourly.reindex(full_range)
hourly.index.name = 'Timestamp'

# Interpolate gaps <= 3 hours
for col_name in hourly.columns:
    mask = hourly[col_name].isna()
    groups = mask.ne(mask.shift()).cumsum()
    gap_sizes = mask.groupby(groups).transform('sum')
    # Only fill gaps of at most 3 hours
    fillable = mask & (gap_sizes <= 3)
    hourly[col_name] = hourly[col_name].interpolate(method='linear')
    # Undo interpolation for gaps > 3 hours
    too_long = mask & (gap_sizes > 3)
    hourly.loc[too_long, col_name] = np.nan

remaining_missing = hourly[target].isna().sum()
total_hours = len(hourly)
print(f"  After interpolation (gaps ≤ 3h): {remaining_missing} missing target values ({remaining_missing/total_hours*100:.2f}%)")

# ══════════════════════════════════════════════════════════════════════
# 7. PATTERN ANALYSIS (is it realistic or synthetic?)
# ══════════════════════════════════════════════════════════════════════
print("\n[7] Pattern analysis (realistic vs synthetic?)...")

hourly_clean = hourly.dropna(subset=[target])

# Hour of day pattern
hourly_clean['hour'] = hourly_clean.index.hour
hourly_clean['dow'] = hourly_clean.index.dayofweek
hourly_clean['month'] = hourly_clean.index.month
hourly_clean['year'] = hourly_clean.index.year

print("\n  Average load by hour of day:")
by_hour = hourly_clean.groupby('hour')[target].mean()
for h, v in by_hour.items():
    bar = "█" * int(v / by_hour.max() * 40)
    print(f"    {h:2d}:00  {v:10.1f} kW  {bar}")

print("\n  Average load by day of week:")
dow_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
by_dow = hourly_clean.groupby('dow')[target].mean()
for d, v in by_dow.items():
    bar = "█" * int(v / by_dow.max() * 40)
    print(f"    {dow_names[d]}  {v:10.1f} kW  {bar}")

print("\n  Average load by month:")
by_month = hourly_clean.groupby('month')[target].mean()
month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
for m, v in by_month.items():
    bar = "█" * int(v / by_month.max() * 40)
    print(f"    {month_names[m-1]}  {v:10.1f} kW  {bar}")

# Temperature-load correlation
temp_col = [c for c in weather_cols if 'temp' in c.lower()][0] if any('temp' in c.lower() for c in weather_cols) else None
if temp_col:
    temp_load_corr = hourly_clean[target].corr(hourly_clean[temp_col])
    print(f"\n  Temperature-Load correlation: {temp_load_corr:.4f}")
    # In real energy data, this is usually U-shaped (heating in winter, cooling in summer)
    # A simple linear correlation may be low; let's check by season
    for season, months in [('Winter', [12,1,2]), ('Spring', [3,4,5]), ('Summer', [6,7,8]), ('Fall', [9,10,11])]:
        mask = hourly_clean['month'].isin(months)
        if mask.sum() > 0:
            sc = hourly_clean.loc[mask, target].corr(hourly_clean.loc[mask, temp_col])
            print(f"    {season}: {sc:.4f}")

# Check load range
load_min = hourly_clean[target].min()
load_max = hourly_clean[target].max()
load_mean = hourly_clean[target].mean()
load_std = hourly_clean[target].std()
print(f"\n  Load statistics:")
print(f"    Min: {load_min:.1f} kW")
print(f"    Max: {load_max:.1f} kW")
print(f"    Mean: {load_mean:.1f} kW")
print(f"    Std: {load_std:.1f} kW")
print(f"    CV: {load_std/load_mean:.3f}")

# Check for constant or near-constant stretches (synthetic indicator)
rolling_std = hourly_clean[target].rolling(24).std()
zero_variance = (rolling_std < 1.0).sum()
print(f"    24h rolling std near zero (<1): {zero_variance} periods ({zero_variance/len(hourly_clean)*100:.2f}%)")

# Autocorrelation at key lags
for lag in [1, 24, 168]:
    ac = hourly_clean[target].autocorr(lag)
    print(f"    Autocorrelation at lag {lag}h: {ac:.4f}")

print("\n  Verdict on realism: ", end="")
# Heuristics: real data has high autocorrelation, clear daily patterns, 
# temperature response, and no constant stretches
if temp_load_corr is not None and abs(temp_load_corr) > 0.15:
    print("Shows temperature response")
else:
    print("Weak temperature response (may be synthetic)")

# ══════════════════════════════════════════════════════════════════════
# 8. WEATHER CONSISTENCY (Open-Meteo comparison)
# ══════════════════════════════════════════════════════════════════════
print("\n[8] Weather consistency check with Open-Meteo...")

if lat is not None and lon is not None and temp_col:
    # We'll sample a subset to avoid huge API calls
    # Open-Meteo archive API allows up to ~1 year per request
    # Our data is Jan 2021 to Feb 2025 - ~4 years
    # Split into yearly requests
    
    start_date = hourly_clean.index.min().strftime('%Y-%m-%d')
    end_date = hourly_clean.index.max().strftime('%Y-%m-%d')
    
    print(f"  Fetching Open-Meteo archive data for ({lat}, {lon})")
    print(f"  Date range: {start_date} to {end_date}")
    
    # Fetch in yearly chunks
    all_meteo = []
    current_start = pd.Timestamp(start_date)
    final_end = pd.Timestamp(end_date)
    
    while current_start < final_end:
        chunk_end = min(current_start + pd.DateOffset(months=11, days=28), final_end)
        url = (
            f"https://archive-api.open-meteo.com/v1/archive?"
            f"latitude={lat}&longitude={lon}"
            f"&start_date={current_start.strftime('%Y-%m-%d')}"
            f"&end_date={chunk_end.strftime('%Y-%m-%d')}"
            f"&hourly=temperature_2m,relative_humidity_2m,cloud_cover,wind_speed_10m"
            f"&wind_speed_unit=ms"
            f"&timezone=America/New_York"
        )
        print(f"    Fetching {current_start.strftime('%Y-%m-%d')} to {chunk_end.strftime('%Y-%m-%d')}...", end=" ")
        try:
            resp = requests.get(url, timeout=30)
            data = resp.json()
            if 'hourly' in data:
                chunk_df = pd.DataFrame({
                    'time': pd.to_datetime(data['hourly']['time']),
                    'meteo_temp': data['hourly']['temperature_2m'],
                    'meteo_humidity': data['hourly']['relative_humidity_2m'],
                    'meteo_cloud': data['hourly']['cloud_cover'],
                    'meteo_wind': data['hourly']['wind_speed_10m'],
                })
                all_meteo.append(chunk_df)
                print(f"OK ({len(chunk_df)} rows)")
            else:
                print(f"No hourly data: {data.get('reason', 'unknown')}")
        except Exception as e:
            print(f"Error: {e}")
        
        current_start = chunk_end + pd.Timedelta(days=1)
    
    if all_meteo:
        meteo = pd.concat(all_meteo).set_index('time')
        meteo = meteo[~meteo.index.duplicated(keep='first')]
        print(f"\n  Open-Meteo data: {len(meteo)} hourly records")
        
        # Align with our hourly data
        common_idx = hourly_clean.index.intersection(meteo.index)
        print(f"  Common timestamps: {len(common_idx)}")
        
        if len(common_idx) > 100:
            hc = hourly_clean.loc[common_idx]
            mc = meteo.loc[common_idx]
            
            # Find matching weather columns
            humidity_col = [c for c in weather_cols if 'humid' in c.lower()][0] if any('humid' in c.lower() for c in weather_cols) else None
            cloud_col = [c for c in weather_cols if 'cloud' in c.lower()][0] if any('cloud' in c.lower() for c in weather_cols) else None
            wind_col = [c for c in weather_cols if 'wind' in c.lower()][0] if any('wind' in c.lower() for c in weather_cols) else None
            
            comparisons = []
            if temp_col:
                corr = hc[temp_col].corr(mc['meteo_temp'])
                me = (hc[temp_col] - mc['meteo_temp']).mean()
                mae = (hc[temp_col] - mc['meteo_temp']).abs().mean()
                comparisons.append(('Temperature', temp_col, corr, me, mae))
            if humidity_col:
                corr = hc[humidity_col].corr(mc['meteo_humidity'])
                me = (hc[humidity_col] - mc['meteo_humidity']).mean()
                mae = (hc[humidity_col] - mc['meteo_humidity']).abs().mean()
                comparisons.append(('Humidity', humidity_col, corr, me, mae))
            if cloud_col:
                corr = hc[cloud_col].corr(mc['meteo_cloud'])
                me = (hc[cloud_col] - mc['meteo_cloud']).mean()
                mae = (hc[cloud_col] - mc['meteo_cloud']).abs().mean()
                comparisons.append(('Cloud Cover', cloud_col, corr, me, mae))
            if wind_col:
                corr = hc[wind_col].corr(mc['meteo_wind'])
                me = (hc[wind_col] - mc['meteo_wind']).mean()
                mae = (hc[wind_col] - mc['meteo_wind']).abs().mean()
                comparisons.append(('Wind Speed', wind_col, corr, me, mae))
            
            print("\n  Weather comparison (dataset vs Open-Meteo):")
            print(f"  {'Variable':<15} {'Column':<30} {'Correlation':>12} {'Mean Error':>12} {'MAE':>10}")
            print("  " + "-" * 85)
            
            weather_decision = "keep_dataset"  # default
            
            for name, col_name, corr, me, mae in comparisons:
                print(f"  {name:<15} {col_name:<30} {corr:>12.4f} {me:>12.2f} {mae:>10.2f}")
                if name == 'Temperature' and corr < 0.9:
                    weather_decision = "use_openmeteo"
            
            print(f"\n  DECISION: ", end="")
            if weather_decision == "keep_dataset":
                print("KEEP dataset weather (temperature correlation >= 0.9)")
            else:
                print("USE Open-Meteo weather (temperature correlation < 0.9)")
            
            # Save Open-Meteo data for potential use
            meteo_out = os.path.join(BACKEND_DIR, "data", "raw", "openmeteo_weather.csv")
            meteo.to_csv(meteo_out)
            print(f"  Saved Open-Meteo data to {meteo_out}")
            
            # Store decision
            decision_info = {
                'weather_decision': weather_decision,
                'temperature_correlation': float(comparisons[0][2]) if comparisons else None,
                'comparisons': [
                    {'variable': name, 'correlation': float(corr), 'mean_error': float(me), 'mae': float(mae)}
                    for name, _, corr, me, mae in comparisons
                ],
                'zone': str(biggest_zone) if zone_col else 'all',
                'zone_column': zone_col,
                'zone_rows': int(len(df_zone)),
                'lat': float(lat),
                'lon': float(lon),
                'target_col': target,
                'temp_col': temp_col,
                'humidity_col': humidity_col,
                'cloud_col': cloud_col,
                'wind_col': wind_col,
                'holiday_col': holiday_col[0] if holiday_col else None,
                'hist_load_col': hist_col,
                'hourly_shape': list(hourly.shape),
                'date_range': [str(hourly.index.min()), str(hourly.index.max())],
            }
            decision_out = os.path.join(SCRIPT_DIR, "audit_decision.json")
            with open(decision_out, 'w') as f:
                json.dump(decision_info, f, indent=2)
            print(f"  Saved audit decisions to {decision_out}")

# ══════════════════════════════════════════════════════════════════════
# 9. SAVE REPORT
# ══════════════════════════════════════════════════════════════════════
print("\n[9] Writing data_report.md...")

# Collect all findings for the report
report_lines = [
    "# GridCast Data Audit Report",
    f"\n**Generated:** {datetime.now().isoformat()}",
    f"\n## 1. Dataset Overview",
    f"- **File:** smart_city_energy_dataset.csv",
    f"- **Shape:** {df.shape[0]:,} rows × {df.shape[1]} columns",
    f"- **Date range:** {df['Timestamp'].min()} to {df['Timestamp'].max()}",
    f"- **Time interval:** {diffs.mode().iloc[0]} (most common)",
    f"- **Columns:** {', '.join(df.columns[:10])}... ({len(df.columns)} total)",
    f"\n## 2. Zone Analysis",
]

if zone_col:
    report_lines.append(f"- **Zone column:** `{zone_col}`")
    report_lines.append(f"- **Number of unique zones:** {df[zone_col].nunique()}")
    report_lines.append(f"- **Selected zone:** `{biggest_zone}` ({biggest_count:,} rows, {biggest_count/len(df)*100:.1f}%)")
    if lat is not None:
        report_lines.append(f"- **Location:** ({lat}, {lon})")

report_lines.extend([
    f"\n## 3. Target Column Analysis",
    f"- **Target:** `{target}` (Electricity Load)",
    f"- **Historical Load column:** `{hist_col}`",
])

if load_col and hist_col:
    report_lines.append(f"- **Identical?** {'Yes' if identical else 'No'}")
    report_lines.append(f"- **Correlation:** {corr:.6f}")
    report_lines.append(f"- **Mean absolute difference:** {mean_diff:.4f}")

report_lines.extend([
    f"\n## 4. Hourly Resampling",
    f"- **Hourly records:** {len(hourly):,}",
    f"- **Interpolated gaps ≤ 3h:** Yes",
    f"- **Remaining missing target values:** {remaining_missing} ({remaining_missing/total_hours*100:.2f}%)",
    f"\n## 5. Pattern Analysis",
    f"- **Load range:** {load_min:.1f} – {load_max:.1f} kW",
    f"- **Mean ± Std:** {load_mean:.1f} ± {load_std:.1f} kW",
    f"- **CV:** {load_std/load_mean:.3f}",
])

if temp_col:
    report_lines.append(f"- **Temperature-Load correlation:** {temp_load_corr:.4f}")

report_lines.extend([
    f"\n## 6. Weather Consistency Check",
])

if all_meteo and comparisons:
    report_lines.append(f"\n| Variable | Correlation | Mean Error | MAE |")
    report_lines.append(f"|----------|------------|-----------|-----|")
    for name, _, c, me, mae in comparisons:
        report_lines.append(f"| {name} | {c:.4f} | {me:.2f} | {mae:.2f} |")
    report_lines.append(f"\n**Decision:** {'Keep dataset weather' if weather_decision == 'keep_dataset' else 'Use Open-Meteo weather'}")

report_lines.extend([
    f"\n## 7. Columns Available",
    f"\n| Column | Dtype | Non-null | Sample Values |",
    f"|--------|-------|----------|---------------|",
])

for col_name in df_zone.columns[:30]:
    non_null = df_zone[col_name].notna().sum()
    sample = str(df_zone[col_name].dropna().iloc[:3].tolist())[:50]
    report_lines.append(f"| {col_name} | {df_zone[col_name].dtype} | {non_null:,} | {sample} |")

report = "\n".join(report_lines)
with open(REPORT_PATH, 'w') as f:
    f.write(report)

print(f"  Report saved to {REPORT_PATH}")
print("\n" + "=" * 70)
print("STAGE 1 COMPLETE. Waiting for 'continue' before Stage 2.")
print("=" * 70)
