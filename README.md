# willchavez-site-preview

Review site: https://willchavez.github.io/willchavez-site-preview/

This repository builds a selected ref from `willchavez/willchavez-site` and publishes it to its own GitHub Pages site. It never pushes to the source repository or deploys production.

## Publish a preview

Push proposed changes to a branch in `willchavez/willchavez-site`, then open **Actions → Deploy preview → Run workflow** here. Set `source_ref` to that branch or, preferably, its full commit SHA. From the CLI:

```sh
gh workflow run preview.yml --repo willchavez/willchavez-site-preview -f source_ref=COMMIT_SHA
```

Wait for the workflow to finish, then open the review site. Each deployment replaces the previous preview. `preview-source.json` and the build summary record the source commit. After Pages deploys, the workflow checks that the public marker matches the requested source commit and fails if the old version remains visible. Pushes to this repository's `main` deploy the source repository's `master` as a baseline, except workflow-only and README-only changes. Publish workflow changes with an explicit `source_ref` so they do not replace an active preview with the baseline.

After review and explicit approval, merge the source changes into `master` in `willchavez/willchavez-site`. Its existing workflow publishes production.

## Setup

In **Settings → Pages**, set Source to **GitHub Actions**. Do not set a custom domain. The workflow uses the standard `GITHUB_TOKEN`; it needs no cross-repository write token because the source is public.

The adapter rewrites built navigation and asset paths for the project subdirectory, removes the production `CNAME`, and marks HTML pages `noindex`. Canonical metadata continues to identify production. Preview content is public; `noindex` is a search-engine hint, not access control.

## Build caching

The workflow restores and saves `source/app/.cache/responsive-images` with GitHub Actions Cache. Cache keys include the platform, image encoder implementation and dependency lockfile, and source image bytes. A fallback restores the previous asset set so adding or editing an image only encodes the changed images. The image builder also hashes every source file and encoder version, preventing stale variants when an image is edited under the same name. Deleted sources are omitted from the fresh output.

The first build for a new encoder/dependency key is cold. Copy and style changes reuse the encoded images on subsequent runs; all HTML is still rebuilt and the normal Pages deployment is preserved. Image-cache tests run before publishing.

Measured with the same image set: the [cold run](https://github.com/willchavez/willchavez-site-preview/actions/runs/42538728481) took 6m18s; the following [CSS-only deployment](https://github.com/willchavez/willchavez-site-preview/actions/runs/42539318981) took 47s end to end, with a 9s Build site step and all 270 images reused. Runner availability and changed images can affect future timings.

If Pages temporarily rejects publishing because an earlier deployment is still in progress, rerun only the failed deploy job after it finishes. The existing artifact is reused, and the public-source check verifies that the requested preview actually became visible.

## Verified publishing

The publisher uses GitHub’s Pages deployment API with a unique build version derived from the source SHA, workflow run, run attempt, and publish attempt. Repeated previews no longer share the workflow repository’s commit as their deployment identity. It waits through temporary busy responses and polls deployment status, then checks the public source marker. If Pages reports success while the public source remains stale, it retries once with another unique version. It fails instead of claiming success if the public source never matches.

Publisher regression checks: `node --test scripts/publish-preview.test.cjs`. The tests exercise unique run versions, a busy deployment, stale public output, and permission failures. They do not change production hosting.
