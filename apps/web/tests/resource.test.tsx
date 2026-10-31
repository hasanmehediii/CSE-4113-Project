import assert from "node:assert/strict";
import { before, after, afterEach, test, type TestContext } from "node:test";
import { act, useEffect, type ReactNode } from "react";
import { JSDOM } from "jsdom";
import type { Root } from "react-dom/client";

let dom: JSDOM;
let root: Root | undefined;
let createRoot: typeof import("react-dom/client").createRoot;
let useResource: typeof import("../src/lib/civic").useResource;
let reload: () => Promise<void>;
const originalFetch = globalThis.fetch;

before(async () => {
  dom = new JSDOM("<div id='root'></div>", { url: "http://localhost:3000", pretendToBeVisual: true });
  const matchMedia = (media: string) => ({
    media, matches: false, onchange: null, addListener() {}, removeListener() {},
    addEventListener() {}, removeEventListener() {}, dispatchEvent() { return false; },
  });
  dom.window.matchMedia = matchMedia;
  Object.assign(globalThis, {
    window: dom.window, self: dom.window, document: dom.window.document, localStorage: dom.window.localStorage,
    matchMedia, Element: dom.window.Element, Node: dom.window.Node,
    HTMLElement: dom.window.HTMLElement, HTMLInputElement: dom.window.HTMLInputElement,
    HTMLSelectElement: dom.window.HTMLSelectElement, HTMLTextAreaElement: dom.window.HTMLTextAreaElement,
    Event: dom.window.Event, FormData: dom.window.FormData, IS_REACT_ACT_ENVIRONMENT: true,
  });
  Object.defineProperty(globalThis, "navigator", { configurable: true, value: dom.window.navigator });
  ({ createRoot } = await import("react-dom/client"));
  ({ useResource } = await import("../src/lib/civic"));
});
afterEach(async () => { if (root) await act(async () => root!.unmount()); root = undefined; localStorage.clear(); });
after(() => { globalThis.fetch = originalFetch; dom.window.close(); });

function Probe({ path }: { path: string }) {
  const resource = useResource<string>(path);
  useEffect(() => { reload = resource.reload; }, [resource.reload]);
  return <div>{resource.loading ? "Loading" : resource.data || "No data"}{resource.error && `: ${resource.error}`}</div>;
}
async function render(path: string) {
  await renderNode(<Probe path={path}/>);
}
async function renderNode(node: ReactNode) {
  try {
    await act(async () => {
      root ||= createRoot(document.getElementById("root")!);
      root.render(node);
    });
  } catch (error) {
    if (error instanceof AggregateError) throw new Error(error.errors.map(cause => String(cause.stack || cause)).join("\n"));
    throw error;
  }
}
function pendingRequests(t: TestContext) {
  const requests: { url: string; resolve: (value: Response) => void }[] = [];
  t.mock.method(globalThis, "fetch", (url: string) => new Promise<Response>(resolve => { requests.push({ url, resolve }); }));
  return requests;
}
async function finish(request: { resolve: (value: Response) => void }, data: unknown, status = 200) {
  await act(async () => { request.resolve(new Response(JSON.stringify(data), { status })); });
}
const content = () => document.getElementById("root")!.textContent;

test("changing the report hides old data immediately and ignores an old manual refresh", async t => {
  const requests = pendingRequests(t);
  await render("/complaints/old");
  await finish(requests[0], "Old report");
  assert.equal(content(), "Old report");
  let oldRefresh: Promise<void>;
  await act(async () => { oldRefresh = reload(); });
  await render("/complaints/new");
  assert.equal(content(), "Loading");
  await finish(requests[2], "New report");
  await finish(requests[1], "Late old report");
  await oldRefresh!;
  assert.equal(content(), "New report");
});

test("a failed new route never presents the old report as its content", async t => {
  const requests = pendingRequests(t);
  await render("/complaints/old");
  await finish(requests[0], "Old report");
  await render("/complaints/missing");
  await finish(requests[1], { detail: "Report not found" }, 404);
  assert.equal(content(), "No data: Report not found");
});

test("overlapping reloads keep the newest response", async t => {
  const requests = pendingRequests(t);
  await render("/complaints");
  await finish(requests[0], "Initial");
  await act(async () => { void reload(); void reload(); });
  await finish(requests[2], "Newest");
  await finish(requests[1], "Stale");
  assert.equal(content(), "Newest");
});

test("a failed refresh preserves data only for the same resource", async t => {
  const requests = pendingRequests(t);
  await render("/complaints");
  await finish(requests[0], "Current list");
  await act(async () => { void reload(); });
  await finish(requests[1], { detail: "Service unavailable" }, 503);
  assert.equal(content(), "Current list: Service unavailable");
});

