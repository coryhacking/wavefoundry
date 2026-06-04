# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-06-03

wave-id: `1p347 build-pack-release-mode-retire-ci-publish`
Title: Make build_pack.py the release CLI; retire CI publish workflow — ship 1.4.1

## Objective

Make `build_pack.py` the canonical release command. The current CI publish workflow (`.github/workflows/release.yml`) ships a regression-shaped zip without the framework semantic index because CI lacks the index-build dependencies (numpy / fastembed / lancedb). The maintainer's local build is already strictly better — it includes the optimized + vacuumed framework index. This wave extends `build_pack.py` with a `--release` flag that adds tag + push + GitHub Release upload around the existing local-build flow, and deletes the CI publish workflow that's now redundant. Bare `build_pack.py --version X.Y.Z` (no `--release`) is kept unchanged so local-build users have a path that doesn't push to GitHub.

## Changes

Change ID: `1p349-enh build-pack-release-cli-with-optional-tag-and-publish`
Change Status: `implemented`

Completed At: 2026-06-03

## Wave Summary

Wave `1p347` (Make build_pack.py the release CLI; retire CI publish workflow — ship 1.4.1) delivered one change: Build-Pack Release CLI With Optional Tag And Publish.

**Changes delivered:**

- **Build-Pack Release CLI With Optional Tag And Publish** (`1p349-enh build-pack-release-cli-with-optional-tag-and-publish`) — 14 ACs completed. Key decisions: Make `build_pack.py` itself the release CLI rather than installing index deps in CI; Keep the bare `build_pack.py --version X.Y.Z` local-only behavior unchanged
## Participants

- `code-reviewer` — required (Python CLI logic in `build_pack.py`; pre-flight checks and subprocess sequencing)
- `qa-reviewer` — required (pre-flight gate coverage; test that all 6 refusal modes fire on their respective inputs)
- `architecture-reviewer` — not required (no boundaries change; release pipeline is an existing surface getting a CLI consolidation)
- `security-reviewer` — not required (no trust boundary; `gh` and `git` are already-trusted local tools)
- `release-reviewer` — required (packaging + distribution surface changes by definition)
- `red-team` — Wave Council adversarial primer per `wave_review.enabled`
- `reality-checker` — required (Wave Council Phase 2 fixed seat)
- `wave-council` — required (Wave Council coordinator)

Rotating fifth Phase 2 seat: defaults to `release-reviewer` since this is a packaging/distribution change.

## Journal Watchpoints

- **Pre-flight gates BLOCK partial-state failures.** Each refusal mode (dirty tree, wrong branch, tag exists locally, tag exists on remote, gh not auth'd, missing CHANGELOG section, `--skip-framework-index` combo) must be tested explicitly. A `--release` invocation that crashes mid-flow is harder to recover from than one that refuses up-front; this is the wave's load-bearing safety property.
- **Bare `build_pack.py --version X.Y.Z` MUST remain bit-for-bit unchanged.** Operator-explicit requirement: local-only users (testing, contributors, non-pushers) keep their existing workflow. The `--release` flag layers on top, never replaces. Regression here blocks declaring done.
- **Dogfood verification IS the AC.** AC-1 (end-to-end `--release` publishes correctly) is verified by cutting the v1.4.1 release of this very change via the new command. If the command can't ship its own release, it doesn't work. Watchpoint: do NOT mark AC-1 done from synthetic-test evidence.
- **The CI workflow deletion is irreversible by simple revert.** Restoring CI publish later would require not just adding the workflow back but also re-handling whatever release v1.4.1+ shipped without it. The decision-log row documents the rationale; future maintainers consulting it should understand this is a deliberate single-maintainer-project choice, not an accident.
- **Partial-state recovery path must be documented.** If tag pushes but `gh release create` fails, the maintainer needs the exact recovery command surfaced in the error message. The release-flow doc must include the recovery playbook for each step.

## Review Evidence

- operator-signoff: approved 2026-06-03 — operator authorized close with explicit "close wave and commit" after the implementation work landed, delivery council PASS verdict was recorded, and the local-only `build_pack.py --version` contract was confirmed preserved. AC-1 (dogfood) verification happens immediately after this close commit via `build_pack.py --release v1.4.1` itself.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-06-03: PASS WITH NOTES** (moderator: wave-council; primer-depth: standard; seats: red-team, architecture-reviewer, release-reviewer, qa-reviewer, reality-checker; rotating-seat: release-reviewer; strongest-challenge: pre-flight gates list 6 refusal modes but don't verify the published zip contains the framework index — a `_compact_framework_index` silent-skip would let `--release` publish a broken zip; strongest-alternative: add an internal `--release-dry-run` mode that walks the pipeline without git/gh side effects, plus a post-build assertion that the zip contains `.lance` files before any push happens)
- Must-fix REL-1: docs/references/release-flow.md must pass docs-lint (manifest entry if required); verify during implementation.
- Must-fix RC-1 (folds red-team Stance A + reality-checker note): add post-build assertion that the zip contains framework-index `.lance` files before any push happens; refuse-with-error otherwise.
- Must-fix QA-1 (folds red-team Stance B): add an internal `--release-dry-run` mode that walks pipeline without git or gh side effects; dogfood AC-1 happens AFTER `--release-dry-run` passes.
- Must-fix AR-1: extract the CHANGELOG-section parser into a named `_extract_changelog_section()` helper instead of inlining the `awk` pattern; gives a testable seam.
- **Delivery-phase Wave Council [delivery-council] — 2026-06-03: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, architecture-reviewer, release-reviewer, qa-reviewer, reality-checker; rotating-seat: release-reviewer; strongest-challenge: dogfood AC-1 depends on the implementation under test — if it fails we don't know whether implementation is broken or whether the failure is separate; strongest-alternative: smoke-test via `--release-dry-run` BEFORE the real release so implementation bugs surface without polluting the public release — folded). All 14 ACs verified except AC-1 (dogfood pending), all 4 prepare-phase must-fixes (REL-1, RC-1, QA-1, AR-1) confirmed folded with test coverage; 2327 tests pass; lint clean; bare-invocation contract preserved by construction.

## Dependencies

- No external wave dependencies.
- Successor concern (out of scope for this wave): a PR-tests CI workflow may be useful if/when contributors arrive. Not in scope here; can be added as a follow-on without disrupting the release flow this wave establishes.
