import { MetaData } from "../types";

interface AboutPageProps {
  meta: MetaData | null;
}

export function AboutPage({ meta }: AboutPageProps) {
  const startStr = meta?.dataset_start
    ? meta.dataset_start.split("T")[0]
    : "2021-01-01";
  const endStr = meta?.dataset_end
    ? meta.dataset_end.split("T")[0]
    : "2025-02-28";

  return (
    <main className="standalone-page about">
      <div className="page-title">
        <p className="eyebrow">ABOUT GRIDCAST</p>
        <h1>Clear forecasts for better grid decisions.</h1>
        <p>
          GridCast makes electricity demand forecasting approachable for the
          people learning, modelling and planning the energy system.
        </p>
      </div>

      <div className="about-grid">
        <section className="panel">
          <h2>How it works</h2>
          <p>
            We combine calendar patterns, recent load, and expected weather
            conditions to estimate demand at a useful level of detail. The
            forecast surfaces uncertainty so it supports judgement instead of
            pretending to replace it.
          </p>
        </section>

        <section className="panel data-note">
          <p className="eyebrow">DATA SOURCE</p>
          <h2>Built on public system data.</h2>
          <p>
            Trained on ISO New England load data, Zone {meta?.zone || "A"}.
            Dataset range: {startStr} to {endStr}, with weather from Open-Meteo.
          </p>
        </section>

        <section className="panel limitations">
          <h2>Limitations to keep in view</h2>
          <ul>
            <li>Unexpected outages and major events are not modeled.</li>
            <li>
              Long-range forecasts show normal patterns, not precise outcomes.
            </li>
            <li>Weather forecasts naturally become less reliable with time.</li>
          </ul>
        </section>
      </div>
    </main>
  );
}
