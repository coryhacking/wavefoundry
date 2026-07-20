# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-07-19
review-evidence-source: events.jsonl

wave-id: `1sxj7 self-populating-memory-and-telemetry-reconciliation`
Title: Self Populating Memory And Telemetry Reconciliation

## Objective

Make the agent-memory layer self-populating so it actually gets used: waves
automatically draft records from their own review evidence, a focused agent
validates whether each draft is current, actionable, durable, and nonredundant,
and the durable source disposition prevents rejected or rewritten drafts from
regenerating. Bundle the telemetry-display and provenance repairs so the Context
Efficiency table, commit reasoning, memory supply, and exploration estimates
reconcile.

## Changes

Change ID: `1svr6-feat self-populating-agent-memory`
Change Status: `implemented`

Change ID: `1sx2f-bug context-efficiency-stage-total-reconciliation`
Change Status: `implemented`

Change ID: `1sxmz-bug commit-provenance-authority-and-completeness`
Change Status: `implemented`

Change ID: `1sxmy-bug memory-supply-and-exploration-estimate-integrity`
Change Status: `implemented`

Change ID: `1syle-enh agent-validated-memory-curation-and-backfill`
Change Status: `implemented`

Change ID: `1sxxw-bug context-efficiency-general-orphaning-and-row-pruning`
Change Status: `implemented`

Change ID: `1sxxx-ref consolidate-lock-files-under-wavefoundry-locks`
Change Status: `implemented`

Completed At: 2026-07-19

## Wave Summary

Wave `1sxj7` (Self Populating Memory And Telemetry Reconciliation) delivered 7 changes: Self-populating agent memory (superseded auto-promotion design), Context Efficiency: per-stage savings must reconcile with the displayed total, Commit provenance authority and completeness, Memory supply and exploration-estimate integrity, Agent-validated memory curation and historical backfill, Context Efficiency: general savings orphan across restarts, and raw rows never prune, and Consolidate dedicated lock files under `.wavefoundry/locks/`. Notable adjustments during implementation: Agent-validated memory curation and historical backfill: Implemented stable source dispositions, compact agent validation, close-time enforcement, and install/upgrade carriers. Removed the obsolete deterministic promotion predicate.; Agent-validated memory curation and historical backfill: Focused implementation review found and repaired three adjacent defects: validation metadata bypassed the pre-write forbidden-content scan; finding/repeated-repair source identities were not wave-scoped and the 20-record page could hide later sources forever; rewrite retry could duplicate a replacement after a partial failure.; Consolidate dedicated lock files under `.wavefoundry/locks/`: Pre-implementation review repaired the plan: added the omitted dashboard launch mutex; replaced unsafe wipe/recovery and inaccurate index-lifecycle wording; made parent creation the responsibility of every lock creator; defined a one-way upgrade that stops/migrates/restarts the dashboard with no runtime fallback; retained `dashboard-start.lock` as a persistent launch mutex while removing its cosmetic unlink lifecycle; classified `upgrade-in-progress.json` explicitly

**Changes delivered:**

- **Self-populating agent memory (superseded auto-promotion design)** (`1svr6-feat self-populating-agent-memory`) — 1 AC completed. Key decisions: Auto-promote candidate->active is allowed; auto-supersede/merge/delete is not; Deterministic structural criteria, not an LLM judge
- **Context Efficiency: per-stage savings must reconcile with the displayed total** (`1sx2f-bug context-efficiency-stage-total-reconciliation`) — 4 ACs completed. Key decisions: Count a net-negative stage as `0`; total = sum of floored per-stage savings
- **Commit provenance authority and completeness** (`1sxmz-bug commit-provenance-authority-and-completeness`) — 8 ACs completed. Key decisions: Repair in the current wave, but keep provenance as a separate change; Evidence ownership requires a typed landing association
- **Memory supply and exploration-estimate integrity** (`1sxmy-bug memory-supply-and-exploration-estimate-integrity`) — 11 ACs completed. Key decisions: Repair in current memory/telemetry wave; SQLite is the live estimate-event authority
- **Agent-validated memory curation and historical backfill** (`1syle-enh agent-validated-memory-curation-and-backfill`) — 8 ACs completed. Key decisions: Use deterministic extraction followed by a focused agent curator and durable source disposition.; Keep validation compact and reuse memory history rather than create another review ledger.
- **Context Efficiency: general savings orphan across restarts, and raw rows never prune** (`1sxxw-bug context-efficiency-general-orphaning-and-row-pruning`) — 9 ACs completed. Key decisions: `producer_id = os.getpid()`; roll in only DEAD pids at wave activation; PID reuse is NOT special-cased
- **Consolidate dedicated lock files under `.wavefoundry/locks/`** (`1sxxx-ref consolidate-lock-files-under-wavefoundry-locks`) — 11 ACs completed. Key decisions: Consolidate dedicated lock files under `.wavefoundry/locks/`; Keep `.wavefoundry/index/index-build.lock` co-located
## Journal Watchpoints

