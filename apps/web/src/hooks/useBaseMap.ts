"use client";
import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from "react";
import type * as Leaflet from "leaflet";
import { useApp } from "@/components/Providers";
import {
  createBaseLayer, osmAttribution, readBaseMapChoice, resolveBaseMap, saveBaseMapChoice, styleBaseLayer,
  subscribeBaseMapChoice, type BaseMapChoice,
} from "@/lib/map-tiles";

/**
 * Keeps one OpenStreetMap base layer on a Leaflet map, styled by the viewer's saved
 * choice (or the site theme for "auto"), with localized attribution and tile-error retry.
 */
export function useBaseMap(map: Leaflet.Map | null) {
  const { theme, language } = useApp();
  const choice = useSyncExternalStore(subscribeBaseMapChoice, readBaseMapChoice, () => "auto" as BaseMapChoice);
  const base = resolveBaseMap(choice, theme);
  const tiles = useRef<Leaflet.TileLayer | null>(null);
  const currentBase = useRef(base);
  const currentLanguage = useRef(language);
  const [tileError, setTileError] = useState(false);

  useEffect(() => {
    if (!map) return;
    let active = true;
    let layer: Leaflet.TileLayer | undefined;
    import("leaflet").then(L => {
      if (!active) return;
      layer = createBaseLayer(L, currentLanguage.current)
        .on("tileerror", () => { if (active) setTileError(true); })
        .on("load", () => { if (active) setTileError(false); });
      layer.addTo(map).bringToBack();
      styleBaseLayer(layer, currentBase.current);
      tiles.current = layer;
    });
    return () => { active = false; if (tiles.current === layer) tiles.current = null; layer?.remove(); };
  }, [map]);

  useEffect(() => {
    currentBase.current = base;
    if (tiles.current) styleBaseLayer(tiles.current, base);
  }, [base]);

  useEffect(() => {
    currentLanguage.current = language;
    const layer = tiles.current;
    if (!map || !layer) return;
    if (layer.options.attribution) map.attributionControl.removeAttribution(layer.options.attribution);
    layer.options.attribution = osmAttribution(language);
    map.attributionControl.addAttribution(layer.options.attribution);
  }, [map, language]);

  const retry = useCallback(() => { setTileError(false); tiles.current?.redraw(); }, []);
  return { choice, base, setChoice: saveBaseMapChoice, tileError, retry };
}
