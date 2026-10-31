"use client";
import { useState } from "react";
import { mutate } from "@/lib/api-client";
import { message, useResource, type Category, type Complaint } from "@/lib/civic";
import { useCivicLocale } from "@/hooks/useCivicLocale";
import { CivicShell, ComplaintCard, Feedback, Gate } from "./CivicUI";

export default function WorkerDashboard() { return <Gate roles={["worker"]}><Workspace /></Gate>; }

function Workspace() {
  const { tr, label, number } = useCivicLocale();
  const [view, setView] = useState("mine");
  const [category, setCategory] = useState("");
  const [page, setPage] = useState(0);
  const [position, setPosition] = useState<{ latitude: number; longitude: number } | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const categories = useResource<Category[]>("/categories");
  const paging = { limit: "30", offset: String(page * 30), ...(category && { category }) };
  const assigned = useResource<{ id: string; status: string; complaint: Complaint }[]>(
    "/workers/assignments?" + new URLSearchParams({ ...paging, status: "active" }), 20000
  );
  const params = new URLSearchParams({ ...paging,
    ...(view === "unsolved" || view === "nearby" || view === "ranked" ? { status: "unsolved" } : view === "done" ? { status: "resolved" } : {}),
    ...(view === "ranked" && { ranked: "true" }),
    ...(view === "nearby" && position && { latitude: String(position.latitude), longitude: String(position.longitude), radius_km: "3" }),
  });
  const reports = useResource<Complaint[]>("/complaints?" + params, 20000);
  function selectView(next: string) { setView(next); setPage(0); }

  function locate() {
    setError(""); setNotice(""); setBusy(true);
    if (!navigator.geolocation) { setError("Location is unavailable in your browser."); setBusy(false); return; }
    navigator.geolocation.getCurrentPosition(p => {
      const value = { latitude: p.coords.latitude, longitude: p.coords.longitude };
      mutate("/workers/location", { ...value, available: true }).then(() => {
        setPosition(value);
        setNotice("Available for assignment for 15 minutes. Refresh your location to stay available.");
        selectView("nearby");
      }).catch(e => setError(message(e))).finally(() => setBusy(false));
    }, () => { setError("Location access failed. Allow location access and retry."); setBusy(false); }, { timeout: 10000 });
  }
  async function unavailable() {
    setBusy(true); setError(""); setNotice("");
    try {
      await mutate("/workers/availability", { available: false }, "PATCH");
      setNotice("You are unavailable for automatic assignments.");
    } catch (e) { setError(message(e)); }
    finally { setBusy(false); }
  }
  const resource = view === "mine" ? assigned : reports;
  const rows = view === "mine" ? assigned.data?.map(a => a.complaint)
    : view === "nearby" && !position ? [] : reports.data;
  return <CivicShell title={tr("Ready to make a difference.")} intro={tr("Browse your active assignments and community reports. Open a report to submit work or evidence.")}>
    <div className="civic-toolbar">
      <button className="button" disabled={busy} onClick={locate}>{tr("Scan nearby & share availability")}</button>
      <button className="button secondary" disabled={busy} onClick={() => void unavailable()}>{tr("Set unavailable")}</button>
    </div>
    {notice && <p className="notice" role="status">{tr(notice)}</p>}
    <div className="civic-toolbar">
      <div className="civic-tabs">{["mine", "unsolved", "nearby", "done", "ranked"].map(tab => <button key={tab} type="button" aria-pressed={view === tab} onClick={() => selectView(tab)}>{tr({ mine: "My assignments", unsolved: "Unsolved", nearby: "Nearby", done: "Completed", ranked: "By priority" }[tab]!)}</button>)}</div>
      <select aria-label={tr("Category")} value={category} onChange={event => { setCategory(event.target.value); setPage(0); }}>
        <option value="">{tr("Every category")}</option>{categories.data?.map(c => <option key={c.code} value={c.code}>{label(c.code, c.label)}</option>)}
      </select>
    </div>
    {view === "ranked" && <p>{tr("Ranking uses ML category suggestions at confidence 60% or above, then category urgency. Pending or low-confidence results use the reported category.")}</p>}
    {view === "nearby" && !position && <p>{tr("Share your location to scan complaints within 3 km.")}</p>}
    <Feedback loading={resource.loading} error={error || resource.error || categories.error} empty={!rows?.length} retry={() => { void assigned.reload(); void reports.reload(); void categories.reload(); }} />
    <div className="civic-grid">{rows?.map(row => <ComplaintCard key={row.id} row={row} />)}</div>
    <div className="civic-toolbar">
      <button className="button secondary" disabled={!page || resource.loading} onClick={() => setPage(page - 1)}>{tr("Previous")}</button>
      <span>{tr("Page ")}{number(page + 1)}</span>
      <button className="button secondary" disabled={resource.loading || (rows?.length || 0) < 30} onClick={() => setPage(page + 1)}>{tr("Next")}</button>
    </div>
  </CivicShell>;
}
