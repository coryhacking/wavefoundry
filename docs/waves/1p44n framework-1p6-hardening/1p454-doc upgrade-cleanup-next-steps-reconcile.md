# Reconcile Upgrade Cleanup Next-Steps Output With Seed-160

Change ID: `1p454-doc upgrade-cleanup-next-steps-reconcile`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-06-08
Wave: 1p44n framework-1p6-hardening

## Rationale

The operator summary printed after an upgrade run drifts from seed-160 (the authoritative editing-pass checklist) and mislabels a step, so an operator reading the console output gets an incomplete and slightly inaccurate sequence.

`_print_operator_summary` in `.wavefoundry/framework/scripts/upgrade_wavefoundry.py:1294-1300` prints exactly 6 items: Drift detection, Journal reconciliation, Spec gaps via seed-230, Docs gate re-run, Index update, and Cleanup lock. Two problems:

1. The list mirrors only part of seed-160 and OMITS the new step-8 backfills that seed-160 enumerates — scan-rules.toml threshold (seed-160:153-158), the `.gitignore` runtime contract (seed-160:152), and `lifecycle_id_policy` (seed-160:151) — as well as any secrets-resolution step. Mirroring is the wrong strategy: it will keep drifting from seed-160 as backfills are added.
2. The journal label at `upgrade_wavefoundry.py:1296` reads `(seed-160 step 0e)`, which is imprecise. In current seed-160 the "Reconcile journals" block is at `160:53` and its sub-items are lettered (a)-(e); `160:58` `(e)` is only "Verify section order", not the reconciliation block. The label should point at the block, not at sub-item (e).

The fix is to make the printed list DEFER to seed-160 as the authoritative editing-pass checklist rather than duplicate every backfill, correct the journal label, and prepend a secrets-resolution step. This is advisory operator output with no behavioral test gate.

## Requirements

1. The printed "Next steps for agent editing pass" list MUST defer to seed-160 as authoritative — prepend a line such as `See seed-160 for the full editing-pass sequence; key steps:` rather than enumerating every seed-160 backfill verbatim.
2. The journal reconciliation label MUST change from `(seed-160 step 0e)` to `(seed-160 step 0 / Reconcile journals)`.
3. A secrets-resolution step MUST be prepended to the list, e.g. `Resolve any docs/scan-findings.json entries via seed-213 before re-running the docs gate`.
4. The list MUST stay short — it must NOT duplicate seed-160's step-8 backfills (scan-rules.toml threshold, .gitignore runtime contract, lifecycle_id_policy) verbatim; deferral replaces enumeration.
5. The existing steps that remain (drift detection, docs gate re-run, index update, cleanup lock) MUST keep their current operator-facing meaning.

## Scope

**Problem statement:** The upgrade cleanup operator summary in `upgrade_wavefoundry.py:1294-1300` diverges from the authoritative seed-160 editing-pass checklist (omits new step-8 backfills and a secrets-resolution step) and mislabels the journal reconciliation step as `(seed-160 step 0e)` when sub-item (e) is only "Verify section order".

**In scope:**

- Editing the `_print_operator_summary` "Next steps" print strings in `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`.
- Prepending a deferral line that points operators to seed-160 as the source of truth.
- Correcting the journal reconciliation label.
- Prepending a secrets-resolution (seed-213) step.

**Out of scope:**

- Changing seed-160, seed-213, or seed-230 content.
- Adding the backfill steps verbatim into the printed list (the whole point is to defer, not duplicate).
- Any non-print behavior of the upgrade flow (drift detection, index rebuild, lock handling logic).

## Acceptance Criteria

