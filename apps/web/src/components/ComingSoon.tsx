"use client";
import Link from "next/link";
import { useApp } from "./Providers";

export default function ComingSoon({ title }: { title: string }) {
  const { t } = useApp();
  const titles: Record<string, string> = { "Complaint map": "অভিযোগের মানচিত্র", "Live map": "লাইভ মানচিত্র", "Complaint details": "অভিযোগের বিস্তারিত", "Admin dashboard": "প্রশাসকের ড্যাশবোর্ড", "Worker dashboard": "কর্মীর ড্যাশবোর্ড" };
  return (
    <main id="main" className="container placeholder">
      <Link href="/" className="eyebrow">← {t("Back to home", "হোমে ফিরে যান")}</Link>
      <h1>{t(title, titles[title] || "শীঘ্রই আসছে")}</h1>
      <p>{t("This feature is in development. We are building a more connected Dhaka, one step at a time.", "এই সুবিধা তৈরি হচ্ছে। ধাপে ধাপে আরও সংযুক্ত ঢাকা গড়ে তুলছি আমরা।")}</p>
      <Link href="/account" className="button">{t("My account", "আমার অ্যাকাউন্ট")} ↗</Link>
    </main>
  );
}
