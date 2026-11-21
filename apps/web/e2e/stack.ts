// Shared settings for the isolated browser smoke stack. Only synthetic data is used.
import { execFileSync, spawnSync, type SpawnSyncOptions } from "node:child_process";
import { existsSync, copyFileSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";

export const REPO_ROOT = path.resolve(__dirname, "../../..");
export const WEB_PORT = Number(process.env.E2E_WEB_PORT || 13000);
export const API_PORT = Number(process.env.E2E_API_PORT || 18000);

/**
 * Each port pair gets its own Compose project, and therefore its own containers and
 * volumes, so a second run on other ports cannot reset or delete the first run's data.
 */
export function projectName(webPort: number, apiPort: number, explicit?: string) {
  if (explicit) return explicit;
  return webPort === 13000 && apiPort === 18000 ? "dubsibhai-e2e" : `dubsibhai-e2e-${webPort}-${apiPort}`;
}
export const PROJECT = projectName(WEB_PORT, API_PORT, process.env.E2E_PROJECT);

/**
 * One run per project at a time. The lock is taken before any setup step and released
 * after teardown; a lock left by a process that no longer exists is reclaimed.
 */
export function acquireRunLock(project: string, dir = os.tmpdir(), pid = process.pid) {
  const file = path.join(dir, `${project}.e2e.lock`);
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      writeFileSync(file, JSON.stringify({ pid, startedAt: new Date().toISOString() }), { flag: "wx" });
      return file;
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code !== "EEXIST") throw error;
      let owner = 0;
      try { owner = Number(JSON.parse(readFileSync(file, "utf-8")).pid) || 0; } catch { /* unreadable: treat as stale */ }
      if (owner && owner !== pid && processExists(owner)) {
        throw new Error(`[e2e] Another browser smoke run (process ${owner}) is using project ${project}. ` +
          "Wait for it to finish, or start this run on other ports (E2E_WEB_PORT/E2E_API_PORT) " +
          "so it gets its own stack.");
      }
      rmSync(file, { force: true });
    }
  }
  throw new Error(`[e2e] Could not take the run lock ${file}.`);
}

export function ownsRunLock(project: string, dir = os.tmpdir(), pid = process.pid) {
  try {
    return Number(JSON.parse(readFileSync(path.join(dir, `${project}.e2e.lock`), "utf-8")).pid) === pid;
  } catch {
    return false;
  }
}

export function releaseRunLock(project: string, dir = os.tmpdir(), pid = process.pid) {
  const file = path.join(dir, `${project}.e2e.lock`);
  try {
    if (Number(JSON.parse(readFileSync(file, "utf-8")).pid) === pid) rmSync(file, { force: true });
  } catch { /* already released */ }
}

function processExists(pid: number) {
  try { process.kill(pid, 0); return true; } catch (error) { return (error as NodeJS.ErrnoException).code === "EPERM"; }
}
export const WEB_URL = `http://localhost:${WEB_PORT}`;
export const API_URL = `http://localhost:${API_PORT}/api/v1`;

export type AccountKey = "reporter" | "verifier1" | "verifier2" | "verifier3" | "verifier4" | "mayor" | "worker";
export interface Account { key: AccountKey; email: string; name: string; role: "citizen" | "worker" | "admin" }

// Five distinct verified citizens are needed: completion is confirmed after 5 approvals.
export const ACCOUNTS: Account[] = [
  { key: "reporter", email: "e2e-reporter@example.com", name: "E2E Reporter", role: "citizen" },
  { key: "verifier1", email: "e2e-verifier-1@example.com", name: "E2E Verifier One", role: "citizen" },
  { key: "verifier2", email: "e2e-verifier-2@example.com", name: "E2E Verifier Two", role: "citizen" },
  { key: "verifier3", email: "e2e-verifier-3@example.com", name: "E2E Verifier Three", role: "citizen" },
  { key: "verifier4", email: "e2e-verifier-4@example.com", name: "E2E Verifier Four", role: "citizen" },
  { key: "mayor", email: "e2e-mayor@example.com", name: "E2E Mayor", role: "admin" },
  { key: "worker", email: "e2e-worker@example.com", name: "E2E Worker", role: "worker" },
];
export const account = (key: AccountKey) => ACCOUNTS.find(row => row.key === key)!;

/** `docker compose` for the isolated project: base local stack plus the e2e override. */
export function composeArgs(...args: string[]) {
  return [
    "compose", "--project-name", PROJECT,
    "--project-directory", path.join(REPO_ROOT, "infra"),
    "-f", path.join(REPO_ROOT, "infra/docker-compose.local.yml"),
    "-f", path.join(__dirname, "docker-compose.e2e.yml"),
    ...args,
  ];
}

const env = () => ({ ...process.env, E2E_WEB_PORT: String(WEB_PORT), E2E_API_PORT: String(API_PORT) });

export function compose(args: string[], options: SpawnSyncOptions = {}) {
  const result = spawnSync("docker", composeArgs(...args), { env: env(), encoding: "utf-8", ...options });
  if (result.error) throw result.error;
  if (result.status !== 0) {
    const output = [result.stdout, result.stderr].filter(Boolean).join("\n").trim();
    throw new Error(`docker ${composeArgs(...args).join(" ")} failed (exit ${result.status})${output ? `:\n${output}` : ""}`);
  }
  return String(result.stdout || "");
}

/** Recent service logs, attached to failed tests. Never throws. */
export function serviceLogs(services = ["api", "web", "ml-service"], tail = 150) {
  try {
    return execFileSync("docker", composeArgs("logs", "--no-color", "--tail", String(tail), ...services), {
      env: env(), encoding: "utf-8", maxBuffer: 10 * 1024 * 1024,
    });
  } catch (error) {
    return `Could not read service logs: ${error instanceof Error ? error.message : String(error)}`;
  }
}

/** The API container reads the root .env; create it from the example like the launchers do. */
export function ensureRootEnv() {
  const target = path.join(REPO_ROOT, ".env");
  if (!existsSync(target)) {
    copyFileSync(path.join(REPO_ROOT, ".env.example"), target);
    console.log("[e2e] Created .env from .env.example (required by the API container).");
  }
}
