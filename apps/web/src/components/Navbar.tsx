"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useApp } from "./Providers";

export default function Navbar() {
  const { t, language, setLanguage, theme, setTheme, user } = useApp();
  const [open, setOpen] = useState(false);
  const menuButton = useRef<HTMLButtonElement>(null);
  const links = [
    { href: "/map", text: t("Dhaka map", "ঢাকার মানচিত্র") },
    { href: "/#how-it-works", text: t("How it works", "যেভাবে কাজ করে") },
    { href: "/#mission", text: t("Our mission", "আমাদের লক্ষ্য") },
    { href: "/#faq", text: t("FAQs", "জিজ্ঞাসা") },
  ];

  useEffect(() => {
    if (!open) return;
    function escape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
        menuButton.current?.focus();
      }
    }
    document.addEventListener("keydown", escape);
    return () => document.removeEventListener("keydown", escape);
  }, [open]);

  return <>
    <a className="skip-link" href="#main">{t("Skip to content", "মূল অংশে যান")}</a>
    <header className="site-header">
      <nav className="navbar site-navbar" aria-label={t("Main navigation", "প্রধান নেভিগেশন")}>
        <Link className="brand" href="/" aria-label="DubsiBhai" onClick={() => setOpen(false)}>
          <Image src="/logo.png" alt="" width={42} height={42} loading="eager" />
          <span>Dubsi<span className="brand-blue">Bhai</span><small>{t("Dhaka civic platform", "ঢাকার নাগরিক সেবা")}</small></span>
        </Link>
        <div className="nav-links">{links.map(link => <Link key={link.href} href={link.href}>{link.text}</Link>)}</div>
        <div className="nav-actions">
          <button type="button" className="language-toggle" onClick={() => setLanguage(language === "en" ? "bn" : "en")} aria-label={t("Switch to Bangla", "ইংরেজিতে দেখুন")}>
            <span lang="en" className={language === "en" ? "selected" : ""}>EN</span><span lang="bn" className={language === "bn" ? "selected" : ""}>বাংলা</span>
          </button>
          <button type="button" className="theme-toggle" aria-label={t(theme === "light" ? "Switch to dark mode" : "Switch to light mode", theme === "light" ? "ডার্ক মোড চালু করুন" : "লাইট মোড চালু করুন")} onClick={() => setTheme(theme === "light" ? "dark" : "light")}>
            <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" aria-hidden="true">
              {theme === "light" ? <path d="M21 13a8.5 8.5 0 0 1-10-10 9 9 0 1 0 10 10Z" /> : <><circle cx="12" cy="12" r="4" /><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5" /></>}
            </svg>
          </button>
          <Link className="button small nav-login" href={user ? "/account" : "/login"}>{user ? t("My account", "আমার অ্যাকাউন্ট") : t("Sign in", "লগইন")}<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true"><path d="M4 12h15m-6-6 6 6-6 6" /></svg></Link>
          <button ref={menuButton} type="button" className="menu-toggle" aria-expanded={open} aria-controls="mobile-nav" aria-label={open ? t("Close menu", "মেনু বন্ধ করুন") : t("Open menu", "মেনু খুলুন")} onClick={() => setOpen(previous => !previous)}>
            <svg width="21" height="21" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" aria-hidden="true">{open ? <path d="m6 6 12 12M6 18 18 6" /> : <path d="M4 6h16M4 12h16M4 18h16" />}</svg>
          </button>
        </div>
      </nav>
      <div className="mobile-nav" id="mobile-nav" hidden={!open}>
        {links.map(link => <Link key={link.href} href={link.href} onClick={() => setOpen(false)}>{link.text}</Link>)}
        <Link href={user ? "/account" : "/login"} onClick={() => setOpen(false)}>{t(user ? "My account" : "Sign in", user ? "আমার অ্যাকাউন্ট" : "লগইন")}</Link>
      </div>
    </header>
  </>;
}