const report = {
  id: "assigned", title: "Assigned drainage complaint", description: "Drainage needs cleaning.",
  address: "Dhaka main road", category_code: "road_flooding", kind: "complaint", condition: "bad",
  latitude: 23.75, longitude: 90.37, status: "assigned", priority: 50, priority_source: "category_rules",
  images: [], author_name: "Resident", likes: 0, dislikes: 0, created_at: 1, resolutions: [],
  active_assignment: { worker_id: "previous-worker" },
};

test("the mayor can explicitly replace an assigned worker from complaint details", async t => {
  let submitted: Record<string, unknown> | null = null;
  t.mock.method(globalThis, "fetch", async (url: RequestInfo | URL, options?: RequestInit) => {
    const path = new URL(String(url)).pathname;
    const body = path.endsWith("/auth/me") ? { id: "mayor", role: "admin", email_verified: true }
      : path.endsWith("/auth/csrf") ? { csrf_token: "token" }
      : path.endsWith("/admin/users") ? [
        { id: "previous-worker", name: "Previous", is_active: true },
        { id: "replacement-worker", name: "Replacement", is_active: true },
      ] : path.endsWith("/assign") ? (submitted = JSON.parse(String(options?.body)))
      : report;
    return new Response(JSON.stringify(body));
  });
  const { Providers } = await import("../src/components/Providers");
  const { default: ComplaintDetail } = await import("../src/components/ComplaintDetail");
  await renderNode(<Providers><ComplaintDetail id="assigned"/></Providers>);
  const form = document.querySelector<HTMLFormElement>("form")!;
  assert.ok(form);
  const select = form.querySelector<HTMLSelectElement>("select")!;
  assert.ok(!Array.from(select.options).some(option => option.value === "previous-worker"));
  select.value = "replacement-worker";
  const button = form.querySelector<HTMLButtonElement>("button")!;
  assert.equal(button.disabled, false);
  assert.equal(button.textContent, "Reassign complaint");
  await act(async () => { button.click(); });
  assert.deepEqual(submitted, { worker_id: "replacement-worker", reassign: true });
});

test("the worker workspace translates and paginates active work without requesting GPS to stop availability", async t => {
  const requests: URL[] = [];
  let stopped = false;
  t.mock.method(globalThis, "fetch", async (url: RequestInfo | URL, options?: RequestInit) => {
    const request = new URL(String(url)); requests.push(request);
    const body = request.pathname.endsWith("/auth/me") ? { id: "worker", role: "worker", email_verified: true }
      : request.pathname.endsWith("/auth/csrf") ? { csrf_token: "token" }
      : request.pathname.endsWith("/workers/availability") ? (stopped = JSON.parse(String(options?.body)).available === false, {})
      : request.pathname.endsWith("/categories") ? []
      : request.pathname.endsWith("/workers/assignments") ? request.searchParams.get("offset") === "30"
        ? [{ id: "older", status: "active", complaint: { ...report, id: "older", title: "Older active report" } }]
        : Array.from({ length: 30 }, (_, i) => ({ id: String(i), status: "active", complaint: { ...report, id: String(i), title: `Active report ${i}` } }))
      : [];
    return new Response(JSON.stringify(body));
  });
  const { Providers } = await import("../src/components/Providers");
  const { default: WorkerDashboard } = await import("../src/components/WorkerDashboard");
  const { changePreference } = await import("../src/lib/preferences");
  await renderNode(<Providers><WorkerDashboard/></Providers>);
  const next = Array.from(document.querySelectorAll("button")).find(button => button.textContent === "Next")!;
  assert.equal(next.disabled, false);
  await act(async () => { next.click(); });
  assert.ok(content()?.includes("Older active report"));
  assert.ok(!content()?.includes("Active report 0"));
  assert.ok(requests.some(url => url.pathname.endsWith("/workers/assignments") && url.searchParams.get("status") === "active" && url.searchParams.get("offset") === "30"));
  await act(async () => { changePreference("language", "bn"); });
  assert.ok(content()?.includes("আমার দায়িত্ব"));
  const unavailable = Array.from(document.querySelectorAll("button")).find(button => button.textContent === "এখন কাজ নিতে পারব না")!;
  await act(async () => { unavailable.click(); });
  assert.equal(stopped, true);
  assert.ok(content()?.includes("স্বয়ংক্রিয়ভাবে এখন আপনাকে নতুন কাজ দেওয়া হবে না।"));
});
