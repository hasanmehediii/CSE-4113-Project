"use client";

import Image from "next/image";
import Link from "next/link";
import type { ReactNode } from "react";
import { useApp } from "./Providers";

export default function AuthLayout({ children, variant }: { children: ReactNode; variant: "login" | "register" | "recovery" }) {
  const { t } = useApp();
  return <main id="main" className="account-access-page">
    <div className={`container account-access-layout${variant === "register" ? " is-registration" : ""}`}>
      <aside className="account-access-story">
        <div className="account-access-photo-container">
          <Image src={variant === "register" ? "/dubsibhai-banner3.png" : "/dubsibhai-banner2.png"} alt="" fill sizes="(max-width: 860px) 1px, 40vw" className="account-access-photo" />
        </div>
        <div className="account-access-shade" />
        <div className="account-access-story-content">
          <span className="account-access-wordmark">DubsiBhai<span>{t("DHAKA · COMMUNITY SERVICES", "ঢাকা · নাগরিক সেবা")}</span></span>
          <div><span className="account-access-story-kicker">{t("A CITY WE CARE FOR", "যে শহরের যত্ন নিই আমরা")}</span><h2>{t("Your neighbourhood.", "আপনার এলাকা।")}<br />{t("Our shared responsibility.", "দায়িত্ব আমাদের সবার।")}</h2><p>{t("Connect with the people making our streets cleaner, safer, and easier to navigate.", "আমাদের পথ পরিচ্ছন্ন, নিরাপদ ও চলাচলের উপযোগী করতে একসঙ্গে কাজ করা মানুষদের সঙ্গে যুক্ত হোন।")}</p></div>
          <div className="account-access-story-footer"><span>{t("For residents & field teams", "বাসিন্দা ও সেবাকর্মীদের জন্য")}</span><strong>{t("A better Dhaka begins with us.", "আমাদের হাতেই সুন্দর ঢাকার শুরু।")}</strong></div>
        </div>
      </aside>
      <div className="account-access-panel"><div className="account-access-top"><Link href="/">← {t("Back to home", "হোমে ফিরে যান")}</Link><span>{t("YOUR ACCOUNT", "আপনার অ্যাকাউন্ট")}</span></div>{children}</div>
    </div>
  </main>;
}
