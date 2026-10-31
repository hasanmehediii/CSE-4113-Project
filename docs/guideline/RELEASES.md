# Automatic DubsiBhai releases

The existing GitHub release **DubsiBhai V1**, tag `V1`, is retained. New releases
use the same repository-wide convention: `V2` / **DubsiBhai V2**, then `V3`, etc.
These tags identify application snapshots; they do not change individual service
package versions or deploy the application to a hosting provider.

## Publish a release

1. Merge reviewed feature/fix branches into `dev` and push `dev`.
2. Open a pull request with **base `main`, compare `dev`** in this repository.
3. Review and merge it, following the team branch guide. Keep the shared `dev` branch.
4. API CI, Web CI, ML Service CI and Release CI run on the resulting `main` commit.
5. After all four pass, **Publish release** creates the next tag at that exact
   checked commit and publishes a GitHub release with generated change notes.

The release workflow uses completion notifications from all four checks. Earlier
notifications exit without publishing if another check is still running or failed.
The final successful check can publish once the full set has passed.

Feature-branch pushes, unmerged/closed PRs, PRs from other branches or forks,
direct pushes to `main`, and failed or cancelled checks do not publish releases.
The workflow must be present on `main`; merging this implementation from `dev`
installs it for the first release and subsequent merges.

## Retry and permissions

The workflow uses the built-in `GITHUB_TOKEN`, with job-scoped contents write,
actions read and pull-request read permissions. No personal access token is needed.
Repository or organization policy must allow those permissions.

If a main CI check fails, fix the issue or rerun that check after addressing an
environmental failure. Successful completion rechecks the entire commit's CI set.
If publishing itself fails, rerun the failed **Publish release** job. A reserved
tag for that commit is reused, and an already published release is left intact.
Existing tags are never force-moved; version reservation handles concurrent merges.

## Validate changes to release automation

From the repository root, with Node.js 22:

```powershell
node --test scripts/tests/release.test.cjs
```

The tests use a fake GitHub client. They cover numbering after V1, exact-commit CI
gating, unrelated/fork events, retries, concurrent version reservations and duplicate
notifications. They never create real tags or releases. Release CI runs these tests
on every push and pull request.
