import { ForecastResponse } from "../../types";
import { Icon } from "../common/Icon";

interface InsightsProps {
  data: ForecastResponse;
}

export function Insights({ data }: InsightsProps) {
  return (
    <div className="insights">
      {data.insights.map((insight: string, i: number) => (
        <article key={i}>
          <Icon>{"✨"}</Icon>
          <p>{insight}</p>
        </article>
      ))}
    </div>
  );
}
