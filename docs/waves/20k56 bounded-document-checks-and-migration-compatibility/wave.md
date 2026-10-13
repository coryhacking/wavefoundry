# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-13
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `20k56 bounded-document-checks-and-migration-compatibility`
Title: Bounded Document Checks And Migration Compatibility

## Objective

Bound ordinary docs validation, preserve useful document-move previews when new-only targets cannot be confirmed, and support explicit exact legacy prompt profiles without adding installed-framework imports.

## Changes

Change ID: `20k55-bug bounded-document-checks-and-migration-compatibility`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer, security-reviewer, docs-contract-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, security-reviewer

Completed At: 2026-10-13

## Wave Summary

Wave `20k56` (Bounded Document Checks And Migration Compatibility) delivered one change: Bounded document checks and migration compatibility.

**Changes delivered:**

- **Bounded document checks and migration compatibility** (`20k55-bug bounded-document-checks-and-migration-compatibility`) — 4 ACs completed. Key decisions: Reuse central descriptor reads with an explicit no-link policy; report refused docs as non-clean.; Skip and report only unconfirmable new-only role targets, preserving old-source preflight.

All admitted ACs and tasks are complete; none are deferred. Required independent reviews, repair reverification and operator approval are recorded. Final integrated qualification passed 12,471 tests across 185 files with 12 reported skips and a matching green framework receipt. Native Windows, live-host and exact new-archive qualification are not claimed. Timing investigation remains deferred while concurrent reviews run.

Retrospective and memory: the code-boundary lessons and negative controls are retained in canonical tests, architecture/spec documentation and this record. Close-time memory proposals found no eligible durable candidate; no duplicate memory file was created. Cleanup retains only wave.md, the admitted change and authoritative events.jsonl in this folder. Cited temporary review evidence remains at its recorded paths; no permanent evidence folder or duplicate readiness artifact is needed.

## Watchpoints

- Strict docs reads must be explicit: default contained reads intentionally support internal links.
- Preserve old-source move preflight and exactly-one legacy contract recognition.
- Serialize shared upgrade-test and architecture/spec/changelog edits with sibling waves; no source edits before readiness.
- Retain compact durable outcomes here and in the admitted change; no new evidence folder. Native Windows execution is not assumed.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| QA-20K56-STALE-CONTAINED-WRAPPERS | do_now | no | completed | qa-reviewer |

*Machine review state — 1 findings; current: do_now 1, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| architecture-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| security-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: operator explicitly authorized closure, commit and push on 2026-10-13; typed approval records that instruction.

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 190 | 2,458,640 |
| implement | 117 | 1,590,664 |
| review | 57 | 1,274,785 |
| **Total** | **364** | **5,324,089** |

<!-- wave:context-efficiency-state {"generation":243,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":117,"content_source_credit":1804500,"derived_artifact_credit":0,"direct_net":1590664,"estimated_tokens_saved":1590664,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4237,"response_debit":212827,"source_credit_count":47,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3228},"plan":{"calls":190,"content_source_credit":2994525,"derived_artifact_credit":2545,"direct_net":2458640,"estimated_tokens_saved":2458640,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":44634,"response_debit":500299,"source_credit_count":147,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6503},"review":{"calls":57,"content_source_credit":1408132,"derived_artifact_credit":0,"direct_net":1274785,"estimated_tokens_saved":1274785,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1748,"response_debit":134530,"source_credit_count":27,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2931}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":364,"content_source_credit":6207157,"derived_artifact_credit":2545,"direct_net":5324089,"estimated_tokens_saved":5324089,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":50619,"response_debit":847656,"source_credit_count":221,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":12662},"wave_id":"20k56 bounded-document-checks-and-migration-compatibility"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 30 | 0 | 22 | 14,833,219 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":22,"estimated_exploration_avoided":14833219,"surfaced_events":30} -->
<!-- wave:exploration-avoided end -->
## Current assumptions

Source-level declarations travel with the incoming pack; they are not target runtime configuration. Refused docs remain non-clean lint results, while skipped unconfirmed new-only role pairs are migration diagnostics. These separate outcomes preserve existing gate intent.

## Outputs produced or expected

One bounded document-read policy, consistent role-preview diagnostics, one empty additive exact-profile declaration, canonical regression tests and updated existing contract docs.

## Review checkpoints

Readiness, all five specialist delivery approvals and council-delivery are current. Full/incremental lint, role-only/combined preview/apply and standalone/installed/incoming classification have successful and refusal/ambiguity controls. Both stale mock wrappers were repaired without weakening their race injections; fresh QA cleared the finding with original-oracle negative controls. Canonical qualification passed 12,471 tests across 185 files with 12 reported skips.

Council used a full independent red-team primer and closing, architecture/security/QA/reality fixed seats, a rotating docs-contract seat and chair synthesis. Related specialist remits shared disclosed contexts. Each seat formed its own assessment, addressed the primer and weighed the alternative; bounded repairs received fresh affected-lane verification. A separate pruning protocol and provenance-module split were considered unnecessary for this scope, with no unresolved material disagreement or automatic backlog. No native Windows, live-host, release-archive or performance qualification is claimed. All ACs/tasks are complete; paused for operator signoff and closure.

## Completion criteria

Every admitted AC and task resolved with current required delivery approvals and qualification gates; leave the wave paused for operator-owned closure. Do not create packaging or commit obligations inside this wave.

## Handoff or next-wave notes

Planning only. No code edits or review signoffs yet. The coordinator may prepare, review and implement under the current operator request, then pause before moving to another wave.

## Review packet

Inspect the admitted change's Requirements, Decision Log and declared Serialization Points. Known source anchors: `read_doc_text` dispatch and full/incremental refusal collectors; `_confirmed_council_role_pairs` and its two callers; `classify_review_plan_prompt` and the standalone private-load contract. Review whether each negative outcome can fail without granting migration authority or producing a false clean lint result. No reported timing or live downstream qualification is claimed.

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-13 | Implementation and required independent delivery reviews complete. All three batch findings are repaired and independently cleared; all ACs/tasks are checked. Combined canonical qualification passes 12,471 tests across 185 files, 12 reported skips. Wave remains paused for operator signoff and closure. | Current typed approvals; green test receipt 83e8456ae65b35e56e2409ee1f48216471edb27552d52272329cd7bcbfc7c520; wave Review checkpoints |
| 2026-10-13 | After focused readiness currency and recorded repair start, both qualification-report and workflow-config mock wrappers now accept and forward containment keywords. Both original refusal tests pass with their injections/assertions unchanged. Production readers unchanged; fresh QA reverification and final qualification pending. | Canonical targeted controls; recorded cycle-1 repair; no release/closure claim |
| 2026-10-13 | Implemented strict cached ordinary-document reads, non-clean refusal reporting, new-only role/wrapper skip diagnostics, and exact source-declared legacy profiles. Final affected modules: 1,483 tests pass with one intended skip; 46 upgrade-boundary tests pass. Known-bad strict-link, new-only abort and ignored-declaration controls fail as intended. Full docs validation passes. Final combined qualification and independent delivery remain pending. | StrictCachedReadTests; StrictOrdinaryDocumentTests; NewOnlyRoleRefusalTests; DeclaredLegacyReviewPlanTests; native Windows unrun |
