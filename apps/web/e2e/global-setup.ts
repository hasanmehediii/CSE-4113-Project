// Starts the isolated stack (unless reused) and creates the synthetic accounts.
import { randomBytes } from "node:crypto";
import { readFileSync } from "node:fs";
import path from "node:path";
import { ACCOUNTS, API_URL, WEB_URL, compose, ensureRootEnv } from "./stack";

async function reachable(url: string) {
  try { return (await fetch(url, { signal: AbortSignal.timeout(5000) })).ok; } catch { return false; }
}

export default async function globalSetup() {
  ensureRootEnv();
  if (process.env.E2E_REUSE_STACK === "1") {
    console.log("[e2e] Reusing the running isolated stack (E2E_REUSE_STACK=1).");
  } else {
    console.log("[e2e] Starting the isolated stack. The first run builds images and trains the ML models (several minutes).");
    compose(["up", "--detach", "--build", "--wait", "--wait-timeout", "900"], { stdio: "inherit" });
  }
  for (const [name, url] of [["API", `${API_URL}/health`], ["web", `${WEB_URL}/login`]] as const) {
    if (!(await reachable(url))) {
      throw new Error(`[e2e] The isolated ${name} is not reachable at ${url}. Check \`docker compose -p dubsibhai-e2e ps\`, or run without E2E_REUSE_STACK.`);
    }
  }
  // A fresh random password per run keeps credentials out of the repository.
  const password = randomBytes(18).toString("base64url");
  const output = compose(
    ["exec", "-T", "-e", "E2E_ACCOUNTS", "-e", "E2E_PASSWORD", "api", "uv", "run", "--no-sync", "python", "-"],
    {
      input: readFileSync(path.join(__dirname, "fixtures/seed_accounts.py")),
      env: { ...process.env, E2E_ACCOUNTS: JSON.stringify(ACCOUNTS), E2E_PASSWORD: password },
    },
  );
  const ids = JSON.parse(output.trim().split("\n").pop()!);
  if (Object.keys(ids).length !== ACCOUNTS.length) throw new Error(`[e2e] Fixture setup returned ${output}`);
  console.log(`[e2e] Synthetic accounts ready: ${ACCOUNTS.map(row => row.email).join(", ")}`);
  // Workers inherit environment variables set during global setup.
  process.env.E2E_PASSWORD = password;
}
