"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useState, useSyncExternalStore } from "react";
import { useApp } from "./Providers";

const banners = [
  { src: "/dubsibhai-banner1.png", caption: ["The streets we share", "আমাদের সবার পথ"] },
  { src: "/dubsibhai-banner2.png", caption: ["The people who care for them", "যাঁদের যত্নে সচল থাকে শহর"] },
  { src: "/dubsibhai-banner3.png", caption: ["A community that takes action", "এগিয়ে আসুক এলাকার মানুষ"] },
] as const;

function subscribeToMotion(callback: () => void) {
  const media = window.matchMedia("(prefers-reduced-motion: reduce)");
  media.addEventListener("change", callback);
  return () => media.removeEventListener("change", callback);
}
function prefersReducedMotion() { return window.matchMedia("(prefers-reduced-motion: reduce)").matches; }
function serverMotionPreference() { return false; }

export default function LandingHero() {
  const { t, language } = useApp();
  const [active, setActive] = useState(0);
  const [paused, setPaused] = useState(false);
  const reducedMotion = useSyncExternalStore(subscribeToMotion, prefersReducedMotion, serverMotionPreference);
  const playing = !paused && !reducedMotion;
  const formatIndex = (value: number) => new Intl.NumberFormat(language === "bn" ? "bn-BD" : "en-GB", { minimumIntegerDigits: 2 }).format(value);

  useEffect(() => {
    if (!playing) return;
    const timer = setInterval(() => setActive(previous => (previous + 1) % banners.length), 2000);
    return () => clearInterval(timer);
  }, [playing]);

  return <section className="landing-hero" aria-labelledby="landing-hero-title">
    <div className="hero-backdrops" aria-hidden="true">
      {banners.map((banner, index) => <div key={banner.src} className={`hero-slide${active === index ? " is-active" : ""}`}>
        <Image src={banner.src} alt="" fill sizes="100vw" preload={index === 0} loading={index === 0 ? undefined : "eager"} className="hero-banner-image" />
      </div>)}
    </div>
    <div className="hero-shade" aria-hidden="true" />
    <div className="container landing-hero-inner">
      <div className="landing-hero-copy">
        <p className="landing-hero-eyebrow"><span aria-hidden="true" />{t("DHAKA · COMMUNITY & CITY SERVICES", "ঢাকা · নাগরিক ও নগর সেবা")}</p>
        <h1 id="landing-hero-title">{t("Better streets.", "সুন্দর পথ।")}<br /><span>{t("A better Dhaka.", "সুন্দর ঢাকা।")}</span></h1>
        <p className="landing-hero-description">{t("Report local problems, follow work on the ground, and help keep your neighbourhood moving. A better city begins with all of us.", "এলাকার সমস্যা জানান, কাজের অগ্রগতি দেখুন, আর সচল রাখুন আপনার পাড়া। সবার অংশগ্রহণেই গড়ে উঠবে সুন্দর ঢাকা।")}</p>
        <div className="landing-hero-actions">
          <Link className="button hero-primary-action" href="/complaints/new">{t("Report an issue", "সমস্যা জানান")}<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true"><path d="M4 12h15m-6-6 6 6-6 6" /></svg></Link>
          <Link className="button hero-map-action" href="/map"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" aria-hidden="true"><path d="m9 4-6 3v14l6-3 6 3 6-3V4l-6 3-6-3Z" /><path d="M9 4v14m6-11v14" /></svg>{t("Explore Dhaka map", "ঢাকার মানচিত্র দেখুন")}</Link>
        </div>
        <p className="landing-hero-note">{t("Open to everyone. Built for our city.", "সবার জন্য উন্মুক্ত। আমাদের শহরের জন্য।")}</p>
      </div>
      <div className="landing-hero-footer">
        <div className="hero-photo-caption"><span>{formatIndex(active + 1)} / {formatIndex(banners.length)}</span><p>{t(banners[active].caption[0], banners[active].caption[1])}</p></div>
        <div className="hero-carousel-controls" role="group" aria-label={t("Banner slideshow controls", "ব্যানার দেখার নিয়ন্ত্রণ")}>
          <div className="hero-slide-selectors">{banners.map((banner, index) => <button key={banner.src} type="button" className="hero-slide-selector" aria-pressed={active === index} aria-label={t(`Show banner ${index + 1}`, `${new Intl.NumberFormat("bn-BD").format(index + 1)} নম্বর ব্যানার দেখুন`)} onClick={() => setActive(index)}><span /></button>)}</div>
          <button type="button" className="hero-playback" aria-label={playing ? t("Pause slideshow", "ব্যানার পরিবর্তন থামান") : t("Play slideshow", "ব্যানার পরিবর্তন চালু করুন")} onClick={() => setPaused(previous => !previous)} disabled={reducedMotion}>
            {playing ? <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true"><path d="M4 3h2v10H4zm6 0h2v10h-2z" /></svg> : <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true"><path d="m5 2 9 6-9 6z" /></svg>}
          </button>
        </div>
      </div>
    </div>
  </section>;
}
