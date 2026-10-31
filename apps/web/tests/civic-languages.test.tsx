import assert from "node:assert/strict";
import { after, afterEach, before, test } from "node:test";
import { act, type ComponentType } from "react";
import { JSDOM } from "jsdom";
import type { Root } from "react-dom/client";
import { AppRouterContext } from "next/dist/shared/lib/app-router-context.shared-runtime";

let dom: JSDOM;
let root: Root | undefined;
let createRoot: typeof import("react-dom/client").createRoot;
let Providers: typeof import("../src/components/Providers").Providers;
let Navbar: typeof import("../src/components/Navbar").default;
let CityMap: typeof import("../src/components/CityMap").default;
let AdminDashboard: typeof import("../src/components/AdminDashboard").default;
let LandingHero: typeof import("../src/components/LandingHero").default;
let AuthForm: typeof import("../src/components/AuthForm").default;
let reducedMotion = false;
let signedIn = true;
let mapFixtures = false;
let lineFixtures = false;
let authMutation: { path: string; body: Record<string, unknown> } | null = null;
let workspace: typeof import("../src/components/ComplaintWorkspace");
let userRole = "citizen";
let adminMutation: { path: string; method: string; body: Record<string, unknown> } | null = null;
let adminError = "";
let emptyAdmin = false;
let application: null | { status: string; review_note: string } = null;
let submittedReport: Record<string, unknown> | null = null;
let predictionQuery = "";
let destination = "";
const originalFetch = globalThis.fetch;

const router = { back() {}, forward() {}, refresh() {}, push(path: string) { destination = path; }, replace(path: string) { destination = path; }, prefetch() {}, bfcacheId: "test" };

