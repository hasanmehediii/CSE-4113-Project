const { test } = require("node:test");
const assert = require("node:assert/strict");
const { publishRelease, REQUIRED_WORKFLOWS } = require("../publish-release.cjs");

function fixture() {
  const sha = "a".repeat(40);
  const repository = "team/DubsiBhai";
  const state = {
    tags: [{ name: "V1", commit: { sha: "old-main" } }],
    releases: [{ tag_name: "V1", name: "DubsiBhai V1", draft: false, prerelease: false, html_url: "releases/V1" }],
    pulls: [{ number: 12, merged_at: "2026-10-31T00:00:00Z", merge_commit_sha: sha,
      base: { ref: "main" }, head: { ref: "dev", repo: { full_name: repository } } }],
    runs: REQUIRED_WORKFLOWS.map((name, id) => ({ name, id, event: "push", head_branch: "main", head_sha: sha, status: "completed", conclusion: "success" })),
    created: [], reserved: [], notes: [],
  };
  const github = {
    paginate: async (method, args) => (await method(args)).data,
    rest: {
      actions: { listWorkflowRunsForRepo: async () => ({ data: state.runs }) },
      git: {
        createRef: async args => {
          const name = args.ref.replace("refs/tags/", "");
          if (state.tags.some(tag => tag.name === name)) throw Object.assign(new Error("Tag exists"), { status: 422 });
          state.reserved.push(args);
          state.tags.push({ name, commit: { sha: args.sha } });
          return { data: {} };
        },
      },
      repos: {
        listPullRequestsAssociatedWithCommit: async () => ({ data: state.pulls }),
        listTags: async () => ({ data: state.tags }),
        listReleases: async () => ({ data: state.releases }),
        generateReleaseNotes: async args => { state.notes.push(args); return { data: { body: "Generated changelog" } }; },
        createRelease: async args => {
          if (state.releases.some(release => release.tag_name === args.tag_name)) throw Object.assign(new Error("Release exists"), { status: 422 });
          const data = { ...args, html_url: `releases/${args.tag_name}` };
          state.created.push(args); state.releases.push(data);
          return { data };
        },
      },
    },
  };
  const context = { repo: { owner: "team", repo: "DubsiBhai" }, payload: {
    workflow_run: { event: "push", head_branch: "main", head_sha: sha, conclusion: "success", head_repository: { full_name: repository } },
  } };
  const core = { info() {} };
  return { github, context, core, state, sha };
}

test("publishes DubsiBhai V2 at the checked merge SHA and preserves V1", async () => {
  const input = fixture();
  const before = structuredClone(input.state.releases[0]);
  const release = await publishRelease(input);
  assert.equal(release.name, "DubsiBhai V2");
  assert.equal(release.target_commitish, input.sha);
  assert.equal(release.draft, false);
  assert.equal(release.prerelease, false);
  assert.deepEqual(input.state.releases[0], before);
  assert.equal(input.state.notes[0].previous_tag_name, "V1");
  assert.equal(input.state.tags.find(tag => tag.name === "V2").commit.sha, input.sha);
  assert.match(release.body, /Generated changelog/);
});

test("repeated workflow completions publish exactly once", async () => {
  const input = fixture();
  await publishRelease(input);
  await publishRelease(input);
  assert.equal(input.state.created.length, 1);
  assert.equal(input.state.reserved.length, 1);
});

for (const condition of ["failure", "cancelled", "in_progress", "missing"]) {
  test(`does not release while an exact-commit check is ${condition}`, async () => {
    const input = fixture();
    if (condition === "missing") input.state.runs.pop();
    else if (condition === "in_progress") input.state.runs[0].status = condition;
    else input.state.runs[0].conclusion = condition;
    assert.equal(await publishRelease(input), null);
    assert.equal(input.state.reserved.length, 0);
  });
}

test("a newer failed run takes precedence over an older successful run", async () => {
  const input = fixture();
  input.state.runs.push({ ...input.state.runs[0], id: 1000, conclusion: "failure" });
  assert.equal(await publishRelease(input), null);
});

test("a successful check from another commit cannot satisfy the gate", async () => {
  const input = fixture();
  input.state.runs[0].head_sha = "unrelated";
  assert.equal(await publishRelease(input), null);
});

for (const change of [
  input => { input.context.payload.workflow_run.event = "pull_request"; },
  input => { input.context.payload.workflow_run.head_branch = "dev"; },
  input => { input.context.payload.workflow_run.head_repository.full_name = "fork/DubsiBhai"; },
  input => { input.state.pulls = []; },
  input => { input.state.pulls[0].head.ref = "feature/example"; },
  input => { input.state.pulls[0].head.repo.full_name = "fork/DubsiBhai"; },
  input => { input.state.pulls[0].merge_commit_sha = "other-merge"; },
  input => { input.state.pulls[0].merged_at = null; },
]) {
  test(`ignores unrelated events and non-dev merges (${change.toString()})`, async () => {
    const input = fixture(); change(input);
    assert.equal(await publishRelease(input), null);
    assert.equal(input.state.created.length, 0);
  });
}

test("increments versions numerically and ignores unrelated tag conventions", async () => {
  const input = fixture();
  input.state.tags.push(...["V9", "V10", "v999", "preview"].map(name => ({ name, commit: { sha: name } })));
  assert.equal((await publishRelease(input)).tag_name, "V11");
});

test("resumes a reserved tag after release creation was interrupted", async () => {
  const input = fixture();
  input.state.tags.push({ name: "V2", commit: { sha: input.sha } });
  assert.equal((await publishRelease(input)).tag_name, "V2");
  assert.equal(input.state.reserved.length, 0);
});

test("a concurrent tag reservation retries with the next version", async () => {
  const input = fixture();
  const reserve = input.github.rest.git.createRef;
  input.github.rest.git.createRef = async args => {
    if (args.ref === "refs/tags/V2") {
      input.state.tags.push({ name: "V2", commit: { sha: "another-merge" } });
      throw Object.assign(new Error("Tag exists"), { status: 422 });
    }
    return reserve(args);
  };
  const release = await publishRelease(input);
  assert.equal(release.tag_name, "V3");
  assert.equal(input.state.tags.find(tag => tag.name === "V2").commit.sha, "another-merge");
});

test("permission and service failures are reported rather than treated as success", async () => {
  const input = fixture();
  input.github.rest.repos.createRelease = async () => { throw Object.assign(new Error("Forbidden"), { status: 403 }); };
  await assert.rejects(publishRelease(input), /Forbidden/);
});
