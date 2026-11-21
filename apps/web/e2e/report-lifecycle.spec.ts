import { expect, test, type Browser, type BrowserContext, type Page } from "@playwright/test";
import { API_URL, account, serviceLogs, type AccountKey } from "./stack";

// Problems seen by every page in this test, attached when the test fails.
const diagnostics: string[] = [];
// One traced browser context per signed-in account. Traces are recorded here rather than
// by the config: Playwright's built-in trace collection stalls on contexts a test creates.
const contexts: { key: AccountKey; context: BrowserContext }[] = [];

function watch(page: Page, who: string) {
  page.on("pageerror", error => diagnostics.push(`[${who}] page error: ${error.message}`));
  page.on("console", message => {
    // Failed requests are recorded with their URL below; skip the browser's generic duplicate.
    if (message.type() === "error" && !message.text().startsWith("Failed to load resource")) {
      diagnostics.push(`[${who}] console error: ${message.text()}`);
    }
  });
  page.on("response", response => {
    const url = new URL(response.url());
    // Signed-out pages probe /auth/me and receive 401 by design.
    if (response.status() >= 400 && url.pathname.startsWith("/api/") && !url.pathname.endsWith("/auth/me")) {
      diagnostics.push(`[${who}] HTTP ${response.status()} ${response.request().method()} ${url.pathname}`);
    }
  });
}

async function signIn(browser: Browser, key: AccountKey) {
  const user = account(key);
  const context = await browser.newContext();
  await context.tracing.start({ title: key, screenshots: true, snapshots: true });
  contexts.push({ key, context });
  const page = await context.newPage();
  watch(page, key);
  await page.goto("/login");
  await page.locator("#email").fill(user.email);
  await page.locator("#password").fill(process.env.E2E_PASSWORD!);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.waitForURL(url => !url.pathname.startsWith("/login"));
  return page;
}

// The first badge on the detail page is the report's status.
const status = (page: Page) => page.locator("article.civic-card .civic-card-meta .civic-badge").first();

test.afterEach(async ({}, testInfo) => {
  const failed = testInfo.status !== testInfo.expectedStatus;
  if (failed) {
    await testInfo.attach("browser-diagnostics.txt", { body: diagnostics.join("\n") || "none", contentType: "text/plain" });
    await testInfo.attach("service-logs.txt", { body: serviceLogs(), contentType: "text/plain" });
  }
  for (const { key, context } of contexts.splice(0)) {
    if (failed) {
      // One trace per account: open with `pnpm exec playwright show-trace <file>`.
      const path = testInfo.outputPath(`trace-${key}.zip`);
      await context.tracing.stop({ path });
      await testInfo.attach(`trace-${key}.zip`, { path, contentType: "application/zip" });
    } else {
      await context.tracing.stop();
    }
    await context.close();
  }
  diagnostics.length = 0;
});

test("citizen report → mayor assignment → worker completion → citizen verification", async ({ browser, request }) => {
  const title = `E2E blocked drain ${Date.now().toString(36)}`;
  let reportPath = "";
  let reporter!: Page;

  await test.step("citizen submits a complaint", async () => {
    reporter = await signIn(browser, "reporter");
    await reporter.goto("/complaints/new");
    await reporter.locator('input[name="title"]').fill(title);
    await reporter.locator('select[name="category_code"]').selectOption("blocked_drain");
    await reporter.locator('textarea[name="description"]').fill("Synthetic browser smoke test: the drain is blocked and water is standing.");
    await reporter.locator('input[name="address"]').fill("Synthetic e2e location");
    // Choosing a catalog road also sets the report's coordinates.
    await reporter.locator('select[name="road_id"]').selectOption({ index: 1 });
    await expect(reporter.getByText("Location selected")).toBeVisible();
    // Keep each run's report separate even if an earlier run left a nearby incident.
    await reporter.locator('input[name="separate_incident"]').check();
    await reporter.getByRole("button", { name: /Publish report/ }).click();
    await reporter.waitForURL(/\/complaints\/[0-9a-f-]{36}$/);
    reportPath = new URL(reporter.url()).pathname;
    await expect(reporter.getByRole("heading", { name: title })).toBeVisible();
    await expect(status(reporter)).toHaveText("Open");
  });

  await test.step("mayor assigns the approved worker", async () => {
    const mayor = await signIn(browser, "mayor");
    await mayor.goto(reportPath);
    const form = mayor.locator("form", { has: mayor.getByRole("heading", { name: "Assign work" }) });
    const worker = form.locator('select[name="worker_id"]');
    await expect(worker.locator("option", { hasText: account("worker").name })).toHaveCount(1);
    await worker.selectOption({ label: account("worker").name });
    await form.getByRole("button", { name: "Assign complaint" }).click();
    await expect(status(mayor)).toHaveText("Assigned");
    await expect(mayor.getByRole("heading", { name: "Reassign work" })).toBeVisible();
  });

  await test.step("worker submits completed work", async () => {
    const worker = await signIn(browser, "worker");
    await worker.goto(reportPath);
    await worker.locator('textarea[name="comment"]').first().fill("Synthetic browser smoke test: drain cleared and the water has gone.");
    await worker.getByRole("button", { name: "Submit for community confirmation" }).click();
    await expect(worker.getByText("Saved. The report has been updated.")).toBeVisible();
    await expect(status(worker)).toHaveText("Awaiting confirmation");
    await expect(worker.getByText("0/5 community approvals")).toBeVisible();
  });

  await test.step("five citizens confirm the work", async () => {
    // The reporter keeps the session from the first step; each account signs in once per run.
    const voters: Page[] = [reporter];
    for (const key of ["verifier1", "verifier2", "verifier3", "verifier4"] as const) voters.push(await signIn(browser, key));
    for (const [index, voter] of voters.entries()) {
      await voter.goto(reportPath);
      await voter.getByRole("button", { name: "I confirm this work" }).click();
      await expect(voter.getByText(`${index + 1}/5 community approvals`)).toBeVisible();
    }
    await expect(status(voters[4])).toHaveText("Resolved");
  });

  await test.step("the API reports the resolved lifecycle", async () => {
    const response = await request.get(`${API_URL}/complaints/${reportPath.split("/").pop()}`);
    expect(response.ok()).toBeTruthy();
    const report = await response.json();
    expect(report.status).toBe("resolved");
    expect(report.resolutions).toHaveLength(1);
    expect(report.resolutions[0]).toMatchObject({ status: "confirmed", likes: 5, dislikes: 0 });
  });

  expect(diagnostics.filter(line => line.includes("page error")), "No application page errors").toEqual([]);
});
