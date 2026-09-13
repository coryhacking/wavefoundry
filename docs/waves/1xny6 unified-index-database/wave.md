# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-13
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1xny6 unified-index-database`
Title: Unified Index Database

## Objective

Consolidate semantic and graph indexing in `.wavefoundry/index/index.sqlite`, with one atomic publication boundary and the existing fast graph cache. Deliver a safe standard upgrade from legacy or schema-7 stores, including the filename change, resumable recovery and verified cleanup.

Prepare routine semantic updates in bounded memory before publication, spilling only oversized work to the owned index filesystem. Preserve rollback and the short shared writer transaction.

For the initial transition, preserve compatible semantic data and rebuild the graph from current sources into the staged new database. After fresh-process verification, delete the obsolete owned graph directory; no old graph-format conversion is planned.

## Changes

Change ID: `1xny5-ref unify-graph-index-storage`
Change Status: `complete`

## Participants

- Coordinator: Engineering
- Write-owning roles: coordinator, implementer, QA test author, technical writer; exact file ownership confirmed at Prepare
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer, security-reviewer, performance-reviewer, docs-contract-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer, performance-reviewer, security-reviewer

Completed At: 2026-09-11

## Wave Summary

Delivered one project-local `index.sqlite` for semantic and graph persistence, coherent generation-bound readers, source-rebuilt graph migration with verified cleanup, shared maintenance and durable map fingerprints. The canonical renderer now includes `.wavefoundry/locks/`.

Prepared operations stay in memory under a 64 MiB retained-operation budget, spilling lazily when needed. Small/no-op/graph-only builds create no preparation artifacts; this is not a process-RSS cap. Complete incremental deltas measured 12.02 s median against 12.05 s baseline. Large replay memory and spill costs remain explicit in runtime-qualification.json.

All 13 ACs completed with no intentional deferrals. All ten review findings were repaired and independently reverified; seven specialist delivery lanes and the full council passed. The canonical suite passed 8,871 tests, with 12 intentional skips. Live MCP recovery verified schema 8, exact vector/FTS coverage and semantic retrieval without fallback.

Native Windows/Linux/macOS Intel package execution remains G4 release follow-through. No commit, package build or release was performed. The retrospective timing lesson is promoted in active memory `1xoyl-mem measure-acquired-writer-intervals-and-freeze-per-run-timing-` and project-context-memory.md. Final reports remain in delivery-review.json; historical failed measurements remain distinguishable from corrected qualification.

## Watchpoints

- Memory-first preparation (Requirement 11 / AC-13) passed scope readiness, implementation and independent delivery review. No commit is authorized by the request to finish the wave.
- Preserve standard upgrades with no bridge release; never edit a pending receipt or delete the only index to force progress.
- Existing evaluation timings are operator-accepted. Keep single-transaction integration distinct from query cache replacement, retrieval ordering and unproven memory/disk savings.
- Stable graph identities and change-sized publication must replace the prototype's full-table rewrite. Old graph reset/repair must never destroy the shared semantic store.
- Watchpoint: the initial full source graph rebuild is automatic and distinct from legacy semantic `--rebuild-storage`. Keep the old graph until verification; remove the folder only when its contents are verified obsolete and owned, preserving unknown contents and external symlink/reparse targets.
- Readiness contracts allocate schema 8 against the current schema-7 tree, include dashboard/map consumers and freeze query sampling/screens. Re-Prepare if another change takes the schema allocation first.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| ARCH-CURRENT-1 | do_now | no | completed | architecture-reviewer, qa-reviewer, code-reviewer, wave-council-delivery |
| ARCH-CURRENT-2 | do_now | no | completed | architecture-reviewer, qa-reviewer, code-reviewer, wave-council-delivery |
| CODE-CURRENT-1 | do_now | no | completed | code-reviewer, qa-reviewer, architecture-reviewer, wave-council-delivery |
| DOCS-CURRENT-1 | do_now | no | completed | docs-contract-reviewer, wave-council-delivery |
| DOCS-FINAL-1 | do_now | no | completed | docs-contract-reviewer, architecture-reviewer, wave-council-delivery |
| PERF-CURRENT-1 | do_now | no | completed | performance-reviewer, qa-reviewer, wave-council-delivery |
| PERF-CURRENT-2 | do_now | no | completed | performance-reviewer, qa-reviewer, wave-council-delivery |
| QA-CURRENT-1 | do_now | no | completed | qa-reviewer, release-reviewer, wave-council-delivery |
| QA-CURRENT-2 | do_now | no | completed | qa-reviewer, release-reviewer, wave-council-delivery |
| REL-CURRENT-1 | do_now | no | completed | release-reviewer, qa-reviewer, wave-council-delivery |

*Machine review state — 10 findings; current: do_now 10, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | approved | current executed approval follows every affected repair | none |
| code-reviewer | approved | current executed approval follows every affected repair | none |
| qa-reviewer | approved | current executed approval follows every affected repair | none |
| architecture-reviewer | approved | current executed approval follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval follows every affected repair | none |
| release-reviewer | approved | current executed approval follows every affected repair | none |
| performance-reviewer | approved | current executed approval follows every affected repair | none |
| security-reviewer | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- Uses completed evaluation change `1xny2-task evaluate-sqlite-graph-consolidation` in wave `1xny3 sqlite-graph-consolidation-evaluation` and proposed ADR 1xny4.
- Evaluation wave 1xny3 closed by operator instruction on 2026-09-10. The OPEN slot is available; this wave remains readied until implementation is requested.

## Current assumptions

Local-only indexing; same APSW/sqlite-vec runtime, FP32 embeddings and public graph behavior. Memory and unrelated host-local stores remain separate. Existing resident graph serving remains the baseline.

## Outputs produced or expected

One consolidated change document, production implementation with focused tests, a compact qualification/review record, updated ADR and canonical operator guidance. Avoid additional planning Markdown files.

## Review checkpoints

Final delivery council — 2026-09-11: **PASS**. Full-depth red-team primer; fixed architecture-reviewer, security-reviewer, qa-reviewer and reality-checker seats; rotating fifth seat rotating-best-alternative (council-alternative-final). All fixed seats explicitly weighed the alternative. Anonymous-first merit synthesis was unanimous, maximum current severity none; identities were restored only afterward. No challenge round was required. Closing red-team verified all ten original real/do_now findings retain their classifications with completed independent repairs and no outstanding lane.

Seat evidence: architecture-reviewer passed six snapshot/map/report controls and killed the stale map-receipt mutation; security-reviewer passed four native cleanup/identity controls and caught the permissive ownership mutation; qa-reviewer passed 61 controls and caught the FTS positional-integrity mutation; reality-checker executed the public coordinator no-spool check and detected forced eager spill. All reported no findings. The rotating best-alternative reviewer confirmed main-database preparation blocks a competing writer and verified actual 64 MiB overflow/cleanup. No stronger alternative was established: dual row/byte replay caps lack a demonstrated bottleneck, direct-main preparation extends writer occupancy, and unlimited RAM loses the bound. No backlog was created.

Falsification check: correlated shared evidence and bounded local fixtures do not prove universal correctness or native package support. Distinct negative controls and preserved G4 limits support this source-delivery verdict. Retain the acquired-writer timing lesson and the distinction between retained preparation bytes and process RSS. All 58 source hashes remain frozen; 8,871 tests passed. Current-plan readiness was independently rebound after stale handoff prose was refreshed. Reports and executable evidence: delivery-review.json#final_council; final timings: runtime-qualification.json#memory_preparation_qualification.

- Memory-preparation readiness expansion — 2026-09-11: full primer; architecture, security, QA and reality fixed seats plus rotating docs-contract alternative all approve the current bounded-memory plan. Fixed seats weighed a framed temporary-file stream and retained existing SQLite overflow because its proposed savings are unmeasured while it adds a framing/rollback protocol. Fresh anonymous-first synthesis is unanimous, maximum severity medium from resolved plan conditions, no open readiness blocker. Evidence: `readiness-review-r2.json#memory_preparation`. Approval is readiness only; AC-13 implementation/resource evidence remains pending.

