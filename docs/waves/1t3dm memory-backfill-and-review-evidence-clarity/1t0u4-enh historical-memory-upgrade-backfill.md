# Historical Memory Backfill During Install and Upgrade

Change ID: `1t0u4-enh historical-memory-upgrade-backfill`
Change Status: `complete`
Owner: framework
Status: complete
Last verified: 2026-07-19
Wave: `1t3dm memory-backfill-and-review-evidence-clarity`

## Rationale

The agent-memory system now proposes and validates durable learning as waves
close, but a project upgrading into that system starts with no automatic memory
from its existing wave history. The current upgrade installs the memory tools,
renders their carriers, rebuilds the indexes, and reloads MCP; it never
enumerates prior waves or invokes memory proposal/validation. The existing
`memory_supply.draft_candidates` primitive is deliberately single-wave and
extracts only code-anchored Decision Log rows plus repaired typed
`events.jsonl` findings.

That leaves established projects with the weakest experience precisely when
memory should be most valuable. Upgrade must provide a one-way, resumable,
Git-independent historical collection path: mechanical code drafts conservative
candidates, a focused agent validates their usefulness against current targets,
and durable source dispositions make the process safe to retry. This change
populates a real corpus and records the measurements needed to decide whether
the deferred `1sufn` retrieval-fusion plan is justified; it does not
pre-authorize fusion.

## Requirements

1. **Historical inventory.** Enumerate all locally present closed/completed wave
   folders under `docs/waves/` in deterministic lifecycle order. Do not require
   Git, a landing commit, network access, or an existing semantic index. Fresh
   installs with no history are an explicit successful no-op.
2. **Modern and pre-ledger extraction.** Reuse the canonical Decision Log and
   typed `events.jsonl` sources where present. Add a conservative legacy adapter
   for pre-`events.jsonl` waves that reads only stable project artifacts
   (`wave.md`, admitted change docs, recorded decisions/repairs, and explicit
   code anchors). Never read raw transcripts and never create or rewrite a
   historical review ledger as a side effect of memory backfill.
3. **Candidate-only mechanics.** Automated extraction may create only
   `candidate` records with stable, wave-scoped `source_event` identities.
   Semantic promote/retain/reject/rewrite decisions remain agent-owned through
   `wave_memory_validate`; no heuristic auto-promotion, auto-supersession,
   merge, or deletion is introduced.
4. **Durable upgrade pause and resume.** Introduce an explicit
   `awaiting_memory_validation` boundary after framework archive
   extraction/render/prune/docs-gate and before index Phase 4. The retained
   upgrade lock records the upgrade
   identity, phase, backfill state, exact pending count, and last failure. The
   post-docs-gate response instructs the MCP caller to reload the newly
   installed implementation, run bounded `wave_memory_backfill` /
   `wave_memory_validate` calls, then invoke
   `wave_upgrade(phase="resume_after_memory")`. The CLI exposes the equivalent
   commands. `resume_after_memory` recomputes the authoritative pending set; it
   advances to the existing index phase only when that set is empty.
   `update_index`, `rebuild_index`, and cleanup fail closed while the upgrade
   lock says validation is pending.
   The canonical `memory_backfill_runs` SQLite row owns
   `inventory_pending → awaiting_validation → ready_for_index →
   publishing_index → indexed`;
   upgrade/install state files mirror only the lifecycle run id and current
   gate. Index publication remains owned by canonical index state.
5. **Install and migration parity.** Fresh install, upgrade, and migration of an
   already wave-enabled project route through the same inventory/drafting
   implementation. Fresh projects produce zero work; projects carrying
   historical waves receive the same backfill semantics regardless of entry
   path. Canonical surfaces are
   `wave_memory_backfill(mode="create", limit=...)` /
   `wave_memory_validate(...)` /
   `wave_upgrade(phase="resume_after_memory")` for MCP, and
   `wf memory-backfill` / `wf memory-validate` /
   `wf upgrade --resume-after-memory` for the CLI. Install and migration
   carriers invoke or direct these same surfaces after their framework reload
   and before their final index/complete gate.
   Setup separates dependency/server smoke from index publication: a fresh
   project with no eligible history continues directly, while an already
   wave-enabled target with candidates returns
   `awaiting_memory_validation`. After validation, rerunning the ordinary
   `wf setup` command detects the durable setup run, recomputes its authoritative
   pending census, and resumes the setup index/complete transition. No
   setup-memory-specific MCP tool or public resume flag is introduced; the
   existing observational `wave_install_audit` remains read-only. Migration
   uses the same reentrant setup gate.
