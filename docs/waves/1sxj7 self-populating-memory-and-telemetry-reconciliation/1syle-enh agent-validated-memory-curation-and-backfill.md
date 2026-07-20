# Agent-validated memory curation and historical backfill

Change ID: `1syle-enh agent-validated-memory-curation-and-backfill`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-18
Wave: `1sxj7 self-populating-memory-and-telemetry-reconciliation`

## Rationale

The deterministic memory extractor is intentionally conservative, but structural
eligibility is not semantic usefulness. A live dry-run over twelve recent closed
waves produced two drafts: one contained correction-history noise, and the other
reduced a concrete test-discovery failure to “Original attack closed; controls
pass.” Neither should be auto-promoted without an agent checking the underlying
evidence, current target, action delta, durability, canonical overlap, and
duplication.

The current close path can also regenerate a rejected source because memory
records do not durably identify the source event or its validation disposition.
Agent validation therefore needs a small typed authoring surface and a
repo-visible source disposition, not an unbounded new review council.

## Requirements

1. Every evidence-derived draft carries a stable `source_event` identity into
   the persisted memory record. A previously validated, rejected, or superseded
   source event is not regenerated.
2. Evidence-derived records begin as `candidate`; deterministic eligibility must
   never substitute for semantic validation.
3. Add a typed agent-validation operation with four outcomes: promote, retain as
   candidate, reject, or rewrite. It records a concise action delta, evidence
   verification, current-target verification, canonical-overlap assessment, and
   rationale. Mechanical linkage and status transitions remain tool-owned.
4. Rewrites preserve history: create the corrected record and supersede the
   generated candidate in one serialized operation under the shared
   cross-process memory lock. A surfaced partial-failure diagnostic must make
   either recovery step explicit; do not claim multi-file crash atomicity.
5. Delivery review/close surfaces unvalidated evidence-derived candidates and
   directs the active agent through the bounded validation rubric. This is a
   focused memory-quality checkpoint, not a new full council or code-delivery
   re-review.
6. Validation rejects secrets, missing/stale evidence, target mismatches,
   status-only prose, cheaply rediscoverable facts, and content already fully
   authoritative in canonical docs. A valid memory must state what changes the
   next action.
7. Install and upgrade render the validation guidance and expose the same MCP
   contract in target projects.
8. Run a selective historical backfill over the recent closed-wave cohort.
   Preserve zero-memory waves; only validated, current, nonredundant lessons are
   activated.

## Scope

**Problem statement:** automatic extraction identifies structural candidates but
does not establish that their prose is true, current, actionable, durable, or
nonredundant, and rejected sources lack a durable suppression identity.

**In scope:**

- `memory_supply.py`, memory record parsing/rendering, and server tool contracts.
- Focused lifecycle guidance and close/review diagnostics.
- Tests for source-event idempotency, all validation outcomes, atomic rewrite,
  fail-closed validation, install/upgrade rendering, and close-time visibility.
- Agent-curated backfill of a bounded recent-wave cohort.

**Out of scope:**

- Calling an LLM from framework Python.
- Semantic contradiction auto-resolution, automatic deletion, or automatic
  supersession without an explicit agent judgment.
- Requiring every wave to produce a memory.
- A new full review-evidence schema or review council lane.

## Acceptance Criteria

- [x] AC-1: Persisted evidence-derived records carry a stable source-event
  identity, and dry-run/create/close do not regenerate a source whose record was
  promoted, retained, rejected, or superseded.
- [x] AC-2: The validation tool fails closed unless all load-bearing judgments
  are supplied and the referenced candidate, evidence, and current target are
  available.
- [x] AC-3: Promote, retain, reject, and rewrite are executable and fixture-pinned;
  rewrite creates the corrected record and supersedes the source candidate in
  one serialized operation, with explicit recovery diagnostics for either
  possible partial failure.
- [x] AC-4: Evidence-derived records are never auto-promoted solely by the
  deterministic importance predicate; delivery review and close responses name
  pending validation and the recovery operation.
- [x] AC-5: Canonical seeds and rendered review/close carriers define the bounded
  rubric: evidence fidelity, current truth, action delta, durability,
  canonical-overlap, target accuracy, duplication/contradiction, and confidence.
- [x] AC-6: Install and upgrade fixtures prove new targets and upgraded targets
  receive the validation contract and tool documentation without project-specific
  content.
- [x] AC-7: A historical dry-run report covers at least twelve recent closed waves
  and records proposed/promoted/retained/rejected/rewritten/zero-memory counts.
  Created memories are individually evidence- and current-tree-verified.
- [x] AC-8: Full framework tests, docs lint, and current-wave validation pass.

## Tasks

- [x] Persist source-event and validation metadata in the memory record contract.
- [x] Implement the typed validation/rewrite operation and MCP registration.
- [x] Make proposal/close idempotency honor dispositions across all statuses.
- [x] Update lifecycle seeds, rendered surfaces, architecture, and tool spec.
- [x] Add focused, install/upgrade, concurrency, and close-path tests.
- [x] Run the bounded historical extraction and agent-curated backfill.
- [x] Reconcile wave evidence and handoff.
- [x] Complete wave-level delivery review and reconcile the current finding
  heads; all thirteen findings are independently terminal and the fresh
  wave-council delivery approval supersedes the withdrawn historical approval.

