import { ForecastResponse } from "../../types";

interface PatternProps {
  data: ForecastResponse;
}

export function Pattern({ data }: PatternProps) {
  const maxLoad = Math.max(...data.daily_pattern.map((d) => d.avg_load));

  return (
    <div className="detail-content">
      <div className="detail-copy">
        <p className="eyebrow">AVERAGE BY HOUR</p>
        <h3>Daily load distribution</h3>
        <p>
          Shows the average expected demand at each hour of the day across the
          selected forecast period.
        </p>
      </div>
      <div className="mini-bars">
        {data.daily_pattern.map((d) => (
          <div key={d.hour}>
            <i
              style={{
                height: `${
                  (d.avg_load / Math.max(16000, maxLoad)) * 142
                }px`,
              }}
            />
            <span>{d.hour % 4 === 0 ? d.hour : ""}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
