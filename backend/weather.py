# -*- coding: utf-8 -*-
"""
Weather data fetching for GridCast.
Fetches from Open-Meteo archive and forecast APIs, with typical-weather fallback.

Weather sources (in priority order):
1. Open-Meteo archive API for past dates
2. Open-Meteo forecast API for dates up to ~16 days ahead
3. typical_weather.csv (by month and hour) as fallback
"""
import os
import logging
import requests
import pandas as pd
from datetime import date, datetime, timedelta

logger = logging.getLogger(__name__)

# Zone location (from audit)
LATITUDE = 35.00984180463772
LONGITUDE = -105.51861709741044
TIMEZONE = "America/New_York"

# API URLs (can be overridden by environment variables)
ARCHIVE_API = os.getenv("OPENMETEO_ARCHIVE_URL", "https://archive-api.open-meteo.com/v1/archive")
FORECAST_API = os.getenv("OPENMETEO_FORECAST_URL", "https://api.open-meteo.com/v1/forecast")
API_TIMEOUT = int(os.getenv("OPENMETEO_TIMEOUT", "15"))  # seconds


def load_typical_weather(path: str) -> pd.DataFrame:
    """Load the typical weather CSV (mean by month and hour from training)."""
    return pd.read_csv(path)


def get_typical_weather(typical_df: pd.DataFrame, month: int, hour: int) -> dict:
    """Get typical weather for a given month and hour."""
    row = typical_df[(typical_df["month"] == month) & (typical_df["hour"] == hour)]
    if len(row) > 0:
        r = row.iloc[0]
        return {
            "temperature": float(r["temperature"]),
            "humidity": float(r["humidity"]),
            "cloud_cover": float(r["cloud_cover"]),
            "wind_speed": float(r["wind_speed"]),
        }
    # Fallback to monthly mean if exact hour not found
    month_rows = typical_df[typical_df["month"] == month]
    if len(month_rows) > 0:
        return {
            "temperature": float(month_rows["temperature"].mean()),
            "humidity": float(month_rows["humidity"].mean()),
            "cloud_cover": float(month_rows["cloud_cover"].mean()),
            "wind_speed": float(month_rows["wind_speed"].mean()),
        }
    return {"temperature": 15.0, "humidity": 50.0, "cloud_cover": 50.0, "wind_speed": 5.0}


def fetch_archive_weather(start_date: date, end_date: date) -> pd.DataFrame | None:
    """
    Fetch historical weather from Open-Meteo archive API.
    Returns a DataFrame with hourly data, or None on failure.
    """
    try:
        params = {
            "latitude": LATITUDE,
            "longitude": LONGITUDE,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "hourly": "temperature_2m,relative_humidity_2m,cloud_cover,wind_speed_10m",
            "wind_speed_unit": "ms",
            "timezone": TIMEZONE,
        }
        resp = requests.get(ARCHIVE_API, params=params, timeout=API_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        if "hourly" not in data:
            logger.warning(f"Archive API returned no hourly data: {data.get('reason', 'unknown')}")
            return None

        df = pd.DataFrame({
            "time": pd.to_datetime(data["hourly"]["time"]),
            "temperature": data["hourly"]["temperature_2m"],
            "humidity": data["hourly"]["relative_humidity_2m"],
            "cloud_cover": data["hourly"]["cloud_cover"],
            "wind_speed": data["hourly"]["wind_speed_10m"],
        })
        return df.set_index("time")

    except Exception as e:
        logger.warning(f"Archive API error: {e}")
        return None


def fetch_forecast_weather(start_date: date, end_date: date) -> pd.DataFrame | None:
    """
    Fetch forecast weather from Open-Meteo forecast API.
    Available for dates up to ~16 days ahead.
    Returns a DataFrame with hourly data, or None on failure.
    """
    try:
        # Forecast API uses forecast_days or specific date range
        days_ahead = (end_date - date.today()).days + 1
        if days_ahead > 16:
            end_date = date.today() + timedelta(days=15)

        params = {
            "latitude": LATITUDE,
            "longitude": LONGITUDE,
            "hourly": "temperature_2m,relative_humidity_2m,cloud_cover,wind_speed_10m",
            "wind_speed_unit": "ms",
            "timezone": TIMEZONE,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }
        resp = requests.get(FORECAST_API, params=params, timeout=API_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        if "hourly" not in data:
            logger.warning(f"Forecast API returned no hourly data")
            return None

        df = pd.DataFrame({
            "time": pd.to_datetime(data["hourly"]["time"]),
            "temperature": data["hourly"]["temperature_2m"],
            "humidity": data["hourly"]["relative_humidity_2m"],
            "cloud_cover": data["hourly"]["cloud_cover"],
            "wind_speed": data["hourly"]["wind_speed_10m"],
        })
        return df.set_index("time")

    except Exception as e:
        logger.warning(f"Forecast API error: {e}")
        return None


def get_weather_for_range(
    start: datetime,
    end: datetime,
    typical_df: pd.DataFrame,
) -> tuple[pd.DataFrame, str, list[str]]:
    """
    Get weather data for a datetime range, using the best available source.

    Returns:
        (weather_df, source_label, warnings)
        weather_df: DataFrame indexed by hourly timestamps with columns:
                    temperature, humidity, cloud_cover, wind_speed
        source_label: "archive_api", "forecast_api", "typical", "mixed"
        warnings: list of warning messages
    """
    hours = pd.date_range(start, end, freq="1h")
    result = pd.DataFrame(index=hours, columns=["temperature", "humidity", "cloud_cover", "wind_speed"])
    result.index.name = "time"

    today = datetime.now().date()
    warnings = []
    sources_used = set()

    # Split the range into: past, near-future (<= 16 days), far-future
    past_end = min(end.date(), today - timedelta(days=1))
    forecast_end = min(end.date(), today + timedelta(days=15))

    # 1. Fetch archive data for past dates
    if start.date() <= past_end:
        logger.info(f"Fetching archive weather: {start.date()} to {past_end}")
        archive = fetch_archive_weather(start.date(), past_end)
        if archive is not None:
            common = result.index.intersection(archive.index)
            if len(common) > 0:
                result.loc[common] = archive.loc[common]
                sources_used.add("archive_api")

    # 2. Fetch forecast data for near-future dates
    forecast_start = max(start.date(), today)
    if forecast_start <= forecast_end:
        logger.info(f"Fetching forecast weather: {forecast_start} to {forecast_end}")
        forecast = fetch_forecast_weather(forecast_start, forecast_end)
        if forecast is not None:
            common = result.index.intersection(forecast.index)
            if len(common) > 0:
                result.loc[common] = forecast.loc[common]
                sources_used.add("forecast_api")

    # 3. Fill remaining gaps with typical weather
    missing_mask = result["temperature"].isna()
    if missing_mask.any():
        n_missing = missing_mask.sum()
        logger.info(f"Filling {n_missing} hours with typical weather")
        for ts in result.index[missing_mask]:
            typical = get_typical_weather(typical_df, ts.month, ts.hour)
            result.loc[ts] = typical
        sources_used.add("typical")

        if "archive_api" not in sources_used and "forecast_api" not in sources_used:
            warnings.append(
                "Could not fetch weather data from Open-Meteo. "
                "Using typical historical weather patterns instead."
            )

    # Determine overall source label
    if len(sources_used) == 1:
        source = sources_used.pop()
    elif len(sources_used) > 1:
        source = "mixed"
    else:
        source = "typical"

    # Convert to float
    for col in result.columns:
        result[col] = pd.to_numeric(result[col], errors="coerce")

    return result, source, warnings
