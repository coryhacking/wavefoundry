# Secret-scan + reconcile downstream-feedback fixes

Change ID: `1p8o5-bug secret-scan-reconcile-downstream-fixes`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-28
Wave: `1p8nw secret-scan-lifecycle-ids`

## Rationale

The downstream test of the 1.9.5 candidate (`p8o2`) validated the headline fixes (`data.summary` now emits on the primary `wave_upgrade()` call — 1p8kz confirmed) but surfaced four residual discrepancies in the secret-scan / reconcile surfaces. All are operator-reported from a real upgrade; #3 is a genuine downstream docs-lint risk, the rest are accuracy/usability.

1. **reconcile_scan exclusion is narrower than its seed spec.** The 1p8gx adversarial-review SCAN-2 fix anchored `EXCLUDED_ROOT_FILES = ("CHANGELOG.md",)` to the repo root only (`reconcile_scan.py:89-91`), so a nested `.wavefoundry/CHANGELOG.md` is flagged — yet seed-160:48 promises the scan "never flags … `CHANGELOG.md`". The renderer-managed `docs/prompts/prompt-surface-manifest.json` (historical `upgrade_merge_notes`) is also flagged. These are historical false-positives.
2. **Host allow-rule files appear in the wrong channel.** seed-160:50 says the scan "does **not** cover host permission/allow-rule files" and they should be "flagged **separately** for the operator." But `reconcile_scan` scans `.json` files and returns `.claude/settings.local.json` inside `summary.reconciliation` (the edit-these list), where an agent cannot self-edit it anyway.
3. **seed-213 references a doc not shipped to consumers (real downstream risk).** seed-213 (from 1p8l0) references `docs/references/scan-findings-format.md`, which exists in this self-host repo + as the framework copy (`.wavefoundry/framework/docs/`) but is **not rendered/shipped into consumer `docs/references/`** — so a consumer that mirrors the seed gets a broken relative link → docs-lint fails.
4. **The scan-findings ledger is not written on a clean scan.** `save_exceptions` is only called `if exceptions_changed` (`secrets_validators.py:1599`), so a zero-finding scan with no prior file writes nothing — the file's *absence* is ambiguous ("clean" vs "never ran"). Operators want an always-present ledger so presence = "scan ran."

## Requirements

