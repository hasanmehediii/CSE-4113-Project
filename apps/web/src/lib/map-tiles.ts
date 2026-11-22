import type * as Leaflet from "leaflet";

/**
 * Base maps shared by every Leaflet map. "auto" follows the site theme.
 *
 * All styles use the same OpenStreetMap raster tiles; Light and Dark are drawn by CSS
 * filters on the tile layer only (see live-map.css), so road overlays keep their colours,
 * no API key or extra provider is needed, and switching reuses cached tiles. Keyless
 * third-party light/dark basemaps (for example CARTO) now watermark tiles without a key.
 */
export type BaseMap = "streets" | "light" | "dark";
export type BaseMapChoice = "auto" | BaseMap;
export const BASE_MAP_CHOICES: BaseMapChoice[] = ["auto", "streets", "light", "dark"];

// Do not add cache-busting parameters to OSM tiles (OSM tile usage policy).
export const OSM_TILES = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
export const osmAttribution = (language: string) =>
  `&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap ${language === "bn" ? "অবদানকারী" : "contributors"}</a>`;

export function resolveBaseMap(choice: BaseMapChoice, theme: string): BaseMap {
  // Auto keeps the familiar street map in light mode and a matching dark map in dark mode.
  return choice === "auto" ? (theme === "dark" ? "dark" : "streets") : choice;
}

const STORAGE_KEY = "dubsi-map-base";
const CHANGE_EVENT = "dubsi-map-base-change";

export function readBaseMapChoice(): BaseMapChoice {
  try {
    const value = localStorage.getItem(STORAGE_KEY) as BaseMapChoice | null;
    return value && BASE_MAP_CHOICES.includes(value) ? value : "auto";
  } catch {
    return "auto";
  }
}

export function saveBaseMapChoice(choice: BaseMapChoice) {
  try { localStorage.setItem(STORAGE_KEY, choice); } catch { /* Optional storage; the choice still applies now. */ }
  window.dispatchEvent(new Event(CHANGE_EVENT));
}

export function subscribeBaseMapChoice(onChange: () => void) {
  const onStorage = (event: StorageEvent) => { if (event.key === STORAGE_KEY) onChange(); };
  window.addEventListener(CHANGE_EVENT, onChange);
  window.addEventListener("storage", onStorage);
  return () => { window.removeEventListener(CHANGE_EVENT, onChange); window.removeEventListener("storage", onStorage); };
}

export function createBaseLayer(L: typeof Leaflet, language: string) {
  return L.tileLayer(OSM_TILES, {
    maxZoom: 19,
    referrerPolicy: "strict-origin-when-cross-origin",
    attribution: osmAttribution(language),
    className: "base-map-tiles",
  });
}

/** Applies a style to an existing base layer without reloading its tiles. */
export function styleBaseLayer(layer: Leaflet.TileLayer, base: BaseMap) {
  const element = layer.getContainer();
  if (!element) return;
  for (const name of ["streets", "light", "dark"] as const) element.classList.toggle(`base-map-${name}`, name === base);
}
