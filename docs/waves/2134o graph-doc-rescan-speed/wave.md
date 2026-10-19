# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-19
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `2134o graph-doc-rescan-speed`
Title: Graph Doc Rescan Speed

## Objective

Operators running a full or large graph build wait seconds instead of about five minutes for the document rescan phase and get an identical graph, and a source-drift retry log no longer blames embedding on a graph-only build. No new dependency and no graph contract change.

## Changes

Change ID: `212o7-enh doc-term-matcher-token-lookup`
Change Status: `implemented`

Change ID: `212o8-bug graph-only-source-drift-message`
Change Status: `implemented`

## Participants

- Coordinator: Engineering
- Write-owning roles: <roles selected during Prepare wave>
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer

Completed At: 2026-10-19

## Wave Summary

Wave `2134o` (Graph Doc Rescan Speed) delivered two changes: Faster document term matching in graph builds and Source drift message names embedding on graph-only builds. Notable adjustments during implementation: Faster document term matching in graph builds: Delivery repair. Security seat (medium) and red-team (note): per-boundary cost scaled with the longest repository term (one 10,000-char term made 1 MB take about 6 minutes). Repaired: each boundary now tries whichever is fewer, the distinct term lengths (checked against a boundary bitmap) or the boundaries in the window, and a long candidate is sliced only when its first 16 folded characters match a term of that length; `_re_fold_char` cache capped at 65,536. Pathological 1 MB with a 10,002-char term: 5.3 s; with 50,000 terms up to 192 chars: 2.9 s. Code-reviewer then found no test term exceeded the 16-char prefix, so an off-by-one prefix mutant survived; added `test_long_terms_sharing_prefixes_match_the_regex`, which kills it. QA note: the linear-growth timing test could flake under load; it now compares 16x text against a 64x limit (quadratic is about 256x). Stale `matcher` annotation corrected.; Faster document term matching in graph builds: QA round 2 blocked: no test guarded the security repair (forcing the old window walk, mutant N2, passed every test). Added `test_one_long_term_does_not_slow_every_position` (same text with and without one 10,002-char term, ratio below 20); N2 fails it at 319x. Code-reviewer and qa-reviewer re-approved the repaired matcher (`2134o-del-code-reviewer-2`, `2134o-del-qa-reviewer-2`); both timing tests passed 10 of 10 runs under heavy CPU load.; Faster document term matching in graph builds: AC-3 measurement (forced `indexer.py --content graph --full --verbose`, no tree edits during the run, single pass, no drift retry): `doc rescans (489 changed docs)` 20:17:09 to `merge entries` 20:17:10, about 1 s, down from 5:10 on 2026-10-19; doc progress lines `250/489 docs` and `489/489 docs` printed. Whole graph extraction span 2:13 (was 7:26); the longest remaining gap is code extraction (1:22 between `250/554` and `500/554 code files`). Graph 73,706 nodes / 218,250 edges against 73,688 / 218,194 before; the difference is code added since (this wave's matcher and tests), not matching (AC-2).

**Changes delivered:**

- **Faster document term matching in graph builds** (`212o7-enh doc-term-matcher-token-lookup`) — 5 ACs completed. Key decisions: Replace the alternation with span lookup plus a fallback for terms a token split cannot reach, keeping exact regex semantics.
- **Source drift message names embedding on graph-only builds** (`212o8-bug graph-only-source-drift-message`) — 3 ACs completed. Key decisions: Use one neutral word, "indexing", for every mode.
## Watchpoints

- Watchpoint: do not edit tracked sources while the AC-3 rebuild runs; a mid-build edit triggers the indexer's one-time drift retry (the cause of the double pass seen in wave 212ym).
- Watchpoint: if `212o7` AC-2 finds any graph difference, bump `GRAPH_BUILDER_VERSION` in this wave.

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
| council-readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 21 | 731,571 |
| implement | 36 | 0 |
| review | 8 | 25,301 |
| **Total** | **65** | **756,872** |

<!-- wave:context-efficiency-state {"generation":57,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":36,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-6647,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1288,"response_debit":6673,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1314},"plan":{"calls":21,"content_source_credit":768612,"derived_artifact_credit":7529,"direct_net":731571,"estimated_tokens_saved":731571,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2448,"response_debit":46550,"source_credit_count":20,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4428},"review":{"calls":8,"content_source_credit":38669,"derived_artifact_credit":1472,"direct_net":25301,"estimated_tokens_saved":25301,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2704,"response_debit":15350,"source_credit_count":12,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3214}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":65,"content_source_credit":807281,"derived_artifact_credit":9001,"direct_net":750225,"estimated_tokens_saved":756872,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":6440,"response_debit":68573,"source_credit_count":32,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":8956},"wave_id":"2134o graph-doc-rescan-speed"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
