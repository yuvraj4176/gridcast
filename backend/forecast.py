# -*- coding: utf-8 -*-
"""
Core forecast logic for GridCast.
Handles mode selection, feature building, prediction, and confidence bands.
"""
import json
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from features import build_features, FEATURE_COLS_SHORT, FEATURE_COLS_LONG
from holidays_util import is_holiday, get_holiday_name

logger = logging.getLogger(__name__)


def select_mode(start_date, days, hourly_df):
    """
    Select the forecast mode based on the request parameters.

    SHORT-TERM (Model A): when history exists up to the origin,
      the origin is within the dataset range, at least 8 days after
      dataset start (so lags exist), and days <= 14.
    LONG-TERM (Model B): otherwise.

    Returns: (mode, reason)
    """
    origin = pd.Timestamp(start_date)
    dataset_start = hourly_df.index.min()
    dataset_end = hourly_df.index.max()

    # Check if origin is within dataset range with enough lag history
    has_history = (
        origin >= dataset_start + timedelta(days=8)
        and origin <= dataset_end + timedelta(days=1)
    )

    if has_history and days <= 14:
        return "short_term", (
            "Recent load data is available for this date, enabling "
            "high-accuracy forecasting with lag features."
        )
    elif not has_history:
        return "long_term", (
            f"Start date is outside the dataset range "
            f"({dataset_start.strftime('%Y-%m-%d')} to {dataset_end.strftime('%Y-%m-%d')}), "
            "so lag features are unavailable. Using calendar + weather model."
        )
    else:
        return "long_term", (
            f"Forecast period of {days} days exceeds the 14-day limit for "
            "short-term mode. Using calendar + weather model for longer horizons."
        )