- `server_impl.py` / `memory_supply.py` / `context_efficiency.py` edited under `framework_edit_allowed`; open before editing, close immediately after.
- Superseded watchpoint (`1svr6` → `1syle`): deterministic auto-promotion was
  removed after the historical cohort proved structural eligibility is not
  semantic usefulness. Extraction is deterministic and candidate-only; the
  active agent records a compact semantic verdict. Automatic contradiction
  resolution, deletion, merge, and supersession remain prohibited.
- Watchpoint (`1sx2f`): display/aggregation-only — do NOT change the per-call `context_avoided` floor or the stored accounting fields; only the total's aggregation of the floored per-stage savings changes. Follow-up: update the existing context-efficiency tests that assert the old raw-signed total.
- Watchpoint (`1sxmz`): ownership comes only from a canonical local commit plus an explicit landing association or anchored landing subject; generic SHA prose is never authority.
- Watchpoint (`1sxmy`): exploration avoided remains an estimate in a distinct projection and never enters measured Context Efficiency totals; repeated/unmatched events earn no additional credit.
- Watchpoint (`1syle`): deterministic extraction establishes eligibility, not
  semantic usefulness. Evidence-derived records begin as candidates; a focused
  agent supplies the action delta and promote/retain/reject/rewrite judgment.
  Preserve zero-memory waves, never auto-resolve contradictions, and do not turn
  memory validation into a new full council.
- Watchpoint (`1sxxw`): keep random producer identity distinct from liveness.
  Live producers retain their own general buckets through crash-released OS lease
  locks; concurrent lifecycle actions may claim an abandoned producer only once.
  Close generation is the exact published cutoff; sealed payload rows become a
  cumulative floor while compact event-ID tombstones preserve replay. Active
  phases retain source/version dedup and paired-evaluation direct-net authority.
- Watchpoint (`1sxxx`): the shared lock module owns mechanics only—lazy parent
  creation, open/acquire/release, byte ranges, typed contention/I/O outcomes,
  held probing, and in-place metadata. Producer abandonment, adoption
  re-entrancy, dashboard launch ordering, and index interruption/F_GETLK policy
  remain in their resource wrappers. Upgrade is a one-way cutover: stop a running
  dashboard, prove old dedicated locks are free, remove old carriers, install
  canonical-only paths, and restart only after successful cleanup. Every creator
  must work when `.wavefoundry/locks/` is absent; `dashboard-start.lock` remains
  a persistent launch mutex and is never unlinked after a successful start.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| context-checkpoint-path-unpinned | do_now | no | completed | wave-council-delivery |
| delivery-evidence-not-green | do_now | no | completed | wave-council-delivery |
| exploration-estimate-compaction-loss | do_now | no | completed | wave-council-delivery |
| failed-upgrade-cleanup-drops-dashboard-restart | do_now | no | completed | wave-council-delivery |
| memory-close-one-shot-silent | do_now | no | completed | wave-council-delivery |
| memory-cost-stale-projection | do_now | no | completed | wave-council-delivery |
| memory-lifecycle-carriers-stale | do_now | no | completed | wave-council-delivery |
| memory-promotion-tier-not-selective | do_now | no | completed | wave-council-delivery |
| memory-test-runner-premature-main | do_now | no | completed | wave-council-delivery |
| memory-yield-deferral-unresolved | do_now | no | completed | wave-council-delivery |
| preimplementation-verdict-not-recorded | do_now | no | completed | wave-council-delivery |
| readiness-amendment-coverage-gap | do_now | no | completed | wave-council-delivery |
| superseded-auto-promotion-acs-still-asserted | do_now | no | completed | wave-council-delivery |

