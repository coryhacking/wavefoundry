# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-10
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `207t4 graph-community-publication`
Title: Graph Community Publication

## Objective

Preserve complete graph communities and members across reset publication and recover incomplete persisted memberships before fingerprint reuse.

## Changes

<!-- Changes admitted by wf_add_change. -->

Change ID: `207t3-bug graph-community-reset-publication`
Change Status: `implemented`

## Participants

- Coordinator: Engineering coordinator
- Write-owning roles: Implementer and technical writer
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, performance-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, performance-reviewer

Completed At: 2026-10-09

## Wave Summary

Delivered complete community replacement rows on reset publication and completeness checks before persisted fingerprint reuse, preserving atomicity and incremental behavior.

- All admitted changes are implemented and every AC and task is completed; there are no intentionally unmet checkboxes.
- All required specialist delivery approvals and council-readiness are current; findings are terminal. Council-delivery is not selected by the current Prepare receipt. Docs-contract review was performed where required.
- Operator closure approval was explicitly given and recorded as typed evidence on 2026-10-09. Completed chronology is recorded above.
- Closure proved the current green framework receipt: 11995 tests, hash 83a742059996ef0eedc2fd3c637d5ef8864dedfbdacbf8c8c88f29d226f86092. No framework code or seed changed during closure.
- Cleanup retains authoritative events, unique reports, reproducible probes, receipts and historical fingerprints in their existing evidence locations. The later authorized2026-10-10 cleanup removes verified redundant working copies; see Evidence Retention below.
- Retrospective: A reset needs complete replacement rows; matching fingerprints do not prove persisted membership completeness. The reviewed contracts and regression owners already capture this lesson; no additional durable memory is warranted.
- Memory checkpoint: memory_propose(create) was run; no pending candidate remains. The proposal produced zero new candidates.
- The session handoff records all six closures. Closure did not commit, push or publish a new pack.

## Watchpoints

- Watchpoint: public 204mp remains OPEN; this wave must be readied without activation.
- Preserve the completed Rust graph extraction and call-site changes.
- No close, commit or push authorization.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

*Machine review state — 0 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| architecture-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| performance-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 149 | 1,994,210 |
| implement | 90 | 1,511,280 |
| review | 250 | 594,686 |
| **Total** | **489** | **4,100,176** |

<!-- wave:context-efficiency-state {"generation":452,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":90,"content_source_credit":1753300,"derived_artifact_credit":0,"direct_net":1511280,"estimated_tokens_saved":1511280,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3259,"response_debit":240784,"source_credit_count":35,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2023},"plan":{"calls":149,"content_source_credit":2410054,"derived_artifact_credit":1688,"direct_net":1994210,"estimated_tokens_saved":1994210,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":11018,"response_debit":410319,"source_credit_count":75,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3805},"review":{"calls":250,"content_source_credit":1815380,"derived_artifact_credit":352,"direct_net":594686,"estimated_tokens_saved":594686,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":16225,"response_debit":1207205,"source_credit_count":80,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2384}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":489,"content_source_credit":5978734,"derived_artifact_credit":2040,"direct_net":4100176,"estimated_tokens_saved":4100176,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":30502,"response_debit":1858308,"source_credit_count":190,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":8212},"wave_id":"207t4 graph-community-publication"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 39 | 0 | 28 | 18,995,541 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":28,"estimated_exploration_avoided":18995541,"surfaced_events":39} -->
<!-- wave:exploration-avoided end -->
## Review Checkpoints

### Readiness coordination — receipt `review-policy-0cce62e074406ee233a9`

- Phase: readiness only; phase-isolation207lx currently owns OPEN. Public204mp is paused with its C5 finding open. No graph source edits or activation.
- Briefing packet: `/tmp/wf-207t4-readiness-packet.json`; nine scoped paths, eight current working-tree Git blobs plus planned-absent `test_graph_transactional_state.py`. Scope and source fingerprints stay fixed for this review.
- Primer declared before execution: standard, three stances, two questions per stance, as configured for this bounded repair of existing publication contracts. Actual isolated red-team context `graph_redteam_primer` ran first; fixed architecture/security/QA/reality seats are independent contexts, followed by rotating performance and independent chair synthesis. Required code/QA/architecture/docs/performance judgments remain their actual reviewers' responsibility.
- Allocation: inherited capable model requested for code-grounded reviews; observed runtime model/effort identity unknown. Isolation is necessary for independent priors; two reviews run concurrently only when host capacity permits. Coordinator writes lifecycle evidence, reviewers own judgments; no self-approval.
- Primer independently reproduced both reset cells: changed-fingerprint preparation omits unchanged rows; compatible predecessor walker with unchanged fingerprint returns no community publication and loses all community rows at real `build_index` commit. A reset always requires replacement publication; previous-generation ID remapping must remain distinct from the reset write baseline. Recovery controls include missing community/member and equal-count wrong identity; valid no-reset reuse is the positive control.
- Executed primer artifacts: `/tmp/wf-207t4-redteam-probe.py`, `/tmp/wf-207t4-redteam-build-probe.py` and their logs. Real reset/no-reset, WAL rollback visibility, and two existing transaction/source-read failure controls; no repair, approval, live rebuild, consumer response run or full suite claim.