before(async () => {
  dom = new JSDOM("<!doctype html><html lang='en' data-theme='light'><body><div id='root'></div></body></html>", { url: "http://localhost:3000", pretendToBeVisual: true });
  const window = dom.window;
  Object.defineProperty(window.SVGSVGElement.prototype, "createSVGRect", { configurable: true, value: () => ({}) });
  window.scrollTo = () => {};
  Object.assign(globalThis, {
    window, self: window, document: window.document, localStorage: window.localStorage,
    HTMLElement: window.HTMLElement, HTMLInputElement: window.HTMLInputElement,
    HTMLSelectElement: window.HTMLSelectElement, HTMLTextAreaElement: window.HTMLTextAreaElement,
    Element: window.Element, Node: window.Node, SVGElement: window.SVGElement,
    Event: window.Event, File: window.File, Image: window.Image, FormData: window.FormData,
    getComputedStyle: window.getComputedStyle, requestAnimationFrame: window.requestAnimationFrame.bind(window),
    cancelAnimationFrame: window.cancelAnimationFrame.bind(window), IS_REACT_ACT_ENVIRONMENT: true,
  });
  Object.defineProperty(globalThis, "navigator", { value: window.navigator, configurable: true });
  const matchMedia = (query: string) => ({ matches: query === "(prefers-reduced-motion: reduce)" && reducedMotion, media: query, onchange: null, addListener() {}, removeListener() {}, addEventListener() {}, removeEventListener() {}, dispatchEvent() { return false; } });
  window.matchMedia = matchMedia;
  Object.assign(globalThis, { matchMedia });
  // Leaflet needs a measurable viewport; JSDOM has no CSS layout engine.
  for (const [property, size] of [["clientWidth", 800], ["offsetWidth", 800], ["clientHeight", 345], ["offsetHeight", 345]] as const) {
    Object.defineProperty(window.HTMLElement.prototype, property, { configurable: true, get() { return this.classList.contains("report-map-canvas") || this.classList.contains("live-road-map") ? size : 0; } });
  }
  const originalRect = window.HTMLElement.prototype.getBoundingClientRect;
  window.HTMLElement.prototype.getBoundingClientRect = function() {
    return this.classList.contains("report-map-canvas") || this.classList.contains("live-road-map") ? { x: 0, y: 0, top: 0, left: 0, right: 800, bottom: 345, width: 800, height: 345, toJSON() {} } : originalRect.call(this);
  };
  globalThis.fetch = async (input, options) => {
    const url = new URL(String(input));
    const path = url.pathname;
    if (path.endsWith("/map/predictions")) {
      predictionQuery = url.search;
      return new Response(JSON.stringify({ at: url.searchParams.get("at"), rainfall_mm: Number(url.searchParams.get("rainfall_mm")), forecast_horizon_min: Number(url.searchParams.get("forecast_horizon_min") || 60), timezone: "Asia/Dhaka", data_source: "synthetic", model_version: "test-road-risk-v1", roads: [
        { road_id: "bad-road", waterlogging_probability: .8, traffic_probability: .2, risk: "high" },
        { road_id: "good-road", waterlogging_probability: .1, traffic_probability: .7, risk: "high" },
      ] }));
    }
    if (path.endsWith("/auth/me") && !signedIn) return new Response(JSON.stringify({ detail: "Authentication required" }), { status: 401 });
    if ((path.endsWith("/auth/login") || path.endsWith("/auth/register")) && options?.method === "POST") {
      authMutation = { path, body: JSON.parse(String(options.body)) };
      return new Response(JSON.stringify(path.endsWith("/login") ? { id: "resident", name: "Resident Alpha", role: "citizen", email_verified: true } : { message: "If eligible, an email will be sent. Check your inbox." }), { status: path.endsWith("/login") ? 200 : 202 });
    }
    if (path.includes("/admin/") && options?.method && options.method !== "GET") {
      adminMutation = { path, method: options.method, body: JSON.parse(String(options.body)) };
      return new Response(JSON.stringify(adminError ? { detail: adminError } : {}), { status: adminError ? 409 : 200 });
    }
    if (path.endsWith("/complaints") && options?.method === "POST") {
      submittedReport = JSON.parse(String(options.body));
      return new Response(JSON.stringify({ id: "created-report" }), { status: 201 });
    }
    const body = path.endsWith("/auth/me") ? { id: "resident", name: "Resident Alpha", role: userRole, email_verified: true }
      : path.endsWith("/auth/csrf") ? { csrf_token: "test-csrf" }
      : path.endsWith("/admin/analytics") ? {
        by_status: emptyAdmin ? {} : { assigned: 2, resolved: 1 }, by_category: emptyAdmin ? {} : { blocked_drain: 3 },
        by_area: emptyAdmin ? [] : [{ area: "Original area name", total: 3, resolved: 1 }],
        leaders: emptyAdmin ? [] : [{ id: "leader", name: "Original leader name", points: 12 }], users: 10, workers: 2, unmapped_reports: 1,
      }
      : path.endsWith("/admin/users") ? emptyAdmin ? [] : [{ id: "account", name: "Original account name", email: "account@example.com", phone: null, role: url.searchParams.get("role") || "citizen", is_active: true, points: 12 }]
      : path.endsWith("/admin/worker-applications") ? [{ user_id: "applicant", name: "Original applicant name", email: "applicant@example.com", has_nid_number: true, nid_image_url: "https://example.com/private-identity.jpg" }]
      : path.endsWith("/admin/moderation") ? [
        { id: "case", complaint_id: "report", subject_name: "Original subject name", kind: "false_complaint", evidence: [{ image_url: "https://example.com/evidence.jpg", comment: "Original evidence comment" }] },
        { id: "worker-case", complaint_id: "report", subject_name: "Original worker name", kind: "worker_dispute", evidence: [{ image_url: "https://example.com/evidence.jpg", comment: "" }] },
      ]
      : path.endsWith("/map/roads") && mapFixtures ? [
        { id: "bad-road", name: "Dhanmondi Road 12", condition: "bad", open_complaints: 2, historical_reports_90d: 4, sensitivity: "high", latitude: 23.75, longitude: 90.37, ...(lineFixtures ? { path: [[23.75, 90.37], [23.76, 90.38]], paths: [[[23.75, 90.37], [23.755, 90.375]], [[23.757, 90.377], [23.76, 90.38]]], segment_from: "South junction", segment_to: "North junction" } : {}) },
        { id: "good-road", name: "Mirpur 10", condition: "good", open_complaints: 0, historical_reports_90d: 1, sensitivity: "normal", latitude: 23.81, longitude: 90.36 },
      ]
      : path.endsWith("/complaints") && mapFixtures ? [
        { id: "bad-report", title: "Drain overflowing", description: "Drain overflowing this morning", address: "Dhanmondi Road 12", kind: "complaint", condition: "bad", status: "assigned", category_code: "blocked_drain", latitude: 23.75, longitude: 90.37 },
        { id: "good-report", title: "Road is clear", description: "No standing water here today", address: "Mirpur 10", kind: "road_update", condition: "good", status: "open", category_code: "road_flooding", latitude: 23.81, longitude: 90.36 },
        { id: "false-report", title: "False report", description: "This report has been disproven", address: "Dhanmondi", kind: "complaint", condition: "bad", status: "false", category_code: "blocked_drain", latitude: 23.75, longitude: 90.37 },
      ]
      : path.endsWith("/areas") && userRole === "admin" ? [{ id: "area", name: "Original area name" }]
      : path.endsWith("/map/roads") && userRole === "admin" ? [{ id: "road", name: "Original road name", condition: "bad", open_complaints: 3, latitude: 23.77, longitude: 90.39 }]
      : path.endsWith("/categories") ? [{ code: "blocked_drain", label: "Blocked drain", base_priority: 75 }]
      : path.endsWith("/me/points") ? { balance: 2, total: 1, entries: [{ id: "entry", delta: 1, reason: "complaint" }] }
      : path.endsWith("/workers/application") ? application
      : path.endsWith("/complaints") && (url.searchParams.has("q") || path.endsWith("/me/complaints")) ? [{
        id: "report", title: "My original report title", description: "My original report description",
        address: "My written street address", author_name: "Resident Alpha", category_code: "blocked_drain",
        kind: "complaint", status: "assigned", created_at: 1792058400, likes: 2, dislikes: 1,
      }] : [];
    return new Response(JSON.stringify(path.endsWith("/me/complaints") && url.searchParams.has("include_total") ? { items: body, total: 1 } : body), { status: 200, headers: { "Content-Type": "application/json" } });
  };
  ({ createRoot } = await import("react-dom/client"));
  ({ Providers } = await import("../src/components/Providers"));
  ({ default: Navbar } = await import("../src/components/Navbar"));
  ({ default: CityMap } = await import("../src/components/CityMap"));
  ({ default: AdminDashboard } = await import("../src/components/AdminDashboard"));
  ({ default: LandingHero } = await import("../src/components/LandingHero"));
  ({ default: AuthForm } = await import("../src/components/AuthForm"));
  workspace = await import("../src/components/ComplaintWorkspace");
});

afterEach(async () => {
  await act(async () => { root?.unmount(); });
  root = undefined;
  application = null;
  submittedReport = null;
  predictionQuery = "";
  destination = "";
  userRole = "citizen";
  adminMutation = null;
  adminError = "";
  emptyAdmin = false;
  reducedMotion = false;
  signedIn = true;
  mapFixtures = false;
  lineFixtures = false;
  authMutation = null;
  Reflect.deleteProperty(navigator, "geolocation");
  document.documentElement.lang = "en";
  document.documentElement.dataset.theme = "light";
  localStorage.clear();
});
after(() => { globalThis.fetch = originalFetch; dom.window.close(); });

