# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-07-20
review-evidence-source: events.jsonl

wave-id: `1t3dm memory-backfill-and-review-evidence-clarity`
Title: Memory Backfill And Review Evidence Clarity

## Objective

Give established projects a one-way, resumable path to derive and
agent-validate useful memories from pre-upgrade wave history. At the same time,
make `wave.md` show compact, causal current review state while `events.jsonl`
retains the complete machine-readable history, and make that record readable
in the dashboard without exposed control markers or source-line-driven spacing.

## Changes

Change ID: `1t0u4-enh historical-memory-upgrade-backfill`
Change Status: `complete`

Change ID: `1t3dl-enh review-evidence-current-state-projection`
Change Status: `complete`

Change ID: `1t3dn-enh dashboard-wave-document-rendering`
Change Status: `complete`

Completed At: 2026-07-20

## Wave Summary

Wave `1t3dm` (Memory Backfill And Review Evidence Clarity) delivered 3 changes: Historical Memory Backfill During Install and Upgrade, Review Evidence Current-State Projection, and Dashboard Wave-Document Rendering. Notable adjustments during implementation: Historical Memory Backfill During Install and Upgrade: Delivery repair hardened first-run concurrency with a transactionally unique active run, preserved original candidate identity across crash/rewrite/conflict recovery, and made CLI/MCP worklists exact and run-scoped. Setup and upgrade now refuse index publication while validation is pending, including an old-loaded-runner/new-extracted-code backstop that persists the resumable run before returning action-required.; Historical Memory Backfill During Install and Upgrade: Removed the setup-only MCP registration and public setup resume flag. Ordinary `wf setup` now reuses the non-indexed SQLite setup run at its existing memory gate, so pause → validation → plain rerun publishes exactly once without moving publication authority into the memory tool. Updated install/migration seeds, local carriers, architecture/tool docs, registration guidance, and packaged consumer assertions.; Historical Memory Backfill During Install and Upgrade: Delivery repair closed the stale-census and duplicate-publication windows with a run-scoped `publishing_index` receipt integrated into the canonical index epoch CAS. Setup and upgrade now revalidate source fingerprints at finalization, publish both semantic layers synchronously under the receipt, keep detached jobs receipt-free, recover a published generation without a second pass, reuse unchanged indexed runs, and requeue changed history. An old loaded upgrade runner leaves candidate-bearing publication to the newly installed runner rather than forwarding authority through older child choreography. The same round made setup help observational, rejected escaped inventory parents, eliminated the duplicate public inventory scan, corrected setup numbering, and made the documented MCP census executable.

**Changes delivered:**

- **Historical Memory Backfill During Install and Upgrade** (`1t0u4-enh historical-memory-upgrade-backfill`) — 12 ACs completed. Key decisions: Mechanically draft, then require bounded agent validation.; Persist resumable progress in `memory-state.sqlite`, with no fallback file.
- **Review Evidence Current-State Projection** (`1t3dl-enh review-evidence-current-state-projection`) — 10 ACs completed. Key decisions: Keep complete history only in `events.jsonl`; render current approval state in `wave.md`.; A withheld state carries reason and next action derived from current heads.
- **Dashboard Wave-Document Rendering** (`1t3dn-enh dashboard-wave-document-rendering`) — 8 ACs completed. Key decisions: Repair the shared block renderer, not `wave.md` preprocessing.; Treat comments as presentation metadata outside fences.
## Journal Watchpoints

- Historical extraction is candidate-only. Python establishes source identity,
  idempotency, and resumability; an agent owns promote/retain/reject/rewrite.
- Backfill must work without Git, network access, or a pre-existing semantic
  index. State lives only in the existing `memory-state.sqlite`; there is no
  JSON or Markdown fallback.
- Upgrade must reload the installed MCP implementation before agent validation,
  then index accepted memories in the same upgrade. Pending validation is
  reported honestly without corrupting a valid framework upgrade.
- Setup is reentrant: after historical validation, rerunning ordinary `wf setup`
  resumes the durable setup run. Do not add a setup-memory-specific MCP tool or
  public resume flag; upgrade retains its existing phase-oriented resume.
- `events.jsonl` remains the complete review-history authority. The new
  `wave.md` block is a bounded current-state projection, not another ledger.