### Full readiness review outcome

- Actual required code/QA/architecture/docs/performance reviewers approve current-plan feasibility with notes. All four fixed seats completed artifact-first pre-primer reads and explicitly weighed the rotating membership-digest alternative; no readiness candidates or blockers. Their individual initial reads, primer effects, all six answers, source anchors, commands, controls and limitations are preserved in `readiness-evidence.json`.
- Fresh chair context `207t4-council-chair-fresh-independent-20261009-01` ran the first synthesis on anonymized shuffled seat outputs before identity. Shared causal claims were deduplicated; no distinctive verbatim pre-primer contamination identified. The independently rerun real build reset loses 2 communities/9 members/1 analysis with identical fingerprint; two actual publication-fault/source-denial recovery tests pass without skips. Nine working-tree scope fingerprints unchanged.
- Council outcome: approved with notes; agreement unanimous, maximum readiness finding severity none. Red-team closing held the empty sealed candidate set before the chair's Falsification Check. No required-lane waiver, future-green claim or broader membership-digest requirement.
- Implementation guidance: preserve fresh/reset computation, reset with valid unchanged analysis and incomplete-member recovery; both exact indexer callers; old generation for supported ID remapping separate from empty replacement diff baseline; historical member fingerprints; exact projected identities/community catalog/fixed categories. At least two production and two evidence candidates must demonstrate independent order/identity and limits 1/2 after reset/recovery. Preserve global reset semantics, the sole transaction, and ordinary incremental/no-op writes.
- Strongest alternative considered: membership digests can certify more historical production-partition changes, but require format/backfill/provenance policy and cannot certify an already-corrupt baseline. All fixed seats retained the bounded plan. Documentation must describe structural/catalog/fixed-category completeness and must not claim certification of every structurally complete production repartition.
- Actual evidence is readiness-only. Canonical setup, original live queries, whole-suite green, implementation delivery review, pause/close/commit/push remain future work. No graph source edits or activation occurred during this preparation.

### Implementation freeze — graph207t4

- Change207t3 is implemented with AC1–5 complete; independent delivery review and canonical setup/full-suite tasks remain pending. This is a focused implementation result, not closure approval.
- Focused qualification: transaction/cluster94, controlled public responses3, whole indexer398; 495 passed, zero skips. Nine transaction and two consumer source mutants killed at substantive assertions. Evidence and exact nine frozen SHA256 paths: `implementation-evidence.json`; coordinator packet `/tmp/wf-207t4-frozen.json`.
- Both actual indexer reset callers, unchanged-fingerprint reset reuse, structural corruption recovery, empty/historical/fixed-category valid reuse, bounded writes, actual WAL/rollback/source/schema/global-reset versus ordinary-layer behavior and two independently limited production/evidence candidates are covered. No exact historical production repartition certification is claimed.
- Root owns canonical setup/original live consumer qualification, quiet full suite, C1 upstream test inventory and fresh independent delivery reviewers. Helpers finished; no close/commit/push or self-approval. Source freeze holds until root serializes the next wave.

### Independent delivery review outcome

All five required specialist lanes approved the frozen current scope through typed executable evidence after full canonical qualification. Three fresh independent contexts disclose separate code/QA, architecture/docs and security/performance remits; no implementer self-approval or required council-delivery waiver occurred. Exact reports are retained in ../204mp waveforge-follow-up/evidence/delivery-20261009-01.

Phase review additionally exercised a real producer-built terminal repair chain, fresh-delivery chronology, rejection without append of invalid reverification, and paired operator-blocked close. Graph review independently checked both callers, reset/reuse/recovery, literal production/evidence identities and hubs at limits1/2, retained Rust behavior, transactional/source/schema/layer controls, and realistic sparse50k cost. Reviewers disclose a redundant early fixed-category guard survivor; deletion of the actual combined invariant is detected. Structural completeness is not semantic partition certification.

All ACs and tasks are complete. Technical close dry run and pause follow; operator approval remains unrecorded. Subsequent unrelated framework edits require a fresh shared qualification receipt. No close, commit or push.

## Evidence Retention

Authorized cleanup on 2026-10-10 removed 2 redundant working files (19,560 bytes); 0 evidence files remain. The removed folder contained only byte-identical shared qualification copies; the originals remain in wave 204mp and qualification-evidence.md now links to them. Preserve this record, admitted change, immutable ledger and existing source-review proof. The 11,977-test shared receipt a77f5893ba5fc13cdddf41a465cd5e8f70d958f234cc722a11bdf2d879dbebac is historical qualification, not a new run. All ledger-cited paths and bytes stay unchanged.
