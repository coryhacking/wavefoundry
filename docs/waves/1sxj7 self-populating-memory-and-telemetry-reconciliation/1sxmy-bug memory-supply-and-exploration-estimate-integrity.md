# Memory supply and exploration-estimate integrity

Change ID: `1sxmy-bug memory-supply-and-exploration-estimate-integrity`
Change Status: `implemented`
Owner: framework
Status: implemented
Last verified: 2026-07-18
Wave: `1sxj7 self-populating-memory-and-telemetry-reconciliation`

## Rationale

The retrospective review of closed wave `1stwm` found that its green fixtures
do not exercise the real typed-ledger or concurrent public paths:

- 0 of 54 completed real-defect heads could draft because targets are read from
  `disposition_rationale`, while docs/config/dotted prose pass the “code anchor”
  filter;
- duplicate scan and write are not one transaction, so concurrent proposal
  calls create duplicate candidates; Unicode and evidence serialization also
  corrupt identity;
- candidate writes are reported as promotions;
- repeated or unrelated briefings inflate estimated exploration avoided; and
- the estimate’s JSON authority loses concurrent writes, source cost can be
  stale, and passive/stage/cited paths promised by the change are absent.

These are directly in the current wave’s memory auto-supply and telemetry
reconciliation boundary. Repairing them here avoids shipping an automatic close
hook on top of a non-atomic/noisy supply primitive.

## Requirements

1. **Real typed-ledger derivation.** Repaired-finding targets come from a
   canonical executable-evidence field linked through `evidence_record_id`, not
   from prose in `disposition_rationale`. Draft evidence preserves finding,
   evidence, wave/change, and target identities.
2. **Conservative admitted sources.** Decision candidates come only from
   admitted change docs. Parse Decision Logs with the canonical/escaped-pipe
   table parser. Code anchors use the configured project source-file policy or
   explicit `symbol:` refs; docs/config/data may be represented only by an
   explicitly named non-code kind/contract, never mislabeled as code.
3. **Atomic idempotency.** Candidate/add duplicate scan + write is serialized
   under the existing cross-process mutation lock and re-reads the corpus under
   the lock. The cache seqlock remains cache-coherence state, not exclusion.
4. **Stable duplicate identity.** Normalize Unicode with `casefold` while
   retaining letters/numbers; an empty normalized summary cannot establish
   content equality. Canonicalize persisted/caller evidence refs and treat only
   typed source event/finding identities—not generic wave/path refs—as the
   evidence-identity signal.
5. **Honest proposal response.** Candidate creation reports
   `records_written`/`records_created`; `records_promoted` means actual
   candidate-to-active transitions only. Use canonical wave resolution and
   distinguish full ID, unique prefix, ambiguous ID, and missing wave.
6. **Deduplicated exploration events.** Persist exploration credit in the
   existing telemetry SQLite authority with a stable event key containing
   receiving wave/stage/phase, source origin, memory ID, normalized target
   context, and surfaced/cited state. Repeated identical events do not accrue.
7. **Origin attribution budget.** Within a receiving phase, all records derived
   from one source exploration share a bounded budget; their total credit cannot
   exceed the documented fraction of that origin cost. Surface-call counts stay
   separate from credited unique events.
8. **Evidenced relevance only.** Credit requires a concrete target match from a
   supported advisory path. Unmatched/default top-N surfacing earns zero.
   Describe this honestly as target-match attribution unless a real semantic
   relevance score is available.
9. **Current grounding and complete coverage.** Source cost reads the current
   healthy SQLite telemetry snapshot, with the last wave projection only as an
   explicit fallback. One centralized event API covers explicit brief and
   passive advisory surfaces with stage/phase and cited state.
10. **Durable projection and portability.** Exploration telemetry checkpoints
    to a separate wave block at lifecycle/reload/upgrade flush gates, never
    enters measured Context Efficiency totals, and installs/upgrades lazily
    without a legacy-data migration requirement.

## Scope

**Problem statement:** Automatic close-time memory supply can be noisy,
non-idempotent, and misleading, while its exploration estimate can be inflated
or lost.

**In scope:**

- `memory_supply.py`, `memory_records.py`, `server_impl.py`,
  `context_efficiency.py` (or its existing SQLite store interface).
- Public `wave_memory_propose`, `wave_memory_add`, close-time auto-population,
  explicit brief, and passive advisory consumers.
- Canonical SQLite schema created lazily for installed/upgraded projects;
  separate wave projection and documentation.
- Hermetic real-ledger, Unicode, two-process, repeat-credit, same-origin-budget,
  lost-update, passive-stage, stale-grounding, install, and upgrade fixtures.

**Out of scope:**

- Fuzzy semantic duplicate detection or contradiction resolution.
- Auto-supersede/merge/delete.
- Claiming exploration avoidance is measured causation or adding it to measured
  Context Efficiency savings.
- Broadly mining transcripts or every prose field for memory candidates.

## Acceptance Criteria

- [x] AC-1: A valid real `events.jsonl` repaired-finding chain drafts the exact
  expected failed-attempt/fragile-file candidates; synthetic rationale-only
  paths are unnecessary. (required)
- [x] AC-2: Only admitted, correctly parsed change decisions and supported code
  anchors qualify; historical corpus calibration shows docs/config noise is not
  mislabeled as code. (required)
- [x] AC-3: Two concurrent public add/propose creators yield one record, and
  retry remains idempotent. (required)
- [x] AC-4: Unicode summaries and serialized evidence refs produce correct,
  deterministic duplicate verdicts without false empty collisions or generic
  wave-ref blocking. (required)
- [x] AC-5: Response counts and wave lookup states are semantically honest;
  candidate writes are never reported as promotions. (required)
