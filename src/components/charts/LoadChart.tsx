import { SeriesPoint } from "../../types";
import { formatNumber } from "../../utils/formatters";

interface LoadChartProps {
  series: SeriesPoint[];
  isDaily: boolean;
}

export function LoadChart({ series, isDaily }: LoadChartProps) {
  const width = 920;
  const height = 310;
  const pad = { l: 62, r: 16, t: 18, b: 42 };

  const vals = series.flatMap((d) => [
    d.lower ?? d.load,
    d.upper ?? d.load,
    d.load,
  ]);
  const min = Math.min(...vals) - 300;
  const max = Math.max(...vals) + 300;

  const n = series.length;
  const x = (i: number) =>
    pad.l + (n > 1 ? i / (n - 1) : 0) * (width - pad.l - pad.r);
  const y = (v: number) =>
    pad.t + (1 - (v - min) / (max - min)) * (height - pad.t - pad.b);
  const line = (data: number[]) =>
    data.map((v, i) => `${i ? "L" : "M"}${x(i)},${y(v)}`).join(" ");

  const area =
    series[0]?.upper !== undefined
      ? `${line(series.map((d) => d.upper ?? d.load))} L${x(n - 1)},${y(
          series[n - 1]?.lower ?? series[n - 1]?.load
        )} ${series
          .slice()
          .reverse()
          .map((d, i) => `L${x(n - 1 - i)},${y(d.lower ?? d.load)}`)
          .join(" ")} Z`
      : "";

  // X axis ticks
  const ticks: number[] = [];
  if (isDaily) {
    for (let i = 0; i < n; i++) ticks.push(i);
  } else {
    // 24 hour blocks
    const step = Math.max(1, Math.floor(n / 6));
    for (let i = 0; i < n; i += step) ticks.push(i);
    if (ticks[ticks.length - 1] !== n - 1) ticks.push(n - 1);
  }

  const formatTick = (i: number) => {
    const d = new Date(series[i].time);
    if (isDaily) {
      return d.toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
      });
    }
    return d.toLocaleTimeString(undefined, {
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    });
  };

  return (
    <div className="chart-wrap">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="chart"
        role="img"
        aria-label="Predicted electricity load chart"
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
                {formatNumber(v)}
              </text>
            </g>
          );
        })}
        {area && <path d={area} className="confidence" />}
        {series
          .filter((d) => d.holiday)
          .map((d) => (
            <circle
              key={d.time}
              cx={x(series.indexOf(d))}
              cy={y(d.load)}
              r="4.5"
              className="holiday"
            />
          ))}
        <path d={line(series.map((d) => d.load))} className="forecast-line" />
        {ticks.map((i) => (
          <text
            key={i}
            x={x(i)}
            y={height - 15}
            textAnchor="middle"
            className="axis"
          >
            {formatTick(i)}
          </text>
        ))}
      </svg>
    </div>
  );
}
