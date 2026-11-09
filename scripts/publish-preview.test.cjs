const test = require('node:test');
const assert = require('node:assert/strict');
const { publishPreview } = require('./publish-preview.cjs');
const sourceSha = 'a'.repeat(40);
function fixture({ stale = 0, busy = 0, permanent = false } = {}) {
  const versions = [], logs = [];
  let checks = 0, creates = 0;
  const args = {
    sourceSha, context: { repo: { owner: 'willchavez', repo: 'willchavez-site-preview' }, runId: 42, runAttempt: 1 },
    core: { getIDToken: async () => 'private-oidc-token', setSecret: () => {}, info: v => logs.push(v), warning: v => logs.push(v), setOutput: () => {} },
    github: { rest: { actions: { listWorkflowRunArtifacts: async () => ({ data: { artifacts: [{ id: 9, name: 'github-pages', expired: false }] } }) } }, request: async (route, params) => {
      if (route.startsWith('POST')) {
        creates++;
        if (permanent) throw Object.assign(new Error('forbidden'), { status: 403 });
        if (creates <= busy) throw Object.assign(new Error('due to in progress deployment'), { status: 400 });
        versions.push(params.pages_build_version);
        assert.equal(params.artifact_id, 9);
        return { data: { id: params.pages_build_version } };
      }
      return { data: { status: 'succeed' } };
    } },
    fetchPublic: async () => ({ ok: true, json: async () => ({ commit: ++checks <= stale ? 'b'.repeat(40) : sourceSha }) }),
    wait: async () => {}, createAttempts: 3, statusAttempts: 2, publicAttempts: 2,
  };
  return { args, versions, logs };
}
test('unique versions across source, workflow retries, and redeployments; secrets stay out of logs', async () => {
  const a = fixture(), b = fixture();b.args.context.runAttempt = 2;
  const first = await publishPreview(a.args), retry = await publishPreview(b.args);
  assert.notEqual(first.version, retry.version);
  assert.equal(first.sourceSha, sourceSha);
  assert.equal(a.logs.some(v => v.includes('private-oidc-token')), false);
});
test('wait for a busy Pages deployment and verify the publicly served source', async () => {
  const f = fixture({ busy: 1, stale: 1 });
  assert.equal((await publishPreview(f.args)).sourceSha, sourceSha);
});
test('a falsely successful deployment gets a fresh version before it can succeed', async () => {
  const f = fixture({ stale: 2 });
  await publishPreview(f.args);
  assert.equal(f.versions.length, 2);
  assert.notEqual(f.versions[0], f.versions[1]);
});
test('never report success when the public marker stays stale', async () => {
  const f = fixture({ stale: 100 });
  await assert.rejects(publishPreview(f.args), /never matched/);
});
test('permission failures fail immediately rather than retrying or cancelling another deployment', async () => {
  const f = fixture({ permanent: true });
  await assert.rejects(publishPreview(f.args), /forbidden/);
  assert.equal(f.versions.length, 0);
});
