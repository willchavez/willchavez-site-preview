const { createHash } = require('node:crypto');

// Use a distinct Pages build version for every publish attempt. The workflow's
// own commit is often unchanged while source_ref points at different site code.
async function publishPreview({ github, core, context, sourceSha, fetchPublic = fetch,
  wait = ms => new Promise(resolve => setTimeout(resolve, ms)),
  createAttempts = 12, statusAttempts = 60, publicAttempts = 24 }) {
  if (!/^[a-f0-9]{40}$/.test(sourceSha)) throw new Error('Expected a full source commit SHA');
  const repo = context.repo;
  const runAttempt = context.runAttempt ?? process.env.GITHUB_RUN_ATTEMPT ?? 1;
  const { data } = await github.rest.actions.listWorkflowRunArtifacts({ ...repo, run_id: context.runId, per_page: 100 });
  const artifacts = data.artifacts.filter(a => a.name === 'github-pages' && !a.expired);
  if (artifacts.length !== 1) throw new Error('Expected one unexpired github-pages artifact');
  const pageUrl = `https://${repo.owner.toLowerCase()}.github.io/${repo.repo}/`;
  const terminal = new Set(['deployment_failed', 'deployment_content_failed', 'deployment_cancelled', 'deployment_lost']);
  for (let publish = 1; publish <= 2; publish++) {
    const version = createHash('sha1').update(`${sourceSha}:${context.runId}:${runAttempt}:${publish}`).digest('hex');
    const idToken = await core.getIDToken();
    core.setSecret(idToken);
    let deployment;
    for (let attempt = 0; attempt < createAttempts; attempt++) {
      try {
        deployment = (await github.request('POST /repos/{owner}/{repo}/pages/deployments', {
          ...repo, artifact_id: artifacts[0].id, pages_build_version: version, oidc_token: idToken,
        })).data;
        break;
      } catch (error) {
        const temporary = error.status >= 500 || error.status === 429 ||
          (error.status === 400 && /in progress deployment/i.test(error.message));
        if (!temporary || attempt === createAttempts - 1) throw error;
        core.info('Pages is busy; waiting before retrying this artifact.');
        await wait(5000);
      }
    }
    const id = deployment.id || deployment.status_url?.split('/').pop() || version;
    core.info(`Publishing source ${sourceSha} with unique Pages version ${version}`);
    let succeeded = false;
    for (let poll = 0; poll < statusAttempts; poll++) {
      const { data: status } = await github.request('GET /repos/{owner}/{repo}/pages/deployments/{deployment_id}', { ...repo, deployment_id: id });
      if (status.status === 'succeed') { succeeded = true; break; }
      if (terminal.has(status.status)) throw new Error(`Pages deployment ended with ${status.status}`);
      await wait(5000);
    }
    if (!succeeded) {
      try { await github.request('POST /repos/{owner}/{repo}/pages/deployments/{deployment_id}/cancel', { ...repo, deployment_id: id }); } catch {}
      throw new Error('Timed out waiting for Pages deployment');
    }
    for (let poll = 0; poll < publicAttempts; poll++) {
      try {
        const response = await fetchPublic(`${pageUrl}preview-source.json?run=${context.runId}-${runAttempt}-${publish}-${poll}`, {
          headers: { 'Cache-Control': 'no-cache' }, signal: AbortSignal.timeout(15000),
        });
        if (response.ok && (await response.json()).commit === sourceSha) {
          core.info(`Verified public preview source: ${sourceSha}`);
          core.setOutput('page_url', pageUrl);
          return { sourceSha, version, pageUrl };
        }
      } catch { /* A temporarily missing public marker is retried. */ }
      await wait(5000);
    }
    core.warning('Pages reported success but the public source is stale; retrying once with a fresh build version.');
  }
  throw new Error('Public preview never matched the requested source commit; refusing to report success');
}
module.exports = { publishPreview };
