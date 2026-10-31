"use client";
import { useState } from "react";
import { useCivicLocale } from "@/hooks/useCivicLocale";
import { useResource, type Complaint } from "@/lib/civic";
import { Feedback } from "./CivicUI";

export default function IncidentChoice({ latitude, longitude, category, roadId }: {
  latitude: number; longitude: number; category: string; roadId: string;
}) {
  const { tr, number } = useCivicLocale();
  const [separate, setSeparate] = useState(false);
  const params = new URLSearchParams({ latitude: String(latitude), longitude: String(longitude), category_code: category, ...(roadId && { road_id: roadId }) });
  const nearby = useResource<Complaint[]>(`/complaints/similar?${params}`);
  return <section className="civic-card" aria-label={tr("Related incidents")}>
    <h3>{tr("One blockage, many voices")}</h3>
    <p>{tr("Nearby reports about the same problem share one incident and one work assignment. Your report and photos are kept.")}</p>
    <Feedback loading={nearby.loading} error={nearby.error} retry={() => void nearby.reload()}/>
    <button type="button" className="button secondary" disabled={nearby.loading} onClick={() => void nearby.reload()}>{tr("Refresh nearby incidents")}</button>
    {!!nearby.data?.length && <label>{tr("Is this the same incident?")}
      <select name="incident_id" disabled={separate} required={!separate && nearby.data.length > 1} defaultValue="">
        <option value="">{tr(nearby.data.length > 1 ? "Choose an incident or mark it separate" : "Automatically join the matching incident")}</option>
        {nearby.data.map(row => <option key={row.id} value={row.id}>{row.title} · {number(row.incident_reporter_count || 1)} {tr("reporters")}</option>)}
      </select>
    </label>}
    <label><input type="checkbox" name="separate_incident" checked={separate} onChange={event => setSeparate(event.target.checked)} /> {tr("This is a different blockage. Keep it as a separate incident.")}</label>
    <small>{tr("Grouping uses the category, location within 80 metres, and an active incident seen within 24 hours. It never discards your submission.")}</small>
  </section>;
}
