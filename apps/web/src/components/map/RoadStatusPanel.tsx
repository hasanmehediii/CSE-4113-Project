"use client";
import { useCivicLocale } from "@/hooks/useCivicLocale";
import type { Road } from "@/lib/civic";
import { Feedback } from "../CivicUI";
import {
  SOURCE_LABELS, STATUS_LABELS, STATUS_SOURCES, statusValue,
  type RoadStatusResponse, type StatusHazard, type StatusSource,
} from "@/lib/road-status";

const SEASONS: Record<string, string> = { dry: "dry season", pre_monsoon: "pre-monsoon", monsoon: "monsoon", post_monsoon: "post-monsoon" };
const DAY_TYPES: Record<string, string> = { workday: "workdays (Sunday–Thursday)", friday: "Fridays", saturday: "Saturdays" };

interface Props {
  data: RoadStatusResponse | null; loading: boolean; error: string; retry: () => void;
  source: StatusSource; onSource: (source: StatusSource) => void;
  hazard: StatusHazard; onHazard: (hazard: StatusHazard) => void;
  roads: Road[]; focusId?: string; onSelectRoad: (road: Road) => void;
}

export default function RoadStatusPanel(props: Props) {
  const { tr, number, language } = useCivicLocale();
  // Reports expire within 4 hours, so the time of day (Dhaka) is enough.
  const clock = (seconds: number) => new Intl.DateTimeFormat(language === "bn" ? "bn-BD" : "en-GB", { timeZone: "Asia/Dhaka", hour: "2-digit", minute: "2-digit", hourCycle: "h23" }).format(new Date(seconds * 1000));
  const { data, source, hazard } = props;
  const percent = (value: number | null | undefined) => value === null || value === undefined ? "—" : `${number(Math.round(value * 100))}%`;
  const weather = data?.sources.weather;
  const historical = data?.sources.historical;
  return <section className="road-status-panel" aria-label={tr("Traffic & water")}>
    <div className="road-form-tabs road-status-sources" role="group" aria-label={tr("Status source")}>
      {STATUS_SOURCES.map(value => <button key={value} type="button" aria-pressed={source === value} onClick={() => props.onSource(value)}>{tr(SOURCE_LABELS[value])}</button>)}
    </div>
    <div className="road-form-tabs" role="group" aria-label={tr("Risk type")}>
      <button type="button" aria-pressed={hazard === "traffic"} onClick={() => props.onHazard("traffic")}>{tr("Traffic jam")}</button>
      <button type="button" aria-pressed={hazard === "waterlogging"} onClick={() => props.onHazard("waterlogging")}>{tr("Waterlogging")}</button>
    </div>
    <div className="road-status-explainer">
      {source === "community" && <p>{tr("Citizens' reports from the last 4 hours. A newer “clear” update clears the road; each report expires after 4 hours.")}</p>}
      {source === "historical" && <>
        <span className="road-demo-badge">{tr("SYNTHETIC HISTORY")}</span>
        <p>{tr("How often this road was jammed or waterlogged in a generated two-year Dhaka history, for this hour and kind of day. Not observed data.")}</p>
        {historical && <p className="road-status-period">{tr(DAY_TYPES[historical.day_type] ?? historical.day_type)} · {tr(SEASONS[historical.season] ?? historical.season)} · {number(historical.hour)}:00</p>}
      </>}
      {source === "weather" && <>
        <p>{tr("Rain in the last 3 hours from Open-Meteo, an open-source weather API. A rain-based estimate: it does not measure traffic, and no open live traffic feed covers Dhaka.")}</p>
        {weather?.status === "unavailable" && <p role="status" className="road-form-error">{tr("Live rainfall from Open-Meteo is not available right now.")}</p>}
        {weather?.status === "stale" && <p role="status">{tr("Showing the last rainfall update; Open-Meteo could not be reached.")}</p>}
      </>}
    </div>
    <Feedback loading={props.loading && !data} error={props.error} retry={props.retry} />
    <div className="road-status-list">
      {props.roads.map(road => {
        const row = data?.roads.find(item => item.road_id === road.id);
        const value = statusValue(row, source, hazard);
        const community = row?.community[hazard];
        return <button type="button" className="city-map-road road-status-row" key={road.id} aria-pressed={props.focusId === road.id} onClick={() => props.onSelectRoad(road)}>
          <span><strong>{road.name}</strong><span className={`road-status-badge ${value}`}>{tr(STATUS_LABELS[value])}</span></span>
          <small className="road-status-sources-line">
            <span>{tr("Reported")}: {community?.status === "reported" ? `${number(community.reports)}${community.expires_at ? ` · ${tr("until")} ${clock(community.expires_at)}` : ""}` : tr(community?.status === "clear" ? "clear" : "none")}</span>
            <span>{tr("Usual")}: {percent(row?.historical[hazard].probability)}</span>
            <span>{tr("Rain 3 h")}: {row?.weather ? `${number(row.weather.rain_mm_3h)} ${tr("mm")}` : "—"}</span>
          </small>
        </button>;
      })}
    </div>
  </section>;
}
