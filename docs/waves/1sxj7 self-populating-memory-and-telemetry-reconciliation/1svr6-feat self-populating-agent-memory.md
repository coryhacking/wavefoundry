# Self-populating agent memory (superseded auto-promotion design)

Change ID: `1svr6-feat self-populating-agent-memory`
Change Status: `implemented`
Owner: framework
Status: implemented
Last verified: 2026-07-18
Wave: `1sxj7 self-populating-memory-and-telemetry-reconciliation`
Superseded by: `1syle-enh agent-validated-memory-curation-and-backfill`

## Rationale

The agent-memory layer now has supply (`wave_memory_propose`, 1stwk), dedup
(1stwl), honest-ranked surfacing (1ro44 + the 1svuj policy fix), a measured
value signal (1svuk), and an eval guard (1sufm). But it has a fatal adoption
gap: **every step is manual.** Someone must remember to run `wave_memory_propose`
after a close and then `wave_memory_reconcile` each candidate. Nobody will, so
the corpus stays empty and the (already-automatic) surfacing has nothing to
surface. Dogfooding confirmed the corpus is empty and manual supply yields only
a handful of records across all history.

The surfacing is already woven into everyday work (advisories fire on
`code_read`/`code_impact`/`code_callhierarchy` and `wave_prepare`/`wave_review`/
`wave_audit`, and `candidate` records surface too, labeled). So the fix is to
make **supply and curation automatic** so the loop runs with no manual step: a
closing wave deposits records from its own review evidence, a deterministic
importance criteria promotes the durable ones to `active`, and the close output
reports what happened.

> **Current disposition:** This document preserves the originally implemented
> deterministic auto-promotion design and its chronology. During the same wave,
> live evaluation showed that structural importance rules could not establish
> semantic usefulness. Change `1syle` therefore superseded auto-promotion with
> candidate-only extraction, required focused agent validation, durable source
> dispositions, and a pre-close completeness gate. The acceptance criteria below
> mark the displaced mechanism `[~]`; `1syle` is the current contract.

## Requirements

1. **Auto-supply at close (always on, no kill switch).** `wave_close` runs the
   1stwk drafting for the closing wave automatically and writes the drafts as
   `candidate` records through the existing fenced write path. Bounded and
   idempotent (the 1stwl dedup makes re-close safe); it never reads a raw
   transcript and never auto-supersedes/merges/deletes.
2. **Deterministic importance criteria for auto-promotion.** A pure, documented
   function of structural facts already deterministic in the repo promotes
   qualifying candidates to `active` at close. No embeddings, no LLM judgment,
   no clock, no randomness: the same wave ledger + Decision Logs yield the same
   promotion set every run. Inputs: `kind`, evidence-ref count, presence of a
   concrete code-anchor target, source-signal class (repaired real-defect vs
   decision), and duplicate status.
3. **Tiered promotion.** Auto-promote to `active` the strong durable signals: a
   `failed_attempt`/`fragile_file` from a completed real-defect repair, or a
   `decision` that carries a code anchor and a substantive rationale. Thinner or
   ambiguous drafts stay `candidate` (they still surface, labeled). A record
   never auto-promotes if it duplicates an existing active record.
4. **Never auto-rewrite.** Auto-promotion is a `candidate -> active` status
   transition only. The 1ro44 invariant that nothing auto-supersedes, merges, or
   deletes stays firm; duplicates and contradictions are still only surfaced
   (1stwl), never auto-resolved. This is the explicit, recorded relaxation:
   auto-*promote* yes, auto-*supersede* never.
5. **Memory summary in the close output.** `wave_close` returns a memory section
   reporting what was drafted and promoted (counts by kind, ids, and the ones
   left as `candidate` for optional review), so the operator sees the corpus
   change at close without a separate command.
6. **Widen the drafting yield (gated by the eval).** The current drafting is too
   thin (dogfood: ~13 `decision` records across all closed waves, zero
   findings). Extend 1stwk's sources so real durable signals are not missed: mine
   the change doc's Risks / Journal Watchpoints for `fragile_file` signals, and
   relax the finding path so a finding that names a file anywhere in its record
   (not only a backticked rationale) can draft. Any widening must be shown, on
   the 1sufm-style eval, to add signal without flooding the corpus.