def generate_forecast(
    start_date,
    days,
    resolution,
    temp_change,
    model_short,
    model_long,
    residual_quantiles,
    hourly_df,
    weather_df,
    weather_source,
    weather_warnings,
):
    """
    Generate a full forecast response.

    Parameters
    ----------
    start_date : date
    days : int
    resolution : str, "hourly" or "daily"
    temp_change : float
    model_short : fitted model for short-term
    model_long : fitted model for long-term
    residual_quantiles : dict with quantiles by hour
    hourly_df : DataFrame with historical hourly load data
    weather_df : DataFrame with weather for forecast period
    weather_source : str, source label
    weather_warnings : list of warning strings

    Returns
    -------
    dict matching the ForecastResponse schema
    """
    origin = pd.Timestamp(start_date)
    end = origin + timedelta(days=days)
    hours = pd.date_range(origin, end - timedelta(hours=1), freq="1h")

    # Select mode
    mode, mode_reason = select_mode(start_date, days, hourly_df)
    warnings = list(weather_warnings)

    if mode == "long_term":
        warnings.append(
            "Long-range forecasts show typical patterns, not exact values. "
            "Use this view for planning scenarios rather than hour-by-hour operations."
        )

    # Build the prediction DataFrame
    pred_df = pd.DataFrame(index=hours)
    pred_df.index.name = "Timestamp"

    # Add weather (with temp_change applied)
    for ts in pred_df.index:
        if ts in weather_df.index:
            pred_df.loc[ts, "temperature"] = weather_df.loc[ts, "temperature"] + temp_change
            pred_df.loc[ts, "humidity"] = weather_df.loc[ts, "humidity"]
            pred_df.loc[ts, "cloud_cover"] = weather_df.loc[ts, "cloud_cover"]
            pred_df.loc[ts, "wind_speed"] = weather_df.loc[ts, "wind_speed"]
        else:
            # This shouldn't happen since weather.py fills all gaps
            pred_df.loc[ts, "temperature"] = 15.0 + temp_change
            pred_df.loc[ts, "humidity"] = 50.0
            pred_df.loc[ts, "cloud_cover"] = 50.0
            pred_df.loc[ts, "wind_speed"] = 5.0

    # Add holidays
    pred_df["is_holiday"] = [1 if is_holiday(ts.date()) else 0 for ts in pred_df.index]

    # Convert to numeric
    for col in ["temperature", "humidity", "cloud_cover", "wind_speed"]:
        pred_df[col] = pd.to_numeric(pred_df[col], errors="coerce").fillna(15.0 if col == "temperature" else 50.0)

    # ── Short-term mode: recursive prediction with lag features ──
    if mode == "short_term":
        # Initialize load column with historical data for lags
        # We need at least 168 hours before the origin
        lag_start = origin - timedelta(hours=168)
        hist_range = pd.date_range(lag_start, origin - timedelta(hours=1), freq="1h")

        # Combine history + forecast period
        full_df = pd.DataFrame(index=hist_range.union(hours))
        full_df.index.name = "Timestamp"

        # Fill historical load
        for ts in hist_range:
            if ts in hourly_df.index:
                full_df.loc[ts, "load"] = hourly_df.loc[ts, "load"]
            else:
                full_df.loc[ts, "load"] = np.nan

        # Fill weather and holidays for full range
        for ts in full_df.index:
            if ts in pred_df.index:
                full_df.loc[ts, "temperature"] = pred_df.loc[ts, "temperature"]
                full_df.loc[ts, "humidity"] = pred_df.loc[ts, "humidity"]
                full_df.loc[ts, "cloud_cover"] = pred_df.loc[ts, "cloud_cover"]
                full_df.loc[ts, "wind_speed"] = pred_df.loc[ts, "wind_speed"]
                full_df.loc[ts, "is_holiday"] = pred_df.loc[ts, "is_holiday"]
            elif ts in hourly_df.index:
                full_df.loc[ts, "temperature"] = hourly_df.loc[ts, "temperature"]
                full_df.loc[ts, "humidity"] = hourly_df.loc[ts, "humidity"]
                full_df.loc[ts, "cloud_cover"] = hourly_df.loc[ts, "cloud_cover"]
                full_df.loc[ts, "wind_speed"] = hourly_df.loc[ts, "wind_speed"]
                full_df.loc[ts, "is_holiday"] = hourly_df.loc[ts, "is_holiday"]
            else:
                full_df.loc[ts, "temperature"] = 15.0
                full_df.loc[ts, "humidity"] = 50.0
                full_df.loc[ts, "cloud_cover"] = 50.0
                full_df.loc[ts, "wind_speed"] = 5.0
                full_df.loc[ts, "is_holiday"] = 1 if is_holiday(ts.date()) else 0

        # Convert to numeric
        for col in full_df.columns:
            full_df[col] = pd.to_numeric(full_df[col], errors="coerce")

        # Interpolate missing historical load
        full_df["load"] = full_df["load"].interpolate(method="linear", limit=3)

        # Recursive prediction: day by day
        for ts in hours:
            # Build features for this single row
            # We need lag_24 and lag_168
            lag_24_ts = ts - timedelta(hours=24)
            lag_168_ts = ts - timedelta(hours=168)

            lag_24 = full_df.loc[lag_24_ts, "load"] if lag_24_ts in full_df.index else np.nan
            lag_168 = full_df.loc[lag_168_ts, "load"] if lag_168_ts in full_df.index else np.nan

            # If lags are missing, use mean load
            mean_load = hourly_df["load"].mean()
            if pd.isna(lag_24):
                lag_24 = mean_load
            if pd.isna(lag_168):
                lag_168 = mean_load

            # Build feature vector
            hour = ts.hour
            day_of_week = ts.dayofweek
            month = ts.month
            is_wknd = 1 if day_of_week >= 5 else 0
            hol = int(full_df.loc[ts, "is_holiday"]) if ts in full_df.index else 0

            features = [
                hour, day_of_week, month, is_wknd, hol,
                np.sin(2 * np.pi * hour / 24),
                np.cos(2 * np.pi * hour / 24),
                np.sin(2 * np.pi * month / 12),
                np.cos(2 * np.pi * month / 12),
                float(full_df.loc[ts, "temperature"]),
                float(full_df.loc[ts, "humidity"]),
                float(full_df.loc[ts, "cloud_cover"]),
                float(full_df.loc[ts, "wind_speed"]),
                lag_24, lag_168,
            ]

            pred = model_short.predict([features])[0]
            full_df.loc[ts, "load"] = pred  # Store for future lags

        # Extract predictions for the forecast period
        predictions = full_df.loc[hours, "load"].values.astype(float)

    # ── Long-term mode: direct prediction (no lags) ──
    else:
        feat_df = build_features(pred_df, include_lags=False)
        # Ensure load column exists (needed by build_features but won't be used)
        if "load" not in pred_df.columns:
            feat_df["load"] = 0  # placeholder, not used
        X = feat_df[FEATURE_COLS_LONG].values
        predictions = model_long.predict(X)

    # ── Confidence bands ──
    quantiles = residual_quantiles.get(mode, residual_quantiles.get("short_term", {}))
    lower = np.zeros(len(predictions))
    upper = np.zeros(len(predictions))

    for i, ts in enumerate(hours):
        h = str(ts.hour)
        q = quantiles.get(h, {"q10": -200, "q90": 200})

        # Widen bands for later days in the forecast
        days_ahead = (ts - origin).total_seconds() / 86400
        # Widening factor: starts at 1.0 for day 0, increases by 5% per day
        widen = 1.0 + 0.05 * days_ahead

        lower[i] = predictions[i] + q["q10"] * widen
        upper[i] = predictions[i] + q["q90"] * widen

    # Clamp to non-negative
    predictions = np.maximum(predictions, 0)
    lower = np.maximum(lower, 0)

    # ── Get actuals (if available) ──
    actuals = []
    for ts in hours:
        if ts in hourly_df.index and not pd.isna(hourly_df.loc[ts, "load"]):
            # Only include actuals that are after the origin (comparison data)
            actuals.append(float(hourly_df.loc[ts, "load"]))
        else:
            actuals.append(None)

    # ── Build series ──
    series = []
    for i, ts in enumerate(hours):
        point = {
            "time": ts.isoformat(),
            "load": round(float(predictions[i]), 2),
            "lower": round(float(lower[i]), 2),
            "upper": round(float(upper[i]), 2),
            "temp": round(float(pred_df.loc[ts, "temperature"]), 1) if ts in pred_df.index else None,
            "humidity": round(float(pred_df.loc[ts, "humidity"]), 1) if ts in pred_df.index else None,
            "cloud_cover": round(float(pred_df.loc[ts, "cloud_cover"]), 1) if ts in pred_df.index else None,
            "wind_speed": round(float(pred_df.loc[ts, "wind_speed"]), 1) if ts in pred_df.index else None,
            "holiday": is_holiday(ts.date()),
            "holiday_name": get_holiday_name(ts.date()),
            "actual": actuals[i],
        }
        series.append(point)

    # ── Daily aggregation if requested ──
    if resolution == "daily":
        daily_series = []
        day_groups = {}
        for pt in series:
            day = pt["time"][:10]
            if day not in day_groups:
                day_groups[day] = []
            day_groups[day].append(pt)

        for day, points in day_groups.items():
            loads = [p["load"] for p in points]
            lowers = [p["lower"] for p in points]
            uppers = [p["upper"] for p in points]
            temps = [p["temp"] for p in points if p["temp"] is not None]
            humids = [p["humidity"] for p in points if p["humidity"] is not None]
            clouds = [p["cloud_cover"] for p in points if p["cloud_cover"] is not None]
            winds = [p["wind_speed"] for p in points if p["wind_speed"] is not None]
            acts = [p["actual"] for p in points if p["actual"] is not None]
            hol = any(p["holiday"] for p in points)
            hol_name = next((p["holiday_name"] for p in points if p["holiday_name"]), None)

            daily_series.append({
                "time": day,
                "load": round(np.mean(loads), 2),
                "lower": round(np.mean(lowers), 2),
                "upper": round(np.mean(uppers), 2),
                "temp": round(np.mean(temps), 1) if temps else None,
                "humidity": round(np.mean(humids), 1) if humids else None,
                "cloud_cover": round(np.mean(clouds), 1) if clouds else None,
                "wind_speed": round(np.mean(winds), 1) if winds else None,
                "holiday": hol,
                "holiday_name": hol_name,
                "actual": round(np.mean(acts), 2) if acts else None,
            })
        series = daily_series

    # ── Summary ──
    loads = [p["load"] for p in series]
    peak_idx = np.argmax(loads)
    lowest_idx = np.argmin(loads)
    avg_load = np.mean(loads)

    # Total energy in MWh
    if resolution == "hourly":
        total_mwh = sum(loads) / 1000  # kW * 1h / 1000 = MWh
    else:
        # Daily: each point is average kW for that day
        total_mwh = sum(l * 24 for l in loads) / 1000

    # vs period average: compare to the historical average for same month range
    hist_months = set()
    for ts in hours:
        hist_months.add(ts.month)
    hist_avg = hourly_df[hourly_df.index.month.isin(hist_months)]["load"].mean()
    if hist_avg > 0 and not pd.isna(hist_avg):
        vs_pct = round((avg_load - hist_avg) / hist_avg * 100, 1)
    else:
        vs_pct = None

    summary = {
        "peak": round(loads[peak_idx], 2),
        "peak_time": series[peak_idx]["time"],
        "lowest": round(loads[lowest_idx], 2),
        "lowest_time": series[lowest_idx]["time"],
        "average": round(avg_load, 2),
        "total_mwh": round(total_mwh, 2),
        "vs_period_average_pct": vs_pct,
    }

    # ── Daily pattern (average by hour of day) ──
    if resolution == "hourly":
        hourly_loads = {}
        for pt in series:
            h = int(pt["time"][11:13])
            if h not in hourly_loads:
                hourly_loads[h] = []
            hourly_loads[h].append(pt["load"])
        daily_pattern = [
            {"hour": h, "avg_load": round(np.mean(hourly_loads.get(h, [0])), 2)}
            for h in range(24)
        ]
    else:
        # For daily resolution, compute from the hourly predictions
        # (we still have hourly internally)
        daily_pattern = [{"hour": h, "avg_load": round(avg_load, 2)} for h in range(24)]

    # ── Insights ──
    insights = _generate_insights(series, summary, mode, temp_change, hours)

    return {
        "mode": mode,
        "mode_reason": mode_reason,
        "weather_source": weather_source,
        "warnings": warnings,
        "summary": summary,
        "series": series,
        "daily_pattern": daily_pattern,
        "insights": insights,
        "generated_at": datetime.now().isoformat(),
    }


