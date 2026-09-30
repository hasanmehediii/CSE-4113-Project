"use client";
import Image from "next/image";
import Link from "next/link";
import { useState } from "react";
import { useApp } from "./Providers";
export default function Navbar() {
  const { t, language, setLanguage, theme, setTheme, user, loading } = useApp();
  const [open, setOpen] = useState(false);
  return <>
    <a className="skip-link" href="#main">{t("Skip to content", "মূল অংশে যান")}</a>
    <header className="nav-wrap"><nav className="navbar" aria-label={t("Main navigation", "প্রধান নেভিগেশন")}>
      <Link className="brand" href="/" aria-label="DubsiBhai" onClick={() => setOpen(false)}><Image src="/logo.png" alt="" width={46} height={46} priority /><span>Dubsi<span className="brand-blue">Bhai</span><small>{t("A better Dhaka, together", "একসাথে গড়ি সুন্দর ঢাকা")}</small></span></Link>
      <div className="nav-links"><Link href="/#dhaka-map">{t("Dhaka map", "ঢাকার মানচিত্র")}</Link><Link href="/#how-it-works">{t("How it works", "যেভাবে কাজ করে")}</Link><Link href="/#mission">{t("Our mission", "আমাদের লক্ষ্য")}</Link><Link href="/#faq">{t("FAQs", "জিজ্ঞাসা")}</Link></div>
      <div className="nav-actions"><button className="language-toggle" onClick={() => setLanguage(language === "en" ? "bn" : "en")} aria-label={t("Switch to Bangla", "ইংরেজিতে দেখুন")}><span className={language === "en" ? "selected" : ""}>EN</span><span className={language === "bn" ? "selected" : ""}>বাং</span></button>
        <button className="theme-toggle" aria-label={t(theme === "light" ? "Switch to dark mode" : "Switch to light mode", theme === "light" ? "ডার্ক মোড চালু করুন" : "লাইট মোড চালু করুন")} onClick={() => setTheme(theme === "light" ? "dark" : "light")}>{theme === "light" ? "☾" : "☀"}</button>
        <Link className="button small nav-login" href={user ? "/account" : "/login"}>{user ? t("My account", "আমার অ্যাকাউন্ট") : t("Sign in", "লগইন")} <span aria-hidden="true">↗</span></Link>
        <button className="menu-toggle" aria-expanded={open} aria-controls="mobile-nav" aria-label={t("Toggle menu", "মেনু খুলুন")} onClick={() => setOpen(!open)}>{open ? "×" : "☰"}</button></div>
      </nav>{open && <div className="mobile-nav" id="mobile-nav"><Link href="/#dhaka-map" onClick={() => setOpen(false)}>{t("Dhaka map", "ঢাকার মানচিত্র")}</Link><Link href="/#how-it-works" onClick={() => setOpen(false)}>{t("How it works", "যেভাবে কাজ করে")}</Link><Link href="/#mission" onClick={() => setOpen(false)}>{t("Our mission", "আমাদের লক্ষ্য")}</Link><Link href="/#faq" onClick={() => setOpen(false)}>{t("FAQs", "জিজ্ঞাসা")}</Link><Link href={user ? "/account" : "/login"} onClick={() => setOpen(false)}>{t(user ? "My account" : "Sign in", user ? "আমার অ্যাকাউন্ট" : "লগইন")}</Link></div>}</header>
  </>;
}
