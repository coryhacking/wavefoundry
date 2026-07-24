# Exploration-Avoided: Conditional Rendering and Cost Propagation

Change ID: `1tdl8-enh exploration-avoided-render-and-cost-propagation`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-23
Wave: `1tg55 exploration-avoided-signal-quality`

## Rationale

The `## Estimated Exploration Avoided` block has rendered `0 | 0 | 0 | 0` on every wave since it shipped (1svuk). Investigation (2026-07-23, operator-directed) found the metric is wired but its credit preconditions barely intersect real usage, and one precondition is broken by a genuine defect: only 19 of 82 memory records carry a positive `Source exploration cost`, because every record minted through `_memory_add_response_locked` drops the stamp — which includes `memory_validate` REWRITES (the path that produced the most-surfaced advisories, e.g. the fragile-file records) and hand-authored `memory_add(supersedes=...)` successors. The grounding value evaporates on exactly the records that surface most. Separately, the always-rendered zero table is noise in every wave record, while `wf_audit` already displays the number only when positive. Operator decision: render the block only when nonzero, fix the cost-propagation defect at its one minting seam, and explicitly defer any crediting-surface expansion; if the metric remains zero after these fixes, that is recorded evidence for removing it entirely in a follow-up.

## Requirements

1. **Conditional wave.md rendering.** The exploration-avoided projection renders the visible table and caveat prose only when the wave's totals are nonzero. When all totals are zero, the section renders no visible table (the machine `wave:exploration-avoided-state` comment and markers may remain for flush idempotence). A zero-to-nonzero transition adds the table at the next flush. Closed waves' historical blocks are never rewritten. `wf_audit`'s existing positive-only display is unchanged.
2. **Supersession cost propagation.** When a new record is minted superseding another (both the `memory_validate` rewrite path and `memory_add` with `supersedes=`), the new record inherits the superseded record's `source_exploration_cost` unless a cost is explicitly provided. Records minted without any supersession link keep today's behavior (no stamp unless provided).
3. **Backfill drafts stop stamping zero.** `memory_supply` omits the `Source exploration cost:` line when the measured cost is 0 (a zero grounds nothing and reads as false precision); the estimator's skip-nonpositive behavior is unchanged.
4. **Crediting surfaces are explicitly NOT expanded.** The exact-match, action-time-only credit discipline (per-path advisories and targeted briefs) is the anti-inflation guarantee; prepare/review advisory surfaces remain non-crediting. Recorded as a decision, not an omission.
5. **Tests:** conditional-render both directions (zero renders no table; nonzero renders it; flush idempotent), rewrite-path inheritance, `supersedes=` inheritance, explicit-cost override, no-supersession non-inheritance, and backfill zero-omission. Existing estimator invariants unmodified.

## Scope

**Problem statement:** a permanently-zero table renders on every wave, and the metric's grounding stamp is dropped by the minting seam that produces the most-surfaced records.

**In scope:**

- `exploration_avoided.py` conditional projection rendering
- The `_memory_add_response_locked` minting seam: supersession cost inheritance (covers `memory_validate` rewrite and `memory_add(supersedes=)`)
- `memory_supply` zero-stamp omission
- Tests for all three behaviors; memory README / context-efficiency reference notes

**Out of scope:**

- Crediting at prepare/review advisory surfaces (deliberate; anti-inflation discipline)
- Backfilling cost stamps onto existing records (history is not rewritten; inheritance applies from now on)
- Removing the metric (named follow-up ONLY if it stays zero after these fixes)
- Changing attribution factors or the exact-match confidence gate

## Acceptance Criteria

- [x] AC-1: a wave with all-zero exploration-avoided totals renders no visible table in wave.md; a nonzero wave renders the table with the caveat; the flush is idempotent in both states and the transition adds the table; closed waves are untouched.
- [x] AC-2: a `memory_validate` rewrite inherits the superseded record's positive `Source exploration cost`; a `memory_add(supersedes=...)` successor inherits likewise; an explicitly provided cost wins; a non-superseding add stays unstamped.
- [x] AC-3: backfill drafts with measured cost 0 omit the line; drafts with positive cost keep it; the estimator's behavior is byte-unchanged.
- [x] AC-4: docs gate and full framework suite green; the reference docs state the conditional rendering and inheritance rules plus the explicit non-expansion decision.

## Tasks

- [x] Conditional projection + flush-idempotence tests.
- [x] Supersession inheritance at the minting seam + inheritance/override tests.
- [x] Zero-stamp omission + test; reference-doc notes; docs gate; full suite.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| render | implementer | — | exploration_avoided.py projection |
| propagation | implementer | — | One minting seam covers both paths |
| verification | qa-reviewer | render, propagation | Both-direction render + inheritance matrix |

