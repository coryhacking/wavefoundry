# Multi-finding repair-cycle authoring

Change ID: `1sua7-bug multi-finding-repair-cycle-authoring`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-17
Wave: `1stwj context-efficiency-telemetry`

## Rationale

The executable-review protocol documents multiple findings in one reviewer
context and cycle as the normal review shape, and the typed authoring surface
assigns each finding a distinct idempotency identity. Initial delivery supports
that shape. Repair recording does not: every compact finding call emits its own
`review_run`, while relationship validation permits only one `repair_start` and
one `reverification` run per cycle. The second repaired finding therefore fails
with `repair cycle N has more than one repair_start`.

This reproduced while recording five independently verified repairs for wave
`1stwj`. The implementation defects are closed, but the canonical ledger cannot
represent their truthful shared repair cycle without inventing sequential
cycles. Closure must remain fail-closed until the public authoring path can
record the real history.

## Requirements

1. Preserve the existing per-finding compact authoring API and idempotency
   identity. Multiple distinct findings using the same actor/context/run kind
   and cycle must append distinct per-finding bundles without collision.
2. Treat a repair cycle as a group of findings, not as one physical run.
   Exactly one `repair_start` is permitted per `(cycle, finding_id)`, while a
   historical batch run may start several actionable findings at once.
   Existing actor/context/finding/kind/cycle identity plus request digest
   remains the exact-retry and conflicting-retry boundary.
3. Permit ordered same-cycle `reverification` progress for one finding because
   each fresh independent actor may clear only its own required lane. A
   reverification may advance only a finding with an earlier `repair_start` in
   that cycle. The finding becomes cycle-terminal only when its current
   same-cycle head either (a) comes from reverification, has repair state
   `completed`, and has no `blocking_required_lanes`, (b) truthfully
   reclassifies the finding to `not_issue` or `dont_do_later` with
   `not_required` repair state and no required lanes, or (c) carries the
   protocol's valid distinct `operator_waived` state and waiver metadata with
   no unresolved required lanes. A waiver is never relabeled as completed or
   independent verification.
4. Starting cycle N+1 remains prohibited until every started finding in cycle N
   is complete. Once a cycle is complete, later repair starts cannot be appended
   retroactively to that cycle.
5. Automatic cycle-2 convergence checkpointing occurs only after all findings
   started in cycles 1 and 2 are cycle-terminal. The checkpoint freezes the
   then-current synthesis heads, never a partially reverified cycle.
6. Preserve single-finding history validity, initial-delivery multi-finding
   behavior, and already-valid batch repair histories in which one
   `repair_start` or `reverification` run seals several candidate findings.
   Cycle membership is derived from actionable synthesis rows, not from every
   candidate in a mixed-disposition batch.
7. Preserve append-only canonical events, per-finding operation identities,
   approval freshness, lane reassessment authority, operator-waiver semantics,
   and closure semantics. `operator_waived` remains a lower-level/legacy
   validator-compatible residual-risk terminal state, not completed
   reverification; the compact tool does not gain waiver authoring in this
   change.
8. Prove the correction through the registered
   `wave_record_review_evidence` path, not hand-authored JSONL, including a
   faithful temporary replay of the five-finding `1stwj` repair shape.
9. A later delivery-review pass may discover a new finding at any point. The
   typed authoring path must append it without decreasing the repair-cycle
   counter or pretending it had a prior repair start. After recording the
   finding, the coordinator records `repair_start` before mutation, repairs it
   immediately, and reverifies it in the currently open cycle when that cycle
   remains partial. Only an already-terminal aggregate cycle forces the next
   cycle number; that numbering is chronology, not another council or delayed
   repair round.

## Scope

**Problem statement:** The compact authoring surface emits one review run per
finding, but repair-cycle validation models a cycle as exactly one run. That
internal contradiction blocks normal multi-finding repairs.

**In scope:**

- Repair-cycle relationship validation and completion derivation.
- Convergence-checkpoint emission after aggregate cycle completion.
- Compact authoring regressions for multi-finding repair and reverification.
- Recording the existing `1stwj` repair evidence through the corrected tool.
- Protocol/reference wording needed to make the aggregate semantics explicit.

**Out of scope:**

- A new batch request schema or new MCP tool.
- Changing finding judgment fields, actionability, lane reassessment, approval
  freshness, or evidence integrity rules.
- Rewriting historical event records or weakening closure gates.
- Treating separate findings as fabricated sequential repair cycles.

## Acceptance Criteria

- [x] AC-1: Two or more distinct findings can record `repair_start` in the same
  cycle through the public typed tool; a second start for the same finding and
  cycle fails closed, while an exact identified retry replays. (required)
- [x] AC-2: One finding with two required lanes can record two ordered,
  fresh-independent same-cycle reverifications through the public tool. The
  first clears only its actor's lane and leaves the cycle partial; the second
  clears the final lane and makes the finding cycle-terminal. (required)
- [x] AC-3: Cycle N+1 cannot start before all cycle-N findings complete, and a
  completed cycle cannot be extended retroactively. (required)
