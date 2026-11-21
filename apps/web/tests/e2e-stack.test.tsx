// Isolation rules of the browser smoke stack (issue #10). No Docker is needed.
import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { test } from "node:test";
import { acquireRunLock, ownsRunLock, projectName, releaseRunLock } from "../e2e/stack";

test("different port pairs get different Compose projects, and so different volumes", () => {
  assert.equal(projectName(13000, 18000), "dubsibhai-e2e");
  assert.equal(projectName(13001, 18001), "dubsibhai-e2e-13001-18001");
  assert.notEqual(projectName(13001, 18001), projectName(13002, 18001));
  assert.equal(projectName(13001, 18001, "custom-e2e"), "custom-e2e");
});

test("a second run on the same project is rejected while the first is alive", () => {
  const dir = mkdtempSync(path.join(os.tmpdir(), "e2e-lock-"));
  // This test process plays the first run; another pid tries to start.
  const file = acquireRunLock("dubsibhai-e2e", dir, process.pid);
  // Teardown only acts for the owner; the rejected run must leave the first run's stack alone.
  assert.equal(ownsRunLock("dubsibhai-e2e", dir, process.pid), true);
  assert.equal(ownsRunLock("dubsibhai-e2e", dir, process.pid + 1), false);
  assert.throws(() => acquireRunLock("dubsibhai-e2e", dir, process.pid + 1), /Another browser smoke run \(process \d+\) is using project dubsibhai-e2e/);
  // Other projects (other ports) are independent.
  releaseRunLock("dubsibhai-e2e-13001-18001", dir, process.pid);
  acquireRunLock("dubsibhai-e2e-13001-18001", dir, process.pid + 1);
  // Only the owner releases its lock.
  releaseRunLock("dubsibhai-e2e", dir, process.pid + 1);
  assert.equal(JSON.parse(readFileSync(file, "utf-8")).pid, process.pid);
  releaseRunLock("dubsibhai-e2e", dir, process.pid);
  acquireRunLock("dubsibhai-e2e", dir, process.pid + 1);
});

test("a lock left by a finished or crashed run is reclaimed", () => {
  const dir = mkdtempSync(path.join(os.tmpdir(), "e2e-lock-"));
  const file = path.join(dir, "dubsibhai-e2e.e2e.lock");
  writeFileSync(file, JSON.stringify({ pid: 2_147_000_000, startedAt: "2026-01-01T00:00:00Z" }));
  acquireRunLock("dubsibhai-e2e", dir, process.pid);
  assert.equal(JSON.parse(readFileSync(file, "utf-8")).pid, process.pid);
  writeFileSync(file, "not json");
  releaseRunLock("dubsibhai-e2e", dir, process.pid);
  acquireRunLock("dubsibhai-e2e", dir, process.pid);
});
