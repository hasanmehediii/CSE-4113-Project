"use client";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useApp } from "@/components/Providers";
import { api, ApiError, mutate } from "@/lib/api-client";
import type { Session } from "@/lib/auth";
import { errorMessage } from "@/components/AuthForm";

export default function AccountPage() {
  const { t, language, user, loading, authUnavailable, refresh, logout, setUser } = useApp();
  const router = useRouter();
  const [sessions, setSessions] = useState<Session[]>([]);
  const [failure, setFailure] = useState<unknown>(null);
  const [retryAction, setRetryAction] = useState<(() => Promise<void>) | null>(null);
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);
  const loadSessions = useCallback(async () => {
    try { setSessions(await api<Session[]>("/auth/sessions")); setFailure(null); setRetryAction(null); }
    catch (error) { if (error instanceof ApiError && error.status === 401) { setUser(null); router.replace("/login"); } else { setFailure(error); setRetryAction(() => loadSessions); } }
  }, [router, setUser]);
  useEffect(() => {
    if (user) {
      let active = true;
      api<Session[]>("/auth/sessions").then(rows => { if (active) setSessions(rows); }).catch(error => {
        if (!active) return;
        if (error instanceof ApiError && error.status === 401) { setUser(null); router.replace("/login"); } else { setFailure(error); setRetryAction(() => loadSessions); }
      });
      return () => { active = false; };
    }
    if (!loading && !authUnavailable) router.replace("/login");
  }, [user, loading, authUnavailable, router, setUser, loadSessions]);
  async function action(kind: "logout" | "all" | "verify" | "revoke", id?: string) {
    setBusy(true); setFailure(null); setRetryAction(null);
    try {
      if (kind === "logout" || kind === "all") { await logout(kind === "all"); router.replace("/login"); }
      else if (kind === "verify") { await mutate("/auth/resend-verification", { email: user?.email }); setSent(true); }
      else { await mutate(`/auth/sessions/${encodeURIComponent(id!)}`, undefined, "DELETE"); await loadSessions(); }
    } catch (error) { setFailure(error); setRetryAction(() => () => action(kind, id)); } finally { setBusy(false); }
  }
  if (loading || !user) return <main id="main" className="account container"><div className="account-card"><h1>{t(authUnavailable ? "Connection unavailable" : "Opening your account…", authUnavailable ? "সংযোগ পাওয়া যাচ্ছে না" : "অ্যাকাউন্ট খোলা হচ্ছে…")}</h1>{authUnavailable && <button className="button" onClick={() => void refresh()}>{t("Try again", "আবার চেষ্টা করুন")}</button>}</div></main>;
  return <main id="main" className="account container"><span className="eyebrow">{t("YOUR COMMUNITY STARTS HERE", "আপনার কমিউনিটির শুরু এখানে")}</span><h1>{t("Hello,", "স্বাগতম,")} {user.name}<span className="brand-blue">.</span></h1><p>{t("Good to have you on board. Manage your account and keep it secure.", "আপনাকে পেয়ে ভালো লাগছে। অ্যাকাউন্টের তথ্য ও নিরাপত্তা দেখুন।")}</p>
    {authUnavailable && <p role="status" className="alert">{t("We couldn’t refresh your account. Check your connection.", "অ্যাকাউন্ট হালনাগাদ করা যায়নি। সংযোগ পরীক্ষা করুন।")}</p>}
    {failure !== null && <p className="alert error" role="alert">{errorMessage(failure, t)} <button onClick={() => { if (retryAction) void retryAction(); else void loadSessions(); }}>{t("Retry", "আবার চেষ্টা")}</button></p>}
    <nav className="account-service-links" aria-label={t("My services", "আমার সেবা")}><Link className="button" href="/community">{t("My reports & points", "আমার অভিযোগ ও পয়েন্ট")}</Link><Link className="button secondary" href="/complaints">{t("Community reports", "কমিউনিটি রিপোর্ট")}</Link><Link className="button secondary" href="/complaints/new">{t("Report an issue", "সমস্যা জানান")}</Link><Link className="button secondary" href={user.role === "admin" ? "/admin" : user.role === "worker" ? "/worker" : "/workers/apply"}>{user.role === "admin" ? t("Mayor dashboard", "মেয়র ড্যাশবোর্ড") : user.role === "worker" ? t("Worker dashboard", "সেবাকর্মী ড্যাশবোর্ড") : t("Apply as worker", "সেবাকর্মী আবেদন")}</Link></nav>
    <div className="account-grid"><section className="account-card"><h2>{t("Your profile", "আপনার প্রোফাইল")}</h2><dl><dt>{t("Name", "নাম")}</dt><dd>{user.name}</dd><dt>{t("Email", "ইমেইল")}</dt><dd>{user.email}</dd><dt>{t("Account type", "অ্যাকাউন্টের ধরন")}</dt><dd>{user.role === "admin" ? t("Administrator", "প্রশাসক") : user.role === "worker" ? t("Service worker", "সেবাকর্মী") : t("Resident", "বাসিন্দা")}</dd></dl><span className={`verification-badge ${user.email_verified ? "verified" : ""}`}>{user.email_verified ? t("✓ Email verified", "✓ ইমেইল যাচাই হয়েছে") : t("Email not verified", "ইমেইল যাচাই হয়নি")}</span>{!user.email_verified && <div className="verification-actions"><button className="button secondary" disabled={busy || sent} onClick={() => void action("verify")}>{t(sent ? "Email requested" : "Resend verification", sent ? "ইমেইল পাঠানোর অনুরোধ হয়েছে" : "আবার যাচাইকরণ ইমেইল পাঠান")}</button><Link className="text-link" href="/verify-email">{t("Enter verification token", "যাচাইকরণ টোকেন দিন")}</Link>{sent && <p role="status">{t("Check your inbox and spam folder.", "ইনবক্স ও স্প্যাম ফোল্ডার দেখুন।")}</p>}</div>}</section>
    <section className="account-card"><h2>{t("What’s next?", "এরপর কী?")}</h2><span className="eyebrow">{t("IN DEVELOPMENT", "তৈরি হচ্ছে")}</span><h3>{t("Your neighbourhood, connected.", "সংযুক্ত হোক আপনার পাড়া।")}</h3><p>{t("Report issues, follow the live map, and track confirmed work through your community workspace.", "অভিযোগ, লাইভ মানচিত্র ও কাজের অগ্রগতি দেখার সুবিধা আসছে। আপনার অ্যাকাউন্ট প্রস্তুত।")}</p><Link className="text-link" href="/#how-it-works">{t("Explore the vision", "আমাদের পরিকল্পনা দেখুন")} ↗</Link><div className="account-security"><Link href="/forgot-password">{t("Reset my password", "পাসওয়ার্ড রিসেট করুন")}</Link><button className="button secondary" disabled={busy} onClick={() => void action("logout")}>{t("Sign out", "লগআউট")}</button></div></section></div>
    <section className="account-card sessions"><div className="section-heading"><div><h2>{t("Active sessions", "সক্রিয় সেশন")}</h2><p>{t("Recognise every session? Sign out of any you don’t use.", "সব সেশন কি পরিচিত? অব্যবহৃত সেশন থেকে লগআউট করুন।")}</p></div><button className="button secondary" disabled={busy} onClick={() => void action("all")}>{t("Sign out everywhere", "সব সেশন থেকে লগআউট")}</button></div>{sessions.map(session => <div key={session.id} className="session-row"><div><strong>{session.current ? t("This session", "বর্তমান সেশন") : t("Other session", "অন্য সেশন")}</strong><small>{t("Last active: ", "সর্বশেষ সক্রিয়: ")}{new Date(session.last_seen_at * 1000).toLocaleString(language === "bn" ? "bn-BD" : "en-GB")}</small></div>{session.current ? <span className="verification-badge verified">{t("Current", "বর্তমান")}</span> : <button className="text-link" disabled={busy} onClick={() => void action("revoke", session.id)}>{t("Revoke", "বাতিল করুন")}</button>}</div>)}</section>
  </main>;
}
