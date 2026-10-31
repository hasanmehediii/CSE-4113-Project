"use client";

import { useEffect, useRef, useState } from "react";
import type * as Leaflet from "leaflet";
import { useCivicLocale } from "@/hooks/useCivicLocale";
import { DHAKA_CENTRE, isDhakaLocation, type ReportLocation } from "@/lib/report-location";

type Props = {
  value: ReportLocation | null;
  onChange: (point: ReportLocation) => void;
  onError: (message: string) => void;
  disabled?: boolean;
};

export default function LocationPicker({ value, onChange, onError, disabled = false }: Props) {
  const { tr, language } = useCivicLocale();
  const container = useRef<HTMLDivElement>(null);
  const instance = useRef<Leaflet.Map | null>(null);
  const marker = useRef<Leaflet.Marker | null>(null);
  const tiles = useRef<Leaflet.TileLayer | null>(null);
  const latest = useRef({ value, onChange, onError, disabled });
  const [map, setMap] = useState<Leaflet.Map | null>(null);
  const [tileError, setTileError] = useState(false);
  const [loadError, setLoadError] = useState(false);

  useEffect(() => { latest.current = { value, onChange, onError, disabled }; }, [value, onChange, onError, disabled]);

  useEffect(() => {
    let active = true;
    let current: Leaflet.Map | undefined;
    let observer: ResizeObserver | undefined;
    import("leaflet").then(L => {
      if (!active || !container.current) return;
      current = L.map(container.current, {
        scrollWheelZoom: false,
        maxBounds: [[23.6, 90.2], [24, 90.6]],
        minZoom: 11,
      }).setView([DHAKA_CENTRE.latitude, DHAKA_CENTRE.longitude], 12);
      instance.current = current;
      tiles.current = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        referrerPolicy: "strict-origin-when-cross-origin",
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>',
      }).on("tileerror", () => { if (active) setTileError(true); }).addTo(current);
      current.on("click", (event: Leaflet.LeafletMouseEvent) => {
        if (latest.current.disabled) return;
        const point = { latitude: event.latlng.lat, longitude: event.latlng.lng };
        if (isDhakaLocation(point)) latest.current.onChange(point);
        else latest.current.onError("Report locations must be within the Dhaka service area.");
      });
      if (typeof ResizeObserver !== "undefined") {
        observer = new ResizeObserver(() => current?.invalidateSize());
        observer.observe(container.current);
      }
      setMap(current);
    }).catch(() => { if (active) setLoadError(true); });
    return () => {
      active = false;
      observer?.disconnect();
      if (instance.current === current) {
        instance.current = null;
        marker.current = null;
        tiles.current = null;
      }
      current?.remove();
    };
  }, []);

  const latitude = value?.latitude;
  const longitude = value?.longitude;
  useEffect(() => {
    if (!map || instance.current !== map) return;
    let active = true;
    import("leaflet").then(L => {
      if (!active || instance.current !== map) return;
      if (latitude === undefined || longitude === undefined) {
        marker.current?.remove();
        marker.current = null;
        return;
      }
      const point: Leaflet.LatLngTuple = [latitude, longitude];
      if (!marker.current) {
        marker.current = L.marker(point, {
          draggable: !disabled,
          icon: L.divIcon({
            className: "report-map-marker",
            html: '<span class="report-map-pin"><span></span></span>',
            iconSize: [36, 44], iconAnchor: [18, 44],
          }),
        }).addTo(map);
        marker.current.on("dragend", () => {
          const moved = marker.current?.getLatLng();
          if (!moved || latest.current.disabled) return;
          const point = { latitude: moved.lat, longitude: moved.lng };
          if (isDhakaLocation(point)) latest.current.onChange(point);
          else {
            const previous = latest.current.value;
            if (previous) marker.current?.setLatLng([previous.latitude, previous.longitude]);
            latest.current.onError("Report locations must be within the Dhaka service area.");
          }
        });
      } else marker.current.setLatLng(point);
      if (disabled) marker.current.dragging?.disable();
      else marker.current.dragging?.enable();
      marker.current.getElement()?.setAttribute("aria-label", tr("Selected report location. Drag to adjust."));
      if (!map.getBounds().contains(point)) map.panTo(point, { animate: false });
    });
    return () => { active = false; };
  }, [map, latitude, longitude, disabled, tr]);

  useEffect(() => {
    if (!map || instance.current !== map) return;
    for (const [selector, title] of [[".leaflet-control-zoom-in", tr("Zoom in")], [".leaflet-control-zoom-out", tr("Zoom out")]]) {
      const control = map.getContainer().querySelector<HTMLAnchorElement>(selector);
      if (control) { control.title = title; control.setAttribute("aria-label", title); }
    }
    const layer = tiles.current;
    if (layer) {
      if (layer.options.attribution) map.attributionControl.removeAttribution(layer.options.attribution);
      layer.options.attribution = `&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap ${language === "bn" ? "অবদানকারী" : "contributors"}</a>`;
      map.attributionControl.addAttribution(layer.options.attribution);
    }
  }, [map, language, tr]);

  function chooseCentre() {
    if (!map || disabled) return;
    const centre = map.getCenter();
    const point = { latitude: centre.lat, longitude: centre.lng };
    if (isDhakaLocation(point)) onChange(point);
    else onError("Report locations must be within the Dhaka service area.");
  }

  return <div className="report-location-picker">
    <div className="report-map-canvas" ref={container} aria-label={tr("Choose report location on the map")} aria-describedby="report-map-help" />
    <span className="report-map-crosshair" aria-hidden="true">+</span>
    <button type="button" className="report-map-centre" disabled={!map || disabled} onClick={chooseCentre}>{tr("Use map centre")}</button>
    {!map && !loadError && <span className="report-map-loading" role="status">{tr("Loading map…")}</span>}
    {(tileError || loadError) && <div className="report-map-error" role="status">
      <span>{tr("Map unavailable? Use your current location or enter coordinates below.")}</span>
      {tileError && <button type="button" onClick={() => { setTileError(false); tiles.current?.redraw(); }}>{tr("Retry street map")}</button>}
    </div>}
  </div>;
}
