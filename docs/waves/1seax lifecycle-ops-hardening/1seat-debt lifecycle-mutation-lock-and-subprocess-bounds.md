# Lifecycle Mutation Lock, Idempotent-Retry Guarantees, and Selective Subprocess Bounds

Change ID: `1seat-debt lifecycle-mutation-lock-and-subprocess-bounds`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-07-21
Wave: `1seax lifecycle-ops-hardening`

## Rationale

External code review (2026-07-12), validated against `2952df8f` — with the severity DELIBERATELY downgraded from the review's P0. The mechanics are real: `wave_add_change` moves the change doc, then writes `wave.md` (~6048/6067); removal reverses; `wave_close` writes `wave.md` then the handoff separately. A crash or concurrent call between steps leaves a half-mutation. But the blast radius is git-versioned, human-readable markdown: failures are visible in `git status`, most operations self-heal on retry (re-running admission finds the doc at target and completes the record), and there are zero field incidents across the framework's entire wave history. The review's proposed transaction layer (recovery journal, rollback, fault injection at every filesystem boundary) is disproportionate — rejected per "simplest solution first."

The right-sized version: (a) an advisory lifecycle-mutation lock so two agents/sessions can't interleave lifecycle writes on the same repo; (b) an ordering audit ensuring every multi-file mutation writes the REFERENCING record last (so a partial state is always re-runnable forward); (c) tests proving idempotent retry for each mutation. Plus the selective subset of the review's subprocess finding: timeouts + bounded capture for SHORT MCP-reachable subprocess ops (gardener, surface render) — explicitly NOT for upgrade/setup, which are long-running by design (in-line model downloads).

## Requirements