- [ ] AC-1: The printed "Next steps" list begins with a deferral line naming seed-160 as the authoritative editing-pass checklist (e.g. `See seed-160 for the full editing-pass sequence; key steps:`).
- [ ] AC-2: The journal reconciliation line reads `seed-160 step 0 / Reconcile journals` and no longer contains the string `step 0e`.
- [ ] AC-3: A secrets-resolution step referencing `docs/scan-findings.json` and seed-213 is present and ordered before the docs-gate re-run step.
- [ ] AC-4: The printed list does NOT enumerate the seed-160 step-8 backfills (no literal `scan-rules.toml threshold`, `.gitignore runtime contract`, or `lifecycle_id_policy` items) — it stays short and defers instead.
- [ ] AC-5 (regression): A test asserts the rendered `_print_operator_summary` output contains the seed-160 deferral line, the corrected journal label, and the secrets-resolution step, and does NOT contain the `step 0e` string. If `_print_operator_summary` is not directly unit-testable, the existing upgrade-script test module is extended to capture its emitted lines.

## Tasks

- [ ] Read seed-160 (`.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`) around lines 53-58 and 151-158 to confirm the current block/label wording before editing.
- [ ] Open a gate as required before editing the framework script (`framework_edit_allowed`), and close it immediately after.
- [ ] Edit `_print_operator_summary` in `upgrade_wavefoundry.py` (lines ~1294-1300): prepend the seed-160 deferral line.
- [ ] Prepend the secrets-resolution (seed-213) step ahead of the docs-gate re-run step.
- [ ] Correct the journal reconciliation label from `(seed-160 step 0e)` to `(seed-160 step 0 / Reconcile journals)`.
- [ ] Confirm the list remains short and does not enumerate seed-160 step-8 backfills.
- [ ] Add/extend a regression test asserting the rendered output (AC-5).
- [ ] Run `python3 .wavefoundry/framework/scripts/run_tests.py` and confirm green.

## Agent Execution Graph


| Workstream            | Owner       | Depends On  | Notes                                                              |
| --------------------- | ----------- | ----------- | ----------------------------------------------------------------- |
| print-string-rewrite  | Engineering | —           | Edit `_print_operator_summary` strings; coordinate on shared file |
| regression-test       | Engineering | print-string-rewrite | Assert rendered output (AC-5)                            |


## Serialization Points

- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py` — the print strings are a SHARED edit surface with sibling changes 1p44o / 1p44p / 1p44q / 1p44r in this wave; sequence this change against those to avoid merge collisions on the same function/region.

## Affected Architecture Docs

N/A — this is an advisory operator-output string change confined to a single function in one framework script; no module boundary, data/control flow, or verification architecture is affected.

## AC Priority


| AC   | Priority   | Rationale                                                                                  |
| ---- | ---------- | ------------------------------------------------------------------------------------------ |
| AC-1 | required   | Deferral to seed-160 is the core fix that stops future drift.                              |
| AC-2 | required   | Correcting the mislabel is the second named defect in the brief.                           |
| AC-3 | required   | Secrets-resolution step is an explicit required addition from the brief.                   |
| AC-4 | important  | Keeping the list short is the design intent; enumeration would re-introduce drift.         |
| AC-5 | important  | Regression guard locks the corrected output; advisory output has no behavioral test gate.  |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
|      |        |          |


## Decision Log


| Date       | Decision                                                                 | Reason                                                                                   | Alternatives                                                                 |
| ---------- | ------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| 2026-06-08 | Defer the printed list to seed-160 instead of mirroring its backfills.   | Mirroring keeps drifting as seed-160 adds step-8 backfills; deferral is drift-resistant. | Enumerate all seed-160 steps in the print output (rejected — duplication).   |
| 2026-06-08 | Relabel journal step as `seed-160 step 0 / Reconcile journals`.          | `(e)` in seed-160 is only "Verify section order"; the reconciliation block is step 0.    | Keep `step 0e` (rejected — imprecise) or drop the label (loses traceability).|


## Risks


| Risk                                                                          | Mitigation                                                                            |
| ----------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| Concurrent edits to `_print_operator_summary` by sibling changes collide.     | Honor the serialization point; sequence against 1p44o/1p44p/1p44q/1p44r.              |
| Deferral line drifts if seed-160 step numbering changes again.                | Reference the block name ("Reconcile journals"), not a line number, in the label.     |
| Regression test asserts on brittle full-string match.                         | Assert on substring presence/absence (deferral line, label, secrets step) only.       |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
