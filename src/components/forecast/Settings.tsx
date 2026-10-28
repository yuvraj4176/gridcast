interface SettingsProps {
  period: number;
  setPeriod: (v: number) => void;
  temp: number;
  setTemp: (v: number) => void;
  res: "hourly" | "daily";
  setRes: (v: "hourly" | "daily") => void;
  startDate: string;
  setStartDate: (v: string) => void;
  onGenerate: () => void;
  loading: boolean;
  mobile?: boolean;
}

export function Settings({
  period,
  setPeriod,
  temp,
  setTemp,
  res,
  setRes,
  startDate,
  setStartDate,
  onGenerate,
  loading,
  mobile = false,
}: SettingsProps) {
  return (
    <aside className={mobile ? "settings-sheet" : "settings-panel"}>
      <div className="settings-title">
        <div>
          <p className="eyebrow">FORECAST INPUTS</p>
          <h2>Forecast Settings</h2>
        </div>
        {mobile && <span className="text-slate-400">━</span>}
      </div>

      <label className="field-label">
        Start date
        <input
          className="field"
          type="date"
          value={startDate}
          onChange={(e) => setStartDate(e.target.value)}
        />
      </label>

      <label className="field-label">
        Forecast period
        <select
          className="field"
          value={period}
          onChange={(e) => setPeriod(Number(e.target.value))}
        >
          {[1, 7, 14, 30, 90].map((v) => (
            <option key={v} value={v}>
              {v} {v === 1 ? "day" : "days"}
            </option>
          ))}
        </select>
      </label>

      <fieldset>
        <legend className="field-label">Resolution</legend>
        <div className="segmented">
          <label>
            <input
              type="radio"
              name={mobile ? "mres" : "res"}
              checked={res === "hourly"}
              onChange={() => setRes("hourly")}
            />{" "}
            Hourly
          </label>
          <label>
            <input
              type="radio"
              name={mobile ? "mres" : "res"}
              checked={res === "daily"}
              onChange={() => setRes("daily")}
            />{" "}
            Daily totals
          </label>
        </div>
      </fieldset>

      <div className="temp">
        <div className="flex justify-between">
          <label className="field-label">Temperature change</label>
          <span className="mono">
            {temp > 0 ? "+" : ""}
            {temp}°C
          </span>
        </div>
        <input
          aria-label="Temperature change"
          type="range"
          min="-10"
          max="10"
          value={temp}
          onChange={(e) => setTemp(Number(e.target.value))}
        />
        <div className="range-label">
          <span>−10°</span>
          <span>Normal</span>
          <span>+10°</span>
        </div>
      </div>

      <button className="primary" onClick={onGenerate} disabled={loading}>
        {loading && <span className="spinner" />}
        {loading ? "Building forecast" : "Generate Forecast"}
        <span>→</span>
      </button>

      <p className="settings-help">
        Short periods (≤14d) use recent data and weather forecasts. Long periods
        show typical patterns.
      </p>
    </aside>
  );
}
