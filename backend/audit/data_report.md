# GridCast Data Audit Report

**Generated:** 2026-10-03

## 1. Dataset Overview

- **File:** smart_city_energy_dataset.csv
- **Shape:** 72,960 rows x 60 columns
- **Time resolution:** 30-minute intervals (uniform, no gaps in raw timestamps)
- **Date range:** 2021-01-01 00:00 to 2025-02-28 23:30
- **Duration:** 1,519 days (~4.2 years)
- **Source:** ISONE Smart City Energy Dataset (Kaggle)

## 2. Zone Analysis

The dataset has two zone columns:

| Column | Unique Values | Distribution |
|--------|--------------|--------------|
| Region/Zone ID | 3 | ZoneA: 43,957 (60.2%), ZoneB: 21,779 (29.9%), ZoneC: 7,224 (9.9%) |
| Substation ID / Region ID | 4 | R1: 36,386 (49.9%), R2: 22,074 (30.3%), R3: 10,785 (14.8%), R4: 3,715 (5.1%) |

**Selected zone: ZoneA** (Region/Zone ID) -- the zone with the most rows (43,957 = 60.2%).

- **Location:** Latitude 35.01, Longitude -105.52 (near Santa Fe, NM)

## 3. Electricity Load vs Historical Electricity Load

| Metric | Value |
|--------|-------|
| Identical? | No |
| Correlation | 0.9971 |
| Mean absolute difference | 15.93 kW |
| Load mean/std | 449.63 / 261.66 kW |
| Historical Load mean/std | 449.68 / 260.76 kW |

**Finding:** Historical Electricity Load is NOT a lagged copy of Electricity Load (checked shifts of 1, 2, 48, 336 rows -- 0% match). It appears to be a slightly noisy duplicate or an independent estimate. Per the anti-leakage rules, Historical Electricity Load (kW) is excluded from model inputs.

## 4. Hourly Resampling

- **Hourly records after resampling:** 36,480
- **Gaps interpolated (<=3h):** Yes
- **Remaining missing target values:** 87 (0.24%)

## 5. Pattern Analysis -- Realism Assessment

### 5a. Daily Pattern
Load by hour of day is essentially **flat** (range: 437-460 kW, variation ~5%). Real electricity data shows clear morning ramp and evening peak (variation ~30-50%).

### 5b. Weekly Pattern
Weekday vs weekend variation: ~3%. Real data typically shows 10-20% weekday/weekend difference.

### 5c. Seasonal/Monthly Pattern
Monthly range: 444-462 kW (~4% variation). Real ISO-NE data shows strong seasonal swings (summer cooling, winter heating).

### 5d. Temperature-Load Correlation
- Dataset temperature vs load: **-0.001** (essentially zero)
- Open-Meteo real temperature vs load: **0.007** (essentially zero)
- In real energy systems, this correlation is typically 0.3-0.8.

### 5e. Autocorrelation
| Lag | Value |
|-----|-------|
| 1 hour | 0.163 |
| 24 hours | -0.0001 |
| 168 hours (1 week) | 0.007 |

Real load data has autocorrelation ~0.95 at 1h, ~0.85 at 24h. This data has near-zero day-to-day correlation.

### 5f. Load Range
- Min: -23.8 kW (negative load is unrealistic for system demand)
- Max: 2,351.7 kW
- CV (coefficient of variation): 0.492 (high noise relative to mean)

### **Verdict: The dataset is SYNTHETIC / randomly generated.**
The load values appear to be random noise around ~450 kW, with no meaningful temporal, seasonal, or weather-driven patterns. This is confirmed by:
1. No daily pattern (flat across hours)
2. No weekly pattern (flat across days)
3. No seasonal pattern (flat across months)
4. Zero temperature-load correlation
5. Near-zero autocorrelation beyond 1 hour
6. Negative load values

**Impact on the project:** The ML models will have genuinely low signal to learn from. Model MAPE will be high because the data is essentially random noise. This is not a model quality issue -- it reflects the nature of the data. The app will still work correctly, but predictions will essentially show the mean with wide confidence bands.

## 6. Weather Consistency Check

Compared dataset weather columns to real Open-Meteo archive data for the same location (35.01, -105.52):

| Variable | Correlation | Mean Error | MAE |
|----------|------------|-----------|-----|
| Temperature | 0.0057 | 8.72 C | 12.76 C |
| Humidity | -0.0020 | - | - |
| Cloud Cover | -0.0112 | - | - |
| Wind Speed | -0.0002 | - | - |

**All correlations are near zero.** The dataset's weather columns are completely uncorrelated with real weather at the stated coordinates.

**DECISION: TRAIN ON Open-Meteo historical weather.**
- Reason: Temperature correlation = 0.006 (far below the 0.9 threshold)
- Training and live prediction will both use the same Open-Meteo weather source
- This ensures consistency even though the load itself is synthetic

## 7. Key Columns for Modeling

### Allowed inputs (per anti-leakage rules):
- Calendar: hour, day of week, month, is_weekend, Is Holiday, cyclic sin/cos
- Weather: Temperature, Humidity, Cloud Cover, Wind Speed (from Open-Meteo)
- Lagged load: only lags >= 24 hours older than the predicted hour

### Excluded (same-time measurements):
Net Load, Renewable Energy Load, Curtailment Risk, Peak Load Indicator, Time Since Last Peak, Time Until Next Predicted Peak, Voltage, Current, Power Factor, Transformer Load Level, Smart Meter Reading, EV Charging, Public Transit, Battery columns, Demand Response Signal, Historical Electricity Load, Solar PV Output, Wind Power Output, Solar Panel Temperature, Grid Frequency, etc.

## 8. Decisions Summary

| Decision | Choice | Reason |
|----------|--------|--------|
| Zone | ZoneA (Region/Zone ID) | Most rows (60.2%) |
| Target | Electricity Load | As specified |
| Weather source for training | Open-Meteo archive | Dataset weather uncorrelated with reality (r=0.006) |
| Resampling | Hourly means | As specified |
| Historical Load column | Excluded | Not a lag; nearly identical duplicate |
