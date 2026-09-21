# Wave Record

Owner: Engineering
Status: closed
Completed at: 2026-09-20
Last verified: 2026-09-20
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1y0h2 handler-module-split`
Title: Handler Module Split

## Objective

When this wave closes, the code-navigation and graph-query handler families live in `codenav_handlers.py` and `graph_handlers.py` with invocation-time delegation from the existing decorated closures in `server_impl.py`, are unit-tested without the transport, stay fresh across `wf_reload_mcp`, and the public tool surface is unchanged.

## Changes

Change ID: `1y0bf-ref codenav-graph-handler-modules`
Change Status: `complete`

## Participants

- Coordinator: Engineering
- Write-owning roles: implementer (extraction and integration), qa (handler guard tests)
- Requested review lanes: architecture-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer

Completed At: 2026-09-20

## Wave Summary

Delivered all nineteen code-navigation and graph-query responses and their exclusive helpers in reloadable sibling modules. Public registration, golden tool surface and handler digests remain unchanged. Shared behavioral helpers remain invocation-time lookups; standard-library and typing imports are owned locally.

All ten acceptance criteria and all tasks completed; no deferrals. Independent code, QA and architecture approvals and the refreshed readiness council are current. Full suite: 9,418 tests, 12 skips, green current receipt. Final retrieval baseline: `docs/reports/retrieval-quality-1y0bf-final.json`, stable completed generation1772 and verified production digest. Final evidence and reproducible fingerprints are in `delivery-evidence.md` and `verification-summary.json`.

Review improvements corrected source-owner censuses and patch-census documentation, strengthened containment with a real outside file and killed bypass control, and removed incidental standard-library coupling. Retrospective lessons are recorded below; memory curation yielded no new promotions because durable decisions already reside in canonical architecture documentation. Closed under explicit operator authorization; changes remain uncommitted.

## Watchpoints

- Watchpoint: blocked until `1y0h1` closes; the introspection registry must be available before moving response families.
- Neither module may import `server_impl` at top level; shared helpers stay in the composition root behind the existing lazy indirection.
- Both modules must be added to the reload purge list; a stale handler after an upgrade would be a silent regression.
- Defer pacing decision to the operator; it is maintainer value only and carries the most merge surface for downstream patches.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| READY-B1 | do_now | no | completed | — |
| READY-R1 | do_now | no | completed | — |
| handler-graph-accessor-source-gate | do_now | no | completed | code-reviewer |

*Machine review state — 3 findings; current: do_now 3, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking follows every affected repair | none |
| architecture-reviewer | approved | current executed approval by coryhacking follows every affected repair | none |
| operator-signoff | approved | current executed approval by coryhacking follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- `1y0h1 tool-registry-dispatch` must close before implementation.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| credit_history_unavailable | 0 | 0 |

<!-- wave:context-efficiency-state {"generation":242,"measurement_status":"credit_history_unavailable","pending":false,"schema_version":1,"stages":{"implement":{"calls":26,"content_source_credit":470915,"derived_artifact_credit":0,"direct_net":463928,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1776,"response_debit":7600,"source_credit_count":3,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2389},"plan":{"calls":55,"content_source_credit":290376,"derived_artifact_credit":4281,"direct_net":202911,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":19856,"response_debit":81054,"source_credit_count":49,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":9164},"review":{"calls":176,"content_source_credit":3799122,"derived_artifact_credit":3489,"direct_net":3584223,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":19340,"response_debit":201050,"source_credit_count":104,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2002}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":257,"content_source_credit":4560413,"derived_artifact_credit":7770,"direct_net":4251062,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":40972,"response_debit":289704,"source_credit_count":156,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":13555},"wave_id":"1y0h2 handler-module-split"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 5 | 0 | 4 | 766,621 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":4,"estimated_exploration_avoided":766621,"surfaced_events":5} -->
<!-- wave:exploration-avoided end -->
## Review checkpoints

- 2026-09-20 closure: all authorized follow-up fixes complete; final independent approvals recorded, prepare receipt refreshed, close dry-run and create succeeded. Current final evaluation is generation1772; earlier checkpoint descriptions below are chronological history. Handoff reconciled to idle; no remaining AC/task or design deferrals.

- **Prepare-phase Wave Council [prepare-council] — 2026-09-20: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, security-reviewer; rotating-seat: security-reviewer; strongest-challenge: ineffective or stale verification concealed by narrowed prose; strongest-alternative: extend lifecycle patch census to all handlers, unnecessary given explicit observation rule and executed controls). Bounded readiness refresh for corrected plan text; same scope and lanes. Red-team reproduced AST/runtime/surface and actual-root-escape proof; security verified preserved containment and census scope. Independent moderator executed the real-root negative control and reproduced four manifests plus all14 current file hashes. Security reuses its disclosed independent QA context. No findings; final gardened fingerprint2e67176fef75db44764cab545b54530afe46136b66f41118b5f3f593d751b3d2.

- 2026-09-20 operator-authorized pre-close follow-up: direct stdlib/typing imports replace composition-root aliases, existing outside-root file plus killed resolver-bypass control strengthens containment evidence, Requirement 7 accurately scopes the lifecycle-only patch census, and three durable fingerprint manifests reproduce the historical and final review hashes. Independent code/architecture approve; QA approved the refreshed final receipts. No behavior change or scope deferral.

- 2026-09-20 final delivery: code, QA and architecture approvals current; all ACs/tasks complete, no unresolved findings. Cycle 3 repaired the two stale whole-server source censuses and independent mutation reverification passed. Full suite: 9,418 tests, 12 skips, green current receipt. Standing evaluation: valid new baseline at stable generation 1762; pre-run indexed hashes match both handlers. Full docs lint and diff whitespace check pass. Framework edit gate closed; wave remains open and uncommitted pending operator closure. No specs changed, so docs-contract lane is not applicable. See `delivery-evidence.md` and `verification-summary.json`.

- 2026-09-20 delivery: source frozen at `deb126f99a76186ff1cfa8e9e59c802291c97741a73b4fb65ffd16c1bb80fd9e`. Independent code and architecture lanes approve; QA shares the architecture reviewer context and awaits final full-suite/indexed-evaluator receipts. Both reviewers authored neither implementation nor new tests. All moved definitions and all nineteen actual response calls match the baseline under documented normalization. Focused mutation controls killed missing late binding, ignore filtering, production fingerprint membership and reload eviction. No new actionable finding or scope deferral. See `delivery-evidence.md`.

- **Prepare-phase Wave Council [prepare-council] — 2026-09-17: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, security-reviewer; rotating-seat: security-reviewer; strongest-challenge: whether relocating handler bodies could let a tool's permission tier silently drift; strongest-alternative: none needed, tier travels with the registry-composed ToolSpec, not file location).

## Closure reconciliation

- Delivered nineteen handler responses and exclusive helpers in sibling modules; public registration, golden surface and handler digests preserved. Shared behavior stays invocation-time bound; standard-library and typing names belong to each module.
- All acceptance criteria and tasks completed; no intentionally deferred ACs or tasks. Final full-suite and protected retrieval receipts are complete; QA independently verified their final hashes and approved.
- Docs-contract review: not applicable — no `docs/specs/*.md` changes.
- Retrospective: source-location censuses must enumerate every relocated owner; missing-file fixtures cannot prove root containment. The final fixture includes a real outside file and a bypass counterexample. Durable import-boundary decisions remain in architecture docs and the change decision log; evidence recipes and manifests preserve review reproducibility.
- Memory checkpoint: the prior six proposals were rejected as duplicates or incorrect targets; the closing proposal pass returned zero new candidates. No new canonical policy is needed for these bounded corrections.
- Operator explicitly authorized fixes followed by closure in the current request. No commit is authorized for this wave.
