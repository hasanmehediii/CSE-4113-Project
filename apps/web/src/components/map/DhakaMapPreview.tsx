"use client";
import Link from "next/link";
import { useApp } from "../Providers";
import { useResource, type Complaint, type Road } from "@/lib/civic";
import LiveRoadMap from "./LiveRoadMap";
import DhakaWeather from "./DhakaWeather";

export default function DhakaMapPreview() {
  const { t } = useApp();
  const roads = useResource<Road[]>("/map/roads", 20000);
  const reports = useResource<Complaint[]>("/complaints", 20000);
  return <section className="section container water-map-section" id="dhaka-map" aria-labelledby="map-heading">
    <div className="section-heading"><div><span className="eyebrow">{t("OUR CITY, IN VIEW", "আমাদের শহরের বর্তমান চিত্র")}</span><h2 id="map-heading">{t("Dhaka, one road at a time.", "ঢাকার প্রতিটি পথের পাশে।")}</h2></div><p>{t("Explore public road reports and community-confirmed work. Updates refresh every 20 seconds.", "রাস্তার খবর এবং যাচাইকৃত কাজ দেখুন। প্রতি ২০ সেকেন্ডে তথ্য হালনাগাদ হয়।")}</p></div>
    <div className="civic-map-layout"><LiveRoadMap roads={roads.data || []} complaints={reports.data || []} /><aside className="civic-card"><DhakaWeather /><h3>{t("Your road. Your voice.", "আপনার পথ। আপনার কথা।")}</h3><div className="map-legend"><span className="bad">● {t("Bad", "খারাপ")}</span><span className="good">● {t("Good", "ভালো")}</span><span>● {t("Unknown", "অজানা")}</span></div><p>{t("Conditions come from community reports and confirmed cleanups. Roads without recent evidence remain unknown.", "এলাকাবাসীর খবর ও যাচাইকৃত কাজের ভিত্তিতে অবস্থা দেখানো হয়। সাম্প্রতিক তথ্য না থাকলে অবস্থা অজানা থাকে।")}</p>{(roads.error || reports.error) && <p role="status">{t("Live reports are temporarily unavailable. Open the map to retry.", "লাইভ তথ্য সাময়িকভাবে পাওয়া যাচ্ছে না। আবার মানচিত্র খুলুন।")}</p>}<Link className="button" href="/map">{t("Explore live road conditions", "রাস্তার বর্তমান অবস্থা দেখুন")} →</Link><p><Link className="text-link" href="/complaints/new">{t("Report a problem", "সমস্যা জানান")} ↗</Link></p><small>{t("Community observations; IoT readings are planned for a later release.", "এলাকাবাসীর পর্যবেক্ষণ; পরবর্তী সংস্করণে আইওটি তথ্য যুক্ত হবে।")}</small></aside></div>
  </section>;
}