- A withheld lane must say which current findings block it, which reviewer
  lanes remain unresolved, and what action clears it. Reasonless `withheld` or
  repeated per-finding withdrawal lines do not meet the contract.
- Projection refresh owns only its marker and provably generated legacy state
  lines; readiness narratives, verification notes, historical deviations, and
  non-adopted closed history must remain untouched.
- Backfill populates and measures the corpus before the deferred `1sufn`
  retrieval-fusion plan is reconsidered. This wave does not implement fusion.
- Dashboard repair belongs in the shared Markdown renderer. Do not preprocess
  only `wave.md`, alter raw `/api/doc` content, or remove ownership markers from
  source files.
- Physical source wrapping must not create visual paragraphs. Blank lines and
  structural blocks govern spacing; normal prose uses the available dialog
  width, while intrinsically wide tables/code scroll locally.
- Marker-looking text inside fenced code remains visible. Comment suppression
  applies only to presentation outside code and cannot affect lifecycle,
  indexing, or MCP authority.

## Participants

- Product owner: operator — acknowledged the historical-backfill and dashboard
  operator goals in the requests that created and expanded this wave.
- Coordinator / implementation owner: framework implementer.
- Final integration owner: wave coordinator — reconciles shared
  upgrade/install/package carriers after all three workstreams land.
- Required review lanes: architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, release-reviewer, code-reviewer, docs-contract-reviewer, performance-reviewer
- Rotating readiness seat: `release-reviewer`, because all three changes carry
  install/upgrade/package consumer-delivery obligations.

## Prepare Review Evidence

- Product-owner acknowledgment: recorded from the operator's explicit requests
  to add historical upgrade backfill, causal review-state presentation, and the
  two dashboard rendering repairs to this wave.
- Readiness council: completed after the initial full-depth review blocked the first
  draft on upgrade phase/claim ambiguity, signoff-row identity, participant
  assignment, and missing concurrency/visual controls. The plans were amended
  before any implementation edit.
- red-team: passed — challenged the durable pause, split authority, stale-claim
  reclaim, and simpler post-upgrade alternative before the fixed seats ran.
- architecture-reviewer: passed — the repaired SQLite authority, mirrored
  lifecycle state, resume gates, legacy-adoption matrix, and locked projection
  protocol are coherent.
- security-reviewer: passed — short OS-lock-scoped random-token claims avoid
  unsafe long-lived leases and prose-only evidence is never fabricated.
- qa-reviewer: passed — exact commands, action-required semantics, killed-child
  and concurrency controls, malformed-marker cases, fixed viewport geometry,
  and package execution are falsifiable.
- reality-checker: passed — current setup/upgrade/index ordering was reconciled
  to the new explicit pause rather than relying on a nonexistent window.
- release-reviewer: passed — install, upgrade, migration, package asset parity,
  retained restart intent, and recovery commands are assigned.
- code-reviewer: passed — source inspection confirmed the three workstreams
  have coherent chokepoints and the corrected persistence-before-reload order.
- docs-contract-reviewer: passed — canonical signoff-key identity,
  observational dry-run purity, operator-facing reasons/next actions, and
  carrier obligations are explicit.
- performance-reviewer: passed — historical work is bounded at 10 waves,
  20 candidates, and 64 KiB per response; projection size depends on current
  heads and paused backfill defers repeated background refresh.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-07-19: PASS** (moderator: wave-council; primer-depth: full; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, release-reviewer; rotating-seat: release-reviewer; strongest-challenge: durable validation pause could strand a valid installation or split authority between upgrade and memory state; strongest-alternative: optional post-upgrade maintenance was simpler but rejected because it publishes before validation and loses same-upgrade convergence)
- pre-implementation-review: passed — coordinator re-read the three repaired,
  readied change contracts and the implementation context after
  `wave_implement`; the first edit is constrained to the recorded
  ledger-first projection, durable backfill state machine, and shared dashboard
  renderer serialization points.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| agents-tool-list-omits-live-tools | do_now | no | completed | docs-contract-reviewer, release-reviewer, wave-council-delivery |
