# Context Efficiency: per-stage savings must reconcile with the displayed total

Change ID: `1sx2f-bug context-efficiency-stage-total-reconciliation`
Change Status: `implemented`
Owner: framework
Status: implemented
Last verified: 2026-07-18
Wave: `1sxj7 self-populating-memory-and-telemetry-reconciliation`

## Rationale

The per-wave `## Context Efficiency` table does not add up. Observed:

```
| Stage     | Tool calls | Estimated token savings |
| close     |          3 |                      54 |
| implement |          1 |                   1,137 |
| review    |          2 |                       0 |
| **Total** |          6 |                     334 |
```

`54 + 1,137 + 0 = 1,191`, but the total is `334`. Root cause (confirmed in
`context_efficiency.py`): each stage's displayed `estimated_tokens_saved` is
`max(0, direct_net + matched_pair_residual)` (`~:1435`), so a stage whose
`direct_net` is negative shows `0`; but the **total** is
`max(0, totals.direct_net + residual)` where `totals.direct_net` sums the
**raw, unclamped** per-stage `direct_net` (`~:1441`/`~:1450`). So the review
stage here is genuinely `-857` (its request+response tokens exceeded the source
content it surfaced, which is normal for a review that records evidence and
returns little source), shown as `0` per stage but subtracted as `-857` in the
total: `54 + 1,137 - 857 = 334`.

The number is not wrong; the presentation is inconsistent, so the column cannot
be reconciled against the total.

## Requirements

1. **Count a net-negative stage as `0`, everywhere.** A stage whose savings would
   be negative counts as `0` in its own row (already the case) AND in the total.
   No negative savings value is ever shown; no label is added. Savings stay
   `>= 0`.
2. **The total is the sum of the displayed (floored) per-stage values.** With the
   observed data the total becomes `54 + 1,137 + 0 = 1,191`, so the column
   reconciles with the total exactly.
3. The underlying per-call and stored accounting is unchanged; this is a display
   /reporting-consistency fix, not a change to how savings are computed. (The
   per-call `context_avoided` floor and the stored `direct_net`/debit fields keep
   their current meaning; only the total's aggregation of the per-stage savings
   changes from summing raw signed `direct_net` to summing the floored per-stage
   savings.)

## Scope

**Problem statement:** the `## Context Efficiency` per-stage column floors
negative stages to `0` while the total subtracts their raw negative value, so the
stages do not add up to the total.

**In scope (edited under `framework_edit_allowed`):**
- `context_efficiency.py` — the total's `estimated_tokens_saved` is computed as
  the sum of the per-stage floored (`max(0, ...)`) savings, not from the raw
  signed `totals.direct_net`, so stages and total reconcile.
- Tests — `test_context_efficiency.py` / `test_server_context_efficiency.py`: a
  fixture with a net-negative stage asserts each stage shows `>= 0` and the
  displayed stages sum exactly to the displayed total.
- Docs — a one-line note only if needed.

**Out of scope:**
- **Changing how savings are measured** — the per-call floor and the closed-ledger
  accounting are unchanged; only the total's aggregation reconciles with the
  floored per-stage rows.
- **The estimated-exploration-avoided block (1svuk)** — separate, already its own
  labeled line; not touched here.

## Acceptance Criteria

- [x] AC-1: The displayed per-stage `estimated_tokens_saved` values sum exactly to the displayed total for every wave, including when a stage would be net-negative. (required) — the total now sums the floored per-stage savings (`context_efficiency.py`, both `_snapshot_from_conn` and `_normalized_checkpoint_state`); `test_negative_and_positive_stages_reconcile_through_checkpoint_path` drives normalization, render, parse, replace, and unhealthy zeroing and asserts `sum(stages) == total`.
- [x] AC-2: A net-negative stage counts as `0` in both its row and the total; no negative value is shown and no label is added. A fixture with a would-be-negative stage proves stages-sum-to-total with that stage at `0`. (required) — `test_wave_total_is_sum_of_floored_stage_savings` (prepare stage -100 floored to 0, review +200, total 200 = 0 + 200); no label added.
- [x] AC-3: The per-call context_avoided floor and the stored accounting fields are unchanged (measurement is not altered; only the total's aggregation of per-stage savings reconciles). (required) — only the total's `estimated_tokens_saved` aggregation changed; per-stage floor (`:1435`), per-call floor, and stored `direct_net`/debits untouched (the test still asserts `direct_net == 100`).
- [x] AC-4: Full framework suite green; docs-lint clean. (required) — full suite 5802 OK (one unrelated timing flake in test_indexer, passes in isolation); `wave_validate` docs-lint ok after regenerating the 3 closed-wave CE tables whose displayed total changed.

## Tasks

- [x] Compute the total `estimated_tokens_saved` as the sum of the floored per-stage savings in `context_efficiency.py` (not from raw signed `totals.direct_net`).
- [x] Fixture test with a would-be-negative stage: each stage `>= 0`; stages sum to total. — `test_wave_total_is_sum_of_floored_stage_savings`.
- [x] Regenerate the 3 closed-wave CE tables whose displayed total changed (1stwj, 1stwm, 1sufq) so render matches state. — mechanical re-render of the generated marker block; per-stage state data unchanged.
- [x] Full suite + docs-lint.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| fix | framework | — | total = sum of floored per-stage savings in context_efficiency.py |
| verify | framework | fix | would-be-negative-stage fixture; suite |


## Serialization Points

- `context_efficiency.py` — edited under `framework_edit_allowed`.

## Affected Architecture Docs

`N/A` — a display-consistency fix within the telemetry rendering; no boundary or accounting change.

## AC Priority

(Populated at Prepare wave.)


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | Stages must reconcile with the total |
| AC-2 | required | Negatives count as 0, no label, no negative shown |
| AC-3 | required | Do not change measurement, only the total's aggregation |
| AC-4 | required | No regression |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-18 | Change doc authored; operator found the table not adding up | `context_efficiency.py:1435` per-stage `max(0,...)` vs `:1450` total over raw signed sum; observed 54+1137+0 shown but total 334 (review stage = -857) |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-18 | Count a net-negative stage as `0`; total = sum of floored per-stage savings | Operator direction: no negative number shown, no label; savings stay `>= 0` and the column reconciles with the total | Show signed per-stage values so they sum to a signed total (rejected per operator — do not display negatives); leave as-is (rejected — the table is misleading) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Existing tests assert the old total (raw signed sum) | Update the affected assertions to the reconciled floored-sum total; AC-3 keeps the measurement/accounting unchanged |
| A wave that is net-negative overall now reports a small positive total instead of 0-from-negative | Intended: negative stages are counted as break-even (0), which is the operator-chosen presentation; the raw signed `direct_net` remains in the stored state for anyone who needs it |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
