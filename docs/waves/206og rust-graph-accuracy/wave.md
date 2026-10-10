# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-08
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `206og rust-graph-accuracy`
Title: Rust Graph Accuracy

## Objective

Repair the three Tensorwell Rust graph findings after 1.29.0+pvbx: incorrect call-site provenance, unresolved typed loop bindings, and collapsed trait implementation identities. Validate target identity, exact locations and retained genuine relationships independently.

## Changes

Change ID: `206of-bug rust-graph-identity-and-provenance`
Change Status: `implemented`

## Participants

- Coordinator: Engineering coordinator
- Write-owning roles: Implementer and technical writer; assignments confirmed at Prepare
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, performance-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, performance-reviewer

Completed At: 2026-10-09

## Wave Summary

Delivered exact Rust call-site provenance, supported loop-binding inference and distinct trait implementation identities through extraction, resolution, storage and MCP projection. The Profile.as_str relationship was genuine; its displayed location was wrong. Live Tensorwell qualification remains a downstream follow-up.

- All admitted changes are implemented and every AC and task is completed; there are no intentionally unmet checkboxes.
- All required specialist delivery approvals and council-readiness are current; findings are terminal. Council-delivery is not selected by the current Prepare receipt. Docs-contract review was performed where required.
- Operator closure approval was explicitly given and recorded as typed evidence on 2026-10-09. Completed chronology is recorded above.
- Closure proved the current green framework receipt: 11995 tests, hash 83a742059996ef0eedc2fd3c637d5ef8864dedfbdacbf8c8c88f29d226f86092. No framework code or seed changed during closure.
- Cleanup retains authoritative events, unique reports, reproducible probes, receipts and historical fingerprints in their existing evidence locations. No artifact was established to be both disposable and redundant; none was removed.
- Retrospective: Target identity, retained genuine relationships and exact locations require separate publication assertions. The reviewed contracts and regression owners already capture this lesson; no additional durable memory is warranted.
- Memory checkpoint: memory_propose(create) was run; no pending candidate remains. The repeated write fence refused an empty batch; the read-only proposal confirms both prior candidates are dispositioned and zero remain. Their rejected records are preserved.
- The session handoff records all six closures. Closure did not commit, push or publish a new pack.

## Watchpoints

- Planning only; do not activate while wave 204mk occupies the open slot.
- Watchpoint: readiness contract specifies impl IDs, occurrence metadata and builder-version transition; independent review is pending.
- Preserve conservative unknown-member handling and current .collect() coverage.
- Tensorwell live results are reporter evidence; local reproduction and implementation are pending.
- Keep this graph work separate from public compatibility wave 204mp.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| rust-binding-lookup-quadratic | do_now | no | completed | performance-reviewer, code-reviewer, qa-reviewer |
| rust-let-initializer-shadow | do_now | no | completed | code-reviewer, qa-reviewer |
| rust-qualified-impl-call | do_now | no | completed | code-reviewer, qa-reviewer |

*Machine review state — 3 findings; current: do_now 3, maybe_later 0, dont_do_later 0, not_issue 0*
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

- No implementation dependency on wave 204mp. Activation requires the current open slot to be available. Existing graph integrity behavior from wave 203pu is a preservation baseline.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 30 | 124,076 |
| implement | 141 | 2,395,741 |
| review | 225 | 3,696,051 |
| **Total** | **396** | **6,215,868** |

<!-- wave:context-efficiency-state {"generation":423,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":141,"content_source_credit":2707217,"derived_artifact_credit":0,"direct_net":2395741,"estimated_tokens_saved":2395741,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":5159,"response_debit":309008,"source_credit_count":52,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2691},"plan":{"calls":30,"content_source_credit":172523,"derived_artifact_credit":1303,"direct_net":124076,"estimated_tokens_saved":124076,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":5376,"response_debit":50877,"source_credit_count":23,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6503},"review":{"calls":225,"content_source_credit":3779612,"derived_artifact_credit":2729,"direct_net":3696051,"estimated_tokens_saved":3696051,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":34016,"response_debit":525019,"source_credit_count":146,"source_credit_drop_count":0,"structural_source_credit":470361,"workflow_prompt_credit":2384}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":396,"content_source_credit":6659352,"derived_artifact_credit":4032,"direct_net":6215868,"estimated_tokens_saved":6215868,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":44551,"response_debit":884904,"source_credit_count":221,"source_credit_drop_count":0,"structural_source_credit":470361,"workflow_prompt_credit":11578},"wave_id":"206og rust-graph-accuracy"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 59 | 0 | 28 | 37,717,059 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":28,"estimated_exploration_avoided":37717059,"surfaced_events":59} -->
<!-- wave:exploration-avoided end -->
## Review checkpoints

