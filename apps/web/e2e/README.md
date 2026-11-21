# Browser smoke test: report → assignment → completion → verification

One repeatable [Playwright](https://playwright.dev/docs/intro) workflow drives a real
Chromium browser through the main civic lifecycle with synthetic accounts:

1. A citizen signs in and publishes a complaint on a catalog road.
2. The mayor assigns it to an approved worker.
3. The worker submits completed work.
4. Five citizens (the reporter and four others) confirm the work; the report becomes
   **Resolved**, and the API reports one confirmed completion with 5 approvals.

## Run it

Prerequisites: Docker Desktop running and the web dependencies installed. From
`apps/web`, the first time only:

```powershell
pnpm install
pnpm exec playwright install chromium
```

Then:

```powershell
pnpm test:e2e
```

The first run builds images and trains the ML models inside the test stack, so allow
several minutes. Later runs reuse Docker's build cache.

## Isolated environment

The test never uses the normal development stack or its data.

- **Separate stack.** `global-setup.ts` starts Compose project `dubsibhai-e2e` from
  `infra/docker-compose.local.yml` plus `e2e/docker-compose.e2e.yml`. It has its own
  containers and volumes. Only the web app (`localhost:13000`) and API
  (`localhost:18000`) are published; the database, Redis, MongoDB, Mailpit and ML are
  not, so a running development stack or a local PostgreSQL on 5432 does not conflict.
- **Fixture setup.** `fixtures/seed_accounts.py` runs inside the test API container
  and creates or refreshes seven verified `@example.com` accounts: five citizens, a
  mayor and an approved worker (see `ACCOUNTS` in `stack.ts`). Each run uses a new
  random password, so no credential is stored in the repository. The script refuses to
  run unless the container carries the `E2E_ISOLATED_STACK` marker set by the override.
  The real mayor settings in the root `.env` are blanked for this stack.
- **Cleanup.** `global-teardown.ts` runs `docker compose -p dubsibhai-e2e down --volumes`,
  removing the test containers and all test data, whether the test passed or failed.
- **Root `.env`.** The API container reads it. If it does not exist, setup copies
  `.env.example`, as `start.ps1` does.

## Options

| Variable | Effect |
| --- | --- |
| `E2E_KEEP_STACK=1` | Keep the test stack after the run, for inspection at `http://localhost:13000` |
| `E2E_REUSE_STACK=1` | Skip startup and teardown; use an already-running test stack (fast reruns) |
| `E2E_WEB_PORT`, `E2E_API_PORT` | Change the published test ports (defaults 13000 and 18000) |
| `E2E_BROWSER_CHANNEL=chrome` | Use an installed Chrome (or `msedge`) instead of Playwright's Chromium |

In PowerShell, set a variable for one run with `$env:E2E_KEEP_STACK = "1"; pnpm test:e2e`,
then `Remove-Item Env:E2E_KEEP_STACK`. Each account may sign in five times per 15 minutes,
so when reusing a stack wait a few minutes between repeated runs.

## When it fails

- The list output names the failing step, such as "worker submits completed work".
- `playwright-report/index.html` (open with `pnpm exec playwright show-report playwright-report`)
  shows the step, the error and a screenshot of every signed-in account's page.
- `test-results/` keeps one trace per signed-in account, such as `trace-worker.zip`.
  Open one with `pnpm exec playwright show-trace <path-to-trace.zip>` to replay that
  account's actions, page snapshots and network requests.
- Two attachments are added to a failed test: `browser-diagnostics.txt` (page errors,
  console errors and failed API calls, labelled by account) and `service-logs.txt`
  (the last 150 log lines from the test API, web and ML containers).
- If setup fails before the browser starts, rerun with `E2E_KEEP_STACK=1` and inspect
  `docker compose -p dubsibhai-e2e ps` and `docker compose -p dubsibhai-e2e logs api`.

## Scope

This is a smoke baseline for the main workflow in Chromium at 1366 × 900. It does not
cover other browsers, mobile layouts, image uploads, Google sign-in or email delivery.
Test accounts and fixtures were prepared for this workflow; confirm them with Moin
(screens) and Biplob (API and fixture setup) before relying on the test in reviews.
