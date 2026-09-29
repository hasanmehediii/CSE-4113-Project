import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import ts from "typescript";

const source = await readFile(new URL("../src/lib/api-client.ts", import.meta.url), "utf8");
const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 } }).outputText;
let run = 0;
const client = () => import(`data:text/javascript;base64,${Buffer.from(compiled).toString("base64")}#${++run}`);
const json = (body, status = 200) => new Response(JSON.stringify(body), { status });

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
