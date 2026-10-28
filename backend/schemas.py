# -*- coding: utf-8 -*-
"""
Pydantic schemas for the GridCast API.
Defines request/response models for all endpoints.
"""
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import date


class ForecastRequest(BaseModel):
    """Request body for POST /forecast"""
    start_date: date = Field(..., description="Forecast start date (YYYY-MM-DD)")
    days: int = Field(..., description="Forecast period in days")
    resolution: str = Field("hourly", description="'hourly' or 'daily'")
    temp_change: float = Field(0.0, description="Temperature adjustment in C (-10 to +10)")

    @field_validator("days")
    @classmethod
    def validate_days(cls, v):
        allowed = [1, 7, 14, 30, 90]
        if v not in allowed:
            raise ValueError(f"days must be one of {allowed}")
        return v

    @field_validator("resolution")
    @classmethod
    def validate_resolution(cls, v):
        if v not in ("hourly", "daily"):
            raise ValueError("resolution must be 'hourly' or 'daily'")
        return v

    @field_validator("temp_change")
    @classmethod
    def validate_temp_change(cls, v):
        if v < -10 or v > 10:
            raise ValueError("temp_change must be between -10 and +10")
        return v


class SeriesPoint(BaseModel):
    """A single point in the forecast time series."""
    time: str
    load: float
    lower: float
    upper: float
    temp: Optional[float] = None
    humidity: Optional[float] = None
    cloud_cover: Optional[float] = None
    wind_speed: Optional[float] = None
    holiday: bool = False
    holiday_name: Optional[str] = None
    actual: Optional[float] = None


class DailyPatternPoint(BaseModel):
    """Average load by hour of day."""
    hour: int
    avg_load: float


class ForecastSummary(BaseModel):
    """Summary statistics for the forecast period."""
    peak: float
    peak_time: str
    lowest: float
    lowest_time: str
    average: float
    total_mwh: float
    vs_period_average_pct: Optional[float] = None


class ForecastResponse(BaseModel):
    """Response for POST /forecast"""
    mode: str  # "short_term" or "long_term"
    mode_reason: str
    weather_source: str  # "forecast_api" | "archive_api" | "typical" | "mixed"
    warnings: List[str] = []
    summary: ForecastSummary
    series: List[SeriesPoint]
    daily_pattern: List[DailyPatternPoint]
    insights: List[str]
    generated_at: str


class MetaResponse(BaseModel):
    """Response for GET /meta"""
    dataset_start: str
    dataset_end: str
    zone: str
    available_modes: List[str]
    test_period_start: str
    test_period_end: str


class HealthResponse(BaseModel):
    """Response for GET /health"""
    status: str
    models_loaded: bool