async function mount(Page: ComponentType) {
  try {
  await act(async () => {
    root = createRoot(document.getElementById("root")!);
    root.render(<AppRouterContext.Provider value={router}><Providers><Navbar /><Page /></Providers></AppRouterContext.Provider>);
    await new Promise(resolve => setTimeout(resolve, 50));
  });
  await act(async () => { await new Promise(resolve => setTimeout(resolve, 50)); });
  if (Page === CityMap) {
    // Leaflet is loaded asynchronously; wait for the control instead of assuming a cold import finishes in 50ms.
    for (let attempt = 0; attempt < 100 && !document.querySelector(".leaflet-control-zoom-in"); attempt++) {
      await act(async () => { await new Promise(resolve => setTimeout(resolve, 30)); });
    }
  }
  } catch (error) {
    if (error instanceof AggregateError) throw new Error(error.errors.map(cause => String(cause)).join("\n"));
    throw error;
  }
}
async function toggle() {
  const button = document.querySelector<HTMLButtonElement>(".language-toggle");
  assert.ok(button);
  await act(async () => { button.click(); });
}
function content() { return document.getElementById("main")!.textContent!; }
function capturedAuthRequest() { return authMutation; }

test("map controls switch EN -> Bangla -> EN through the navbar", async () => {
  await mount(CityMap);
  assert.ok(content().includes("Know your road. Help your city."));
  await toggle();
  assert.equal(document.documentElement.lang, "bn");
  assert.ok(content().includes("আপনার পথের খবর রাখুন। শহরের পাশে থাকুন।"));
  assert.ok(content().includes("সব রাস্তা"));
  assert.ok(content().includes("রাস্তার অবস্থা"));
  assert.ok(!content().includes("Latest community reports"));
  assert.equal(document.querySelector(".leaflet-control-zoom-in")?.getAttribute("title"), "বড় করে দেখুন");
  assert.ok(document.querySelector(".leaflet-control-attribution")?.textContent?.includes("অবদানকারী"));
  await toggle();
  assert.ok(content().includes("Latest community reports"));
});

test("complaint search categories and status options follow the toggle while keeping API values", async () => {
  await mount(workspace.ReportList);
  await toggle();
  assert.ok(content().includes("আপনার এলাকার কথা পৌঁছে যাক।"));
  assert.ok(document.querySelector('option[value="blocked_drain"]')?.textContent?.includes("নর্দমায় বাধা"));
  assert.ok(document.querySelector('option[value="awaiting_confirmation"]')?.textContent?.includes("যাচাইয়ের অপেক্ষায়"));
  assert.ok(document.querySelector('input[aria-label="অভিযোগ খুঁজুন"]'));
  assert.ok(content().includes("পৃষ্ঠা ১"));
  assert.ok(content().includes("দায়িত্ব দেওয়া হয়েছে"));
  assert.ok(content().includes("My original report title"));
  assert.ok(content().includes("My original report description"));
});

test("new report fields, file picker and required-field feedback translate without losing a draft", async () => {
  await mount(workspace.NewReport);
  const input = document.querySelector<HTMLInputElement>('input[name="title"]')!;
  assert.ok(input);
  input.value = "My own report text";
  await toggle();
  assert.equal(input.value, "My own report text");
  assert.ok(content().includes("ছোট একটি তথ্য। প্রয়োজনীয় পরিবর্তন।"));
  assert.ok(content().includes("কোনো ছবি বাছাই করা হয়নি"));
  const description = document.querySelector<HTMLTextAreaElement>('textarea[name="description"]')!;
  await act(async () => { description.checkValidity(); });
  assert.equal(description.validationMessage, "এই ঘরটি পূরণ করুন।");
  await toggle();
  assert.equal(input.value, "My own report text");
  await act(async () => { description.checkValidity(); });
  assert.equal(description.validationMessage, "Please fill out this field.");
});

function coordinate(name: string) { return document.querySelector<HTMLInputElement>(`input[name="${name}"]`)!; }
async function clickReportMap(x = 400, y = 172.5) {
  const canvas = document.querySelector<HTMLElement>(".report-map-canvas")!;
  assert.ok(canvas.classList.contains("leaflet-container"));
  await act(async () => { canvas.dispatchEvent(new dom.window.MouseEvent("click", { bubbles: true, clientX: x, clientY: y })); });
  await act(async () => { await new Promise(resolve => setTimeout(resolve, 20)); });
}
async function changeCoordinate(name: string, value: string) {
  const input = coordinate(name);
  await act(async () => {
    Object.getOwnPropertyDescriptor(dom.window.HTMLInputElement.prototype, "value")!.set!.call(input, value);
    input.dispatchEvent(new dom.window.Event("input", { bubbles: true }));
  });
}

test("map clicks, pin dragging, manual coordinates and language switching keep the selected place", async () => {
  await mount(workspace.NewReport);
  assert.equal(coordinate("latitude").value, "");
  assert.equal(document.querySelector(".report-map-marker"), null);
  await clickReportMap();
  assert.ok(Math.abs(Number(coordinate("latitude").value) - 23.77) < .001);
  assert.ok(Math.abs(Number(coordinate("longitude").value) - 90.39) < .001);
  const marker = document.querySelector<HTMLElement>(".report-map-marker")!;
  const canvas = document.querySelector<HTMLElement>(".report-map-canvas")!;
  assert.ok(marker);
  const beforeDrag = coordinate("longitude").value;
  await act(async () => {
    const down = new dom.window.MouseEvent("mousedown", { bubbles: true, button: 0, buttons: 1, clientX: 400, clientY: 170, view: dom.window as unknown as Window });
    // Leaflet 1.x checks the legacy `which` property, which JSDOM leaves at 0.
    Object.defineProperty(down, "which", { value: 1 });
    marker.dispatchEvent(down);
    canvas.dispatchEvent(new dom.window.MouseEvent("mousemove", { bubbles: true, buttons: 1, clientX: 420, clientY: 170 }));
    canvas.dispatchEvent(new dom.window.MouseEvent("mousemove", { bubbles: true, buttons: 1, clientX: 450, clientY: 170 }));
    await new Promise(resolve => setTimeout(resolve, 30));
    canvas.dispatchEvent(new dom.window.MouseEvent("mouseup", { bubbles: true, button: 0, clientX: 450, clientY: 170 }));
  });
  assert.notEqual(coordinate("longitude").value, beforeDrag);
  await changeCoordinate("latitude", "23.750123");
  await changeCoordinate("longitude", "90.370456");
  await toggle();
  assert.equal(coordinate("latitude").value, "23.750123");
  assert.equal(coordinate("longitude").value, "90.370456");
  assert.ok(content().includes("সঠিক জায়গা চিহ্নিত করুন"));
  assert.ok(content().includes("জায়গা বাছাই করা হয়েছে"));
  assert.equal(document.querySelector(".report-map-marker")?.getAttribute("aria-label"), "অভিযোগের নির্বাচিত স্থান। টেনে অবস্থান ঠিক করুন।");
  assert.equal(document.querySelector(".report-map-canvas .leaflet-control-zoom-in")?.getAttribute("title"), "বড় করে দেখুন");
});