6. **Durable resumability and authority split.** Store per-wave source
   fingerprints, short extraction-claim state, outcome counts, and last failure
   in the existing dedicated `memory-state.sqlite` authority. Do not add a
   JSON/Markdown fallback store. The retained upgrade lock stores only the
   lifecycle phase/upgrade identity and a reported snapshot of the SQLite
   state; SQLite plus durable memory-record `source_event` dispositions govern
   the pending set.
7. **Short transactional claims; no agent lease.** A per-wave claim covers only
   one bounded mechanical extraction/write call while the existing
   process-released project mutation lock is held. The SQLite row carries a
   random writer token and source fingerprint. A process crash releases the OS
   lock; the next holder may atomically replace an unfinished token and replay
   the same wave because stable `source_event` identities and durable
   dispositions make the write idempotent. Agent validation never holds or
   renews a claim across turns: independent agents may validate different
   candidate sources concurrently through the existing fenced
   `wave_memory_validate` path.
   The lifecycle run id plus random claim token is the ABA-proof identity;
   neither PID nor elapsed time alone authorizes reclaim.
8. **Bounded agent work.** Extraction and candidate review are paged by a named
   record budget: at most 10 waves, 20 candidate records, and 64 KiB of
   serialized response content per call (the first candidate may exceed the
   byte target only up to the existing per-record schema limit). The server
   chooses the next deterministic incomplete wave from durable state; callers
   do not own an offset cursor that can skip work. A changed source fingerprint
   invalidates only that wave's completed extraction row and requeues it.
   Responses return exact eligible/processed/remaining wave and candidate
   counts plus recovery commands. Exhaustiveness is achieved through repeated
   bounded batches, not one unbounded prompt. “Same upgrade” means the same
   retained upgrade identity proceeds from docs gate through all validation
   batches, index, and cleanup; it does not mean one unbounded process call.
9. **Deferred publication while paused.** Candidate and validation mutations
    made for an `awaiting_validation` lifecycle run update durable memory files
    and invalidation state but suppress ordinary background index refresh.
    upgrade `resume_after_memory` / an ordinary repeated `wf setup` call performs
    the single authoritative index update after the pending census reaches zero.
    Immediately before the index epoch CAS, the finalizer re-inventories sources
    under the shared mutation lock, refuses any newly pending work, and stores a
    durable `publishing_index` receipt containing the exact attempt, expected
    generation, and inventory digest. A retry after index publication but before
    the final backfill checkpoint reconciles that receipt and must not rerun the
    expensive index pass. Changed history requeues validation; unchanged
    completed runs remain reusable.
    Normal non-backfill memory tools retain their existing refresh behavior.
10. **Action-required result, not rollback or false success.** MCP returns
    status `ok` with lifecycle state `awaiting_memory_validation`, exact counts,
    and next tools. CLI exits with a documented action-required code `4` while
    retaining the upgrade/install run state and dashboard restart intent.
    This is neither an upgrade failure nor completion; index and cleanup remain
    blocked. Mechanical failures retain `last_failure` and return failure.
11. **Honest coverage.** Report waves scanned, waves with no durable source,
   candidates drafted, promoted, retained, rejected, rewritten, skipped by
   durable disposition, unsupported legacy sources, and failures. A zero result
   must distinguish “no durable source” from “source unreadable/unsupported.”
12. **Evaluation handoff.** After a real backfill, run or emit the exact
    `1sufm` memory-evaluation command against the populated corpus and record
    whether the promotion trigger for planned change `1sufn` is met. The
    upgrade/backfill never implements or enables retrieval fusion itself.

## Scope

**Problem statement:** Projects upgrading into the enhanced memory system keep
their historical waves but receive no automatic historical candidate supply or
agent-validation worklist.

**In scope:**

- A shared historical-wave inventory and backfill coordinator, exposed through
  a typed MCP/CLI surface suitable for install, upgrade, retry, and explicit
  operator runs.
- Conservative pre-ledger extraction without historical-ledger mutation.
- Candidate creation, durable wave-scoped dispositions, SQLite checkpointing,
  transactional claims, bounded paging, and structured progress/results.
