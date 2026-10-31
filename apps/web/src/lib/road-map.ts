import type { Road } from "./civic";

/** Separate OSM ways must never be joined across gaps or carriageways. */
export function roadPaths(road: Road): [number, number][][] {
  return road.paths?.length ? road.paths : road.path?.length ? [road.path] : [];
}

export interface RoadRisk {
  road_id: string;
  waterlogging_probability: number;
  traffic_probability: number;
  risk: "low" | "moderate" | "high";
}
export interface RoadForecast {
  at: string; timezone: string; rainfall_mm: number; data_source: string;
  model_version: string; roads: RoadRisk[];
  forecast_horizon_min?: number;
  aggregation?: string;
}
export const riskColor = (risk?: RoadRisk, hazard: "waterlogging" | "traffic" = "waterlogging") => {
  if (!risk) return "#667884";
  const value = hazard === "waterlogging" ? risk.waterlogging_probability : risk.traffic_probability;
  return value >= .65 ? "#c03938" : value >= .35 ? "#d18a20" : "#22735c";
};
export function dhakaDateTime() {
  return new Date(Date.now() + 6 * 3600_000).toISOString().slice(0, 16);
}
export const googleMapsKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY || "";
export const mapProvider = process.env.NEXT_PUBLIC_MAP_PROVIDER || (googleMapsKey ? "google" : "osm");
