"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api-client";

export interface Category { code: string; label: string; base_priority: number }
export interface Road { id: string; name: string; area_id: string; latitude: number; longitude: number; condition: string; open_complaints: number; sensitivity: string; historical_reports_90d: number; last_report_at: number | null; path?: [number, number][]; paths?: [number, number][][]; geometry_source?: string; segment_from?: string; segment_to?: string }
export interface Resolution { id: string; worker_id: string; worker_name: string; comment: string; image_url: string | null; status: string; likes: number; dislikes: number; created_at: number; superseded?: boolean }
export interface Complaint { id: string; title: string; description: string; address: string; category_code: string; kind: string; condition: string; latitude: number; longitude: number; status: string; priority: number; priority_source: string; images: string[]; author_name: string; likes: number; dislikes: number; created_at: number; incident_id?: string | null; incident_report_count?: number; incident_reporter_count?: number; points_awarded?: number; resolutions?: Resolution[]; active_assignment?: { worker_id: string } | null }
export function label(value: string) { return value.replaceAll("_", " "); }
export function date(value: number) { return new Date(value * 1000).toLocaleString("en-GB", { timeZone: "Asia/Dhaka" }); }
export function message(error: unknown) { return error instanceof Error ? error.message : "Please try again."; }
export function useResource<T>(path: string | null, poll = 0) {
  const [state, setState] = useState<{ path: string | null; data: T | null; error: string; loading: boolean }>({ path, data: null, error: "", loading: true });
  const currentPath = useRef(path);
  const generation = useRef(0);
  const active = useRef(false);
  const reload = useCallback(async (signal?: AbortSignal) => {
    if (!path || !active.current || currentPath.current !== path) return;
    const request = ++generation.current;
    try {
      const data = await api<T>(path, { signal });
      if (active.current && !signal?.aborted && request === generation.current && currentPath.current === path) {
        setState({ path, data, error: "", loading: false });
      }
    } catch (error) {
      if (active.current && !signal?.aborted && request === generation.current && currentPath.current === path) {
        setState(previous => ({ path, data: previous.path === path ? previous.data : null, error: message(error), loading: false }));
      }
    }
  }, [path]);
  useEffect(() => {
    currentPath.current = path;
    active.current = true;
    if (!path) return () => { active.current = false; };
    const controller = new AbortController();
    void reload(controller.signal);
    const timer = poll ? setInterval(() => { void reload(controller.signal); }, poll) : undefined;
    return () => { active.current = false; controller.abort(); clearInterval(timer); };
  }, [reload, poll, path]);
  return { ...(!path ? { data: null, error: "", loading: false } : state.path === path ? state : { data: null, error: "", loading: true }), reload };
}
