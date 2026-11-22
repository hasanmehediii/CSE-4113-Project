"use client";

import { useCallback, useMemo, useRef, useState, type FormEvent } from "react";
import Link from "next/link";
import { useCivicLocale } from "@/hooks/useCivicLocale";
import { useResource, type Complaint, type Road } from "@/lib/civic";
import { Feedback } from "./CivicUI";
import LiveRoadMap from "./map/LiveRoadMap";
import RoadReportForm from "./map/RoadReportForm";
import RoadPredictionPanel from "./map/RoadPredictionPanel";
import RoadStatusPanel from "./map/RoadStatusPanel";
import { statusColor, statusValue, type RoadStatusResponse, type StatusHazard, type StatusSource } from "@/lib/road-status";
import { api } from "@/lib/api-client";
import { dhakaDateTime, isRoadForecast, mapProvider, PREDICTION_INVALID, predictionFailure, type PredictionFailure, type RoadForecast } from "@/lib/road-map";

function reportCondition(row: Complaint) {
  return row.status === "resolved" ? "good" : row.condition || (row.kind === "complaint" ? "bad" : "unknown");
}

export default function CityMap() {
  const { tr, label, number } = useCivicLocale();
  const roads = useResource<Road[]>("/map/roads?main_only=true", 20000);
  const reports = useResource<Complaint[]>("/complaints", 20000);
  const [condition, setCondition] = useState("all");
  const [query, setQuery] = useState("");
  const [panel, setPanel] = useState("reports");
  const [focus, setFocus] = useState<Road | null>(null);
  const [mode, setMode] = useState("community");
  const [at, setAt] = useState(dhakaDateTime);
  const [rain, setRain] = useState("0");
  const [horizon, setHorizon] = useState(60);
  const [hazard, setHazard] = useState<"waterlogging" | "traffic">("waterlogging");
  // The scenario a forecast answers is the one we submitted; responses need not echo every field.
  const [forecast, setForecast] = useState<{ result: RoadForecast; at: string; rain: number; horizon: number } | null>(null);
  const [forecastError, setForecastError] = useState<PredictionFailure | null>(null);
  const [predicting, setPredicting] = useState(false);
  const predictionRequest = useRef(0);
  const selectRoad = useCallback((road: Road) => { setFocus(road); setPanel("roads"); }, []);
  const selected = roads.data?.find(road => road.id === focus?.id) || focus;
  const predictionMode = mode === "predictions";
  const statusMode = mode === "status";
  const [statusSource, setStatusSource] = useState<StatusSource>("community");
  const [statusHazard, setStatusHazard] = useState<StatusHazard>("traffic");
  // Fetched only while the view is open; community reports change, so refresh each minute.
  const roadStatus = useResource<RoadStatusResponse>(statusMode ? "/map/road-status" : null, 60000);
  const scenarioChanged = Boolean(forecast && (forecast.at !== at || forecast.rain !== Number(rain) || forecast.horizon !== horizon));
  const result = forecast?.result ?? null;
  async function predict(event: FormEvent) {
    event.preventDefault();
    const request = ++predictionRequest.current;
    const scenario = { at, rain: Number(rain), horizon };
    setPredicting(true); setForecastError(null); setForecast(null);
    try {
      const response = await api<unknown>(`/map/predictions?at=${encodeURIComponent(`${at}:00+06:00`)}&rainfall_mm=${encodeURIComponent(rain)}&forecast_horizon_min=${horizon}`);
      if (!isRoadForecast(response)) throw new Error(PREDICTION_INVALID);
      if (request === predictionRequest.current) setForecast({ result: response, ...scenario });
    } catch (error) { if (request === predictionRequest.current) setForecastError(predictionFailure(error)); }
    finally { if (request === predictionRequest.current) setPredicting(false); }
  }
  const search = query.trim().toLocaleLowerCase();
  const selectedRoads = useMemo(() => (roads.data || []).filter(row => (predictionMode || statusMode || condition === "all" || row.condition === condition) && row.name.toLocaleLowerCase().includes(search)), [roads.data, condition, search, predictionMode, statusMode]);
  const statusColors = useMemo(() => statusMode && roadStatus.data
    ? Object.fromEntries(roadStatus.data.roads.map(row => [row.road_id, statusColor(statusValue(row, statusSource, statusHazard))]))
    : undefined, [statusMode, roadStatus.data, statusSource, statusHazard]);
  const selectedReports = useMemo(() => (reports.data || []).filter(row => row.status !== "false" && (condition === "all" || reportCondition(row) === condition) && `${row.title} ${row.address} ${row.description}`.toLocaleLowerCase().includes(search)), [reports.data, condition, search]);
  const ready = roads.data !== null && reports.data !== null;
  const stats = [
    { text: "Roads in this view", value: selectedRoads.length, color: "blue" },
    { text: "Needs attention", value: selectedRoads.filter(row => row.condition === "bad").length, color: "bad" },
    { text: "Good conditions", value: selectedRoads.filter(row => row.condition === "good").length, color: "good" },
    { text: "Reports shown", value: selectedReports.length, color: "blue" },
  ];

  return <main id="main" className="city-map-page">
    <div className="city-map-container">
      <header className="city-map-heading"><div><span className="eyebrow">{tr("DHAKA · LIVE CITY MAP")}</span><h1>{tr("Dhaka city map")}</h1><p>{tr("Know your road. Help your city.")}</p></div><div className="city-map-heading-actions"><Link className="city-map-all-reports" href="/complaints">{tr("Community reports")} →</Link><Link className="button" href="/complaints/new">{tr("+ Add a report")}</Link></div></header>
      <div className="city-map-stats">{stats.map(stat => <div key={stat.text}><span className={`city-map-stat-dot ${stat.color}`} aria-hidden="true" /><span>{tr(stat.text)}</span><strong>{ready ? number(stat.value) : "—"}</strong></div>)}</div>
      <section className="city-map-board" aria-label={tr("Dhaka map workspace")}>
        <div className="road-mode-bar"><div className="road-mode-tabs" role="group" aria-label={tr("Map layers")}>{[["community", "Community reports", "01"], ["roads", "Road updates", "02"], ["predictions", "Predicted risk", "03"], ["status", "Traffic & water", "04"]].map(([value, title, index]) => <button type="button" key={value} aria-pressed={mode === value} onClick={() => { setMode(value); setPanel(value === "community" ? "reports" : "roads"); }}><span>{index}</span>{tr(title)}</button>)}</div><span className="road-scope">{tr("DHAKA · MAIN ROADS ONLY")}</span></div>
        <div className="city-map-toolbar">
          {predictionMode || statusMode ? <span className="road-layer-label">{tr(statusMode ? (statusHazard === "waterlogging" ? "Waterlogging · three sources" : "Traffic · three sources") : hazard === "waterlogging" ? "Rainwater risk · scenario" : "Traffic risk · scenario")}</span> : <div className="city-map-filters" role="group" aria-label={tr("Filter road conditions")}>{["all", "bad", "good", "unknown"].map(value => <button key={value} type="button" aria-pressed={condition === value} onClick={() => setCondition(value)}>{label(value)}</button>)}</div>}
          <div className="city-map-search"><svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5" /><path d="m16 16 5 5" /></svg><input type="search" value={query} maxLength={150} aria-label={tr("Search the map")} placeholder={tr("Search a road, area or report")} onChange={event => setQuery(event.target.value)} /></div>
        </div>
        <div className="city-map-feedback"><Feedback error={roads.error || reports.error} retry={() => { void roads.reload(); void reports.reload(); }} /></div>
        <div className="city-map-workspace">
          <div className="city-map-surface"><LiveRoadMap roads={selectedRoads} complaints={mode === "community" ? selectedReports : []} focus={selected} onSelectRoad={selectRoad} risks={scenarioChanged ? undefined : result?.roads} hazard={hazard} predictionMode={predictionMode} roadColors={statusColors} /><div className="road-map-instruction"><span aria-hidden="true">↗</span><div><strong>{tr(predictionMode ? "Explore a time & rain scenario" : statusMode ? "Compare three sources" : "Tap a highlighted road")}</strong><span>{tr(predictionMode ? "Dashed lines show predicted risk, not live conditions." : statusMode ? "Colours follow the source and hazard you choose." : "Choose a segment, then share what you see.")}</span></div></div><span className="city-map-access-label">{tr("Public map · No account needed")}</span></div>
          <aside className="city-map-activity" aria-label={tr("Map activity")}>
            <div className="city-map-panel-heading"><span className="city-map-live-dot" aria-hidden="true" /><h2>{tr(predictionMode ? "Road forecast" : statusMode ? "Traffic & water" : "Road watch")}</h2><span>{tr(predictionMode ? "Scenario view" : statusMode ? "Updates every minute" : "Updates every 20s")}</span></div>
            {!predictionMode && !statusMode && <div className="city-map-panel-tabs" role="group" aria-label={tr("Map activity")}><button type="button" aria-pressed={panel === "reports"} onClick={() => setPanel("reports")}>{tr("Recent reports")}<span>{number(selectedReports.length)}</span></button><button type="button" aria-pressed={panel === "roads"} onClick={() => setPanel("roads")}>{tr("Roads")}<span>{number(selectedRoads.length)}</span></button></div>}
            <div className="city-map-activity-list">
              <h3 className="city-map-list-title">{tr(predictionMode ? "Road risk estimates" : statusMode ? "Road status by source" : panel === "reports" ? "Latest community reports" : "Road conditions")}</h3>
              {(roads.loading || reports.loading) && <p className="city-map-loading" role="status">{tr("Loading…")}</p>}
              {predictionMode && <RoadPredictionPanel at={at} rain={rain} horizon={horizon} hazard={hazard} forecast={result} error={forecastError} predicting={predicting} stale={scenarioChanged} onAt={setAt} onRain={setRain} onHorizon={setHorizon} onHazard={setHazard} onPredict={predict} />}
              {statusMode && <RoadStatusPanel data={roadStatus.data} loading={roadStatus.loading} error={roadStatus.error} retry={() => void roadStatus.reload()} source={statusSource} onSource={setStatusSource} hazard={statusHazard} onHazard={setStatusHazard} roads={selectedRoads} focusId={focus?.id} onSelectRoad={selectRoad} />}
              {selected && !predictionMode && <RoadReportForm key={selected.id} road={selected} onClose={() => setFocus(null)} onSaved={() => { void roads.reload(); void reports.reload(); }} />}
              {!statusMode && (panel === "reports" && !predictionMode ? selectedReports.map(row => <Link className="city-map-report" key={row.id} href={`/complaints/${row.id}`}><div><span className={`civic-badge ${row.status}`}>{label(row.status)}</span><span>{label(row.category_code)}</span></div><h3>{row.title}</h3><p>{row.address}</p><span className="city-map-report-link">{tr("View report")} →</span></Link>) : selectedRoads.map(row => { const risk = !scenarioChanged && result?.roads.find(r => r.road_id === row.id); const probability = risk ? hazard === "waterlogging" ? risk.waterlogging_probability : risk.traffic_probability : null; return <button type="button" className="city-map-road" key={row.id} aria-pressed={focus?.id === row.id} onClick={() => selectRoad(row)}><span><strong>{row.name}</strong>{predictionMode ? <span className="road-risk-value">{probability === null ? "—" : `${number(Math.round(probability * 100))}%`}</span> : <span className={`civic-badge ${row.condition}`}>{label(row.condition)}</span>}</span><small>{row.segment_from ? `${row.segment_from} → ${row.segment_to}` : `${number(row.open_complaints)}${tr(" open · ")}${number(row.historical_reports_90d)}${tr(" in 90 days")}`}</small>{predictionMode && probability !== null && <small>{tr(result?.aggregation === "maximum_segment_probability" ? "Highest segment probability · uncalibrated" : "Model probability · uncalibrated")}</small>}{!predictionMode && row.sensitivity === "high" && <small className="city-map-sensitivity">{tr("Historically sensitive")}</small>}</button>; }))}
              {!statusMode && !roads.loading && !reports.loading && !(panel === "reports" ? selectedReports.length : selectedRoads.length) && <div className="city-map-empty"><svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.3" aria-hidden="true"><path d="M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 1 1 16 0Z" /><circle cx="12" cy="10" r="2.5" /></svg><h3>{tr("Nothing in this view yet")}</h3><p>{tr(query || condition !== "all" ? "Try another search or show all conditions." : panel === "reports" ? "Community reports will appear here as people share updates." : "Roads will appear here when the city road catalog is added.")}</p>{query || condition !== "all" ? <button type="button" onClick={() => { setQuery(""); setCondition("all"); }}>{tr("Clear filters")}</button> : <Link href="/complaints/new">{tr("Share a local update")} →</Link>}</div>}
            </div>
            <details className="city-map-help"><summary>{tr("How are conditions determined?")}</summary><p>{tr("Good reports expire after 24 hours. Open complaints keep a road marked bad until work is confirmed.")}</p><p>{tr("Predictions use a separate model trained on synthetic hourly scenarios. Rainfall is entered by you, not a live weather reading.")}</p><p>{tr("Highlighted roads follow OpenStreetMap geometry. Conditions apply to the selected corridor.")}</p><p>{tr("Traffic & water compares three sources: citizens' reports from the last 4 hours, a synthetic history for the current hour, and a prediction for now from the open-source Open-Meteo weather API and that history.")}</p></details>
          </aside>
        </div>
        <footer className="city-map-board-footer"><div className="map-legend">{statusMode ? (statusSource === "community" ? <><span className="bad">{tr("● Reported")}</span><span className="good">{tr("● Reported clear")}</span><span>{tr("● No recent report")}</span></> : <><span className="bad">{tr("● High")}</span><span className="road-moderate">{tr("● Moderate")}</span><span className="good">{tr("● Low")}</span><span>{tr("● No data")}</span></>) : predictionMode ? <><span className="bad">{tr("● High ≥65%")}</span><span className="road-moderate">{tr("● Moderate ≥35%")}</span><span className="good">{tr("● Low <35%")}</span><span>{tr("● No prediction")}</span></> : <><span className="bad">{tr("● Bad")}</span><span className="good">{tr("● Good")}</span><span>{tr("● Unknown")}</span></>}</div><span className="road-provider-credit">{mapProvider === "google" ? "Google Maps" : "Leaflet · OpenStreetMap"} · <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">{tr("Road shapes: © OpenStreetMap")}</a></span></footer>
      </section>
    </div>
  </main>;
}
