# Flatten CHANGELOG to single source of truth at repo root

Change ID: `1p3i6-enh flatten-changelog-single-source`
Change Status: `implemented`
Owner: framework-maintainer
Status: implemented
Last verified: 2026-06-05
Wave: 1p3dk framework-drift-convergence

## Rationale

The repo carried two hand-maintained release-history files: root `CHANGELOG.md` (Keep-a-Changelog, used by `build_pack.py --release` to extract GitHub Release notes) and `.wavefoundry/CHANGELOG.md` (narrative-prose, bundled into the pack zip and shipped to consumers on upgrade). Wave `131at` (2026-06-01) declared the vendored file canonical and rejected dual sources of truth. In practice the opposite happened — every entry added across 1.4.x and 1.5.0 went into root only; the vendored file stuck at 1.3.31. The duplication is exactly the wave `1p3dk` meta-recommendation pattern ("no dual-valid states") expressed in the repo's own filesystem.

This change flips canonical to root `CHANGELOG.md` and teaches `build_pack.py` to copy root → pack at zip-build time, so consumers still receive an in-tree changelog on upgrade (offline-readable, MCP-indexable, `code_keyword`/`docs_search` findable) but the wavefoundry repo only edits one file. The narrative-prose format diagnostic in `build_pack.py` becomes obsolete (root is Keep-a-Changelog by convention; section headers are self-disciplining) and is removed along with its `--skip-changelog-diagnostic` CLI flag.

## Requirements

