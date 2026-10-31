"use client";
import { useEffect, useRef, useState } from "react";
import type { RoadMapProps } from "./LiveRoadMap";
import { googleMapsKey, riskColor, roadPaths } from "@/lib/road-map";
import { useCivicLocale } from "@/hooks/useCivicLocale";
import { useRouter } from "next/navigation";

interface GMap { setCenter(point: Point): void; setZoom(zoom: number): void; fitBounds(bounds: Bounds, padding?: number): void }
interface Point { lat: number; lng: number }
interface Bounds { extend(point: Point): void }
interface Overlay { setMap(map: GMap | null): void; addListener(event: string, listener: () => void): void }
interface Maps {
  Map: new (node: HTMLElement, options: Record<string, unknown>) => GMap;
  Polyline: new (options: Record<string, unknown>) => Overlay;
  Circle: new (options: Record<string, unknown>) => Overlay;
  LatLngBounds: new () => Bounds;
  event: { clearInstanceListeners(instance: object): void };
}
const globals = () => window as unknown as { google?: { maps: Maps }; __dubsiMapsLoaded?: () => void };
let loader: Promise<Maps> | null = null;
function loadGoogle(): Promise<Maps> {
  if (globals().google?.maps.Map) return Promise.resolve(globals().google!.maps);
  if (loader) return loader;
  loader = new Promise<Maps>((resolve, reject) => {
    if (!googleMapsKey) { reject(new Error("Google Maps key missing")); return; }
    const script = document.createElement("script");
    const fail = () => { clearTimeout(timer); delete globals().__dubsiMapsLoaded; script.remove(); reject(new Error("Google Maps could not load")); };
    const timer = setTimeout(fail, 15000);
    globals().__dubsiMapsLoaded = () => { clearTimeout(timer); delete globals().__dubsiMapsLoaded; resolve(globals().google!.maps); };
    script.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(googleMapsKey)}&loading=async&callback=__dubsiMapsLoaded&v=weekly`;
    script.async = true; script.onerror = fail;
    document.head.appendChild(script);
  }).catch(error => { loader = null; throw error; });
  return loader;
}

export default function GoogleRoadMap({ roads, complaints, focus, onSelectRoad, risks, hazard, predictionMode }: RoadMapProps) {
  const router = useRouter();
  const { tr } = useCivicLocale();
  const container = useRef<HTMLDivElement>(null);
  const instance = useRef<GMap | null>(null);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    let map: GMap | null = null;
    loadGoogle().then(G => {
      if (!active || !container.current) return;
      map = new G.Map(container.current, { center: { lat: 23.785, lng: 90.395 }, zoom: 12, minZoom: 11, maxZoom: 16,
        restriction: { latLngBounds: { north: 23.91, south: 23.66, west: 90.28, east: 90.51 }, strictBounds: true },
        mapTypeControl: false, streetViewControl: false, gestureHandling: "cooperative" });
      instance.current = map; setReady(true);
    }).catch(e => { if (active) setError(e.message); });
    return () => { active = false; if (map) globals().google?.maps.event.clearInstanceListeners(map); instance.current = null; };
  }, []);
  useEffect(() => {
    const map = instance.current, G = globals().google?.maps;
    if (!ready || !map || !G) return;
    const overlays: Overlay[] = [];
    for (const road of roads) {
      const color = predictionMode ? riskColor(risks?.find(row => row.road_id === road.id), hazard) : road.condition === "bad" ? "#c03938" : road.condition === "good" ? "#22735c" : "#667884";
      const paths = roadPaths(road);
      if (paths.length) {
        for (const points of paths) {
          const path = points.map(([lat, lng]) => ({ lat, lng }));
          overlays.push(new G.Polyline({ map, path, strokeColor: focus?.id === road.id ? "#086bbc" : "#ffffff", strokeWeight: 12, clickable: false }));
          const line = new G.Polyline({ map, path, strokeColor: color, strokeWeight: 7,
            ...(predictionMode ? { strokeOpacity: 0, icons: [{ icon: { path: "M 0,-1 0,1", strokeColor: color, strokeOpacity: 1, scale: 3 }, offset: "0", repeat: "16px" }] } : {}) });
          line.addListener("click", () => onSelectRoad?.(road)); overlays.push(line);
        }
      } else {
        const marker = new G.Circle({ map, center: { lat: road.latitude, lng: road.longitude }, radius: 60, fillColor: color, fillOpacity: .85, strokeColor: color });
        marker.addListener("click", () => onSelectRoad?.(road)); overlays.push(marker);
      }
    }
    for (const row of complaints.filter(r => r.status !== "false")) {
      const marker = new G.Circle({ map, center: { lat: row.latitude, lng: row.longitude }, radius: 35, fillColor: "#d28423", fillOpacity: .8, strokeColor: "#fff" });
      marker.addListener("click", () => { router.push(`/complaints/${encodeURIComponent(row.id)}`); }); overlays.push(marker);
    }
    return () => { overlays.forEach(overlay => { G.event.clearInstanceListeners(overlay); overlay.setMap(null); }); };
  }, [ready, roads, complaints, focus, onSelectRoad, risks, hazard, predictionMode, router]);
  useEffect(() => {
    const map = instance.current, G = globals().google?.maps;
    if (!ready || !map || !G || !focus) return;
    if (roadPaths(focus).length) { const bounds = new G.LatLngBounds(); roadPaths(focus).flat().forEach(([lat, lng]) => bounds.extend({ lat, lng })); map.fitBounds(bounds, 50); }
    else { map.setCenter({ lat: focus.latitude, lng: focus.longitude }); map.setZoom(14); }
  }, [ready, focus]);
  return <div className="live-road-map-frame"><div ref={container} className="live-road-map" aria-label={tr("Interactive Dhaka road condition map")} /><button className="city-map-reset" type="button" onClick={() => { instance.current?.setCenter({ lat: 23.785, lng: 90.395 }); instance.current?.setZoom(12); }}>{tr("Reset view")}</button>{error && <div className="map-load-notice" role="alert">{tr("Street map unavailable. Select a road from the list to continue.")}</div>}</div>;
}
