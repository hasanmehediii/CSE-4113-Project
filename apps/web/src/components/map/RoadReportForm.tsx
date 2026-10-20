"use client";
import { useEffect, useRef, useState, type FormEvent } from "react";
import Link from "next/link";
import { useApp } from "@/components/Providers";
import { mutate } from "@/lib/api-client";
import { message, type Road } from "@/lib/civic";
import { useCivicLocale } from "@/hooks/useCivicLocale";

export default function RoadReportForm({ road, onSaved, onClose }: { road: Road; onSaved: () => void; onClose: () => void }) {
  const { user, loading } = useApp();
  const { tr, label, date } = useCivicLocale();
  const [kind, setKind] = useState("road_update");
  const [condition, setCondition] = useState("bad");
  const [cause, setCause] = useState("road_flooding");
  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState("");
  const selection = useRef<HTMLElement>(null);
  useEffect(() => {
    if (window.matchMedia("(max-width: 800px)").matches) selection.current?.scrollIntoView?.({ block: "nearest" });
  }, []);
  async function submit(event: FormEvent) {
    event.preventDefault(); if (busy) return;
    setBusy(true); setError("");
    try {
      const result = await mutate<{ id: string }>("/complaints", {
        road_id: road.id, latitude: road.latitude, longitude: road.longitude,
        kind, condition: kind === "complaint" ? "bad" : condition,
        category_code: cause, title: `${road.name} — ${cause === "other" ? "Traffic / obstruction" : cause === "road_flooding" ? "Waterlogging" : cause === "blocked_drain" ? "Blocked drain" : "Road damage"} · ${kind === "complaint" || condition === "bad" ? "Needs attention" : "Road is clear"}`.slice(0, 180),
        address: `${road.name}${road.segment_from ? ` (${road.segment_from}–${road.segment_to})` : ""}`,
        description, images: [],
      });
      setSaved(result.id); setDescription(""); onSaved();
    } catch (e) { setError(message(e)); }
    finally { setBusy(false); }
  }
  return <section ref={selection} className="road-selection" aria-label={tr("Selected road")}>
    <div className="road-selection-top"><span>{tr("SELECTED ROAD")}</span><button type="button" aria-label={tr("Close road selection")} onClick={onClose}>×</button></div>
    <h3>{road.name}</h3><p className="road-endpoints">{road.segment_from ? `${road.segment_from} → ${road.segment_to}` : tr("Main road")}</p>
    <div className="road-current"><span className={`civic-badge ${road.condition}`}>{label(road.condition)}</span><span>{road.last_report_at ? date(road.last_report_at) : tr("No recent observations")}</span></div>
    {saved ? <div role="status" className="road-saved">{tr("Your update is on the map.")} <Link href={`/complaints/${saved}`}>{tr("View report")} →</Link><button type="button" onClick={() => setSaved("")}>{tr("Add another update")}</button></div> : <>
      <div className="road-form-tabs" role="group" aria-label={tr("Report type")}><button type="button" aria-pressed={kind === "road_update"} onClick={() => setKind("road_update")}>{tr("Quick update")}</button><button type="button" aria-pressed={kind === "complaint"} onClick={() => setKind("complaint")}>{tr("File a complaint")}</button></div>
      <form className="road-report-form" onSubmit={submit}>
        {kind === "road_update" && <fieldset><legend>{tr("What is the road like?")}</legend><div className="road-condition-options"><button type="button" aria-pressed={condition === "bad"} onClick={() => setCondition("bad")}>● {tr("Blocked / difficult")}</button><button type="button" aria-pressed={condition === "good"} onClick={() => setCondition("good")}>● {tr("Clear / passable")}</button></div></fieldset>}
        <label>{tr("What did you observe?")}<select value={cause} onChange={event => setCause(event.target.value)}><option value="road_flooding">{tr("Rainwater / waterlogging")}</option><option value="other">{tr("Traffic jam / obstruction")}</option><option value="blocked_drain">{label("blocked_drain")}</option><option value="road_damage">{label("road_damage")}</option></select></label>
        <label>{tr("A few details")}<textarea required minLength={10} maxLength={5000} rows={3} value={description} placeholder={tr("Mention the direction, nearby landmark and what you saw.")} onChange={event => setDescription(event.target.value)} /></label>
        <p className="road-form-hint">{tr("Updates describe this road segment. A clear update does not close an unresolved complaint.")}</p>
        {error && <p role="alert" className="road-form-error">{error}</p>}
        {loading ? <p role="status">{tr("Loading…")}</p> : user ? <button className="button" disabled={busy} type="submit">{busy ? tr("Saving…") : tr(kind === "complaint" ? "Submit complaint" : "Share road update")}</button> : <Link className="button" href="/login?next=%2Fmap">{tr("Sign in to share an update")}</Link>}
      </form>
    </>}
  </section>;
}
