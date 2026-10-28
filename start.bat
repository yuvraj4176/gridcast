@echo off
echo ===================================================
echo Starting GridCast Backend and Frontend...
echo ===================================================

echo Starting FastAPI Backend on http://127.0.0.1:8000 ...
start "GridCast Backend" cmd /k "python backend\main.py"

echo Starting Vite Frontend on http://localhost:8443 ...
start "GridCast Frontend" cmd /k "npm run dev"

echo.
echo Both servers have been launched in separate windows!
echo - Frontend: http://localhost:8443
echo - Backend:  http://127.0.0.1:8000
echo.
