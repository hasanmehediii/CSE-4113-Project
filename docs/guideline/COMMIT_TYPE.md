# Commit Messages and Branch Workflow

This guide explains how we contribute to **DubsiBhai**. Every change goes through a task branch and a pull request (PR), including small fixes and documentation updates.

## 1. Branch rules

| Branch | Purpose | Who merges into it? |
| --- | --- | --- |
| `main` | Reviewed, tested, stable code | Project maintainer, after checking `dev` |
| `dev` | Integration branch for the team's completed work | Project maintainer or an assigned reviewer |
| Task branch | One feature, fix, or other focused change | Its author pushes commits and opens a PR into `dev` |

**Do not push directly to `main` or `dev`.** Push your task branch and wait for review and merge approval. Do not merge your own PR unless the maintainer explicitly authorizes it.

The normal flow is:

```text
dev -> task branch -> PR into dev -> review and merge
dev -> PR into main -> final checks and maintainer approval -> merge
```

Create task branches from the latest `dev`, and target `dev` when opening their PRs. A task PR must not target `main`.

## 2. Branch names

Use this format:

```text
<type>/<short-description>
```

Use lowercase words separated by hyphens. Keep each branch focused on one task.

Examples:

```text
feat/complaint-submission
fix/login-validation
docs/local-setup-guide
refactor/complaint-service
test/api-health-checks
chore/update-dependencies
ci/api-checks
```

Use the commit types below as branch prefixes too. If your task has an issue number, you may include it: `feat/12-complaint-submission`.

## 3. Commit message format

Every commit message must start with a lowercase type in parentheses, followed by a colon, one space, and a short description:

```text
(type): describe the change
```

Examples:

```text
(feat): add complaint submission endpoint
(fix): reject complaints with missing coordinates
(docs): explain how to run all services on Windows
```

Use **our exact format**: `(feat): ...`, rather than `feat: ...` or `feat(...): ...`.

| Type | When to use it | Example |
| --- | --- | --- |
| `feat` | Add a new feature or capability | `(feat): add ward filtering to the complaint map` |
| `fix` | Correct broken or incorrect behavior | `(fix): return 404 for missing complaints` |
| `docs` | Change documentation only | `(docs): add API setup instructions` |
| `style` | Change code formatting without changing behavior | `(style): format API imports and indentation` |
| `refactor` | Restructure code without adding features or fixing behavior | `(refactor): extract complaint validation into a service` |
| `perf` | Improve performance while preserving behavior | `(perf): reduce queries when listing complaints` |
| `test` | Add or update tests | `(test): cover invalid login credentials` |
| `build` | Change build tooling, packaging, or dependency configuration | `(build): configure the Next.js production build` |
| `ci` | Change automated checks or deployment workflows | `(ci): run API tests on pull requests` |
| `chore` | Perform maintenance that does not fit another type | `(chore): ignore local model weights` |
| `revert` | Undo an earlier change | `(revert): undo complaint auto-verification` |

Choose the type based on the purpose of the change. For example, a dependency update that fixes a bug can use `fix`; routine dependency maintenance can use `chore` or `build`. A new visual UI feature uses `feat`; correcting a broken layout uses `fix`. `style` is for code formatting.

### Writing useful messages

- Start the description with an action: `add`, `fix`, `update`, `remove`, or `refactor`.
- Explain what changed. Avoid messages such as `update`, `done`, `final`, or `fixed things`.
- Keep the first line concise; aim for 72 characters or fewer and omit a trailing period.
- Keep one logical change per commit. A feature and its tests can belong together; unrelated work should be separate.
- Mention the affected area when helpful, such as API, web, or ML service.
- Use an optional body to explain why a change is needed or describe migration steps.

For an incompatible API or configuration change, use the normal prefix and explain the impact in the body:

```text
(feat): require ward identifiers when creating complaints

BREAKING CHANGE: complaint creation now requires ward_id.
Update API clients before deploying this change.
```

## 4. Complete contribution workflow

Run Git commands from the repository root. Replace the example branch name, paths, and message with your own task details.

### Step 1: Start from the latest dev

