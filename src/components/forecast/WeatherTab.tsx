import { ForecastResponse } from "../../types";

interface WeatherTabProps {
  data: ForecastResponse;
}

export function WeatherTab({ data }: WeatherTabProps) {
  const temps = data.series
    .map((s) => s.temp)
    .filter((t): t is number => t !== null && t !== undefined);
  const hums = data.series
    .map((s) => s.humidity)
    .filter((h): h is number => h !== null && h !== undefined);
  const clouds = data.series
    .map((s) => s.cloud_cover)
    .filter((c): c is number => c !== null && c !== undefined);
  const winds = data.series
    .map((s) => s.wind_speed)
    .filter((w): w is number => w !== null && w !== undefined);

  const avgTemp = temps.length
    ? Math.round(temps.reduce((a, b) => a + b, 0) / temps.length)
    : "-";
  const avgHum = hums.length
    ? Math.round(hums.reduce((a, b) => a + b, 0) / hums.length)
    : "-";
  const avgCloud = clouds.length
    ? Math.round(clouds.reduce((a, b) => a + b, 0) / clouds.length)
    : "-";
  const avgWind = winds.length
    ? Math.round(winds.reduce((a, b) => a + b, 0) / winds.length)
    : "-";

  return (
    <div className="weather-content">
      <div>
        <p className="eyebrow">WEATHER OUTLOOK</p>
        <h3>
          {data.weather_source === "typical"
            ? "Typical seasonal weather patterns"
            : "Forecast period averages"}
        </h3>
        <div className="weather-stats">
          <span>
            <b>{avgTemp}°C</b>Temperature
          </span>
          <span>
            <b>{avgHum}%</b>Humidity
          </span>
          <span>
            <b>{avgCloud}%</b>Cloud cover
          </span>
          <span>
            <b>{avgWind} m/s</b>Wind speed
          </span>
        </div>
      </div>
      <svg viewBox="0 0 420 160" className="weather-chart">
        <path d="M4,112 C50,92 72,120 108,89 S165,55 208,74 S260,105 305,55 S365,35 416,60" />
        <path d="M4,112 C50,92 72,120 108,89 S165,55 208,74 S260,105 305,55 S365,35 416,60 L416,156 L4,156Z" />
      </svg>
    </div>
  );
}
