# Readiness Findings Need A Same-Phase Clearing Path

Change ID: `1tmb0-bug review-loop-has-no-readiness-clearing-path`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-26
Wave: `1tj0l cwd-independent-host-surface-launchers`

## Rationale

Executable review evidence currently has a complete delivery repair loop but no honest readiness
repair loop. A readiness finding may be introduced only as `readiness` at cycle 0. `repair_start`
requires a preceding `initial_delivery`, and `reverification` requires `repair_start`. The result is
that a plan can carry blocking `do_now` findings while `wave-council-readiness` remains approved and
`wf_prepare_wave` reports no repairs needed. The only documented way to terminalize those findings is
to claim delivery review began, implement first, and repair the plan finding later.

Wave `1tj0l` proves the contradiction on the live corpus: eleven readiness findings are pending while
the readiness approval projects as current and `wf_prepare_wave(mode="dry_run")` reports
`repairs_needed: 0`. This is not merely confusing prose. It prevents the desired review -> repair ->
independent re-review loop from finishing in the phase where the defect was found.

The smallest correction reuses the existing `repair_start` and `reverification` kinds. A cycle-1
`repair_start` may follow a cycle-0 readiness synthesis while the wave is still planned/readied; its
reverification remains subject to the existing lane, freshness, independence, and evidence-integrity
rules. No readiness-specific record kinds or second ledger are introduced.

## Requirements

1. A blocking readiness finding with a pending repair makes `wave-council-readiness` stale/withheld
   until the finding reaches a terminal current head.
2. For a finding born at readiness, cycle-1 `repair_start` is accepted after its cycle-0 readiness
   synthesis without requiring an `initial_delivery` record.
3. `reverification` follows that repair exactly as it does in delivery: the required independent lane
   clears only its own lane, and the readiness approval may be recorded only after every blocking
   readiness finding is terminal.
4. Delivery-born findings retain the existing `initial_delivery -> repair_start -> reverification`
   grammar. The readiness exception must not weaken delivery chronology.
5. Seed 209 and the MCP tool contract show both legal sequences and route each rejection to the exact
   corrective call. They must not instruct agents to carry a repaired plan finding into delivery.
6. Existing ledgers remain readable. This changes validation of new transitions and approval
   currency; it does not rewrite historical events.

## Scope

**In scope:**

- `.wavefoundry/framework/scripts/review_evidence.py`: readiness approval staleness and the
  predecessor rule for `repair_start`.
- `.wavefoundry/framework/scripts/server_impl.py`: compact tool guidance and any readiness projection
  that currently claims open findings do not affect readiness.
- `.wavefoundry/framework/seeds/209-agent-harness-core.prompt.md`: same-phase recipe and rejection
  recovery guidance.
- Focused review-evidence, lifecycle, install/upgrade render, and prompt-carrier tests.
- `docs/contributing/review-and-evals.md` and rendered prompt surfaces.

**Out of scope:**

- New run kinds, schema fields, ledgers, or lifecycle phases.
- Weakening fresh-context or repairer-versus-reverifier independence.
- Requiring non-blocking `maybe_later`, `dont_do_later`, or `not_issue` observations to block
  readiness.
- Rewriting historical ledgers that were valid under the prior rule.

## Acceptance Criteria

- [x] AC-1: A real readiness finding makes `wave-council-readiness` withheld and
  `wf_prepare_wave` reports the blocking finding rather than `repairs_needed: 0`.
- [x] AC-2: The validator accepts
  `readiness(cycle 0) -> repair_start(cycle 1) -> reverification(cycle 1) -> readiness approval`
  without any `initial_delivery` record.
- [x] AC-3: The same sequence fails when the repair actor attempts to clear its own lane, freshness or
  independence is false, the required lane is unchanged, or reverification precedes repair start.
- [x] AC-4: A delivery-born finding still rejects `repair_start` without `initial_delivery`; the
  readiness exception is finding-origin-specific rather than global.
- [x] AC-5: A plan with two findings remains withheld after only one is repaired and becomes eligible
  only after both current heads are terminal.
- [x] AC-6: Seed 209, MCP tool guidance, and `review-and-evals.md` carry the two legal recipes and no
  longer teach readiness carry-forward as the normal repair mechanism.
- [x] AC-7: Existing closed-wave ledgers validate unchanged, install and upgrade render the corrected
  carriers, docs lint passes, and the full framework suite is green.

