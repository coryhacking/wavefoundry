# Context Efficiency: general savings orphan across restarts, and raw rows never prune

Change ID: `1sxxw-bug context-efficiency-general-orphaning-and-row-pruning`
Change Status: `implemented`
Owner: framework
Status: implemented
Last verified: 2026-07-18
Wave: `1sxj7 self-populating-memory-and-telemetry-reconciliation`

## Rationale

Two related defects in the context-efficiency telemetry (`context_efficiency.py`),
found by inspecting the live sidecar (`.wavefoundry/logs/context-efficiency.sqlite`).

**1. `general` savings orphan across MCP server restarts.** Retrieval-tool calls
credit to `focus.wave_id or general:{producer_id}`. `producer_id` is a fresh random
hex per MCP **process** (`secrets.token_hex(16)` at start). The roll-forward that is
supposed to move `general` into a wave — `flush(transfer_general_to=<wave>)`, fired on
mutating lifecycle tools — only moves **`general:{self.producer_id}`**, i.e. the *current*
process's bucket (`context_efficiency.py` ~:1252, and the `telemetry_event` update at
~:1268 is scoped `AND producer_id=self.producer_id`). So when the server restarts
(`wave_mcp_reload`, a new conversation, a crash), the new process has a new
`producer_id` and **never** sweeps the old instance's `general`. The live store shows
**14 distinct `general:<producer_id>` buckets** (one per instance this session) holding
~7.68M tokens that are permanently stranded: never attributed to any wave, never cleaned
up. The operator's intent is that `general` is a temporary holding area that rolls into
the next wave's work whenever that is, so it never persists.

**2. Raw event rows never prune.** The only `DELETE` in the module is the general
`source_credit` transfer (~:1263). `telemetry_event` rows are never deleted — the general
transfer only *re-attributes* them (`UPDATE ... SET wave_id=...`). `read_wave_snapshot`
re-aggregates the per-wave totals from the raw `telemetry_event`/`source_credit` rows on
every call, so the tables grow unbounded (one row per retrieval call, forever, across all
waves and all orphaned producers). The sidecar is disposable/rebuildable and small today
(589 `telemetry_event` + 388 `source_credit` rows, ~455 KB), but it only grows.

## Requirements

1. **Producer-owned general with crash-released leases.** Keep the existing random,
   process-unique `producer_id`; a PID is liveness, not identity, and may be reused by an
   unrelated process. Each `ProcessTelemetry` instance holds a producer-specific OS lock
   for its lifetime under the context-efficiency sidecar directory. Use the established
   cross-platform lock shape: POSIX `flock` and native-Windows `msvcrt.locking` on a
   sentinel byte. Process exit/crash releases the lock automatically. Construction must
   remain fail-isolated: if a lease cannot be established, the producer may continue to
   write its own telemetry, but its bucket is conservatively treated as live and is never
   reclaimed by another process.
2. **Atomic own-bucket transfer plus orphan claim.** A successful create/prepare lifecycle
   action transfers the invoking producer's general bucket immediately. In the same
   `BEGIN IMMEDIATE` transaction it may claim and transfer producer buckets whose lease
   locks are provably unheld. Live peer buckets remain untouched. The database claim and
   row reassignment are one transaction, so two concurrent lifecycle actions cannot both
   claim the same orphan: the first transaction claims it, the second observes no eligible
   rows. Failed and dry-run lifecycle actions transfer nothing. Ambiguous lock state fails
   safe toward live.
3. **Checkpoint compaction only after an explicit covered-row cutoff.** The atomically
   written, validator-valid `wave.md` `## Context Efficiency` state is the durable
   aggregate floor; Git commit is not part of publication. The checkpoint carries an
   explicit cutoff identifying exactly which SQLite rows it covers. Publication order is:
   capture aggregate + cutoff, atomically write `wave.md`, CAS-mark that generation
   published, then transactionally compact only rows at or below the cutoff. Reads return
   `checkpoint floor + raw rows newer than the cutoff`. A crash before or after any step
   must yield either the old floor plus raw rows or the new floor plus post-cutoff rows,
   never loss or double counting.
4. **Preserve replay, source-dedup, and paired-evaluation authority.** Compaction seals a
   closed wave, retains one compact `WITHOUT ROWID` event-ID tombstone per removed event,
   and replaces payload rows with the cumulative checkpoint floor. Exact event replay
   therefore survives compaction. Source-dedup and paired-evaluation authority remain in
   raw SQLite for every active phase; a closed wave refuses evaluation mutation, and
   reopen creates a new phase above the floor. Unswept general is never pruned.
   The separate `exploration_credit_event` estimate ledger is also retained:
   those rows are its aggregate and idempotency authority, not disposable
   retrieval payload.