test("publishing requires an explicit valid location and sends the chosen pin with report details", async () => {
  await mount(workspace.NewReport);
  const form = document.querySelector<HTMLFormElement>(".report-composer")!;
  coordinate("title").value = "Water overflowing near the school";
  coordinate("address").value = "Dhanmondi Road 12";
  document.querySelector<HTMLTextAreaElement>('textarea[name="description"]')!.value = "The drain has been overflowing since this morning.";
  document.querySelector<HTMLSelectElement>('select[name="category_code"]')!.value = "blocked_drain";
  await act(async () => { form.dispatchEvent(new dom.window.Event("submit", { bubbles: true, cancelable: true })); });
  assert.equal(submittedReport, null);
  assert.ok(content().includes("Choose a location on the map or enter valid Dhaka coordinates."));
  assert.equal(document.activeElement, document.querySelector(".report-location"));
  await clickReportMap(470, 200);
  const latitude = Number(coordinate("latitude").value);
  const longitude = Number(coordinate("longitude").value);
  await act(async () => {
    form.dispatchEvent(new dom.window.Event("submit", { bubbles: true, cancelable: true }));
    await new Promise(resolve => setTimeout(resolve, 30));
  });
  assert.deepEqual(submittedReport, {
    kind: "complaint", title: "Water overflowing near the school", description: "The drain has been overflowing since this morning.",
    address: "Dhanmondi Road 12", category_code: "blocked_drain", road_id: null,
    latitude, longitude, condition: "bad", images: [],
  });
  assert.equal(destination, "/complaints/created-report");
});

test("the full composer preserves a separate-incident choice and evidence through a language switch", async t => {
  const fallback = globalThis.fetch;
  t.mock.method(globalThis, "fetch", async (url: RequestInfo | URL, options?: RequestInit) => {
    if (String(url).includes("/complaints/similar")) return new Response(JSON.stringify([
      { id: "first-nearby", title: "First nearby blockage", incident_reporter_count: 2 },
      { id: "second-nearby", title: "Different nearby blockage", incident_reporter_count: 3 },
    ]));
    return fallback(url, options);
  });
  await mount(workspace.NewReport);
  coordinate("title").value = "A genuinely separate blockage";
  coordinate("address").value = "A different drain near the junction";
  document.querySelector<HTMLTextAreaElement>('textarea[name="description"]')!.value = "This separate problem needs its own work assignment.";
  const category = document.querySelector<HTMLSelectElement>('select[name="category_code"]')!;
  await act(async () => { category.value = "blocked_drain"; category.dispatchEvent(new dom.window.Event("change", { bubbles: true })); });
  await clickReportMap();
  const choices = document.querySelector<HTMLSelectElement>('select[name="incident_id"]')!;
  assert.equal(choices.required, true);
  const separate = document.querySelector<HTMLInputElement>('input[name="separate_incident"]')!;
  await act(async () => { separate.click(); });
  await toggle();
  assert.equal(separate.checked, true);
  assert.equal(category.value, "blocked_drain");
  assert.equal(coordinate("title").value, "A genuinely separate blockage");
  assert.ok(content().includes("আলাদা ঘটনা হিসেবে রাখুন"));
  await act(async () => { document.querySelector(".report-composer")!.dispatchEvent(new dom.window.Event("submit", { bubbles: true, cancelable: true })); });
  assert.equal((submittedReport as Record<string, unknown> | null)?.separate_incident, true);
  assert.equal((submittedReport as Record<string, unknown> | null)?.incident_id, undefined);
});

test("a delayed GPS result preserves a later map selection and coordinates outside Dhaka are rejected", async () => {
  let gpsSuccess: PositionCallback | undefined;
  Object.defineProperty(navigator, "geolocation", { configurable: true, value: { getCurrentPosition(success: PositionCallback) { gpsSuccess = success; } } });
  await mount(workspace.NewReport);
  await act(async () => { document.querySelector<HTMLButtonElement>(".report-locate")!.click(); });
  await clickReportMap();
  const selected = coordinate("latitude").value;
  await act(async () => { gpsSuccess!({ coords: { latitude: 23.8, longitude: 90.4 } } as GeolocationPosition); });
  assert.equal(coordinate("latitude").value, selected);
  await changeCoordinate("latitude", "22.5");
  await act(async () => { document.querySelector<HTMLFormElement>(".report-composer")!.dispatchEvent(new dom.window.Event("submit", { bubbles: true, cancelable: true })); });
  assert.equal(submittedReport, null);
  assert.equal(document.querySelector(".report-map-marker"), null);
  assert.ok(content().includes("Choose a location on the map or enter valid Dhaka coordinates."));
});

test("worker application form translates its labels and approval guidance", async () => {
  await mount(workspace.WorkerApply);
  await toggle();
  assert.ok(content().includes("সুন্দর এলাকার জন্য কাজ করুন।"));
  assert.ok(content().includes("এনআইডি নম্বর"));
  assert.ok(content().includes("অনুমোদনের জন্য জমা দিন"));
  assert.ok(!content().includes("Submit for approval"));
});

