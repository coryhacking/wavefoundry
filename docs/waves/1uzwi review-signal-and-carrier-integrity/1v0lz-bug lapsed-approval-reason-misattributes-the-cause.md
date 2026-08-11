# A Lapsed Approval's Reason String Misattributes The Cause

Change ID: `1v0lz-bug lapsed-approval-reason-misattributes-the-cause`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-08-10
Wave: 1uzwi review-signal-and-carrier-integrity

## Rationale

When a readiness approval lapses because its `policy_receipt_id` no longer matches the current receipt, the projected review-status reason reads **"approval evidence has invalid actor or independence"**. The actor is valid and the independence flags are true; the failed conjunct is receipt currency. Wave `1uwpf` hit this live: after three legitimate supersessions, all five lapsed approvals displayed the misleading string in the wave record's own `wave:review-status` table, and the readiness reverification (red-team seat) traced it to the validity chain in `review_evidence.py` — the reason is derived from the composite `approval_valid` expression rather than from which conjunct failed, and the string lives at a single site inside `review_authority_projection` (the status-row else-branch; line 1439 today). The symbol anchor is the citation, a readiness-council correction: the earlier "module-level constant block" label misapplied the line-anchor exemption to an inline expression.

The cost is concrete: an operator debugging from that message audits actor identity and independence — the two things that are fine — instead of running the one-call recovery (`wf_prepare_wave(mode='ready')` plus re-record). This repository's own operators hit exactly that misdirection twice during `1uwpf`.

## Requirements

1. **The reason names the failed conjunct.** At minimum three distinguishable causes: stale receipt binding (with current vs pinned receipt ids, the `1upba` attribution pattern), invalid actor, and missing/false independence flags. A composite failure names the first failed conjunct in evaluation order. When no current receipt exists at all (an approval pinned to a receipt in a wave whose current receipt is absent), the stale-binding reason renders the pinned id with an explicit no-current-receipt marker rather than fabricating a current id.
2. **Derivation only.** The validity predicate itself is untouched — which approvals are valid does not change, only how an invalid one is described. `1upba` and `1uwpf` verified that predicate at length; this change must not reopen it.
3. **The projection carries it.** The corrected reason reaches the `wave:review-status` table and any envelope that surfaces it, not just the internal record.

## Scope

**Problem statement:** the most common way an approval lapses (receipt supersession — the designed, routine outcome of any plan edit) is reported as the rarest (identity/independence failure).

**In scope:** the reason derivation in `review_evidence.py`; the projection rendering; tests distinguishing the three causes.

**Out of scope:** the validity predicate; receipt chaining; any ledger schema change.

## Acceptance Criteria

- [x] AC-1: An approval lapsed by receipt supersession projects a reason naming the stale binding with both receipt ids, reproduced **red-first** against the current string; the no-current-receipt edge renders the pinned id with an explicit marker, on its own fixture.
- [x] AC-2: An approval with a genuinely wrong actor, and one with `independent: false`, each project their own cause — three distinguishable strings, one test per cause.
- [x] AC-3: The set of valid approvals is byte-identical before and after across the existing `review_evidence` test corpus (derivation-only pin).
- [x] AC-4: The corrected reason renders in the `wave:review-status` projection, asserted on the projected markdown.
- [x] AC-5: The full framework suite and docs-lint pass.

## Tasks

- [x] Red-first: pin the current misattribution on a superseded-receipt fixture.
- [x] Split the reason derivation by conjunct; thread through the projection.
- [x] Run the full suite and docs-lint.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| red-test | implementer | — | Supersession fixture, current string pinned as wrong |
| derivation | implementer | red-test | Conjunct-ordered causes; predicate untouched |
| projection | implementer | derivation | AC-4 |

## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/review_evidence.py`
- `.wavefoundry/framework/scripts/tests/test_review_evidence.py`

## Affected Architecture Docs

`N/A` with rationale: diagnostic text derivation only; the review-authority flow in `docs/architecture/data-and-control-flow.md` is unchanged.

## AC Priority

| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The defect, on the routine path. |
| AC-2 | required | Without distinguishable causes the fix just moves the ambiguity. |
| AC-3 | required | The predicate is verified territory; this pin keeps the change derivation-only. |
| AC-4 | important | The wave record table is where operators actually read it. |
| AC-5 | required | Standard gate. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-10 | Planned from wave `1uwpf`'s carried-forward findings. Premises verified before authoring: the string exists at one `review_evidence.py` site, and the misattribution was observed live on all five lapsed `1uwpf` approvals with actor and independence both valid | red-team seat trace plus direct grep, 2026-08-10 |
| 2026-08-10 | Readiness council (red-team and docs-contract seats): citation corrected to the symbol anchor `review_authority_projection` (the module-level-constant-block label misapplied the line-anchor exemption), and the no-current-receipt edge added to Requirement 1 and AC-1 with a stated message shape | seat reports, both executed against `review_evidence.py`, 2026-08-10 |
| 2026-08-10 | Thought: implement by computing per-conjunct booleans once and deriving BOTH `approval_valid` and the reason from them (identical truth table, so the predicate stays untouched in the plan's semantic sense; the code lane recommended this shape to avoid a parallel derivation). Reason order: malformed context, invalid actor (recorded vs expected), missing independence, stale receipt binding (both ids; no-current-receipt marker on the None edge). Fixtures built via the canonical producer `build_policy_receipt`. Red-first: new `LapsedApprovalReasonTests` written before the code change and observed failing against current code | implementation start, 2026-08-10 |
| 2026-08-10 | Implemented. Red observed: 7 of 8 new tests failed against current code with the misattributed string on the supersession fixture (executed output pinned the exact sentence). Green: 8/8 after the conjunct split; `test_review_evidence` 152/152 and `test_dashboard_server` 189/189 file-scope. AC-3 executed with the qa lane's protocol: `derive_states.py` serialization (sorted wave/key/state JSON lines from `review_status_rows` over every real `docs/waves/*/events.jsonl`), old code from a clean `git archive HEAD` extract vs new working tree, 373 rows, ZERO state diffs (zero why diffs too: the live corpus currently holds only valid or absent approvals, so the changed strings are exercised by the unit fixtures). AC-4 asserted on `review_status_human_table` output, the projection's table renderer. Extra cause beyond the plan's three: malformed verification context gets its own message, per the qa lane's fourth-shape note | LapsedApprovalReasonTests; scratchpad/1v0lz-baseline/{old,new}.jsonl comparison, 2026-08-10 |
| 2026-08-10 | Canonical full suite on the delivered tree: 7087 tests across 62 files, OK (222s), the calibrated budget test inside the pool; independently re-executed by the delivery code and qa lanes, both 7087/62 OK. Delivery code lane proved the refactored predicate truth-table-equivalent by exhaustive 616-combination enumeration (zero mismatches) and a scratch HEAD-tree probe showed the fix, not the tests, carries the behavior (7 of 8 red there). Cosmetic disposition (code lane): an approval carrying approval_phase but no policy_receipt_id renders None as the pinned id, an accurate description of that defect state; no change | delivery lane reports, 2026-08-10 |
| 2026-08-10 | Delivery review found the wave's own review-status projection stale: the 23:29 receipt supersession re-rendered it through pre-implementation server code (the known old-code window), writing the legacy misattribution string this change removes, which the delivered staleness validator then correctly flagged (docs-lint red on wave.md). Repair: wf_reload_mcp (impl 1.15.5+phr8, impl_matches_disk true) plus projection regeneration on the next ledger write; the regenerated table carries the new stale-binding message with both receipt ids, the fix demonstrating itself on its own wave record | all three delivery lanes' executed traces; post-repair wf_validate_docs, 2026-08-10 |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-10 | Name the first failed conjunct in evaluation order rather than all failed conjuncts | One clear cause with a recovery beats a list; composite failures are rare and the first conjunct is actionable | Enumerate all failed conjuncts (rejected: noise in the common case) |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Tests elsewhere pin the current string | The red-first pass enumerates pinning tests before the edit; each moves with a stated reason, per the `1uhcb` tripwire discipline |
| The split accidentally changes validity | AC-3's corpus-wide pin |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
