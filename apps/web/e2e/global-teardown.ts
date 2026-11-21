// Removes the isolated stack this run started, together with its volumes.
import { PROJECT, compose, ownsRunLock, releaseRunLock } from "./stack";

export default async function globalTeardown() {
  // Playwright calls teardown even when setup failed. A run that never took the lock
  // (another run owns this project) must not touch that run's stack.
  if (!ownsRunLock(PROJECT)) {
    console.log(`[e2e] This run does not own project ${PROJECT}; leaving its stack untouched.`);
    return;
  }
  try {
    if (process.env.E2E_KEEP_STACK === "1" || process.env.E2E_REUSE_STACK === "1") {
      console.log(`[e2e] Keeping the isolated stack. Remove it later with: docker compose -p ${PROJECT} down -v`);
    } else if (process.env.E2E_STACK_STARTED !== "1") {
      console.log(`[e2e] This run did not start ${PROJECT}; leaving it untouched.`);
    } else {
      console.log(`[e2e] Removing the isolated stack ${PROJECT} and its volumes.`);
      compose(["down", "--volumes", "--remove-orphans"], { stdio: "inherit" });
    }
  } finally {
    releaseRunLock(PROJECT);
  }
}