## Serialization Points

- None; the render and propagation surfaces are independent.

## Affected Architecture Docs

- `docs/references/context-efficiency.md` (rendering + inheritance notes). No boundary or flow changes.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The noise being removed, without rewriting history. |
| AC-2 | required | The genuine defect: grounding must survive supersession. |
| AC-3 | important | False-precision cleanup; estimator-neutral. |
| AC-4 | required | Standard gates + the recorded non-expansion decision. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-23 | Drafted from the operator-directed investigation: credit requires exact-target match + positive stamped cost + action-time surface + open wave; 19 of 82 records carry positive cost; the minting seam (`_memory_add_response_locked`) drops the stamp for rewrites and supersedes-adds; only the wave.md projection renders when zero (`wf_audit` already gates); lint carries no EA validation, so conditional rendering is lint-safe. | Session censuses (`code_keyword`/`code_read` over `exploration_avoided.py`, `server_impl.py` credit sites, memory-corpus grep) |
| 2026-07-23 | Implemented. Render: `render_checkpoint_block` emits markers + machine state only when all totals are zero (heading/table/caveat appear only nonzero); the existing heading-aware `replace_checkpoint_block` handles both transitions, including collapsing a legacy full zero table on the next flush. Inheritance: `_memory_add_response_locked` gains `_source_exploration_cost` (explicit wins) and inherits a POSITIVE cost from the `supersedes` target. LIVE-CAUGHT during testing: the rewrite path passes no `supersedes` into the minting call (supersession is applied to the OLD record afterwards), so param-keyed inheritance never fired for the primary defect case — the rewrite site now passes the predecessor's cost explicitly; also the lock-acquisition re-entry was not forwarding the new parameter (and, latently, `_defer_index_refresh` — forwarded now, behavior-neutral since no caller uses it without the lock). Supply: measured cost 0 becomes an omitted stamp (None), not `Source exploration cost: 0`. | `exploration_avoided.py`; `server_impl.py`; `memory_supply.py`; `test_memory_records` 168 OK |
| 2026-07-23 | Tests: zero-state markers-only render + flush idempotence + legacy-table collapse + zero-to-nonzero transition (single heading); `SupersessionCostInheritanceTests` matrix (supersedes-add inherits, rewrite inherits, explicit wins, non-superseding unstamped, zero-cost predecessor not stamped); propose zero-omission dry-run + created-record assertions. Docs: estimated-exploration-avoided reference gains the two new invariants; memory README's cost section documents omission + inheritance. | New tests in `test_memory_records.py`; doc diffs |
| 2026-07-23 | Full-suite verification took three runs to land honestly: two loaded runs failed in `test_repeated_warm_estimator_and_projection_budgets` (a warm p95 25ms budget assertion; 29.7ms under concurrent suite/MCP load), which also retroactively explains the unnamed 1tbt7-review flake; the test passes in isolation and the QUIET full run is green: 6,181 tests across 59 files OK, zero failures. Docs gate clean. The flake is captured as active memory `1tdvh-mem warm-perf-budget-test-flakes-under-load` and is follow-up material (load-aware budget), out of this wave's scope — the timing path is untouched by this change and the first failure predates it. | Quiet suite log; isolation run; memory record |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-23 | Render only when nonzero; keep the machine state comment. | A permanently-empty table is noise; the state comment preserves flush idempotence and the zero-to-nonzero transition. | Removing the metric now (premature — the propagation fix may light it up); rendering always (the status quo being corrected). |
| 2026-07-23 | Inherit cost through supersession at the one minting seam. | The learning's grounding exploration is the same across a rewrite or successor; the stamp dropping there is why the most-surfaced records ground nothing. | Backfilling stamps onto history (rewrites records); stamping at validate-time only (misses hand-authored supersessions). |
| 2026-07-23 | Do not expand crediting surfaces. | The exact-match action-time discipline is the anti-inflation guarantee that makes the estimate honest; broad prepare/review crediting would inflate it. | Crediting prepare/review advisories (rejected); if the metric stays zero after these fixes, remove it in a follow-up with that evidence. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Conditional markers break a consumer expecting the table. | Census found no parser of the table (audit reads the store, lint validates nothing here); tests pin both render states. |
| Inheritance stamps a wrong cost on a semantically new record. | Inheritance applies only through explicit supersession links, where the grounding exploration is shared by construction; explicit cost always wins. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
