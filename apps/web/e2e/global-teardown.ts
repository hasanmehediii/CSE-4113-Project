// Removes the isolated stack and its volumes, so every default run starts clean.
import { compose } from "./stack";

export default async function globalTeardown() {
  if (process.env.E2E_KEEP_STACK === "1" || process.env.E2E_REUSE_STACK === "1") {
    console.log("[e2e] Keeping the isolated stack. Remove it later with: docker compose -p dubsibhai-e2e down -v");
    return;
  }
  console.log("[e2e] Removing the isolated stack and its volumes.");
  compose(["down", "--volumes", "--remove-orphans"], { stdio: "inherit" });
}
