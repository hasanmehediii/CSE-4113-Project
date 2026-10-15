"use client";
import { useCivicLocale } from "@/hooks/useCivicLocale";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import ReportComposer from "./ReportComposer";
import { mutate } from "@/lib/api-client";
import { message, useResource, type Category, type Complaint } from "@/lib/civic";
import { CivicShell, ComplaintCard, Feedback, Gate, CivicForm } from "./CivicUI";
export function ReportList() {
    const { tr, label, number } = useCivicLocale();
    const [query, setQuery] = useState("");
    const [search, setSearch] = useState("");
    const [status, setStatus] = useState("");
    const [category, setCategory] = useState("");
    const [page, setPage] = useState(0);
    const categories = useResource<Category[]>("/categories");
    const reports = useResource<Complaint[]>(`/complaints?${new URLSearchParams({ q: search, ...(status && { status }), ...(category && { category }), offset: String(page * 30) })}`, 20000);
    return <CivicShell title={tr("Your neighbourhood, heard.")} intro={tr("Explore public complaints and road updates. Search by street, area, or report details.")}><CivicForm className="civic-toolbar" onSubmit={e => { e.preventDefault(); setSearch(query); setPage(0); }}><input aria-label={tr("Search reports")} value={query} maxLength={150} onChange={e => setQuery(e.target.value)} placeholder={tr("Search Dhanmondi, drainage\u2026")}/><button className="button">{tr("Search")}</button><select aria-label={tr("Status")} value={status} onChange={e => { setStatus(e.target.value); setPage(0); }}><option value="">{tr("Every status")}</option>{["unsolved", "awaiting_confirmation", "resolved", "disputed", "false"].map(s => <option key={s} value={s}>{label(s)}</option>)}</select><select aria-label={tr("Category")} value={category} onChange={e => { setCategory(e.target.value); setPage(0); }}><option value="">{tr("Every category")}</option>{categories.data?.map(c => <option key={c.code} value={c.code}>{label(c.code, c.label)}</option>)}</select></CivicForm><Feedback loading={reports.loading} error={reports.error || categories.error} empty={!reports.data?.length} retry={() => void reports.reload()}/><div className="civic-grid">{reports.data?.map(row => <ComplaintCard key={row.id} row={row}/>)}</div><div className="civic-toolbar"><button className="button secondary" disabled={!page} onClick={() => setPage(page - 1)}>{tr("Previous")}</button><span>{tr("Page ")}{number(page + 1)}{tr(" \u00B7 up to 30 reports")}</span><button className="button secondary" disabled={(reports.data?.length || 0) < 30} onClick={() => setPage(page + 1)}>{tr("Next")}</button></div></CivicShell>;
}
export function NewReport() { return <Gate><ReportComposer /></Gate>; }
export function CommunityPage() { return <Gate><Contributions /></Gate>; }
function Contributions() {
    const { tr, label, number } = useCivicLocale();
    const reports = useResource<Complaint[]>("/me/complaints", 20000);
    const points = useResource<{
        balance: number;
        entries: {
            id: string;
            delta: number;
            reason: string;
        }[];
    }>("/me/points", 20000);
    return <CivicShell title={tr("Your contribution to Dhaka.")} intro={tr("Track your reports, community feedback, and points.")}><div className="civic-stats"><div><strong>{points.data ? number(points.data.balance) : "—"}</strong><span>{tr("Community points")}</span></div><div><strong>{reports.data ? number(reports.data.length) : "—"}</strong><span>{tr("Recent reports (up to 30)")}</span></div></div><div className="civic-toolbar"><Link className="button" href="/complaints/new">{tr("+ Add a report")}</Link><Link className="button secondary" href="/account">{tr("Account & security")}</Link></div><Feedback error={reports.error || points.error} loading={reports.loading} empty={!reports.data?.length} retry={() => { void reports.reload(); void points.reload(); }}/><div className="civic-grid">{reports.data?.map(row => <ComplaintCard key={row.id} row={row}/>)}</div><section className="civic-card"><h2>{tr("Points history")}</h2>{points.data?.entries.map(e => <div className="civic-ledger-row" key={e.id}><span>{label(e.reason)}</span><strong>{e.delta > 0 ? "+" : ""}{number(e.delta)}</strong></div>)}{!points.data?.entries.length && <p>{tr("Your contributions will appear here.")}</p>}</section></CivicShell>;
}
export function WorkerApply() { return <Gate roles={["citizen", "worker"]}><ApplicationForm /></Gate>; }
function ApplicationForm() {
    const { tr, label } = useCivicLocale();
    const application = useResource<{
        status: string;
        review_note: string | null;
    } | null>("/workers/application");
    const [error, setError] = useState("");
    const [busy, setBusy] = useState(false);
    async function submit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        const data = new FormData(event.currentTarget);
        setBusy(true);
        setError("");
        try {
            await mutate("/workers/application", { nid_number: data.get("nid_number") || null, nid_image_url: data.get("nid_image_url") || null });
            await application.reload();
        }
        catch (e) {
            setError(message(e));
        }
        finally {
            setBusy(false);
        }
    }
    return <CivicShell title={tr("Work for a better neighbourhood.")} intro={tr("Submit your identity information for review by the mayor. Your account remains a citizen account until approved.")}><Feedback error={error || application.error} loading={application.loading}/>{application.data && <div className="civic-card"><h2>{tr("Application: ")}{label(application.data.status)}</h2><p>{application.data.review_note || tr("The mayor will review your application.")}</p>{application.data.status === "approved" && <Link className="button" href="/worker">{tr("Worker dashboard")}</Link>}</div>}{!application.loading && (!application.data || application.data.status === "rejected") && <CivicForm className="civic-card civic-form" onSubmit={submit}><label>{tr("NID number")}<input name="nid_number" inputMode="numeric" pattern="(?:[0-9]{10}|[0-9]{13}|[0-9]{17})" autoComplete="off"/></label><label>{tr("Or a private HTTPS link to your NID image")}<input name="nid_image_url" type="url" placeholder="https://…"/></label><p>{tr("Your NID number is stored as a one-way fingerprint. The image link is visible only to administrators. Use a private link and keep it available during review.")}</p><button className="button" disabled={busy}>{busy ? tr("Submitting\u2026") : tr("Submit for approval")}</button></CivicForm>}</CivicShell>;
}
