"use client";
import { useState } from "react";
import { mutate } from "@/lib/api-client";
import { message, useResource, type Category, type Complaint } from "@/lib/civic";
import { CivicShell, ComplaintCard, Feedback, Gate } from "./CivicUI";

export default function WorkerDashboard() { return <Gate roles={["worker"]}><Workspace /></Gate>; }
function Workspace() {
  const [view, setView] = useState("mine"); const [category, setCategory] = useState("");
  const [position, setPosition] = useState<{ latitude: number; longitude: number } | null>(null);
  const [error, setError] = useState(""); const [notice, setNotice] = useState(""); const [busy, setBusy] = useState(false);
  const categories = useResource<Category[]>("/categories");
  const assigned = useResource<{ id: string; status: string; complaint: Complaint }[]>("/workers/assignments", 20000);
  const params = new URLSearchParams({ ...(view === "unsolved" || view === "nearby" || view === "ranked" ? { status: "unsolved" } : view === "done" ? { status: "resolved" } : {}), ...(category && { category }), ...(view === "ranked" && { ranked: "true" }), ...(view === "nearby" && position && { latitude: String(position.latitude), longitude: String(position.longitude), radius_km: "3" }) });
  const reports = useResource<Complaint[]>(`/complaints?${params}`, 20000);
  function locate(available: boolean) {
    setError(""); setBusy(true);
    if (!navigator.geolocation) { setError("Location is unavailable in your browser."); setBusy(false); return; }
    navigator.geolocation.getCurrentPosition(p => {
      const value = { latitude: p.coords.latitude, longitude: p.coords.longitude };
      setPosition(value);
      mutate("/workers/location", { ...value, available }).then(() => { setNotice(available ? "Available for assignment for 15 minutes. Refresh your location to stay available." : "You are unavailable for automatic assignments."); if (available) setView("nearby"); }).catch(e => setError(message(e))).finally(() => setBusy(false));
    }, () => { setError("Location access failed. Allow location access and retry."); setBusy(false); }, { timeout: 10000 });
  }
  const rows = view === "mine" ? Array.from(new Map((assigned.data || []).map(a => [a.complaint.id, a.complaint])).values()) : view === "nearby" && !position ? [] : reports.data;
  return <CivicShell title="Ready to make a difference." intro="Your assignments, nearby issues, and the latest 30 complaints. Open a report to submit work or evidence."><div className="civic-toolbar"><button className="button" disabled={busy} onClick={() => locate(true)}>Scan nearby & share availability</button><button className="button secondary" disabled={busy} onClick={() => { setBusy(true); setError(""); mutate("/workers/availability", { available: false }, "PATCH").then(() => setNotice("You are unavailable for automatic assignments.")).catch(e => setError(message(e))).finally(() => setBusy(false)); }}>Set unavailable</button></div>{notice && <p className="notice" role="status">{notice}</p>}<div className="civic-toolbar"><div className="civic-tabs">{["mine", "all", "unsolved", "done", "ranked", "nearby"].map(v => <button key={v} aria-pressed={view === v} onClick={() => setView(v)}>{v === "mine" ? "My assignments" : v}</button>)}</div><select aria-label="Filter category" value={category} onChange={e => setCategory(e.target.value)}><option value="">All categories</option>{categories.data?.map(c => <option key={c.code} value={c.code}>{c.label}</option>)}</select></div>{view === "ranked" && <p>Ranking uses ML category suggestions at confidence 60% or above, then category urgency. Pending or low-confidence results use the reported category.</p>}{view === "nearby" && !position && <p>Share your location to scan complaints within 3 km.</p>}<Feedback loading={view === "mine" ? assigned.loading : reports.loading} error={error || assigned.error || reports.error} empty={!rows?.length} retry={() => { void assigned.reload(); void reports.reload(); }} /><div className="civic-grid">{rows?.filter(r => !category || r.category_code === category).map(r => <ComplaintCard key={r.id} row={r} />)}</div></CivicShell>;
}
