# Release Flow — Wavefoundry

Owner: Engineering
Status: active
Last verified: 2026-06-03

How Wavefoundry ships a release. Single-maintainer project; the release happens from the maintainer's machine via `build_pack.py --release`.

## The release command

```bash
python3 .wavefoundry/framework/scripts/build_pack.py --version <X.Y.Z> --release
```

What it does in order:

1. **Pre-flight refusals** (cheap, before any build):
   - working tree must be clean
   - on `main` branch
   - `vX.Y.Z` tag must not exist locally or on `origin`
   - `gh auth status` must succeed
   - `CHANGELOG.md` must contain a `## [X.Y.Z]` section
2. **Build** the distribution zip (same as a normal `build_pack.py --version X.Y.Z` invocation) — runs the docs gate, builds + optimizes + vacuums the framework semantic index via `_compact_framework_index`, stamps `VERSION`, writes `INSTALL.md`, produces `~/.wavefoundry/dist/wavefoundry-X.Y.Z.<build-suffix>.zip`.
3. **Post-build assertion**: zip must contain framework-index `.lance` files. Halts before any side effects if missing.
4. **Tag** the current `HEAD` with `vX.Y.Z`. Annotation message is derived from the most recent wave-close commit subject (e.g., `Close wave 1p347 and ship 1.4.0 → 1.4.1`), or `Release vX.Y.Z` as a fallback.
5. **Push** the tag to `origin`.
6. **Publish** a GitHub Release via `gh release create vX.Y.Z`. Title is the bare version. Notes are extracted from the `## [X.Y.Z]` section of `CHANGELOG.md`. The local zip is uploaded as the release asset.

## The non-release option (testing, local-only)

```bash
python3 .wavefoundry/framework/scripts/build_pack.py --version <X.Y.Z>
```

Bare invocation (no `--release`) builds the zip locally and exits without any git or GitHub side effects. This is the path for testing, contributor builds, or any time you want a packaged framework without publishing it.

## Smoke-testing the release pipeline

To walk the entire `--release` flow without producing any side effects (no tag, no push, no upload):

```bash
python3 .wavefoundry/framework/scripts/build_pack.py --version <X.Y.Z> --release-dry-run
```

This validates pre-flight checks, builds the zip, runs the post-build assertion, and prints the `git`/`gh` commands that *would* execute. Use this before a real `--release` if the pipeline has changed or if you want a low-risk verification.

## Incompatibilities

- `--release` + `--skip-framework-index` is refused. The whole point of `--release` is to ship the framework index that CI cannot build; combining them would publish the exact regression-shape zip the flag exists to prevent.

## Recovery — when a step fails partway

Each step prints a recovery command in its error message. Common cases:

- **Tag pushed but `gh release create` failed.** The tag is on `origin`; only step 3 remains. Re-run the upload manually:
  ```bash
  gh release create v<X.Y.Z> --title <X.Y.Z> \
    --notes-file <(awk '/^## \[<X.Y.Z>\]/{flag=1;next} /^## \[/{flag=0} flag' CHANGELOG.md) \
    ~/.wavefoundry/dist/wavefoundry-<X.Y.Z>.<build-suffix>.zip
  ```
  Or, if the wrong tag was pushed, delete it on both sides (`git push origin :refs/tags/v<X.Y.Z>` and `git tag -d v<X.Y.Z>`) and re-run `build_pack.py --release`.
- **`gh auth status` failed during pre-flight.** Sign in with `gh auth login`, or `gh auth switch -u <username>` if multiple accounts are configured.
- **Working tree dirty.** Commit or stash before re-running `--release`. Uncommitted changes are a signal that the release isn't ready.

## CI

There is no CI workflow that publishes releases. The release happens entirely on the maintainer's machine via `build_pack.py --release`. CI (when it exists for PR-tests) is scoped to running tests + lint on PRs and pushes; it has no role in publishing.

The historical `.github/workflows/release.yml` workflow was removed in wave `1p347` because it shipped a strictly worse artifact (no framework index, since CI lacked `numpy`/`fastembed`/`lancedb`). The maintainer's local build was always the better artifact; `--release` makes it the official one.
