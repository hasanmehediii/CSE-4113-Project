import { defineConfig, devices } from "@playwright/test";
import { WEB_URL } from "./stack";

// One browser, one worker: the workflow is a single ordered story against one stack.
export default defineConfig({
  testDir: ".",
  testMatch: "*.spec.ts",
  timeout: 5 * 60_000,
  expect: { timeout: 30_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  forbidOnly: !!process.env.CI,
  outputDir: "../test-results",
  reporter: [["list"], ["html", { open: "never", outputFolder: "../playwright-report" }]],
  globalSetup: "./global-setup.ts",
  globalTeardown: "./global-teardown.ts",
  use: {
    ...devices["Desktop Chrome"],
    // Optional: E2E_BROWSER_CHANNEL=chrome or msedge uses an installed browser instead.
    channel: process.env.E2E_BROWSER_CHANNEL || undefined,
    baseURL: WEB_URL,
    viewport: { width: 1366, height: 900 },
    // The Next.js dev server compiles each page on first visit.
    navigationTimeout: 90_000,
    actionTimeout: 30_000,
    // The spec records one trace per signed-in account itself and attaches them on failure.
    // Built-in tracing stays off: with contexts created by the test it stalls until the
    // test timeout after a failure. Video is off: the traces already keep a screenshot timeline.
    trace: "off",
    screenshot: "only-on-failure",
    video: "off",
  },
});
