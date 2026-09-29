"use client";
import { createContext, useCallback, useContext, useEffect, useRef, useState, useSyncExternalStore, type ReactNode } from "react";
import { subscribePreferences, preferenceSnapshot, serverPreferences, changePreference } from "@/lib/preferences";
import { api, ApiError, mutate } from "@/lib/api-client";
import type { User } from "@/lib/auth";
type Language = "en" | "bn";
type Theme = "light" | "dark";
type Context = {
  language: Language; theme: Theme;
  setLanguage: (value: Language) => void; setTheme: (value: Theme) => void;
  t: (en: string, bn: string) => string;
  user: User | null; loading: boolean; authUnavailable: boolean;
  refresh: () => Promise<void>; setUser: (user: User | null) => void;
  logout: (all?: boolean) => Promise<void>;
};
const AppContext = createContext<Context | null>(null);
export function Providers({ children }: { children: ReactNode }) {
  const preferences = useSyncExternalStore(subscribePreferences, preferenceSnapshot, serverPreferences);
  const language: Language = preferences.startsWith("bn:") ? "bn" : "en";
  const theme: Theme = preferences.endsWith(":dark") ? "dark" : "light";
  const [user, updateUser] = useState<User | null>(null);
  const generation = useRef(0);
  const [loading, setLoading] = useState(true);
  const [authUnavailable, setUnavailable] = useState(false);
  const setUser = useCallback((value: User | null) => {
    generation.current += 1;
    updateUser(value); setLoading(false); setUnavailable(false);
  }, []);
  const setLanguage = useCallback((value: Language) => {
    changePreference("language", value);
  }, []);
  const setTheme = useCallback((value: Theme) => {
    changePreference("theme", value);
  }, []);
  const refresh = useCallback(() => {
    const request = ++generation.current;
    return api<User>("/auth/me").then(value => {
      if (request !== generation.current) return;
      updateUser(value); setUnavailable(false);
    }, error => {
      if (request !== generation.current) return;
      if (error instanceof ApiError && error.status === 401) { updateUser(null); setUnavailable(false); }
      else setUnavailable(true);
    }).finally(() => { if (request === generation.current) setLoading(false); });
  }, []);
  useEffect(() => {
    void refresh();
    const onFocus = () => { void refresh(); };
    window.addEventListener("focus", onFocus);
    return () => { window.removeEventListener("focus", onFocus); };
  }, [refresh]);
  async function logout(all = false) { await mutate(`/auth/${all ? "logout-all" : "logout"}`); setUser(null); }
  return <AppContext.Provider value={{ language, theme, setLanguage, setTheme, t: (en, bn) => language === "bn" ? bn : en, user, loading, authUnavailable, refresh, setUser, logout }}>{children}</AppContext.Provider>;
}
export function useApp() { const context = useContext(AppContext); if (!context) throw new Error("useApp requires Providers"); return context; }
