# Add an upgrade floor and surface post-extract migration-log errors

Change ID: `1p5do-enh upgrade-floor-and-migration-log-surfacing`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-13
Wave: `1p5dk 1-6-release-hardening`

## Rationale

Two upgrade-flow robustness gaps surfaced in the review:

1. **No upgrade floor.** The only version guard in `phase_preflight` is direction (abort on downgrade; allow upgrade/same — `upgrade_wavefoundry.py:1029-1038`). There is no minimum supported `from_version`. The 1.4→1.5 migrations are version-gated and still present, so a `1.4.x → 1.6` skip works — but any transition *older* than 1.4→1.5 relies on migrations that have been pruned from `upgrade_extensions.py`. So a multi-major skip from an ancient install can land mechanically "successful" while silently missing an intermediate migration that no longer exists. An unparseable `from_version` also proceeds (`_from_version_predates` returns True defensively).

2. **Migration failures don't surface in the summary.** `post_extract` migrations (convergence + 1.4→1.5) isolate their own failures — each `except` records to a report log and continues (`upgrade_extensions.py:816-861`, `724-728`) — and do **not** set `failed_phase`. `_docs_gate_summary_line` returns `PASSED` whenever `failed_phase is None` (`:1377-1391`). So a tree where a migration partially failed can still print "Upgrade complete / Docs gate: PASSED." The failure is in `.wavefoundry/logs/upgrade-*migration*.log`, but nothing forces the operator to read it. Relatedly, `_detect_version_transitions` returns `[]` when no prior index/graph state exists (`:582`), so the "this will be a substantial rebuild" signal goes silent exactly when a fresh-but-stale install most needs it.

## Requirements

1. Add an explicit **supported-`from_version` floor of 1.4.0** as a **loud warning, not an abort**: below 1.4.0 (and for unparseable versions) the upgrade prints a clear surfaced warning and proceeds. Rationale (operator-confirmed 2026-06-13): all known projects are ≥ 1.5.1, so nothing is actually below the floor — the floor's job is to make the already-published 1.5.0 "supported floor is 1.4.0" claim real and self-documenting, not to block a live case. Warn-not-abort avoids blocking a hypothetical legitimate edge case for no real-world benefit.
2. **Surface migration-log errors in the final summary**: cleanup scans `upgrade-migration-*.log` / `upgrade-convergence-migration.log` for `ERROR:` lines and downgrades the "Upgrade complete / PASSED" summary to a warning that points at the log when any are present.
3. **Don't go silent on an empty version snapshot**: when `_snapshot_pre_extract_versions` is empty but an index exists, log "version baseline unknown — full re-embed expected" so the operator still gets the rebuild-cost signal.
4. The convergence migration surfaces a warning when `workflow-config.json` exists but can't be parsed/rewritten (today it silently no-ops, then the gate fails with no migration-side signal).

## Scope

**Problem statement:** the upgrade has no version floor (silent partial migrations on ancient skips) and can report a clean summary over a partially-failed migration or an unknown rebuild baseline.

**In scope:**

- `upgrade_wavefoundry.py` (`phase_preflight` floor guard; cleanup summary log-scan; the empty-snapshot signal) and `upgrade_extensions.py` (convergence parse-failure warning).
- Tests for: below-floor abort/warn; migration-log `ERROR:` downgrades the summary; empty-snapshot logs the rebuild signal.

**Out of scope:**

- Changing the "version bumps are logged, not force-rebuilt" design (intentional log-and-trust — see wave watchpoint; defer any rebuild-policy change).
- The secrets baseline (`1p5dn`) and any doc text (`1p5dm` documents the floor this change establishes).

## Acceptance Criteria

