# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-07-20
review-evidence-source: events.jsonl

wave-id: `1sq9i freshness-false-stale-fix`
Title: Freshness False Stale Fix

## Objective

Fix the one-sided ignore-path filtering in `project_layer_freshness` that makes `code_ask` report a permanent false `index_freshness: "stale"` on any repo with a generated codebase map (a 1.13.0-new, default-hitting field bug). Read-side uniform ignore filter heals stuck indexes in place; must land before the 1.13.0 release.

## Changes

Change ID: `1sq9h-bug freshness-ignore-path-false-stale`
Change Status: `implemented`

Completed At: 2026-07-16

## Wave Summary

Wave `1sq9i` (Freshness False Stale Fix) delivered one change: Freshness reports permanent false-stale for ignore-listed recorded layer-state paths.

**Changes delivered:**

- **Freshness reports permanent false-stale for ignore-listed recorded layer-state paths** (`1sq9h-bug freshness-ignore-path-false-stale`) — 5 ACs completed. Key decisions: Read-side uniform ignore filter (state loop + eligible); Fold into unreleased 1.13.0
## Journal Watchpoints

- `indexer.py` is edited under the `framework_edit_allowed` gate — open before editing, close immediately after.
- Blocking: this fix must land in the 1.13.0 pack before release; the false-stale signal is new in 1.13.0 (wave 1seav) and default-hitting.
- Watchpoint: the regression probe must fail against the pre-fix code (prove non-vacuity by source mutation), not just pass post-fix.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

<details class="wavefoundry-review-evidence">
<summary>Machine review evidence — 5 records; 2 runs; 0 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 0</summary>
</details>
<!-- wave:finding-synthesis end -->

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-07-16: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, architecture-reviewer; rotating-seat: architecture-reviewer; strongest-challenge: the regression probe must be proven non-vacuous by source mutation, not merely pass post-fix — carried as an implementation watchpoint; strongest-alternative: build-side stop-stamping ignore paths into layer state — rejected as primary because it only heals after a rebuild, whereas the read-side filter fixes already-stuck indexes in place.)
- prepare-council seat — red-team: confirmed against the tree that the fix targets the real firing branch (`docs/references/codebase-map.md` ∈ docs state ∩ `_PROJECT_STALE_IGNORE_PATHS` ∩ absent from `filtered_file_meta` ⇒ the "recorded path gone" branch at indexer.py:1466-1473). Filtering ignore paths from `eligible` cannot hide a genuine staleness — every `_PROJECT_STALE_IGNORE_PATHS` member regenerates each build and is ignored by contract, and non-ignore paths remain fully checked. Read-side change heals existing indexes without a rebuild (freshness is a read-time computation; stored state is untouched).
- prepare-council seat — architecture-reviewer: the defect is a broken invariant (ignore filter applied to walk + snapshot but not state + eligible); restoring uniform ignore discipline across all four comparison inputs is the principled fix. No contract/boundary change — `project_layer_freshness` signature/return, `_index_freshness_verdict`, and the `code_ask` envelope are unchanged; `wave_index_health` uses a separate path and is unaffected; the change is localized to one function.

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- wave-council-readiness: approved 2026-07-16 — root cause is confirmed against the tree (field report + local reproduction); the fix is a minimal, read-side uniform ignore filter with a clear non-vacuity requirement (AC-3 fails pre-fix); scope is one function + one regression test; no boundary/contract change. No blocking concerns.
- operator-signoff: pending operator closure confirmation

## Dependencies

- No external wave dependencies.
