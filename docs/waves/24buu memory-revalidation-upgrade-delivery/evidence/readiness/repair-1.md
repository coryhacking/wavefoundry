# 24buu readiness repair, cycle 1

Owner: Engineering
Status: active
Last verified: 2026-11-24

One bounded repair pass over the five specs, recorded as `repair_start` cycle 1 for all 17 findings (context `24buu-readiness-repair-1`, actor implementer). Each spec's Progress Log has a "Bounded readiness repair (cycle 1)" row.

| Finding | Spec | Repair |
| --- | --- | --- |
| CR-1, QA-1 | 24but | Requirement 1: `churn_available` false when the index store is absent, unopenable, wrong-schema or the read raises; `index_state_store.py` in scope; AC-7 rewritten with real absent, corrupt and wrong-schema fixtures, no monkeypatch. |
| CR-2, QA-2 | 24but | AC-1 expected object includes `"churn_available": true`. |
| DC-2 | 24but | Requirement 3: the merge covers every copy 24bn8 leaves in place (edited, baseline-unknown, symlinked, changed after comparison). |
| DC-3 | 24but | Requirement 5: the self-hosted `review-policy-upgrade` region is regenerated from `UPGRADE_POLICY_BLOCK`, never hand-edited; the line-break pin kept or updated in the same edit. |
| SEC-1 | 24ax3 | Requirement 5: outside layers use the `_claude` matcher and `_codex` rules, follow symlinks read-only, and hold every route named in an unparseable file; AC-4 covers six cases. |
| QA-4 | 24ax3 | One path resolver honoring `HOME`, `USERPROFILE`, `CLAUDE_CONFIG_DIR`, `CODEX_HOME` and `WAVEFOUNDRY_MANAGED_SETTINGS_PATH`; enterprise paths named per platform. |
| QA-5 | 24ax3 | AC-9: symlinked or outside-checkout repository files are not written. |
| AR-2 | 24ax3, 24bn8 | Trigger pinned: any `--include-permissions` render runs the migration (1.51.0 argv verbatim, AC-10); `wf setup` runs it too (operator direction) and setup readiness reports withheld tools with `wf setup` as the remedy (AC-11); 24bn8 replaces only when the upgrade lock holds captured findings (AC-8). |
| AR-3 | all four | Affected Architecture Docs name `data-and-control-flow.md` sections and `threat-model.md` (24ax3). |
| DC-1 | 24ax3, 24bn8, 24bn9 | Each names the seed 160 section or paragraph it revises in place and pins the absence of the old sentence. |
| DC-4 | 24ax3, 24bn9, 24bn7 | Target-visible carrier stated; 24bn7 changelog under a new Fixed heading. |
| QA-3 | 24bn7 | Protocol-2 fixture, non-dry run, stubbed next step, both zips; path entry at `sys.path` index 1. |
| AR-1 | 24bn9 | The release-zip entry and `--resume-after-gate` also auto-clean; bridge recovery says cleanup is complete; AC-9, AC-10. |
| QA-6 | 24bn9 | AC-7 (restart-required, retained checkpoint), AC-8 (real child, one terminal result). |
| QA-7 | 24bn8 | AC-7: unknown-baseline and unchanged-upstream copies untouched. |

Also folded in from lane notes: 24bn9 accepts `WAVEFOUNDRY_STORAGE_OLD_MCP_PID` as an opt-out; 24ax3 keeps valid existing receipts, lists read files in the receipt, prints resolved paths, re-parses the Codex file with `tomllib`, orders migrate, receipts, managed render, and runs in the permissions-only backstop; 24bn8 saves replaced paths in the lock.
