"use client";
import Image from "next/image";
import Link from "next/link";
import { useApp } from "@/components/Providers";
import DhakaMapPreview from "@/components/map/DhakaMapPreview";
import LandingCommunity from "@/components/LandingCommunity";

export default function HomePage() {
  const { t, user } = useApp();
  return <main id="main">
    <section className="hero container">
      <div className="hero-copy">
        <span className="eyebrow"><span className="status-dot" />{t("SMALL ACTIONS. BETTER NEIGHBOURHOODS.", "ছোট উদ্যোগে বদলে যাক আমাদের পাড়া।")}</span>
        <h1>{t("Our city.", "আমাদের শহর।")}<br />{t("Our streets.", "আমাদের পথ।")}<br /><em>{t("Our responsibility.", "আমাদের দায়িত্ব।")}</em></h1>
        <p className="hero-description">{t("A blocked drain shouldn’t bring life to a standstill. Connect everyday concerns with the people who can make a difference — one neighbourhood at a time.", "বন্ধ ড্রেনে থেমে থাকুক না জীবন। আপনার এলাকার সমস্যা পৌঁছে দিন সমাধানে কাজ করা মানুষদের কাছে। একসাথে বদলে দিই আমাদের পাড়া।")}</p>
        <div className="hero-buttons"><Link className="button" href={user ? "/account" : "/register"}>{t("Be part of the change", "পরিবর্তনের অংশ হোন")} ↗</Link><a href="#how-it-works" className="text-link">{t("See how it works", "কীভাবে কাজ করে")} ↓</a></div>
        <div className="hero-note"><span className="mini-avatars" aria-hidden="true"><i>ঢা</i><i>কা</i><i>♡</i></span><p>{t("Built for people. Built for Dhaka.", "মানুষের জন্য। ঢাকার জন্য।")}<small>{t("Community-led • Free to join", "সবার উদ্যোগে • বিনামূল্যে যোগ দিন")}</small></p></div>
      </div>
      <div className="hero-art"><div className="art-grid" /><span className="art-coordinate">23.8103° N / 90.4125° E</span><div className="orbit orbit-one" /><div className="orbit orbit-two" />
        <span className="floating-label top-label"><span className="status-dot" />{t("A cleaner tomorrow", "আগামীর পরিচ্ছন্ন শহর")}</span>
        <Image className="hero-mascot" src="/logo.png" alt={t("DubsiBhai water-drop mascot with Dhaka’s skyline", "ঢাকার আকাশরেখার সঙ্গে ডুবসিভাই মাসকট")} width={650} height={650} priority />
        <div className="floating-card"><span className="check-icon">✓</span><div><strong>{t("Every voice matters.", "প্রতিটি মতামত গুরুত্বপূর্ণ।")}</strong><small>{t("Let’s keep Dhaka flowing.", "সচল থাকুক আমাদের ঢাকা।")}</small></div><span className="card-arrow">↗</span></div><span className="art-caption">{t("YOUR NEIGHBOURHOOD. YOUR IMPACT.", "আপনার পাড়া। আপনার অবদান।")}</span>
      </div>
    </section>
    <div className="principles"><div className="container"><span>{t("A city that cares starts with us", "যত্নের শহর শুরু হোক আমাদের হাতে")}</span><strong>◉ {t("Community first", "সবার আগে মানুষ")}</strong><strong>⌖ {t("Locally connected", "নিজ এলাকার পাশে")}</strong><strong>↗ {t("Visible progress", "দৃশ্যমান অগ্রগতি")}</strong></div></div>
    <DhakaMapPreview />
    <section className="section container" id="how-it-works"><div className="section-heading"><div><span className="eyebrow">{t("FROM CONCERN TO ACTION", "সমস্যা থেকে সমাধানের পথে")}</span><h2>{t("A small step. A clearer path.", "ছোট পদক্ষেপে, সুন্দর পথ।")}</h2></div><p>{t("The reporting experience we’re building puts your neighbourhood at the centre.", "আপনার এলাকাকে গুরুত্ব দিয়েই তৈরি হচ্ছে আমাদের অভিযোগ ব্যবস্থা।")}</p></div>
      <div className="steps">{[
        ["01", "⌖", "Spot it. Share it.", "দেখুন। জানান।", "A blocked drain or a waterlogged street? Share the location, a photo, and what you see.", "বন্ধ ড্রেন বা জলাবদ্ধ রাস্তা? অবস্থান, ছবি ও সমস্যার বিবরণ জানান।"],
        ["02", "↗", "Connect the right people.", "পৌঁছে যাক সঠিক মানুষের কাছে।", "Help local teams understand the issue and coordinate the next step.", "স্থানীয় কর্মীদের সমস্যা বুঝতে ও পরবর্তী কাজের পরিকল্পনায় সাহায্য করুন।"],
        ["03", "✓", "Follow the difference.", "দেখুন পরিবর্তন।", "Follow updates from a reported concern through to completed work.", "অভিযোগ থেকে কাজ শেষ হওয়া পর্যন্ত অগ্রগতির খবর দেখুন।"],
      ].map(([n, icon, en, bn, desc, bdesc]) => <article className="step-card" key={n}><div className="step-top"><span className="step-icon" aria-hidden="true">{icon}</span><span>{n}</span></div><h3>{t(en, bn)}</h3><p>{t(desc, bdesc)}</p></article>)}</div>
      <p className="development-note"><span className="status-dot" />{t("Reporting, live water levels, and work tracking are in development. Explore the base map and create your account today.", "অভিযোগ, পানির লাইভ স্তর ও কাজের অগ্রগতি দেখার সুবিধা তৈরি হচ্ছে। এখনই মানচিত্র দেখুন ও অ্যাকাউন্ট খুলুন।")}</p>
    </section>
    <section className="mission container" id="mission"><div className="mission-visual"><span className="eyebrow">{t("THE DHAKA WE BELIEVE IN", "আমাদের স্বপ্নের ঢাকা")}</span><div className="mission-words">{t("Less waterlogging.", "কম জলাবদ্ধতা।")}<br /><span>{t("More living.", "সচল জীবন।")}</span></div><div className="mission-lines" aria-hidden="true"><i /><i /><i /></div><span className="mission-tag">DHAKA · ঢাকা</span></div><div className="mission-copy"><span className="eyebrow">{t("OUR SHARED RESPONSIBILITY", "দায়িত্ব আমাদের সবার")}</span><h2>{t("Better streets begin with better connections.", "যোগাযোগ বাড়ুক, পথ বদলে যাক।")}</h2><p>{t("The people who live on a street know it best. DubsiBhai brings residents and service teams closer, so everyday drainage problems have a clearer path to attention.", "একটি এলাকার মানুষই সেই এলাকার সমস্যা সবচেয়ে ভালো জানেন। বাসিন্দা ও সেবাকর্মীদের মধ্যে যোগাযোগ সহজ করে ড্রেনেজ সমস্যার সমাধানের পথ তৈরি করাই ডুবসিভাইয়ের লক্ষ্য।")}</p><ul className="mission-list"><li>{t("Designed for residents and field workers", "বাসিন্দা ও মাঠপর্যায়ের কর্মীদের জন্য")}</li><li>{t("In Bangla and English, for more of us", "বাংলা ও ইংরেজিতে, সবার সুবিধার জন্য")}</li><li>{t("Built around transparency and community", "স্বচ্ছতা ও মানুষের অংশগ্রহণকে গুরুত্ব দিয়ে")}</li></ul></div></section>
    <LandingCommunity />
    <section className="section faq-section container" id="faq"><div><span className="eyebrow">{t("GOOD TO KNOW", "জেনে রাখুন")}</span><h2>{t("A few things you might be wondering.", "কিছু সাধারণ প্রশ্নের উত্তর।")}</h2></div><div className="faq-list">{[
      ["Does the map show live water levels?", "মানচিত্রে কি পানির লাইভ স্তর দেখা যায়?", "Not yet. You can explore the Dhaka street map now. Live measurements will be added when the monitoring system is connected.", "এখনো নয়। এখন ঢাকার রাস্তার মানচিত্র দেখতে পারেন। পর্যবেক্ষণ ব্যবস্থা যুক্ত হলে পানির লাইভ পরিমাপ যোগ হবে।"],
      ["Who can join DubsiBhai?", "কারা ডুবসিভাইয়ে যোগ দিতে পারবেন?", "Anyone who wants to help improve drainage and reduce waterlogging in Dhaka can create a resident account.", "ঢাকার ড্রেনেজ ব্যবস্থা উন্নত করতে ও জলাবদ্ধতা কমাতে আগ্রহী যে কেউ বাসিন্দা হিসেবে অ্যাকাউন্ট খুলতে পারেন।"],
      ["Can I report a problem right now?", "এখনই কি অভিযোগ জানাতে পারব?", "Not yet. Account registration is available; reporting, the live map, and service tracking are still being developed.", "এখনো নয়। অ্যাকাউন্ট খোলা যাচ্ছে; অভিযোগ, লাইভ মানচিত্র ও সেবার অগ্রগতি দেখার কাজ চলছে।"],
      ["Is this an emergency service?", "এটি কি জরুরি সেবা?", "No. DubsiBhai is a community project. Contact the appropriate local authority for urgent help.", "না। ডুবসিভাই একটি কমিউনিটি প্রকল্প। জরুরি প্রয়োজনে সংশ্লিষ্ট স্থানীয় কর্তৃপক্ষের সঙ্গে যোগাযোগ করুন।"],
      ["Do I need to pay to create an account?", "অ্যাকাউন্ট খুলতে কি টাকা লাগবে?", "No. Creating a DubsiBhai account is free.", "না। ডুবসিভাইয়ে বিনামূল্যে অ্যাকাউন্ট খুলতে পারবেন।"],
    ].map(([q, bq, a, ba]) => <details key={q}><summary>{t(q, bq)}<span aria-hidden="true">+</span></summary><p>{t(a, ba)}</p></details>)}</div></section>
    <section className="join-banner container"><span className="eyebrow">{t("IT STARTS WITH US", "শুরু হোক আমাদের দিয়ে")}</span><h2>{t("Let’s keep Dhaka moving.", "সচল রাখি আমাদের ঢাকা।")}</h2><p>{t("Your neighbourhood deserves a little more care. Be part of it.", "আমাদের পাড়ার যত্নে এগিয়ে আসুন। পরিবর্তনের অংশ হোন।")}</p><Link className="button" href={user ? "/account" : "/register"}>{t(user ? "Go to my account" : "Join the community", user ? "আমার অ্যাকাউন্টে যান" : "আমাদের সঙ্গে যুক্ত হোন")} ↗</Link></section>
  </main>;
}