| memory-backfill-parent-symlink-escapes-repo | do_now | no | completed | code-reviewer, qa-reviewer, reality-checker, wave-council-delivery |
| memory-index-publication-checkpoint-not-exactly-once | do_now | no | completed | qa-reviewer, performance-reviewer, code-reviewer, architecture-reviewer, release-reviewer, wave-council-delivery |
| memory-index-publication-stale-census-window | do_now | no | completed | code-reviewer, architecture-reviewer, qa-reviewer, reality-checker, release-reviewer, wave-council-delivery |
| resume-after-gate-skips-projection-repair | do_now | no | completed | code-reviewer, architecture-reviewer, qa-reviewer, release-reviewer, wave-council-delivery |
| setup-seed-step-numbering-contradiction | do_now | no | completed | docs-contract-reviewer, release-reviewer, wave-council-delivery |
| unchanged-setup-reopens-completed-backfill | do_now | no | completed | reality-checker, qa-reviewer, docs-contract-reviewer, release-reviewer, wave-council-delivery |
| wf-setup-help-mutates-project | do_now | no | completed | reality-checker, code-reviewer, docs-contract-reviewer, release-reviewer, wave-council-delivery |

<details class="wavefoundry-review-evidence">
<summary>Machine review evidence — 150 records; 39 runs; 8 findings; current: do_now 8, maybe_later 0, dont_do_later 0, not_issue 0</summary>
</details>
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | approved | current executed approval follows every affected repair | none |
| architecture-reviewer | approved | current executed approval follows every affected repair | none |
| security-reviewer | approved | current executed approval follows every affected repair | none |
| qa-reviewer | approved | current executed approval follows every affected repair | none |
| reality-checker | approved | current executed approval follows every affected repair | none |
| release-reviewer | approved | current executed approval follows every affected repair | none |
| code-reviewer | approved | current executed approval follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval follows every affected repair | none |
| performance-reviewer | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- Closed wave `1sxj7 self-populating-memory-and-telemetry-reconciliation`
  provides the candidate-only memory proposal/validation workflow, durable
  dispositions, upgrade reconciliation window, and historical self-host
  evidence this wave generalizes to consumer projects.
- Closed wave `1slep external-wave-event-ledger` provides `events.jsonl` as the
  append-only review authority and the existing one-way ledger-adoption model.
- Planned change `1sufn measured-lexical-semantic-memory-fusion` remains
  deferred. Historical backfill must emit the existing `1sufm` evaluation
  result before that plan is reconsidered.
- The dashboard change has no external wave dependency; it repairs the shared
  `renderMarkdownish`/`DocDialog` path already delivered to consumer projects.

## Execution Graph

| Order | Change | Depends on | Completion boundary |
| ---: | --- | --- | --- |
| 1 | `1t3dl` review-evidence current-state projection | `1slep` ledger authority | One derivation serves lifecycle gates, dashboard/resources, lint, and Markdown projection |
| 1 | `1t3dn` dashboard wave-document rendering | Existing shared document viewer | Marker-free, normally wrapped wave/change DOM and responsive layout |
| 2 | `1t0u4` historical memory backfill | `1sxj7` memory workflow | Install/upgrade/migration expose bounded post-reload validation and index accepted records |
| 3 | Integrated verification | all three changes | Consumer upgrade, self-host upgrade, no-Git, concurrency, narrative preservation, dashboard parity, and full suite pass |

The three changes can be implemented in parallel until they touch shared
dashboard consumers, lifecycle, or upgrade orchestration. Their
consumer-upgrade fixtures, dashboard asset delivery, and canonical prompt
carrier updates must be reconciled together.

## Serialization Points

- `review_evidence.py`, the lifecycle review/close consumers, dashboard/resource
  readers, docs lint, and the Markdown projector must switch to one typed
  current-state derivation in the same landing step.
- Historical memory inventory, `memory-state.sqlite` claims, the typed MCP/CLI
  surface, and install/upgrade/migration sequencing form one backfill protocol
  and must not land as independently authoritative partial paths.
- Upgrade ordering is load-bearing: install/extract and docs gate → persist the
  durable `awaiting_memory_validation` pause → return/reload the newly installed
  MCP implementation → bounded extraction and agent validation →
  `resume_after_memory` → normal index phase → cleanup/restart.
- Setup/install/migration use the same SQLite lifecycle run states. Existing
  historical projects pause after dependency/server readiness and before index;
  fresh zero-history projects continue directly.