## Tasks

- [x] Add failing lifecycle fixtures for AC-1 through AC-5 before changing the validator.
- [x] Implement the readiness-origin predecessor and approval-currency rules without new record kinds.
- [x] Update seed 209 and tool guidance under the required edit gates; regenerate surfaces.
- [~] Exercise this wave's own readiness findings through the new path before implementation begins — intentionally not met: this change repairs the bootstrap path itself, so the corrected mechanism could only execute after the first implementation edit; chronology is recorded rather than backfilled.
- [x] Run focused tests, install/upgrade render tests, docs lint, and the full suite.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| lifecycle-red-tests | implementer | — | Exact live 1tj0l contradiction plus controls |
| validator | implementer | lifecycle-red-tests | Reuse existing run kinds |
| carriers | implementer | validator | Seed, MCP guidance, rendered docs |
| self-hosted-proof | code-reviewer | carriers | Clear 1tj0l readiness findings in readiness |

## Serialization Points

- This change is implemented before the other `1tj0l` changes so the wave can terminalize its
  readiness findings honestly before launcher code edits begin.
- Framework and seed gates are opened only around their respective edits and closed immediately.
- Seed 209 is rendered through the canonical surface renderer; generated files are never hand-edited.

## Affected Architecture Docs

`docs/contributing/review-and-evals.md` must describe the same-phase readiness loop and the unchanged
delivery loop. No ADR is needed: this closes a missing transition in the existing executable-evidence
protocol without adding a new protocol concept.

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | A gate that reports approval over blocking plan findings is misleading. |
| AC-2 | required | This is the missing transition. |
| AC-3 | required | Same-phase repair must preserve independent verification. |
| AC-4 | required | Prevents the exception from weakening delivery chronology. |
| AC-5 | required | Proves aggregate rather than single-finding correctness. |
| AC-6 | important | Keeps agent behavior aligned with the grammar. |
| AC-7 | required | Compatibility and distribution gate. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-26 | Reversed the earlier carry-to-delivery proposal after independent review executed the live 1tj0l state: eleven open readiness findings coexist with an approved readiness row and `repairs_needed: 0`. The bounded replacement reuses `repair_start` and `reverification` in readiness rather than adding record kinds. | `wf_review_event(list)`; `wf_prepare_wave(1tj0l, dry_run)`; `review_evidence.py` predecessor rule |
| 2026-07-26 | Implemented same-phase readiness repair grammar and current-head approval semantics. Readiness-born findings may progress through the existing repair/reverification chain without an `initial_delivery` record; delivery chronology remains unchanged. Closed ledgers are compared under their historical projection so the fix does not rewrite archives. | `test_review_evidence.py`, `test_docs_lint.py`, `test_server_tools.py`, `test_dashboard_server.py`, `test_upgrade_wavefoundry.py` |
| 2026-07-26 | The first canonical full-suite run caught two stale lifecycle fixtures and forced the phase boundary to be explicit: readiness-born current heads affect readiness; delivery-born repairs never reopen the crossed readiness gate. Unknown historical/synthetic phase retains explicit lane behavior. | Pre-repair `WaveLifecycleMutationTests` failures; focused review-evidence and lifecycle tests green after phase-aware repair |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-26 | Permit existing repair kinds to terminalize readiness-born findings before implementation. | It preserves chronology and the established independent lane-clearing machinery with the smallest grammar change. | Carry findings into delivery (rejected: claims readiness while blocking plan defects remain); add readiness-specific kinds (rejected: duplicate protocol); ignore findings for readiness (rejected: current confusing behavior). |
| 2026-07-26 | Current unresolved finding heads withhold approval even when an approval record is newer; terminal repairs stale only approvals that predate the repair. | Record order alone cannot convert an unresolved finding into a pass. This closes the exact state that made the open wave look ready while eleven findings remained pending. | Treat the latest approval as authoritative regardless of current findings (rejected: recreates the defect); add a new readiness-only approval kind (rejected: unnecessary schema). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| The exception accidentally permits delivery repair without initial delivery | AC-4 pins finding-origin-specific behavior. |
| Readiness becomes impossible after any observation | Only actionable blocking current heads stale approval; terminal and non-blocking outcomes do not. |
| Old ledgers fail validation | AC-7 validates the closed corpus byte-for-byte without rewriting it. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
