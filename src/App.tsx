import { useState, useEffect } from "react";
import { fetchMeta, fetchModelPerformance } from "./api";
import { Page, MetaData, PerformanceData } from "./types";
import { Bolt } from "./components/common/Bolt";
import { ForecastPage } from "./pages/ForecastPage";
import { PerformancePage } from "./pages/PerformancePage";
import { AboutPage } from "./pages/AboutPage";

export default function App() {
  const [page, setPage] = useState<Page>("forecast");
  const [dark, setDark] = useState(false);
  const [meta, setMeta] = useState<MetaData | null>(null);
  const [perf, setPerf] = useState<PerformanceData | null>(null);

  useEffect(() => {
    fetchMeta().then(setMeta).catch(console.error);
    fetchModelPerformance().then(setPerf).catch(console.error);
  }, []);

  return (
    <div className={dark ? "dark" : ""}>
      <div className="site">
        <header className="topbar">
          <button
            className="brand"
            onClick={() => setPage("forecast")}
            type="button"
          >
            <Bolt />
            <span>GridCast</span>
            <em>electricity intelligence</em>
          </button>

          <nav>
            <button
              type="button"
              className={page === "forecast" ? "nav-active" : ""}
              onClick={() => setPage("forecast")}
            >
              Forecast
            </button>
            <button
              type="button"
              className={page === "performance" ? "nav-active" : ""}
              onClick={() => setPage("performance")}
            >
              Model Performance
            </button>
            <button
              type="button"
              className={page === "about" ? "nav-active" : ""}
              onClick={() => setPage("about")}
            >
              About
            </button>
          </nav>

          <button
            className="theme-toggle"
            onClick={() => setDark(!dark)}
            aria-label="Toggle dark mode"
            type="button"
          >
            {dark ? "☀" : "◐"}
          </button>
        </header>

        {page === "forecast" && <ForecastPage meta={meta} />}
        {page === "performance" && <PerformancePage perf={perf} meta={meta} />}
        {page === "about" && <AboutPage meta={meta} />}
      </div>
    </div>
  );
}