test("pending application status translates while preserving the mayor's written note", async () => {
  application = { status: "pending", review_note: "An independently written review note" };
  await mount(workspace.WorkerApply);
  await toggle();
  assert.ok(content().includes("আবেদনের অবস্থা: অপেক্ষমাণ"));
  assert.ok(content().includes("An independently written review note"));
});

test("community headings, point counts and ledger reasons follow the toggle", async () => {
  await mount(workspace.CommunityPage);
  await toggle();
  assert.ok(content().includes("ঢাকার জন্য আপনার অবদান।"));
  assert.ok(content().includes("অবদানের পয়েন্ট"));
  assert.ok(content().includes("২"));
  assert.ok(content().includes("অভিযোগ"));
  await toggle();
  assert.ok(content().includes("Community points"));
});

async function adminTab(text: string) {
  const button = [...document.querySelectorAll<HTMLButtonElement>(".admin-tabs button")].find(button => button.textContent === text);
  assert.ok(button, `Missing admin tab: ${text}`);
  await act(async () => { button.click(); });
  await act(async () => { await new Promise(resolve => setTimeout(resolve, 10)); });
}
async function submitForm(form: HTMLFormElement) {
  await act(async () => {
    form.dispatchEvent(new dom.window.Event("submit", { bubbles: true, cancelable: true }));
    await new Promise(resolve => setTimeout(resolve, 10));
  });
}

test("admin overview translates all tabs, chart labels, counts and accessible meter labels", async () => {
  userRole = "admin";
  await mount(AdminDashboard);
  assert.ok(content().includes("A clearer picture. Better decisions."));
  await toggle();
  assert.ok(content().includes("পরিষ্কার চিত্র। সঠিক সিদ্ধান্ত।"));
  assert.deepEqual([...document.querySelectorAll(".admin-tabs button")].map(button => button.textContent), ["সারসংক্ষেপ", "অভিযোগ ও তথ্য", "ব্যবহারকারী", "সেবাকর্মী", "আবেদন", "অভিযোগ পর্যালোচনা", "রাস্তা"]);
  assert.deepEqual([...document.querySelectorAll(".civic-stats strong")].map(element => element.textContent), ["৩", "১", "১০", "২"]);
  assert.ok(content().includes("অবস্থা অনুযায়ী অভিযোগ"));
  assert.ok(content().includes("ধরন অনুযায়ী অভিযোগ"));
  assert.ok(content().includes("১২ পয়েন্ট"));
  assert.ok(content().includes("Original area name"));
  assert.ok(content().includes("Original leader name"));
  const meter = document.querySelector<HTMLMeterElement>('meter[aria-label="নর্দমায় বাধা: ৩"]')!;
  assert.ok(meter);
  assert.equal(meter.value, 3);
  await toggle();
  assert.equal(document.querySelector(".civic-stats strong")?.textContent, "3");
  assert.ok(content().includes("Community point leaders"));
});

test("admin report, user and worker searches translate without changing written content or roles", async () => {
  userRole = "admin";
  await mount(AdminDashboard);
  await toggle();
  await adminTab("অভিযোগ ও তথ্য");
  assert.ok(document.querySelector('input[aria-label="সব অভিযোগ ও তথ্য খুঁজুন"]'));
  assert.ok(content().includes("My original report title"));
  assert.ok(content().includes("পৃষ্ঠা ১"));
  await adminTab("ব্যবহারকারী");
  assert.ok(document.querySelector('input[aria-label="অ্যাকাউন্ট খুঁজুন"]'));
  assert.ok(content().includes("নাগরিক"));
  assert.ok(content().includes("সক্রিয়"));
  assert.ok(content().includes("১২ পয়েন্ট"));
  assert.ok(content().includes("অ্যাকাউন্ট ব্লক করুন ও সব সেশন বাতিল করুন"));
  const reason = coordinate("reason");
  reason.value = "My independently written reason";
  await toggle();
  assert.equal(reason.value, "My independently written reason");
  assert.ok(content().includes("Original account name"));
  assert.ok(content().includes("account@example.com"));
  await adminTab("Workers");
  await toggle();
  assert.ok(document.querySelector(".civic-card-meta")?.textContent?.includes("সেবাকর্মী"));
});

test("worker approval forms translate, preserve drafts and send the original decision values", async () => {
  userRole = "admin";
  await mount(AdminDashboard);
  await adminTab("Applications");
  const note = document.querySelector<HTMLTextAreaElement>('textarea[name="note"]')!;
  const decision = document.querySelector<HTMLSelectElement>('select[name="decision"]')!;
  note.value = "My independently written review";
  decision.value = "reject";
  await toggle();
  assert.equal(note.value, "My independently written review");
  assert.equal(decision.value, "reject");
  assert.equal(decision.selectedOptions[0].textContent, "আবেদন প্রত্যাখ্যান করুন");
  assert.ok(content().includes("ব্যক্তিগত পরিচয়পত্র দেখুন"));
  assert.ok(content().includes("সিদ্ধান্ত সংরক্ষণ করুন"));
  assert.ok(content().includes("Original applicant name"));
  await submitForm(note.form!);
  assert.deepEqual(adminMutation, { path: "/api/v1/admin/worker-applications/applicant/review", method: "POST", body: { approve: false, note: "My independently written review" } });
});

