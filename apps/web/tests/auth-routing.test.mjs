import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import ts from "typescript";

const source = await readFile(new URL("../src/lib/auth.ts", import.meta.url), "utf8");
const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 } }).outputText;
const { accountHome } = await import(`data:text/javascript;base64,${Buffer.from(compiled).toString("base64")}`);

test("citizens enter their contributions workspace", () => {
  assert.equal(accountHome({ role: "citizen", worker_application_status: null }), "/community");
});
test("pending or rejected worker applicants enter their application status page", () => {
  for (const status of ["pending", "rejected"]) assert.equal(accountHome({ role: "citizen", worker_application_status: status }), "/workers/apply");
});
test("approved workers and mayors enter their role workspace", () => {
  assert.equal(accountHome({ role: "worker", worker_application_status: "approved" }), "/worker");
  assert.equal(accountHome({ role: "admin" }), "/admin");
});
