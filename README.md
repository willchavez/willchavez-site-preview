# willchavez-site-preview

Review site: https://willchavez.github.io/willchavez-site-preview/

This repository builds a selected ref from `willchavez/willchavez-site` and publishes it to its own GitHub Pages site. It never pushes to the source repository or deploys production.

## Publish a preview

Push proposed changes to a branch in `willchavez/willchavez-site`, then open **Actions → Deploy preview → Run workflow** here. Set `source_ref` to that branch or, preferably, its full commit SHA. From the CLI:

```sh
gh workflow run preview.yml --repo willchavez/willchavez-site-preview -f source_ref=COMMIT_SHA
```

Wait for the workflow to finish, then open the review site. Each deployment replaces the previous preview. `preview-source.json` and the build summary record the source commit. Pushes to this repository's `main` deploy the source repository's `master` as a baseline.

After review and explicit approval, merge the source changes into `master` in `willchavez/willchavez-site`. Its existing workflow publishes production.

## Setup

In **Settings → Pages**, set Source to **GitHub Actions**. Do not set a custom domain. The workflow uses the standard `GITHUB_TOKEN`; it needs no cross-repository write token because the source is public.

The adapter rewrites built navigation and asset paths for the project subdirectory, removes the production `CNAME`, and marks HTML pages `noindex`. Canonical metadata continues to identify production. Preview content is public; `noindex` is a search-engine hint, not access control.
