# Fix Upgrade Prune Count Reporting

Change ID: `1p44q-bug upgrade-prune-count-reporting`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-06-08
Wave: 1p44n framework-1p6-hardening

## Rationale

The `pruned_count` reported by the upgrade flow is structurally always 0, so the upgrade summary and persisted lock under-report how many framework files were actually deleted. The deletions themselves are correct — this is a cosmetic/reporting defect only.

The root cause is a mismatch between what `prune_framework.py` emits and what `upgrade_wavefoundry.py` scans for:

- `upgrade_wavefoundry.py:1123` derives the count via `sum(1 for line in result.stdout.splitlines() if "removed" in line.lower() or "pruned" in line.lower())`.
- `prune_framework.py` prints per-file deletions to STDOUT as `deleted: <path>` (`prune_framework.py:133`) and `[dry-run] would delete: <path>` (`prune_framework.py:130`) — neither line contains the substrings `removed` or `pruned`.
- `prune_framework.py` prints the count SUMMARY to STDERR: `prune: <label> N item(s)` (`prune_framework.py:187`) and `prune: nothing to remove` (`prune_framework.py:189`).
- `phase_pruning` runs the subprocess with `capture_output=True` (`upgrade_wavefoundry.py:1116`), so STDERR is not present in `result.stdout`.

Net effect: the stdout scan never matches, `pruned` is always 0, and that 0 is persisted to the upgrade lock via `update_upgrade_lock(root, pruned_count=pruned_count)` (`upgrade_wavefoundry.py:1584`) and displayed in the summary as `Files pruned: 0` (`upgrade_wavefoundry.py:1285`).

## Requirements

1. The pruned count returned by `phase_pruning` MUST equal the real number of files pruned (or, in dry-run, the number that would be pruned) during a pruning upgrade.
2. The count MUST be derived from a stable, machine-checkable signal from `prune_framework.py` rather than the current `removed`/`pruned` substring heuristic that never matches.
3. The corrected count MUST flow unchanged through the existing persistence path: persisted to the upgrade lock via `update_upgrade_lock(root, pruned_count=...)` and shown in the upgrade summary as `Files pruned: N`.
4. When nothing is pruned, the count MUST be 0 (the `prune: nothing to remove` case must not be miscounted as nonzero).
5. The change MUST NOT alter which files are deleted or any other prune side effects — reporting only.

## Scope

**Problem statement:** `pruned_count` in the upgrade flow is always 0 because `upgrade_wavefoundry.py` scans `result.stdout` for `removed`/`pruned` substrings, but `prune_framework.py` emits per-file `deleted:`/`would delete:` lines to stdout and the count summary to stderr (which `capture_output=True` keeps out of `result.stdout`). The persisted lock value and the upgrade summary therefore under-report real deletions.

**In scope:**

- Correcting the count derivation in `phase_pruning` (`upgrade_wavefoundry.py` around line 1116-1123) to parse a signal the prune script actually emits.
- Optionally adding a machine-readable count line (e.g. `pruned_count: N`) to `prune_framework.py` stdout if that is chosen as the source of truth.
- A unit test exercising the count extraction against a fixture of representative prune output.

**Out of scope:**

- Any change to which files are selected for pruning or to the deletion logic itself.
- Changes to the upgrade lock schema beyond the existing `pruned_count` field.
- Dry-run vs. apply behavior changes other than ensuring both report an accurate count.

## Acceptance Criteria

- [ ] AC-1: After a pruning upgrade that removes N files, the value returned by `phase_pruning` equals N (the real number of pruned files), not 0.
- [ ] AC-2: The corrected count is persisted to the upgrade lock via `update_upgrade_lock(root, pruned_count=N)` and rendered in the upgrade summary as `Files pruned: N`.
- [ ] AC-3: When `prune_framework.py` emits `prune: nothing to remove`, the reported count is exactly 0.
- [ ] AC-4: A new unit test feeds a fixture of representative prune output (multiple `deleted:` lines plus the `prune: <label> N item(s)` summary, and a separate `nothing to remove` case) and asserts the extracted count matches.
- [ ] AC-5 (regression): The existing framework test suite (`python3 .wavefoundry/framework/scripts/run_tests.py`) passes with the new test included.

