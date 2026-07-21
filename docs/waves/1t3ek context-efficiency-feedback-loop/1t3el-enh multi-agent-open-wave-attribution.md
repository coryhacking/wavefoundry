# Multi-Agent Open-Wave Attribution

Change ID: `1t3el-enh multi-agent-open-wave-attribution`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-07-20
Wave: TBD

## Rationale

Operator-reported gap (2026-07-20): real workflows run multiple agents against one wave —
one agent plans, another reviews the plan, the coordinator implements and runs the
lifecycle gates, a fresh agent runs the delivery review, the coordinator closes. Context
Efficiency telemetry is per-process: each agent session runs its own MCP server process
with its own producer bucket, and instrumented retrieval attributes to a wave only when
THAT process has lifecycle focus. Focus is set only by lifecycle calls made in that
process.

Consequences today: only the gate-running coordinator's work attributes correctly.
Every other agent's retrieval lands in its producer's `general` bucket and is adopted
only at a create/prepare boundary in some LATER process — attributed to the WRONG wave,
stamped `plan`. Work from producers whose leases stay live may never transfer at all.
This under-counts implement/review-stage savings (observed: wave `1t3gt` showed
`implement: 1` while multiple sessions worked) and inflates the next wave's `plan`
bucket with the previous wave's exploration.

The single-OPEN invariant makes this fixable: at most one wave is `active`/`implementing`
at any moment, so any producer can cheaply resolve "the wave this work belongs to"
without coordination.

## Requirements

1. **Retrieval-time open-wave attribution:** when an instrumented call executes in a
   process with no lifecycle focus, and exactly one wave is currently OPEN
   (`active`/`implementing`), attribute the event to that wave instead of the producer's
   `general` bucket. Stage derives from observable wave state at event time: `plan` when
   the wave is `planned`-but-being-prepared is NOT applicable (no OPEN wave means general,
   unchanged); an OPEN wave attributes as `implement` until the canonical events.jsonl
   contains a delivery-run record (`initial_delivery` or later), and `review` after.
   Sealed/closed waves are never attribution targets (existing redirect stands).
2. **Boundary adoption extended:** `wf_review_wave` (implementation phase) and
   `wf_close_wave` also adopt provably-unheld peer producers' general buckets into the
   wave, using the stage rule from Requirement 1 rather than hardcoded `plan` — so
   crashed or exited helper agents' work is captured at the boundaries that follow it,
   not by the next wave's prepare.
3. **No double-counting:** existing once-only source-credit keys, event replay
   protection, and producer fences apply unchanged to the new attribution paths;
   cross-producer merges reuse the existing collapse logic.
4. **Honest labeling:** attributed-by-open-wave events are distinguishable in the store
   (attribution provenance column or equivalent) and the wave.md visibility note keeps
   saying the totals may include exploration not exclusive to the wave. No causal
   overclaim.
5. **No attribution when ambiguity exists:** zero OPEN waves, or any state where the
   OPEN wave cannot be resolved cheaply and unambiguously, falls back to today's
   `general` bucket behavior.
6. Direct-focus behavior (the gate-running process) is unchanged.

## Scope

**Problem statement:** Multi-agent waves under-count implement/review savings and
misattribute helper-agent work to the next wave's plan bucket, because attribution
requires per-process lifecycle focus and adoption only happens at create/prepare.

**In scope:**

- Open-wave resolution helper (cheap, cached-with-invalidation, cwd-independent)
- Retrieval-time attribution in `context_efficiency` when focus is absent
- Stage derivation from wave status + delivery-run presence
- Extended boundary adoption at implementation-review and close
- Attribution-provenance marking in the store schema
- Hermetic tests: multi-producer scenarios (live peer, exited peer, no OPEN wave,
  ambiguous state, sealed wave)

**Out of scope:**

- Cross-repository attribution
- Any change to the savings equation, credits, or debits
- Rewriting historical misattributed data (accepted as-is per the 1t3ld precedent)

## Acceptance Criteria

- [x] AC-1: A producer with no focus records retrieval while a wave is OPEN; the event
      attributes to that wave with the stage from the derivation rule, verified by
      hermetic multi-process-simulating test.
- [x] AC-2: With no OPEN wave (or an unresolvable state), behavior is byte-identical to
      today's general bucket, verified by test.
- [x] AC-3: Implementation-review and close boundaries adopt an exited peer's general
      bucket into the wave with derived stage; a live peer's bucket is untouched,
      verified by test.
- [x] AC-4: No double-counting across the new paths: replayed events and repeated
      source/version pairs collapse exactly as on existing paths, verified by test.
- [x] AC-5: Attributed-by-open-wave events carry distinguishable provenance in the
      store, verified by test.
- [x] AC-6: Full framework test suite passes
      (`python3 .wavefoundry/framework/scripts/run_tests.py`).

## Tasks

- [x] Design and implement the open-wave resolver (status read with cheap caching and
      correct invalidation; never blocks the retrieval path on failure)
- [x] Implement retrieval-time attribution with the stage-derivation rule
- [x] Extend boundary adoption at implementation-review and close with derived stage
- [x] Add attribution provenance to the store schema (with the schema-version
      consideration the store contract requires)
