# Pre-release checks

Before merging a release PR from `dev` to `main`, verify the candidate commit's
five CI workflows and exercise the main application path. Keep release testing
separate from any shared database and use synthetic accounts/evidence.

## Verification record: 31 October 2026

The pre-release-polish changes were tested in a clean Git checkout without an
existing `.env`, `node_modules` or `.venv`. The root Windows Docker launcher built
the services, created example-based environment files, migrated a new PostgreSQL
database through `20261031_05`, bootstrapped categories/roads and trained missing
synthetic ML artifacts. All ten services reached their required running/healthy
state. A subsequent `start.ps1 -NoBuild` completed successfully.

The test used project `dubsi-release-smoke`, separate Docker volumes and alternate
published localhost ports so the existing `infra` stack and its data stayed in
place. Only host ports and corresponding frontend/CORS URLs were adjusted for
isolation; container-internal healthcheck ports stayed at their normal values.
The final API and CSS fixes below were applied to that checkout before retesting.
Docker build caches were available; this was not an offline or empty-image-cache test.

Real Chromium 156 browser interactions verified:

- Real password login for citizen, mayor and approved-worker accounts.
- Personal report history beyond the first 30 records, and point-ledger history
  beyond the first 100 entries. Report and ledger pages navigate independently.
- Two citizens submit complaints through the full composer with uploaded images.
  Both original submissions and images remain under one shared incident.
- Both the original reporter and a later witness see no incident vote buttons,
  including when the witness opens the original incident's URL.
- A mayor assigns one worker, explicitly reassigns to another, and the replacement
  submits completion through the additional report's URL.
- Five independent citizens confirm completion using the browser; both reports
  show `resolved`, one shared resolution and five approvals.
- Bangla labels and an unchanged draft after switching languages. Incident and
  composer layouts fit a 390 × 844 mobile viewport without horizontal scrolling;
  desktop history/workflow testing used 1366 × 900.
- No application `pageerror` events during the completed browser run.

The initial checks found two additional defects, now fixed and rechecked:

1. Direct Docker API authentication requests lacked `X-Real-IP` and were rejected.
   Missing proxy headers now use the connection peer for rate limiting. Headers
   from untrusted peers stay ignored; malformed supplied addresses from trusted
   peers still return 400. Regression tests cover these cases.
2. The composer location panel could grow beyond the viewport and, while sticky,
   intercept clicks on Publish. It now stays in the grid's normal flow. Browser
   submissions with manual coordinates and incident suggestions complete normally.

These checks provide a smoke-test baseline. They do not establish coverage for
every browser/device, Google OAuth, real SMTP delivery or a public deployment.
The browser runner and synthetic fixtures used for this verification are local
test artifacts, not a checked-in cross-browser CI suite.

## Repeat the application check

1. Clone the release candidate into a clean directory and run `./start.ps1` on
   Windows, or `bash scripts/start.sh` on Linux. Check migration/bootstrap logs,
   service health, web login and API/ML readiness. Use separate databases/volumes
   if another checkout is running. Never point test fixtures at shared user data.
2. Prepare verified synthetic citizen accounts, a mayor and two approved workers
   in the isolated database. Create enough personal history to cross page limits.
3. Follow the report/group/assign/reassign/complete/confirm sequence above, using
   distinct accounts. Check originals, uploaded evidence, counts and shared status.
4. Repeat key pages on mobile and in Bangla. Verify drafts, pagination, voting
   controls, retry states and that the Publish button is clickable.
5. Stop the isolated test project after checking. Keep the normal development
   project and its volumes intact.

## History and participation API

- `GET /api/v1/me/complaints?limit=30&offset=30` preserves the existing array
  response; `include_total=true` instead returns `{items, total}`. Limits are
  1–100, offsets are nonnegative, and totals include every personal submission.
- `GET /api/v1/me/points?limit=20&offset=100` returns `{balance, total, entries}`.
  The default limit remains 100. Balance always includes the full ledger, and
  total counts only the signed-in account's entries.
- `GET /api/v1/me/complaints/{report_id}/participation` returns the authenticated
  account's `{is_reporter}` for the whole incident. Public report responses do
  not expose reporter account IDs. UI visibility does not replace server checks.

After review, use a same-repository **dev → main PR**. Check all five workflows
on the resulting main commit, then verify the first real numbered publication as
described in [RELEASES.md](RELEASES.md). A main merge publishes a GitHub release;
it does not deploy the application to public hosting.
