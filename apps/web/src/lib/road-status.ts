/** Road traffic/waterlogging status from three separate sources (GET /map/road-status). */
export type StatusSource = "community" | "historical" | "weather";
export type StatusHazard = "traffic" | "waterlogging";
export type RiskLevel = "high" | "moderate" | "low" | "unknown";

export interface CommunityStatus {
  status: "reported" | "clear" | "none";
  reports: number; clear_reports: number;
  last_report_at: number | null; expires_at: number | null;
}
export interface LevelStatus { level: RiskLevel; probability?: number | null }
export interface RoadStatusRow {
  road_id: string;
  community: Record<StatusHazard, CommunityStatus>;
  historical: Record<StatusHazard, LevelStatus>;
  /** "Now": current Open-Meteo rain applied to the history for this hour and that much rain. */
  weather: ({ rain_mm_1h: number; rain_mm_3h: number; observed_at: string; rain_band: RainBand } & Record<StatusHazard, LevelStatus>) | null;
}
export type RainBand = "none" | "light" | "heavy";
export type AvoidReason = "reported_traffic" | "reported_waterlogging" | "likely_traffic" | "likely_waterlogging";
export interface CityWeather { temperature_c: number | null; weather_code: number | null; rain_mm_1h: number; rain_mm_3h: number; observed_at: string }
export interface RoadStatusResponse {
  generated_at: string;
  sources: {
    community: { window_hours: number };
    historical: { at: string; season: string; day_type: string; hour: number; notice: string; data_source: string };
    weather: { status: "live" | "stale" | "unavailable"; fetched_at: string | null; city?: CityWeather | null; message?: string };
  };
  /** Reported problems first (actual conditions), then roads with a high predicted risk now. */
  avoid_now?: { road_id: string; reasons: AvoidReason[] }[];
  roads: RoadStatusRow[];
}

export const STATUS_SOURCES: StatusSource[] = ["community", "historical", "weather"];
export const SOURCE_LABELS: Record<StatusSource, string> = {
  community: "Reported · last 4 h", historical: "Usual at this time", weather: "Now · weather + history",
};

/** One display value per road, source and hazard. */
export type StatusValue = "reported" | "clear" | "none" | RiskLevel;
export function statusValue(row: RoadStatusRow | undefined, source: StatusSource, hazard: StatusHazard): StatusValue {
  if (!row) return source === "community" ? "none" : "unknown";
  if (source === "community") return row.community[hazard].status;
  if (source === "historical") return row.historical[hazard].level;
  return row.weather?.[hazard].level ?? "unknown";
}

const COLORS: Record<StatusValue, string> = {
  reported: "#c03938", high: "#c03938", moderate: "#d18a20", clear: "#22735c", low: "#22735c",
  none: "#667884", unknown: "#667884",
};
export const statusColor = (value: StatusValue) => COLORS[value];

export const STATUS_LABELS: Record<StatusValue, string> = {
  reported: "Reported", clear: "Reported clear", none: "No recent report",
  high: "High", moderate: "Moderate", low: "Low", unknown: "No data",
};

export const AVOID_REASON_LABELS: Record<AvoidReason, string> = {
  reported_traffic: "Jam reported", reported_waterlogging: "Waterlogging reported",
  likely_traffic: "Jam likely now", likely_waterlogging: "Waterlogging likely now",
};
export const RAIN_BAND_LABELS: Record<RainBand, string> = { none: "no rain", light: "light rain", heavy: "heavy rain" };