1. **Advisory lifecycle-mutation lock, scoped by CENSUS not by hand-list (plan-review revision):** one per-root lock (index-build-lock OS pattern). The covered set is derived from a complete census of MCP tools carrying mutation behavior — the review caught that a hand-written list omitted at least `wave_set_handoff` (races pause/close handoff writes) and `wave_gate_open`/`wave_gate_close` (race close's forced gate mutation). The census enumerates EVERY writer and marks each: covered-by-lifecycle-lock / protected-by-another-lock (index-build, table locks) / safely-independent-with-rationale. The census table is required AC-1 evidence in this doc. A held lock returns a structured busy response, never corrupts.
2. **Ordering audit + forward-recoverability:** each multi-file lifecycle mutation documented and (where needed) reordered so the referencing record is written last; for each, a retry after any single-step interruption completes the operation (no manual repair).
3. **Idempotent-retry tests:** per mutation, simulate the interruption between steps (move done, record not written; record written, handoff not) and assert a re-run converges. No fault-injection framework — targeted fixtures at the known seams.
4. **Close-gate signoff-token regression protection (rebaselined after pre-implementation review):** `_lane_has_signoff_in_evidence` already uses fail-closed parsing: only the final exact state line beginning with an explicit positive token authorizes, and conditional/future-tense wording and placeholders are rejected. Preserve that behavior with fixtures for the phrasings this session actually produced; no production parser rewrite is planned unless the audit finds a gap.
5. **Prepare seat-alignment validation (council amendment):** `wave_prepare`'s verdict validation compares the recorded council seats against the generated brief's required seats (fixed + rotating) instead of validating structure only; mismatch is a named diagnostic.
6. **Selective subprocess bounds:** timeouts for the gardener and surface-render subprocess calls (short ops; generous defaults, config-tunable like the 1p9bg docs-lint bound) + bounded captured output with a truncation marker. Upgrade/setup/index-build spawns explicitly EXEMPT (long-running by design; already logged to persistent files).
7. **No behavior change on the happy path:** all lifecycle tool responses keep their shapes; the lock is invisible when uncontended.

## Writer Census (AC-1 evidence, 2026-07-20)

Every mutating MCP tool, dispositioned. Lifecycle-lock = serialized by the new
per-root `lifecycle-mutation.lock` (`_LIFECYCLE_MUTATION_LOCK_TOOLS`).


| Tool | Disposition | Rationale |
| ---- | ----------- | --------- |
| `wf_create_wave` | lifecycle-lock | writes wave.md + journal + events scaffold |
| `wf_add_change` | lifecycle-lock | doc move + wave.md write |
| `wf_remove_change` | lifecycle-lock | wave.md write + doc move back |
| `wf_prepare_wave` | lifecycle-lock | relocations + wave.md status flip + projections |
| `wf_pause_wave` | lifecycle-lock | wave.md + handoff writes |
| `wf_close_wave` | lifecycle-lock | wave.md + handoff + projections + memory drafting |
| `wf_reopen_wave` | lifecycle-lock | wave.md status write |
| `wf_implement_wave` | lifecycle-lock | wave.md status write |
| `wf_set_handoff` | lifecycle-lock | handoff write (races pause/close handoff writes) |
| `wf_open_gate` / `wf_close_gate` | lifecycle-lock | guard-overrides write (races close's forced gate mutation) |
| `wf_review_evidence` | other-lock | serialized by its own `review_event_write_lock` (project-global); its wave.md projection rewrite happens under that lock |
| `memory_add` / `memory_propose` / `memory_validate` / `memory_backfill` / `memory_reconcile` | other-lock | serialized by the memory-state fence (`_memory_fence`) |
| `index_build` / `index_optimize` | other-lock | serialized by `index-build.lock` (OS lock; 1t72b exclusion discipline) |
| `wf_upgrade` | independent | single-operator orchestration with its own phase lock/status file; long-running by design |
| `wf_start_dashboard` / `wf_stop_dashboard` / `wf_restart_dashboard` | independent | dashboard lifecycle owns its pid/port state file with cmdline reconciliation |
| `wf_new_*` (10 scaffolds) | independent | each writes one fresh `docs/plans/<id>.md`; lifecycle-id minting dedupes against on-disk IDs, so two sessions cannot collide on a path |
| `wf_sync_surfaces` / `wf_garden_docs` | independent | idempotent full-surface renders; byte-identical re-renders are no-ops (1t729 net-change discipline), and interleaving with lifecycle writes touches disjoint files |
| `wf_context_efficiency_eval` | other-lock | evaluation writes go through the context-efficiency store's serialized write path |
| `wf_reload_mcp` | independent | process-level module reload; no repo file writes |

## Ordering Audit (AC-2 evidence, 2026-07-20)


| Mutation | On-disk order | Forward-recoverable? |
| -------- | ------------- | -------------------- |
| Admission (`wf_add_change`) | 1. move doc into wave folder 2. write wave.md (referencing record LAST) | Yes — retry finds the doc at target (`source == target`), skips the move, completes the record (fixture-pinned) |
| Removal (`wf_remove_change`) | 1. move doc back to plans 2. write wave.md (referencing record LAST) | Yes — retry sees `wave_exists=False`, skips the move, strips the block (fixture-pinned) |
| Close (`wf_close_wave`) | 1. write wave.md (status closed + summary + projection) 2. converge handoff (REORDERED this change: the handoff heal now runs for every create-mode close of a closed wave, not only on the fresh transition) | Yes after this change — retry on an already-closed wave converges the handoff instead of skipping it (fixture-pinned) |
| Prepare create (`wf_prepare_wave`) | 1. relocations 2. wave.md projection + status flip last | Yes — relocation retry logic mirrors admission |
| Pause (`wf_pause_wave`) | 1. wave.md status 2. handoff | Handoff is advisory session state; a re-run of pause rewrites it (accepted; same class as close pre-fix but pause re-runs cleanly because it does not guard on current status) |

## Scope

**Problem statement:** lifecycle mutations lack a concurrency guard and interruption-recovery guarantees; two short subprocess paths lack bounds.

**In scope:** `server_impl.py` lifecycle tools + a small lock helper; the two subprocess call sites; fixtures.
**Out of scope:** transaction journal/rollback machinery (rejected — see Rationale); upgrade/setup deadlines; `meta.json`/index writes (already atomic-swap + locked).

## Acceptance Criteria

- [x] AC-1: Two concurrent lifecycle mutations on the same root serialize via the lock; the loser gets a structured busy response (fixture with a held lock). Evidence includes the COMPLETE writer census table (every mutating MCP tool dispositioned: lifecycle-lock / other-lock / independent-with-rationale).
- [x] AC-5: The existing fail-closed signoff behavior remains pinned: unbracketed conditional signoff phrasing does not pass the close gate, and bracketed placeholders still read as missing (`SignoffParserHardeningTests.test_full_attack_matrix`; placeholder-close regression tests).
- [x] AC-6: `wave_prepare` flags a recorded council whose seats do not include the brief's required rotating seat (fixture), while matching councils pass unchanged.
- [x] AC-2: For admission, removal, and close: an interruption between file steps leaves a state from which re-running the SAME tool call converges to the correct end state — fixture-pinned per mutation.
- [x] AC-3: Gardener and surface-render subprocess calls carry timeouts and bounded output (truncation flagged); upgrade/setup spawns are pinned as exempt.
- [x] AC-4: Full suite bytecode-free + docs validation; uncontended-path behavior unchanged (6,081 tests across 59 files, OK, 2026-07-20); two stale source pins updated for the close reorder and the canonical vocabulary (behavior intact).

## Tasks

- [x] Lock helper + wiring across the mutating lifecycle tools.
- [x] Ordering audit table in this doc; reorder where a mutation is not forward-recoverable (close's handoff heal reordered).
- [x] Interruption/retry fixtures (admission, removal, close); concurrency fixture.
- [x] Audit and pin the existing fail-closed signoff parser with regression fixtures; do not duplicate its production implementation without a newly observed gap.
- [x] Subprocess timeouts + bounded capture at the two sites; exemption pins.
- [x] Suite + validate.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| lock+audit | implementer | — | First: the concurrency guard, forward-recoverability audit, and prepare-seat alignment |
| retry-fixtures | qa-reviewer | lock+audit | Interruption seams |
| subprocess-bounds | implementer | lock+audit + retry-fixtures | Last: two short MCP-reachable sites only, with generous config-tunable limits and slow-machine-safe recovery diagnostics |


## Serialization Points

- `lock+audit` and its retry fixtures precede subprocess bounds. Bounds remain
  deliberately selective: only gardener and surface rendering receive
  generous, configuration-tunable deadlines; upgrade/setup/index builds stay
  exempt. Timeout responses must name the operation and give a rerun/recovery
  path so a slower computer is diagnosable rather than silently treated as a
  failure.

## Affected Architecture Docs

- `docs/architecture/cross-cutting-concerns.md` (locking inventory) — one entry. N/A otherwise (no boundary change).

## AC Priority

(Proposed; confirmed at Prepare wave.)


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The multi-agent concurrency gap is the real risk. |
| AC-2 | required | Forward-recoverability is the right-sized transactionality. |
| AC-3 | important | Bounded ops; low incidence, low cost. |
| AC-4 | required | Standard gate + no-regression. |
| AC-5 | required | Preserve the close authorization boundary already fixed in the current baseline. |
| AC-6 | required | Council-seat alignment prevents false readiness approvals. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-12 | Plan-review revision (external, validated) + council amendment: hand-written lock scope replaced by a required writer CENSUS (omissions caught: `wave_set_handoff` ~6492, gate tools ~6385); two validator-hardening items adopted into scope — close-gate signoff-token parsing (verified: only `<...>` placeholders are skipped at ~5151, so this session's unbracketed phrasing pre-approved closure on three waves before repair) and prepare seat-alignment validation (the structural parser accepted councils missing the brief's rotating seat). | Plan review; parser source reads; the three repaired wave records. |
| 2026-07-20 | Pre-implementation review rebaselined AC-5: the current parser already fail-closes on exact final state lines and rejects conditional/future phrasing and placeholders. Scope is regression protection, not a duplicate parser rewrite. | Current `server_impl.py:_lane_has_signoff_in_evidence` source review. |
| 2026-07-20 | Confirmed existing regression coverage for AC-5; marked complete. | `SignoffParserHardeningTests.test_full_attack_matrix`, `test_placeholder_signoff_does_not_count_as_approval`, and `test_placeholder_signoff_blocks_wf_close_wave`. |
| 2026-07-12 | Drafted from the external code review (P0-2 + P1 subprocess), validated against `2952df8f` and DOWNGRADED: mechanics confirmed (move-then-write ~6048/6067; close's two-step write), but git-backed markdown + visible failures + retry-mostly-self-heals + zero field incidents make the proposed journal/rollback layer disproportionate. Right-sized to lock + ordering audit + retry guarantees + selective bounds. | Review report; source reads; wave-history incident base rate (none). |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-12 | Advisory lock + forward-recoverable ordering + retry tests — NOT a transaction journal with rollback. | Matches actual risk (concurrent agents; interrupted retries) at a fraction of the machinery; git is the recovery journal a docs repo already has. | **Full transaction layer (review's proposal):** disproportionate; adds its own failure modes. **Do nothing:** the concurrency gap is real as multi-agent use grows. |
| 2026-07-12 | Upgrade/setup/index spawns exempt from deadlines. | In-line model downloads and full rebuilds are legitimately long; a deadline converts slow-network success into failure. Persistent logs already cover observability. | **Blanket deadlines (review's proposal):** breaks legitimate operations. |
| 2026-07-20 | Rebaseline signoff work to regression protection. | The required fail-closed parser is already in the current baseline; preserving it with fixtures adds value, while reimplementing it adds risk without benefit. | Duplicate parser rewrite (rejected: no identified behavior gap). |
| 2026-07-20 | Lock wiring is a registration-layer wrapping pass (the 1t3s7 pattern), applied before the cost wrapper so busy responses stay cost-accounted; acquisition is a single non-blocking attempt (never wait-while-holding, per the 1t72b TOCTOU/phantom-hold lessons); an unusable lock file degrades to unguarded (advisory semantics — never block a single-session repo on lock machinery) | One chokepoint covers the whole census column; per-tool edits would drift | Per-response-function acquisition (rejected: 11 edit sites, drift-prone) |
| 2026-07-20 | The contended-path fixture uses a REAL second process | fcntl record locks never conflict within one process (the 1t72b lesson), so an in-process fixture would be vacuous | In-process second-acquire fixture (rejected: cannot observe held-ness) |
| 2026-07-20 | Close's handoff heal reordered out of the fresh-transition branch | The live audit found the one non-forward-recoverable seam: a retry after the wave.md write skipped the handoff entirely | Leave and document (rejected: AC-2 requires convergence by same-call retry) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Lock leaks on crash | OS-lock pattern (released by the kernel on exit), mirroring the proven index-build lock. |
| Reordering changes observable intermediate states some test pins | Audit first; touch only non-forward-recoverable orderings. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
