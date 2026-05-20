# Seed Diff Output on Upgrade

Change ID: `12r1b-maint seed-diff-on-upgrade`
Change Status: `implemented`
Owner: framework-engineer
Status: implemented
Last verified: 2026-05-19
Wave: `12r09 automated-upgrade`

## Rationale

After the mechanical upgrade phases run, the agent still has to figure out what changed in the framework seeds. Today there is no mechanism: the agent must inspect the seeds manually, compare against its prior knowledge, or rely on drift detection. This is error-prone — seeds are the authoritative source of framework instructions, and the agent needs to know what changed so it can reconcile project-specific files, update its journal, and close spec gaps.

The fix: compute the seed diff from the zip contents vs. the current seeds on disk **before** extraction, and emit the full unified diff in the phase 0 change plan output. `wave_upgrade_response` captures stdout and returns it in `data.output`, so the agent receives the complete diff in the same MCP call that ran the upgrade — no extra step required.

## Requirements

1. A new `_compute_seed_diffs(root, zip_path)` function reads `*.md` files from `.wavefoundry/framework/seeds/` inside the zip (also checking alt prefix `framework/seeds/`), compares them to the current seeds on disk at `.wavefoundry/framework/seeds/`, and returns a list of `(filename, status, unified_diff_text)` tuples where `status` is `"modified"`, `"added"`, or `"removed"`.
2. Seed diffs are computed in `phase_preflight`, after the zip is detected and before confirmation, and passed into `_print_change_plan`.
3. `_print_change_plan` emits a summary line — `Seeds changed: N (M modified, A added, R removed)` or `Seeds changed: none` — followed by a full labeled diff block for each changed seed (`── Seed diff: <filename> [status] ──` then the unified diff text). The seed diff block appears after the existing plan table and before the `Proceed?` prompt.
4. When no zip is being applied, the summary line reads `Seeds changed: n/a (no zip — current tree already applied)`.
5. Missing or malformed seeds inside the zip are skipped with a warning line; the function never raises.

## Scope

**Problem statement:** After a mechanical upgrade the agent has no structured view of what changed in the framework seeds and must discover changes manually, increasing the risk of missed reconciliation.

**In scope:**

- `scripts/upgrade_wavefoundry.py` — `_compute_seed_diffs()`, updated `phase_preflight`, updated `_print_change_plan`

**Out of scope:**

- Diffing non-seed framework files (scripts, bin, surfaces)
- Storing the diff in the lock file or operator summary
- A separate `wave_upgrade(phase="seed_diff")` MCP entry point

## Acceptance Criteria

- AC-1: When a zip is applied, `wave_upgrade(phase="preflight_to_docs_gate")` output includes a `Seeds changed: N` summary line.
- AC-2: Each changed seed appears with a labeled header and a valid unified diff.
- AC-3: Unchanged seeds are not listed.
- AC-4: Added and removed seeds are correctly labeled.
- AC-5: When no zip is applied, the plan shows `Seeds changed: n/a`.
- AC-6: A missing or unreadable seed inside the zip does not crash the upgrade.
- AC-7: All existing tests continue to pass.

## Tasks

- Add `_compute_seed_diffs(root, zip_path)` to `upgrade_wavefoundry.py`
- Update `phase_preflight` to compute seed diffs and pass to `_print_change_plan`
- Update `_print_change_plan` to accept and emit seed diffs
- Add unit tests for `_compute_seed_diffs` (modified, added, removed, no-change, no-zip cases)

## Agent Execution Graph

| Workstream | Owner              | Depends On | Notes                                |
| ---------- | ------------------ | ---------- | ------------------------------------ |
| impl       | framework-engineer | —          | All changes in upgrade_wavefoundry.py |
| tests      | framework-engineer | impl       | Unit tests for _compute_seed_diffs   |

## Serialization Points

- `upgrade_wavefoundry.py` only — no shared files with other in-flight changes.

## Affected Architecture Docs

N/A — output-only enhancement to an existing script; no boundary, schema, or MCP surface change.

## AC Priority

| AC   | Priority  | Rationale                                      |
| ---- | --------- | ---------------------------------------------- |
| AC-1 | required  | Core deliverable                               |
| AC-2 | required  | Agent must be able to read and act on the diff |
| AC-3 | required  | Clean output — noise-free                      |
| AC-4 | required  | Complete coverage of change types              |
| AC-5 | required  | Graceful no-zip path                           |
| AC-6 | required  | Robustness                                     |
| AC-7 | required  | No regression                                  |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-19 | Implemented. `_compute_seed_diffs()` added to `upgrade_wavefoundry.py`; `phase_preflight` computes diffs from zip vs disk before extraction; `_print_change_plan` emits summary line + full labeled unified diffs. 7 unit tests added covering modified/added/removed/unchanged/bad-zip/alt-prefix/mixed cases. Pre-existing `test_single_build_gate_sets_pending_flag` race condition also fixed (rearmed timer fired after patch context exited). 1381 tests pass. | `python3 .wavefoundry/framework/scripts/run_tests.py` — 1381 OK |

## Decision Log

| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-05-19 | Compute diffs from zip vs disk in phase 0, before extraction | Agent needs structured diff before the upgrade commits to disk; reading from zip is non-destructive | Diff after extraction (loses the "before" state); separate `--seed-diff` flag (adds CLI complexity) |
| 2026-05-19 | Emit diffs inline in stdout (not a separate file) | `wave_upgrade_response` already captures stdout; agent gets diff in `data.output` with no extra MCP call | Write diff to a temp file and surface its path (requires agent to read separately) |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Very large seed diffs make `data.output` unwieldy | Seeds are markdown docs; diffs are typically a few hundred lines per seed; acceptable for MCP response |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.