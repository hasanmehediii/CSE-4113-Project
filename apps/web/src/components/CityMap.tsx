"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useCivicLocale } from "@/hooks/useCivicLocale";
import { useResource, type Complaint, type Road } from "@/lib/civic";
import { Feedback } from "./CivicUI";
import LiveRoadMap from "./map/LiveRoadMap";

function reportCondition(row: Complaint) {
  return row.status === "resolved" ? "good" : row.condition || (row.kind === "complaint" ? "bad" : "unknown");
}

export default function CityMap() {
  const { tr, label, number } = useCivicLocale();
  const roads = useResource<Road[]>("/map/roads", 20000);
  const reports = useResource<Complaint[]>("/complaints", 20000);
  const [condition, setCondition] = useState("all");
  const [query, setQuery] = useState("");
  const [panel, setPanel] = useState("reports");
  const [focus, setFocus] = useState<Road | null>(null);
  const search = query.trim().toLocaleLowerCase();
  const selectedRoads = useMemo(() => (roads.data || []).filter(row => (condition === "all" || row.condition === condition) && row.name.toLocaleLowerCase().includes(search)), [roads.data, condition, search]);
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
        <div className="city-map-toolbar"><div className="city-map-filters" role="group" aria-label={tr("Filter road conditions")}>{["all", "bad", "good", "unknown"].map(value => <button key={value} type="button" aria-pressed={condition === value} onClick={() => setCondition(value)}>{label(value)}</button>)}</div><div className="city-map-search"><svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5" /><path d="m16 16 5 5" /></svg><input type="search" value={query} maxLength={150} aria-label={tr("Search the map")} placeholder={tr("Search a road, area or report")} onChange={event => setQuery(event.target.value)} /></div></div>
        <div className="city-map-feedback"><Feedback error={roads.error || reports.error} retry={() => { void roads.reload(); void reports.reload(); }} /></div>
        <div className="city-map-workspace">
          <div className="city-map-surface"><LiveRoadMap roads={selectedRoads} complaints={selectedReports} focus={focus} /><span className="city-map-access-label">{tr("Public map · No account needed")}</span></div>
          <aside className="city-map-activity" aria-label={tr("Map activity")}>
            <div className="city-map-panel-heading"><span className="city-map-live-dot" aria-hidden="true" /><h2>{tr("Road watch")}</h2><span>{tr("Updates every 20s")}</span></div>
            <div className="city-map-panel-tabs" role="group" aria-label={tr("Map activity")}><button type="button" aria-pressed={panel === "reports"} onClick={() => setPanel("reports")}>{tr("Recent reports")}<span>{number(selectedReports.length)}</span></button><button type="button" aria-pressed={panel === "roads"} onClick={() => setPanel("roads")}>{tr("Roads")}<span>{number(selectedRoads.length)}</span></button></div>
            <div className="city-map-activity-list">
              <h3 className="city-map-list-title">{tr(panel === "reports" ? "Latest community reports" : "Road conditions")}</h3>
              {(roads.loading || reports.loading) && <p className="city-map-loading" role="status">{tr("Loading…")}</p>}
              {panel === "reports" ? selectedReports.map(row => <Link className="city-map-report" key={row.id} href={`/complaints/${row.id}`}><div><span className={`civic-badge ${row.status}`}>{label(row.status)}</span><span>{label(row.category_code)}</span></div><h3>{row.title}</h3><p>{row.address}</p><span className="city-map-report-link">{tr("View report")} →</span></Link>) : selectedRoads.map(row => <button type="button" className="city-map-road" key={row.id} aria-pressed={focus?.id === row.id} onClick={() => setFocus(row)}><span><strong>{row.name}</strong><span className={`civic-badge ${row.condition}`}>{label(row.condition)}</span></span><small>{number(row.open_complaints)}{tr(" open · ")}{number(row.historical_reports_90d)}{tr(" in 90 days")}</small>{row.sensitivity === "high" && <small className="city-map-sensitivity">{tr("Historically sensitive")}</small>}</button>)}
              {!roads.loading && !reports.loading && !(panel === "reports" ? selectedReports.length : selectedRoads.length) && <div className="city-map-empty"><svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.3" aria-hidden="true"><path d="M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 1 1 16 0Z" /><circle cx="12" cy="10" r="2.5" /></svg><h3>{tr("Nothing in this view yet")}</h3><p>{tr(query || condition !== "all" ? "Try another search or show all conditions." : panel === "reports" ? "Community reports will appear here as people share updates." : "Roads will appear here when the city road catalog is added.")}</p>{query || condition !== "all" ? <button type="button" onClick={() => { setQuery(""); setCondition("all"); }}>{tr("Clear filters")}</button> : <Link href="/complaints/new">{tr("Share a local update")} →</Link>}</div>}
            </div>
            <details className="city-map-help"><summary>{tr("How are conditions determined?")}</summary><p>{tr("Good reports expire after 24 hours. Open complaints keep a road marked bad until work is confirmed.")}</p><p>{tr("Historical sensitivity means at least 3 reports in 90 days. Predictive ML and IoT readings will be added later.")}</p></details>
          </aside>
        </div>
        <footer className="city-map-board-footer"><div className="map-legend"><span className="bad">{tr("● Bad")}</span><span className="good">{tr("● Good")}</span><span>{tr("● Unknown")}</span></div><Link href="/complaints">{tr("Explore all reports →")}</Link></footer>
      </section>
    </div>
  </main>;
}