"use client";

import { useEffect, useState } from "react";
import { useApp } from "../Providers";

type CurrentWeather = {
  time: number;
  temperature_2m: number;
  apparent_temperature: number;
  relative_humidity_2m: number;
  precipitation: number;
  weather_code: number;
  wind_speed_10m: number;
  is_day: number;
};

const endpoint = "https://api.open-meteo.com/v1/forecast?latitude=23.8103&longitude=90.4125&current=temperature_2m,apparent_temperature,relative_humidity_2m,precipitation,weather_code,wind_speed_10m,is_day&timezone=Asia%2FDhaka&timeformat=unixtime&forecast_days=1";

function condition(code: number, day: boolean): [string, string, string] {
  if (code === 0) return [day ? "☀" : "☾", day ? "Clear sky" : "Clear night", day ? "পরিষ্কার আকাশ" : "পরিষ্কার রাত"];
  if (code <= 2) return [day ? "⛅" : "☁", "Partly cloudy", "আংশিক মেঘলা"];
  if (code === 3) return ["☁", "Overcast", "মেঘাচ্ছন্ন"];
  if ([45, 48].includes(code)) return ["≋", "Foggy", "কুয়াশাচ্ছন্ন"];
  if ([51, 53, 55, 56, 57].includes(code)) return ["☂", "Drizzle", "গুঁড়ি গুঁড়ি বৃষ্টি"];
  if ([61, 63, 65, 66, 67, 80, 81, 82].includes(code)) return ["☂", "Rain", "বৃষ্টি"];
  if ([71, 73, 75, 77, 85, 86].includes(code)) return ["❄", "Snow", "তুষারপাত"];
  if ([95, 96, 99].includes(code)) return ["ϟ", "Thunderstorm", "বজ্রসহ বৃষ্টি"];
  return ["☁", "Current conditions", "বর্তমান আবহাওয়া"];
}

export default function DhakaWeather() {
  const { t, language } = useApp();
  const [weather, setWeather] = useState<CurrentWeather | null>(null);
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    let disposed = false;
    async function refresh() {
      try {
        const response = await fetch(endpoint, {
          signal: AbortSignal.any([controller.signal, AbortSignal.timeout(12000)]),
        });
        if (!response.ok) throw new Error("Weather unavailable");
        const data = await response.json();
        const current = data.current;
        const fields: (keyof CurrentWeather)[] = ["time", "temperature_2m", "apparent_temperature", "relative_humidity_2m", "precipitation", "weather_code", "wind_speed_10m", "is_day"];
        if (!current || fields.some(key => typeof current[key] !== "number" || !Number.isFinite(current[key]))) {
          throw new Error("Incomplete weather data");
        }
        if (!disposed) { setWeather(current); setFailed(false); }
      } catch {
        if (!disposed) setFailed(true);
      }
    }
    void refresh();
    const interval = window.setInterval(() => void refresh(), 10 * 60 * 1000);
    return () => { disposed = true; controller.abort(); window.clearInterval(interval); };
  }, [attempt]);

  const locale = language === "bn" ? "bn-BD" : "en-GB";
  const number = (value: number, decimals = 0) => new Intl.NumberFormat(locale, { maximumFractionDigits: decimals }).format(value);
  const [icon, en, bn] = weather ? condition(weather.weather_code, weather.is_day === 1) : ["☁", "", ""];
  const updated = weather ? new Intl.DateTimeFormat(locale, { timeZone: "Asia/Dhaka", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }).format(new Date(weather.time * 1000)) : "";

  return <section className="dhaka-weather" aria-label={t("Dhaka weather", "ঢাকার আবহাওয়া")}>
    <div className="weather-heading"><span className="eyebrow">{t("DHAKA WEATHER", "ঢাকার আবহাওয়া")}</span><span className="weather-label">{t("Now", "এখন")}</span></div>
    <div aria-live="polite">
      {weather ? <>
        <div className="weather-current"><span className="weather-icon" aria-hidden="true">{icon}</span><div><strong className="weather-temperature">{number(weather.temperature_2m)}°<small>C</small></strong><p>{t(en, bn)}</p></div></div>
        <p className="weather-feels">{t("Feels like", "অনুভূত তাপমাত্রা")} {number(weather.apparent_temperature)}°C</p>
        <dl className="weather-metrics">
          <div><dt>{t("Rain · last 15 min", "বৃষ্টি · গত ১৫ মিনিট")}</dt><dd>{number(weather.precipitation, 1)} {t("mm", "মিমি")}</dd></div>
          <div><dt>{t("Humidity", "আর্দ্রতা")}</dt><dd>{number(weather.relative_humidity_2m)}%</dd></div>
          <div><dt>{t("Wind", "বাতাস")}</dt><dd>{number(weather.wind_speed_10m, 1)} {t("km/h", "কিমি/ঘণ্টা")}</dd></div>
        </dl>
        <p className="weather-updated">{t("As of", "তথ্যের সময়")} {updated} · {t("Dhaka time", "ঢাকার সময়")}</p>
      </> : <p className="weather-placeholder">{failed ? t("Weather is temporarily unavailable.", "আবহাওয়ার তথ্য আপাতত পাওয়া যাচ্ছে না।") : t("Loading Dhaka weather…", "ঢাকার আবহাওয়া লোড হচ্ছে…")}</p>}
      {failed && <div className="weather-error">{weather && <p>{t("Refresh unavailable. Showing the last update.", "নতুন তথ্য পাওয়া যায়নি। সর্বশেষ তথ্য দেখানো হচ্ছে।")}</p>}<button type="button" onClick={() => { setFailed(false); setAttempt(value => value + 1); }}>{t("Try again", "আবার চেষ্টা করুন")}</button></div>}
    </div>
    <p className="weather-source">{t("Weather model data by", "আবহাওয়ার মডেল তথ্য")} <a href="https://open-meteo.com/" target="_blank" rel="noopener noreferrer">Open-Meteo ↗</a></p>
  </section>;
}
