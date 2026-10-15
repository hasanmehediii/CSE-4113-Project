"use client";

import { useState, type FormEvent } from "react";
import AuthLayout from "./AuthLayout";
import { CivicForm } from "./CivicUI";
import Link from "next/link";
import { ApiError, mutate } from "@/lib/api-client";
import { accountHome } from "@/lib/auth";
import { useApp } from "./Providers";
import GoogleSignIn from "./GoogleSignIn";
import { useCivicLocale } from "@/hooks/useCivicLocale";

type AccountType = "citizen" | "worker";

export default function RegistrationForm() {
  const { t, user, loading } = useApp();
  const { tr } = useCivicLocale();
  const [accountType, setAccountType] = useState<AccountType>("citizen");
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState("");
  const [success, setSuccess] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    const form = new FormData(event.currentTarget);
    setFailure("");
    if (form.get("password") !== form.get("confirm")) {
      setFailure("Passwords do not match.");
      return;
    }
    const nidNumber = String(form.get("nid_number") || "").trim();
    const nidImage = String(form.get("nid_image_url") || "").trim();
    if (accountType === "worker" && !nidNumber && !nidImage) {
      setFailure("Add your NID number or a private HTTPS link to your NID image.");
      return;
    }
    const data: Record<string, unknown> = {
      account_type: accountType,
      name: String(form.get("name") || "").trim(),
      email: String(form.get("email") || "").trim(),
      password: String(form.get("password") || ""),
      phone: String(form.get("phone") || "").trim() || null,
      date_of_birth: form.get("date_of_birth") || null,
      blood_group: form.get("blood_group") || null,
    };
    if (accountType === "worker") data.worker_identity = { nid_number: nidNumber || null, nid_image_url: nidImage || null };
    setBusy(true);
    try {
      await mutate("/auth/register", data);
      setSuccess(true);
    } catch (error) {
      setFailure(error instanceof ApiError && error.status === 429
        ? "Too many attempts. Wait a few minutes and try again."
        : error instanceof ApiError ? error.detail
        : "Could not connect. Please try again.");
    } finally { setBusy(false); }
  }

  return <AuthLayout variant="register">
    <header className="registration-heading">
      <div>

        <span className="eyebrow">{t("A BETTER DHAKA STARTS WITH YOU", "সুন্দর ঢাকার শুরু আপনার হাতে")}</span>
        <h1>{t("Create your account.", "আপনার অ্যাকাউন্ট খুলুন।")}</h1>
        <p>{t("Join as a citizen or apply to work for your community.", "নাগরিক হিসেবে যোগ দিন অথবা সেবাকর্মী হওয়ার আবেদন করুন।")}</p>
      </div>

    </header>

    <section className="registration-card" aria-label={t("Create account", "অ্যাকাউন্ট খুলুন")}>
      {user ? <div className="notice">
        <h2>{t("You are already signed in.", "আপনি ইতিমধ্যেই লগইন করেছেন।")}</h2>
        <p>{t("Citizens can apply to become workers from their existing account.", "নাগরিকরা তাদের বর্তমান অ্যাকাউন্ট থেকেই সেবাকর্মী হওয়ার আবেদন করতে পারেন।")}</p>
        <div className="registration-actions"><Link className="button" href={accountHome(user)}>{t("Open my workspace", "আমার কর্মক্ষেত্র খুলুন")}</Link>{user.role === "citizen" && <Link className="button secondary" href="/workers/apply">{t("Apply as a worker", "সেবাকর্মী হওয়ার আবেদন")}</Link>}</div>
      </div> : success ? <div className="registration-success" role="status">
        <span className="check-icon">✓</span>
        <h2>{t("Check your inbox.", "আপনার ইমেইল দেখুন।")}</h2>
        <p>{t("If your account is eligible, a verification email will arrive shortly. Check your spam folder too.", "অ্যাকাউন্ট উপযুক্ত হলে শিগগিরই যাচাইকরণ ইমেইল আসবে। স্প্যাম ফোল্ডারও দেখুন।")}</p>
        {accountType === "worker" && <p className="registration-approval-note">{t("Worker signup includes an application for the mayor to review. Verify your email and sign in to track approval. Worker tools unlock after approval.", "সেবাকর্মী নিবন্ধনের আবেদন মেয়র পর্যালোচনা করবেন। ইমেইল যাচাই করে লগইন করুন। অনুমোদনের পর সেবাকর্মীর সুবিধা চালু হবে।")}</p>}
        <div className="registration-actions"><Link className="button" href="/verify-email">{t("Verify email", "ইমেইল যাচাই করুন")}</Link><Link className="button secondary" href="/login">{t("Sign in", "লগইন")}</Link></div>
        <Link className="text-link" href="/resend-verification">{t("Resend verification email", "আবার যাচাইকরণ ইমেইল পাঠান")}</Link>
      </div> : <>
        <CivicForm onSubmit={submit} className="registration-form" aria-busy={busy}>
          <fieldset disabled={busy || loading} className="registration-fields">
            <fieldset className="registration-role-choice">
              <legend>{t("How would you like to join?", "আপনি কীভাবে যোগ দিতে চান?")}</legend>
              <div className="registration-role-options">
                <label className={accountType === "citizen" ? "selected" : ""}>
                  <input type="radio" name="account_type" value="citizen" checked={accountType === "citizen"} onChange={() => { setAccountType("citizen"); setFailure(""); }} />
                  <span><strong>{t("Citizen", "নাগরিক")}</strong><small>{t("Report issues, share road updates, and verify completed work.", "সমস্যা জানান, রাস্তার খবর দিন ও সম্পন্ন কাজ যাচাই করুন।")}</small></span>
                </label>
                <label className={accountType === "worker" ? "selected" : ""}>
                  <input type="radio" name="account_type" value="worker" checked={accountType === "worker"} onChange={() => { setAccountType("worker"); setFailure(""); }} />
                  <span><strong>{t("Worker", "সেবাকর্মী")}</strong><small>{t("Apply to resolve complaints. NID details and mayor approval required.", "সমস্যা সমাধানে কাজ করুন। এনআইডি ও মেয়রের অনুমোদন প্রয়োজন।")}</small></span>
                </label>
              </div>
            </fieldset>

            <fieldset className="registration-section">
              <legend>{t("About you", "আপনার পরিচয়")}</legend>
              <div className="registration-grid">
                <label className="field-wide" htmlFor="signup-name">{t("Full name", "পুরো নাম")}<input id="signup-name" name="name" required maxLength={100} pattern=".*\S.*" autoComplete="name" /></label>
                <label htmlFor="signup-email">{t("Email address", "ইমেইল ঠিকানা")}<input id="signup-email" name="email" type="email" required maxLength={320} autoComplete="email" placeholder="you@example.com" /></label>
                <label htmlFor="signup-phone">{t("Phone number (optional)", "ফোন নম্বর (ঐচ্ছিক)")}<input id="signup-phone" name="phone" type="tel" autoComplete="tel" maxLength={30} placeholder="+8801712345678" /></label>
                <label htmlFor="signup-dob">{t("Date of birth (optional)", "জন্মতারিখ (ঐচ্ছিক)")}<input id="signup-dob" name="date_of_birth" type="date" min="1900-01-01" max={new Date().toISOString().slice(0, 10)} /></label>
                <label htmlFor="signup-blood">{t("Blood group (optional)", "রক্তের গ্রুপ (ঐচ্ছিক)")}<select id="signup-blood" name="blood_group" defaultValue=""><option value="">{t("Prefer not to say", "জানাতে চাই না")}</option>{["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"].map(group => <option key={group}>{group}</option>)}</select></label>
              </div>
            </fieldset>

            <fieldset className="registration-section">
              <legend>{t("Secure your account", "অ্যাকাউন্টের নিরাপত্তা")}</legend>
              <div className="registration-grid">
                <label htmlFor="signup-password">{t("Password", "পাসওয়ার্ড")}<input id="signup-password" name="password" type={showPassword ? "text" : "password"} required minLength={8} maxLength={128} autoComplete="new-password" aria-describedby="signup-password-help" /></label>
                <label htmlFor="signup-confirm">{t("Confirm password", "পাসওয়ার্ড নিশ্চিত করুন")}<input id="signup-confirm" name="confirm" type={showPassword ? "text" : "password"} required minLength={8} maxLength={128} autoComplete="new-password" /></label>
              </div>
              <div className="registration-password-help"><small id="signup-password-help">{t("Use 8–128 characters. A memorable passphrase works well.", "৮–১২৮ অক্ষর ব্যবহার করুন। সহজে মনে থাকে এমন দীর্ঘ বাক্য দিতে পারেন।")}</small><button type="button" aria-pressed={showPassword} onClick={() => setShowPassword(!showPassword)}>{t(showPassword ? "Hide passwords" : "Show passwords", showPassword ? "পাসওয়ার্ড লুকান" : "পাসওয়ার্ড দেখুন")}</button></div>
            </fieldset>

            {accountType === "worker" && <fieldset className="registration-section registration-identity">
              <legend>{t("Worker identity", "সেবাকর্মীর পরিচয় যাচাই")}</legend>
              <p>{t("Provide either your NID number or a private link to the card image. Your application stays pending until the mayor approves it.", "এনআইডি নম্বর অথবা কার্ডের ছবির ব্যক্তিগত লিংক দিন। মেয়রের অনুমোদন না পাওয়া পর্যন্ত আবেদন অপেক্ষমাণ থাকবে।")}</p>
              <div className="registration-grid">
                <label htmlFor="signup-nid">{t("NID number", "এনআইডি নম্বর")}<input id="signup-nid" name="nid_number" inputMode="numeric" autoComplete="off" pattern="(?:[0-9]{10}|[0-9]{13}|[0-9]{17})" maxLength={17} aria-describedby="signup-nid-help" /><small id="signup-nid-help">{t("10, 13 or 17 digits. Stored as a private fingerprint.", "১০, ১৩ অথবা ১৭ সংখ্যা। ব্যক্তিগত ফিঙ্গারপ্রিন্ট হিসেবে সংরক্ষিত হবে।")}</small></label>
                <label htmlFor="signup-nid-image">{t("Or a private NID image link", "অথবা এনআইডি ছবির ব্যক্তিগত লিংক")}<input id="signup-nid-image" name="nid_image_url" type="url" pattern="https://.*" maxLength={2048} autoComplete="off" placeholder="https://…" /><small>{t("Use HTTPS. Only the mayor can view the submitted link.", "HTTPS লিংক দিন। জমা দেওয়া লিংকটি শুধু মেয়র দেখতে পারবেন।")}</small></label>
              </div>
            </fieldset>}

            {failure && <p className="alert error" role="alert">{tr(failure)}</p>}
            <div className="registration-submit"><p>{accountType === "worker" ? t("Next: verify your email, then wait for worker approval.", "এরপর ইমেইল যাচাই করুন এবং অনুমোদনের জন্য অপেক্ষা করুন।") : t("Next: verify your email and start contributing to your city.", "এরপর ইমেইল যাচাই করে আপনার শহরের জন্য অবদান রাখুন।")}</p><button className="button" type="submit">{busy ? t("Creating account…", "অ্যাকাউন্ট তৈরি হচ্ছে…") : accountType === "worker" ? t("Create account & apply as worker", "অ্যাকাউন্ট খুলুন ও আবেদন করুন") : t("Create citizen account", "নাগরিক অ্যাকাউন্ট খুলুন")} <span aria-hidden="true">↗</span></button></div>
          </fieldset>
        </CivicForm>
        {accountType === "citizen" && <GoogleSignIn />}
        <p className="registration-signin">{t("Already have an account?", "আগেই অ্যাকাউন্ট খুলেছেন?")} <Link className="text-link" href="/login">{t("Sign in", "লগইন")}</Link></p>
      </>}
    </section>
  </AuthLayout>;
}