Make sure your working tree is clean before switching branches. Commit unfinished work on its existing task branch, or stash it first.

```powershell
git status
git fetch origin
git switch dev
git pull --ff-only origin dev
git switch -c feat/complaint-submission
```

If `dev` exists on the remote but you do not yet have a local copy, replace `git switch dev` with:

```powershell
git switch --track origin/dev
```

If `origin/dev` does not exist yet, ask the maintainer to create it before starting this workflow.

### Step 2: Implement and check your change

Make the change, run the affected app, and run the relevant checks. Check [the project README](../../README.md) for setup and startup commands.

For frontend changes, run these inside `apps/web`:

```powershell
npx --yes pnpm@10.34.5 lint
npx --yes pnpm@10.34.5 typecheck
npx --yes pnpm@10.34.5 build
```

For Python changes, run these inside the affected service folder, `apps/api` or `apps/ml-service`:

```powershell
uv run pytest
uv run ruff check app tests
```

For documentation-only changes, check the wording, paths, links, and command examples. If you cannot run a relevant check, explain that in your PR.

### Step 3: Review and commit

Return to the repository root, inspect your changes, and stage only the files that belong to this task:

```powershell
git status
git diff
git add apps/api/app/api/v1/complaints.py
git diff --cached
git commit -m "(feat): add complaint submission endpoint"
```

Add other relevant files explicitly as needed. Do not commit secrets, `.env` files, virtual environments, `node_modules`, generated build output, or downloaded model weights. Commit relevant dependency manifests and lockfile changes together.

### Step 4: Push your task branch

```powershell
git push -u origin feat/complaint-submission
```

For later commits on that same branch:

```powershell
git push
```

A push uploads your commits; it does not merge them into `dev` or `main`.

### Step 5: Open a pull request into dev

On GitHub, open a PR with:

- **Base:** `dev`
- **Compare:** your task branch, for example `feat/complaint-submission`
- **Title:** the same format as a commit, for example `(feat): add complaint submission endpoint`
- **Description:** what changed, why, checks performed and their results, and any limitations or follow-up work

Link the related issue if there is one. Include screenshots for visible UI changes when useful. Request review from the maintainer or assigned reviewer, then wait for approval and merge.

If changes are requested, add commits to the **same branch** and push again. The existing PR updates automatically; you do not need a new PR.

### Step 6: Update your branch if dev changes

If your PR needs the latest changes from `dev`, run this while on your task branch:

```powershell
git fetch origin
git merge origin/dev
```

If Git opens an editor for a merge commit, use a message such as:

```text
(chore): merge latest dev into complaint submission branch
```

If conflicts occur, resolve them carefully, stage the resolved files, and finish the merge with a commit in the same format. Run the relevant checks again, then push. Ask the affected teammate if you are unsure how their code should be combined with yours.

Do not force-push shared branches or discard someone else's work to resolve a conflict.

### Step 7: After your PR is merged

Update your local `dev` before beginning the next task:

```powershell
git switch dev
git pull --ff-only origin dev
```

Create a **new task branch** for new work. The merged branch can be deleted through the PR page after confirming the work is in `dev`.

## 5. Moving dev into main

The maintainer opens a separate PR from `dev` into `main` when the integrated changes are ready.

Before merging, the maintainer checks the combined application, relevant tests and builds, configuration changes, and any unresolved issues. Only approved, stable work moves into `main`.

Use the same message format for the PR title and any editable merge or squash commit message. For example:

```text
(chore): merge verified development changes into main
```

If checks fail, fix the problems through task branches into `dev`, then check the release PR again. Do not bypass the workflow with a direct push to `main`.

## 6. Maintainer setup

These are team rules; this document alone does not enforce them. The maintainer should configure repository access and branch protection or rulesets for both `main` and `dev`:

- Require pull requests and review approval before merging.
- Restrict merges into `main` to the maintainer or designated release owners.
- Block direct pushes, force pushes, and branch deletion, including bypasses where supported.
- Require relevant status checks once CI workflows are implemented and working.
- Require review conversations to be resolved before merge.

Until automated checks are available, reviewers must verify the reported local checks before approving a PR.
