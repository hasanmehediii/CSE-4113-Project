const origin = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");
const base = origin.endsWith("/api/v1") ? origin : `${origin}/api/v1`;
export class ApiError extends Error {
  constructor(public status: number, public detail: string) { super(detail); }
}
export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${base}${path}`, {
    ...options, credentials: "include", cache: "no-store",
    headers: { "Content-Type": "application/json", ...options.headers },
    signal: options.signal ?? AbortSignal.timeout(15000),
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new ApiError(response.status, typeof body.detail === "string" ? body.detail : "Invalid request");
  return body as T;
}
// Mutations are serialized because the server rotates session-bound CSRF cookies.
let mutations: Promise<unknown> = Promise.resolve();
let csrfToken: string | null = null;
async function csrf() {
  if (!csrfToken) csrfToken = (await api<{ csrf_token: string }>("/auth/csrf")).csrf_token;
  return csrfToken;
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
