import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import ts from "typescript";

const source = await readFile(new URL("../src/lib/api-client.ts", import.meta.url), "utf8");
const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 } }).outputText;
let run = 0;
const client = () => import(`data:text/javascript;base64,${Buffer.from(compiled).toString("base64")}#${++run}`);
const json = (body, status = 200) => new Response(JSON.stringify(body), { status });

test("signup validation reports the invalid field so the user can correct it", async t => {
  t.mock.method(globalThis, "fetch", async () => json({ detail: [{ loc: ["body", "worker_identity", "nid_number"], msg: "Use a valid NID number" }] }, 422));
  const { api, ApiError } = await client();
  await assert.rejects(api("/auth/register"), error => error instanceof ApiError && error.status === 422 && error.detail.includes("nid_number") && error.detail.includes("valid NID"));
});

test("cookies accompany reads; login rotates the CSRF token before logout", async t => {
  const calls = [];
  let issued = 0;
  t.mock.method(globalThis, "fetch", async (url, options) => {
    calls.push([url, options]);
    return json(url.endsWith("/csrf") ? { csrf_token: `token-${++issued}` } : {});
  });
  const { api, mutate } = await client();
  await api("/auth/me");
  await mutate("/auth/login", { email: "resident@example.com", password: "test-passphrase" });
  await mutate("/auth/logout");
  assert.equal(issued, 2);
  assert.ok(calls.every(([, options]) => options.credentials === "include" && options.cache === "no-store"));
  assert.equal(calls[2][1].headers["X-CSRF-Token"], "token-1");
  assert.equal(calls[4][1].headers["X-CSRF-Token"], "token-2");
});

test("Google nonce and credential keep the same CSRF binding", async t => {
  let issued = 0;
  const tokens = [];
  t.mock.method(globalThis, "fetch", async (url, options) => {
    if (url.endsWith("/csrf")) return json({ csrf_token: `token-${++issued}` });
    tokens.push(options.headers["X-CSRF-Token"]);
    return json({ nonce: "nonce" });
  });
  const { mutate } = await client();
  await mutate("/auth/google/nonce");
  await mutate("/auth/google", { credential: "credential", nonce: "nonce" });
  assert.equal(issued, 1);
  assert.deepEqual(tokens, ["token-1", "token-1"]);
});

test("expired CSRF is retried once, but incorrect credentials are not retried", async t => {
  let issued = 0;
  let submissions = 0;
  t.mock.method(globalThis, "fetch", async url => {
    if (url.endsWith("/csrf")) return json({ csrf_token: `token-${++issued}` });
    submissions++;
    return submissions === 1 ? json({ detail: "Invalid CSRF token" }, 403) : json({ detail: "Invalid email or password" }, 401);
  });
  const { mutate, ApiError } = await client();
  await assert.rejects(mutate("/auth/login", {}), error => error instanceof ApiError && error.status === 401);
  assert.equal(issued, 2);
  assert.equal(submissions, 2);
});

test("concurrent mutations serialize and a failed request does not block the queue", async t => {
  let active = 0;
  let maximum = 0;
  let submissions = 0;
  t.mock.method(globalThis, "fetch", async url => {
    if (url.endsWith("/csrf")) return json({ csrf_token: "token" });
    active++; maximum = Math.max(maximum, active);
    await new Promise(resolve => setTimeout(resolve, 5));
    active--; submissions++;
    return submissions === 1 ? json({ detail: "Rate limited" }, 429) : json({ ok: true });
  });
  const { mutate } = await client();
  const results = await Promise.allSettled([mutate("/auth/resend-verification", {}), mutate("/auth/forgot-password", {})]);
  assert.equal(maximum, 1);
  assert.equal(results[0].status, "rejected");
  assert.equal(results[1].status, "fulfilled");
});

test("a timed out image upload releases the queue for subsequent saves", async t => {
  const controllers = new Map();
  let started;
  const uploadStarted = new Promise(resolve => { started = resolve; });
  t.mock.method(AbortSignal, "timeout", () => {
    const controller = new AbortController();
    controllers.set(controller.signal, controller);
    return controller.signal;
  });
  t.mock.method(globalThis, "fetch", async (url, options) => {
    if (url.endsWith("/csrf")) return json({ csrf_token: "token" });
    if (url.endsWith("/media")) return new Promise((resolve, reject) => {
      assert.ok(options.signal, "uploads must have a deadline");
      options.signal.addEventListener("abort", () => reject(options.signal.reason));
      started(controllers.get(options.signal));
    });
    return json({ saved: true });
  });
  const { uploadImage, mutate } = await client();
  const upload = uploadImage(new File(["photo"], "photo.png"));
  const failedUpload = assert.rejects(upload, /Upload timed out/);
  const save = mutate("/complaints", { title: "Another report" });
  (await uploadStarted).abort(new Error("Upload timed out"));
  await failedUpload;
  assert.deepEqual(await save, { saved: true });
});

test("image uploads retry only an expired CSRF token, not a permission denial", async t => {
  let uploads = 0;
  t.mock.method(globalThis, "fetch", async url => {
    if (url.endsWith("/csrf")) return json({ csrf_token: "token" });
    uploads++;
    return json({ detail: "Verify your email first" }, 403);
  });
  const { uploadImage, ApiError } = await client();
  await assert.rejects(uploadImage(new File(["photo"], "photo.png")), error => error instanceof ApiError && error.status === 403);
  assert.equal(uploads, 1);
});

test("an HTML upload gateway error has a useful message and does not poison the queue", async t => {
  t.mock.method(globalThis, "fetch", async url => url.endsWith("/csrf")
    ? json({ csrf_token: "token" }) : new Response("Bad gateway", { status: 502 }));
  const { uploadImage, ApiError } = await client();
  await assert.rejects(uploadImage(new File(["photo"], "photo.png")), error => error instanceof ApiError && error.detail === "Image upload failed");
});

test("caller cancellation and the API deadline both remain active", async t => {
  const deadline = new AbortController();
  const caller = new AbortController();
  let signal;
  t.mock.method(AbortSignal, "timeout", () => deadline.signal);
  t.mock.method(globalThis, "fetch", async (url, options) => { signal = options.signal; return json({}); });
  const { api } = await client();
  await api("/complaints", { signal: caller.signal });
  caller.abort();
  assert.equal(signal.aborted, true);
  await api("/complaints", { signal: new AbortController().signal });
  deadline.abort();
  assert.equal(signal.aborted, true);
});
