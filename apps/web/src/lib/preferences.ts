// An external store gives server rendering a stable default while hydrating
// from the preferences applied before first paint. Auth data never goes here.
export function subscribePreferences(callback: () => void) {
  const sync = () => {
    try {
      const root = document.documentElement;
      root.lang = localStorage.getItem("dubsi-language") === "bn" ? "bn" : "en";
      const theme = localStorage.getItem("dubsi-theme");
      root.dataset.theme = theme === "dark" || (!theme && matchMedia("(prefers-color-scheme: dark)").matches) ? "dark" : "light";
    } catch { /* Preferences remain available without storage. */ }
    callback();
  };
  window.addEventListener("storage", sync);
  window.addEventListener("dubsi-preferences", callback);
  const media = matchMedia("(prefers-color-scheme: dark)");
  media.addEventListener("change", sync);
  return () => { window.removeEventListener("storage", sync); window.removeEventListener("dubsi-preferences", callback); media.removeEventListener("change", sync); };
}
export function preferenceSnapshot() { return `${document.documentElement.lang}:${document.documentElement.dataset.theme}`; }
export function serverPreferences() { return "en:light"; }
export function changePreference(key: "language" | "theme", value: string) {
  if (key === "language") document.documentElement.lang = value;
  else document.documentElement.dataset.theme = value;
  try { localStorage.setItem(`dubsi-${key}`, value); } catch { /* Optional storage. */ }
  window.dispatchEvent(new Event("dubsi-preferences"));
}
