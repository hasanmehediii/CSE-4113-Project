// Called only for successful push workflows on main; tests use a fake GitHub client.
const REQUIRED_WORKFLOWS = ["API CI", "Web CI", "ML Service CI", "Release CI"];
const version = tag => /^V[1-9]\d*$/.test(tag) ? BigInt(tag.slice(1)) : null;

async function publishRelease({ github, context, core }) {
  const { owner, repo } = context.repo;
  const run = context.payload.workflow_run;
  const repository = `${owner}/${repo}`;
  if (!run || run.event !== "push" || run.head_branch !== "main" ||
      run.conclusion !== "success" || run.head_repository?.full_name !== repository) {
    core.info("This event is not a successful main-branch push check; no release.");
    return null;
  }
  const sha = run.head_sha;
  const pulls = await github.paginate(github.rest.repos.listPullRequestsAssociatedWithCommit, {
    owner, repo, commit_sha: sha, per_page: 100,
  });
  const pull = pulls.find(pr => pr.merged_at && pr.merge_commit_sha === sha &&
    pr.base.ref === "main" && pr.head.ref === "dev" && pr.head.repo?.full_name === repository);
  if (!pull) {
    core.info("This commit is not a merged dev-to-main pull request; no release.");
    return null;
  }
  const runs = await github.paginate(github.rest.actions.listWorkflowRunsForRepo, {
    owner, repo, branch: "main", event: "push", head_sha: sha, per_page: 100,
  });
  for (const name of REQUIRED_WORKFLOWS) {
    const latest = runs.filter(item => item.name === name && item.head_sha === sha &&
      item.event === "push" && item.head_branch === "main").sort((a, b) => b.id - a.id)[0];
    if (!latest || latest.status !== "completed" || latest.conclusion !== "success") {
      core.info(`${name} has not passed for ${sha}; a later successful check can retry.`);
      return null;
    }
  }

  // Reserve a tag atomically before creating its release. createRelease alone
  // ignores target_commitish when the tag already exists, which could otherwise
  // attach a concurrent release to the wrong merge commit.
  for (let attempt = 0; attempt < 3; attempt++) {
    const [tags, releases] = await Promise.all([
      github.paginate(github.rest.repos.listTags, { owner, repo, per_page: 100 }),
      github.paginate(github.rest.repos.listReleases, { owner, repo, per_page: 100 }),
    ]);
    const marker = `<!-- dubsibhai-release:${sha} -->`;
    const existing = releases.find(item => !item.draft &&
      (item.body?.includes(marker) || tags.some(tag => tag.name === item.tag_name && tag.commit.sha === sha)));
    if (existing) {
      core.info(`Already published: ${existing.html_url}`);
      return existing;
    }
    const numbered = tags.filter(tag => version(tag.name) !== null);
    const highest = numbered.reduce((value, tag) => version(tag.name) > value ? version(tag.name) : value, 0n);
    const reserved = numbered.find(tag => tag.commit.sha === sha);
    const tag = reserved?.name || `V${highest + 1n}`;
    if (!reserved) {
      try {
        await github.rest.git.createRef({ owner, repo, ref: `refs/tags/${tag}`, sha });
      } catch (error) {
        if (error.status !== 422 || attempt === 2) throw error;
        continue;
      }
    }
    const previous = releases.filter(item => !item.draft && !item.prerelease && version(item.tag_name) !== null)
      .sort((a, b) => version(a.tag_name) > version(b.tag_name) ? -1 : 1)[0];
    const notes = await github.rest.repos.generateReleaseNotes({
      owner, repo, tag_name: tag, target_commitish: sha,
      ...(previous && { previous_tag_name: previous.tag_name }),
    });
    try {
      const { data: release } = await github.rest.repos.createRelease({
        owner, repo, tag_name: tag, target_commitish: sha, name: `DubsiBhai ${tag}`,
        body: `Released from dev → main in #${pull.number}.\n\n${notes.data.body}\n\n${marker}`,
        draft: false, prerelease: false, make_latest: "true",
      });
      core.info(`Published ${release.name}: ${release.html_url}`);
      return release;
    } catch (error) {
      if (error.status !== 422 || attempt === 2) throw error;
    }
  }
}

module.exports = { publishRelease, REQUIRED_WORKFLOWS };