<details class="wavefoundry-review-evidence">
<summary>Machine review evidence — 160 records; 47 runs; 13 findings; current: do_now 13, maybe_later 0, dont_do_later 0, not_issue 0</summary>
</details>
<!-- wave:finding-synthesis end -->

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-07-18: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, code-reviewer; rotating-seat: code-reviewer; strongest-challenge: `1svr6` auto-promotion relaxes the deliberate 1ro44 human-gated-promotion posture — resolved: auto-promote is a `candidate -> active` status transition that rewrites no history, the rejected agentmemory behavior was auto-SUPERSEDE on similarity which stays prohibited, the relaxation is operator-directed and recorded as a decision, and the criteria is a deterministic pure function guarded by the 1sufm eval; strongest-alternative: keep promotion human-gated — rejected because the manual step is precisely the adoption killer the wave exists to remove.)
- prepare-council seat — red-team: the achievability rests on existing foundations verified this session: `wave_memory_propose`/`memory_supply.draft_candidates` (1stwk), `find_duplicates` (1stwl), the record schema + fenced write path, and the `wave_close` integration point. The dangerous failure modes are bounded: over-promotion by the tiered criteria + dedup + a required eval before/after on any drafting widening (AC-6); a close-time failure by fail-isolation (the memory step must never block the close mutation); history rewrite by the firm no-auto-supersede invariant (AC-4). Residual, non-blocking: "importance" is an approximation via structural proxies — that is exactly what the eval measures, not a hidden assumption.
- prepare-council seat — code-reviewer: `1sx2f` is a contained aggregation fix — the total's `estimated_tokens_saved` should sum the floored per-stage savings instead of the raw signed `totals.direct_net` (`context_efficiency.py` ~:1450), leaving the per-call floor and stored accounting unchanged (AC-3); the only ripple is updating the existing context-efficiency tests that assert the old raw-signed total. `1svr6` reuses the measured search/brief surface and the 1stwk/1stwl primitives with no new external surface. The deterministic criteria is testable with a fixture wave -> exact promoted set, mirroring 1sufm. No blocking concerns.
- **Prepare-phase Wave Council amendment [prepare-council] — 2026-07-18: PASS**
  (moderator: wave-council; primer-depth: focused; seats: red-team,
  docs-contract-reviewer; rotating-seat: docs-contract-reviewer;
  strongest-challenge: Python cannot perform semantic validation and the current
  close-time auto-promote would merely rename a structural heuristic — resolved
  by requiring compact agent judgment while typed tools own source identity,
  mutation, and history; strongest-alternative: retain deterministic
  auto-promotion and add more heuristics — rejected because the live twelve-wave
  sample produced structurally eligible but non-actionable prose.)
- prepare-council amendment seat — red-team: verified current source boundaries in
  `memory_supply.draft_candidates`, `is_auto_promote`, record parsing, proposal
  dedup, reconciliation, and close-time population. The load-bearing gap is real:
  `source_event` is not persisted, rejected history does not suppress proposal,
  and final synthesis rationale can omit the original failure mechanism. The
  proposed source identity plus serialized rewrite closes regeneration without
  authorizing automatic contradiction resolution or deletion.
- prepare-council amendment seat — docs-contract-reviewer: the target-project
  contract must be canonical-seed-owned and rendered through install/upgrade.
  A compact four-outcome rubric is sufficient; carrier-presence tests prove
  distribution, while behavioral tests must separately prove source suppression,
  fail-closed validation, serialized rewrite, and explicit partial-failure
  recovery without claiming multi-file crash atomicity. No separate validation ledger is
  justified because the repo-visible memory record can preserve the disposition.
