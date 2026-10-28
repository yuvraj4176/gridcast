# -*- coding: utf-8 -*-
"""
Tests for GridCast backend.
"""
import pytest
from datetime import date, datetime, timedelta
import pandas as pd
import numpy as np
from fastapi.testclient import TestClient

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import app, app_state
from features import build_features
from forecast import select_mode
from holidays_util import is_holiday

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_mock_state(monkeypatch):
    """Mock the app state for fast testing without loading real models."""
    def mock_weather(start_ts, end_ts, typical_df):
        cur = start_ts
        records = []
        while cur < end_ts:
            records.append({
                "time": cur,
                "temperature": 15.0,
                "humidity": 50.0,
                "cloud_cover": 50.0,
                "wind_speed": 5.0
            })
            cur += pd.Timedelta(hours=1)
        w_df = pd.DataFrame(records).set_index("time")
        return w_df, "typical", []

    monkeypatch.setattr("main.get_weather_for_range", mock_weather)

    if app_state["model_short"] is not None:
        return # already loaded
        
    class MockModel:
        def predict(self, X):
            return np.ones(len(X)) * 450.0

    app_state["model_short"] = MockModel()
    app_state["model_long"] = MockModel()
    app_state["residual_quantiles"] = {
        "short_term": {str(i): {"q10": -50, "q90": 50} for i in range(24)},
        "long_term": {str(i): {"q10": -50, "q90": 50} for i in range(24)}
    }
    app_state["metrics"] = {
        "test_period": {"start": "2024-01-01", "end": "2025-02-28"}
    }
    
    # Mock hourly df
    dates = pd.date_range("2023-01-01", "2024-01-10", freq="1h")
    df = pd.DataFrame(index=dates)
    df.index.name = "Timestamp"
    df["load"] = 450.0
    df["temperature"] = 15.0
    df["humidity"] = 50.0
    df["cloud_cover"] = 50.0
    df["wind_speed"] = 5.0
    df["is_holiday"] = 0
    app_state["hourly_df"] = df
    
    # Mock typical weather
    typ = []
    for m in range(1, 13):
        for h in range(24):
            typ.append({"month": m, "hour": h, "temperature": 15.0, "humidity": 50.0, "cloud_cover": 50.0, "wind_speed": 5.0})
    app_state["typical_weather_df"] = pd.DataFrame(typ)


def test_feature_builder_no_lookahead():
    """Ensure feature builder doesn't use future load data."""
    dates = pd.date_range("2024-01-01", periods=48, freq="1h")
    df = pd.DataFrame(index=dates)
    df["load"] = np.arange(48)
    
    feats = build_features(df, include_lags=True)
    
    # At index 25, lag_24 should be the load from index 1 (value 1)
    assert feats["lag_24"].iloc[25] == 1.0
    # No lag should point forward
    assert pd.isna(feats["lag_24"].iloc[0])


def test_mode_selection():
    """Test short_term vs long_term mode selection."""
    df = app_state["hourly_df"]
    
    # Short term: within dataset, <= 14 days
    mode, _ = select_mode("2024-01-05", 7, df)
    assert mode == "short_term"
    
    # Long term: > 14 days
    mode, _ = select_mode("2024-01-05", 30, df)
    assert mode == "long_term"
    
    # Long term: outside dataset
    mode, _ = select_mode("2025-05-01", 7, df)
    assert mode == "long_term"


def test_holidays():
    """Test holiday flags."""
    assert is_holiday(date(2024, 7, 4)) == True  # July 4th
    assert is_holiday(date(2024, 7, 5)) == False


def test_health_endpoint():
    """Smoke test health endpoint."""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_forecast_endpoint_schema_and_temp_change():
    """Test forecast endpoint schema, daily aggregation, and temp_change."""
    # Test base prediction
    resp1 = client.post("/forecast", json={
        "start_date": "2024-01-05",
        "days": 1,
        "resolution": "hourly",
        "temp_change": 0
    })
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert "series" in data1
    assert len(data1["series"]) == 24
    
    # Test daily aggregation
    resp2 = client.post("/forecast", json={
        "start_date": "2024-01-05",
        "days": 7,
        "resolution": "daily",
        "temp_change": 0
    })
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert len(data2["series"]) == 7
    
    # Test temp_change effect
    resp3 = client.post("/forecast", json={
        "start_date": "2024-01-05",
        "days": 1,
        "resolution": "hourly",
        "temp_change": 5.0
    })
    assert resp3.status_code == 200
    data3 = resp3.json()
    
    # With mock model, prediction might not change, but temperature in series must reflect the +5
    t1 = data1["series"][0]["temp"]
    t3 = data3["series"][0]["temp"]
    if t1 is not None and t3 is not None:
        assert round(t3, 1) == round(t1 + 5.0, 1)