5. **Conservation and isolation invariants.** For a transfer, unaffected waves are
   byte-identical and every event/request/response debit moves exactly once. Source credit
   follows the existing target-phase uniqueness key: distinct credits move exactly once,
   while the only permitted decrease is a reproducible duplicate
   `(source_id, version_id)` collapsing when multiple producer buckets merge into the one
   `pre-wave` phase. For compaction alone, every public wave snapshot is byte-identical
   before/after. The per-call `context_avoided` floor and 1sx2f stage/total reconciliation
   remain unchanged.
6. **Pre-release legacy reconciliation.** The current self-host store contains random-ID
   general buckets from older server processes. Because this telemetry schema has not
   shipped, do not add a versioned compatibility layer. Before any schema reset, perform
   one explicit local reconciliation that attributes those unheld legacy buckets to the
   current wave (or records an operator-directed discard); the shipped implementation
   then has one canonical lease model.
7. **Idempotent and fail-isolated.** Re-running transfer, claim, publication, or compaction
   is a no-op. A telemetry failure never changes a lifecycle mutation's domain result, but
   the response reports telemetry projection/claim failure honestly and leaves durable
   state retriable.

## Scope

**Problem statement:** `general` savings are keyed per-process and only the live process's
bucket ever rolls forward, so server restarts strand them permanently; and the raw event
rows are never pruned, so the sidecar grows unbounded.

**In scope (edited under `framework_edit_allowed`):**
- `context_efficiency.py` — unique producer IDs; producer lease acquisition/probing;
  transactional own-bucket transfer + orphan claim; checkpoint cutoff/floor-aware reads;
  safe sealed-state compaction that preserves replay, source-dedup, and paired evaluation.
- `server_impl.py` — successful create/prepare transfer triggers and the publication/CAS/
  compaction ordering.
- Setup/upgrade/package paths — producer lease directories and the disposable schema must
  work in newly installed and upgraded target repositories without a compatibility layer.
- Tests — two live producers/two concurrent lifecycle actions; one abandoned producer
  claimed exactly once; ambiguous lock state left live; POSIX/native-Windows lock branches;
  failed/dry-run lifecycle calls transfer nothing; crash matrix around publication; bounded
  rows; replay/source-dedup/evaluation preservation; totals conservation and idempotence.

**Out of scope:**
- **Changing what counts as a saving** — the accounting and the per-call floor are unchanged.
- **The estimated-exploration-avoided sidecar (1svuk)** — a separate JSON store, not touched.
- **The memory work in this wave (`1svr6`)** — owned by another agent; not touched here.

## Acceptance Criteria

- [x] AC-1: Random unique producer IDs remain canonical; each producer owns a crash-released OS lease lock, with POSIX and native-Windows branches fixture-covered and ambiguous probes failing safe toward live. (required)
- [x] AC-2: A barrier test with two live producers and two concurrent lifecycle transfers proves each live bucket reaches only its owner wave, one abandoned producer is claimed by exactly one wave, and no event/source credit is lost or duplicated. (required)
- [x] AC-3: Registered successful create and prepare paths transfer own + provably orphaned general exactly once; dry-run and failed lifecycle paths transfer nothing. (required)
- [x] AC-4: Checkpoints carry an exact covered-row cutoff; crash/concurrent-writer fixtures at snapshot, markdown replacement, generation CAS, and prune boundaries prove no loss or double count. (required)
- [x] AC-5: Compaction bounds payload-bearing rows while preserving exact event replay through compact tombstones, active-phase source/version dedup and paired-evaluation attach/replace/revoke, the separate exploration-estimate authority/idempotency rows, and byte-identical public snapshots. (required)
- [x] AC-6: Transfer conserves events and debits exactly; source-credit change is either equal/opposite or exactly explained by the canonical target-phase dedup key. Compaction alone changes no public total, including the separately labeled exploration estimate; per-call flooring and 1sx2f reconciliation remain intact. (required)
- [x] AC-7: Transfer/claim/compaction are transactional, idempotent, fail-isolated, and retriable after forced failure. (required)
- [x] AC-8: Fresh install and upgrade disposable-target fixtures exercise the canonical schema/lease model; no pre-release compatibility layer ships, and the self-host legacy buckets are explicitly reconciled before reset. (required)
- [x] AC-9: Full framework suite green; docs-lint clean. (required)