- Backfill validation mutations suppress background refresh only while a
  lifecycle run is awaiting validation. Resume owns the authoritative index
  publication.
- The upgrade compactor may remove only generated approval-state lines whose
  typed ledger equivalence is proven. Ambiguous or non-adopted closed records
  are reported, not rewritten.
- `wfds.js` is the sole Markdown-rendering repair chokepoint. `DocDialog` must
  not gain a wave-only cleanup path, and parser/CSS behavior must be verified
  together before dashboard asset packaging and upgrade parity are accepted.
- Backfill claims are short mechanical transactions protected by the
  process-released project mutation lock plus a random SQLite writer token.
  No claim or advisory fence spans an agent turn.
- Review event append, adoption/compaction, prepare, review, and close re-read
  all authorities under `review_event_write_lock` and preserve the existing
  ledger-first partial-commit recovery states.

## Implementation Verification

- Canonical suite: the final exact-tree run passed 5,972/5,972 tests across
  56 isolated files. An earlier run hit one pre-existing load-sensitive
  benchmark under six-worker contention; the exact fixture passed 3/3 in
  isolation and the failure did not recur. The three composite full-suite ACs
  are now `[x]`.
- Focused suites: review evidence 89, dashboard 182, docs lint 828, upgrade
  332, setup 29, memory backfill 32, setup-index 156, index-state 36,
  package 97, and MCP upgrade/status 25, all green. The opt-in checked-in
  Chrome geometry regression also passed 1/1. The canonical run selected the
  CPU embedding provider explicitly to avoid the pre-existing
  environment-specific CoreML crash class.
- Historical inventory dry run: 149 eligible closed waves, zero unreadable or
  unsupported waves, no repository mutation. The baseline memory evaluation
  remains recall@3/MRR 1.0 with 5/5 policy invariants; `1sufn` stays deferred
  until the historical candidates are actually validated.
- Dashboard geometry: at 1440×900, page/dialog/body scroll widths were
  1440/858/790 and exactly matched client widths; at 390×844 they were
  390/369/301 and also matched. Both probes found zero overflowing paragraphs
  or long inline spans, ownership comments were absent, and tables scrolled
  locally. The checked-in test now reproduces those assertions through real
  Chrome when `WAVEFOUNDRY_BROWSER_TESTS=1`; retained captures remain under
  this wave's `evidence/` directory.
- Upgrade compatibility: a process still holding the old upgrader imports the
  newly extracted validator at `pre_docs_gate`, repairs review-status
  projection before lint, and records the completed bridge in the retained
  upgrade lock. Both projection and docs-gate failures resume by regenerating
  projection before lint; the focused 329-test upgrade suite pins old-runner,
  stale-marker, actual-failure-phase, publication/cleanup refusal, typed exit
  classification, and retry-idempotency paths.
- Package and upgrade execution: tests extract the produced/installed framework
  into a disposable target and execute its review-evidence, memory-backfill,
  CLI, and dashboard-renderer assets. This verifies runnable consumer delivery,
  not only source-string presence.
- MCP delivery: fresh registration includes the reusable
  `wave_memory_backfill` operation but no setup-memory-specific resume tool.
  Reload sends `notifications/tools/list_changed` for callable
  additions/removals as well as description changes. Because this wave changes
  thin `server.py`, the current host still requires one process restart to load
  that notifier.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 49 | 2,004,778 |
| implement | 1 | 770 |
| review | 346 | 8,404,536 |
| **Total** | **396** | **10,410,084** |

<!-- wave:context-efficiency-state {"generation":369,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":1,"content_source_credit":0,"direct_net":770,"estimated_tokens_saved":770,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":9,"response_debit":646,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1425},"plan":{"calls":49,"content_source_credit":2100013,"direct_net":2004249,"estimated_tokens_saved":2004778,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1578,"response_debit":97372,"source_credit_count":66,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3186},"review":{"calls":346,"content_source_credit":9248075,"direct_net":8401286,"estimated_tokens_saved":8404536,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":11900,"response_debit":837628,"source_credit_count":267,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2739}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":396,"content_source_credit":11348088,"direct_net":10406305,"estimated_tokens_saved":10410084,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":13487,"response_debit":935646,"source_credit_count":333,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":7350},"wave_id":"1t3dm memory-backfill-and-review-evidence-clarity"} -->
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
