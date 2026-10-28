# GridCast: Electricity Demand Forecasting

GridCast is a full-stack web application for forecasting electricity demand based on historical loads, calendar patterns, and weather conditions. 
It uses actual trained Machine Learning models on ISO New England load data and Open-Meteo weather data.

## Project Structure

```text
├── src/                          # React + TypeScript Frontend (Vite)
│   ├── components/
│   │   ├── charts/               # LoadChart and CompareChart SVG visualizers
│   │   ├── common/               # Bolt, Icon, SummaryCard, ChartShell, EmptyState
│   │   └── forecast/             # Settings, DetailTabs, Pattern, WeatherTab, DataTable, Insights
│   ├── pages/                    # ForecastPage, PerformancePage, AboutPage
│   ├── types/                    # Shared TypeScript interfaces & types
│   ├── utils/                    # Number & date formatting utilities
│   ├── api.ts                    # Backend API client
│   ├── App.tsx                   # Top-level application shell & router
│   ├── index.css                 # Global styling & Tailwind v4 theme
│   └── main.tsx                  # React entrypoint
├── backend/                      # FastAPI Backend & ML Pipeline
│   ├── audit/                    # Data audits, verification scripts & audit decisions
│   ├── data/
│   │   ├── hourly.csv            # Cleaned hourly dataset used for models/serving
│   │   └── raw/                  # Original raw datasets (ISO-NE & Open-Meteo)
│   ├── models/                   # Trained models (.joblib), metrics.json, typical weather
│   ├── tests/                    # Pytest test suite (test_api.py)
│   ├── training/                 # Data preparation & model training pipelines
│   ├── main.py                   # FastAPI application entrypoint
│   ├── forecast.py               # Forecast generation & uncertainty logic
│   ├── weather.py                # Live Open-Meteo & typical weather fallback
│   ├── features.py               # Feature engineering (lags, calendar cyclical features)
│   ├── holidays_util.py          # US/MA holiday lookups
│   ├── schemas.py                # Pydantic request/response schemas
│   └── requirements.txt          # Python dependencies
├── start.bat                     # Windows launch helper (backend + frontend)
└── package.json                  # Frontend dependencies and scripts
```

## Prerequisites

- Node.js (v18+)
- Python (3.10+)

## Setup and Running

1. **Start the Backend (FastAPI)**

   Open a terminal and run:
   ```bash
   cd backend
   pip install -r requirements.txt
   python main.py
   ```
   *(Alternatively: `python -m uvicorn main:app --reload --port 8000`)*


2. **Start the Frontend (React/Vite)**

   Open a second terminal and run:
   ```bash
   npm install
   npm run dev
   ```

3. **Access the App**
   - Frontend: [http://localhost:5173](http://localhost:5173) (or the port Vite provides)
   - API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)

## Features

- **Short-term Forecasting**: Uses historical lag features for high-accuracy predictions up to 14 days.
- **Long-term Forecasting**: Falls back to calendar and typical weather patterns for longer horizons.
- **Scenario Testing**: Adjust the temperature offset (-10°C to +10°C) to simulate extreme weather demand responses.
- **Model Transparency**: Dedicated page showing error metrics (MAE, MAPE), model comparisons, and feature importance.
- **Real Weather Integration**: Fetches real historical or forecasted weather from Open-Meteo to build the predictions.
