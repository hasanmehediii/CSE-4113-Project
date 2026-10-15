"use client";
import { useCallback, useEffect, useState } from "react";
import { api } from "./api-client";

export interface Category { code: string; label: string; base_priority: number }
export interface Road { id: string; name: string; area_id: string; latitude: number; longitude: number; condition: string; open_complaints: number; sensitivity: string; historical_reports_90d: number; last_report_at: number | null }
export interface Resolution { id: string; worker_id: string; worker_name: string; comment: string; image_url: string | null; status: string; likes: number; dislikes: number; created_at: number }
export interface Complaint { id: string; title: string; description: string; address: string; category_code: string; kind: string; condition: string; latitude: number; longitude: number; status: string; priority: number; priority_source: string; images: string[]; author_name: string; likes: number; dislikes: number; created_at: number; resolutions?: Resolution[]; active_assignment?: { worker_id: string } | null }
export function label(value: string) { return value.replaceAll("_", " "); }
export function date(value: number) { return new Date(value * 1000).toLocaleString("en-GB", { timeZone: "Asia/Dhaka" }); }
export function message(error: unknown) { return error instanceof Error ? error.message : "Please try again."; }
export function useResource<T>(path: string, poll = 0) {
  const [state, setState] = useState<{ data: T | null; error: string; loading: boolean }>({ data: null, error: "", loading: true });
  const reload = useCallback(async (signal?: AbortSignal) => {
    try {
      const data = await api<T>(path, { signal });
      if (!signal?.aborted) setState({ data, error: "", loading: false });
    } catch (error) {
      if (!signal?.aborted) setState(previous => ({ ...previous, error: message(error), loading: false }));
    }
  }, [path]);
  useEffect(() => {
    const controller = new AbortController();
    void reload(controller.signal);
    const timer = poll ? setInterval(() => { void reload(controller.signal); }, poll) : undefined;
    return () => { controller.abort(); clearInterval(timer); };
  }, [reload, poll]);
  return { ...state, reload };
}
