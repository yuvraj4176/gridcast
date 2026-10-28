import { useState } from "react";
import { generateForecast } from "../api";
import { Tab, MetaData, ForecastResponse } from "../types";
import { formatNumber } from "../utils/formatters";
import { SummaryCard } from "../components/common/SummaryCard";
import { ChartShell } from "../components/common/ChartShell";
import { EmptyState } from "../components/common/EmptyState";
import { LoadChart } from "../components/charts/LoadChart";
import { Settings } from "../components/forecast/Settings";
import { DetailTabs } from "../components/forecast/DetailTabs";

interface ForecastPageProps {
  meta: MetaData | null;
}

export function ForecastPage({ meta }: ForecastPageProps) {
  const [period, setPeriod] = useState(7);
  const [temp, setTemp] = useState(0);
  const [res, setRes] = useState<"hourly" | "daily">("hourly");
  const [startDate, setStartDate] = useState(
    new Date().toISOString().split("T")[0]
  );

  const [data, setData] = useState<ForecastResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState<Tab>("pattern");
  const [sheet, setSheet] = useState(false);

  const generate = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await generateForecast({
        start_date: startDate,
        days: period,
        resolution: res,
        temp_change: temp,
      });
      setData(result);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "An error occurred";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const long = data?.mode === "long_term";


  return (
    <div className="dashboard">
      <Settings
        period={period}
        setPeriod={setPeriod}
        temp={temp}
        setTemp={setTemp}
        res={res}
        setRes={setRes}
        startDate={startDate}
        setStartDate={setStartDate}
        onGenerate={generate}
        loading={loading}
      />

      <main className="main-content">
        <button className="settings-button" onClick={() => setSheet(true)}>
          ☷ Settings
        </button>

        {!data ? (
          error ? (
            <div className="error-banner">
              <span>×</span>
              <div>
                <strong>Error</strong>
                <p>{error}</p>
              </div>
            </div>
          ) : (
            <EmptyState onGenerate={generate} />
          )
        ) : (
          <>
            <div className="mode-line">
              <span className={long ? "mode-badge long" : "mode-badge"}>
                <i />{" "}
                {long
                  ? "Long-term estimate · Typical pattern"
                  : "Short-term forecast · High accuracy"}
              </span>
              <span className="update-note">
                Weather-aware · ISO-NE load {meta?.zone ?? "ZoneA"}
              </span>
            </div>



            <div className="summary-grid">
              <SummaryCard
                icon="⌁"
                label="Peak demand"
                value={`${formatNumber(data.summary.peak)} kW`}
                note={new Date(data.summary.peak_time).toLocaleString(
                  undefined,
                  {
                    weekday: "short",
                    month: "short",
                    day: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                  }
                )}
                trend={
                  data.summary.vs_period_average_pct
                    ? `${data.summary.vs_period_average_pct > 0 ? "↑" : "↓"} ${Math.abs(
                        data.summary.vs_period_average_pct
                      )}%`
                    : undefined
                }
                amber
              />
              <SummaryCard
                icon="⌄"
                label="Lowest demand"
                value={`${formatNumber(data.summary.lowest)} kW`}
                note={new Date(data.summary.lowest_time).toLocaleString(
                  undefined,
                  {
                    weekday: "short",
                    month: "short",
                    day: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                  }
                )}
              />
              <SummaryCard
                icon="∿"
                label="Average demand"
                value={`${formatNumber(data.summary.average)} kW`}
                note="Across selected period"
              />
              <SummaryCard
                icon="◫"
                label="Total energy"
                value={`${formatNumber(data.summary.total_mwh)} MWh`}
                note="Forecast period total"
              />
            </div>

            <ChartShell
              title="Predicted Electricity Load"
              generatedAt={data.generated_at}
              action={
                <div className="chart-legend">
                  <span>
                    <i className="line-key" />
                    Forecast
                  </span>
                  <span>
                    <i className="band-key" />
                    Confidence range
                  </span>
                  <span>
                    <i className="dot-key" />
                    Holiday
                  </span>
                </div>
              }
            >
              <LoadChart series={data.series} isDaily={res === "daily"} />
            </ChartShell>

            <DetailTabs tab={tab} setTab={setTab} data={data} />
          </>
        )}
      </main>

      {sheet && (
        <div className="sheet-backdrop" onClick={() => setSheet(false)}>
          <div onClick={(e) => e.stopPropagation()}>
            <Settings
              mobile
              period={period}
              setPeriod={setPeriod}
              temp={temp}
              setTemp={setTemp}
              res={res}
              setRes={setRes}
              startDate={startDate}
              setStartDate={setStartDate}
              onGenerate={generate}
              loading={loading}
            />
          </div>
        </div>
      )}
    </div>
  );
}
