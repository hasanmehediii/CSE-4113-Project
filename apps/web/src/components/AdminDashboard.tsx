"use client";
import { useCivicLocale } from "@/hooks/useCivicLocale";
import { useState, type FormEvent } from "react";
import Link from "next/link";
import { mutate, mediaUrl } from "@/lib/api-client";
import { message, useResource, type Complaint, type Road } from "@/lib/civic";
import { CivicShell, ComplaintCard, Feedback, Gate, CivicForm } from "./CivicUI";
interface Account {
    id: string;
    name: string;
    email: string;
    phone: string | null;
    role: string;
    is_active: boolean;
    points: number;
}
interface Application {
    user_id: string;
    name: string;
    email: string;
    has_nid_number: boolean;
    nid_image_url: string | null;
}
interface Case {
    id: string;
    subject_user_id: string;
    subject_name: string;
    complaint_id: string;
    kind: string;
    evidence: {
        image_url: string;
        comment: string;
    }[];
}
interface Analytics {
    by_status: Record<string, number>;
    by_category: Record<string, number>;
    by_area: {
        area: string;
        total: number;
        resolved: number;
    }[];
    leaders: {
        id: string;
        name: string;
        points: number;
    }[];
    users: number;
    workers: number;
    unmapped_reports: number;
}
export default function AdminDashboard() { return <Gate roles={["admin"]}><Workspace /></Gate>; }
function Workspace() {
    const { tr, label } = useCivicLocale();
    const [tab, setTab] = useState("overview");
    return <CivicShell title={tr("A clearer picture. Better decisions.")} intro={tr("Review evidence, support workers, and see where Dhaka needs attention.")}><div className="civic-tabs admin-tabs">{["overview", "reports", "users", "workers", "applications", "moderation", "roads"].map(t => <button key={t} aria-pressed={tab === t} onClick={() => setTab(t)}>{label(t)}</button>)}</div>{tab === "overview" ? <Overview /> : tab === "reports" ? <Reports /> : tab === "users" || tab === "workers" ? <People key={tab} role={tab === "workers" ? "worker" : ""}/> : tab === "applications" ? <Applications /> : tab === "moderation" ? <Moderation /> : <Catalog />}</CivicShell>;
}
function Bars({ values, title }: {
    values: Record<string, number>;
    title: string;
}) {
    const { tr, label, number } = useCivicLocale();
    const max = Math.max(1, ...Object.values(values));
    return <section className="civic-card"><h2>{title}</h2>{Object.entries(values).map(([name, count]) => <div key={name} className="civic-chart-row"><span>{label(name)}</span><meter min={0} max={max} value={count} aria-label={`${label(name)}: ${number(count)}`}/><strong>{number(count)}</strong></div>)}{!Object.keys(values).length && <p>{tr("No reports yet.")}</p>}</section>;
}
function Overview() {
    const { tr, number } = useCivicLocale();
    const stats = useResource<Analytics>("/admin/analytics", 20000);
    const data = stats.data;
    return <><Feedback loading={stats.loading} error={stats.error} retry={() => void stats.reload()}/>{data && <><div className="civic-stats"><div><strong>{number(Object.values(data.by_status).reduce((a, b) => a + b, 0))}</strong><span>{tr("Total reports")}</span></div><div><strong>{number(data.by_status.resolved || 0)}</strong><span>{tr("Confirmed resolutions")}</span></div><div><strong>{number(data.users)}</strong><span>{tr("Accounts")}</span></div><div><strong>{number(data.workers)}</strong><span>{tr("Approved workers")}</span></div></div><div className="civic-detail-grid"><Bars title={tr("Reports by status")} values={data.by_status}/><Bars title={tr("Reports by category")} values={data.by_category}/></div><div className="civic-detail-grid"><section className="civic-card"><h2>{tr("Where help is needed")}</h2>{data.by_area.map(a => <div className="civic-ledger-row" key={a.area}><strong>{a.area}</strong><span>{number(a.total)}{tr(" reports \u00B7 ")}{number(a.resolved)}{tr(" resolved")}</span></div>)}<p>{number(data.unmapped_reports)}{tr(" reports are not yet linked to a catalogued road.")}</p></section><section className="civic-card"><h2>{tr("Community point leaders")}</h2>{data.leaders.map((p, i) => <div className="civic-ledger-row" key={p.id}><span>{number(i + 1)}. {p.name}</span><strong>{number(p.points)}{tr(" pts")}</strong></div>)}{!data.leaders.length && <p>{tr("Contributions will appear here.")}</p>}</section></div></>}</>;
}
function Reports() {
    const { tr } = useCivicLocale();
    const [q, setQ] = useState("");
    const [search, setSearch] = useState("");
    const [page, setPage] = useState(0);
    const rows = useResource<Complaint[]>(`/complaints?q=${encodeURIComponent(search)}&offset=${page * 30}`);
    return <><CivicForm className="civic-toolbar" onSubmit={e => { e.preventDefault(); setSearch(q); setPage(0); }}><input value={q} maxLength={150} onChange={e => setQ(e.target.value)} aria-label={tr("Search all reports")} placeholder={tr("Search by area, road or complaint")}/><button className="button">{tr("Search")}</button></CivicForm><p>{tr("Open a report to assign a worker or request automatic assignment.")}</p><Feedback loading={rows.loading} error={rows.error} empty={!rows.data?.length}/><div className="civic-grid">{rows.data?.map(row => <ComplaintCard key={row.id} row={row}/>)}</div><Pager page={page} setPage={setPage} more={rows.data?.length === 30}/></>;
}
function Pager({ page, setPage, more }: {
    page: number;
    setPage: (n: number) => void;
    more: boolean;
}) {
    const { tr, number } = useCivicLocale();
    return <div className="civic-toolbar"><button className="button secondary" disabled={!page} onClick={() => setPage(page - 1)}>{tr("Previous")}</button><span>{tr("Page ")}{number(page + 1)}</span><button className="button secondary" disabled={!more} onClick={() => setPage(page + 1)}>{tr("Next")}</button></div>;
}
function People({ role }: {
    role: string;
}) {
    const { tr, label, number } = useCivicLocale();
    const [q, setQ] = useState("");
    const [search, setSearch] = useState("");
    const [page, setPage] = useState(0);
    const [error, setError] = useState("");
    const [busy, setBusy] = useState(false);
    const rows = useResource<Account[]>(`/admin/users?${new URLSearchParams({ q: search, ...(role && { role }), offset: String(page * 30) })}`);
    async function block(e: FormEvent<HTMLFormElement>, account: Account) {
        e.preventDefault();
        setBusy(true);
        setError("");
        const reason = new FormData(e.currentTarget).get("reason");
        try {
            await mutate(`/admin/users/${account.id}/block`, { blocked: account.is_active, reason }, "PATCH");
            await rows.reload();
        }
        catch (e) {
            setError(message(e));
        }
        finally {
            setBusy(false);
        }
    }
    return <><CivicForm className="civic-toolbar" onSubmit={e => { e.preventDefault(); setSearch(q); setPage(0); }}><input aria-label={tr("Search accounts")} placeholder={tr("Name, email or phone")} value={q} maxLength={100} onChange={e => setQ(e.target.value)}/><button className="button">{tr("Search")}</button></CivicForm><Feedback loading={rows.loading} error={error || rows.error} empty={!rows.data?.length}/><div className="civic-grid">{rows.data?.map(account => <article className="civic-card" key={account.id}><h3>{account.name}</h3><p>{account.email}<br />{account.phone || tr("No phone supplied")}</p><div className="civic-card-meta"><span>{label(account.role)}</span><span>{number(account.points)}{tr(" pts")}</span><span>{account.is_active ? tr("Active") : tr("Blocked")}</span></div>{account.role !== "admin" && <CivicForm className="civic-form" onSubmit={e => void block(e, account)}><label>{tr("Reason")}<input name="reason" required minLength={5} maxLength={1000}/></label><button className="button secondary" disabled={busy}>{account.is_active ? tr("Block account & revoke sessions") : tr("Unblock account")}</button></CivicForm>}</article>)}</div><Pager page={page} setPage={setPage} more={rows.data?.length === 30}/></>;
}
function Applications() {
    const { tr } = useCivicLocale();
    const [page, setPage] = useState(0);
    const rows = useResource<Application[]>(`/admin/worker-applications?offset=${page * 30}`);
    const [error, setError] = useState("");
    const [busy, setBusy] = useState(false);
    async function review(e: FormEvent<HTMLFormElement>, id: string) {
        e.preventDefault();
        const data = new FormData(e.currentTarget);
        setBusy(true);
        setError("");
        try {
            await mutate(`/admin/worker-applications/${id}/review`, { approve: data.get("decision") === "approve", note: data.get("note") });
            await rows.reload();
        }
        catch (e) {
            setError(message(e));
        }
        finally {
            setBusy(false);
        }
    }
    return <><Feedback loading={rows.loading} error={error || rows.error} empty={!rows.data?.length}/><div className="civic-grid">{rows.data?.map(a => <article className="civic-card" key={a.user_id}><h3>{a.name}</h3><p>{a.email}</p><p>{a.has_nid_number ? tr("NID fingerprint supplied") : tr("Image-based application")}</p>{a.nid_image_url && <a href={mediaUrl(a.nid_image_url)} className="text-link" target="_blank" rel="noopener noreferrer">{tr("Inspect private identity document \u2197")}</a>}<CivicForm className="civic-form" onSubmit={e => void review(e, a.user_id)}><label>{tr("Review notes")}<textarea name="note" required minLength={3} maxLength={1000}/></label><label>{tr("Decision")}<select name="decision"><option value="approve">{tr("Approve worker")}</option><option value="reject">{tr("Reject application")}</option></select></label><button className="button" disabled={busy}>{tr("Save decision")}</button></CivicForm></article>)}</div><Pager page={page} setPage={setPage} more={rows.data?.length === 30}/></>;
}
function Moderation() {
    const { tr, label } = useCivicLocale();
    const [page, setPage] = useState(0);
    const rows = useResource<Case[]>(`/admin/moderation?offset=${page * 30}`);
    const [error, setError] = useState("");
    const [busy, setBusy] = useState(false);
    async function review(e: FormEvent<HTMLFormElement>, id: string) {
        e.preventDefault();
        const data = new FormData(e.currentTarget);
        setBusy(true);
        setError("");
        try {
            await mutate(`/admin/moderation/${id}/review`, { status: data.get("status"), note: data.get("note") });
            await rows.reload();
        }
        catch (e) {
            setError(message(e));
        }
        finally {
            setBusy(false);
        }
    }
    return <><p>{tr("Review the original report and image evidence. Account blocks are managed in Users or Workers.")}</p><Feedback loading={rows.loading} error={error || rows.error} empty={!rows.data?.length}/><div className="civic-grid">{rows.data?.map(row => <article key={row.id} className="civic-card"><span className="civic-badge disputed">{label(row.kind)}</span><h3>{row.subject_name}</h3><Link className="text-link" href={`/complaints/${row.complaint_id}`}>{tr("Open original complaint \u2192")}</Link>{row.evidence.map((e, i) => <p key={i}>{e.comment || tr("Image evidence")} · <a className="text-link" href={mediaUrl(e.image_url)} target="_blank" rel="noopener noreferrer">{tr("View image \u2197")}</a></p>)}<CivicForm className="civic-form" onSubmit={e => void review(e, row.id)}><label>{tr("Review notes")}<textarea name="note" required minLength={5} maxLength={1000}/></label><label>{tr("Outcome")}<select name="status"><option value="actioned">{tr("Evidence accepted / reviewed")}</option><option value="dismissed">{tr("Dismiss case")}</option></select></label><button className="button" disabled={busy}>{tr("Save review")}</button></CivicForm></article>)}</div><Pager page={page} setPage={setPage} more={rows.data?.length === 30}/></>;
}
function Catalog() {
    const { tr, label, number } = useCivicLocale();
    const areas = useResource<{
        id: string;
        name: string;
    }[]>("/areas");
    const roads = useResource<Road[]>("/map/roads");
    const [error, setError] = useState("");
    const [busy, setBusy] = useState(false);
    async function save(e: FormEvent<HTMLFormElement>, kind: "areas" | "roads") {
        e.preventDefault();
        const form = e.currentTarget;
        const data = new FormData(form);
        setBusy(true);
        setError("");
        try {
            await mutate(`/admin/${kind}`, kind === "areas" ? { name: data.get("name"), ward: data.get("ward") || null } : { name: data.get("name"), area_id: data.get("area_id"), latitude: Number(data.get("latitude")), longitude: Number(data.get("longitude")) });
            form.reset();
            await areas.reload();
            await roads.reload();
        }
        catch (e) {
            setError(message(e));
        }
        finally {
            setBusy(false);
        }
    }
    return <><Feedback error={error || areas.error || roads.error}/><div className="civic-detail-grid"><CivicForm className="civic-card civic-form" onSubmit={e => void save(e, "areas")}><h2>{tr("Add an area")}</h2><label>{tr("Name")}<input name="name" required minLength={3} maxLength={100}/></label><label>{tr("Ward (optional)")}<input name="ward" maxLength={30}/></label><button className="button" disabled={busy}>{tr("Add area")}</button></CivicForm><CivicForm className="civic-card civic-form" onSubmit={e => void save(e, "roads")}><h2>{tr("Add a road")}</h2><label>{tr("Road name")}<input name="name" required minLength={3} maxLength={150}/></label><label>{tr("Area")}<select name="area_id" required defaultValue=""><option value="" disabled>{tr("Select an area")}</option>{areas.data?.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}</select></label><div className="civic-field-row"><label>{tr("Latitude")}<input name="latitude" type="number" step="any" required min={23.6} max={24}/></label><label>{tr("Longitude")}<input name="longitude" type="number" step="any" required min={90.2} max={90.6}/></label></div><button className="button" disabled={busy}>{tr("Add road")}</button></CivicForm></div><section className="civic-card"><h2>{tr("Road catalog")}</h2>{roads.data?.map(r => <div className="civic-ledger-row" key={r.id}><strong>{r.name}</strong><span>{label(r.condition)} · {number(r.open_complaints)}{tr(" open")}</span></div>)}</section></>;
}
