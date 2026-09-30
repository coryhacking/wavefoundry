# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-30
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1zf1w coreml-cache-key`
Title: Coreml Cache Key

## Objective

Key the CoreML compiled-model cache by ONNX Runtime version and model content so a runtime upgrade can never load a stale compile, and remove superseded compiles. Restores reranker acceleration found broken on a 1.28.0+pti1 field upgrade.

## Changes

Change ID: `1zf1v-bug coreml-cache-stale-compile`
Change Status: `complete`

## Participants

- Coordinator: Engineering
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer

Completed At: 2026-09-30

## Wave Summary

Wave `1zf1w` (Coreml Cache Key) delivered one change: Stale CoreML Compiled-Model Cache Silently Disables Reranker Acceleration. Notable adjustments during implementation: Stale CoreML Compiled-Model Cache Silently Disables Reranker Acceleration: Delivery review (independent, Opus): code-reviewer, qa-reviewer, red-team and security-reviewer APPROVE, no build-changing defect. Adversarial pruning checks held (escaping names, symlinked cache root, symlink, file, dangling and junction entries, a symlink swapped in between scandir and rmtree with `rmtree.avoids_symlink_attacks` true). 20 mutants: 15 killed, 4 equivalent by design, 1 real test gap. Taken: `test_only_the_creating_mkdir_prunes` (the exists-then-makedirs mutant now fails); Transition wording for the orphaned old-build entry and mixed ONNX Runtime versions; a note on the real-cache test that it must run under the tool venv; CHANGELOG mentions the provider options. Kept as is: the real-cache test (isolation cannot reach the probe child and would cost a cold compile per run). Follow-up, out of scope: the unreferenced `Snowflake__snowflake-arctic-embed-xs` CoreML cache (190 MB) is on no retired-model allowlist.

**Changes delivered:**

- **Stale CoreML Compiled-Model Cache Silently Disables Reranker Acceleration** (`1zf1v-bug coreml-cache-stale-compile`) — 5 ACs completed. Key decisions: Key by ONNX Runtime version plus a content digest of the static ONNX file; Prune siblings only when a new key is created
## Watchpoints

- Watchpoint: do not delete the stale reranker cache by hand; it is the real-hardware oracle for AC-4.
- Watchpoint: pruning must never follow a symlink or leave the model's `MLProgram_ALL` directory.
- Follow-up: rebuilding the static ONNX file when its builder changes is out of scope.

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
| wave-council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| wave-council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-09-30: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, security-reviewer; rotating-seat: security-reviewer; strongest-challenge: pruning deletes directories and `_safe` only replaces `/`, so a `..` model name or a symlinked cache directory could steer deletion outside the model's cache; resolved by a containment guard that refuses to prune; strongest-alternative: add the macOS version to the key, rejected because partitioning is ONNX Runtime's and it would recompile on every point release)
- Prepare council seat evidence (2026-09-30): red-team approved (key covers runtime repartitioning and rebuilt graphs; no code path uses another static graph for the same model); security-reviewer approved with the containment, symlink and mkdir-detection conditions now in Requirement 2.

- **Delivery-phase Wave Council [delivery-council] — 2026-09-30: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, security-reviewer; rotating-seat: security-reviewer; strongest-challenge: steering the prune outside the model's cache through a crafted name, a symlinked root or entry, or a symlink swapped in mid-removal; every case refused or unlinked without traversal; strongest-alternative: isolate the real-cache reranker test's cache, rejected because the probe child imports the module afresh and a cold compile per run is costly; disagreements: none)
- Delivery council seat evidence (2026-09-30): red-team approved (mixed-version accumulation and thrash documented in the Transition requirement); security-reviewer approved (containment, symlink and race cases measured in scratch against temp caches).

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 12 | 2,721 |
| implement | 9 | 24,419 |
| review | 19 | 16,585 |
| **Total** | **40** | **43,725** |

<!-- wave:context-efficiency-state {"generation":40,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":9,"content_source_credit":37160,"derived_artifact_credit":1428,"direct_net":24419,"estimated_tokens_saved":24419,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1759,"response_debit":12410,"source_credit_count":13,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0},"plan":{"calls":12,"content_source_credit":10366,"derived_artifact_credit":1918,"direct_net":2721,"estimated_tokens_saved":2721,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1113,"response_debit":14961,"source_credit_count":8,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6511},"review":{"calls":19,"content_source_credit":52664,"derived_artifact_credit":259,"direct_net":16585,"estimated_tokens_saved":16585,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":766,"response_debit":37888,"source_credit_count":7,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2316}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":40,"content_source_credit":100190,"derived_artifact_credit":3605,"direct_net":43725,"estimated_tokens_saved":43725,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3638,"response_debit":65259,"source_credit_count":28,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":8827},"wave_id":"1zf1w coreml-cache-key"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