7. **Deterministic + testable.** The promotion criteria and the close-time supply
   are covered by hermetic fixtures (a fixture wave -> the exact drafted +
   promoted set), mirroring the 1sufm discipline.

## Scope

**Problem statement:** the memory loop is fully manual, so the corpus stays
empty and the automatic surfacing has nothing to surface; it needs automatic
supply + a deterministic, principled auto-promotion so everything happens as
part of a normal `wave_close`.

**In scope (edited under `framework_edit_allowed`):**
- `wave_close` (`server_impl.py`) — invoke the 1stwk drafting for the closing
  wave, apply the deterministic importance criteria to promote durable
  candidates, and add the memory summary to the close response.
- The importance criteria — a documented pure function (new small helper or in
  `memory_supply.py`), reusing 1stwk drafting + 1stwl dedup + the record schema.
- Widen 1stwk drafting sources (Risks/Journal Watchpoints; relaxed finding path).
- Docs — memory README (the automatic lifecycle + the criteria), a decision
  record for the never-auto-promote relaxation, a lifecycle-prompt note that
  close now populates memory.
- Tests — hermetic fixture wave: exact drafted + promoted set, idempotent
  re-close, invariant (no auto-supersede), close-summary shape; an eval
  before/after for the widened drafting.

**Out of scope:**
- **Auto-supersede / auto-merge / auto-delete** — the invariant stays firm.
- **LLM-judged importance** — the criteria is deterministic by design.
- **Retrieval/ranking changes** — 1svuj already landed; RRF fusion (1sufn)
  stays deferred.
- **Reconcile UX beyond the close summary** — promotion is automatic; a richer
  candidate-review surface can follow.

## Acceptance Criteria

- [~] AC-1: `wave_close` automatically drafts memory `candidate` records from the closing wave's typed evidence (1stwk), always on, bounded, idempotent, with no kill switch. (required) — SUPERSEDED by `1syle`: close now performs a pre-close completeness check and requires every eligible source to have a candidate plus focused agent disposition; `_auto_populate_memory_for_wave` remains only a defensive post-close fallback, not the authoritative workflow.
- [~] AC-2: A deterministic, documented importance criteria auto-promotes qualifying candidates to `active`. (required) — SUPERSEDED by `1syle` AC-2/AC-4: structural facts draft candidates but never supply a semantic verdict; `wave_memory_validate` owns promotion.
- [~] AC-3: Structural tiering auto-promotes repaired findings and code-anchored decisions. (required) — SUPERSEDED by `1syle`: every evidence-derived record stays `candidate` until a focused agent verifies the evidence and current target.
- [~] AC-4: Auto-promotion is a status transition only and never auto-supersedes, merges, or deletes. (required) — SUPERSEDED because auto-promotion was removed; the still-current no-automatic-rewrite invariant is enforced by `1syle`'s typed promote/retain/reject/rewrite paths.
- [~] AC-5: The `wave_close` response includes drafted/promoted/candidate counts. (required) — SUPERSEDED by the pre-close candidate-validation diagnostics and explicit `wave_memory_propose` / `wave_memory_validate` responses; a post-close fallback may still report candidate writes but never promotion.
- [~] AC-6: Widen drafting through Risks/Journal Watchpoints and relaxed finding paths. (important) — SUPERSEDED by `1syle`'s conservative real-ledger/Decision-Log extraction plus operator-directed, agent-validated historical backfill; no unvalidated yield widening ships.
- [~] AC-7: Hermetic fixtures cover the deterministic drafted+promoted set. (required) — SUPERSEDED by `1syle`'s candidate-only extraction, four validation dispositions, pre-close completeness, retry, and install/upgrade fixtures.
- [x] AC-8: Full framework suite green; docs-lint clean. (required) — full suite 5802 OK (one unrelated test_indexer timing flake, passes in isolation); `wave_validate` docs-lint ok.

## Tasks

