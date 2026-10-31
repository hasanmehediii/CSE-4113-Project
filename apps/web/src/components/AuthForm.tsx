"use client";
import { useEffect, useState, type FormEvent } from "react";
import AuthLayout from "./AuthLayout";
import { CivicForm } from "./CivicUI";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useApp } from "./Providers";
import { ApiError, mutate } from "@/lib/api-client";
import type { User } from "@/lib/auth";
import GoogleSignIn from "./GoogleSignIn";
import RegistrationForm from "./RegistrationForm";
import { accountHome } from "@/lib/auth";

export type AuthMode = "login" | "register" | "forgot-password" | "reset-password" | "verify-email" | "resend-verification";
const headings: Record<AuthMode, [string, string]> = {
  login: ["Welcome back.", "আবার স্বাগতম।"], register: ["A better Dhaka starts with you.", "সুন্দর ঢাকার শুরু আপনার হাতে।"],
  "forgot-password": ["Let’s get you back in.", "আবার ফিরে আসুন।"], "reset-password": ["A fresh start.", "নতুন করে শুরু।"],
  "verify-email": ["Make it official.", "ইমেইল নিশ্চিত করুন।"], "resend-verification": ["A new verification link.", "নতুন যাচাইকরণ লিংক।"],
};
export function errorMessage(error: unknown, t: (en: string, bn: string) => string) {
  if (!(error instanceof ApiError)) return t("Could not connect. Check your connection and try again.", "সংযোগ করা যায়নি। ইন্টারনেট সংযোগ পরীক্ষা করে আবার চেষ্টা করুন।");
  if (error.status === 429) return t("Too many attempts. Please wait a few minutes and try again.", "অনেকবার চেষ্টা করা হয়েছে। কয়েক মিনিট পরে আবার চেষ্টা করুন।");
  if (error.status === 503) return t("Sign-in is temporarily unavailable. Please try again shortly.", "লগইন সেবা সাময়িকভাবে বন্ধ। কিছুক্ষণ পরে চেষ্টা করুন।");
  if (error.status === 401) return t("Your email or password is incorrect, or your session has expired.", "ইমেইল বা পাসওয়ার্ড সঠিক নয়, অথবা সেশনের মেয়াদ শেষ।");
  if (error.status === 409) return t("Use your existing sign-in method for this email address.", "এই ইমেইলের জন্য আগে ব্যবহার করা পদ্ধতিতে লগইন করুন।");
  if (error.status === 400) return t("This link is invalid or expired. Request a new email and try again.", "লিংকটি সঠিক নয় বা মেয়াদ শেষ। নতুন ইমেইল পাঠানোর অনুরোধ করুন।");
  if (error.status === 403) return t("Your security check expired. Please try again.", "নিরাপত্তা যাচাইয়ের মেয়াদ শেষ। আবার চেষ্টা করুন।");
  if (error.status === 422) return t("Check your details. New passwords must be 8–128 characters.", "তথ্য যাচাই করুন। নতুন পাসওয়ার্ড ৮–১২৮ অক্ষরের হতে হবে।");
  return t("Something went wrong. Please try again.", "কিছু সমস্যা হয়েছে। আবার চেষ্টা করুন।");
}

export default function AuthForm({ mode }: { mode: AuthMode }) {
  return mode === "register" ? <RegistrationForm /> : <AccountAccessForm mode={mode} />;
}

