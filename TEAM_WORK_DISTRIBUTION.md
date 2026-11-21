# DubsiBhai — Team Work Distribution

Prepared: 20 November 2026

Team: **Moin, Biplob, Nafisha and Mehedi**

## Purpose and scope

Divide ownership of the existing project, finish targeted improvements, and
prepare a reliable demonstration. Most core features already exist: members
should understand, verify and improve their assigned modules rather than rebuild
them. The tasks below are planned work, not a claim that a listed feature is broken.

Mehedi has a deliberately light implementation workload to leave time for finding,
reporting and fixing small bugs across the project. Nafisha has a slightly more
challenging integration workload and can use Claude Code for assistance; Nafisha
remains responsible for understanding and verifying the changes.

## Ownership at a glance

| Member | Main responsibility | Workload | Main deliverable |
| --- | --- | --- | --- |
| **Moin** | Frontend and user experience | Moderate | Reliable citizen, worker and mayor screens on desktop and mobile |
| **Biplob** | Backend, database and local service integration | Moderate | Verified API rules, persistent data and working service setup |
| **Nafisha** | ML service, map predictions and integration testing | Moderate | Tested prediction flow, clear model limitations and one automated browser workflow |
| **Mehedi** | Manual testing, bug tracking and small fixes | QA | Reproducible bug reports, simple fixes and retest results |

Ownership means coordinating changes in an area, explaining its behavior and
reviewing fixes that touch it. It does not mean implementing every future feature
mentioned in the project README.

## Moin — Frontend and user experience

**Primary files:** `apps/web/src/app/`, `apps/web/src/components/`,
`apps/web/src/lib/civic-i18n.ts` and relevant frontend tests. Coordinate map and
prediction component changes with Nafisha.

| ID | Task | Completion criteria |
| --- | --- | --- |
| M1 | Verify the citizen journey: account screens, complaint creation, complaint list/detail and personal history. Fix concrete UI issues found. | A citizen can submit a report and find it again. Validation, loading, empty and failed-request states are understandable. |
| M2 | Check worker and mayor screens: applications, assignments, completion submission and moderation controls. | Each role sees the appropriate actions; successful changes refresh the displayed state. Coordinate API behavior with Biplob. |
| M3 | Polish mobile layouts, English/Bangla text and light/dark themes. | Key screens fit a 390-pixel-wide viewport without horizontal scrolling; controls remain reachable and language changes preserve drafts. |
| M4 | Verify UI changes and prepare a short visual walkthrough. | Relevant frontend tests, lint, type checking and build pass. Provide screenshots and steps for the changed screens. |

**First task:** M1. Complete one citizen journey before polishing additional pages.

## Biplob — Backend, database and service setup

**Primary files:** `apps/api/`, `db/`, `infra/` and root/service launchers.
Coordinate ML worker changes with Nafisha and visible API errors with Moin.

| ID | Task | Completion criteria |
| --- | --- | --- |
| B1 | Verify registration/login, session handling and role checks against the existing API tests. Fix reproduced defects. | Valid requests work and unauthorized role actions are rejected by the server. Relevant authentication tests pass. |
| B2 | Verify the report lifecycle: incident grouping, assignment/reassignment, completion, verification and moderation. | A complete workflow preserves every report and its evidence, shares incident status correctly and rejects stale or duplicate actions. Add regression coverage for behavior changed. |
| B3 | Check migrations, bootstrap and persistence in an isolated local stack. | A fresh database reaches the current migration head, bootstrap can run again, and data survives a normal stop/start. Document any setup correction. |
| B4 | Verify startup and background services on a teammate's machine. | Record the startup command, service status and any errors. Confirm the event-projection and classification workers start. Investigate the reported PowerShell/VS Code crash using actual logs; record whether it is resolved or still reproducible. |

**First task:** B3, followed by B4, so everyone has a usable development setup.

Keep fixes focused. Major authentication redesigns, incident merge/split tools and
production hosting are outside this assignment.

### Biplob validation record — 21 November 2026