1. `build_pack.py` sources `.wavefoundry/CHANGELOG.md` in the pack zip from root `CHANGELOG.md` instead of `.wavefoundry/CHANGELOG.md`. Pack-zip layout (consumer's tree post-unzip) is unchanged.
2. `check_changelog_format()` function, its call site, and the `--skip-changelog-diagnostic` CLI flag are removed from `build_pack.py`.
3. `.wavefoundry/CHANGELOG.md` is deleted from the wavefoundry repo. Root `CHANGELOG.md` is the single source of truth.
4. `seed-240` (Package Wavefoundry prompt) is updated to reflect the new flow — root is canonical, Keep-a-Changelog format, no narrative-prose diagnostic, stale RELEASE_NOTES.md migration note removed.
5. Existing build-pack tests continue to pass; the `test_wavefoundry_changelog_included_in_pack` assertion still succeeds because the file is still in the zip (now sourced from root).
6. `build_pack.py --release` flow continues to extract GitHub Release notes from root `CHANGELOG.md` (unchanged — it already used root).

## Scope

**Problem statement:** Two release-history files, both hand-maintained, drift apart in practice. Wave `131at`'s "vendored is canonical" decision is contradicted by ~6 months of editing habit; operator preference is to consolidate at root and distribute to consumers via the pack at zip-build time.

**In scope:**

- `build_pack.py` source-path flip + diagnostic removal + CLI flag removal
- `.wavefoundry/CHANGELOG.md` deletion from the wavefoundry repo
- `seed-240` rewrite of step 4, options table, zip layout section, removal of stale RELEASE_NOTES.md migration note
- CHANGELOG entry documenting the flip

**Out of scope:**

- Backfilling 1.4.x / 1.5.0 entries into a vendored narrative-prose format — root carries the canonical history in Keep-a-Changelog form and consumers receive that form
- Migration helper for consumers whose previous vendored `.wavefoundry/CHANGELOG.md` was hand-edited — by `131at` design the consumer copy is wavefoundry-managed and overwritten on upgrade; no migration needed
- Reversing wave `131at`'s journal entry — superseded-by note in the new `[1.5.0]` CHANGELOG bullet is sufficient

## Acceptance Criteria

- [x] AC-1: `build_pack.py` no longer defines `check_changelog_format()`; grep returns zero hits in the script.
- [x] AC-2: `build_pack.py` no longer exposes `--skip-changelog-diagnostic`; `--help` output omits the flag.
- [x] AC-3: A pack built from the current repo contains `.wavefoundry/CHANGELOG.md` whose content is byte-equal to repo-root `CHANGELOG.md`. (Verified against `wavefoundry-1.5.0.p3ib.zip`: `diff <(unzip -p ... .wavefoundry/CHANGELOG.md) CHANGELOG.md` returns clean; 39642 bytes.)
- [x] AC-4: `.wavefoundry/CHANGELOG.md` does not exist in the wavefoundry repo working tree.
- [x] AC-5: Operator-facing CHANGELOG guidance is updated to Keep-a-Changelog framing. (Originally landed as a seed-240 step 4 rewrite; subsequently the seed was deleted by 1p3i9 and the same guidance is now carried by `docs/prompts/package-wavefoundry.prompt.md`. AC intent satisfied; the surface that carries the guidance moved.)
- [x] AC-6: `python3 .wavefoundry/framework/scripts/run_tests.py` passes (2640 tests).
- [x] AC-7: `docs-lint` returns clean (`exit 0`, no errors).

## Tasks

- [x] Edit `build_pack.py`: delete `check_changelog_format()` function (lines 324-383).
- [x] Edit `build_pack.py`: delete `--skip-changelog-diagnostic` CLI flag (lines 910-917).
- [x] Edit `build_pack.py`: delete the `check_changelog_format()` call site (lines 1028-1030).
- [x] Edit `build_pack.py`: flip the pack-zip changelog source path from `fw.parent / "CHANGELOG.md"` to `repo_root / "CHANGELOG.md"` (lines 789-796), update the surrounding comment to explain the indirection.
- [x] Edit `seed-240`: rewrite step 4 (Keep-a-Changelog format, root is canonical), update options table (drop `--skip-changelog-diagnostic`), update Zip Layout section, remove stale pre-relocation RELEASE_NOTES.md migration note. (Subsequently superseded by 1p3i9 which deleted the seed entirely; Keep-a-Changelog guidance now lives in `docs/prompts/package-wavefoundry.prompt.md`.)
- [x] Delete `.wavefoundry/CHANGELOG.md` via `git rm`.
- [x] Run framework tests: `python3 .wavefoundry/framework/scripts/run_tests.py`. (2640 tests pass.)
- [x] Run docs-lint and resolve any drift.
- [x] Add bullet under root CHANGELOG `[1.5.0]` documenting this flip and the supersession of `131at`'s vendored-canonical design.

## Agent Execution Graph


| Workstream                | Owner               | Depends On | Notes |
| ------------------------- | ------------------- | ---------- | ----- |
| build_pack.py flip        | framework-maintainer | —          | Source-path flip + diagnostic deletion. |
| seed-240 rewrite          | framework-maintainer | —          | Independent of script edit. |
| Delete vendored CHANGELOG | framework-maintainer | build_pack.py flip | Must flip first so packs source from root, then delete the vendored copy. |
| Verification              | framework-maintainer | All above  | Tests + docs-lint + pack-build smoke. |


## Serialization Points

- `build_pack.py` is touched by 4 separate Edit operations on the same file — serialize the edits within that file.

## Affected Architecture Docs

N/A — change is confined to the packaging workflow (single script + single seed). No domain map / layering / cross-cutting impact.

## AC Priority


| AC   | Priority      | Rationale |
| ---- | ------------- | --------- |
| AC-1 | required      | Function must be gone to eliminate the diagnostic surface. |
| AC-2 | required      | CLI flag must be gone to keep the help output clean and avoid misleading operator-facing surface. |
| AC-3 | required      | The core contract of this change — consumers must continue to receive an in-tree changelog. |
| AC-4 | required      | The duplication removal is the user-facing outcome. |
| AC-5 | required      | Seed-first doc workflow; consumers pick this up on upgrade. |
| AC-6 | required      | No regressions in the existing test suite. |
| AC-7 | required      | docs-lint must stay clean. |


## Progress Log


| Date       | Update                                        | Evidence |
| ---------- | --------------------------------------------- | -------- |
| 2026-06-05 | Change admitted into wave 1p3dk; doc filled.  | `wave_add_change` → `1p3i6-enh flatten-changelog-single-source` admitted. |


## Decision Log


| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-06-05 | Root `CHANGELOG.md` is canonical; `build_pack.py` copies it into the pack zip at `.wavefoundry/CHANGELOG.md`. | In-tree changelog stays available to consumers (offline, MCP-indexable); duplication eliminated in wavefoundry repo. | (a) Keep vendored canonical (rejected — caused 6+ months of dual-edit drift); (b) Retire vendored CHANGELOG entirely, point consumers at GitHub Releases (rejected — softly contradicts the "local harness, no service" framing and removes offline access). |
| 2026-06-05 | Remove the narrative-prose chronological-section diagnostic. | Diagnostic was specific to the vendored narrative-prose format; root uses Keep-a-Changelog whose section headers (`### Changed`/`### Removed`/etc.) are self-disciplining. The diagnostic no longer applies. | (a) Rewrite the diagnostic to validate Keep-a-Changelog shape (rejected — Keep-a-Changelog is already widely understood and tooled; reinventing a validator adds maintenance burden for marginal value). |
| 2026-06-05 | Supersedes wave `131at` (`131at-enh changelog-cumulative-project-level.md`) without reopening that wave. | `131at` ran to close; reopening adds lifecycle complexity for a 2-line outcome. The new `[1.5.0]` CHANGELOG bullet documents the supersession. | (a) Reopen `131at` and re-close (rejected — overhead with no traceability gain). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Consumer projects that hand-edited their own `.wavefoundry/CHANGELOG.md` lose those edits on next upgrade. | Consumer copy was already wavefoundry-managed per `131at` (`"Consumer projects do not edit either file — it's a wavefoundry-managed snapshot of release history."`); contract is unchanged. |
| Existing `test_wavefoundry_changelog_included_in_pack` test fails after the flip. | Test fixture uses the real `.wavefoundry/framework/` (default `framework_dir`); `repo_root / "CHANGELOG.md"` resolves to the real root file which exists. Test should pass without change. Verify in AC-6. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
