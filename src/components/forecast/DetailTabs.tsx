import { Tab, ForecastResponse } from "../../types";
import { Pattern } from "./Pattern";
import { WeatherTab } from "./WeatherTab";
import { DataTable } from "./DataTable";
import { Insights } from "./Insights";

interface DetailTabsProps {
  tab: Tab;
  setTab: (t: Tab) => void;
  data: ForecastResponse;
}

export function DetailTabs({ tab, setTab, data }: DetailTabsProps) {
  const tabs: [Tab, string][] = [
    ["pattern", "Daily Pattern"],
    ["weather", "Weather"],
    ["table", "Data Table"],
    ["insights", "Insights"],
  ];

  return (
    <section className="panel detail-panel">
      <div className="tabs">
        {tabs.map(([id, name]) => (
          <button
            className={tab === id ? "tab-active" : ""}
            onClick={() => setTab(id)}
            key={id}
          >
            {name}
          </button>
        ))}
      </div>
      {tab === "pattern" && <Pattern data={data} />}
      {tab === "weather" && <WeatherTab data={data} />}
      {tab === "table" && <DataTable data={data} />}
      {tab === "insights" && <Insights data={data} />}
    </section>
  );
}
