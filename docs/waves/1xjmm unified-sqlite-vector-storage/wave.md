# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-09
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1xjmm unified-sqlite-vector-storage`
Title: Unified SQLite Vector Storage

## Objective

Replace local LanceDB storage with one SQLite store for chunk text, vectors, FTS and indexing state. Preserve retrieval and incremental updates, migrate destinations through standard wf_upgrade, and retire obsolete data only after verified publication and recovery tests.

## Changes

Change ID: `1xj6o-ref unified-sqlite-vector-storage`
Change Status: `complete`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: senior-data-engineer (schema/transactions/migration), implementer (runtime, adapters, upgrade and cleanup); serialized shared-file edits
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer, security-reviewer, release-reviewer, performance-reviewer, docs-contract-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer, performance-reviewer, security-reviewer

Completed At: 2026-09-09

## Wave Summary

Wave `1xjmm` (Unified SQLite Vector Storage) delivered one change: Convert Local Vector Storage to Unified SQLite. Notable adjustments during implementation: Convert Local Vector Storage to Unified SQLite: ARCH-DEL-1 retained-stage recovery guard added.

**Changes delivered:**

- **Convert Local Vector Storage to Unified SQLite** (`1xj6o-ref unified-sqlite-vector-storage`) — 10 ACs completed. Key decisions: No bridge release; complete compatibility work within this wave's standard `wf_upgrade` conversion; Stage beside the current stores, validate, then cut over and clean up

Validation: current 8,714-test receipt (five skips), all required delivery lanes, isolated final readiness refresh, package resume fixtures, source MCP full rebuild and operator-reported destination upgrades. Source rebuild reconciles 31,816 docs and 9,066 code rows with live FTS, no missing/orphan vectors and integrity ok. Local package: 1.23.0+powy; no release published.

Intentionally unmet ACs (`[~]`): none. Native Windows/Linux/Intel execution remains operator-authorized release follow-through; quantization and graph/memory consolidation were outside scope. Decisions and lessons are retained in accepted ADR 1xjmn, canonical upgrade/storage guidance and validated memory 1xk4o: preserve receipt/publication authority, identify packages by content, and separate owned-store cleanup from shared dependency ownership. Project-authored prompts require explicit clause reconciliation. Closure memory proposal returned zero pending/new candidates.

## Watchpoints

Historical implementation watchpoints below are resolved for local delivery; retained for provenance.

- Blocking watchpoint: G0 readiness then activation, G1 concrete runtime/migration contract before production adapter edits; evaluation1xhbo is closed.
- Cleanup is conditional on new-process verification and proven path/environment ownership.
- Runtime choice and old-process exclusion are G1 deliverables, not claims established by the prototype.
- Prepare council primer depth: full (persistent format, cleanup authority, native runtime, cross-project environment and old-process boundaries). Rotating fifth seat: docs-contract-reviewer, matching the computed policy receipt; release-reviewer additionally checks deployment.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| ALIAS-DOC-1 | do_now | no | completed | docs-contract-reviewer, release-reviewer |
| ARCH-DEL-1 | do_now | no | completed | architecture-reviewer, qa-reviewer, release-reviewer, code-reviewer, wave-council-delivery |
| DOC-DEL-1 | do_now | no | completed | docs-contract-reviewer |
| FINAL-DOC-1 | do_now | no | completed | architecture-reviewer, docs-contract-reviewer |
| HEALTH-FTS | do_now | no | completed | code-reviewer, qa-reviewer, docs-contract-reviewer |
| HEALTH-RECOVERY | do_now | no | completed | code-reviewer, qa-reviewer, docs-contract-reviewer |
| MAINT-GRAPH | do_now | no | completed | architecture-reviewer, qa-reviewer, wave-council-delivery |
| MAINT-REPORT | do_now | no | completed | code-reviewer, qa-reviewer, wave-council-delivery |
| MAINT-TEXT | do_now | no | completed | docs-contract-reviewer, qa-reviewer, wave-council-delivery |
| PLAT-1 | do_now | no | completed | code-reviewer, qa-reviewer, architecture-reviewer |
| PLAT-2 | do_now | no | completed | release-reviewer, docs-contract-reviewer |
| PLAT-3 | do_now | no | completed | code-reviewer, qa-reviewer, performance-reviewer |
| PLAT-4 | do_now | no | completed | code-reviewer, qa-reviewer |
| PLAT-5 | do_now | no | completed | security-reviewer, architecture-reviewer, qa-reviewer |
| PLAT-6 | do_now | no | completed | release-reviewer, qa-reviewer, architecture-reviewer |
| PLAT-DOC-7 | do_now | no | completed | docs-contract-reviewer |

*Machine review state — 16 findings; current: do_now 16, maybe_later 0, dont_do_later 0, not_issue 0*
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

## Review Checkpoints

- **Delivery-phase Wave Council [delivery-council] — 2026-09-09: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: unknown external clients may read the removed key; strongest-alternative: retain a deprecated alias for one release, rejected because the operator explicitly chose immediate removal with a 1.23.0 migration notice). Full council coverage of the intentional API change; paired code/QA, performance/reality and docs/release perspectives are not extra independent votes. The docs seat found ALIAS-DOC-1 in two active tool descriptions; bounded correction and independent cycle-6 replay cleared it. Final agreement is unanimous with no unresolved reviewer blockers. Current full suite: 8,661 tests, five skips. Reports and mutation tables are retained in implementation-evidence.json under alias_retirement.

**Platform repair cycle 3 — 2026-09-09.** All six accepted platform findings and the additional recovery-documentation finding are independently cleared. The current 8,658-test suite and exact test4 package qualification pass. Native platform qualification and operator delivery signoff remain pending. Full repair reports and mutation evidence are retained in implementation-evidence.json under platform_repair; no extra Markdown reports were created.

**Earlier architecture-filter review — 2026-09-09.** The architecture-filter repair has
independent code, QA and architecture reports, native negative controls and live
semantic MCP verification. Historical filter-repair suite: 8,638 tests / 84 files / five skips.
The source tree remained frozen throughout those reviews. FINAL-DOC-1 reconciles
stale current-status prose and is independently cleared across all current sections
and both handoffs. Independent focused council approves local technical delivery;
receipt refresh and operator closure checks remain separate. Reports are retained in implementation-evidence.json under
architecture_filter_final_review; no new Markdown report files are required.

**Earlier local conversion delivery — 2026-09-09: approved for its reviewed tree.**
Seven specialist approvals and the full Wave Council delivery are retained in the
ledger. Fixed seats: architecture, security, QA and reality-checker; rotating fifth:
release reviewer. All weighed and rejected mandatory re-embedding because it loses
compatible reuse while retaining the same publication/recovery gates. ARCH-DEL-1
and DOC-DEL-1 were independently repaired. The prior 8,637-test receipt and test3
package qualify the earlier conversion tree, not the later architecture-filter repair.

The standard live repository upgrade completed, including verified SQLite publication
and owned Lance cleanup; live-upgrade-evidence.json records the exact package and
operator-confirmed 132-source memory recovery. Graph and memory stores remain separate.
ADR 1xjmn is accepted. The test4 package now includes the filter and platform repairs. Native testing
on other platforms remains release follow-through; operator signoff, closure and commit
are not implied by local technical approval.

Historical readiness checkpoints follow.

Operator decision: **No bridge release.** The rotating review's conditional bridge-release alternative
is rejected, not a fallback delivery plan. Resolve compatibility through this wave's standard
`wf_upgrade` path; unresolved G1 evidence still blocks dependent conversion. This does not waive
runtime, process-exclusion, recovery or platform gates.

G0 checkpoint 2026-09-09: evaluation 1xhbo closed; implementation explicitly authorized.
Fresh full-depth primer, all seven requested readiness lanes and final council completed. Full reports
and bounded controls are retained in `runtime-qualification.json`, with approvals in the typed ledger.
Prepare passed and Implement wave opened this wave. No conversion source edits yet; G1 remains unresolved.

- **Prepare-phase Wave Council [prepare-council] — 2026-09-09: PASS** (moderator: wave-council; primer-depth: full; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: exclude incompatible consumers and retain recoverable publication state; strongest-alternative: separate compatibility release considered and rejected by operator)

Seat agreement: unanimous G0 approval; highest severity high applies to retained later-gate
compatibility/recovery obligations, not an unresolved G0 blocker. Reality's supplemental code,
performance and release assessments share one context and count as one council seat. Four targeted
role follow-throughs explicitly weighed the rotating alternative; they are not extra votes or the
original seat identities. The `reality-checker` found no G0 blocker: real plan-parser baseline and six
omission controls passed; runtime/first-hop proof and growth disposition remain later obligations.
Its full evidence is in `runtime-qualification.json` under `readiness_reviews.reality_supplemental`.
Final independent synthesis resolved the protocol follow-through. The
operator rejected the unselected bridge proposal; the approved delivery path remains standard upgrade.

G1 local runtime probes passed on macOS ARM64 with Python 3.11.13 and 3.13.5, APSW 3.53.4.0,
SQLite 3.53.4 and sqlite-vec 0.1.9. Native cosine, atomic chunk/vector/external-FTS rollback,
WAL snapshots, FK/readonly rejection, keyed backup, integrity and reopen were exercised. Other
platforms remain unexecuted. Operator was asked whether local qualification may unlock adapter
development while other platforms remain gated before enablement/release; no answer or timing
revision is assumed.

An exact archived hook/finalizer boundary probe covered 1.16.2+pipa and 1.22.0+pomi. A fail-hard
incoming hook stopped downstream index/cleanup reachability, but an already-extracted retry
deleted the generic checkpoint in both versions. The separate migration receipt survived. G1 must
resolve receipt-first recovery and old-host exclusion; this narrow probe is not a full upgrade pass.
The supported upgrade floor is not narrowed merely to the oldest locally available archive.

### ADR addition — 2026-09-09

Operator requested durable ADR documentation and clarified database placement. Added proposed
[ADR 1xjmn](../../architecture/decisions/1xjmn-adr%20unified-sqlite-vector-storage.md): both docs and code
share `.wavefoundry/index/index-state.sqlite`, with separate logical tables and one canonical text copy.
The plan now explicitly names this existing path and tracks ADR finalization at G1. Operator also
required cleanup of legacy `__manifest` alongside the code/docs stores: exact targets are
`.wavefoundry/index/__manifest/`, `code.lance/` and `docs.lance/`, only after verified migration.
AC-7/8 and cleanup tasks cover retention on failure and no recreation after search/refresh/reopen. Prior architecture
review covers its recorded plan fingerprint; changed-plan readiness must be refreshed. No database
conversion or external reviewer execution occurred.

### Preparation review — 2026-09-09, incomplete

Docs/gardening validation passed. Prepare owns the current policy receipt; the wave remains planned,
not readied or active, pending the remaining independent lanes and wave-council-readiness.
No implementation or destination mutation occurred.

Full-depth isolated red-team primer completed first. Strongest challenge: an old coordinator may
continue after semantic-index failure and release publication fencing at cleanup while older native
processes remain. Best alternative: keep standard wf_upgrade and stage/verify/retire, but prove an
explicit executing-version/process/authority/receipt/recovery table through the oldest supported
runner at G1. The three primer questions cover first-hop process exclusion, cutover/cleanup/receipt
predicates and runtime/platform/envelope evidence. Its initial plan recommendations were applied:
required lanes explicit, G1 followed by concrete-contract re-Prepare, no new global registry merely
to uninstall dependencies. No red-team product certification or council synthesis is claimed.

Architecture readiness: **PASS**, independent Codex session
`01a0842f-4602-7e51-a48b-c796e81eb143`, frozen plan git hash
`89683f76b0b8d117262acc09314ab6e222f896b2`. Typed approval recorded in events.jsonl.
Validated source anchors: upgrade_wavefoundry.phase_index_update/phase_cleanup,
publication_control.publication_checkpoint_reason, IndexStateStore.ensure_current/reset,
finalize_build_epoch/build_epoch_token and _semantic_epoch_matches_active_models.
Q1 remains a required G1 executable handoff, not a guessed implementation; Q2 requires stable current
SQLite authority before accepting writes or owned cleanup, with migration progress subordinate to it;
Q3 requires platform/runtime and actual quality/availability gates before adoption. The staged design
is stronger than delete-first or permanent dual writes. G1 follow-through must include old schema-reset
consumers and update domain-map.md/layering-rules.md to preserve the single semantic-authority contract.

| Architecture plan control | Counterfactual omitted clause | Observation |
| --- | --- | --- |
| ARCH-P1 | Invoking old MCP exclusion | Detected |
| ARCH-P2 | Replacement/receipt/CAS non-atomicity | Detected |
| ARCH-P3 | Current-state retry validation | Detected |
| ARCH-P4 | Newer-write rollback protection | Detected |
| ARCH-P5 | Pre-production re-Prepare | Detected |

All five original clauses passed; in-memory omissions failed. These checks establish plan-contract
presence only; no migration, platform, availability or production transaction was executed.
Full transient report: `/tmp/1xjmm-architecture-review.txt`; review facts above and typed ledger are durable.

Historical review execution blocker (resolved by later explicit operator authorization for read-only
OpenAI Codex reviews): built-in fresh-agent thread capacity was exhausted. One external read-only
Codex CLI architecture session was approved and completed. Automatic approval review rejected the
additional security/QA sessions because external model-service transfer of private repository content
lacked specific destination authorization. No alternate external route was attempted before authorization.
Current continuation uses that authorization; no missing approval is inferred.

## Dependencies

- Evaluation wave 1xhbo: reviewed 1xhdh shared-layout evidence and corrected static CPU reranker 1xj6n. Freeze those exact inputs before implementation; final delivery review and closure passed, including exact source/model identities and three bounded CPU exceptions.
- Operator product intent: conversion and cleanup plan explicitly requested, followed by preparation/review/implementation; no new search behavior or release version approved.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 581 | 16,262,290 |
| implement | 573 | 8,588,058 |
| review | 1,424 | 25,872,052 |
| **Total** | **2,578** | **50,722,400** |

<!-- wave:context-efficiency-state {"generation":2534,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":573,"content_source_credit":9808334,"derived_artifact_credit":1114,"direct_net":8588058,"estimated_tokens_saved":8588058,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":20041,"response_debit":1207586,"source_credit_count":218,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6237},"plan":{"calls":581,"content_source_credit":17768136,"derived_artifact_credit":1543,"direct_net":16262290,"estimated_tokens_saved":16262290,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":21562,"response_debit":1519993,"source_credit_count":330,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":34166},"review":{"calls":1424,"content_source_credit":29489265,"derived_artifact_credit":11890,"direct_net":25872052,"estimated_tokens_saved":25872052,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":161948,"response_debit":3469044,"source_credit_count":655,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1889}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":2578,"content_source_credit":57065735,"derived_artifact_credit":14547,"direct_net":50722400,"estimated_tokens_saved":50722400,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":203551,"response_debit":6196623,"source_credit_count":1203,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":42292},"wave_id":"1xjmm unified-sqlite-vector-storage"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 192 | 0 | 32 | 126,089,430 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":32,"estimated_exploration_avoided":126089430,"surfaced_events":192} -->
<!-- wave:exploration-avoided end -->
Health recovery follow-through complete: dependency/bootstrap guidance uses wf setup; ordinary staleness uses MCP update; chunker mismatch uses rebuild; storage failures preserve their specific remedy. Structural corruption retains concurrent diagnostics while all guidance prioritizes preservation. The full suite caught and drove repair of an FTS diagnostic regression; independent review and the final 8,660-test run pass. Detailed evidence is in implementation-evidence.json under health_recovery_guidance. No closure, commit or package publication was performed.

Alias retirement is implemented: live and fallback coverage expose vector_rows only; consumers, tests, current tool documentation and the 1.23.0 migration notice agree. Full suite: 8,661 tests, five skips; current receipt and live MCP smoke pass. Final independent docs/release verification is approved and recorded. No storage/schema change, package build, closure or commit is included.

Release target: 1.23.0. Version 1.22.0 is already tagged; this wave's new changelog entries are under 1.23.0. Existing test3/test4 package evidence retains the versions actually tested.

Maintenance follow-through (2026-09-09): implementing operator-authorized AC9 corrections MAINT-REPORT, MAINT-GRAPH and MAINT-TEXT. Existing delivery approvals precede these edits; current full-suite and focused repair review will refresh. Builder lanes: coordinator implementer (response/terminology) and senior-data-engineer (graph reclamation).

Maintenance verification complete: 8672 tests/five skips, current green hash 505ea45016622a4b20cc14398e5742e76e4fa4ef928857c6e6f0ea85d76d8663. Independent repair findings terminal and code/QA/architecture/docs technical perspectives approved. Formal readiness and delivery Council refresh remain pending; wave remains implementing/open and uncommitted.

Recovery artifact correction: use the revision-2 povc rebuild kit referenced in implementation-evidence.json. It covers the normal failed-indexing checkpoint retained at awaiting_memory_validation; unchanged powm passed the same-state ordinary rebuild replay. No checkpoint edits or new feature package were needed.

Current package follow-up: 1.23.0+powy adds explicit every-upgrade reconciliation of storage recovery instructions into existing project prompts while preserving customizations. Independent review, 8,714-test receipt, docs validation and two packaged resume tests pass. Operator-reported povc recovery/MCP smoke/powm upgrade results are recorded separately in implementation-evidence.json. Wave remains open.

## Closure Reconciliation

All ten ACs and all tasks are complete; no silent unchecked or intentionally unmet items remain. Seven required delivery lanes and selected council delivery approvals are reconciled in typed evidence; final readiness refresh addresses the PROMPT-RECOVERY task digest. Operator explicitly authorized closure and commit after package and MCP rebuild results. Docs-contract review was performed (DOC-DEL-1, FINAL-DOC-1, platform/alias and final prompt-guidance reports); no current blocker remains. Framework receipt is current and docs validation passed.

Memory/retrospective checkpoint completed: reviewed the non-obvious recovery, ownership and prompt-carrier lessons above against accepted ADR/current canonical instructions and existing memory; memory_propose returned zero pending/new candidates, with existing disposition retained. Handoff will be reset to idle after successful closure. Chronology/status timestamps are finalized by wf_close_wave. Scanner coverage skips the presentation and two compressed evidence archives; no unresolved secrets findings were reported.