- **Prepare-phase Wave Council amendment [prepare-council] — 2026-07-19: PASS**
  (moderator: wave-council; primer-depth: focused; seats: red-team,
  docs-contract-reviewer; rotating-seat: docs-contract-reviewer;
  strongest-challenge: `telemetry_event` and `source_credit` are replay,
  source-dedup, and paired-evaluation authority rather than disposable detail,
  while `wave.md` publication and SQLite mutation cannot be one transaction —
  resolved by requiring an exact covered-row cutoff, crash-matrix verification,
  and sealed-state or compact-tombstone preservation before deletion;
  strongest-alternative: globally sweep every general bucket on the first
  lifecycle action — rejected because concurrent live agents would be attributed
  to the transaction race winner. Random producer identity plus crash-released
  OS leases and transactional orphan claims preserve ownership and converge
  abandoned buckets.)
- prepare-council amendment seat — red-team: PID-only liveness cannot establish
  producer identity after PID reuse, and global sweeping is transactionally safe
  but semantically wrong for concurrent agents. The revised plan keeps unique
  producer IDs, holds a POSIX/native-Windows OS lease for the producer lifetime,
  transfers the caller's own bucket, and claims an unheld producer exactly once
  under `BEGIN IMMEDIATE`. Required fixtures cover two live producers, two
  concurrent lifecycle actions, one abandoned producer, failed claims, and
  conservation.
- prepare-council amendment seat — docs-contract-reviewer: the current spec
  explicitly makes general producer-scoped and create/prepare-triggered, while
  current code uses event IDs and phase/source/version keys as behavioral
  accounting authority. The revised ACs preserve those contracts, distinguish
  atomically written markdown from a Git commit, require install/upgrade parity,
  and forbid pruning unattributed general.
- **Prepare-phase Wave Council amendment [prepare-council] — 2026-07-19: PASS**
  (moderator: wave-council; primer-depth: focused; seats: red-team,
  docs-contract-reviewer; rotating-seat: docs-contract-reviewer; scope: newly
  admitted `1sxxx`;
  strongest-challenge: moving path authorities before quiescing old processes
  creates two independent singleton domains — resolved by making upgrade stop
  the dashboard, gate every old dedicated carrier, retain restart intent on
  failure, and install runtime code that recognizes only canonical paths;
  strongest-alternative: dual-path compatibility — rejected by operator
  direction because it preserves split authority instead of completing the
  upgrade.)
- prepare-council amendment seat — red-team: the dashboard server lock is both
  an OS lock and its process-metadata inode, while the parent start mutex spans
  check -> spawn -> readiness. The revised plan therefore forbids inode
  replacement, retains the start mutex as a persistent carrier, requires the
  post-acquire recheck, and tests concurrent starts plus held-old-lock upgrade
  refusal. The index lock remains co-located because its F_GETLK holder and
  interrupted-build semantics are resource-specific.
- prepare-council amendment seat — docs-contract-reviewer: current raw lock mechanics are
  duplicated across dashboard, adoption, producer, and index code, but their
  stale/reap/re-entrancy policies differ. A bounded engine for parent creation,
  binary open, acquire/release, byte selection, held probes, typed failures, and
  in-place metadata removes the mechanical duplication without creating a
  universal policy manager. The producer path is coordinated with still-open
  `1sxxw` so it ships at its final location.

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- pre-implementation-review: missed — no distinct coordinator-owned pre-implementation verdict, pre-mortem, and packet-completeness checkpoint was recorded before the first implementation edit. The prepare-phase councils above are genuine readiness evidence, but they are not a substitute for this separate gate. This historical deviation cannot be repaired retroactively; it is acknowledged here, and the current tree must pass fresh independent delivery review before close.
- readiness-amendment: missed — no distinct pre-edit readiness amendment names the later-admitted `1sxmz` or `1sxmy` changes. Later implementation, repair, and delivery evidence must not be presented as contemporaneous readiness approval. The historical gap is recorded explicitly and both changes remain subject to the current full independent delivery review.
- wave-council-readiness: approved 2026-07-18 — reuses existing 1stwk/1stwl/1ro44/1sufm foundations; the invariant-relaxation (auto-promote yes, auto-supersede never) is bounded and recorded; the telemetry fix is display-aggregation-only. No blocking concerns.
- operator-signoff: <approved when operator confirms closure>
- wave-council-readiness: approved 2026-07-18 — focused amendment for newly
  admitted `1syle`; red-team and docs-contract review verified the live extraction,
  record, reconciliation, close, and install/upgrade boundaries. Implementation
  may proceed with candidate-only extraction, compact agent judgment, durable
  source-event suppression, and no new review ledger.
