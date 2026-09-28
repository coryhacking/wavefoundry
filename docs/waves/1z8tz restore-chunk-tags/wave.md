# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-28
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1z8tz restore-chunk-tags`
Title: Restore Chunk Tags

## Objective

The `tags` filter on `docs_search` and `code_search` works again: the indexer writes tags from the repository's layout, without re-embedding. Layout defaults are read at call time, not captured at import.

## Changes

Change ID: `1z8ty-debt resolve-layout-defaults-at-call-time`
Change Status: `complete`

Change ID: `1z8tt-enh archive-memory-backfill`
Change Status: `complete`

## Participants

- Coordinator: <wave coordinator>
- Write-owning roles: <roles selected during Prepare wave>
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer

Completed At: 2026-09-28

## Wave Summary

Wave `1z8tz` (Restore Chunk Tags) delivered two changes: Restore Chunk Tags and Resolve Layout Defaults at Call Time and Memory Backfill From the Read-Only Archive. Notable adjustments during implementation: Restore Chunk Tags and Resolve Layout Defaults at Call Time: Implemented (implementer agent, coordinator doc edits). `_tag_utils.infer_tags(path, *, waves_prefix=None, archive_prefix=None)` with a call-time `default_waves_prefix()`; `indexer._tag_prefixes` resolves once per build and `_chunks_for_file` tags every chunk on the full, incremental and server live paths; `_chunk_hash` hashes a constant `tags: []`; `_skip_exempt` covers stale paths on rechunk; `CHUNKER_VERSION` 43 (the `performance-budget.md` pin updated with it); `is_excluded` requires `excluded_dirs`; `retrieval_eval` defaults at call time; chunker alias removed; tool descriptions list `memory` and name the rechunk remedy; seed 211 and `guru.md` gain `memory` (`guru.md` also had drifted: its `journal` row pointed at the memory directory and its example used `journal` for memory records, both corrected). New `tests/test_chunk_tags.py` (15 tests). `test_fts_lexical_layer.test_metadata_only_difference_changes_the_map` pinned the old tags-in-hash contract and now tests a `section`-only change, with a new test pinning the tags-only contract. Mutants (hash with real tags, no rechunk exemption, no live-path tags, import-time default) each fail. Census exception: `review_policy.SCAFFOLD_DOCS` is still built from `record_paths.PLANS_ROOT` at import because the upgrade reads it across versions (`upgrade_extensions`) and `test_upgrade_wavefoundry` pins it; the census test lists it as the one known exception. Found in passing: `_live_docs_chunks` reads only `docs/` and `.wavefoundry/framework/`, so a waves root relocated outside `docs/` never reaches the live fallback (pre-existing, unchanged). Gapfill: none for retrieval (MCP code tools used); edits by Edit tool; Restore Chunk Tags and Resolve Layout Defaults at Call Time: Readiness review. B1 (blocking) adopted: excluding tags from the hash would let the registry fast path skip every file on a rechunk, writing no tags while AC-3 passed; the hash keeps a constant `tags` field, rechunk paths are exempt from the registry skip, and AC-3 asserts both zero encoder calls and stored tags. N1: the third chunk-production caller (`_live_docs_chunks`) added. N2: layout-change remedy documented. N3: `archive_prefix` named. N4: `memory` added to the advertised vocabulary. N5: the `retrieval_eval` apparatus is kept with a call-time default instead of removed. N6: test and census pins named; Restore Chunk Tags and Resolve Layout Defaults at Call Time: Rescoped at the operator's direction ("Restore"). While tracing `_tag_utils` callers, found that no production path calls tag inference and the stored `tags` column is empty; traced the regression to `28ca7657`. Also found the unused `is_excluded` default and the test-only `retrieval_eval` helpers.

**Changes delivered:**

- **Restore Chunk Tags and Resolve Layout Defaults at Call Time** (`1z8ty-debt resolve-layout-defaults-at-call-time`) — 6 ACs completed. Key decisions: Keep stored tags and fix the rechunk path, rather than compute tags at query time; Constant `"tags": []` in `_chunk_hash` plus a registry-skip exemption on rechunk
- **Memory Backfill From the Read-Only Archive** (`1z8tt-enh archive-memory-backfill`) — 6 ACs completed. Key decisions: Keep the folder-name key; shadow by id token with live precedence and a diagnostic; Opt-in `include_archive` on `resolve_wave_dir`
## Watchpoints

- <Add watchpoint, follow-up, or blocking notes here — coordination constraints, sequencing, or guard requirements.>

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| archive-backfill-docs-drift | do_now | no | completed | — |
| chunk-tag-test-coverage-gaps | do_now | no | completed | — |
| tag-prefix-matching-edges | do_now | no | completed | — |

*Machine review state — 3 findings; current: do_now 3, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| architecture-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
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
| plan | 26 | 70,614 |
| implement | 11 | 437,439 |
| review | 70 | 1,075,179 |
| **Total** | **107** | **1,583,232** |

<!-- wave:context-efficiency-state {"generation":105,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":11,"content_source_credit":442691,"derived_artifact_credit":0,"direct_net":437439,"estimated_tokens_saved":437439,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":170,"response_debit":5348,"source_credit_count":5,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":266},"plan":{"calls":26,"content_source_credit":94843,"derived_artifact_credit":2609,"direct_net":70614,"estimated_tokens_saved":70614,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2552,"response_debit":30797,"source_credit_count":14,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6511},"review":{"calls":70,"content_source_credit":1176785,"derived_artifact_credit":2555,"direct_net":1075179,"estimated_tokens_saved":1075179,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":9283,"response_debit":97194,"source_credit_count":61,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2316}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":107,"content_source_credit":1714319,"derived_artifact_credit":5164,"direct_net":1583232,"estimated_tokens_saved":1583232,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":12005,"response_debit":133339,"source_credit_count":80,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":9093},"wave_id":"1z8tz restore-chunk-tags"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