2026-09-11 full delivery review: **changes required**. Fresh code, QA, architecture, release, performance and docs-contract lanes found actionable items; security approved its bounded path/cleanup scope, with native platform execution explicitly pending. Full-depth primer and fixed council seats ran, including rotating docs-contract review. Reports, mutation tables and embedded scratch reproducers are retained in [delivery-review.json](delivery-review.json); typed findings are authoritative in events.jsonl. Council roster: architecture-reviewer, security-reviewer, qa-reviewer and reality-checker; rotating fifth seat docs-contract-reviewer; standalone code, release and performance lanes also ran. Anonymous-first synthesis then restored lane authority: majority agreement, maximum severity high, nine deduplicated findings. No material blocker disagreement required a challenge round. All fixed seats weighed output-digest recovery and agreed it cannot alone satisfy AC-7 no-stale-overwrite; prefer a short serialized output/receipt publication, with digest checks as optional recovery. Source packet stayed unchanged. AC-5/6/7/9/10/11 are reopened; no repairs, closure, commit, package or live migration were performed by this review.

Operator followup: prefer in-memory prepared index updates. The present spool is production staging, created eagerly even for builds with no semantic updates. Memory bounds and overflow behavior must be specified before implementing the preference; it is not an approval of an unreviewed implementation.

