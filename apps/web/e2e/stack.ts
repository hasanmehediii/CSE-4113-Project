// Shared settings for the isolated browser smoke stack. Only synthetic data is used.
import { execFileSync, spawnSync, type SpawnSyncOptions } from "node:child_process";
import { existsSync, copyFileSync } from "node:fs";
import path from "node:path";

export const REPO_ROOT = path.resolve(__dirname, "../../..");
export const PROJECT = process.env.E2E_PROJECT || "dubsibhai-e2e";
export const WEB_PORT = Number(process.env.E2E_WEB_PORT || 13000);
export const API_PORT = Number(process.env.E2E_API_PORT || 18000);
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
