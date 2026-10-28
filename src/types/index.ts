export type Tab = "pattern" | "weather" | "table" | "insights";
export type Page = "forecast" | "performance" | "about";

export interface ForecastRequestParams {
  start_date: string;
  days: number;
  resolution: "hourly" | "daily";
  temp_change: number;
}

export interface SeriesPoint {
  time: string;
  load: number;
  lower?: number;
  upper?: number;
  temp?: number | null;
  humidity?: number | null;
  cloud_cover?: number | null;
  wind_speed?: number | null;
  holiday?: boolean;
  holiday_name?: string | null;
}

export interface DailyPatternPoint {
  hour: number;
  avg_load: number;
}

export interface ForecastSummary {
  peak: number;
  peak_time: string;
  lowest: number;
  lowest_time: string;
  average: number;
  total_mwh: number;
  vs_period_average_pct?: number;
}

export interface ForecastResponse {
  mode: "short_term" | "long_term";
  mode_reason: string;
  generated_at: string;
  weather_source: string;
  warnings: string[];
  summary: ForecastSummary;
  series: SeriesPoint[];
  daily_pattern: DailyPatternPoint[];
  insights: string[];
}

export interface MetaData {
  dataset_start?: string;
  dataset_end?: string;
  zone?: string;
  available_modes?: string[];
  test_period_start?: string;
  test_period_end?: string;
}

export interface SampleTestWeekPoint {
  time: string;
  load: number;
  actual: number;
}

export interface ModelMetricsItem {
  name: string;
  test_mae?: number;
  test_mape?: number;
  improvement_over_baseline_pct?: number;
  improvement_pct?: number;
  feature_importance?: Record<string, number>;
}

export interface PerformanceData {
  best_short_term?: {
    name: string;
    test_mae?: number;
    test_mape?: number;
  };
  best_long_term?: {
    name: string;
    test_mae?: number;
    test_mape?: number;
  };
  sample_test_week?: SampleTestWeekPoint[];
  test_period?: {
    start: string;
    end: string;
  };
  baselines?: {
    best_baseline_mae?: number;
    baseline_mae?: number;
    baseline_mape?: number;
    same_hour_last_week?: {
      mae?: number;
      mape?: number;
    };
  };
  baseline_mae?: number;
  baseline_mape?: number;
  models?: Record<string, ModelMetricsItem>;
}