## Tasks

- [x] Implement unique producer lease acquire/probe/release and transactional orphan claims.
- [x] Pin successful create/prepare triggers; prove concurrent ownership and no transfer on dry-run/failure.
- [x] Add checkpoint cutoffs and a crash-recoverable publish/CAS/compact protocol.
- [x] Preserve replay/source-dedup/paired-evaluation authority while bounding sealed data.
- [x] Reconcile the self-host legacy general buckets without shipping compatibility code.
- [x] Add fresh-install/upgrade coverage, full suite, and docs-lint.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| lease/claim | framework | — | producer ownership + exactly-once orphan claim |
| checkpoint/compact | framework | — | covered-row cutoff + sealed-state compaction |
| lifecycle | framework | lease/claim, checkpoint/compact | successful create/prepare triggers |
| verify | framework | all | concurrency + crash + bounded-growth + invariant tests |


## Serialization Points

- `context_efficiency.py` (+ the `server_impl.py` flush call sites) — edited under `framework_edit_allowed`. Independent of the memory changes in this wave.

## Affected Architecture Docs

- `docs/specs/mcp-tool-surface.md` — producer-owned general, lease/orphan-claim,
  checkpoint-cutoff, and compaction authority contract.
- `docs/architecture/data-and-control-flow.md` — producer lease and cross-file
  publish/CAS/compact ordering.
- `docs/architecture/testing-architecture.md` — concurrent producer, crash-matrix,
  install/upgrade, and bounded-growth verification.

## AC Priority

