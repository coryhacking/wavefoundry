# Upgrade Extraction Leaks Bundle Runner Files Into the Project Root

Change ID: `1u0cc-bug upgrade-extract-leaks-bundle-runner-files`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-07-31
Wave: `1tz6l release-upgrade-hardening`

## Rationale

Since the single release package began carrying both the extractable feature pack and the
protocol-bridge zipapp runner (wave 1tz6l), the upgrade's Phase 0b applies the archive with an
unfiltered `zf.extractall(root)` (`upgrade_wavefoundry.py:3631`). That extracts the bridge runner
members (`payload/` with multi-megabyte archives, `__main__.py`, `upgrade_bridge_bootstrap.py`,
`subprocess_util.py`) into the target project root alongside the intended `.wavefoundry/` tree.
The existing root cleanup (`_remove_root_bootstrap_file`) removes only `install-wavefoundry.md`,
so the runner members linger as committable debris. Observed in the field on the first two 1.15.0
upgrades: roughly 3.7 MB of un-ignored installer files left at each target repo root.

The unfiltered extraction is also an overwrite hazard: a target project that legitimately owns a
root `__main__.py` or `payload/` directory would have those files silently replaced by archive
content. On POSIX, CPython's zip extraction does not treat backslash as a separator, so a member
named `.wavefoundry\evil.py` lands as a literal root file today; an allowlist filter skips it by
structure.

The same debris is minted by the two documented manual extraction paths, which no shipped surface
cleans up (verified by the prepare council: `install-block.md` has no cleanup instruction; seed-160
step 0 instructs `unzip -o` with a cleanup limited to `install-wavefoundry.md`). Those surfaces are
in scope as companions so the defect is not merely moved to the manual paths.

## Requirements

1. Phase 0b extraction writes only intended members into the project root: archive paths under the
   feature prefix (`.wavefoundry/`) and the transient root bootstrap `install-wavefoundry.md`.
   Bridge runner members (`payload/*`, `__main__.py`, `upgrade_bridge_bootstrap.py`,
   `subprocess_util.py`) and any other unexpected root-level member are skipped, never written.
2. The allowlist derives from the constants that already define the pack layout
   (`upgrade_bundle.FEATURE_MEMBER_PREFIX`, `upgrade_bundle.FEATURE_ROOT_MEMBERS`) rather than
   re-hardcoding literals in the runner, keeping the extraction contract single-sourced. If
   importing at that point is unsafe (extraction replaces framework code mid-upgrade), mirror the
   constants locally with a test pinning them equal to `upgrade_bundle`'s.
3. A pre-existing project file or directory whose name collides with a skipped member is left
   byte-identical: never overwritten, never deleted.
4. Existing behavior is otherwise preserved: `install-wavefoundry.md` is still extracted and then
   removed by the existing fail-safe cleanup; the extract-idempotence guard (`_tree_already_at`)
   and the pre/post extract hooks are untouched. The existing ordering guard test
   (`test_extract_phase_wires_the_cleanup_after_extractall`, which anchors on the literal
   `zf.extractall` source text) is re-anchored on the new call, not deleted.
5. The skip decision is logged once per upgrade (member count, not per-file spam) so the upgrade
   log records that runner members were withheld. On a feature-only archive (the bridge-retained
   inner zip) the skip count is zero and no misleading line fires.
6. The documented manual extraction paths stop minting the debris: seed-160's step-0 fallback and
   the install surfaces (seed-010 extraction step, `install-block.md`) instruct scoped extraction
   (e.g. `unzip -o <zip> '.wavefoundry/*' 'install-wavefoundry.md' -d .`) instead of full-archive
   extraction, and the rendered `docs/prompts/upgrade-wavefoundry.prompt.md` is regenerated through
   the canonical renderer. Manual instructions must not use `rm -rf` of runner names (collision
   destruction, same hazard AC-3 guards against).

## Scope

**Problem statement:** The combined release zip's zipapp runner members are extracted into target
project roots on every install/upgrade and never cleaned up, and the unfiltered extraction can
overwrite same-named project files.

**In scope:**

- The single root-directed extraction site in `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`
  (Phase 0b)
- Regression tests in `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py`
- Companion doc/seed updates for the manual paths: `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`
  (step-0 fallback), `.wavefoundry/framework/seeds/010-install-wavefoundry.prompt.md` (extraction
  step), `.wavefoundry/framework/install/install-block.md`, and regeneration of rendered prompt
  surfaces (seed edits under the `seed_edit_allowed` gate)

**Out of scope:**

- The bundle runner itself (`upgrade_bundle.py`, `upgrade_bridge_bootstrap.py`); the bridge
  materialize path writes into `.wavefoundry/upgrade-assets/` (destination computed in
  `upgrade_bridge_bootstrap.py`), not the project root, and the bridge-retained feature archive is
  the inner feature-only zip snapshotted before runner members are appended (`build_pack.py`), so
  no runner member reaches the root via the bridge path
- Remediation of already-polluted repositories (one-time manual cleanup, already performed)
- Pack layout changes in `build_pack.py` (the single-artifact decision is settled)

## Acceptance Criteria

- [x] AC-1: After an upgrade that applies a combined release zip, the project root contains no
  `payload/` directory, `__main__.py`, `upgrade_bridge_bootstrap.py`, or `subprocess_util.py`
  originating from the archive.
- [x] AC-2: Archive members under `.wavefoundry/` are extracted exactly as before, and
  `install-wavefoundry.md` continues to be dropped at the root and removed by the existing
  fail-safe cleanup, in the existing order (cleanup after extraction).