- [~] Deterministic importance criteria — implemented initially, then removed when `1syle` superseded structural auto-promotion with agent validation.
- [~] Hook auto-supply + auto-promote into `wave_close` — superseded by `1syle`'s pre-close completeness gate; the remaining helper is defensive candidate-only fallback.
- [~] Add the drafted/promoted memory summary to `wave_close` — superseded by explicit candidate/validation diagnostics and tool responses.
- [~] Widen 1stwk drafting — superseded by conservative extraction plus the agent-validated backfill.
- [x] Docs: preserve the historical decision and mark it superseded by `1syle`; the memory README and lifecycle carriers describe the current candidate-validation flow.
- [~] Deterministic-promotion fixtures — replaced by `1syle` candidate, disposition, retry, lifecycle, install, and upgrade fixtures.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| criteria | framework | — | deterministic importance function + widened drafting |
| close-hook | framework | criteria | wave_close auto-supply + auto-promote + summary |
| verify | framework | close-hook | fixture tests, eval before/after, docs |


## Serialization Points

- `server_impl.py` (`wave_close`, memory helpers) and `memory_supply.py` — edited under `framework_edit_allowed`.

## Affected Architecture Docs

`docs/architecture/testing-architecture.md` (fixture tier note) and the memory README; a decision record under `docs/architecture/decisions/` for the never-auto-promote relaxation (auto-promote yes, auto-supersede never). No layering change.

## AC Priority

(Populated at Prepare wave.)


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | Automatic supply is the adoption fix |
| AC-2 | required | Deterministic, auditable promotion |
| AC-3 | required | Principled importance bar, no flood |
| AC-4 | required | The never-auto-rewrite invariant must hold |
| AC-5 | required | Visibility at close |
| AC-6 | important | Yield is currently too thin |
| AC-7 | required | Hermetic, reproducible verification |
| AC-8 | required | No regression |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-18 | Change doc authored on operator direction: no kill switch, deterministic auto-evaluation criteria for auto-population, memory summary at close | Operator direction; dogfood (13 thin decisions, corpus empty); 1stwk/1stwl/1ro44/1sufm foundations |
| 2026-07-18 | Implemented `memory_supply.is_auto_promote` (deterministic pure fn) + `_auto_populate_memory_for_wave` hooked into `wave_close_response` (fenced, forbidden-scanned, fail-isolated, idempotent) + memory summary in the close envelope. Docs: README "Automatic at close" + `1svr6-adr`. AC-6 (widen yield) deferred to a measured follow-up. Suite 5802 OK; docs-lint ok. | `memory_supply.py`; `server_impl.py wave_close_response`; `MemoryAutoPopulateTests` (5); `1svr6-adr` |
| 2026-07-19 | Reconciled this original design with the later same-wave `1syle` contract: deterministic auto-promotion and post-close authority are superseded; candidate-only extraction, focused agent validation, durable source disposition, and pre-close completeness are canonical. Historical implementation claims remain in the chronology but no longer masquerade as current AC evidence. | `1syle` AC-1–AC-8; `memory_supply.py` (“never auto-promotes”); `_memory_validation_diagnostics`; `wave_memory_validate` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-18 | Auto-promote candidate->active is allowed; auto-supersede/merge/delete is not | Promotion is a status transition that rewrites no history; the rejected agentmemory behavior was auto-supersede on similarity. Operator-directed relaxation of human-gated promotion | Keep promotion human-gated (rejected — the manual step is the adoption killer); copy agentmemory auto-supersede (rejected — rewrites history) |
| 2026-07-18 | Deterministic structural criteria, not an LLM judge | Auditable, reproducible, testable like the 1sufm eval | LLM "is this important?" judge (rejected — non-deterministic, unauditable) |
| 2026-07-18 | Always on, no kill switch | Operator direction; a toggle that defaults off would never be turned on | Config toggle (rejected per operator) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Over-promotion floods the corpus and dilutes surfacing | Tiered criteria + 1stwl dedup + 1sufm eval before/after on any widening |
| Auto-promote perceived as violating the invariant | It is a status transition only; the no-supersede/merge/delete invariant stays firm and is covered by a test + a decision record |
| Close becomes slower or can fail on the memory step | The memory step is bounded and fail-isolated: a supply failure never blocks the close mutation |
| Widened drafting adds noise | Gate the widening on the eval; ship only what adds signal |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