- [ ] AC-1: an upgrade from below 1.4.0 (and from an unparseable version) **loud-warns and proceeds** with a clear surfaced message; an upgrade from ≥ 1.4.0 (e.g. 1.5.1) does not warn; asserted by test.
- [x] AC-2: a `post_extract` migration that records an `ERROR:` causes the final summary to surface a warning pointing at the log (`_warn_if_migration_errors`, called next to `_warn_if_background_code_incomplete`), not silently "PASSED"; `.preview.log` dry-run reports are ignored. Asserted by `test_migration_errors_surface` / `_clean_log_silent` / `_preview_log_ignored`.
- [x] AC-3: an empty pre-extract version snapshot with an existing index logs the "full re-embed / graph re-extract" signal (`_warn_if_no_version_baseline`, called in the no-transitions `else`); asserted by test.
- [x] AC-4: a malformed `workflow-config.json` produces a convergence-migration warning on stderr (not a silent no-op); asserted by `ConvergenceParseWarningTests`. Full suite **3116 OK**.

## Tasks

- [x] Add the `from_version` floor guard in `phase_preflight` (`_below_upgrade_floor` + `SUPPORTED_UPGRADE_FLOOR="1.4.0"`, loud-warn).
- [x] Cleanup-phase scan of migration logs for `ERROR:` (`_warn_if_migration_errors`).
- [x] Empty-snapshot rebuild-signal log (`_warn_if_no_version_baseline`); convergence parse-failure warning (`upgrade_extensions._rewrite_legacy_config_keys`).
- [x] Tests for each (9 tests); floor value `1.4.0` to be documented in `1p5dm`.

## Agent Execution Graph


| Workstream     | Owner  | Depends On   | Notes |
| -------------- | ------ | ------------ | ----- |
| [workstream-1] | [role] | —            |       |
| [workstream-2] | [role] | workstream-1 |       |


## Serialization Points

- The floor value must match what `1p5dm` documents — settle it once and reference from both.

## Affected Architecture Docs

`N/A` — robustness guards within the upgrade flow; no boundary/contract change. (The floor is operator-facing but documented in `1p5dm`, not an architecture doc.)

## AC Priority

(Populated at Prepare wave.)

| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | A silent partial migration on a version skip is a correctness hazard. |
| AC-2 | required  | A green summary over a failed migration hides a broken upgrade. |
| AC-3 | important | The rebuild-cost signal must not vanish exactly when it's most needed. |
| AC-4 | important | A silent convergence no-op makes the later gate failure baffling. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-14 | **Added `~/Downloads/` as a 5th pack search path (operator-flagged)** — browser-downloaded packs commonly land there and were silently missed (discovery only saw repo root, `~/`, `~/.wavefoundry/`, `~/.wavefoundry/dist/`). Added `_DOWNLOADS_DIR` to both `search_dirs` tuples + the 3 docstring/help enumerations; 2 new tests (`test_finds_zip_in_downloads`, `test_downloads_competes_on_semver`) + isolated `_DOWNLOADS_DIR` in the discovery + dry-run tests so they don't scan the real `~/Downloads`. Full suite **3118 OK**. | `upgrade_wavefoundry.py`, `test_upgrade_wavefoundry.py` |
| 2026-06-13 | Implemented all four in `upgrade_wavefoundry.py` + `upgrade_extensions.py`: `_below_upgrade_floor` + `SUPPORTED_UPGRADE_FLOOR="1.4.0"` loud-warn in `phase_preflight`; `_warn_if_migration_errors` (scans real, non-`.preview` migration logs for `ERROR:`) called at cleanup; `_warn_if_no_version_baseline` in the no-transitions branch; convergence parse-failure warning in `_rewrite_legacy_config_keys`. 9 tests added; full suite **3116 OK**. | `upgrade_wavefoundry.py`, `upgrade_extensions.py`, `test_upgrade_wavefoundry.py` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-13 | Floor = loud-warn at 1.4.0 (not hard-abort, not dropped) | All known projects are ≥ 1.5.1 so nothing is below the floor; warn makes the published 1.5.0 floor claim real without risking a block on a legitimate edge case | Hard-abort below 1.4.0 (blocks a hypothetical ancient install for no benefit); drop the floor entirely (leaves the published 1.5.0 claim unenforced) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A hard floor-abort blocks a legitimate ancient-install upgrade | Prefer loud-warn-and-proceed over hard-abort if the migration chain is defensively idempotent; confirm at prepare |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