## Agent Execution Graph


| Workstream     | Owner  | Depends On   | Notes |
| -------------- | ------ | ------------ | ----- |
| Record contract and tool | implementer | — | Source identity, validation, rewrite |
| Lifecycle integration | implementer | Record contract and tool | Review/close guidance and diagnostics |
| Historical backfill | memory curator | Lifecycle integration | Validate against evidence and current tree |
| Verification | QA reviewer | All prior work | Focused plus full-suite execution |


## Serialization Points

- `memory_records.py` owns the persisted schema and must land before server/lifecycle
  integrations.
- Backfill begins only after source-event suppression and validation outcomes are
  proven, so a rejected historical candidate cannot be regenerated.
- Framework and seed edit gates must be opened and closed around their respective
  shipped surfaces.

## Affected Architecture Docs

- `docs/architecture/data-and-control-flow.md` — candidate → validation →
  disposition/rewrite path.
- `docs/architecture/testing-architecture.md` — validation and historical
  backfill verification.
- `docs/agents/memory/README.md` and `docs/specs/mcp-tool-surface.md` — operator
  and tool contracts.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority                                             | Rationale |
| ---- | ---------------------------------------------------- | --------- |
| AC-1 | required | Prevents rejected or rewritten sources from regenerating. |
| AC-2 | required | Semantic validation must fail closed. |
| AC-3 | required | All disposition paths preserve history under one serialized writer boundary and surface recoverable partial failure without claiming multi-file crash atomicity. |
| AC-4 | required | Removes unvalidated auto-promotion. |
| AC-5 | important | Makes agent judgment consistent and bounded. |
| AC-6 | required | Framework behavior must reach target projects. |
| AC-7 | important | Proves usefulness on real historical evidence. |
| AC-8 | required | Release safety. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-18 | Planned after live twelve-wave extraction and corpus census. | 2 drafts, 10 zero-memory waves, 0 existing records. |
| 2026-07-18 | Implemented stable source dispositions, compact agent validation, close-time enforcement, and install/upgrade carriers. Removed the obsolete deterministic promotion predicate. | `memory_records.py`; `memory_supply.py`; `server_impl.py`; lint parity; lifecycle seeds/templates/specs; targeted memory/docs-lint/setup/upgrade suites. |
| 2026-07-18 | Completed the twelve-wave historical cohort. Ten waves correctly yielded zero candidates; the two generated drafts were rewritten after evidence/current-target review into two active actionable records, with the generated drafts preserved as superseded history. | `1shv4` → `mem-differential-guard-for-java-initializer-chunking`; `1slep` → `mem-mid-file-unittest-main-hides-later-tests`; reruns report `skipped_dispositions: 1`. |
| 2026-07-18 | Extended the historical backfill by 44 older closed waves across index-state, lifecycle, portability, retrieval, graph, install/upgrade, and security hardening. The combined 56-wave census produced 29 candidates: 12 were rewritten into current actionable memories, 17 were rejected as stale, interim, wave-local, invalid-target, or canonical-contract duplicates, and 39 waves correctly remained zero-memory. No candidate remains pending. | Current corpus: 12 active, 17 rejected, 12 superseded, 0 candidate. All 15 source-bearing waves from the expanded cohorts rerun with `records_proposed: 0` and 29 aggregate `skipped_dispositions`. |
| 2026-07-18 | Focused implementation review found and repaired three adjacent defects: validation metadata bypassed the pre-write forbidden-content scan; finding/repeated-repair source identities were not wave-scoped and the 20-record page could hide later sources forever; rewrite retry could duplicate a replacement after a partial failure. | No-write/no-echo secret fixture; 25-source pagination/close fixture; wave-scoped source IDs; partial-failure retry fixture reuses the first replacement. |
| 2026-07-18 | Verification complete. | Canonical `run_tests.py`: 5,842 tests across 54 files, all green; `wave_validate`: clean; `git diff --check`: clean. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-18 | Use deterministic extraction followed by a focused agent curator and durable source disposition. | Python cannot establish semantic usefulness; agent judgment can, while typed tools own linkage and mutation. | Keep deterministic auto-promotion (reject: produced non-actionable prose); require a full council (reject: disproportionate); fully manual memory authoring (reject: loses automation). |
| 2026-07-18 | Keep validation compact and reuse memory history rather than create another review ledger. | The memory record itself can preserve source identity, validation, status, and supersession. | Add a separate validation JSONL authority (reject: unnecessary second store). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Agent rubber-stamps generated prose | Require evidence/current-target checks and an explicit next-action delta. |
| Validation becomes another review-cycle rabbit hole | Bound it per candidate; memory findings do not reopen delivery unless they reveal a real product defect. |
| Historical backfill floods retrieval | Preserve zero-memory waves and activate only curated, nonredundant records. |
| Rewrite or rejection regenerates at close | Persist stable source-event identity and suppress across all statuses. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
