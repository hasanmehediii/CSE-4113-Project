"use client";
import { useCivicLocale } from "@/hooks/useCivicLocale";

import { useState, type FormEvent } from "react";
import Image from "next/image";
import Link from "next/link";
import { mediaUrl, mutate, uploadImage } from "@/lib/api-client";
import { message, useResource, type Complaint, type Resolution } from "@/lib/civic";
import { CivicShell, Feedback, CivicForm, CivicFileInput } from "./CivicUI";
import { useApp } from "./Providers";
import IncidentReports from "./IncidentReports";
async function imageFrom(data: FormData) {
    const file = data.get("photo");
    return file instanceof File && file.size ? uploadImage(file) : String(data.get("image_url") || "") || null;
}
function PhotoFields({ required = false }: {
    required?: boolean;
}) {
    const { tr } = useCivicLocale();
    return <><label>{tr("Evidence photo (optional upload)")}<CivicFileInput /></label><label>{required ? tr("Or an evidence image link") : tr("Image link (optional)")}<input name="image_url" type="url" placeholder="https://…"/></label><small>{tr("JPEG, PNG or WebP up to 5 MB. ")}{required && tr("An image or link is required.")}</small></>;
}
export default function ComplaintDetail({ id }: {
    id: string;
}) {
    const { tr, label, date, number } = useCivicLocale();
    const report = useResource<Complaint>(`/complaints/${encodeURIComponent(id)}`, 20000);
    const { user } = useApp();
    const [error, setError] = useState("");
    const [busy, setBusy] = useState(false);
    const [success, setSuccess] = useState("");
    const row = report.data;
    const canVote = user?.role === "citizen" && user.email_verified;
    // Scope the request to the current account so switching users hides old permissions immediately.
    const participation = useResource<{ is_reporter: boolean }>(user && user.role !== "admin"
        ? `/me/complaints/${encodeURIComponent(id)}/participation?viewer=${encodeURIComponent(user.id)}` : null, 20000);
    const independent = participation.data?.is_reporter === false;
    async function action(path: string, data: unknown, method = "POST") {
        setBusy(true);
        setError("");
        setSuccess("");
        try {
            await mutate(path, data, method);
            setSuccess("Saved. Thank you for helping your community.");
            await report.reload();
        }
        catch (e) {
            setError(message(e));
        }
        finally {
            setBusy(false);
        }
    }
    async function evidence(event: FormEvent<HTMLFormElement>, path: string, type: "false" | "resolve" | "dispute") {
        event.preventDefault();
        if (busy)
            return;
        const form = event.currentTarget;
        const data = new FormData(form);
        setBusy(true);
        setError("");
        setSuccess("");
        try {
            const image_url = await imageFrom(data);
            if (type !== "resolve" && !image_url)
                throw new Error("Please upload evidence or supply an image link.");
            await mutate(path, { comment: data.get("comment") || null, image_url, ...(type === "dispute" && { value: -1 }) }, type === "dispute" ? "PUT" : "POST");
            form.reset();
            setSuccess("Saved. The report has been updated.");
            await report.reload();
        }
        catch (e) {
            setError(message(e));
        }
        finally {
            setBusy(false);
        }
    }
    return <CivicShell title={row?.title || tr("Community report")} intro={row?.address}><Feedback error={report.error || error} loading={report.loading} retry={() => void report.reload()}/>{success && <p className="notice" role="status">{tr(success)}</p>}{row && <><div className="civic-detail-grid"><article className="civic-card"><div className="civic-card-meta"><span className={`civic-badge ${row.status}`}>{label(row.status)}</span><span>{label(row.category_code)}</span><span>{row.kind === "road_update" ? `${tr("Road update:")} ${label(row.condition)}` : tr("Civic complaint")}</span></div><p className="civic-description">{row.description}</p><p>{tr("Reported by ")}{row.author_name} · {date(row.created_at)}{tr(" (Dhaka)")}</p><p><a className="text-link" href={`https://www.openstreetmap.org/?mlat=${row.latitude}&mlon=${row.longitude}#map=17/${row.latitude}/${row.longitude}`} target="_blank" rel="noopener noreferrer">{tr("View exact location \u2197")}</a></p><div className="civic-photos">{row.images.map(url => <a key={url} href={mediaUrl(url)} target="_blank" rel="noopener noreferrer"><Image src={mediaUrl(url)} width={640} height={400} alt={tr("Community report evidence")} unoptimized/></a>)}</div><div className="civic-toolbar"><span>{number(row.likes)}{tr(" support \u00B7 ")}{number(row.dislikes)}{tr(" disagree")}</span>{canVote && independent && row.status !== "false" && <><button className="button secondary" disabled={busy} onClick={() => void action(`/complaints/${row.id}/vote`, { value: 1 }, "PUT")}>{tr("Support")}</button><button className="button secondary" disabled={busy} onClick={() => void action(`/complaints/${row.id}/vote`, { value: -1 }, "PUT")}>{tr("Disagree")}</button></>}</div>{participation.data?.is_reporter && <p>{tr("You reported this incident. Incident voting is available to other citizens.")}</p>}{user && user.role !== "admin" && <Feedback error={participation.error} loading={participation.loading} retry={() => void participation.reload()}/>}<>{!user && <Link className="text-link" href="/login">{tr("Sign in to contribute or verify work")}</Link>}</></article><aside className="civic-card"><h2>{tr("What happens next?")}</h2><p>{tr("Workers handle assigned issues. Completion becomes confirmed after 5 distinct verified citizens approve it.")}</p><p>{tr("Incident voting and false-report evidence apply to the shared blockage. Five citizen dislikes and evidence from two approved workers trigger moderation; the original incident reporter can lose their points.")}</p><p>{tr("Category priority: ")}{number(row.priority)}{tr("/100. Source: ")}{label(row.priority_source)}{tr(". ML category suggestions inform urgency when confidence is at least 60%.")}</p></aside></div>{user?.role === "admin" && <AssignmentControls id={row.id} disabled={busy || !["open", "disputed", "assigned"].includes(row.status) || row.kind !== "complaint"} reassign={row.status === "assigned"} currentWorker={row.active_assignment?.worker_id} action={action}/>}{user?.role === "worker" && user.email_verified && <div className="civic-detail-grid">{row.active_assignment?.worker_id === user.id && participation.data?.is_reporter && <p>{tr("You reported this incident. Ask the mayor to reassign this work.")}</p>}{row.active_assignment?.worker_id === user.id && independent && <CivicForm className="civic-card civic-form" onSubmit={e => void evidence(e, `/complaints/${id}/resolutions`, "resolve")}><fieldset disabled={busy}><h2>{tr("Submit completed work")}</h2><label>{tr("Work summary")}<textarea name="comment" required minLength={5} maxLength={2000} placeholder={tr("We have cleaned Mirpur-10 Lane 7\u2026")}/></label><PhotoFields /><button className="button">{tr("Submit for community confirmation")}</button></fieldset></CivicForm>}{row.status !== "false" && independent && <CivicForm className="civic-card civic-form" onSubmit={e => void evidence(e, `/complaints/${id}/false-reports`, "false")}><fieldset disabled={busy}><h2>{tr("Report false information")}</h2><label>{tr("Explain your evidence")}<textarea name="comment" required minLength={5} maxLength={1000}/></label><PhotoFields required/><button className="button secondary">{tr("Submit false-information evidence")}</button></fieldset></CivicForm>}</div>}{row.incident_id && row.incident_id !== row.id && <p><Link className="text-link" href={`/complaints/${row.incident_id}`}>{tr("Open the shared incident")}</Link></p>}{(row.incident_report_count || 1) > 1 && <IncidentReports key={row.incident_id || row.id} incidentId={row.incident_id || row.id} total={row.incident_report_count!} reporters={row.incident_reporter_count || 1}/>}<h2 className="civic-section-title">{tr("Work & community verification")}</h2>{!row.resolutions?.length && <p className="civic-empty">{tr("No work completion has been submitted yet.")}</p>}{row.resolutions?.map(resolution => <ResolutionCard key={resolution.id} row={resolution} canVote={Boolean(canVote && row.status !== "false")} busy={busy} like={() => void action(`/resolutions/${resolution.id}/vote`, { value: 1 }, "PUT")} dispute={e => void evidence(e, `/resolutions/${resolution.id}/vote`, "dispute")}/>)}</>}</CivicShell>;
}
function ResolutionCard({ row, canVote, busy, like, dispute }: {
    row: Resolution;
    canVote: boolean;
    busy: boolean;
    like: () => void;
    dispute: (e: FormEvent<HTMLFormElement>) => void;
}) {
    const { tr, label, date, number } = useCivicLocale();
    return <article className="civic-card"><div className="civic-card-meta"><strong>{row.worker_name}</strong><span className={`civic-badge ${row.status}`}>{label(row.status)}</span><span>{date(row.created_at)}</span></div><p className="civic-description">{row.comment}</p>{row.image_url && <a className="text-link" href={mediaUrl(row.image_url)} target="_blank" rel="noopener noreferrer">{tr("View worker evidence \u2197")}</a>}<p>{number(row.likes)}{tr("/5 community approvals \u00B7 ")}{number(row.dislikes)}{tr(" disputes")}</p>{canVote && row.status !== "disputed" && <><button className="button" disabled={busy} onClick={like}>{tr("I confirm this work")}</button><details className="civic-dispute"><summary>{tr("Disagree? Submit image evidence")}</summary><CivicForm className="civic-form" onSubmit={dispute}><fieldset disabled={busy}><label>{tr("What remains unresolved?")}<textarea name="comment" maxLength={1000}/></label><PhotoFields required/><button className="button secondary">{tr("Send dispute to the mayor")}</button></fieldset></CivicForm></details></>}</article>;
}
function AssignmentControls({ id, disabled, reassign, currentWorker, action }: {
    id: string;
    disabled: boolean;
    reassign: boolean;
    currentWorker?: string;
    action: (path: string, data: unknown) => Promise<void>;
}) {
    const { tr } = useCivicLocale();
    const workers = useResource<{
        id: string;
        name: string;
        is_active: boolean;
    }[]>("/admin/users?role=worker&limit=100");
    return <CivicForm className="civic-card civic-form" onSubmit={e => {
        e.preventDefault();
        void action(`/admin/complaints/${id}/assign`, { worker_id: new FormData(e.currentTarget).get("worker_id") || null, reassign });
    }}><fieldset disabled={disabled}>
        <h2>{tr(reassign ? "Reassign work" : "Assign work")}</h2>
        <Feedback error={workers.error}/>
        {reassign && <p>{tr("The previous assignment will be cancelled. Only the replacement worker can submit completion.")}</p>}
        <label>{tr("Worker")}<select name="worker_id"><option value="">{tr("Automatically choose an available worker")}</option>{workers.data?.filter(w => w.is_active && (!reassign || w.id !== currentWorker)).map(w => <option key={w.id} value={w.id}>{w.name}</option>)}</select></label>
        <p>{tr("Automatic assignment prefers lighter workloads, then nearby workers who shared their location within 15 minutes.")}</p>
        <button className="button">{tr(reassign ? "Reassign complaint" : "Assign complaint")}</button>
    </fieldset></CivicForm>;
}
