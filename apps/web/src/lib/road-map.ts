import type { Road } from "./civic";
import { ApiError } from "./api-client";

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
const isProbability = (value: unknown) => typeof value === "number" && value >= 0 && value <= 1;
/** The map renders `at` and each road's probabilities; anything less is a failed prediction. */
export function isRoadForecast(value: unknown): value is RoadForecast {
  if (!value || typeof value !== "object") return false;
  const forecast = value as Partial<RoadForecast>;
  return typeof forecast.at === "string" && !Number.isNaN(Date.parse(forecast.at)) && Array.isArray(forecast.roads)
    && forecast.roads.every(road => road && typeof road.road_id === "string"
      && isProbability(road.waterlogging_probability) && isProbability(road.traffic_probability));
}

export const PREDICTION_INVALID = "The ML service returned an invalid prediction response. Try again.";
const FIXED_MESSAGES = [
  "Road prediction service is not reachable. Start the ML service, then try again.",
  PREDICTION_INVALID,
  "Choose a time within seven days of now",
  "Forecast horizon must be 30, 60 or 120 minutes",
  "The loaded road-risk model supports only the 60-minute horizon. Choose 60 minutes, or retrain the model with the supplied dataset.",
];
export interface PredictionFailure { message: string; detail?: string }
/**
 * Turns an API failure into a fixed sentence the UI can translate. A variable technical
 * reason from the ML service is kept separately as `detail` instead of being shown as the message.
 */
export function predictionFailure(error: unknown): PredictionFailure {
  if (!(error instanceof ApiError)) {
    return error instanceof Error && error.message === PREDICTION_INVALID
      ? { message: PREDICTION_INVALID } : { message: "Could not connect. Please try again." };
  }
  const known = FIXED_MESSAGES.find(text => text === error.detail);
  if (known) return { message: known };
  if (error.status === 503) {
    const detail = error.detail.replace(/^Road prediction unavailable\.\s*/, "");
    return { message: "Road prediction is unavailable because the road-risk model is not loaded. Retrain or reload the model, then try again.", detail: detail || undefined };
  }
  if (error.status === 422) return { message: "Check the date, horizon and rainfall, then try again.", detail: error.detail };
  return { message: "The ML service could not complete this prediction. Try again.", detail: error.detail };
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