- Environment: Linux, Docker Engine/Compose v2, PostgreSQL 17, MongoDB 8,
  Redis 7 and Mailpit.
- Fresh migrations applied successfully and reached Alembic head
  `20261031_06`. The bootstrap was rerun successfully and remained idempotent.
  A database stop/start preserved the migration state.
- The API suite passed 101 tests with 7 optional real-database tests skipped.
  The focused auth, registration, civic, assignment, lifecycle and incident
  suites passed 71 tests. Seven opt-in PostgreSQL/Mongo integration tests passed
  with `RUN_POSTGRES_TESTS=1`.
- The complete Docker stack started API, ML, web, Nginx, event projection and
  classification workers. API and ML health endpoints were ready; the stack
  was stopped without deleting volumes.
- Setup correction: Git now tracks the Linux `.sh` launchers as executable,
  so `./scripts/migrate.sh` and `./scripts/start.sh` can be used directly.
- The reported PowerShell/VS Code crash could not be reproduced on this Linux
  machine because Windows tools and logs were unavailable. The existing
  PowerShell launchers record startup failures and direct the user to service
  logs; still required: rerun `.\run.ps1 -Check` on the affected Windows/VS
  Code machine and attach the launcher logs under `.cache/run-all/<run-id>/`
  if the crash recurs.

## Nafisha — ML, maps and integration testing

**Primary files:** `apps/ml-service/`, `packages/data/`, `packages/new-data/`,
map/prediction components under `apps/web/src/components/map/`, and relevant tests.
Coordinate `apps/api/app/api/v1/map.py` and classification-worker changes with Biplob.

| ID | Task | Completion criteria |
| --- | --- | --- |
| N1 | Verify both ML paths: Bengali complaint classification and road-risk prediction. Improve diagnostics for a reproduced startup or inference problem. | Missing models can be trained; `/ready` succeeds after loading; valid inputs produce the expected response structure. Invalid inputs and unavailable models have tested failure behavior. |
| N2 | Verify the full prediction flow from map selection and rainfall input through the API to the ML response. Fix integration defects found. | The selected road and supplied rainfall reach inference correctly; results match the selected road. Failed requests show an understandable state and can be retried. |
| N3 | Audit road coverage and prediction explanations. | Document current mapped/unmapped segment counts and any mapping errors. Clearly distinguish synthetic scenario predictions from observations and explain that the weather widget does not currently supply prediction rainfall. Coordinate visible wording with Moin. |
| N4 | Add one repeatable real-browser smoke workflow using a suitable browser test tool. | In an isolated test environment, synthetic citizen, mayor and worker accounts complete report → assignment → completion → citizen verification. Include a documented command, fixture setup/cleanup and useful failure output. |

**First task:** N1, then N2. Build N4 after Moin and Biplob confirm the main
workflow and agree on test accounts and fixture setup.

Claude Code can help inspect code, draft changes and implement tests. Review its
output, run the checks and be ready to explain the API flow and model limitations.
This assignment does not require collecting real Dhaka observations, claiming
real-world accuracy, implementing new prediction algorithms or connecting a live
weather provider.

## Mehedi — Bug discovery, small fixes and retesting

**Primary area:** the running application, bug records and setup documentation.
Make small code changes in the relevant owner's area after coordinating with them.

Reserve most of the available time for testing and retesting. There is no major
new feature, database migration, ML implementation or test-framework setup assigned
to Mehedi.

| ID | Task | Completion criteria |
| --- | --- | --- |
| H1 | Follow the manual smoke checklist below and record what happens. | Mark each check Pass, Fail or Blocked, with the tested commit and environment. |
| H2 | Report reproducible bugs found in teammates' work. | Each report contains steps, expected/actual behavior, evidence and the relevant owner. |
| H3 | Fix small, clearly understood issues: typos, incorrect labels, documentation mistakes, broken links or minor spacing problems. | The issue no longer reproduces, the change is small and the module owner reviews it. |
| H4 | Retest teammates' fixes and update their bug records. | Record the tested commit and Pass/Fail result. Reopen an issue if the original reproduction still fails. |

