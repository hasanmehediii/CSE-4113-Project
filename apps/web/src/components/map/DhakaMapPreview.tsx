"use client";

import { useState } from "react";
import { useApp } from "../Providers";
import DhakaWeather from "./DhakaWeather";

// Viewports only: these areas do not represent water-level monitoring coverage.
const areas = [
  { en: "All Dhaka", bn: "পুরো ঢাকা", bbox: "90.32,23.67,90.47,23.90", lat: 23.785, lon: 90.395, zoom: 12 },
  { en: "North Dhaka", bn: "উত্তর ঢাকা", bbox: "90.33,23.80,90.45,23.90", lat: 23.85, lon: 90.39, zoom: 13 },
  { en: "Central Dhaka", bn: "মধ্য ঢাকা", bbox: "90.34,23.73,90.44,23.81", lat: 23.77, lon: 90.39, zoom: 13 },
  { en: "South Dhaka", bn: "দক্ষিণ ঢাকা", bbox: "90.34,23.68,90.45,23.75", lat: 23.715, lon: 90.395, zoom: 13 },
];

export default function DhakaMapPreview() {
  const { t } = useApp();
  const [selected, setSelected] = useState(0);
  const area = areas[selected];
  const external = `https://www.openstreetmap.org/#map=${area.zoom}/${area.lat}/${area.lon}`;
  return (
    <section className="section container water-map-section" id="dhaka-map" aria-labelledby="map-heading">
      <div className="section-heading">
        <div><span className="eyebrow">{t("A CLEARER PICTURE OF OUR CITY", "আমাদের শহরের আরও স্পষ্ট চিত্র")}</span><h2 id="map-heading">{t("Dhaka, one road at a time.", "ঢাকার প্রতিটি পথের পাশে।")}</h2></div>
        <p>{t("Explore the city today. Road water levels will appear here when the live monitoring system is connected.", "আজই শহরের মানচিত্র দেখুন। লাইভ পর্যবেক্ষণ ব্যবস্থা যুক্ত হলে এখানে রাস্তার পানির স্তর দেখা যাবে।")}</p>
      </div>
      <div className="water-map-card">
        <div className="map-toolbar"><div className="map-area-controls" role="group" aria-label={t("Map area", "মানচিত্রের এলাকা")}>{areas.map((item, index) => <button key={item.en} type="button" aria-pressed={selected === index} onClick={() => setSelected(index)}>{t(item.en, item.bn)}</button>)}</div><span className="preview-badge">{t("MAP PREVIEW", "মানচিত্রের প্রিভিউ")}</span></div>
        <div className="map-content">
          <div className="map-canvas">
            <iframe key={area.en} title={t(`Interactive street map: ${area.en}`, `রাস্তার ইন্টার‌্যাক্টিভ মানচিত্র: ${area.bn}`)} src={`https://www.openstreetmap.org/export/embed.html?bbox=${encodeURIComponent(area.bbox)}&layer=mapnik`} loading="lazy" referrerPolicy="no-referrer" allowFullScreen />
          </div>
          <aside className="map-sidebar" aria-label={t("Weather and water monitoring", "আবহাওয়া ও পানির স্তর পর্যবেক্ষণ")}>
            <DhakaWeather />
            <span className="eyebrow">{t("ROAD WATER LEVELS", "রাস্তার পানির স্তর")}</span>
            <h3>{t("The map is ready. Live readings are next.", "মানচিত্র প্রস্তুত। এরপর আসবে লাইভ তথ্য।")}</h3>
            <div className="map-empty-reading"><span aria-hidden="true">≈</span><strong>{t("No readings yet", "এখনো কোনো পরিমাপ নেই")}</strong><p>{t("Monitoring is not connected. No road conditions are being reported.", "পর্যবেক্ষণ ব্যবস্থা যুক্ত হয়নি। কোনো রাস্তার বর্তমান অবস্থা দেখানো হচ্ছে না।")}</p></div>
            <dl className="map-status-list"><div><dt>{t("Selected view", "নির্বাচিত এলাকা")}</dt><dd>{t(area.en, area.bn)}</dd></div><div><dt>{t("Data connection", "তথ্য সংযোগ")}</dt><dd>{t("Not connected", "সংযুক্ত নয়")}</dd></div><div><dt>{t("Last reading", "সর্বশেষ পরিমাপ")}</dt><dd>{t("Unavailable", "পাওয়া যায়নি")}</dd></div></dl>
            <p className="map-future-note">{t("Coming next: road-level readings, observation times, and waterlogging updates.", "পরবর্তী ধাপে: রাস্তার পানির স্তর, পরিমাপের সময় ও জলাবদ্ধতার খবর।")}</p>
          </aside>
        </div>
        <div className="map-attribution"><span>{t("Map data", "মানচিত্রের তথ্য")} © <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap contributors</a></span><a href={external} target="_blank" rel="noopener noreferrer">{t("Open map in a new tab", "নতুন ট্যাবে মানচিত্র খুলুন")} ↗</a></div>
      </div>
      <p className="map-help">{t("Drag to explore and use + / − to zoom. If the map does not load, use the link above. This preview contains no live water-level data.", "টেনে মানচিত্র দেখুন, + / − দিয়ে জুম করুন। মানচিত্র না এলে উপরের লিংক ব্যবহার করুন। এই প্রিভিউতে পানির স্তরের লাইভ তথ্য নেই।")}</p>
    </section>
  );
}
