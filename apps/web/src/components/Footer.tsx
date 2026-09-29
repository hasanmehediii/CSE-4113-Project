"use client";
import Link from "next/link";
import Image from "next/image";
import { useApp } from "./Providers";

export default function Footer() {
  const { t, user } = useApp();
  const groups = [
    { title: t("Discover", "জেনে নিন"), links: [
      ["/#dhaka-map", t("Dhaka map", "ঢাকার মানচিত্র")],
      ["/#how-it-works", t("How it works", "যেভাবে কাজ করে")],
      ["/#mission", t("Our mission", "আমাদের লক্ষ্য")],
      ["/#faq", t("Common questions", "সাধারণ জিজ্ঞাসা")],
    ] },
    { title: t("Your account", "আপনার অ্যাকাউন্ট"), links: [
      [user ? "/account" : "/login", t(user ? "Account overview" : "Sign in", user ? "অ্যাকাউন্টের তথ্য" : "লগইন করুন")],
      ["/register", t("Join the community", "আমাদের সঙ্গে যুক্ত হোন")],
      ["/forgot-password", t("Password recovery", "পাসওয়ার্ড পুনরুদ্ধার")],
    ] },
  ];
  return (
    <footer className="site-footer">
      <div className="container">
        <div className="footer-main">
          <div className="footer-identity">
            <Link href="/" className="footer-brand" aria-label="DubsiBhai home">
              <Image src="/logo.png" alt="" width={58} height={58} />
              <span className="brand-text">Dubsi<span>Bhai</span>.</span>
            </Link>
            <p>{t("Better streets. Stronger communities. A shared effort to keep Dhaka flowing.", "সুন্দর পথ। ঐক্যবদ্ধ মানুষ। সচল ঢাকা গড়তে আমাদের সম্মিলিত উদ্যোগ।")}</p>
            <span className="footer-location"><span aria-hidden="true">⌖</span> {t("Made for Dhaka, Bangladesh", "ঢাকা, বাংলাদেশের জন্য")}</span>
          </div>
          {groups.map(group => (
            <nav className="footer-links" key={group.title} aria-label={group.title}>
              <h2>{group.title}</h2>
              {group.links.map(([href, label]) => <Link href={href} key={href}>{label}</Link>)}
            </nav>
          ))}
          <div className="footer-community">
            <span className="eyebrow">{t("A CITY WE SHARE", "শহরটা আমাদের সবার")}</span>
            <h2>{t("Small actions. Lasting change.", "ছোট উদ্যোগে স্থায়ী পরিবর্তন।")}</h2>
            <p>{t("Be part of a more connected neighbourhood.", "আরও সংযুক্ত পাড়া গড়তে পাশে থাকুন।")}</p>
            <Link className="footer-cta" href={user ? "/account" : "/register"}>{t(user ? "Go to your account" : "Get started", user ? "অ্যাকাউন্টে যান" : "শুরু করুন")} <span aria-hidden="true">↗</span></Link>
          </div>
        </div>
        <div className="footer-bottom">
          <p>© {new Date().getFullYear()} DubsiBhai. {t("Made for the streets we call home.", "আমাদের চেনা শহরের জন্য।")}</p>
          <span className="footer-project-status"><span className="status-dot" />{t("A community project for a better Dhaka", "সুন্দর ঢাকার জন্য একটি কমিউনিটি উদ্যোগ")}</span>
          <a className="footer-top" href="#main">{t("Back to top", "উপরে ফিরুন")} <span aria-hidden="true">↑</span></a>
        </div>
      </div>
    </footer>
  );
}