- [x] AC-4: The cycle-2 convergence checkpoint appears exactly once and only on
  the reverification that completes the final outstanding cycle-2 finding; its
  frozen boundary contains every then-current finding head. (required)
- [x] AC-5: Existing single-finding, initial-delivery multi-finding,
  idempotency/conflict, approval-freshness, operator-waiver, and closure tests
  remain green. A legacy fixture with one multi-candidate repair-start run and
  one multi-candidate reverification run remains valid, including a
  mixed-disposition candidate set. (required)
- [x] AC-6: A registered public-path fixture reproducing the five-finding,
  multi-lane
  `1stwj` shape records one shared repair cycle without fake cycle increments,
  and the live wave can subsequently record its real verified repairs through
  the same tool. (required)
- [x] AC-7: Canonical seed 209, the project protocol reference, and the public
  MCP contract describe aggregate cycle completion. Thin rendered carriers
  remain synchronized pointers, and carrier-registry/install/upgrade/package
  distribution tests prove the updated canonical seed and implementation ship
  without rewriting target wave history. (required)
- [x] AC-8: Canonical framework tests and docs lint pass; no canonical JSONL is
  edited by hand. (required)
- [x] AC-9: A later registered delivery-review pass can append a newly
  discovered actionable finding through `wave_record_review_evidence`; the
  finding can start, repair, and reverify immediately in the currently open
  partial cycle, while only a finding discovered after aggregate completion
  uses the next cycle number. Exact replay/conflict, lane, approval, and
  convergence rules remain fail-closed. (required)

## Tasks

- [x] Add aggregate per-cycle/per-finding repair-state derivation.
- [x] Replace one-run-per-cycle validation with one-start-per-finding,
  multi-lane reverification progress, and aggregate-completion rules.
- [x] Delay convergence checkpoint emission until aggregate cycles 1 and 2 are
  fully complete.
- [x] Add compact authoring, two-lane, legacy batch, validator, closure, and
  five-finding public-path regressions.
- [x] Update protocol/reference wording for multi-finding repair cycles.
- [x] Regenerate/verify public carriers and install/upgrade propagation.
- [x] Record `1stwj` repair and reverification evidence through the corrected
  public tool, then run review/close dry-runs.
- [x] Run focused and full framework verification.
- [x] Permit and regression-test newly discovered findings in later review
  passes without fabricated cycle decreases or prior repair starts.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| cycle semantics | implementer | — | validator + reusable completion derivation |
| authoring checkpoint | implementer | cycle semantics | convergence timing |
| regression matrix | qa-reviewer | cycle semantics | public tool and known-bad cases |
| live reconciliation | coordinator | regression matrix | typed tool only |

## Serialization Points

- `review_evidence.py` cycle derivation must land before server/tool fixtures.
- Open both `framework_edit_allowed` and `seed_edit_allowed` before their
  respective implementation edits and close each after verification.
- The live `events.jsonl` ledger is mutated only after focused tests pass, through
  `wave_record_review_evidence` under its existing lock.
- Delivery approval remains withheld until the expanded wave is independently
  reviewed.

## Affected Architecture Docs

- `.wavefoundry/framework/seeds/209-agent-harness-core.prompt.md` — canonical
  repair-cycle and convergence contract.
- `docs/contributing/review-and-evals.md` — clarify that one cycle may contain
  multiple per-finding runs and completes only as an aggregate.
- `docs/architecture/testing-architecture.md` — record the multi-finding
  public-path regression obligation if not already covered by the protocol
  reference.
- `docs/specs/mcp-tool-surface.md` and the registered tool docstring — replace
  singular reverification/checkpoint timing with final-outstanding aggregate
  completion.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | This is the reproduced public authoring failure. |