test("moderation translates case types, evidence actions and server errors while preserving evidence", async () => {
  userRole = "admin";
  adminError = "Case has already been reviewed";
  await mount(AdminDashboard);
  await toggle();
  await adminTab("অভিযোগ পর্যালোচনা");
  assert.ok(content().includes("মিথ্যা অভিযোগ"));
  assert.ok(content().includes("সেবাকর্মীর কাজে আপত্তি"));
  assert.ok(content().includes("মূল অভিযোগ খুলুন"));
  assert.ok(content().includes("ছবি দেখুন"));
  assert.ok(content().includes("ছবির প্রমাণ"));
  assert.ok(content().includes("Original evidence comment"));
  const form = document.querySelector<HTMLFormElement>(".civic-card .civic-form")!;
  form.querySelector<HTMLTextAreaElement>('textarea[name="note"]')!.value = "My written moderation note";
  form.querySelector<HTMLSelectElement>('select[name="status"]')!.value = "dismissed";
  await submitForm(form);
  assert.deepEqual(adminMutation?.body, { status: "dismissed", note: "My written moderation note" });
  assert.ok(document.querySelector('[role="alert"]')?.textContent?.includes("অভিযোগটি আগেই পর্যালোচনা করা হয়েছে"));
  await toggle();
  assert.ok(document.querySelector('[role="alert"]')?.textContent?.includes("Case has already been reviewed"));
});

test("road catalog translates forms and validation without changing names, IDs or coordinates", async () => {
  userRole = "admin";
  await mount(AdminDashboard);
  await toggle();
  await adminTab("রাস্তা");
  assert.ok(content().includes("নতুন এলাকা যোগ করুন"));
  assert.ok(content().includes("রাস্তার তালিকা"));
  assert.ok(content().includes("খারাপ · ৩ অমীমাংসিত"));
  assert.ok(content().includes("Original road name"));
  const form = [...document.querySelectorAll<HTMLFormElement>(".civic-card.civic-form")][1];
  const name = form.querySelector<HTMLInputElement>('input[name="name"]')!;
  await act(async () => { name.checkValidity(); });
  assert.equal(name.validationMessage, "এই ঘরটি পূরণ করুন।");
  await act(async () => {
    name.value = "Independently named road";
    name.dispatchEvent(new dom.window.Event("input", { bubbles: true }));
  });
  form.querySelector<HTMLSelectElement>('select[name="area_id"]')!.value = "area";
  form.querySelector<HTMLInputElement>('input[name="latitude"]')!.value = "23.770123";
  form.querySelector<HTMLInputElement>('input[name="longitude"]')!.value = "90.390456";
  await toggle();
  assert.equal(name.value, "Independently named road");
  await submitForm(form);
  assert.deepEqual(adminMutation?.body, { name: "Independently named road", area_id: "area", latitude: 23.770123, longitude: 90.390456 });
});

test("empty admin analytics and search results follow the Bangla toggle", async () => {
  userRole = "admin";
  emptyAdmin = true;
  await mount(AdminDashboard);
  await toggle();
  assert.ok(content().includes("এখনো কোনো তথ্য জমা পড়েনি।"));
  assert.ok(content().includes("অবদান এখানে দেখা যাবে।"));
  await adminTab("ব্যবহারকারী");
  assert.ok(content().includes("এই অনুসন্ধানে এখনো কোনো তথ্য পাওয়া যায়নি।"));
});

function activeBanner() {
  return [...document.querySelectorAll<HTMLButtonElement>(".hero-slide-selector")].findIndex(button => button.getAttribute("aria-pressed") === "true");
}

test("landing hero uses all three supplied images and loops every two seconds", async context => {
  context.mock.timers.enable({ apis: ["setInterval"] });
  await mount(LandingHero);
  const images = [...document.querySelectorAll<HTMLImageElement>(".hero-banner-image")];
  assert.equal(images.length, 3);
  for (let index = 0; index < 3; index++) assert.ok(images[index].src.includes(encodeURIComponent(`/dubsibhai-banner${index + 1}.png`)));
  assert.equal(activeBanner(), 0);
  await act(async () => { context.mock.timers.tick(1999); });
  assert.equal(activeBanner(), 0);
  await act(async () => { context.mock.timers.tick(1); });
  assert.equal(activeBanner(), 1);
  for (const expected of [2, 0, 1, 2, 0]) {
    await act(async () => { context.mock.timers.tick(2000); });
    assert.equal(activeBanner(), expected);
    assert.equal(document.querySelectorAll(".hero-slide.is-active").length, 1);
  }
  assert.equal(document.querySelector<HTMLAnchorElement>(".hero-primary-action")?.getAttribute("href"), "/complaints/new");
  assert.equal(document.querySelector<HTMLAnchorElement>(".hero-map-action")?.getAttribute("href"), "/map");
});

test("hero playback controls pause and resume, with Bangla text preserving the current banner", async context => {
  context.mock.timers.enable({ apis: ["setInterval"] });
  await mount(LandingHero);
  const playback = document.querySelector<HTMLButtonElement>(".hero-playback")!;
  await act(async () => { playback.click(); });
  await act(async () => { context.mock.timers.tick(6000); });
  assert.equal(activeBanner(), 0);
  await act(async () => { document.querySelectorAll<HTMLButtonElement>(".hero-slide-selector")[2].click(); });
  await toggle();
  assert.equal(activeBanner(), 2);
  assert.ok(document.querySelector(".landing-hero")?.textContent?.includes("সুন্দর ঢাকা।"));
  assert.ok(document.querySelector(".hero-photo-caption")?.textContent?.includes("০৩ / ০৩"));
  assert.equal(playback.getAttribute("aria-label"), "ব্যানার পরিবর্তন চালু করুন");
  await act(async () => { playback.click(); });
  await act(async () => { context.mock.timers.tick(2000); });
  assert.equal(activeBanner(), 0);
  assert.equal(playback.getAttribute("aria-label"), "ব্যানার পরিবর্তন থামান");
});

test("reduced motion keeps the background still while allowing manual banner selection", async context => {
  reducedMotion = true;
  context.mock.timers.enable({ apis: ["setInterval"] });
  await mount(LandingHero);
  await act(async () => { context.mock.timers.tick(10000); });
  assert.equal(activeBanner(), 0);
  await act(async () => { document.querySelectorAll<HTMLButtonElement>(".hero-slide-selector")[1].click(); });
  assert.equal(activeBanner(), 1);
  await act(async () => { context.mock.timers.tick(4000); });
  assert.equal(activeBanner(), 1);
});