- Upgrade/install/migration orchestration, in-process MCP reload ordering,
  the new awaiting-validation boundary, resume command, index-after-validation
  ordering, and operator recovery guidance.
- Setup/upgrade/migration fixtures covering empty, modern-ledger, pre-ledger,
  mixed-history, no-Git, retry, crash, and two-writer projects.
- Memory documentation, upgrade guidance, data/control-flow documentation, and
  the post-backfill `1sufm` evaluation handoff.

**Out of scope:**

- Automatic semantic promotion or contradiction resolution.
- Reading raw conversations, agent transcripts, or external services.
- Rewriting historical `wave.md` or generating `events.jsonl` for old waves.
- Cross-repository/team memory synchronization.
- Implementing `1sufn` lexical+semantic fusion, a graph relevance stream, or
  the separately deferred briefing token-budget change.
- Requiring Git or source control for inventory, identity, or correctness.

## Acceptance Criteria

- [x] AC-1: A mixed fixture containing modern-ledger, pre-ledger, zero-source,
  and malformed historical waves produces deterministic, truthfully classified
  inventory results without Git or network access. A symlinked `docs/waves`
  parent that resolves outside the repository is refused before enumeration.
  (required)
- [x] AC-2: Modern typed findings and Decision Logs produce the same candidates
  as the existing single-wave path; the legacy adapter extracts only
  code-anchored durable claims and never creates/modifies historical
  `events.jsonl`. (required)
- [x] AC-3: Install/upgrade/migration run the same coordinator; fresh install is
  a zero-work success, while an existing project enters
  `awaiting_memory_validation` after the docs gate and receives post-reload
  bounded work plus the exact `wave_upgrade(phase="resume_after_memory")` and
  `wf upgrade --resume-after-memory` commands for upgrade. Setup and migration
  resume by rerunning ordinary `wf setup`, which recognizes the durable run;
  no one-purpose setup-resume tool or public flag exists. (required)
- [x] AC-4: Candidates remain pending until a focused agent records
  promote/retain/reject/rewrite; automated paths cannot activate, supersede,
  merge, or delete records. (required)
- [x] AC-5: `memory-state.sqlite` persists wave fingerprint, short-lived
  writer-token claim, progress, counts, and failure. A forced process death
  after claim, after one candidate write, and after completion proves that the
  next OS-lock holder reclaims/replays safely without duplicate source events,
  an abandoned claim, or a long-lived agent lease. Same-wave and
  different-wave two-process controls prove serialization and independent
  progress; random writer tokens defeat ABA. (required)
- [x] AC-6: Bounded batches expose total/remaining counts and repeated calls
  exhaust the corpus; a large-history fixture proves the 10-wave/20-record/
  64-KiB bounds, deterministic next-incomplete selection, source-fingerprint
  invalidation, and no permanent page hiding. A known-bad offset-page control
  demonstrates why validated/skipped first-page records cannot hide later
  sources. (required)
- [x] AC-7: Reports distinguish no-source, unsupported/unreadable, disposition
  skip, and failure; no exception is represented as an empty successful
  backfill. (required)
- [x] AC-8: `update_index`, `rebuild_index`, and cleanup refuse while
  authoritative candidates remain pending. `resume_after_memory` recomputes
  zero pending, runs the normal index phase under the retained upgrade
  identity, and includes promoted/rewritten records. The exact
  attempt/generation receipt proves a post-publication checkpoint failure is
  recovered without a second index pass; a source change at finalization
  refuses publication and requeues validation. Reload/version, failure, retry,
  and dashboard-restart-intent fixtures prove the newly installed
  implementation owns the run. (required)
- [x] AC-11: Setup/install separates dependency+server readiness from index
  publication for existing historical projects, returns action-required exit 4
  while validation remains, and resumes through the same SQLite run row; fresh
  zero-history setup stays one-pass. A repeated ordinary `wf setup` invocation
  owns the mutating resume, while observational `wave_install_audit` never
  writes. An unchanged third invocation reuses the indexed run and does not
  reopen validation; changed history reopens the affected work. `wf setup
  --help` is observational and exits before rendering or provisioning.
  Migration follows the same gate. (required)
