export type ReportLocation = { latitude: number; longitude: number };

export const DHAKA_CENTRE: ReportLocation = { latitude: 23.77, longitude: 90.39 };

export function isDhakaLocation(point: ReportLocation): boolean {
  return Number.isFinite(point.latitude) && Number.isFinite(point.longitude)
    && point.latitude >= 23.6 && point.latitude <= 24
    && point.longitude >= 90.2 && point.longitude <= 90.6;
}

export function parseReportLocation(latitude: string, longitude: string): ReportLocation | null {
  if (!latitude.trim() || !longitude.trim()) return null;
  const point = { latitude: Number(latitude), longitude: Number(longitude) };
  return isDhakaLocation(point) ? point : null;
}