test("navbar menu, language and theme controls remain functional with keyboard dismissal", async () => {
  await mount(workspace.CommunityPage);
  const menu = document.querySelector<HTMLButtonElement>(".menu-toggle")!;
  const navigation = document.getElementById("mobile-nav")!;
  assert.equal(navigation.hidden, true);
  await act(async () => { menu.click(); });
  assert.equal(menu.getAttribute("aria-expanded"), "true");
  assert.equal(navigation.hidden, false);
  await toggle();
  assert.ok(navigation.textContent?.includes("ঢাকার মানচিত্র"));
  await act(async () => { document.dispatchEvent(new dom.window.KeyboardEvent("keydown", { key: "Escape", bubbles: true })); });
  assert.equal(menu.getAttribute("aria-expanded"), "false");
  assert.equal(navigation.hidden, true);
  assert.equal(document.activeElement, menu);
  await act(async () => { document.querySelector<HTMLButtonElement>(".theme-toggle")!.click(); });
  assert.equal(document.documentElement.dataset.theme, "dark");
});

test("map filters and search cover roads and reports, preserving markers and selection across languages", async () => {
  mapFixtures = true;
  await mount(CityMap);
  assert.deepEqual([...document.querySelectorAll(".city-map-stats strong")].map(element => element.textContent), ["2", "1", "1", "2"]);
  assert.equal(document.querySelectorAll(".city-map-report").length, 2);
  assert.ok(!content().includes("False report"));
  const markers = [...document.querySelectorAll("path.leaflet-interactive")];
  assert.equal(markers.length, 4);
  const mapContainer = document.querySelector(".live-road-map");
  await toggle();
  assert.equal(document.querySelector(".live-road-map"), mapContainer);
  assert.deepEqual([...document.querySelectorAll("path.leaflet-interactive")], markers);
  assert.ok(document.querySelector('input[aria-label="মানচিত্রে খুঁজুন"]'));
  assert.deepEqual([...document.querySelectorAll(".city-map-stats strong")].map(element => element.textContent), ["২", "১", "১", "২"]);
  await act(async () => { document.querySelectorAll<HTMLButtonElement>(".city-map-filters button")[1].click(); });
  assert.equal(document.querySelectorAll(".city-map-report").length, 1);
  assert.ok(content().includes("Drain overflowing"));
  await toggle();
  assert.equal(document.querySelectorAll(".city-map-filters button")[1].getAttribute("aria-pressed"), "true");
  const search = document.querySelector<HTMLInputElement>(".city-map-search input")!;
  await act(async () => {
    Object.getOwnPropertyDescriptor(dom.window.HTMLInputElement.prototype, "value")!.set!.call(search, "Mirpur");
    search.dispatchEvent(new dom.window.Event("input", { bubbles: true }));
  });
  assert.equal(document.querySelectorAll(".city-map-report").length, 0);
  await toggle();
  assert.equal(search.value, "Mirpur");
  assert.ok(content().includes("অন্য কিছু খুঁজুন অথবা সব অবস্থা দেখুন।"));
  await act(async () => { document.querySelector<HTMLButtonElement>(".city-map-empty button")!.click(); });
  assert.equal(search.value, "");
  assert.equal(document.querySelectorAll(".city-map-report").length, 2);
  await act(async () => { document.querySelectorAll<HTMLButtonElement>(".city-map-panel-tabs button")[1].click(); });
  assert.equal(document.querySelectorAll(".city-map-road").length, 2);
  assert.ok(content().includes("Dhanmondi Road 12"));
  await act(async () => { document.querySelector<HTMLButtonElement>(".city-map-road")!.click(); });
  assert.equal(document.querySelector(".city-map-road")?.getAttribute("aria-pressed"), "true");
  assert.equal(document.querySelectorAll(".city-map-panel-tabs button")[1].getAttribute("aria-pressed"), "true");
});

test("selecting a map road preserves the draft across languages and submits its road ID", async () => {
  mapFixtures = true;
  await mount(CityMap);
  await act(async () => { document.querySelector<SVGElement>("path.leaflet-interactive")!.dispatchEvent(new dom.window.MouseEvent("click", { bubbles: true })); });
  const editor = document.querySelector(".road-selection");
  assert.ok(editor);
  assert.ok(editor.textContent!.includes("Dhanmondi Road 12"));
  await act(async () => { document.querySelectorAll<HTMLButtonElement>(".road-condition-options button")[1].click(); });
  const description = editor.querySelector<HTMLTextAreaElement>("textarea")!;
  await act(async () => {
    Object.getOwnPropertyDescriptor(dom.window.HTMLTextAreaElement.prototype, "value")!.set!.call(description, "This road is passable near the bus stop.");
    description.dispatchEvent(new dom.window.Event("input", { bubbles: true }));
  });
  await toggle();
  assert.equal(description.value, "This road is passable near the bus stop.");
  assert.ok(editor.textContent!.includes("রাস্তার তথ্য দিন"));
  await act(async () => { editor.querySelector("form")!.dispatchEvent(new dom.window.Event("submit", { bubbles: true, cancelable: true })); });
  assert.equal(submittedReport?.road_id, "bad-road");
  assert.equal(submittedReport?.kind, "road_update");
  assert.equal(submittedReport?.condition, "good");
  assert.ok(editor.querySelector('a[href="/complaints/created-report"]'));
});

test("separate road sections have no connecting line and both select the same report corridor", async () => {
  mapFixtures = true;
  lineFixtures = true;
  await mount(CityMap);
  const target = [...document.querySelectorAll<SVGElement>("path.leaflet-interactive")].find(path => path.getAttribute("stroke-width") === "22");
  assert.ok(target);
  assert.equal(target.getAttribute("d")?.match(/M/g)?.length, 2, "each disconnected section starts its own SVG subpath");
  await act(async () => { target.dispatchEvent(new dom.window.MouseEvent("click", { bubbles: true })); });
  const editor = document.querySelector(".road-selection")!;
  assert.ok(editor.textContent!.includes("South junction → North junction"));
  await act(async () => { editor.querySelectorAll<HTMLButtonElement>(".road-form-tabs button")[1].click(); });
  assert.ok(editor.querySelector('button[type="submit"]')!.textContent!.includes("Submit complaint"));
  assert.equal(editor.querySelector(".road-condition-options"), null);
});

