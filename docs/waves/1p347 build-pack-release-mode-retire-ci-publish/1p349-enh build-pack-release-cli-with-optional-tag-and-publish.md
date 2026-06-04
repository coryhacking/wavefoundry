# Build-Pack Release CLI With Optional Tag And Publish

Change ID: `1p349-enh build-pack-release-cli-with-optional-tag-and-publish`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-03
Wave: `1p347 build-pack-release-mode-retire-ci-publish`

## Rationale

The current release flow has two cooperating pieces:

1. **`build_pack.py --version X.Y.Z`** — produces a local distribution zip with an optimized + vacuumed framework index (compaction already runs as part of `_compact_framework_index` at line 276 of `build_pack.py`).
2. **`.github/workflows/release.yml`** — fires on `git push origin v*.*.*`, rebuilds the zip in CI (without the framework index, since CI doesn't have numpy/fastembed installed), and publishes it as a GitHub Release asset.

The CI publish step has two real problems:

- **The shipped zip lacks the pre-built framework index** because CI uses `--skip-framework-index`. Consumers download a zip without semantic embeddings; first `docs_search` against framework seeds triggers a from-scratch local rebuild (~5–15 min including BGE model download). This is friction the maintainer's local zip didn't have.
- **The CI flow contributes nothing the maintainer's machine couldn't.** Wavefoundry is a solo-maintainer project; the CI step duplicates the work `build_pack.py` already does, then ships a *worse* artifact (no index).

The cleanest answer is to make `build_pack.py` itself the official release CLI: extend it with a `--release` flag that performs the same local build (always with the optimized framework index) AND handles tag + push + GitHub Release upload in one transaction. The bare `build_pack.py --version X.Y.Z` keeps its current local-only behavior unchanged, so contributors and local-build users keep their workflow.

The CI release workflow becomes redundant under this model; it is retired.

## Requirements

1. **`build_pack.py --release` flag added.** When set, after the local build completes successfully, `build_pack.py`:
   - Verifies the working tree is clean (no uncommitted changes) and the current branch is `main`
   - Verifies a tag `v<version>` does not already exist locally or on the configured `origin` remote
   - Verifies `gh auth status` succeeds (GitHub CLI authenticated)
   - Creates an annotated tag `v<version>` with a message of the form `"Wave <id>: <prev-version> → <version>"` derived from the most recent wave-close commit, OR a default `"Release v<version>"` if no recent wave can be inferred
   - Pushes the tag to `origin`
   - Extracts the `## [<version>]` section from `CHANGELOG.md` for release notes
   - Calls `gh release create v<version> --title "<version>" --notes-file <extracted> ./dist/wavefoundry-<version>.zip` (uploads the local zip directly; no CI rebuild)
   - On any step failure, surfaces the error clearly and exits non-zero without leaving partial state where avoidable (e.g., if tag push fails, leave the local tag in place; if release create fails, leave the tag pushed and report)

2. **`build_pack.py --version X.Y.Z` (no `--release`) is unchanged.** The bare invocation continues to:
   - Build a local zip under `~/.wavefoundry/dist/` (or `--output DIR`)
   - Optimize + vacuum the framework index via `_compact_framework_index`
   - Stamp VERSION with the new build suffix
   - Take no git or GitHub action
   This is the "build for myself / build for testing / build without pushing to GitHub" path that contributors and local-build users rely on. Operator direction: keep this option.

3. **Pre-flight checks in `--release` mode are explicit and conservative.**
   - Working tree clean: refuse if any tracked file is modified. Uncommitted work is a sign the release isn't ready.
   - On `main` branch: refuse on any other branch — release flow assumes main-branch trunk.
   - Tag doesn't exist: refuse if `v<version>` already exists locally or on `origin` — same-version repackages must explicitly delete the old tag first.
   - `gh` authenticated: refuse if `gh auth status` fails — the upload would fail anyway, fail fast.

4. **CHANGELOG release-notes extraction.** Use the same `awk` pattern that the retired CI workflow used: extract from `## [<version>]` to the next `## [` heading. Write to a temp file passed to `gh release create --notes-file`. If the section is absent, refuse with a clear error pointing the maintainer at CHANGELOG.

5. **The `.github/workflows/release.yml` workflow is deleted.** No CI-triggered release publishing. The repo keeps the existing v1.4.0 release as-is; future releases come from `build_pack.py --release` exclusively.

6. **No new CI workflow added in this change.** A separate test/lint CI workflow may be useful at some point, but is out of scope here. The scope is "make the release flow correct"; CI for PRs is a follow-on if/when the project takes on contributors.

7. **`build_pack.py --skip-framework-index` flag remains available** for emergency local builds when index dependencies (numpy / fastembed / lancedb) aren't available, but is NOT compatible with `--release` — combining them would publish a zip without the framework index, which is the regression this change exists to fix. Mutual-exclusion check raises a clear error.

8. **Documentation updates.** `docs/references/dashboard-install-upgrade.md` or a new `docs/references/release-flow.md` documents the new release command. The doc is operator-facing (how-to-ship), not developer-facing.

## Scope

**Problem statement:** The current release flow ships a zip without the pre-built framework index because CI lacks the index-build dependencies. The maintainer's locally-built zip is a strictly better artifact than what CI publishes. The cleanest fix is to make `build_pack.py` itself the release CLI and retire the CI publish step.

**In scope:**

- Add `--release` flag to `build_pack.py` with pre-flight checks, tag creation, tag push, CHANGELOG extraction, and GitHub Release upload
- Delete `.github/workflows/release.yml`
- Add operator-facing release-flow documentation
- Verify the new flow end-to-end by cutting a 1.4.1 release of this change itself (dogfood)

**Out of scope:**

- Adding a new PR-tests CI workflow (separate change if/when needed)
- Changing `build_pack.py`'s existing local-build behavior
- Any change to how the framework index is built or compacted (`_compact_framework_index` is already correct)
- Multi-author release authorization (single-maintainer project)
- Retroactively re-publishing v1.4.0 with the index (it'd require deleting and re-creating the release; if desired, maintainer can do so manually with `gh release upload v1.4.0 --clobber` after building locally)

## Acceptance Criteria

- [x] AC-1: `build_pack.py --version 1.4.1 --release` end-to-end produces a published GitHub Release at `v1.4.1` with the locally-built zip attached (containing the framework index), tagged from main, with release notes extracted from CHANGELOG.
- [x] AC-2: `build_pack.py --version 1.4.1` (no `--release`) behaves exactly as it does today — local zip only, no git or GitHub side effects.
- [x] AC-3: `--release` refuses with a clear error when the working tree is dirty (test: modify a file, attempt release).
- [x] AC-4: `--release` refuses when on a non-main branch (test: checkout temp branch, attempt release).
- [x] AC-5: `--release` refuses when the target tag already exists locally (test: create tag, attempt release).
- [x] AC-6: `--release` refuses when the target tag already exists on `origin` (test: simulate by pushing a tag then attempting release with same version).
- [x] AC-7: `--release` refuses when `gh auth status` is failing.
- [x] AC-8: `--release` refuses when CHANGELOG.md does not contain a `## [<version>]` section for the requested version.
- [x] AC-9: `--release` combined with `--skip-framework-index` refuses with a clear error explaining the incompatibility.
- [x] AC-10: `.github/workflows/release.yml` is deleted; no workflow fires on tag push anymore.
- [x] AC-11: Operator-facing release-flow doc added (under `docs/references/`) explaining the new command, the pre-flight checks, and the recovery path if a step fails partway.
- [x] AC-12: Full framework test suite passes after all edits (regression discipline).
- [x] AC-13: docs-lint passes after all edits.
- [x] AC-14: CHANGELOG 1.4.1 entry describes the new release flow (Fixed: index-in-published-zip; Changed: build_pack is the release CLI; Removed: CI publish workflow).

## Tasks

- [x] Open `framework_edit_allowed` gate (covers `build_pack.py` + the workflow deletion + docs edits)
- [x] Implement `--release` flag in `build_pack.py` with all pre-flight checks
- [x] Implement the CHANGELOG section extraction helper (inline; reusable)
- [x] Implement the tag derivation (parse most recent wave-close commit message, fallback to default)
- [x] Implement the tag creation, push, and `gh release create` sequence with clear error reporting on each step
- [x] Add the mutual-exclusion check for `--release` + `--skip-framework-index`
- [x] Delete `.github/workflows/release.yml`
- [x] Write `docs/references/release-flow.md` (new) with the release command, pre-flight gates, and recovery notes
- [x] Add CHANGELOG 1.4.1 entry
- [x] Run framework test suite
- [x] Run `wave_validate` / `wave_audit`
- [x] Dogfood: cut a 1.4.1 release of this very change via `build_pack.py --release` end-to-end to verify it works
- [x] Close gate; mark change `implemented`

## Affected Architecture Docs

`N/A` — this change extends `build_pack.py`'s CLI surface with a release-time orchestration mode and deletes a CI workflow. No module boundaries change. No new components. The framework's data-and-control-flow is unaffected; only the release pipeline shape changes.

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 (end-to-end `--release` publishes correctly) | required | Core happy-path verification. |
| AC-2 (bare invocation unchanged) | required | Operator-explicit requirement: keep the local-only option for non-pushers. |
| AC-3 (refuses on dirty tree) | required | Uncommitted work is a signal the release isn't ready. |
| AC-4 (refuses on non-main branch) | required | Releases must come from trunk. |
| AC-5 (refuses on existing local tag) | required | Same-version repackages must be explicit. |
| AC-6 (refuses on existing remote tag) | required | Prevents publishing a duplicate Release with wrong asset. |
| AC-7 (refuses on unauthenticated gh) | required | Fail-fast; the `gh release create` step would fail anyway. |
| AC-8 (refuses when CHANGELOG section missing) | required | Releases without notes are operator-hostile. |
| AC-9 (mutex with `--skip-framework-index`) | required | Prevents publishing a regression-shaped zip (no index). |
| AC-10 (CI workflow deleted) | required | Eliminates the duplicate-build path that motivated this change. |
| AC-11 (operator docs) | required | Without this, the release flow is a tribal-knowledge step. |
| AC-12 (test suite passes) | required | Regression discipline. |
| AC-13 (docs-lint passes) | required | Standard hygiene. |
| AC-14 (CHANGELOG entry) | required | Release-notes discoverability. |

All ACs required. No nice-to-have items — every gate either prevents a real release-bug or unblocks documented usage.

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-06-03 | Make `build_pack.py` itself the release CLI rather than installing index deps in CI | Operator preference: no ongoing CI compute cost. Single-maintainer project, so a maintainer-local release pipeline is sufficient. The CI rebuild was contributing nothing the maintainer's machine couldn't. | Install numpy/fastembed in CI and drop `--skip-framework-index` — rejected per operator on time/compute grounds. Commit the framework index to git — rejected earlier (contradicts existing gitignore policy and introduces binary churn). |
| 2026-06-03 | Keep the bare `build_pack.py --version X.Y.Z` local-only behavior unchanged | Operator-explicit requirement: local-build users (testing, contributors, non-pushers) keep their existing workflow. The `--release` flag layers ON TOP, doesn't replace. | Make `--release` default-on — rejected; would break local-only users. |
| 2026-06-03 | `--release` + `--skip-framework-index` are mutually exclusive | The whole point of this change is to ship the framework index; combining them would publish the same regression-shape zip that CI was producing. Mutex is a small gate that prevents a real footgun. | Allow the combination with a warning — rejected; warnings are easy to ignore. |
| 2026-06-03 | Delete `release.yml` rather than repurpose it | The workflow's job (build + publish) is now done by `build_pack.py --release` on the maintainer's machine. Leaving it as a no-op or a tests-only workflow is scope creep; a future PR-tests workflow can be added cleanly later. | Repurpose to PR-tests-only — rejected as scope creep; the file's commit history would imply continuity that doesn't exist. |
| 2026-06-03 | Refuse `--release` if `gh auth status` fails (rather than discover the failure mid-flow) | Fail-fast is more operator-friendly. The release would fail at the `gh release create` step regardless; pre-flight just surfaces it before any tag is created. | Discover lazily — rejected; partial state (tag pushed but release create failed) is harder to recover from than refuse-up-front. |

## Risks

| Risk | Mitigation |
|---|---|
| Maintainer runs `--release` on a machine without `numpy`/`fastembed`/`lancedb` installed, and the framework index build fails | `_compact_framework_index` raises a clear error today. The new `--release` path adds nothing to that error mode — if local index build fails, the release fails before tag/push. Future improvement could check deps in pre-flight, but it's out of scope. |
| Partial-state recovery: tag pushed but `gh release create` failed | The error message names the exact recovery command: `gh release create v<version> --notes-file <path> ./dist/<zip>` (the maintainer can re-run that step manually). Document in the release-flow doc. |
| `--release` succeeds but the CHANGELOG section was wrong (e.g., maintainer forgot to add the 1.4.1 entry, used a stale 1.4.0 section by mistake) | AC-8 refuses if the requested-version section is absent. Once the section exists with any content, this change doesn't validate its accuracy — that's the maintainer's responsibility, same as today. |
| Future contributor expects CI to publish releases | Documentation is the answer. The release-flow doc states explicitly that releases come from the maintainer's machine, not CI. |
| The tag-derivation logic (parse most recent wave-close commit message) gets a parse it can't handle | Fall back to a default tag message `"Release v<version>"`. Don't fail the release because of cosmetic-message issues. |
| Race: another maintainer pushes a tag between pre-flight check and `git push origin v<version>` | Acknowledged as a known limitation for a hypothetical multi-maintainer future; not a concern today. |

## Related Work

- **1p337 / 1p33i** — established the release zip is the operator-facing surface; this change closes the gap between local-built and CI-built artifacts by making local the canonical path.
- **`build_pack.py` `_compact_framework_index`** — already does the optimize + vacuum work; this change extends the surrounding orchestration, not the core packaging logic.
- **Existing `.github/workflows/release.yml`** — replaced by `build_pack.py --release`; deleted in this change.
- **Foreshadowed: a PR-tests CI workflow** — out of scope here, may be added in a future wave when/if contributors arrive.

## Session Handoff

Admitted to `1p347` immediately after authoring. Sequenced as the single change in the wave. Dogfooded by cutting v1.4.1 via the new `--release` command at the close of the wave — that release IS the verification of AC-1.
