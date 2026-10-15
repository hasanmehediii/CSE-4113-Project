"use client";
import { useEffect, useRef, useState } from "react";
import type * as Leaflet from "leaflet";
import { type Road, type Complaint } from "@/lib/civic";
import { useCivicLocale } from "@/hooks/useCivicLocale";
import { civicLabel, civicNumber } from "@/lib/civic-i18n";

export default function LiveRoadMap({ roads, complaints, focus }: { roads: Road[]; complaints: Complaint[]; focus?: { latitude: number; longitude: number } | null }) {
  const { language, tr } = useCivicLocale();
  const container = useRef<HTMLDivElement>(null);
  const currentMap = useRef<Leaflet.Map | null>(null);
  const tiles = useRef<Leaflet.TileLayer | null>(null);
  const currentLanguage = useRef(language);
  const [map, setMap] = useState<Leaflet.Map | null>(null);
  const [tileError, setTileError] = useState(false);
  useEffect(() => {
    let active = true;
    let instance: Leaflet.Map | undefined;
    import("leaflet").then(L => {
      if (!active || !container.current) return;
      instance = L.map(container.current, { scrollWheelZoom: false }).setView([23.77, 90.39], 12);
      currentMap.current = instance;
      tiles.current = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        // Explicit per-image policy also covers a tab opened before the root
        // metadata changed. Do not add cache-busting parameters to OSM tiles.
        referrerPolicy: "strict-origin-when-cross-origin",
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>',
      }).on("tileerror", () => { if (active) setTileError(true); }).addTo(instance);
      setMap(instance);
    });
    return () => { active = false; if (currentMap.current === instance) { currentMap.current = null; tiles.current = null; } instance?.remove(); };
  }, []);
  useEffect(() => {
    currentLanguage.current = language;
    if (!map || currentMap.current !== map) return;
    const zoomIn = map.getContainer().querySelector<HTMLAnchorElement>(".leaflet-control-zoom-in");
    const zoomOut = map.getContainer().querySelector<HTMLAnchorElement>(".leaflet-control-zoom-out");
    for (const [control, title] of [[zoomIn, language === "bn" ? "বড় করে দেখুন" : "Zoom in"], [zoomOut, language === "bn" ? "ছোট করে দেখুন" : "Zoom out"]] as const) {
      if (control) { control.title = title; control.setAttribute("aria-label", title); }
    }
    const layer = tiles.current;
    if (layer) {
      if (layer.options.attribution) map.attributionControl.removeAttribution(layer.options.attribution);
      layer.options.attribution = `&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap ${language === "bn" ? "অবদানকারী" : "contributors"}</a>`;
      map.attributionControl.addAttribution(layer.options.attribution);
    }
    map.eachLayer(layer => { if (layer.getPopup()?.isOpen()) layer.getPopup()?.update(); });
  }, [map, language]);
  const focusLatitude = focus?.latitude;
  const focusLongitude = focus?.longitude;
  useEffect(() => {
    if (map && currentMap.current === map && focusLatitude !== undefined && focusLongitude !== undefined) map.setView([focusLatitude, focusLongitude], 15, { animate: false });
  }, [map, focusLatitude, focusLongitude]);
  useEffect(() => {
    if (!map || currentMap.current !== map) return;
    let layer: Leaflet.LayerGroup | undefined;
    let active = true;
    import("leaflet").then(L => {
      if (!active || currentMap.current !== map) return;
      layer = L.layerGroup().addTo(map);
      for (const row of roads) {
        const color = row.condition === "bad" ? "#c03938" : row.condition === "good" ? "#22735c" : "#667884";
        // Localize on opening; switching language keeps the map layers intact.
        L.circleMarker([row.latitude, row.longitude], { radius: 9, color, fillColor: color, fillOpacity: 0.8 }).bindPopup(() => {
          const language = currentLanguage.current;
          const content = document.createElement("div");
          const title = document.createElement("strong"); title.textContent = row.name; content.append(title);
          const text = document.createElement("p");
          const open = civicNumber(row.open_complaints, language);
          text.textContent = `${civicLabel(row.condition, language)} · ${open} ${language === "bn" ? "টি অমীমাংসিত অভিযোগ" : "open complaints"}${row.sensitivity === "high" ? (language === "bn" ? " · অতীতে ঝুঁকিপূর্ণ" : " · historically sensitive") : ""}`;
          content.append(text);
          return content;
        }).addTo(layer);
      }
      for (const row of complaints.filter(c => c.status !== "false")) {
        L.circleMarker([row.latitude, row.longitude], { radius: 5, color: row.status === "resolved" || (row.kind === "road_update" && row.condition === "good") ? "#22735c" : "#d28423", fillOpacity: 0.7 }).bindPopup(() => {
          const link = document.createElement("a"); link.textContent = `${row.title} · ${civicLabel(row.status, currentLanguage.current)}`; link.href = `/complaints/${encodeURIComponent(row.id)}`;
          return link;
        }).addTo(layer);
      }
    });
    return () => { active = false; layer?.remove(); };
  }, [map, roads, complaints]);
  return <div className="live-road-map-frame"><div ref={container} className="live-road-map" aria-label={tr("Interactive Dhaka road condition map")} /><button type="button" className="city-map-reset" disabled={!map} onClick={() => map?.setView([23.77, 90.39], 12, { animate: false })}>{tr("Reset view")}</button>{tileError && <div className="map-load-notice" role="status"><span>{tr("Some street tiles could not load. Reports are still available in the activity panel.")}</span><button type="button" onClick={() => { setTileError(false); tiles.current?.redraw(); }}>{tr("Retry street map")}</button><a href="https://www.openstreetmap.org/#map=12/23.77/90.39" target="_blank" rel="noopener noreferrer">{tr("Open street map ↗")}</a></div>}</div>;
}