Additional consumer review, 2026-09-10: source-verified the five initial follow-ups and the graph-quality evaluator producer. The change doc now names unchanged-build orphan reconciliation, complete map inputs and recoverable derived-output receipts, single physical maintenance/accounting, WAL-aware dashboard refresh and post-cutover writer/read-path tests. The evaluator is explicitly in review targets with scratch schema-8 initialization, production-path parity and failed-publication rollback coverage. These clarify existing scope; no extra feature, runtime verification or approval is claimed. Re-Prepare remains required.

2026-09-10 operator scope amendment: codebase-map fingerprint state belongs in index.sqlite, bound to its rendered graph/community generation. Retire the standalone marker and ensure map generation cannot recreate the old graph folder. Requirements 2, Scope and AC-7 now cover this; prior readiness below is historical pending re-Prepare. Evaluation 1xny3 is closed, so the OPEN slot is free.

Planning discovery used current source outlines and targeted reads for SQLite policy, graph extraction/query/community ownership and migration preparation/cutover, plus the filename census. Divergent pre-plan selected stable graph tables with the resident cache; compact snapshots and separate generation manifests remain documented rejected approaches for this plan. Optional Review plan resolved the documented branches; readiness passed below. Delivery review remains outstanding.

Operator refinement: rebuild graph/extraction/community state from current sources rather than translating old graph formats; preserve compatible semantic data and retire the owned old graph folder after verification. AC-6/7 include corrupt/missing old graph, failed rebuild, complete folder cleanup and unknown-content preservation cases.

Qualification will compare isolated baseline and new-store full graph rebuilds on identical frozen sources, including graph evidence and representative public results, not only row counts. Retain actual timings and block adoption on unexplained differences. Ordinary destination upgrades do not require a second shipped graph engine or a readable old graph.

