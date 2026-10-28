# -*- coding: utf-8 -*-
"""
FastAPI application for GridCast.
"""
import os
import json
import logging
from contextlib import asynccontextmanager
import pandas as pd
import joblib
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import sys

# Ensure backend directory is in sys.path so it can be launched from root or backend/
BASE = os.path.dirname(os.path.abspath(__file__))
if BASE not in sys.path:
    sys.path.insert(0, BASE)

from schemas import ForecastRequest, ForecastResponse, MetaResponse, HealthResponse
from forecast import generate_forecast
from weather import load_typical_weather, get_weather_for_range

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Paths
BASE = os.path.dirname(__file__)
MODELS_DIR = os.path.join(BASE, "models")
DATA_DIR = os.path.join(BASE, "data")

# Global state
app_state = {
    "model_short": None,
    "model_long": None,
    "residual_quantiles": None,
    "metrics": None,
    "hourly_df": None,
    "typical_weather_df": None,
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load models and data on startup
    logger.info("Loading models and data...")
    try:
        app_state["model_short"] = joblib.load(os.path.join(MODELS_DIR, "model_short.joblib"))
        app_state["model_long"] = joblib.load(os.path.join(MODELS_DIR, "model_long.joblib"))
        
        with open(os.path.join(MODELS_DIR, "residual_quantiles.json")) as f:
            app_state["residual_quantiles"] = json.load(f)
            
        with open(os.path.join(MODELS_DIR, "metrics.json")) as f:
            app_state["metrics"] = json.load(f)
            
        app_state["hourly_df"] = pd.read_csv(
            os.path.join(DATA_DIR, "hourly.csv"), 
            parse_dates=["Timestamp"], 
            index_col="Timestamp"
        )
        
        app_state["typical_weather_df"] = load_typical_weather(
            os.path.join(MODELS_DIR, "typical_weather.csv")
        )
        logger.info("Models and data loaded successfully.")
    except Exception as e:
        logger.error(f"Error loading models/data: {e}")
        # We don't raise here to allow the /health endpoint to report failure
    
    yield
    # Cleanup (nothing to do)

app = FastAPI(title="GridCast API", lifespan=lifespan)

# CORS (allow frontend dev origin)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For dev, allow all. In prod, restrict to VITE frontend url
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    models_loaded = all(v is not None for v in app_state.values())
    return {
        "status": "ok" if models_loaded else "error",
        "models_loaded": models_loaded
    }

@app.get("/meta", response_model=MetaResponse)
async def get_meta():
    """Get metadata for the UI (dataset ranges, etc)."""
    if not app_state["hourly_df"] is not None:
        raise HTTPException(status_code=503, detail="Data not loaded")
        
    df = app_state["hourly_df"]
    metrics = app_state["metrics"]
    
    return {
        "dataset_start": df.index.min().isoformat(),
        "dataset_end": df.index.max().isoformat(),
        "zone": "ZoneA",
        "available_modes": ["short_term", "long_term"],
        "test_period_start": metrics["test_period"]["start"],
        "test_period_end": metrics["test_period"]["end"],
    }

@app.get("/model-performance")
async def get_model_performance():
    """Get model performance metrics."""
    if app_state["metrics"] is None:
        raise HTTPException(status_code=503, detail="Metrics not loaded")
    return app_state["metrics"]

@app.post("/forecast", response_model=ForecastResponse)
async def create_forecast(req: ForecastRequest):
    """Generate a forecast."""
    if not all(v is not None for v in app_state.values()):
        raise HTTPException(status_code=503, detail="Models/data not fully loaded")

    # Fetch weather for the requested range
    start_ts = pd.Timestamp(req.start_date)
    end_ts = start_ts + pd.Timedelta(days=req.days)
    
    weather_df, weather_source, warnings = get_weather_for_range(
        start_ts, 
        end_ts, 
        app_state["typical_weather_df"]
    )
    
    # Generate forecast
    try:
        response_dict = generate_forecast(
            start_date=req.start_date,
            days=req.days,
            resolution=req.resolution,
            temp_change=req.temp_change,
            model_short=app_state["model_short"],
            model_long=app_state["model_long"],
            residual_quantiles=app_state["residual_quantiles"],
            hourly_df=app_state["hourly_df"],
            weather_df=weather_df,
            weather_source=weather_source,
            weather_warnings=warnings,
        )
        return response_dict
    except Exception as e:
        logger.error(f"Error generating forecast: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

