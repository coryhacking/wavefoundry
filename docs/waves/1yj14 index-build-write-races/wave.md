# Wave Record

Owner: Engineering
Status: closed
Completed at: 2026-09-20
Last verified: 2026-09-19
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1yj14 index-build-write-races`
Title: Index Build Write Races

## Objective

Prevent automatic server document writes from invalidating index builds. Recover once from transient source drift and restore an intact prior snapshot only after verified precommit rollback, preserving unified publication and fail-closed behavior for unsafe failures.

## Changes

Change ID: `1yjof-bug index-build-races-server-doc-writes`
Change Status: `complete`

## Participants

- Coordinator: Codex coordinator
- Write-owning roles: implementer (indexer and server), technical-writer (architecture)
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer, performance-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, performance-reviewer

Completed At: 2026-09-20

## Wave Summary

Delivered automatic server/build source exclusion, one bounded fresh-preparation retry, and prior-snapshot availability only after verified precommit rollback. Unified publication remains intact; unsafe, uncertain and postcommit failures remain fail-closed. Recovery assigns a distinct reader token, rebinds matching lexical statistics and preserves historical layer publication stamps. Corrected optimize failure reporting and source-guard reload freshness, with real-producer and independent import-derived regression coverage.

No admitted AC or task is deferred; all are checked complete and there are no `[~]` ACs. Crash recovery, partial publication and broad record restamping remain outside scope. Operator selected bounded retry over publishing a partial changed-file exclusion set.

Retrospective: the non-obvious boundary is reader availability versus source freshness; restoring historical content must not claim a new publication. A producer-key rename can hide a fail-closed state when tests fabricate the old result shape. Reload coverage must derive expected modules independently from the purge set it validates. These lessons are recorded in the ADR, plan and canonical project-context memory.

## Watchpoints

- No code edits before typed readiness. Preserve unrelated dirty work. One retry maximum; no partial publication; postcommit and uncertain failures remain fail-closed.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| B-1-optimize-error-contract | do_now | no | completed | code-reviewer, qa-reviewer, wave-council-delivery |
| recovery-provenance-doc-overclaim | do_now | no | completed | architecture-reviewer, wave-council-delivery |
| reload-source-guard-omission | do_now | no | completed | code-reviewer, architecture-reviewer, wave-council-delivery |
| uncertain-recovery-diagnostic | do_now | no | completed | code-reviewer, wave-council-delivery |

*Machine review state — 4 findings; current: do_now 4, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| wave-council-delivery | approved | current executed approval by coryhacking follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking follows every affected repair | none |
| architecture-reviewer | approved | current executed approval by coryhacking follows every affected repair | none |
| performance-reviewer | approved | current executed approval by coryhacking follows every affected repair | none |
| operator-signoff | approved | current executed approval by coryhacking follows every affected repair | none |
<!-- wave:review-status end -->

- Operator explicitly approved closure on 2026-09-20 after cycle 2 repairs; typed operator approval recorded.

## Dependencies

- No external wave dependencies.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 132 | 1,123,981 |
| implement | 53 | 1,801,251 |
| review | 199 | 5,316,211 |
| **Total** | **384** | **8,241,443** |

<!-- wave:context-efficiency-state {"generation":260,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":53,"content_source_credit":1938991,"derived_artifact_credit":0,"direct_net":1801251,"estimated_tokens_saved":1801251,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1678,"response_debit":137965,"source_credit_count":38,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1903},"plan":{"calls":132,"content_source_credit":1399569,"derived_artifact_credit":1231,"direct_net":1123981,"estimated_tokens_saved":1123981,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":10534,"response_debit":272217,"source_credit_count":49,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5932},"review":{"calls":199,"content_source_credit":5737443,"derived_artifact_credit":3908,"direct_net":5316211,"estimated_tokens_saved":5316211,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":37260,"response_debit":389882,"source_credit_count":155,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2002}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":384,"content_source_credit":9076003,"derived_artifact_credit":5139,"direct_net":8241443,"estimated_tokens_saved":8241443,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":49472,"response_debit":800064,"source_credit_count":242,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":9837},"wave_id":"1yj14 index-build-write-races"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 13 | 0 | 6 | 7,019,916 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":6,"estimated_exploration_avoided":7019916,"surfaced_events":13} -->
<!-- wave:exploration-avoided end -->
## Work allocation

Full-depth readiness primer: independent storage_primer context. Writer census and concurrency probes: storage_code_ready. Publication feasibility: storage_reverify. Coordinator owns plan and final integration. Existing agent contexts are reused from the prior wave; they are independent of this plan author, not newly isolated sessions. Council seats will disclose context sharing. No implementation delegated before readiness.

## Review checkpoints

- **Cycle 2 focused replay — 2026-09-20: PASS (full suite green: 9,409 tests/113 files, 12 skips, 294.799s).** Independent code and QA contexts each killed the real optimize producer `error` → `failure` mutation across all four failure-path tests. Both verified native reload rejects a missing source-guard purge entry; coverage expectations derive from direct sibling imports, with four explicit bootstrap exclusions. Independent architecture/security verified valid lexical-cache rebinding, rejection of mismatched attempt/generation, historical layer stamps, and stale-source health across 26 focused tests. Frozen code hashes: indexer `4e1619315ff25a33516211869925ca96706b21ea`, server_impl `8941bede3ccf7357639e6510d0f9b0ea22cd4c34`, optimize tests `a1baa8af8405496ee7e95c1ca7054c61cb0bcc26`, lifecycle structure tests `6ac6b0f3e7ea9266b24e5b81c6f8500be13206b8`. All three typed finding heads are completed; aggregate cycle 2 convergence checkpoint recorded.
- **Prepare-phase Wave Council [prepare-council] — 2026-09-20: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, security-reviewer; rotating-seat: security-reviewer; strongest-challenge: provenance narrowing could hide invalid reader-token relabeling; strongest-alternative: fail closed for all recovery or rebind every layer stamp). Independent red-team primer came from the code-review context; isolated security seat addressed it through native cache counterexamples and production reader census. Architecture shared the security context and is not a second independent vote. No material disagreement remained: retain historical publication stamps and rebind only matching lexical cache. Typed readiness reaffirmed and re-Prepare passed on receipt `review-policy-276278671d392a584cbc`.
- **Memory capture — 2026-09-20:** `memory_propose(mode='create')` refused with `memory_state_unwritable` before writing candidates. No production-index repair or rebuild was attempted; this was resolved at closure through a fresh stdio MCP process and explicit candidate validation.

- **Operator delivery review — 2026-09-20: NOT READY.** Cycle 2 records B-1 optimize result-key failure, omitted reload guard, and overbroad provenance wording. Repairs restore the established error contract, derive direct sibling reload coverage independently, and preserve historical layer stamps explicitly. Earlier full-suite receipt does not cover these findings; fresh verification is required.

- Prepare: full adversarial primer rejected predicate-only locking, partial graph publication and broad marker rollback. Operator selected bounded coherent retry with verified precommit recovery. Independent fresh readiness review approved the final concrete contract before activation.
- Delivery: policy-selected red-team and security perspectives ran in distinct author-independent contexts. Additional code/architecture/performance perspectives shared the delivery code reviewer; QA had a separate fresh context; security/reality-checker and synthesis shared the council reviewer. These are disclosed context groupings, not independent votes per role.
- Strongest challenge: recovery must never relabel committed resident changes. Native own-commit observation, external data_version, confirmed rollback and attempt CAS were independently tested, including guard-removal mutants. Best alternative: interlock-only is smaller but misses admitted operator-edit retry and previous-snapshot availability; partial publication would require dependency-aware graph/community reconstruction. No unresolved disagreement.
- Verification: 9,402 tests across 112 files passed; 12 aggregate skips. Wave-focused 26 tests had no skips; independent QA killed eight targeted mutants. Full docs validation passed. The sole diagnostic finding was repaired in cycle 1 and independently reverified. The intentional index_build wording change updated exactly one handler digest fixture entry; all 89 current handler digests match.
- Scope: no crash recovery, partial publication, remote deployment, commit or wave closure. Operator signoff remains operator-owned.


## Closure reconciliation

1. Change complete; every required AC and task has verification evidence.
2. Code, QA, architecture and performance lanes reconciled; independent cycle 2 replay completed.
3. Current typed readiness and delivery Council approvals recorded against the re-Prepared receipt.
4. Docs-contract review: not applicable; no `docs/specs/*.md` changed in this wave. Architecture/ADR documentation reviewed and full docs lint passed.
5. Authorized close succeeded on 2026-09-20; wave is closed, completion date recorded, change status complete.
6. Close-time memory candidates drafted through a fresh stdio MCP process after the attached host's stale runtime refused writes; focused validation rejected malformed temporary-path targets after rewrite was refused; durable lessons were promoted to `docs/references/project-context-memory.md`.
7. Durable lessons are retained in canonical ADR/plan and validated memory; project-context pointers added at closure.
8. Retrospective completed above: recovery provenance, real-producer failure tests, and independent reload census.
9. Idle session handoff records the closed wave and remaining host-restart note.
10. All AC/task checkboxes reconciled; no silent unchecked or intentionally deferred items.

- **Close memory validation — 2026-09-20:** independent curator verified both sources and recommended precise rewrites. The validator rejected rewrite because original targets were absent temporary probe paths. Candidates were explicitly rejected with that rationale; durable lessons were promoted to project-context memory instead. No pending candidate or invented target remains.