- [x] Hermetic multi-producer tests for AC-1 through AC-5
- [x] Update `docs/references/context-efficiency.md` attribution semantics
- [x] Run full framework test suite

## Requirements

1. [Numbered behavioral requirement — specific enough for an implementer to act on unambiguously]
2. …

## Scope

**Problem statement:** [What is broken, missing, or improving?]

**In scope:**

- …

**Out of scope:**

- …

## Acceptance Criteria

- [x] AC-1: [Testable outcome — verifiable by QA, automated test, or manual check]
- [x] AC-2: …

## Tasks

- [ ] [Concrete implementation step]
- [ ] …

## Agent Execution Graph


| Workstream        | Owner       | Depends On | Notes |
| ----------------- | ----------- | ---------- | ----- |
| open-wave-attrib  | Engineering | —          | `context_efficiency.py` core + `server_impl.py` boundaries; store schema touch |


## Serialization Points

- Late-admitted into wave `1t3ek` AFTER `1t22z`/`1t230` landed (operator direction
  2026-07-20), so the sequencing concern is satisfied by ordering: this change builds on
  their landed code rather than racing it.

## Affected Architecture Docs

`docs/references/context-efficiency.md` (attribution semantics section, tracked in
Tasks). The store-schema provenance addition may warrant a line in
`docs/architecture/data-and-control-flow.md`; decide at implementation.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | The operator-reported gap: helper-agent work must attribute to the wave it serves |
| AC-2 | required  | Ambiguity must never guess; today's general-bucket behavior is the safe fallback |
| AC-3 | required  | Exited helpers are the common multi-agent case; live-peer isolation is the existing safety contract |
| AC-4 | required  | Double-counting would corrupt the accounting signal the whole subsystem exists to provide |
| AC-5 | important | Provenance is honesty bookkeeping; the totals are correct without it but unauditable |
| AC-6 | required  | Suite-green is the delivery gate for all framework script changes |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
|      |        |          |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-20 | Provenance is an additive `attribution` column on telemetry_event ('focus'/'open_wave'/'adopted'), following the `source_credits_dropped` ALTER-migration precedent; no schema-version bump needed. | Additive columns with defaults are the store's established migration pattern; nothing reads the column on the accounting path. | Separate provenance table (rejected: joins on the hot path for audit-only data) |
| 2026-07-20 | Stage derivation reads only wave-owned files (wave.md Status line, sibling events.jsonl delivery-run markers) with a 10s TTL cache keyed per root and an explicit test reset seam; any failure resolves to None and keeps general-bucket behavior. | The resolver sits on the retrieval hot path of every focus-less call; it must be cheap, cwd-independent, and unable to fail the tool call. | Uncached per-call scan (rejected: N file reads per retrieval); focus-handshake tools for helper agents (rejected at council: requires the behavior that does not happen) |
| 2026-07-20 | Boundary adoption gating extended to `bool(credit) or reached_review` in `_lifecycle_context_result`: create/prepare keep milestone gating unchanged; a review that RAN and a mutating close also adopt. | An exited helper's bucket should land at the boundary that follows its work; pre-close reviews rarely carry milestone credit, so credit-only gating would defer adoption to the next wave's prepare — the exact misattribution this change removes. | Adopt on every lifecycle call (rejected: dry-runs must not mutate) |
| 2026-07-20 | REPAIRED REAL DEFECT (caught by live verification, missed by all hermetic tests): `_open_write_store_once`'s `schema_ready` fast path skips the migration block on an already-current store, so the new `attribution` ALTER never ran there — the first attributed INSERT failed and the failure semantics correctly POISONED the live store. Fresh test stores get the column via CREATE, which is why every hermetic test passed. Fix: additive columns must appear in the `schema_ready` column check (now documented inline); regression test strips the column from a current store and proves reopen-migrate-record works. | The fast path is the only open path an existing production store takes; a live-store probe (simulating a helper-agent session) was the only verification that exercised it. Reinforces the independent-delivery-verification lesson: execute against real state, not only fixtures. | None; the check-list omission was simply a bug |
| 2026-07-20 | Recorded manual repair of the live store poison: deleted `.wavefoundry/logs/context-efficiency.gap` and the `meta` `accounting_gap` row after the fix landed. The only events lost to the gap were the two defective verification probes themselves; no real accounting was lost. Post-repair probe: `persistence: durable`, attributed row `(1t3ek, implement, open_wave)` on the migrated live store. | The poison marker is deliberately durable with no self-heal; a code-defect-induced poison on this wave's own accounting is honestly repaired by hand with the repair recorded here. | Leave the store poisoned (rejected: would permanently zero this wave's headline over two lost probe events) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Unrelated exploration during an OPEN wave gets attributed to it | Accepted tradeoff, honestly labeled (Requirement 4); the alternative (today) misattributes to the NEXT wave instead, which is strictly worse |
| Open-wave resolution on the hot retrieval path adds latency or a failure mode | Cheap cached read with invalidation; any resolution failure falls back to general (Requirement 5); never blocks or fails the tool call |
| Store schema change interacts with the sealed-floor compaction contract | Schema-version consideration explicit in Tasks; provenance column additive-only |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
