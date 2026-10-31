"use client";
import { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { useCivicLocale } from "@/hooks/useCivicLocale";
import { mediaUrl } from "@/lib/api-client";
import { useResource } from "@/lib/civic";
import { Feedback } from "./CivicUI";

interface Submission {
  id: string; title: string; description: string; address: string;
  author_name: string; created_at: number; images: string[];
}
export default function IncidentReports({ incidentId, total, reporters }: {
  incidentId: string; total: number; reporters: number;
}) {
  const { tr, number, date } = useCivicLocale();
  const [page, setPage] = useState(0);
  const reports = useResource<Submission[]>(`/complaints/${encodeURIComponent(incidentId)}/reports?limit=10&offset=${page * 10}`, 20000);
  return <section aria-label={tr("All reports for this incident")}>
    <h2>{tr("One incident · every report preserved")}</h2>
    <p>{number(total)} {tr("reports from")} {number(reporters)} {tr("people. Assignment and completion are shared.")}</p>
    <Feedback loading={reports.loading} error={reports.error} retry={() => void reports.reload()}/>
    <div className="civic-grid">{reports.data?.map(row => <article key={row.id} className="civic-card">
      <h3><Link href={`/complaints/${row.id}`}>{row.title}</Link></h3>
      <p>{row.author_name} · {date(row.created_at)}</p><p>{row.address}</p>
      <p className="civic-description">{row.description}</p>
      <div className="civic-photos">{row.images.map(url => <a key={url} href={mediaUrl(url)} target="_blank" rel="noopener noreferrer"><Image src={mediaUrl(url)} width={640} height={400} alt={tr("Community report evidence")} unoptimized/></a>)}</div>
    </article>)}</div>
    <div className="civic-toolbar">
      <button type="button" className="button secondary" disabled={!page || reports.loading} onClick={() => setPage(page - 1)}>{tr("Previous")}</button>
      <span>{tr("Page ")}{number(page + 1)}</span>
      <button type="button" className="button secondary" disabled={reports.loading || (page + 1) * 10 >= total} onClick={() => setPage(page + 1)}>{tr("Next")}</button>
    </div>
  </section>;
}
