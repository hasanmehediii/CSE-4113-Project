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
  weather: ({ rain_mm_1h: number; rain_mm_3h: number; observed_at: string } & Record<StatusHazard, LevelStatus>) | null;
}
export interface RoadStatusResponse {
  generated_at: string;
  sources: {
    community: { window_hours: number };
    historical: { at: string; season: string; day_type: string; hour: number; notice: string; data_source: string };
    weather: { status: "live" | "stale" | "unavailable"; fetched_at: string | null; message?: string };
  };
  roads: RoadStatusRow[];
}

export const STATUS_SOURCES: StatusSource[] = ["community", "historical", "weather"];
export const SOURCE_LABELS: Record<StatusSource, string> = {
  community: "Reported · last 4 h", historical: "Usual at this time", weather: "Live rain · Open-Meteo",
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