function AccountAccessForm({ mode }: { mode: AuthMode }) {
  const { t, setUser, user, refresh } = useApp();
  const router = useRouter();
  const [token, setToken] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<unknown>(null);
  const [mismatch, setMismatch] = useState(false);
  const [success, setSuccess] = useState(false);
  const accountMode = mode === "login" || mode === "register";
  const hasPassword = accountMode || mode === "reset-password";
  const hasToken = mode === "reset-password" || mode === "verify-email";
  useEffect(() => {
    if (!hasToken) return;
    const value = new URLSearchParams(window.location.hash.slice(1)).get("token");
    // Read the browser-only fragment once after hydration; never submit on mount.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (value) { setToken(value); window.history.replaceState(null, "", window.location.pathname); }
  }, [hasToken]);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (busy) return;
    const form = new FormData(event.currentTarget);
    const password = String(form.get("password") || "");
    setFailure(null); setMismatch(false);
    if ((mode === "register" || mode === "reset-password") && password !== form.get("confirm")) { setMismatch(true); return; }
    setBusy(true);
    const data: Record<string, string> = {};
    if (!hasToken) data[mode === "login" ? "identifier" : "email"] = String(form.get("email")).trim();
    if (hasPassword) data.password = password;
    if (mode === "register") {
      data.name = String(form.get("name")).trim();
      for (const key of ["phone", "date_of_birth", "blood_group"]) {
        const value = String(form.get(key) || "").trim();
        if (value) data[key] = value;
      }
    }
    if (hasToken) data.token = token.trim();
    try {
      const result = await mutate<User>(`/auth/${mode}`, data);
      if (mode === "login") { setUser(result); router.replace(accountHome(result)); }
      else { setSuccess(true); if (mode === "reset-password") setUser(null); if (mode === "verify-email") await refresh(); }
    } catch (error) { setFailure(error); } finally { setBusy(false); }
  }
  return <AuthLayout variant={mode === "login" ? "login" : "recovery"}>
    <section className="auth-panel"><span className="eyebrow">{t("YOUR DUBSIBHAI ACCOUNT", "আপনার ডুবসিভাই অ্যাকাউন্ট")}</span><h1>{t(...headings[mode])}</h1><p className="auth-intro">{t(mode === "login" ? "Sign in and pick up where you left off." : mode === "register" ? "Create your free resident account. Let’s make a difference together." : hasToken ? "Use the link in your email, or paste your email token below." : "Enter your email. We’ll send a link if your account is eligible.", mode === "login" ? "লগইন করে আবার শুরু করুন।" : mode === "register" ? "বিনামূল্যে বাসিন্দা অ্যাকাউন্ট খুলুন। একসাথে পরিবর্তন আনি।" : hasToken ? "ইমেইলের লিংক ব্যবহার করুন অথবা নিচে ইমেইলে পাওয়া টোকেন দিন।" : "ইমেইল দিন। অ্যাকাউন্ট উপযুক্ত হলে একটি লিংক পাঠানো হবে।")}</p>
      {user && accountMode ? <div className="notice"><p>{t("You’re already signed in.", "আপনি ইতোমধ্যে লগইন করেছেন।")}</p><Link className="button" href="/account">{t("Go to my account", "আমার অ্যাকাউন্টে যান")} ↗</Link></div> : success ? <div className="success-panel" role="status"><span className="check-icon">✓</span><h2>{t(hasToken ? "All set!" : "Check your inbox.", hasToken ? "সম্পন্ন হয়েছে!" : "আপনার ইমেইল দেখুন।")}</h2><p>{t(mode === "verify-email" ? "Your email is verified." : mode === "reset-password" ? "Your password has changed. Sign in with your new password." : "If your account is eligible, you’ll receive an email with the next step. Check your spam folder too.", mode === "verify-email" ? "আপনার ইমেইল যাচাই হয়েছে।" : mode === "reset-password" ? "পাসওয়ার্ড পরিবর্তন হয়েছে। নতুন পাসওয়ার্ড দিয়ে লগইন করুন।" : "অ্যাকাউন্ট উপযুক্ত হলে পরবর্তী ধাপের ইমেইল পাবেন। স্প্যাম ফোল্ডারও দেখুন।")}</p><Link className="button" href={user ? "/account" : "/login"}>{t(user ? "My account" : "Back to sign in", user ? "আমার অ্যাকাউন্ট" : "লগইনে ফিরে যান")} ↗</Link>{mode === "register" && <Link className="text-link" href="/resend-verification">{t("Resend verification email", "আবার যাচাইকরণ ইমেইল পাঠান")}</Link>}</div> : <>
      {accountMode && <nav className="auth-mode-switch" aria-label={t("Account access", "অ্যাকাউন্টে প্রবেশ")}><Link href="/login" aria-current={mode === "login" ? "page" : undefined}>{t("Sign in", "লগইন")}</Link><Link href="/register" aria-current={mode === "register" ? "page" : undefined}>{t("Create account", "অ্যাকাউন্ট খুলুন")}</Link></nav>}
      <CivicForm onSubmit={submit} className="auth-form" aria-busy={busy}>
        <fieldset disabled={busy}>
        {mode === "register" && <label htmlFor="name">{t("Full name", "পুরো নাম")}<input id="name" name="name" autoComplete="name" required maxLength={100} pattern=".*\S.*" placeholder={t("Your full name", "আপনার পুরো নাম")} /></label>}
        {!hasToken && <label htmlFor="email">{mode === "login" ? t("Email or phone", "ইমেইল অথবা ফোন") : t("Email address", "ইমেইল ঠিকানা")}<input id="email" name="email" type={mode === "login" ? "text" : "email"} autoComplete={mode === "login" ? "username" : "email"} required maxLength={320} placeholder="you@example.com" /></label>}
        {mode === "register" && <><label>Phone number (optional)<input name="phone" type="tel" autoComplete="tel" maxLength={30} placeholder="+8801712345678" /></label><label>Date of birth (optional)<input name="date_of_birth" type="date" max={new Date().toISOString().slice(0,10)} /></label><label>Blood group (optional)<select name="blood_group" defaultValue=""><option value="">Prefer not to say</option>{["A+","A-","B+","B-","AB+","AB-","O+","O-"].map(v => <option key={v}>{v}</option>)}</select></label></>}
        {hasToken && <label htmlFor="token">{t("Email token", "ইমেইল টোকেন")}<input id="token" name="token" value={token} onChange={e => setToken(e.target.value)} required minLength={20} maxLength={256} autoComplete="off" spellCheck={false} /></label>}
        {hasPassword && <label htmlFor="password">{t(mode === "reset-password" ? "New password" : "Password", mode === "reset-password" ? "নতুন পাসওয়ার্ড" : "পাসওয়ার্ড")}<span className="password-field"><input id="password" name="password" type={showPassword ? "text" : "password"} autoComplete={mode === "login" ? "current-password" : "new-password"} required minLength={mode === "login" ? 1 : 8} maxLength={128} aria-describedby={mode !== "login" ? "password-help" : undefined} /><button type="button" aria-pressed={showPassword} onClick={() => setShowPassword(!showPassword)}>{t(showPassword ? "Hide" : "Show", showPassword ? "লুকান" : "দেখুন")}</button></span></label>}
        {hasPassword && mode !== "login" && <><small id="password-help" className="field-hint">{t("Use 8–128 characters. A memorable passphrase works well.", "৮–১২৮ অক্ষর ব্যবহার করুন। সহজে মনে থাকে এমন দীর্ঘ বাক্য দিতে পারেন।")}</small><label htmlFor="confirm">{t("Confirm password", "পাসওয়ার্ড নিশ্চিত করুন")}<input id="confirm" name="confirm" type={showPassword ? "text" : "password"} autoComplete="new-password" required minLength={8} maxLength={128} /></label></>}
        {mode === "login" && <Link className="forgot-link" href="/forgot-password">{t("Forgot password?", "পাসওয়ার্ড ভুলে গেছেন?")}</Link>}
        {(failure !== null || mismatch) && <p className="alert error" role="alert">{mismatch ? t("Passwords do not match.", "পাসওয়ার্ড দুটি মিলছে না।") : errorMessage(failure, t)}</p>}
        <button className="button full" type="submit">{busy ? t("Please wait…", "অপেক্ষা করুন…") : t(mode === "login" ? "Sign in" : mode === "register" ? "Create account" : mode === "verify-email" ? "Verify email" : mode === "reset-password" ? "Save new password" : "Send email", mode === "login" ? "লগইন করুন" : mode === "register" ? "অ্যাকাউন্ট খুলুন" : mode === "verify-email" ? "ইমেইল যাচাই করুন" : mode === "reset-password" ? "নতুন পাসওয়ার্ড সংরক্ষণ" : "ইমেইল পাঠান")} <span aria-hidden="true">↗</span></button>
        </fieldset>
      </CivicForm>
      {accountMode && <GoogleSignIn />}
      <p className="auth-switch">{t(mode === "login" ? "New around here?" : mode === "register" ? "Already part of the community?" : "Remember your password?", mode === "login" ? "নতুন এসেছেন?" : mode === "register" ? "আগেই অ্যাকাউন্ট খুলেছেন?" : "পাসওয়ার্ড মনে আছে?")} <Link href={mode === "login" ? "/register" : "/login"}>{t(mode === "login" ? "Create an account" : "Sign in", mode === "login" ? "অ্যাকাউন্ট খুলুন" : "লগইন করুন")}</Link></p>
      {mode === "verify-email" && <Link className="text-link" href="/resend-verification">{t("Request a new verification email", "নতুন যাচাইকরণ ইমেইল পাঠান")}</Link>}
      {mode === "forgot-password" && <Link className="text-link" href="/recover">{t("Recover using a remembered password and DOB", "আগের পাসওয়ার্ড ও জন্মতারিখ দিয়ে অ্যাকাউন্ট ফিরে পান")}</Link>}
      {mode === "reset-password" && <Link className="text-link" href="/forgot-password">{t("Request a new reset link", "নতুন রিসেট লিংক পাঠান")}</Link>}
      </>}
      <p className="auth-footnote">{t("A little less waterlogging. A little more possibility.", "জলাবদ্ধতা কমুক। সম্ভাবনা বাড়ুক।")}</p>
    </section>
  </AuthLayout>;
}
