"use client";
import Script from "next/script";
import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { mutate } from "@/lib/api-client";
import type { User } from "@/lib/auth";
import { useApp } from "./Providers";
type GoogleApi = { accounts: { id: { initialize: (options: { client_id: string; nonce: string; callback: (response: { credential: string }) => void }) => void; renderButton: (container: HTMLElement, options: { theme: string; size: string; shape: string; locale: string }) => void } } };
export default function GoogleSignIn() {
  const { t, language, setUser } = useApp();
  const router = useRouter();
  const target = useRef<HTMLDivElement>(null);
  const [ready, setReady] = useState(false);
  const [started, setStarted] = useState(false);
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;
  if (!clientId) return null;
  async function start() {
    if (busy) return;
    setBusy(true); setFailed(false);
    try {
      const { nonce } = await mutate<{ nonce: string }>("/auth/google/nonce");
      const google = (window as Window & { google?: GoogleApi }).google;
      if (!google || !target.current) throw new Error("Google unavailable");
      google.accounts.id.initialize({ client_id: clientId!, nonce, callback: async ({ credential }) => {
        setBusy(true);
        try { setUser(await mutate<User>("/auth/google", { credential, nonce })); router.replace("/account"); }
        catch { setFailed(true); setStarted(false); target.current?.replaceChildren(); }
        finally { setBusy(false); }
      } });
      google.accounts.id.renderButton(target.current, { theme: "outline", size: "large", shape: "pill", locale: language });
      setStarted(true);
    } catch { setFailed(true); } finally { setBusy(false); }
  }
  return <div className="google-signin"><Script src="https://accounts.google.com/gsi/client" onReady={() => setReady(true)} onError={() => setFailed(true)} /><div className="divider"><span>{t("or", "অথবা")}</span></div>{!started && <button className="button secondary full" disabled={!ready || busy} onClick={start}><b>G</b> {t(busy ? "Please wait…" : "Continue with Google", busy ? "অপেক্ষা করুন…" : "Google দিয়ে চালিয়ে যান")}</button>}<div ref={target} className="google-button" />{failed && <p className="alert error" role="alert">{t("Google sign-in failed. Retry or use your email and password. Existing accounts must use their original sign-in method.", "Google লগইন হয়নি। আবার চেষ্টা করুন বা ইমেইল-পাসওয়ার্ড ব্যবহার করুন। পুরোনো অ্যাকাউন্টে আগের পদ্ধতিতে লগইন করুন।")}</p>}</div>;
}