test("predictions use Dhaka time, switch hazard probabilities, and hide stale scenario colors", async () => {
  mapFixtures = true;
  await mount(CityMap);
  await act(async () => { document.querySelectorAll<HTMLButtonElement>(".road-mode-tabs button")[2].click(); });
  assert.ok(content().includes("SYNTHETIC MODEL · DEMO"));
  assert.ok([...document.querySelectorAll(".road-risk-value")].every(element => element.textContent === "—"));
  await act(async () => { document.querySelector(".road-prediction-panel form")!.dispatchEvent(new dom.window.Event("submit", { bubbles: true, cancelable: true })); });
  const parameters = new URLSearchParams(predictionQuery);
  assert.ok(parameters.get("at")?.endsWith("+06:00"));
  assert.equal(parameters.get("forecast_horizon_min"), "60");
  assert.deepEqual([...document.querySelectorAll(".road-risk-value")].map(element => element.textContent), ["80%", "10%"]);
  await act(async () => { document.querySelectorAll<HTMLButtonElement>(".road-prediction-panel .road-form-tabs button")[1].click(); });
  assert.deepEqual([...document.querySelectorAll(".road-risk-value")].map(element => element.textContent), ["20%", "70%"]);
  const rain = document.querySelector<HTMLInputElement>('.road-prediction-panel input[type="number"]')!;
  await act(async () => {
    Object.getOwnPropertyDescriptor(dom.window.HTMLInputElement.prototype, "value")!.set!.call(rain, "35");
    rain.dispatchEvent(new dom.window.Event("input", { bubbles: true }));
  });
  assert.ok(content().includes("Inputs changed. Run the prediction again"));
  assert.ok([...document.querySelectorAll(".road-risk-value")].every(element => element.textContent === "—"));
  const horizon = document.querySelector<HTMLSelectElement>(".road-prediction-panel select")!;
  await act(async () => {
    horizon.value = "120";
    horizon.dispatchEvent(new dom.window.Event("change", { bubbles: true }));
  });
  await act(async () => { document.querySelector(".road-prediction-panel form")!.dispatchEvent(new dom.window.Event("submit", { bubbles: true, cancelable: true })); });
  assert.equal(new URLSearchParams(predictionQuery).get("forecast_horizon_min"), "120");
});

test("redesigned login translates labels and validation, preserves input and signs in successfully", async () => {
  signedIn = false;
  await mount(() => <AuthForm mode="login" />);
  const email = coordinate("email");
  const password = coordinate("password");
  email.value = "resident@example.com";
  password.value = "pass1234";
  await toggle();
  assert.ok(content().includes("ইমেইল অথবা ফোন"));
  assert.equal(email.value, "resident@example.com");
  assert.equal(password.value, "pass1234");
  await act(async () => { document.querySelector<HTMLButtonElement>(".password-field button")!.click(); });
  assert.equal(password.type, "text");
  await submitForm(password.form!);
  assert.deepEqual(authMutation, { path: "/api/v1/auth/login", body: { identifier: "resident@example.com", password: "pass1234" } });
  assert.equal(destination, "/community");
});

test("citizen signup keeps its profile fields, eight-character minimum and translated feedback", async () => {
  signedIn = false;
  await mount(() => <AuthForm mode="register" />);
  assert.ok(content().includes("Create your account."));
  const email = coordinate("email");
  await toggle();
  await act(async () => { email.checkValidity(); });
  assert.equal(email.validationMessage, "এই ঘরটি পূরণ করুন।");
  coordinate("name").value = "Test Resident";
  email.value = "resident@example.com";
  coordinate("password").value = "pass1234";
  coordinate("confirm").value = "pass1235";
  assert.equal(coordinate("password").minLength, 8);
  await submitForm(email.form!);
  assert.equal(authMutation, null);
  assert.ok(content().includes("পাসওয়ার্ড দুটি মিলছে না।"));
  await toggle();
  assert.ok(content().includes("Passwords do not match."));
  assert.equal(email.value, "resident@example.com");
  coordinate("confirm").value = "pass1234";
  await submitForm(email.form!);
  assert.deepEqual(capturedAuthRequest()?.body, { account_type: "citizen", name: "Test Resident", email: "resident@example.com", password: "pass1234", phone: null, date_of_birth: null, blood_group: null });
  assert.ok(content().includes("Check your inbox."));
});

test("worker signup preserves the selected role and identity across language changes", async () => {
  signedIn = false;
  await mount(() => <AuthForm mode="register" />);
  await act(async () => { document.querySelector<HTMLInputElement>('input[name="account_type"][value="worker"]')!.click(); });
  coordinate("name").value = "Test Applicant";
  coordinate("email").value = "worker@example.com";
  coordinate("password").value = "pass1234";
  coordinate("confirm").value = "pass1234";
  const form = coordinate("email").form!;
  await submitForm(form);
  assert.equal(authMutation, null);
  await toggle();
  assert.ok(content().includes("আপনার এনআইডি নম্বর অথবা এনআইডি ছবির ব্যক্তিগত HTTPS লিংক দিন।"));
  coordinate("nid_number").value = "1234567890";
  await toggle();
  assert.equal(document.querySelector<HTMLInputElement>('input[value="worker"]')!.checked, true);
  assert.equal(coordinate("nid_number").value, "1234567890");
  await submitForm(form);
  assert.deepEqual(capturedAuthRequest()?.body.worker_identity, { nid_number: "1234567890", nid_image_url: null });
  assert.equal(capturedAuthRequest()?.body.account_type, "worker");
  assert.ok(content().includes("Worker signup includes an application for the mayor to review."));
});