- wave-council-readiness: approved 2026-07-19 — focused `1sxxw` amendment verified
  producer ownership, cross-process concurrency, checkpoint crash ordering,
  replay/source-dedup/paired-evaluation authority, and install/upgrade scope
  against the current implementation and specification. Implementation may
  proceed under the revised nine ACs.
- wave-council-readiness: approved 2026-07-19 — focused `1sxxx` amendment
  verified the dashboard start/lifetime handoff, metadata-inode constraint,
  adoption and producer contention behavior, index F_GETLK exception, absent
  parent creation, and one-way upgrade quiescence against the current source.
  Implementation may proceed with a shared mechanical engine, thin
  resource-policy wrappers, canonical-only runtime paths, and no fallback.
- retrospective-repair: implemented — `1sxmz` repairs the four `1sufq` provenance findings and `1sxmy` repairs the five `1stwm` memory/exploration findings. The closed-wave ledgers now carry cycle-1 `repair_start` records with code-reviewer and QA still blocking; no independent approval was self-restored.
- verification: passed — canonical `run_tests.py`: 5,832 tests across 54 files, all green; focused memory/context/provenance: 188 OK; setup/upgrade/server-context: 362 OK; docs-lint and `git diff --check` clean.
- repair-verification: passed — the canonical per-file runner now executes the full memory module (141 tests, previously 16 because of a premature `unittest.main()`); focused context-efficiency 40 OK, upgrade 310 OK, render 54 OK, setup 18 OK, and the authoritative `run_tests.py` rerun is 5,873 tests across 55 files, all green. Docs-lint and `git diff --check` are clean. Cycle-1 repairs are recorded; required independent lane reverification remains pending and is not self-cleared.

## Dependencies

- No external wave dependencies.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| close | 10 | 0 |
| implement | 92 | 2,644,251 |
| plan | 1 | 939 |
| pre-wave | 280 | 3,606,589 |
| prepare | 30 | 1,335,141 |
| review | 327 | 4,670,797 |
| **Total** | **740** | **12,257,717** |

<!-- wave:context-efficiency-state {"generation":461,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"close":{"calls":10,"content_source_credit":0,"direct_net":-12439,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":90,"response_debit":13385,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1036},"implement":{"calls":92,"content_source_credit":2850947,"direct_net":2644251,"estimated_tokens_saved":2644251,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3124,"response_debit":204997,"source_credit_count":59,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1425},"plan":{"calls":1,"content_source_credit":0,"direct_net":939,"estimated_tokens_saved":939,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":20,"response_debit":164,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1123},"pre-wave":{"calls":280,"content_source_credit":4454801,"direct_net":3606589,"estimated_tokens_saved":3606589,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":10227,"response_debit":837985,"source_credit_count":156,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0},"prepare":{"calls":30,"content_source_credit":1429574,"direct_net":1335141,"estimated_tokens_saved":1335141,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":777,"response_debit":95719,"source_credit_count":27,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2063},"review":{"calls":327,"content_source_credit":5273138,"direct_net":4670797,"estimated_tokens_saved":4670797,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":11393,"response_debit":592651,"source_credit_count":208,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1703}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":740,"content_source_credit":14008460,"direct_net":12245278,"estimated_tokens_saved":12257717,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":25631,"response_debit":1744901,"source_credit_count":450,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":7350},"wave_id":"1sxj7 self-populating-memory-and-telemetry-reconciliation"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 0 | 0 | 0 | 0 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
