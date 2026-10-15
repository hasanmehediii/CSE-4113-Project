"use client";
import Link from "next/link";
import { useState, type FormEvent } from "react";
import { mutate } from "@/lib/api-client";
import { message } from "@/lib/civic";
import { CivicShell, Feedback } from "@/components/CivicUI";

export default function RecoveryPage() {
  const [success, setSuccess] = useState(false); const [error, setError] = useState(""); const [busy, setBusy] = useState(false);
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault(); const data = new FormData(e.currentTarget); setBusy(true); setError("");
    try { await mutate("/auth/recover", Object.fromEntries(data)); setSuccess(true); }
    catch (e) { setError(message(e)); } finally { setBusy(false); }
  }
  return <CivicShell title="Recover with a password you remember." intro="Use your current password or one of your last four passwords, your date of birth, and a link delivered to your email.">{success ? <div className="civic-card" role="status"><h2>Check your inbox</h2><p>If your details match an eligible account, a single-use password reset link will arrive by email.</p><Link className="button" href="/reset-password">Enter email token</Link></div> : <form className="civic-card civic-form" onSubmit={submit}><label>Email<input name="email" type="email" required maxLength={320} autoComplete="email" /></label><label>Date of birth<input type="date" name="date_of_birth" required /></label><label>A password you remember<input type="password" name="remembered_password" required maxLength={128} autoComplete="off" /></label><p>These details do not sign you in. You must still open the email link and choose a new password.</p><Feedback error={error} /><button className="button" disabled={busy}>{busy ? "Checking…" : "Request recovery email"}</button><Link className="text-link" href="/forgot-password">Use ordinary email password reset</Link></form>}</CivicShell>;
}