- Readiness allocation: inherited capable model selected for cross-cutting parser, storage and MCP contract analysis; actual runtime model/effort identity is not exposed. Fresh independent reviewer contexts will inspect the current plan and source. Standard primer depth covers target identity, provenance and cache generation boundaries. No implementation, activation, commit or push is authorized.
- Existing setup advisory (`setup_inputs_changed`) is recorded separately from source verification. Direct source reads and fresh local grammar probes are used; no index rebuild or live Tensorwell access is claimed.

### Readiness review, 2026-10-08

- Receipt: `review-policy-06959ca337f048ecbc04`. Reviewed plan hash: `6b00b7b65e981e1d42986f1a355362d038d70bbe`. Actual council seats: red-team and architecture-reviewer; required lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, performance-reviewer. Independent contexts returned readiness approval; no blocking findings were raised or waived.
- Primer strongest challenge: aggregate receiver evidence must not give an unknown occurrence another witness's target or precise span. Existing merge-helper execution in both arrival orders retained only the known witness; the design explicitly requires occurrence resolution before union. Red-team closing reconciliation held the empty finding set.
- Architecture/docs review executed the actual schema function in an isolated in-memory database: two exact occurrence objects round-tripped through existing JSON attributes; deliberately omitted provenance failed its assertion. This proves representability, not correct producer behavior.
- Code/QA review ran the canonical scratch graph producer on a generic two-trait-impl and `Self::ALL` fixture. Independent expected IDs and incoming-relationship assertions detected both current defects. The public callgraph provenance defect was checked separately by fresh council synthesis executing the unchanged line-selection helper, which selected 297 over the intended 384. These are readiness-safe old-behavior controls, not passing repair tests.
- Performance review accepted the bounded per-file lexical-fact design and matched-corpus measurement plan. Its initial helper timings were advisory only; approval used a subsequent canonical scratch-producer control with explicit assertions: 50/100/200 source calls each yielded one resolved edge and zero proven occurrences, and all required-count assertions detected the current bad behavior. Current 50/100/200-call probe timings were 0.001308/0.002633/0.005073 seconds, with five edges and 1,638 serialized bytes each: collapsed counts do not establish occurrence preservation. This is a small baseline, not performance qualification.
- `seat_agreement_aggregate`: seat_agreement `unanimous`; max_severity `none`. Evidence was weighed without seat authority before identity was reattached; distinct checks were not counted as repeated proof of one claim. Strongest alternative: retain individual occurrence facts through resolution, then project existing edge attributes; a dedicated occurrence table adds migration complexity without a requested indexed-occurrence query.
- Implementation notes: verify extraction, fragment union and confidence re-key merges; mixed known/unknown witnesses; UTF-8 and original macro offsets; previous-builder failure paths and coherent pins. Test identity, exact span and genuine relationship retention separately.
- Falsification check: the strongest objection is misattribution surviving additive metadata. The explicit per-occurrence-before-union requirement and independent delivery oracles address it at readiness; future product correctness is unproven. No Tensorwell query, full suite, cache-transition integration test or implementation benchmark was claimed.
- Model fit: fresh inherited capable contexts were selected for adversarial analysis, cross-layer architecture/contracts, parser/QA/performance assessment and independent council synthesis. Runtime model/effort identity is unknown. Scope stayed read-only source/probes plus wave planning records.

### Implementation and delivery review — in progress

- Source frozen for delivery review; reviewed path hashes are in `evidence/delivery-tree.json`.
- Focused implementation verification passed: 46 integrity, 9 provenance, 549 indexer and 102 quality-evaluation tests (seven existing quality skips). Six guard mutants and two independent provenance mutants were detected. These checks establish the stated fixtures, not live Tensorwell qualification.
- Canonical full framework suite is running; final receipt and independent delivery approvals remain pending. No operator signoff, closure, commit or push is recorded.

- Final qualification: 11,915 tests across 175 owners pass in 417.943 seconds, 29 existing skips; the current framework receipt is proven. All three repair findings have independent terminal verification; code, QA, architecture, docs-contract and performance delivery approvals are current. Final document-state receipt refresh is in progress; no implementation or acceptance-criterion delta. Operator closure, commit and push remain unperformed.
