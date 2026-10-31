const origin = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");
const base = origin.endsWith("/api/v1") ? origin : `${origin}/api/v1`;
export class ApiError extends Error {
  constructor(public status: number, public detail: string) { super(detail); }
}
export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${base}${path}`, {
    ...options, credentials: "include", cache: "no-store",
    headers: { "Content-Type": "application/json", ...options.headers },
    signal: options.signal ? AbortSignal.any([options.signal, AbortSignal.timeout(15000)]) : AbortSignal.timeout(15000),
  });
  const body = await response.json().catch(error => {
    if (response.status === 204) return {};
    if (error instanceof SyntaxError) {
      if (!response.ok) return {};
      throw new ApiError(502, "Invalid server response. Please try again.");
    }
    // An aborted or disconnected response body must not look like a successful save.
    throw error;
  });
  if (!response.ok) {
    const detail = typeof body.detail === "string" ? body.detail : Array.isArray(body.detail)
      ? body.detail.map((issue: { loc?: (string | number)[]; msg?: string }) => `${(issue.loc || []).filter(part => part !== "body").join(" · ")}: ${issue.msg || "Invalid value"}`).join(". ")
      : "Invalid request";
    throw new ApiError(response.status, detail);
  }
  return body as T;
}
// Mutations are serialized because the server rotates session-bound CSRF cookies.
let mutations: Promise<unknown> = Promise.resolve();
let csrfToken: string | null = null;
async function csrf() {
  if (!csrfToken) csrfToken = (await api<{ csrf_token: string }>("/auth/csrf")).csrf_token;
  return csrfToken;
}
export function mediaUrl(url: string) {
  return url.startsWith("/media/") ? `${origin.replace(/\/api\/v1$/, "")}${url}` : url;
}
export function uploadImage(file: File): Promise<string> {
  const request = mutations.then(async () => {
    const body = new FormData(); body.set("file", file);
    const send = async () => fetch(`${base}/media`, { method: "POST", credentials: "include", headers: { "X-CSRF-Token": await csrf() }, body, signal: AbortSignal.timeout(15000) });
    let response = await send();
    let result = await response.json().catch(() => ({}));
    if (response.status === 403 && result.detail === "Invalid CSRF token") {
      csrfToken = null; response = await send();
      result = await response.json().catch(() => ({}));
    }
    if (!response.ok) throw new ApiError(response.status, typeof result.detail === "string" ? result.detail : "Image upload failed");
    if (typeof result.url !== "string" || !result.url.startsWith("/media/")) throw new Error("Image upload failed");
    return result.url as string;
  });
  mutations = request.catch(() => undefined);
  return request;
}
export function mutate<T>(path: string, data?: unknown, method = "POST"): Promise<T> {
  const request = mutations.then(async () => {
    const send = async () => api<T>(path, { method, headers: { "X-CSRF-Token": await csrf() }, body: data === undefined ? undefined : JSON.stringify(data) });
    let result: T;
    try { result = await send(); }
    catch (error) {
      if (!(error instanceof ApiError) || error.status !== 403 || error.detail !== "Invalid CSRF token") throw error;
      // This rejection occurs before the handler, so retrying cannot duplicate a mutation.
      csrfToken = null;
      result = await send();
    }
    if (["/auth/login", "/auth/google", "/auth/logout", "/auth/logout-all", "/auth/reset-password"].includes(path)) csrfToken = null;
    return result;
  });
  mutations = request.catch(() => undefined);
  return request;
}
