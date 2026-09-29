"use client";
import Link from "next/link";
import { useApp } from "./Providers";

export default function LandingCommunity() {
  const { t, user } = useApp();
  return <>
    <section className="section container community-section" id="community">
      <div className="section-heading"><div><span className="eyebrow">{t("DIFFERENT ROLES. ONE SHARED CITY.", "ভিন্ন ভূমিকা। শহর আমাদের সবার।")}</span><h2>{t("There’s a place for everyone.", "সবার জন্য আছে একটি জায়গা।")}</h2></div><p>{t("A better drainage service starts when local knowledge and field experience come together.", "এলাকার মানুষের অভিজ্ঞতা ও মাঠপর্যায়ের দক্ষতা এক হলে ড্রেনেজ সেবা আরও ভালো হয়।")}</p></div>
      <div className="community-cards">{[
        ["01", "For residents", "বাসিন্দাদের জন্য", "You know your neighbourhood.", "নিজের পাড়া আপনিই চেনেন।", "Help bring attention to blocked drains and waterlogged streets. The reporting tools we’re building will let you share the location and follow what happens next.", "বন্ধ ড্রেন ও জলাবদ্ধ রাস্তার সমস্যা তুলে ধরুন। তৈরি হতে থাকা অভিযোগ ব্যবস্থায় অবস্থান জানাতে ও পরবর্তী অগ্রগতি দেখতে পারবেন।"],
        ["02", "For service teams", "সেবাকর্মীদের জন্য", "Local knowledge. Real action.", "এলাকার অভিজ্ঞতা। বাস্তব উদ্যোগ।", "Clear locations and useful descriptions can help field teams understand an issue before reaching the street. Task coordination is part of our next stage.", "সঠিক অবস্থান ও বিবরণ পেলে মাঠপর্যায়ের কর্মীরা যাওয়ার আগেই সমস্যা বুঝতে পারবেন। কাজের সমন্বয় আমাদের পরবর্তী ধাপের অংশ।"],
        ["03", "For the community", "সবার জন্য", "See the bigger picture.", "দেখুন পুরো এলাকার চিত্র।", "Our goal is to bring road conditions, local concerns, and service updates into one place, so progress is easier for everyone to follow.", "রাস্তার অবস্থা, এলাকার সমস্যা ও সেবার খবর এক জায়গায় আনা আমাদের লক্ষ্য, যাতে সবাই সহজে অগ্রগতি দেখতে পারেন।"],
      ].map(([n, label, blabel, title, btitle, body, bbody]) => <article className="community-card" key={n}><div className="community-card-top"><span>{t(label, blabel)}</span><span aria-hidden="true">{n}</span></div><h3>{t(title, btitle)}</h3><p>{t(body, bbody)}</p></article>)}</div>
    </section>
    <section className="container roadmap-section" id="whats-next"><div className="roadmap-intro"><span className="eyebrow">{t("BUILDING WITH PURPOSE", "সুনির্দিষ্ট লক্ষ্যে এগিয়ে চলা")}</span><h2>{t("Today’s first step. Tomorrow’s connected city.", "আজকের প্রথম পদক্ষেপ। আগামীর সংযুক্ত শহর।")}</h2><p>{t("We’re building DubsiBhai in stages. Here’s what you can use now and what we’re working towards.", "ধাপে ধাপে তৈরি হচ্ছে ডুবসিভাই। এখন কী ব্যবহার করতে পারবেন এবং সামনে কী আসছে, দেখে নিন।")}</p><Link href={user ? "/account" : "/register"} className="text-link">{t(user ? "Visit your account" : "Start with your account", user ? "আপনার অ্যাকাউন্ট দেখুন" : "অ্যাকাউন্ট খুলে শুরু করুন")} ↗</Link></div><ol className="roadmap-list">{[
      ["Available now", "এখন ব্যবহারযোগ্য", "Your community account", "আপনার কমিউনিটি অ্যাকাউন্ট", "Sign up, verify your email, and explore the Dhaka base map in Bangla or English.", "অ্যাকাউন্ট খুলুন, ইমেইল যাচাই করুন এবং বাংলা বা ইংরেজি ইন্টারফেসে ঢাকার মানচিত্র দেখুন।"],
      ["In development", "তৈরি হচ্ছে", "Report and follow up", "অভিযোগ ও অগ্রগতি", "Location-based complaints, photos, and updates from service teams.", "অবস্থানভিত্তিক অভিযোগ, ছবি ও সেবাকর্মীদের অগ্রগতির খবর।"],
      ["Planned", "পরিকল্পনায় আছে", "Live road water levels", "রাস্তার পানির লাইভ স্তর", "Connect monitoring data to the map, with reading times and road-level context.", "পরিমাপের সময় ও রাস্তার বিবরণসহ পর্যবেক্ষণের তথ্য মানচিত্রে যুক্ত করা।"],
    ].map(([status, bstatus, title, btitle, desc, bdesc], index) => <li key={title}><span className="roadmap-number" aria-hidden="true">{index + 1}</span><div><span className={`roadmap-status ${index === 0 ? "available" : ""}`}>{t(status, bstatus)}</span><h3>{t(title, btitle)}</h3><p>{t(desc, bdesc)}</p></div></li>)}</ol></section>
  </>;
}