1. reconcile_scan excludes `CHANGELOG.md` by **basename** (any path, not root-only) and the renderer-managed `docs/prompts/prompt-surface-manifest.json`; seed-160's exclusion wording is reconciled to match the impl exactly. (The dated self-host snapshot `docs/references/…-feedback-<ver>.md` is a self-host-only long-tail FP that does not occur in consumer repos — accept it or relocate such snapshots to an already-excluded dir; do NOT add a fragile generic docs/references pattern.)
2. reconcile_scan does NOT place host permission/allow-rule files (`.claude/settings.local.json` + per-host equivalents) in `summary.reconciliation`; it surfaces them in a SEPARATE operator-flag channel (e.g. `host_permission_flags`), which `wave_upgrade`'s summary + the operator prose carry distinctly. Matches seed-160:50.
3. The seed-213 reference to `scan-findings-format.md` must not break docs-lint in a consumer repo: either ship/render `scan-findings-format.md` into consumer `docs/references/` on install/upgrade (it documents the consumer's `docs/scan-findings.json`, so it belongs there), or make the seed reference resolve safely (shipped framework path / self-contained). Investigate the reference-docs shipping mechanism and choose.
4. A clean scan (0 findings) WRITES `docs/scan-findings.json` as a bare `[]` so the file's presence confirms the scan ran. Preserve the incremental-scan logic (the missing-file-forces-rescan path) and the gate semantics (`[]` = no findings = no block). Document the always-present-ledger behavior in `scan-findings-format.md`.

## Scope

**Problem statement:** four downstream-test discrepancies in the secret-scan/reconcile surfaces — exclusion FPs, allow-rule channel mismatch, a consumer broken-link risk, and a missing always-present ledger.

**In scope:**

- reconcile_scan exclusion accuracy (#1) + the separate allow-rule channel (#2) + the `wave_upgrade` summary field for the new channel.
- seed-213 reference safety / `scan-findings-format.md` consumer availability (#3).
- Always-write the scan-findings ledger on a clean scan (#4).
- seed-160 + scan-findings-format.md + tests for all four.

**Out of scope:**

- Changing secret-detection rules, statuses, confirmation policy, the secrets gate semantics, or the `sec` ID format (1p8l0, already landed).
- A metadata-wrapper schema for the ledger (bare `[]` chosen for minimal blast radius; the scan-state file already records timing).
- Relocating existing self-host feedback-snapshot docs (separate cleanup).

## Acceptance Criteria

- [x] AC-1: reconcile_scan excludes any-path `CHANGELOG.md` and `prompt-surface-manifest.json`; a test asserts `.wavefoundry/CHANGELOG.md` + the manifest are NOT flagged (and a real in-scope doc still IS). seed-160 exclusion wording matches the impl. (`EXCLUDED_BASENAMES` basename match; `test_changelog_excluded_by_basename_anywhere` + `test_prompt_surface_manifest_excluded`; seed-160:48 reconciled.)
- [x] AC-2: host allow-rule files are returned in a SEPARATE channel, not `summary.reconciliation`; `wave_upgrade`'s summary exposes them distinctly; a test asserts `.claude/settings.local.json` is absent from `reconciliation` and present in the operator-flag list. seed-160 + the reconciliation prose updated. (`scan_repo_channels` → `(reconciliation, host_permission_flags)`; `summary.host_permission_flags` additive field; `HostPermissionChannelTests` + `test_sentinel_host_permission_flags_separate_from_reconciliation`; seed-160:50 + mcp-tool-surface.md updated.)
- [x] AC-3: a consumer carrying the seed-213 content passes docs-lint — `scan-findings-format.md` is reachable (shipped/rendered) or the reference is self-resolving; a test/guard covers the no-broken-link guarantee. (Mechanism: shipped template + seed-012 install provisioning + seed-160 upgrade refresh already wired; the link validator strips inline-code so the inline-code reference is self-resolving. `ScanFindingsFormatReferenceSafetyTests` pins both — no markdown-link form anywhere + the validator does not flag inline code + provisioning chain intact.)
- [x] AC-4: a zero-finding scan writes `docs/scan-findings.json` as `[]` (presence = ran); the incremental-scan path and the secrets-gate (`[]` → no block) are unchanged; tests cover the clean-scan write + the gate on `[]`. (`check_hardcoded_secrets` always-write `elif` gated to `scan_all`; `TestAlwaysPresentLedger` (write + idempotent no-churn + incremental-does-NOT-create) + `test_always_present_empty_ledger_does_not_block`.)
- [x] AC-5: full framework suite + docs-lint pass. (`run_tests.py` 3660 ok; `wf docs-lint` ok; bytecode cleaned.)

## Tasks

- [x] reconcile_scan: CHANGELOG-by-basename + exclude prompt-surface-manifest.json; update is_excluded + the exclusion comments; reconcile seed-160 wording.
- [x] reconcile_scan: add a host-permission-flag classification + a separate return channel; thread it through `wave_upgrade`'s summary (`host_permission_flags`) + the operator prose; update seed-160.
- [x] #3: investigate reference-docs shipping; ship/render scan-findings-format.md to consumers OR make the seed-213 reference safe; add a no-broken-link guard. (Both: provisioning chain already ships it AND the inline-code reference is self-resolving; guard pins both.)
- [x] #4: write `docs/scan-findings.json` as `[]` on a clean scan (preserve incremental + gate); document in scan-findings-format.md.
- [x] Tests for all four + full suite + docs-lint.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| reconcile_scan exclusions + allow-rule channel (#1, #2) | implementer | — | + wave_upgrade summary field + seed-160 |
| seed-213 reference / scan-findings-format shipping (#3) | implementer | — | investigate render/ship; no-broken-link guard |
| always-write ledger (#4) | implementer | — | bare []; preserve incremental + gate |
| tests + docs | qa-reviewer | all | non-vacuous; gate-unchanged |

## Serialization Points

- #2 touches `reconcile_scan` output shape + `wave_upgrade`'s summary assembly (server_impl / upgrade_wavefoundry) — keep the new `host_permission_flags` field additive (don't disturb `reconciliation`).
- #4 touches the secrets scan write path — must not alter the gate (security faithfulness); coordinate with the just-landed 1p8l0 migration (runs before save).

## Affected Architecture Docs

`docs/references/scan-findings-format.md` (#3, #4); `docs/specs/mcp-tool-surface.md` if the `wave_upgrade` summary gains `host_permission_flags`. ADR `N/A`.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Exclusion must match its spec; reduces misleading FPs. |
| AC-2 | required | Allow-rule files in the edit-these list misleads agents. |
| AC-3 | required | Real downstream docs-lint break risk. |
| AC-4 | required | Operator-requested always-present ledger. |
| AC-5 | required | Regression safety. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-28 | Planned from the 1.9.5 (`p8o2`) downstream test feedback (4 items); `data.summary`/1p8kz confirmed working. | `reconcile_scan.py:89-91` (root-only CHANGELOG); seed-160:48/:50; seed-213 → `docs/references/scan-findings-format.md` (not shipped); `secrets_validators.py:1599` (write only if changed). |
| 2026-06-28 | Implemented all 4 items. #1: `EXCLUDED_BASENAMES` (CHANGELOG.md + prompt-surface-manifest.json) basename-matched in `is_excluded`; seed-160:48 reconciled. #2: `scan_repo_channels()` partitions findings into `(reconciliation, host_permission_flags)` on a `StaleReference.host_permission` flag (`HOST_PERMISSION_FILES` = `.claude/settings.local.json`/`.claude/settings.json`/`.cursor/settings.json`); threaded additively through `_run_reconciliation_scan` → `summary.host_permission_flags` + a distinct operator-prose section; seed-160:50 + mcp-tool-surface.md updated. #3: found the shipping chain already wired (shipped template + seed-012 install + seed-160 upgrade + byte-parity guard) AND the link validator strips inline-code so seed-213's inline-code ref is self-resolving — added `ScanFindingsFormatReferenceSafetyTests` pinning both. #4: `check_hardcoded_secrets` writes a bare `[]` on a clean full scan (`elif scan_all and not exists`), gated to full scans so the incremental missing-file rescan trigger is preserved; gate on `[]` unchanged (`_check_secrets_gate` returns no diagnostics on empty). 1p8l0 migration + secrets-gate code untouched. | `run_tests.py` 3646→3660 ok (reconcile +5, upgrade +1, shipped-refs +4, secrets +3, server +1); `wf docs-lint` ok; bytecode-free; `git diff` shows the only `secrets_validators.py` change is the always-write `elif`; server_impl.py not touched by this change. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-28 | Bare `[]` for the always-present ledger (not a metadata wrapper). | Operator point: a metadata wrapper (e.g. `scanned_at`) would rewrite the file on EVERY scan → constant git churn / spurious commits; a bare `[]` only changes when findings change. Also minimal blast radius — `load_exceptions`/the gate read a list, and the scan-state file already records timing. | Metadata wrapper `{scanned_at, findings:[]}` (rejected: churns the file every scan + a schema change touching the gate + the 1p8l0 migration). |
| 2026-06-28 | Separate `host_permission_flags` channel rather than excluding allow-rule files entirely. | Still surfaces stale allow rules to the operator (the seed's intent) without putting them in the edit-these list. | Exclude entirely (rejected: operator never learns of the stale rule). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| #4 always-write disturbs the incremental-scan / gate behavior. | Keep `[]` = no-findings = no-block; test the clean-scan write + the gate on `[]`; preserve the scan-state file. |
| #1 CHANGELOG-by-basename over-excludes a real doc. | Basename match is specific to `CHANGELOG.md` (always release history); test a real in-scope doc is still flagged. |
| #3 shipping scan-findings-format.md to consumers expands the rendered-docs set unexpectedly. | Investigate the existing reference-docs ship path first; prefer the minimal safe option. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