## Tasks

- [ ] Confirm the exact emission contract of `prune_framework.py` (stdout `deleted:`/`would delete:` lines at 130/133; stderr summary `prune: <label> N item(s)` at 187 and `prune: nothing to remove` at 189).
- [ ] Choose the count source: parse `result.stderr` for `prune: ... N item(s)` and extract N (preferred), or count `deleted:`/`would delete:` stdout prefixes, or add a machine-readable `pruned_count: N` stdout line in `prune_framework.py`.
- [ ] Implement the count extraction in `phase_pruning` (`upgrade_wavefoundry.py` ~1116-1123), replacing the `removed`/`pruned` substring heuristic; handle the `nothing to remove` case as 0.
- [ ] Ensure the returned count flows to `update_upgrade_lock` (1584) and the summary line (1285) unchanged.
- [ ] Add a unit test with a prune-output fixture covering the multi-deletion and nothing-to-remove cases.
- [ ] Run `python3 .wavefoundry/framework/scripts/run_tests.py` and confirm green.

## Agent Execution Graph


| Workstream            | Owner       | Depends On | Notes                                                                 |
| --------------------- | ----------- | ---------- | --------------------------------------------------------------------- |
| count-extraction-fix  | Engineering | —          | Edit `phase_pruning` in `upgrade_wavefoundry.py`; optional prune emit |
| prune-output-test     | Engineering | —          | Author fixture + unit test; pairs with the extraction helper          |


## Serialization Points

- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py` (shared) — the count fix touches `phase_pruning` and must coordinate with any other edits in this file.
- `.wavefoundry/framework/scripts/prune_framework.py` (possibly shared) — only if the machine-readable `pruned_count: N` stdout option is chosen.

## Affected Architecture Docs

N/A — the change is confined to the upgrade/prune scripts and a test; it corrects a reporting count with no boundary, data-flow, or verification-architecture impact.

## AC Priority


| AC   | Priority   | Rationale                                                                          |
| ---- | ---------- | ---------------------------------------------------------------------------------- |
| AC-1 | required   | The core defect: count must equal real pruned files.                               |
| AC-2 | required   | Persisted lock and summary must reflect the corrected count to be useful.          |
| AC-3 | important  | Prevents a false-positive count when nothing is pruned.                            |
| AC-4 | required   | Unit test is the named acceptance evidence in the brief.                           |
| AC-5 | required   | Regression gate — full suite must stay green.                                      |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
|      |        |          |


## Decision Log


| Date       | Decision                                                                                          | Reason                                                                                                  | Alternatives                                                                                      |
| ---------- | ------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------ |
| 2026-06-08 | Prefer parsing `result.stderr` for `prune: ... N item(s)` to extract N as the count source.       | N is the prune script's own authoritative total; avoids per-line recounting drift and keeps stdout free. | Count `deleted:`/`would delete:` stdout prefixes; emit machine-readable `pruned_count: N` to stdout. |
| 2026-06-08 | Keep persistence unchanged via `update_upgrade_lock(root, pruned_count=...)`.                      | The lock field and summary line already exist and are correct; only the input value was wrong.          | Add a new lock field — rejected as unnecessary schema churn for a reporting fix.                  |


## Risks


| Risk                                                                                          | Mitigation                                                                                   |
| --------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| `prune: ... N item(s)` stderr format changes later, silently re-breaking extraction.          | Unit test pins the fixture format; co-locate the parse and emit if a stdout signal is added. |
| Regex over-matches and counts unrelated `N item(s)` text.                                      | Anchor on the `prune:` prefix and extract the integer adjacent to `item(s)`.                 |
| Dry-run output uses `would delete`/`would delete` label and could be miscounted.              | Test fixture covers the dry-run label; count derives from the summary N, label-agnostic.     |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
