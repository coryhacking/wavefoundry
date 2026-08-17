# Release Flow — Wavefoundry

Owner: Engineering
Status: active
Last verified: 2026-08-16

How Wavefoundry ships a release. Single-maintainer project; the release happens from the maintainer's machine via `build_pack.py --release`.

## The release command

```bash
python3 .wavefoundry/framework/scripts/build_pack.py --version <X.Y.Z> --release --with-models
```

What it does in order:

1. **Pre-flight refusals** (cheap, before any build):
   - working tree must be clean
   - on `main` branch
   - `vX.Y.Z` tag must not exist locally or on `origin`
   - `gh auth status` must succeed
   - `CHANGELOG.md` must contain a `## [X.Y.Z]` section
2. **Build** the source distribution and matching model companion — runs the docs gate, stamps `.wavefoundry/framework/VERSION`, writes `INSTALL.md`, produces `~/.wavefoundry/dist/wavefoundry-X.Y.Z.<build-suffix>.zip`, and builds the declared model companion (`wavefoundry-models-<MODEL_SET_VERSION>.zip`, set 3 from the release after 1.17.0) from the warmed local cache (a pre-existing companion zip is never reused); the cache must match the canonical model-set manifest byte for byte, with `refs/main` files compared in their normalized 40-byte form. The feature pack ships framework **source only**; the separate companion carries pinned offline model artifacts, not a semantic index.
3. **Commit the stamp**: the VERSION/manifest/README-badge changes the build made are committed automatically (`git add -A && git commit`) so the tag points at the stamped tree.
4. **Tag** the stamp commit locally with `vX.Y.Z`. Annotation message is derived from the most recent wave-close commit subject (e.g., `Close wave 1p347 and ship 1.4.0 → 1.4.1`), or `Release vX.Y.Z` as a fallback.
5. **Push main**: `HEAD` is pushed to `origin/main` (the stamp commit lands on the default branch).
6. **Push the tag** to `origin`.
7. **Publish** a GitHub Release via `gh release create vX.Y.Z`. Title is the bare version. Notes are assembled by prepending `.wavefoundry/framework/install/install-block.md` to the matching `CHANGELOG.md` section. Both the exact feature archive and matching model companion are uploaded; the release receipt names both assets.

## The non-release option (testing, local-only)

```bash
python3 .wavefoundry/framework/scripts/build_pack.py --version <X.Y.Z>
```

Bare invocation (no `--release`) builds the feature zip locally and exits without any git or GitHub side effects. Add `--with-models` when a local companion is needed. Model assets remain optional only on this non-release path.

## Smoke-testing the release pipeline

To walk the entire `--release` flow without git or remote release mutations (no commit, no tag, no push, no upload) — note the LOCAL build still runs, producing the archive and stamping VERSION/manifest/README (the working tree is left dirty; restore the stamped files afterwards):

```bash
python3 .wavefoundry/framework/scripts/build_pack.py --version <X.Y.Z> --release-dry-run --with-models
```

This validates pre-flight checks, builds and verifies both assets, and prints the `git`/`gh` commands that *would* execute. Release and release-dry-run reject missing `--with-models` before build work.

## Recovery — when a step fails partway

Each step prints a recovery command in its error message. Common cases:

- **Tag pushed but `gh release create` failed.** The tag is on `origin`; only the publish step (step 7) remains. Re-run the upload manually:
  ```bash
  gh release create v<X.Y.Z> --title <X.Y.Z> \
    --notes-file <(awk '/^## \[<X.Y.Z>\]/{flag=1;next} /^## \[/{flag=0} flag' CHANGELOG.md) \
    ~/.wavefoundry/dist/wavefoundry-<X.Y.Z>.<build-suffix>.zip \
    ~/.wavefoundry/dist/wavefoundry-models-<MODEL_SET_VERSION>.zip
  ```
  Or, if the wrong tag was pushed, delete it on both sides (`git push origin :refs/tags/v<X.Y.Z>` and `git tag -d v<X.Y.Z>`) and re-run `build_pack.py --release`.
- **`gh auth status` failed during pre-flight.** Sign in with `gh auth login`, or `gh auth switch -u <username>` if multiple accounts are configured.
- **Working tree dirty.** Commit or stash before re-running `--release`. Uncommitted changes are a signal that the release isn't ready.

## CI

There is no CI workflow that publishes releases. The release happens entirely on the maintainer's machine via `build_pack.py --release`. CI (when it exists for PR-tests) is scoped to running tests + lint on PRs and pushes; it has no role in publishing.

The historical `.github/workflows/release.yml` workflow was removed in wave `1p347`. The maintainer's local build is the canonical release artifact; `--release` makes it the official one.
