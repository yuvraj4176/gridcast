import { PerformanceData } from "../../types";

interface CompareChartProps {
  perf?: PerformanceData | null;
}

export function CompareChart({ perf }: CompareChartProps) {
  if (!perf || !perf.sample_test_week || perf.sample_test_week.length === 0) {
    return null;
  }
  const series = perf.sample_test_week;
  const width = 920;
  const height = 310;
  const pad = { l: 52, r: 16, t: 18, b: 42 };

  const vals = series.flatMap((d) => [d.load, d.actual]);
  const min = Math.min(...vals) - 300;
  const max = Math.max(...vals) + 300;

  const n = series.length;
  const x = (i: number) =>
    pad.l + (n > 1 ? i / (n - 1) : 0) * (width - pad.l - pad.r);
  const y = (v: number) =>
    pad.t + (1 - (v - min) / (max - min)) * (height - pad.t - pad.b);
  const line = (data: number[]) =>
    data.map((v, i) => `${i ? "L" : "M"}${x(i)},${y(v)}`).join(" ");

  const ticks = [0, 24, 48, 72, 96, 120, 144, 167].filter((i) => i < n);

  return (
    <div className="chart-wrap">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="chart"
        role="img"
        aria-label="Predicted versus actual load chart"
      >
        {[0, 1, 2, 3, 4].map((i) => {
          const v = min + ((max - min) / 4) * i;
          return (
            <g key={i}>
              <line
                x1={pad.l}
                x2={width - pad.r}
                y1={y(v)}
                y2={y(v)}
                className="gridline"
              />
              <text x="0" y={y(v) + 4} className="axis">
                {Math.round(v / 1000)}k
              </text>
            </g>
          );
        })}
        <path d={line(series.map((d) => d.load))} className="forecast-line" />
        <path d={line(series.map((d) => d.actual))} className="actual-line" />
        {ticks.map((i) => (
          <text
            key={i}
            x={x(i)}
            y={height - 15}
            textAnchor="middle"
            className="axis"
          >
            {new Date(series[i].time).toLocaleDateString(undefined, {
              weekday: "short",
            })}
          </text>
        ))}
      </svg>
    </div>
  );
}