def _generate_insights(series, summary, mode, temp_change, hours):
    """Generate human-readable insights from the forecast."""
    insights = []

    # Peak insight
    peak_time = pd.Timestamp(summary["peak_time"])
    day_name = peak_time.strftime("%A")
    if "T" in summary["peak_time"]:
        time_str = peak_time.strftime("%I %p").lstrip("0")
        insights.append(f"Peak demand of {summary['peak']:.0f} kW expected on {day_name} at {time_str}.")
    else:
        insights.append(f"Peak average demand of {summary['peak']:.0f} kW expected on {day_name}.")

    # vs period average
    if summary.get("vs_period_average_pct") is not None:
        pct = summary["vs_period_average_pct"]
        direction = "above" if pct > 0 else "below"
        insights.append(
            f"Average demand is {abs(pct):.1f}% {direction} the historical average for this period."
        )

    # Holiday insight
    holidays = [s for s in series if s.get("holiday")]
    if holidays:
        hol_name = holidays[0].get("holiday_name", "a holiday")
        insights.append(f"Holiday ({hol_name}) detected in the forecast period, which may affect demand patterns.")

    # Temperature change insight
    if temp_change != 0:
        direction = "increase" if temp_change > 0 else "decrease"
        insights.append(
            f"Temperature adjustment of {temp_change:+.0f}\u00b0C applied. "
            f"This simulates a what-if scenario for demand sensitivity."
        )

    # Mode insight
    if mode == "long_term":
        insights.append(
            "This forecast uses typical calendar and weather patterns. "
            "Actual outcomes will vary from these estimates."
        )

    return insights