- [x] AC-12: Backfill candidate/validation writes do not trigger background
  refresh while the run is awaiting validation; exactly one resume-owned index
  pass publishes the accepted corpus, including retry across a failed final
  checkpoint. Ordinary memory proposal/validation outside backfill retains its
  current refresh behavior. (required)
- [x] AC-9: A real-repository dry run records corpus statistics and the
  `1sufm` evaluation result/promotion-trigger decision for `1sufn` without
  changing fusion defaults. (important)
- [x] AC-10: Full framework suite, focused install/upgrade/migration/concurrency
  tests, docs lint, and package render/install parity pass. (required)
  **Status:** the final exact-tree canonical run passed 5,972 tests across
  56 isolated files. Focused upgrade 332, backfill 32, setup 29,
  setup-index 156, index-state 36, package 97, and live MCP registration
  checks pass.

## Tasks

- [x] Implement the shared historical inventory and modern/legacy extractors.
- [x] Add the typed bulk backfill surface, bounded paging, and truthful report.
- [x] Add `memory-state.sqlite` checkpoint/claim tables and recovery logic.
- [x] Integrate fresh install, upgrade reconciliation, migration, MCP reload,
  `awaiting_memory_validation`, `resume_after_memory`, and guarded
  index/cleanup ordering without fallback storage.
- [x] Gate setup/index publication and suppress background refresh only for an
  active backfill lifecycle run.
- [x] Add focused agent-validation guidance and `1sufm` evaluation handoff.
- [x] Add no-Git, legacy, mixed-history, crash/retry, two-process, large-corpus,
  setup, upgrade, migration, and package fixtures, including killed-child,
  same/different-wave contention, ABA-token, and repeated-page known-bad
  controls.
- [x] Update memory, upgrade, data/control-flow, testing, and tool-surface docs.
- [x] Run a real historical dry run and record counts before delivery review.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| inventory-extraction | implementer | — | Modern + conservative pre-ledger sources |
| state-concurrency | implementer | inventory-extraction | SQLite claims, retry, bounded cursor |
| lifecycle-integration | implementer | state-concurrency | Install/upgrade/migration/reload/index ordering |
| agent-validation-eval | implementer + qa-reviewer | lifecycle-integration | Bounded validation and `1sufm` handoff |
| verification-docs | qa-reviewer + docs-contract-reviewer | all | Cross-platform fixtures, carriers, docs |

## Serialization Points

- `.wavefoundry/framework/scripts/memory_supply.py`,
  `.wavefoundry/framework/scripts/memory_records.py`, the module owning
  `memory-state.sqlite`, and `server_impl.py` form one source/claim/write
  protocol and must land together.
- Upgrade/install/migration ordering must be reviewed against the current
  extraction → docs gate → **durable pause** → reload → bounded candidate
  extraction/agent validation → resume → index → cleanup sequence before
  implementation edits.
- The project mutation OS lock and random SQLite claim token protect only one
  bounded extraction/write call. Do not reuse the five-minute advisory
  `memory_writers` fence or hold a claim across agent turns.
- This change populates and measures the corpus before `1sufn` is reconsidered;
  do not implement fusion concurrently.

## Affected Architecture Docs

- `docs/architecture/data-and-control-flow.md` — historical inventory,
  candidate, validation, checkpoint, and lifecycle ordering.
- `docs/architecture/testing-architecture.md` — legacy/no-Git/concurrency and
  install/upgrade/migration verification.
- `docs/specs/mcp-tool-surface.md` and `docs/agents/memory/README.md` — typed
  tool, statuses, bounded workflow, and recovery semantics.