- **Prepare-phase Wave Council [prepare-council] — 2026-09-10: PASS WITH NOTES** (moderator: wave-council; primer-depth: full; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, docs-contract-reviewer, code-reviewer, release-reviewer, performance-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the current detect predicate skips the schema probe whenever a receipt parses, so a schema-8 upgrade would be a no-op for receipt-less and completed-receipt schema-7 stores and an old-code host could recreate index-state.sqlite beside the new store; strongest-alternative: land schema 8 under the existing filename and drop the rename, removing the both-names ambiguity class, the resolver module and the literal and documentation repoints, at the cost of the operator's recorded naming objection)

Second readiness run after the two operator scope clarifications rotated the review-policy receipt. The primer ran at full depth in isolation; the four fixed seats, the rotating seat and three own-first specialist lanes each ran in a fresh, parallel context after receiving the primer; one targeted challenge round ran on the receipt-layout disagreement. Seat evidence (full reports in [readiness-review-r2.json](readiness-review-r2.json); events.jsonl is the approval authority):

- red-team: primer findings RT-PRIMER-1 through RT-PRIMER-5 (dispatch predicate, old-reader fence, cleanup allowlists, dashboard mechanism, anchor imprecision); bounded check was a withheld-site census that recovered two behavioral filename literals the design table omitted. In the challenge round it resolved the receipt layout: a same-file version-2 receipt holds as the old-code fence, the separate-file alternative is refuted because it leaves no fence, and the first-hop crash concern is refuted because the old runner's only pre-extract read occurs while the file is still version 1.
- architecture-reviewer: ARCH-1 (publication participant census incomplete; three post-commit committers and both epoch fences unnamed), ARCH-2 (single-binding rule collides with three stdlib accessors), ARCH-3 (per-layer generation representation unstated); recommended block pending ARCH-1 and ARCH-2 plan edits; all three repaired. Control: a withheld committer returned zero hits while a known-present term returned three.
- security-reviewer: SEC-1 executed scratch-tree probe showing the reused deletion primitive removes unknown files and link nodes (blocking candidate, repaired with a pre-deletion inventory rule and enumerated owned names), SEC-2 kind-owned allowlists and work-dir (repaired), SEC-3 fence direction decided by receipt layout (repaired). Every controlling actor is the operator or a same-user process; no attacker-reachable boundary. Controls: traversal key and symlinked-ancestor root both refused as unowned.
- qa-reviewer: QA-1 through QA-7 (parity harness and fixture, schema-6/7 fixture capture order, three inversion targets AC-8 retires, evaluator public path and skip hazard, git check-ignore oracle, map-receipt seams, WAL-aware dashboard test); all repaired in AC-5, AC-6, AC-7, AC-8, AC-11, AC-12 and the capture task. Control: the ignore oracle returned not-ignored for a sibling path.
- reality-checker: REAL-1 rollback copy never read back (repaired: forward recovery stated and tested), REAL-2 three schema pins plus a by-name reader (repaired), REAL-3 owned-name enumeration and an omitted folder-creating site (repaired), REAL-4 prototype timings bypass the production path (accepted risk, disclosed), REAL-5 dispatch and fence false by mechanism (severe, repaired). Control: the creation-site sweep recovered a site the plan row omitted.
- docs-contract-reviewer (rotating): DOCS-1 four live-path filename surfaces outside review targets (repaired), DOCS-2 anchor module (repaired), DOCS-3 seed-250 illustration (repaired), DOCS-4 state vocabulary (repaired); refuted the primer's dashboard premise; recorded the no-rename alternative as the strongest path not taken.
- code-reviewer: CODE-1 unnamed commit sites (repaired), CODE-2 two reset mechanisms (repaired), CODE-3 staged rebuild target and held lock (blocking candidate, repaired with three named entry preconditions), CODE-4 v1-literal cleanup allowlists (repaired), CODE-5 single-arm store migration would drop FTS (repaired), CODE-6 gitignore test shape (repaired). Control: a withheld post-commit site was recovered by the sweep.
- release-reviewer: REL-1 three schema constants (repaired), REL-2 protocol value for the new kind with no bridge (repaired), REL-3 builder-version probes point at a retired file (repaired; pinning tests added to targets), REL-4 dormant changelog claims check (repaired in AC-10). Controls: refuted two-constant census; withheld stdlib probe recovered.
- performance-reviewer (advisory): PERF-1 numeric regression predicate and dispatch precondition, PERF-2 lock-held segment and busy-timeout screen, PERF-3 whole-membership community and merge-state churn, PERF-4 checkpoint pressure and reclamation accounting; all landed as plan text in Gates, AC-4, AC-8 and AC-9. Control: refuted the claim that current graph persistence is already change-sized at three write sites.

Aggregate: seat_agreement majority (seven approve-with-notes, one block); max_severity severe. The block-versus-notes split needed no second round because every blocking candidate's repair was a change-doc edit landed before readiness; the architecture lane's blocking authority was honored by repair, not merit-weighted down. Repair rounds: council repairs (round 2), eleven reverifier-found defects RV-A-1 through RV-A-6 and RV-B-1 through RV-B-5 repaired (round 3), and two one-clause fixes RV-A-7 and RV-B-6 (round 4). Two fresh independent reverifiers hold on the final text: storage and upgrade cluster repairs_hold_with_notes, tests and docs cluster repairs_hold. Readiness attests plan completeness and code-grounded feasibility of the named seams, not delivered behavior; G1 through G4 remain delivery gates.

### Falsification Check

Approve readiness with notes. The strongest argument against is that the repair added substantial mechanisms (participant classification, single-binding rule, inventory rule, per-layer generation state, staged-rebuild entry preconditions) reviewed only as text in three rounds, and each round introduced defects a reverifier caught, so a further undetected defect is plausible. It does not change the conclusion: every added mechanism names a current-code anchor the reverifiers resolved and a delivery test under G1 through G4; readiness attests feasibility of named seams, not product behavior; and the moderator authored no approval of its own repairs, which rest on the two independent reverification contexts. This does not approve unimplemented behavior.

### First readiness run, superseded 2026-09-10

- Prior readiness verdict, first council run: PASS (moderator wave-council; primer-depth full; seats red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, docs-contract-reviewer; rotating-seat docs-contract-reviewer; strongest-challenge: completed receipts and separate finalizers could bypass the new migration or split publication; strongest-alternative: compact graph snapshots inside SQLite simplify persistence but require whole-graph rewrites). Its approvals bound a receipt the later scope clarifications superseded; retained as history.

All seven required lanes recorded typed readiness approvals. No actionable findings: architecture checked transaction and cache ownership; security checked receipt/cleanup boundaries; QA checked comparison and recovery contracts; reality checked proposed versus demonstrated behavior; the rotating docs seat weighed the snapshot alternative. Separate own-first code, release, performance and docs assessments supplied those lane approvals. Those four supplemental roles and final synthesis share one reviewer context; they are independent of the author, not of each other. All fixed seats explicitly weighed the alternative and retained stable tables for change-sized updates. The full reports, primer, closing pass, controls and context limitations are in [readiness-review.json](readiness-review.json); events.jsonl is the approval authority.

Readiness improvements: schema 8 allocation, shared filename/persistence ownership, dashboard/map consumer coverage, graph-only/semantic-only freshness rules, parent-authorized final publication, bounded coherent response snapshots, versioned receipt dispatch, strict source rebuild failure and fixed measurement samples are explicit. Operator acknowledgment is the recorded direction to consolidate, rename, rebuild graph from sources, compare results and clean owned artifacts after verification. Review plan has no unresolved operator question. Runtime, migration and native-platform qualification remain delivery/release gates.

#### Falsification Check, first run

Approve readiness only. The strongest objection is that a complete plan can still be implemented with the old completed-receipt short circuit, separate finalizer or overly broad deletion. Current-source review confirms these are real seams; the admitted publication, recovery, cleanup and reader tests explicitly target them before live adoption. The closing red-team held the empty finding set. This does not approve unimplemented behavior.

## Completion criteria

Every admitted AC/task reconciled with change-local evidence; atomic publication and coherent readers proven; standard upgrade/recovery and owned cleanup verified; native qualification status explicit; required independent reviews complete. Closure and release remain operator-owned.

## Handoff or next-wave notes

Implementation and required specialist reviews are complete. Final council and closure records bind the current tree; subsequent work is native supported-platform local-package qualification under G4. Historical evaluation evidence remains separately scoped. No commit or release is included.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 128 | 4,045,831 |
| implement | 216 | 3,764,228 |
| review | 871 | 12,204,301 |
| **Total** | **1,215** | **20,014,360** |

<!-- wave:context-efficiency-state {"generation":1247,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":216,"content_source_credit":4136339,"derived_artifact_credit":1426,"direct_net":3764228,"estimated_tokens_saved":3764228,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":8109,"response_debit":380746,"source_credit_count":83,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":15318},"plan":{"calls":128,"content_source_credit":4350045,"derived_artifact_credit":3511,"direct_net":4045831,"estimated_tokens_saved":4045831,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":17479,"response_debit":302512,"source_credit_count":123,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":12266},"review":{"calls":871,"content_source_credit":14496088,"derived_artifact_credit":5605,"direct_net":12204301,"estimated_tokens_saved":12204301,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":88349,"response_debit":2210932,"source_credit_count":417,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1889}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":1215,"content_source_credit":22982472,"derived_artifact_credit":10542,"direct_net":20014360,"estimated_tokens_saved":20014360,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":113937,"response_debit":2894190,"source_credit_count":623,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":29473},"wave_id":"1xny6 unified-index-database"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 46 | 0 | 13 | 26,700,139 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":13,"estimated_exploration_avoided":26700139,"surfaced_events":46} -->
<!-- wave:exploration-avoided end -->
Operator scope addition, 2026-09-10: include the canonical `.wavefoundry/locks/` ignore rule and regeneration verification (Requirement 10 / AC-12). Preserve the wildcard and project-owned rules. Re-Prepare remains required before source edits.
