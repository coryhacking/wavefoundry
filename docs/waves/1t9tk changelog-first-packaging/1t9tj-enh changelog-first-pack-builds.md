# Changelog-First Pack Builds

Change ID: `1t9tj-enh changelog-first-pack-builds`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-07-22
Wave: `1t9tk changelog-first-packaging`

## Rationale

Operator directive after the 1.14.0 release: the published zip's internal `CHANGELOG.md` was one revision behind the repo's, because the release-notes bullets for the last field-fix waves were written AFTER the field-tested pack was built, and the tested zip was shipped as-is (ship-what-you-tested). The release preflight (`build_pack.py --release`) already requires a matching `## [version]` changelog section, but the plain `--version` build path — the one every test build and the shipped 1.14.0 build actually used — has no changelog requirement at all, so nothing forces the entry to exist before packs start circulating.

## Requirements

1. **Every versioned build requires its changelog entry:** `build_pack.py --version X.Y.Z` fails before any stamping or zip write when root `CHANGELOG.md` has no `## [X.Y.Z]` section, with a message that says to create the entry first. The existing `_extract_changelog_section` is the single detection authority (no second parser).
2. **Fail before side effects:** the check runs in the pre-flight region — before `VERSION` stamping, manifest revision update, and zip creation — so a refused build leaves the tree untouched.
3. **Release path unchanged:** `--release` keeps its existing stricter preflight; the new check must not double-report or change `--release` semantics.
4. **Process rule recorded where the operator reads it:** `docs/prompts/package-wavefoundry.prompt.md` states that the changelog entry for the target version must exist before any build (now mechanically enforced) and must be COMPLETE before the final field-test build; any changelog amendment after a build requires a rebuild before publishing, so a released zip never carries a stale internal changelog; publishes should prefer `--release`, which rebuilds fresh from the clean tree after the preflight.
5. **Hermetic tests:** a versioned build against a changelog without the section fails with the create-the-entry-first message and writes nothing; the same build succeeds once the section exists; `--release`-path behavior is untouched.

## Scope

**Problem statement:** the plain build path lets packs ship before their changelog entry exists or is current, so the archive's only offline release surface can be stale.

**In scope:**

- `build_pack.py` (pre-flight changelog-section requirement on the plain build path)
- `tests/test_build_pack.py` additions
- `docs/prompts/package-wavefoundry.prompt.md` (ordering + rebuild-after-amendment rule)

**Out of scope:**

- Enforcing changelog COMPLETENESS mechanically (not decidable; the prompt carries the procedural rule)
- Changing `--release` orchestration or the ship-what-you-tested tradeoff policy
- Seed changes (the packaging prompt is repo-local to the framework source repository; no seed renders it)

## Acceptance Criteria

- [x] AC-1: `build_pack.py --version X.Y.Z` with no `## [X.Y.Z]` changelog section exits non-zero before stamping VERSION or writing a zip, and the message instructs creating the entry first.
- [x] AC-2: the identical invocation succeeds once the section exists; `--release` preflight behavior is unchanged.
- [x] AC-3: the packaging prompt carries the changelog-first and rebuild-after-amendment rules; docs lint passes.
- [x] AC-4: full framework test suite passes.

## Tasks

- [x] Add the changelog-section pre-flight to the plain build path in `build_pack.py`.
- [x] Hermetic tests for refusal (no side effects) and success; release-path guard test.
- [x] Update `docs/prompts/package-wavefoundry.prompt.md`.
- [x] Full suite + docs gate.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| preflight | implementer | — | Single check in build_pack main |
| docs | implementer | preflight | Prompt ordering text |

## Serialization Points

- None.

## Affected Architecture Docs

N/A: build-tool pre-flight and operator-prompt ordering only; `docs/contributing/build-and-verification.md` already documents `--release` preflight semantics and gains no contract change.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The mechanical enforcement the operator asked for. |
| AC-2 | required | Must not break test builds or the release path. |
| AC-3 | required | The completeness half of the rule is procedural and must be written down. |
| AC-4 | required | Standard gate. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-22 | Drafted from the operator's post-release directive; verified the asymmetry at source: `--release` preflights the `## [version]` section (build_pack.py main, release path) while the plain `--version` path never consults the changelog beyond copying it into the zip. | code_keyword census of CHANGELOG in build_pack.py; package-wavefoundry.prompt.md steps 4-7 |
| 2026-07-22 | Implemented: the plain build path's pre-flight refuses without the `## [version]` section (else-branch of the release preflight, before the docs gate, before any stamping), message says to create the entry first; four tests added (refusal with side-effect assertions, missing-file refusal, success-once-present, release-path source pin); packaging prompt now carries the mechanical-enforcement note plus the completeness and rebuild-after-amendment rules with a preference for --release on publishes. Module 101 OK; known-bad probe (guard vacuously satisfied = pre-fix plain path) flipped both refusal tests. | test_build_pack.py changelog-first block; probe output |
| 2026-07-22 | AC-4 met: full framework suite 6,122/6,122 OK on the final tree; docs lint clean. | run_tests.py output |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-22 | Hard fail with a create-the-entry-first message; no bypass flag. | The entry skeleton costs a minute and the guard exists precisely to force it; a bypass flag re-opens the gap. | Warning-only (ignorable, would not have changed 1.14.0); a completeness check (not mechanically decidable). |
| 2026-07-22 | Prompt-level rule for completeness and rebuild-after-amendment. | Only the operator can judge completeness; the rebuild rule keeps ship-what-you-tested honest because a rebuild after a docs-only changelog amendment differs from the tested zip only in the changelog. | Comparing zip-internal changelog at release time (no owned release step exists outside `--release` to hook). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| The guard blocks a legitimate emergency rebuild. | The failure message names the exact one-line remedy; `--release` already demanded the section, so no supported flow regresses. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