(Populated at Prepare wave.)


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | Producer identity and liveness are distinct; lock probe is cross-platform |
| AC-2 | required | Concurrent agents retain their own attribution; orphan is claimed once |
| AC-3 | required | Only successful real lifecycle mutations transfer |
| AC-4 | required | Cross-file publication is crash recoverable |
| AC-5 | required | Bounded storage cannot weaken accounting authority |
| AC-6 | required | Conservation and displayed totals remain honest |
| AC-7 | required | Transactional + idempotent + observational-only |
| AC-8 | required | Install/upgrade parity and one canonical pre-release schema |
| AC-9 | required | No regression |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-18 | Change doc authored from live-store investigation; NOT to be implemented until the concurrent memory work in this wave is confirmed complete | 14 orphaned `general:<producer_id>` buckets + ~7.68M stranded; only DELETE is general source_credit at `context_efficiency.py:1263`; `transfer_general` scoped `producer_id=self.producer_id` at ~:1268; 589 telemetry_event / 388 source_credit rows live |
| 2026-07-19 | Design refined per operator: `producer_id = os.getpid()` and roll in only DEAD pids (cross-platform liveness, Windows + POSIX). PID reuse intentionally not special-cased (self-healing: a live reused-pid process inherits and forwards the bucket; a dead pid is swept). Dropped the earlier "sweep all producers" and any age-cap/start-time machinery. | Operator direction |
| 2026-07-19 | Plan review rejected PID-only ownership and unbounded raw-row deletion. Revised to random producer identity + crash-released OS lease, transactional orphan claim, exact checkpoint cutoff, and compaction that preserves replay/source dedup/paired-evaluation authority. | Source validation: `telemetry_event.event_id` and `source_credit` PK are live idempotency/dedup authority; `_phase_direct_net` reads both during later evaluation attachment; `wave.md` replacement and SQLite CAS are separate durability steps. |
| 2026-07-19 | Implementation selected the sealed-floor model: close generation is the exact cutoff; payload rows compact only after Markdown publication + CAS; compact event-ID tombstones preserve replay; reopen creates a new raw phase above the floor. The self-host legacy reconciliation moved 280 events and eliminated all 17 general buckets. Its 10,524,850 gross source tokens became 4,454,801 unique pre-wave tokens because the canonical target-phase dedup key collapsed repeated file versions; the conservation AC was corrected rather than preserving double credit. | Executed SQLite reconciliation: general events 280→0, general source rows 228→0; target pre-wave source rows 156 / 4,454,801 tokens. Focused fixtures pin shared-source dedup, live-peer isolation, exactly-once orphan claim, failed compaction retry, replay tombstones, and floor+reopen behavior. |
| 2026-07-19 | Delivery repair retained `exploration_credit_event` across compaction. The rows are the only authority for the separately labeled estimate and its event/origin dedup; deleting them made a published estimate fall to zero. | `test_sealed_compaction_preserves_exploration_estimate_and_dedup` proves estimate and duplicate behavior are unchanged across seal/compact. |
| 2026-07-19 | Implementation and verification complete. Failed mutating lifecycle results were found to still pass `transfer_general=True`; the lifecycle chokepoint now gates transfer on the completed-milestone credit bit, with a regression proving failed prepare leaves general untouched. | `test_context_efficiency.py`: 38 OK; `test_server_context_efficiency.py`: 34 OK; setup 18 OK; upgrade 302 OK; final canonical isolated suite 5,853 tests across 54 files OK. One intervening full-suite run hit the pre-existing background-refresh cross-test timing flake; its exact fixture passed alone and the final canonical rerun was fully green. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-19 | `producer_id = os.getpid()`; roll in only DEAD pids at wave activation | A dead pid can never claim its own general, so it must be swept; a live pid (peer or reused-pid owner) will forward its own bucket. Direct liveness beats a staleness heuristic | Random-hex producer id (rejected — cannot check liveness, strands on restart); heartbeat timestamp + staleness threshold (rejected — a fuzzier proxy than a real liveness check) |
| 2026-07-19 | PID reuse is NOT special-cased | Self-healing: a reused pid means the original owner is dead; a live process on that pid inherits the bucket and forwards it on its next activation. Same-pid-and-same-repo-and-concurrent is astronomically unlikely and still yields one correctly-owned bucket | Pair pid with process start-time / boot id (rejected — adds per-platform start-time lookups for no real benefit here); age-cap backstop (rejected — unnecessary given self-healing) |
| 2026-07-19 | Cross-platform liveness, fail-safe toward "alive" | Must run on Windows and POSIX; when indeterminate, never steal a possibly-live peer's general | Assume alive always (rejected — never reclaims); assume dead always (rejected — steals live peers) |
| 2026-07-18 | Prune raw rows after durable projection; reads use the checkpoint floor + remaining raw | Keeps the disposable sidecar small without changing reported totals | Never prune (rejected — unbounded growth); VACUUM only (rejected — does not remove the logical rows) |
| 2026-07-19 | **Supersedes the three PID decisions above:** retain random producer identity and use a producer-specific crash-released OS lease lock | PID liveness cannot prove producer identity; an unrelated process may reuse the PID. Lease ownership survives concurrency and releases automatically on crash without time heuristics | Sweep every general bucket (rejected for concurrent agents — transactionally safe but semantically assigns live peers to the race winner); PID/start-time census (rejected — more platform-specific than an OS lock) |
| 2026-07-19 | **Supersedes raw-delete wording above:** compact only behind an exact published cutoff while retaining all authority needed for replay, source dedup, and paired evaluation | `wave.md` and SQLite cannot commit atomically, and the raw tables are behavioral authority rather than disposable detail | Delete immediately after projection (rejected — crash windows, replay/dedup weakening, later evaluation breakage); never compact (rejected — unbounded growth) |
| 2026-07-19 | Seal only closed waves; retain compact event-ID tombstones, keep active-phase dedup/evaluation raw, and reopen into a new phase | Exact replay needs an exact retained key, while source dedup/evaluation need no closed-phase mutation once the close seal is authoritative | Drop all authority (rejected); retain all payload rows (rejected); probabilistic replay filter (rejected — false positives) |
| 2026-07-19 | Transfer conservation is measured after canonical target-phase source dedup | Preserving the gross sum across producer buckets would double-credit the same file version when merged into `pre-wave` | Preserve duplicate gross credit (rejected — violates the existing once-per-phase accounting contract) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Compaction changes or duplicates a wave's totals | Exact cutoff + crash matrix + byte-identical before/after fixtures (AC-4/AC-6) |
| Compaction weakens replay/source dedup/evaluation | Seal first or retain compact authority; explicit post-checkpoint behavior tests (AC-5) |
| Concurrent lifecycle actions claim one orphan twice | `BEGIN IMMEDIATE` conditional claim; two-agent barrier fixture (AC-2) |
| A live peer's general is swept | Its producer lease remains held; ambiguous probes fail safe toward live (AC-1/AC-2) |
| Native-Windows lease behavior drifts | Reuse the established sentinel-byte `msvcrt.locking` shape and cover mocked branch behavior (AC-1) |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