| AC-2 | required | Partial and complete cycle state must be truthful. |
| AC-3 | required | Preserve monotonic repair chronology. |
| AC-4 | required | Prevent premature convergence freeze. |
| AC-5 | required | Backward compatibility is load-bearing. |
| AC-6 | required | The current wave must be representable without fabrication. |
| AC-7 | required | Canonical protocol/tool wording and shipped thin-pointer distribution must stay synchronized. |
| AC-8 | required | Shipped framework and docs must remain clean. |
| AC-9 | required | Later findings must join an open repair cycle without inventing another review round. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-07-17 | Defect reproduced while recording five verified `1stwj` repairs. | First `repair_start` appended; second returned `repair cycle 1 has more than one repair_start`. |
| 2026-07-17 | Guru pass confirmed an implementation/design contradiction. | Compact builder emits one candidate/run per finding; validator stores one run position per cycle; `1sl65` explicitly calls same-context/cycle multi-finding review normal. |
| 2026-07-17 | Fresh readiness review blocked the first repair plan. | The duplicate rule contradicted one-lane-per-actor reassessment, legacy batch repair runs were omitted, waiver wording implied false completion, the canonical carrier path was wrong, and the wave packet still described one change. |
| 2026-07-17 | Repaired plan re-readied before code edits. | Fresh red-team and docs-contract rechecks passed; wave paused, re-prepared, and returned to implementing before both edit gates opened. |
| 2026-07-17 | Aggregate repair-cycle implementation and public fixtures completed. | Five-finding/multi-lane public replay, exact retry/conflict, partial-cycle, late-start, terminal-repeat, legacy batch/checkpoint, distinct waiver, and final-outstanding convergence fixtures pass. |
| 2026-07-17 | Historical compatibility caught and repaired during verification. | First docs-lint run exposed `1skt1`'s valid convergence-checkpoint synthesis terminal shape; helper expanded to preserve it and a regression was added without editing the historical ledger. |
| 2026-07-17 | Canonical verification green. | Final exact-tree `run_tests.py`: 5,710 tests across 52 files, OK; docs-lint clean; setup/upgrade/carrier/package focused suites green; live MCP reload propagated the updated tool description. |
| 2026-07-17 | Live shared-cycle authoring and repeated review proven. | The corrected registered tool appended all five cycle-1 repair starts, then 20 ordered lane-scoped reverifications across code, architecture, QA, performance, and docs reviewers. Every actor cleared only its own lane; no fake cycle increments or hand-authored JSONL. |
| 2026-07-17 | Delivery follow-up repaired two adjacent contract gaps. | Truthful actionable-to-`not_issue` / `dont_do_later` reverification now terminalizes without breaking historical checkpoint-only boundary rows; all direct telemetry buffer/focus operations fail isolated so wedged telemetry cannot replace a successful lifecycle result. |
| 2026-07-17 | Later-finding authoring now joins the currently open partial repair cycle. | The registered tool accepted a newly discovered paired-residual finding after earlier repairs, then recorded its cycle-2 `repair_start` before mutation. Fixtures prove a later finding uses the open cycle while only post-terminal discovery advances the cycle number. |
| 2026-07-17 | Close-time approval chronology was scoped to lifecycle phase after a post-convergence dry-run exposed a readiness false block. | Historical `wave-council-readiness` remains required and identity-validated but is never retroactively staled by delivery repairs. Fresh architecture and QA reviewers replayed the pre-fix failure, a 17-case chronology matrix, public close behavior, and adjacent operator/delivery/specialist controls; canonical suite 5,744/5,744. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-07-17 | Keep per-finding tool calls and aggregate them by cycle. | Preserves public schema, per-finding identities, append-only records, and existing reviewer ergonomics. | Add a batch MCP schema (unnecessary new contract); invent one cycle per finding (dishonest chronology); hand-edit JSONL (prohibited). |
| 2026-07-17 | A cycle completes only when every started finding reaches a valid terminal head. | Prevents cycle advancement and convergence over partial repair state while preserving the protocol's distinct operator-waiver path. | Complete on first reverification (current latent defect under multi-run support); call waiver completion (false evidence claim). |
| 2026-07-17 | Same-cycle reverification is progressive and lane-scoped. | A fresh independent actor can clear only its own required lane; a finding is terminal only after the final required lane is cleared. | Reject duplicate finding/kind/cycle runs (would strand multi-lane findings); let one actor clear every lane (breaks authority). |
| 2026-07-17 | Preserve legacy batch runs and keep waiver authoring out of scope. | Existing valid ledgers may seal several candidates in one run; compact authoring has no waiver input and must not relabel residual-risk acceptance as verification. | Force migration to per-finding runs (unnecessary compatibility break); expand the public waiver schema (unrelated scope). |
| 2026-07-17 | Encourage repeated fix/review loops while the action matrix yields unresolved findings. | Same-cycle runs represent lane progress; a later cycle represents a later repair pass. The protocol should converge through evidence, not impose a one-run ceiling. | Stop after one review (strands repairs); increment a cycle per lane/finding (fabricates chronology). |
| 2026-07-17 | Discovery is cycle-neutral; repair work owns cycle numbering. | A reviewer can report a new finding at any pass, then the repair joins the open aggregate cycle. This separates evidence chronology from repair bookkeeping and permits review-and-repair in one loop. | Require a new council/review round for each finding (unnecessary churn); backdate the finding into an earlier run (false chronology). |
| 2026-07-17 | Approval freshness is scoped to the lifecycle authority the approval represents. | Prepare readiness proves the pre-implementation plan gate and cannot logically be recreated after delivery repair; delivery, specialist, and operator approvals remain subject to their existing affected/final chronology. | Re-sign readiness after every delivery repair (retroactive evidence); stop validating readiness at close (weakens the historical stage gate). |

## Risks

| Risk | Mitigation |
| --- | --- |
| Partial multi-finding or multi-lane cycles accidentally count as complete | Derive each finding's terminal state from its current same-cycle reverification head with completed repair state, a truthful `not_issue` / `dont_do_later` reclassification with `not_required` repair state, or a valid distinct operator waiver; every terminal form also requires no unresolved lanes, and completion aggregates across all started actionable findings. |
| A late start mutates a completed cycle | Reject repair starts once the cycle is complete. |
| Convergence checkpoint freezes too early | Emit only when aggregate cycles 1 and 2 are complete after the proposed append. |
| Existing single-finding or batch ledgers regress | Preserve the one-element case and expand historical batch runs by their actionable synthesis rows. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