- [x] AC-3: A pre-existing root file or directory whose name collides with a skipped runner member
  is byte-identical after the upgrade.
- [x] AC-4: Regression tests cover AC-1 through AC-3 plus: a backslash-separator member
  (`.wavefoundry\...`) is skipped, a traversal-shaped member inside the allowed prefix stays
  contained under `.wavefoundry/`, a feature-only archive extracts with skip count zero, and the
  runner's allowlist stays pinned to `upgrade_bundle`'s layout constants. The bundle-shaped zip
  fixture's member layout is produced by (or verified against) the canonical builder. The full
  framework suite passes.
- [x] AC-5: Seed-160 step-0 fallback, seed-010 extraction step, and `install-block.md` instruct
  scoped extraction; the project's reconciled prompt surface (`docs/prompts/upgrade-wavefoundry.prompt.md`,
  an agent-reconciled summary of seed-160, not a mechanically rendered file) and
  `docs/references/dashboard-install-upgrade.md` carry the same scoped instruction, and docs-lint
  passes.

## Tasks

- [x] Replace `zf.extractall(str(root))` with a member-filtered extraction helper (allowlist from
  the pack-layout constants per requirement 2), skipping everything else and logging the
  skipped-member count once
- [x] Re-anchor `test_extract_phase_wires_the_cleanup_after_extractall` on the new call so the
  cleanup-after-extraction ordering guard survives
- [x] Add regression tests: debris absence, `.wavefoundry/` extraction parity, bootstrap cleanup
  still firing, collision file untouched, backslash-member skip, contained traversal, feature-only
  zero-skip, allowlist-constants pin
- [x] Update seed-160 step-0 fallback and install surfaces (seed-010, `install-block.md`) to scoped
  extraction under the `seed_edit_allowed` gate (gate opened and closed); reconcile the project
  prompt surface and dashboard reference doc to match
- [x] Run the full framework test suite

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes                                                        |
| ---------- | ----------- | ---------- | ------------------------------------------------------------ |
| fix        | implementer | —          | Runner filter plus tests; single edit site, no parallel work |
| docs       | implementer | fix        | Seed/install-surface companions plus renderer regeneration   |


## Serialization Points

- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py` (single edit site; no coordination needed)
- Seed edits gated by `seed_edit_allowed`; renderer regeneration follows the seed edits

## Affected Architecture Docs

N/A: the change is confined to the extraction step inside the upgrade runner plus instruction
surfaces; no module boundary, data flow, or verification architecture changes. (Council-verified:
no `docs/architecture/` doc describes the Phase 0b member layout; the threat model treats
distribution zips as trusted.)

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority | Rationale                                                          |
| ---- | -------- | ------------------------------------------------------------------ |
| AC-1 | required | The reported defect: installer debris at target repo roots         |
| AC-2 | required | Must not regress the normal upgrade extraction path                |
| AC-3 | required | Prevents silent destruction of target-project files                |
| AC-4 | required | Field-observed defect needs a pinned regression                    |
| AC-5 | required | Council finding: manual paths otherwise keep minting the debris    |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-31 | Filter helper `_extract_feature_members` + skip-count log implemented; ordering-guard test re-anchored; 8 regression tests added (all green targeted); seed-160/seed-010/install-block scoped-extraction companions landed; prompt surface + dashboard reference reconciled; docs-lint clean | `ExtractFeatureMembersTests` 8/8 + `RemoveRootBootstrapFileTests` 7/7 pass; `wf_validate_docs` passed |
| 2026-07-31 | Field-verified via pack 1.15.0+pfxp in two target repos: transition run (pfwu to pfxp) drops the debris one final time because extraction runs from the pre-upgrade code on disk; all later upgrades extract scoped. One target agent misread the transition drop as "allowlist not wired in", so seed-160 and the prompt surface now state the one-time transition behavior explicitly | pfxp zip inspected: `_extract_feature_members` present, only `extractall(..., members=allowed)` remains; field logs from both target upgrades |


## Decision Log


| Date       | Decision                                            | Reason                                                                                                                     | Alternatives                                                                                                                                 |
| ---------- | --------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| 2026-07-31 | Filter members at extraction, allowlist-based       | Delete-after-extract can destroy a project's own same-named files and still leaves an overwrite window during extraction   | Post-extract deletion of known runner names (rejected: destructive on name collision); gitignore-only (rejected: files still land on disk)     |
| 2026-07-31 | Keep extracting the bootstrap, keep existing cleanup | Preserves the wave-1rxyi behavior and its test story with the smallest diff                                                | Exclude `install-wavefoundry.md` from extraction and let `_remove_root_bootstrap_file` become a fail-safe no-op (viable; larger behavior delta) |
| 2026-07-31 | Manual paths get scoped extraction, not cleanup     | A scoped `unzip` never writes the debris; an `rm` list recreates the collision-destruction hazard                          | Post-unzip `rm -rf payload/ __main__.py ...` in seeds (rejected: destructive on name collision)                                                |


## Risks


| Risk                                                                 | Mitigation                                                                                                    |
| -------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| A future pack adds a new intended root member the filter would skip   | Allowlist derives from the pack-layout constants; a pinning test fails loudly when the layout changes           |
| Skipping members masks a malformed archive                            | Skip count is logged; archive validation remains the bundle runner's job, unchanged                             |
| Seed edits drift from rendered surfaces                               | Regenerate through the canonical renderer in the same task; docs-lint gates the result                          |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