**First task:** H1 on the current shared development version. If setup is blocked,
record the error and ask Biplob to investigate, then continue with documentation
and any available application checks.

For bugs involving permissions, passwords, database state, incident lifecycle or
model behavior, Mehedi supplies a reproduction and works with the owner. Discovering
a difficult bug does not make Mehedi solely responsible for implementing its fix.

### Mehedi's manual smoke checklist

- [ ] Start the project using the documented launcher; open the frontend.
- [ ] Register/login as a synthetic citizen and log out again.
- [ ] Submit a complaint and open its detail page.
- [ ] Try an empty required field and confirm a useful validation message appears.
- [ ] Open the public complaint list and map.
- [ ] Switch English/Bangla and light/dark themes.
- [ ] Open key pages at mobile width and check that buttons remain reachable.
- [ ] With prepared accounts, check mayor assignment and worker completion screens.
- [ ] Retest each reported bug after its owner provides a fix.

### Bug report template

```markdown
## Short title
- Tested commit/branch:
- Environment: Windows/browser, startup command and relevant versions
- Page or service:
- Owner: Moin / Biplob / Nafisha
- Priority: High / Medium / Low
- Steps to reproduce:
  1.
  2.
- Expected behavior:
- Actual behavior:
- Evidence: screenshot, error text or relevant logs without secrets
- Fix commit:
- Retest: Pass / Fail / Blocked, with tested commit
```

Use **High** for a broken core workflow, access-control failure or data-loss issue;
**Medium** for a feature with a practical workaround; **Low** for cosmetic or text
issues. A bug is verified fixed after the original reproduction passes again.

## Delivery order and handoffs

| Phase | Moin | Biplob | Nafisha | Mehedi |
| --- | --- | --- | --- | --- |
| 1. Establish baseline | Verify citizen screens | Verify migrations and teammate startup | Verify model training and readiness | Run available smoke checks and log failures |
| 2. Improve modules | Fix targeted UI issues | Fix API/data/service defects | Verify map-to-ML flow and document coverage | Fix small issues and retest completed changes |
| 3. Integrate | Stabilize screens used by browser tests | Provide isolated account/fixture setup | Implement the automated browser workflow | Repeat the manual checklist and verify fixes |
| 4. Prepare demo | Explain the user interface | Explain API and database lifecycle | Explain ML, integration and limitations | Present test results and any unresolved issues |

Agree dates as a team; this plan does not assume a deadline. Before cross-module
changes, agree on request/response fields, error behavior and who edits shared files.
Biplob coordinates startup/infrastructure changes; Moin coordinates shared UI styles.

## Shared completion rules

- Work in focused task branches from updated `dev`. Follow the existing
  [branch workflow](docs/guideline/BRANCH_WORKFLOW_BN.md) and
  [commit guide](docs/guideline/COMMIT_GUIDE_BN.md).
- Keep each change small enough for its owner or another teammate to review.
  Follow the existing `dev` integration and reviewed `dev` → `main` release process.
- Include what changed, why, how it was verified and any remaining limitation.
- Run checks appropriate to the changed area using [DEVELOPMENT.md](DEVELOPMENT.md).
  For behavior-changing fixes, add a focused regression test when practical.
- Use isolated test data for automated workflows. Keep credentials out of commits
  and retain existing user data when testing launchers.
- Before the final demo, follow [pre-release checks](docs/guideline/PRE_RELEASE_CHECKS.md).
  Record unresolved failures explicitly; do not mark blocked work complete.

## Final deliverables

| Member | Handoff |
| --- | --- |
| Moin | Verified UI changes, relevant checks and screenshots/demo steps |
| Biplob | Verified API/database changes, setup findings and relevant tests |
| Nafisha | Verified ML/map flow, coverage/limitations note and runnable browser smoke test |
| Mehedi | Completed manual checklist, bug records, small fixes and retest evidence |
