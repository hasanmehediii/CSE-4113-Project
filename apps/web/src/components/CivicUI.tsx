"use client";
import { useCivicLocale } from "@/hooks/useCivicLocale";

import Link from "next/link";
import { useEffect, useId, useRef, useState, type ReactNode, type ComponentPropsWithoutRef } from "react";
import { useApp } from "./Providers";
import { type Complaint } from "@/lib/civic";
import { civicValidationMessage } from "@/lib/civic-i18n";

export function CivicForm(props: ComponentPropsWithoutRef<"form">) {
    const { language } = useCivicLocale();
    const form = useRef<HTMLFormElement>(null);
    useEffect(() => {
        form.current?.querySelectorAll<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>("input,select,textarea").forEach(field => field.setCustomValidity(""));
    }, [language]);
    return <form {...props} ref={form} onInvalidCapture={event => {
        const field = event.target;
        if (field instanceof HTMLInputElement || field instanceof HTMLSelectElement || field instanceof HTMLTextAreaElement) field.setCustomValidity(civicValidationMessage(field.validity, field, language));
        props.onInvalidCapture?.(event);
    }} onInputCapture={event => {
        const field = event.target;
        if (field instanceof HTMLInputElement || field instanceof HTMLSelectElement || field instanceof HTMLTextAreaElement) field.setCustomValidity("");
        props.onInputCapture?.(event);
    }} onChangeCapture={event => {
        const field = event.target;
        if (field instanceof HTMLInputElement || field instanceof HTMLSelectElement || field instanceof HTMLTextAreaElement) field.setCustomValidity("");
        props.onChangeCapture?.(event);
    }} />;
}

export function CivicFileInput({ name = "photo" }: { name?: string }) {
    const { tr } = useCivicLocale();
    const input = useRef<HTMLInputElement>(null);
    const id = useId();
    const [selected, setSelected] = useState("");
    useEffect(() => {
        const form = input.current?.form;
        const reset = () => setSelected("");
        form?.addEventListener("reset", reset);
        return () => form?.removeEventListener("reset", reset);
    }, []);
    return <span className="civic-file-control"><input ref={input} id={id} className="civic-file-native" type="file" name={name} accept="image/jpeg,image/png,image/webp" aria-label={tr("Choose a photo")} onChange={event => setSelected(event.currentTarget.files?.[0]?.name || "")} /><button type="button" className="button secondary" aria-controls={id} onClick={() => input.current?.click()}>{tr("Choose a photo")}</button><span aria-live="polite">{selected || tr("No photo selected")}</span></span>;
}
export function CivicShell({ title, intro, children }: {
    title: string;
    intro?: string;
    children: ReactNode;
}) {
    const { tr } = useCivicLocale();
    const { user } = useApp();
    return <main id="main" className="container civic-shell"><nav className="civic-nav" aria-label={tr("City services")}><Link href="/map">{tr("Live map")}</Link><Link href="/complaints">{tr("Community reports")}</Link><Link href="/complaints/new">{tr("Report an issue")}</Link>{user && <Link href="/community">{tr("My contributions")}</Link>}{user?.role === "citizen" && <Link href="/workers/apply">{tr("Become a worker")}</Link>}{user?.role === "worker" && <Link href="/worker">{tr("Worker dashboard")}</Link>}{user?.role === "admin" && <Link href="/admin">{tr("Mayor dashboard")}</Link>}</nav><header className="civic-heading"><span className="eyebrow">{tr("DHAKA \u2022 COMMUNITY SERVICES")}</span><h1>{title}</h1>{intro && <p>{intro}</p>}</header>{children}</main>;
}
export function Gate({ roles, children }: {
    roles?: string[];
    children: ReactNode;
}) {
    const { tr } = useCivicLocale();
    const { user, loading, authUnavailable, refresh } = useApp();
    if (loading)
        return <CivicShell title={tr("Opening your workspace\u2026")}><p role="status">{tr("Checking your account.")}</p></CivicShell>;
    if (authUnavailable)
        return <CivicShell title={tr("Connection unavailable")}><button className="button" onClick={() => void refresh()}>{tr("Retry")}</button></CivicShell>;
    if (!user)
        return <CivicShell title={tr("Sign in to contribute")}><p>{tr("Everyone can view the map. Sign in to report, vote, or work on an issue.")}</p><Link className="button" href="/login">{tr("Sign in")}</Link></CivicShell>;
    if (!user.email_verified)
        return <CivicShell title={tr("Verify your email first")}><Link className="button" href="/verify-email">{tr("Verify email")}</Link></CivicShell>;
    if (roles && !roles.includes(user.role))
        return <CivicShell title={tr("This workspace needs a different account role")}><Link className="button" href="/community">{tr("My contributions")}</Link></CivicShell>;
    return children;
}
export function Feedback({ error, loading, empty, retry }: {
    error?: string;
    loading?: boolean;
    empty?: boolean;
    retry?: () => void;
}) {
    const { tr } = useCivicLocale();
    return <>{error && <p role="alert" className="alert error">{tr(error)} {retry && <button type="button" onClick={retry}>{tr("Retry")}</button>}</p>}{loading && <p role="status">{tr("Loading\u2026")}</p>}{!loading && !error && empty && <p className="civic-empty">{tr("No reports match this view yet.")}</p>}</>;
}
export function ComplaintCard({ row }: {
    row: Complaint;
}) {
    const { tr, label, date, number } = useCivicLocale();
    return <article className="civic-card">
        <div className="civic-card-meta"><span className={`civic-badge ${row.status}`}>{label(row.status)}</span><span>{label(row.category_code)}</span>{row.kind === "road_update" && <span>{tr("Road update \u00B7 ")}{label(row.condition)}</span>}</div>
        <h3><Link href={`/complaints/${row.id}`}>{row.title}</Link></h3><p>{row.address}</p>
        <p className="civic-excerpt">{row.description}</p>
        {(row.incident_report_count || 1) > 1 && <p>{number(row.incident_report_count!)} {tr("reports from")} {number(row.incident_reporter_count || 1)} {tr("reporters")}</p>}
        <footer><span>{row.author_name} · {date(row.created_at)}</span><span>+{number(row.likes)} / −{number(row.dislikes)}</span></footer>
    </article>;
}