- [x] AC-6: Repeating an identical advisory event does not increase credit and
  multiple records from one origin cannot exceed the phase origin budget.
  (required)
- [x] AC-7: Unmatched/default briefings earn zero; matching explicit and passive
  surfaces record the correct wave/stage/phase and surfaced/cited state.
  (required)
- [x] AC-8: Concurrent credit updates are lossless in SQLite; current healthy
  telemetry grounds source cost and projection fallback is explicit/tested.
  (required)
- [x] AC-9: The estimate remains a separate caveated category, projects at all
  required flush gates, and never changes retrieval/advisory bytes or measured
  totals. (required)
- [x] AC-10: Fresh install and upgrade create/use the new schema lazily with no
  unavailable legacy fallback; rendered docs describe the shipped behavior.
  (required)
- [x] AC-11: Focused and full framework suites pass; docs-lint is clean.
  (required)

## Tasks

- [x] Repair typed-ledger target extraction, admitted-change parsing, and code
  anchor classification.
- [x] Serialize duplicate scan+write; repair Unicode and typed evidence identity.
- [x] Correct proposal response fields and canonical wave lookup.
- [x] Move exploration credit events/budgets to the telemetry SQLite authority.
- [x] Centralize target-matched explicit/passive credit with stage/phase context.
- [x] Read current source-cost authority and render the separate checkpoint.
- [x] Add install/upgrade and all retrospective regression fixtures.
- [x] Run focused tests, full suite, docs-lint, and live controls.

## Agent Execution Graph


| Workstream     | Owner  | Depends On   | Notes |
| -------------- | ------ | ------------ | ----- |
| supply | framework | — | real ledger, admitted sources, identity |
| telemetry | framework | — | SQLite events/budgets, grounding, projection |
| integration | framework | supply, telemetry | close/brief/passive paths |
| verify | QA | integration | concurrency, install/upgrade, invariants |


## Serialization Points

- `server_impl.py` is shared by supply and telemetry; integrate after the two
  helpers are stable.
- `context_efficiency.py` owns the existing SQLite authority and projection
  flush; schema and callers change together.
- All framework edits use `framework_edit_allowed`.

## Affected Architecture Docs

Update `docs/architecture/data-and-control-flow.md`,
`docs/architecture/testing-architecture.md`, the memory README, the exploration
estimate reference, and the MCP tool-surface contract.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority                                             | Rationale |
| ---- | ---------------------------------------------------- | --------- |
| AC-1 | required | Required finding supply path must operate on real records |
| AC-2 | required | Conservative signal bar |
| AC-3 | required | Public idempotency under supported concurrency |
| AC-4 | required | Cross-project duplicate correctness |
| AC-5 | required | Honest public response |
| AC-6 | required | Anti-inflation guarantee |
| AC-7 | required | Attribution requires evidenced relevance |
| AC-8 | required | Durable/current authority |
| AC-9 | required | Separate telemetry-only invariant |
| AC-10 | required | Other projects must install/upgrade correctly |
| AC-11 | required | No regression |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-18 | Retrospective 1stwm review admitted five root findings into 1sxj7 | `1stwm/events.jsonl`; real-ledger, concurrency, Unicode, repeated-credit probes |
| 2026-07-18 | Repaired real-ledger supply, admitted decision parsing, code-anchor policy, public mutation serialization, Unicode/evidence identity, response counters, and canonical wave lookup | `memory_supply.py`; `memory_records.py`; `server_impl.py`; public-path concurrency fixtures |
| 2026-07-18 | Replaced the JSON estimate authority with deduplicated SQLite events, per-origin phase budgets, exact-match explicit/passive credit, current source-cost reads, and a separate durable projection | `context_efficiency.py`; `exploration_avoided.py`; lifecycle/reload/upgrade projection tests |
| 2026-07-18 | Calibrated the conservative drafting policy on historical project records | 152 wave directories; 108 drafts (107 decisions, 1 failed-attempt); zero docs/config/data targets mislabeled as code |
| 2026-07-18 | Verified focused, install/upgrade, and full-suite behavior | 188 focused memory/context/provenance tests; 362 setup/upgrade/server-context tests; canonical suite 5,832 OK; docs-lint clean |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-18 | Repair in current memory/telemetry wave | Same public close/supply/telemetry boundary | Reopen closed 1stwm (rejected — preserve closed history) |
| 2026-07-18 | SQLite is the live estimate-event authority | Existing durable/concurrent telemetry substrate and operator direction | Continue JSON sidecar (rejected — lost updates and no durable event identity) |
| 2026-07-18 | Credit only concrete target matches until a real semantic score exists | Honest and deterministic | Fixed weak confidence for unmatched records (rejected — inflatable) |
| 2026-07-18 | Keep exploration events in the existing telemetry SQLite file but in a distinct table and project them as a separate wave block | Reuses durable/concurrent lifecycle plumbing without conflating estimates with measured Context Efficiency | New database or JSON sidecar (rejected — duplicate lifecycle and weaker concurrency) |
| 2026-07-18 | Validate public memory additions before creating or acquiring mutation state, then revalidate duplicate identity under the mutation lock | Invalid requests remain side-effect-free while the scan/write critical section stays atomic | Lock before validation (rejected — refused calls create mutation artifacts) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Tight code-anchor filtering reduces yield | Calibrate on the historical corpus; add a separately named artifact kind only with explicit contract |
| Event key dedups legitimate later use | Include wave/stage/phase and normalized context so a new phase is independently creditable |
| SQLite/projection changes affect upgrades | Lazy schema creation plus disposable telemetry semantics; install/upgrade fixtures |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