- Upgrade/install prompt carriers and their canonical framework seeds.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Historical inventory must work for the project types Wavefoundry supports |
| AC-2 | required | Legacy compatibility must not fabricate or rewrite review authority |
| AC-3 | required | Upgrade/install completeness is the operator’s primary requirement |
| AC-4 | required | Agent judgment remains the semantic trust boundary |
| AC-5 | required | Retry and multi-agent correctness require durable claims |
| AC-6 | required | Historical repositories cannot create an unbounded prompt |
| AC-7 | required | Empty success must not mask incomplete history |
| AC-8 | required | Accepted records must enter the same upgrade’s index |
| AC-9 | important | Real corpus data decides whether deferred fusion is worth doing |
| AC-10 | required | Consumer delivery and regression gate |
| AC-11 | required | Existing-project setup must not index before agent validation |
| AC-12 | required | Paused backfill must not leak partially validated index state |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-07-19 | Planned after closing `1sxj7`; repository review confirmed upgrade installs memory machinery but performs no historical proposal/validation pass. | `upgrade_wavefoundry.py`; `memory_supply.draft_candidates`; operator direction |
| 2026-07-19 | Implemented the Git-independent SQLite coordinator, bounded MCP/CLI authoring and validation flow, setup/upgrade/migration pause/resume gates, refresh suppression, and package delivery. Exact-full-page progress, killed-process recovery at claim/write/completion boundaries, and same/different-wave process serialization are executable fixtures. | `memory_backfill.py`; `memory_cli.py`; `test_memory_backfill.py` (15 tests); `test_setup_wavefoundry.py` (23 tests); `test_upgrade_wavefoundry.py` (313 tests); `test_build_pack.py` (96 tests) |
| 2026-07-19 | Ran the observational real-repository inventory and the standing `1sufm` evaluation. The repository has 149 eligible closed waves, zero unreadable/unsupported waves, and the dry run made no records. The hermetic ranking baseline remains recall@3/MRR 1.0 with 5/5 invariants; lexical-only and semantic-only controls are worse, so `1sufn` remains deferred until the newly backfilled corpus is validated and evaluated. | `wf memory-backfill --mode dry_run`; `tests/eval/run_memory_eval.py --json` |
| 2026-07-19 | Delivery repair hardened first-run concurrency with a transactionally unique active run, preserved original candidate identity across crash/rewrite/conflict recovery, and made CLI/MCP worklists exact and run-scoped. Setup and upgrade now refuse index publication while validation is pending, including an old-loaded-runner/new-extracted-code backstop that persists the resumable run before returning action-required. | `test_memory_backfill.py` (24); `test_setup_wavefoundry.py` (29); `test_upgrade_wavefoundry.py` (321); 16-child process first-run fixture; old-shaped lock fixture |
| 2026-07-19 | Final compatibility repair made the old loaded upgrade runner invoke the newly extracted review-projection validator at its pre-docs gate. The bridge imports the installed module by unique file identity, persists completion in the upgrade lock, and never falls back to old in-memory validation logic. | `HistoricalMemoryUpgradeExtensionBootstrapTests`; `test_upgrade_wavefoundry.py` (322) |
| 2026-07-19 | Delivery re-review found the adjacent retained-lock retry could skip or reject review projection. `resume_after_gate` now accepts both projection and docs-gate failures, always reprojects before lint, preserves the actual failing phase, and clears only after both gates pass. Public CLI/MCP contracts and recovery carriers match. | Exact old-runner external-ledger recovery; focused bridge/retry 11/11; `test_upgrade_wavefoundry.py` (324) |
| 2026-07-19 | Architecture/release/QA re-review closed the remaining publication and recovery-guidance bypasses. Resume-after-memory, update, rebuild, and cleanup refuse retained projection/docs failures; projection backstop failures are rc1 review recovery rather than rc4 memory action, and primary/MCP guidance routes back to `resume_after_gate`. | Exact ready-for-index, cleanup-after-indexed, and primary-failure probes; upgrade 329/329; MCP upgrade/status 25/25; canonical 5,958/5,959 with the unrelated p95 fixture 3/3 green in isolation |
| 2026-07-20 | Reopened setup-resume ACs after operator review found the one-purpose `wave_setup_resume_after_memory` surface unnecessary. The bounded cross-lifecycle `wave_memory_backfill` capability remains; setup becomes reentrant through ordinary `wf setup`, while upgrade retains its existing phase API. | Operator direction; public-surface and state-authority trace |
| 2026-07-20 | Removed the setup-only MCP registration and public setup resume flag. Ordinary `wf setup` now reuses the non-indexed SQLite setup run at its existing memory gate, so pause → validation → plain rerun publishes exactly once without moving publication authority into the memory tool. Updated install/migration seeds, local carriers, architecture/tool docs, registration guidance, and packaged consumer assertions. | Backfill 26/26; setup 29/29; upgrade 329/329; package 97/97; canonical 5,961/5,961 across 56 isolated files; docs-lint clean |
| 2026-07-20 | Delivery repair closed the stale-census and duplicate-publication windows with a run-scoped `publishing_index` receipt integrated into the canonical index epoch CAS. Setup and upgrade now revalidate source fingerprints at finalization, publish both semantic layers synchronously under the receipt, keep detached jobs receipt-free, recover a published generation without a second pass, reuse unchanged indexed runs, and requeue changed history. An old loaded upgrade runner leaves candidate-bearing publication to the newly installed runner rather than forwarding authority through older child choreography. The same round made setup help observational, rejected escaped inventory parents, eliminated the duplicate public inventory scan, corrected setup numbering, and made the documented MCP census executable. | Backfill 32/32; setup 29/29; upgrade 332/332; index-state 36/36; setup-index canonical 156/156; public registration census |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-07-19 | Mechanically draft, then require bounded agent validation. | Python can establish source identity and idempotency but cannot judge durable usefulness. | Auto-promote historical candidates (rejected: confident garbage and history rewrite risk) |
| 2026-07-19 | Persist resumable progress in `memory-state.sqlite`, with no fallback file. | Existing projects can have large histories and concurrent agents; progress must survive crashes and retries. | In-memory run only (rejected: loses work); JSON sidecar (rejected: duplicate authority) |
| 2026-07-19 | Backfill first; evaluate `1sufn` afterward. | Fusion was deferred specifically because the corpus was sparse. | Bundle fusion immediately (rejected: removes its evidence gate) |
| 2026-07-19 | Add an explicit `awaiting_memory_validation` upgrade phase and `resume_after_memory` command. | Readiness review proved the current upgrade has no pre-index reconciliation window; the pause must be durable and testable. | Validate after indexing (rejected: misses same-upgrade indexing); hold one process open (rejected: unbounded and crash-fragile) |
| 2026-07-19 | Claims end with each bounded mechanical call; agent judgment is idempotent, not leased. | The existing five-minute memory fence is for millisecond filesystem mutations and cannot own work across agent turns. | Long-lived lease/heartbeat (rejected: unnecessary coordination complexity) |
| 2026-07-19 | Use server-selected next-incomplete work and fixed response bounds instead of client offsets. | Durable dispositions and per-wave fingerprints are the stable paging authority; offsets alias when validation changes the set. | Client cursor/offset (rejected: can skip or repeat work after mutation) |
| 2026-07-19 | Treat pending validation as action-required state (MCP `ok`, CLI exit 4), not failure or completion. | The framework may already be validly installed, but publishing the index or cleaning up would be dishonest. | Roll back extraction (rejected: unnecessary/destructive); exit 0 completed (rejected: automation can skip validation) |
| 2026-07-19 | Defer background memory index refresh during a lifecycle backfill run. | Existing proposal writes schedule refresh immediately, which violates the pre-index validation boundary. | Allow partial publication (rejected: candidate corpus becomes searchable before verdicts) |
| 2026-07-20 | Keep `wave_memory_backfill`, remove the setup-only resume tool and public setup flag, and make ordinary setup resumable. | Backfill owns durable reusable manual/setup/upgrade coordination; the setup MCP wrapper merely re-exposed one CLI branch without distinct authority. | Fold publication into the memory tool (rejected: mixes lifecycle and memory authority); keep the one-purpose tool (rejected: permanent surface burden) |
| 2026-07-20 | Couple historical-memory authorization to the canonical index epoch CAS with a durable receipt. | A pre-index census plus a later `mark_indexed` permits both stale publication and repeated expensive work after a crash. The exact attempt/generation receipt makes the split recoverable without moving index authority into memory state. | Re-run the index after every uncertain checkpoint (rejected: violates exactly-once operational behavior); treat a pre-index census as sufficient (rejected: stale window) |

## Risks

| Risk | Mitigation |
| --- | --- |
| Legacy prose produces noisy memories | Conservative code-anchor gate plus required agent validation and explicit unsupported counts |
| Upgrade becomes slow or fragile | Bounded/resumable work, non-corrupting pending status, and index after validated writes |
| Concurrent agents duplicate work | Transactional writer-owned per-wave claims and stable source-event identities |
| Upgrade remains paused after a crash | Retained upgrade identity, SQLite pending census, exact resume command, and process-released OS-lock reclaim |
| Old and new evidence formats diverge | One normalized candidate packet with fixture parity across both adapters |
| Real corpus still does not justify fusion | Record the negative evaluation and leave `1sufn` deferred |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
