# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-28
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1z8tx gardener-test-isolation`
Title: Gardener Test Isolation

## Objective

The gardener's relocated-layout tests pass regardless of which test ran before them in the same interpreter.

## Changes

Change ID: `1z8tw-bug gardener-layout-tests-patch-a-stale-module`
Change Status: `complete`

## Participants

- Coordinator: <wave coordinator>
- Write-owning roles: <roles selected during Prepare wave>
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer

Completed At: 2026-09-28

## Wave Summary

Wave `1z8tx` (Gardener Test Isolation) delivered one change: Layout Tests Depend on Test Order. Notable adjustments during implementation: Layout Tests Depend on Test Order: Reverification: finding resolved; all orderings pass including nested; 36-file census shows no fixed-module failure. Adopted the red-team alternative: the test also asserts the no-root tag directly from the server copy's captured `_DEFAULT_WAVES_PREFIX` (a path under it is a wave, `elsewhere/waves/` is not), so the final check is no longer a same-function comparison only. New mutant MD (no-root path hard-codes `docs/waves/`) fails it alone, after archive and after nested. Remaining structural hazard (two `_tag_utils` copies capture layout at import; `test_record_layout_nested` leaves them captured) is out of scope here; Layout Tests Depend on Test Order: Delivery review finding `cold-site-preload-breaks-nested-ordering` (blocking): the preload and guard broke `test_record_layout_nested` then `test_record_layout_cold_sites` (OK at HEAD, 4 `setUp` failures after), and the comment's premise that `load_server()` empties `_script_cache` was false. Repaired: preload and guard removed; the final assertion compares with the server's own `_tag_utils` copy. All cold-site orderings pass (alone; after archive, declared, nested; archive then nested then cold-site); mutants MT and M7 (no-root path uses a fixed bogus prefix) fail the test.

**Changes delivered:**

- **Layout Tests Depend on Test Order** (`1z8tw-bug gardener-layout-tests-patch-a-stale-module`) — 3 ACs completed. Key decisions: Compare with the server's own `_tag_utils` copy instead of preloading; Patch the gardener's own copy in the two tests
## Watchpoints

- <Add watchpoint, follow-up, or blocking notes here — coordination constraints, sequencing, or guard requirements.>

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| cold-site-preload-breaks-nested-ordering | do_now | no | completed | — |

*Machine review state — 1 findings; current: do_now 1, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
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
| plan | 15 | 290 |
| implement | 27 | 1,453,017 |
| review | 15 | 50,723 |
| **Total** | **57** | **1,504,030** |

<!-- wave:context-efficiency-state {"generation":57,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":27,"content_source_credit":1467092,"derived_artifact_credit":0,"direct_net":1453017,"estimated_tokens_saved":1453017,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":836,"response_debit":13801,"source_credit_count":45,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":562},"plan":{"calls":15,"content_source_credit":9573,"derived_artifact_credit":2079,"direct_net":290,"estimated_tokens_saved":290,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1723,"response_debit":16150,"source_credit_count":9,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6511},"review":{"calls":15,"content_source_credit":74210,"derived_artifact_credit":1479,"direct_net":50723,"estimated_tokens_saved":50723,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4451,"response_debit":22831,"source_credit_count":22,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2316}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":57,"content_source_credit":1550875,"derived_artifact_credit":3558,"direct_net":1504030,"estimated_tokens_saved":1504030,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":7010,"response_debit":52782,"source_credit_count":76,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":9389},"wave_id":"1z8tx gardener-test-isolation"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
