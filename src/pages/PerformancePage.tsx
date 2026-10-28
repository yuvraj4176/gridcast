import { MetaData, PerformanceData } from "../types";
import { formatNumber } from "../utils/formatters";
import { SummaryCard } from "../components/common/SummaryCard";
import { ChartShell } from "../components/common/ChartShell";
import { CompareChart } from "../components/charts/CompareChart";

interface PerformancePageProps {
  perf: PerformanceData | null;
  meta: MetaData | null;
}

export function PerformancePage({ perf, meta }: PerformancePageProps) {
  if (!perf) {
    return (
      <main className="standalone-page">
        <div className="page-title">
          <h1>Loading performance data...</h1>
        </div>
      </main>
    );
  }

  const bShort = perf.best_short_term;
  const metrics = bShort && perf.models ? perf.models[bShort.name] : null;
  const fi = metrics?.feature_importance || {};
  const features = Object.entries(fi)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6);
  const bestImprovement =
    metrics?.improvement_over_baseline_pct ?? metrics?.improvement_pct ?? 0;
  const baselineMae =
    perf.baselines?.best_baseline_mae ??
    perf.baselines?.same_hour_last_week?.mae ??
    perf.baseline_mae ??
    0;
  const baselineMape =
    perf.baselines?.same_hour_last_week?.mape ?? perf.baseline_mape ?? 0;

  const testPeriodStart = meta?.test_period_start
    ? meta.test_period_start.split(" ")[0]
    : "2024-01-01";
  const testPeriodEnd = meta?.test_period_end
    ? meta.test_period_end.split(" ")[0]
    : "2025-02-28";

  return (
    <main className="standalone-page">
      <div className="page-title">
        <p className="eyebrow">MODEL QUALITY</p>
        <h1>Performance, without the mystery.</h1>
        <p>
          Validation on a held-out ISO-NE sample from {testPeriodStart} to{" "}
          {testPeriodEnd}.
        </p>
      </div>

      <div className="summary-grid performance-metrics">
        <SummaryCard
          icon="↕"
          label="MAE"
          value={`${formatNumber(metrics?.test_mae)} kW`}
          note="Mean absolute error"
          trend={`↓ ${formatNumber(bestImprovement)}%`}
        />
        <SummaryCard
          icon="%"
          label="MAPE"
          value={`${(metrics?.test_mape ?? 0).toFixed(1)}%`}
          note="Mean absolute percentage error"
        />
        <SummaryCard
          icon="↑"
          label="Improvement"
          value={`${bestImprovement.toFixed(1)}%`}
          note="Over seasonal baseline"
          trend="Best model"
        />
      </div>

      <div className="performance-grid">
        <ChartShell title="Predicted vs Actual load · sample test week">
          <CompareChart perf={perf} />
        </ChartShell>

        <section className="panel feature-panel">
          <div className="panel-head">
            <div>
              <h2>Feature importance</h2>
              <p>{bShort?.name || "Model"} contribution</p>
            </div>
          </div>
          {features.map(([label, value]) => (
            <div className="feature" key={String(label)}>
              <span>{label}</span>
              <div>
                <i style={{ width: `${value}%` }} />
              </div>
              <b>{Number(value).toFixed(1)}%</b>
            </div>
          ))}
        </section>
      </div>

      <section className="panel models">
        <div className="panel-head">
          <div>
            <h2>Model comparison</h2>
            <p>Lower is better (Short-term models)</p>
          </div>
        </div>
        <table>
          <thead>
            <tr>
              <th>Model</th>
              <th>MAE</th>
              <th>MAPE</th>
              <th>Improvement</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Baseline</td>
              <td>{formatNumber(baselineMae)} kW</td>
              <td>
                {baselineMape ? Number(baselineMape).toFixed(1) : "-"}%
              </td>
              <td>-</td>
            </tr>
            {perf.models &&
              Object.entries(perf.models)
                .filter(([k]) => k.includes("short_term"))
                .map(([k, v]) => {
                  const imp =
                    v.improvement_over_baseline_pct ??
                    v.improvement_pct ??
                    0;
                  return (
                    <tr
                      className={k === bShort?.name ? "best-row" : ""}
                      key={k}
                    >
                      <td>{k}</td>
                      <td>{formatNumber(v.test_mae)} kW</td>
                      <td>
                        {typeof v.test_mape === "number"
                          ? v.test_mape.toFixed(1)
                          : "-"}
                        %
                      </td>
                      <td>
                        {typeof imp === "number" ? imp.toFixed(1) : "-"}%
                      </td>
                    </tr>
                  );
                })}
          </tbody>
        </table>
      </section>
    </main>
  );
}
