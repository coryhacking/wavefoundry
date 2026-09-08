# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-08
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1xa00 table-chunk-source-coverage`
Title: Table Chunk Source Coverage

## Objective

Ensure oversized Markdown table chunks carry source payload instead of emitting generated header-only windows with misleading citations. Fix the reproduced wide-table failure, keep complete rows with their headers even above the normal cap, and preserve the existing unmapped wrapping behavior.

## Changes

Change ID: `1x81x-bug oversized-table-row-wrap-emits-header-only-chunk`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer, performance-reviewer, release-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, release-reviewer, performance-reviewer

Completed At: 2026-09-06

## Wave Summary

Wave `1xa00` (Table Chunk Source Coverage) delivered one change: An Over-Cap Table Row Part Line-Wraps Into a Header-Only Chunk With No Source Line. Notable adjustments during implementation: An Over-Cap Table Row Part Line-Wraps Into a Header-Only Chunk With No Source Line: `test_wide_padded_table_has_no_generated_only_chunks`.

**Changes delivered:**

- **An Over-Cap Table Row Part Line-Wraps Into a Header-Only Chunk With No Source Line** (`1x81x-bug oversized-table-row-wrap-emits-header-only-chunk`) — 4 ACs completed. Key decisions: Park as its own plan rather than repair inside wave `1x6ti`.
## Watchpoints

- Watchpoint: one implementer owns chunker.py and test_chunker.py; no source edits before readiness.
- The version bump re-chunks every eligible file on the next index update; unchanged chunk text reuses embeddings by hash when the model and walker are unchanged. No live index rebuild is needed to prove the fixture.
- Preserve source-bearing text and unmapped wrapping; no generated-only windows, mislabeled part counts, or duplicate IDs.
- Keep reports in agent returns and typed evidence; no per-seat Markdown files.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-09-06: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, architecture-reviewer; rotating-seat: architecture-reviewer; strongest-challenge: upstream H2 line windows could sever long-table rows from an irreducible header before the universal table splitter; strongest-alternative: segment every Markdown section into ordered prose/table units before section chunking. The narrower table-presence gate preserves table-bearing titled sections for the existing universal splitter, keeps table-free output byte-identical, emits an irreducible header once with all rows, and passes H1/H2/H3, mixed-table, scaling, coordinate and known-bad controls; `RED-PREP-IRREDUCIBLE-H2-1` is terminal after four independent lane reverifications.)

- **Delivery Wave Council [delivery-council] — 2026-09-06: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, architecture-reviewer; rotating-seat: architecture-reviewer; strongest-challenge: an irreducible header could amplify output per row, and upstream H2 windows could then strand later rows without that header; strongest-alternative: parse every section into a flat ordered prose/table segment list before any other decomposition; disagreements: none. The final targeted replay keeps all rows intact across H1/H2/H3 and mixed tables, emits irreducible headers once, preserves source order and deterministic IDs, leaves table-free window output byte-identical, caps ordinary prose, and measures linear scaling through 2,000,145 characters.)

- Final complete-row readiness: full council pass; unanimous, max severity none; actual seats code/QA/architecture/performance/security/reality/release, rotating release. Typed council and all five required lane approvals recorded; Prepare succeeded and implementation opened. Strongest rejected alternative drops copied headers and violates the operator contract.

- 2026-09-06 operator clarification: every table chunk retains at least one complete data row with headers, exceeding the normal cap if needed. Prior readiness reviewed residual row splitting and is superseded; refresh affected approvals before source edits. Dispatcher integration is now explicit.

- Operator accepted 1x81x for prepare/readiness review and implementation. Closure and commit remain operator-owned.
- Builder: generic implementer for the two-helper repair. Council primer tier: full for a retrieval data-path shape/version change; fixed architecture/security/QA/reality seats, rotating release seat for the re-index migration, plus code and performance lanes. Reviewers validate feasibility, not future implementation behavior.

## Prepare Review Evidence

- Complete-row delta (2026-09-06): code, QA, architecture, performance and security independently reproduced the oversized-row/header failure and approved feasibility. Fresh architecture supplied the exact integrity fields; current typed approvals supersede the earlier row-splitting plan. QA `READY-ROW-TEST-1` is terminal after explicit replacement of the real-world hard-cap/70%-header assertions was independently verified.
- `reality-checker` delta — reproduced complete-row loss and the small-table/huge-prelude route. Its authority hold was based on the earlier pending QA state, since cleared in typed evidence. Its substantive recommendation is retained: the atomic-row regression's third fixture requires a small table behind an oversized prelude to retain header, separator and complete row. No new implementation finding; source remains unchanged at readiness.

- `security-reviewer` — no findings; independently reproduced the public two-empty-chunk baseline and direct mapped-window defect. Trusted local content; no new authority boundary. Current-tree feasibility only.
- `qa-reviewer` and `reality-checker` — independently reproduced the defect and requested explicit tests immune to header-compaction masking. `READY-TEST-1` consolidates this with the code lane's duplicate observation. Named AC-4 tests now require filter-only and compaction-only mutations, all-generated boundaries, source character preservation, numbering, IDs and compatibility. Fresh QA recheck executed all six proposed methods in memory: five fail before the repair, the unmapped control passes; typed lane clearance recorded.
- `code-reviewer` — fresh recheck approves the clarified plan after independently reproducing two empty public chunks and generated-only helper windows. No remaining findings; implementation behavior remains unverified.
- `performance-reviewer` — no findings; public baseline and mapped controls reproduced. Planned scans remain local to each chunk. Preservation applies to source-bearing text; generated copied headers intentionally compact under this plan.
- `release-reviewer` — no findings; baseline and two existing controls executed. Strongest alternative: drop copied headers, which loses column context and does not displace compact-plus-filter. Version 42 requires re-chunking with content-hash embedding reuse for unchanged text.
- Final clarified plan blob: `4a2652839897187e674780082bc26db51c8efa3b`. Review transport: native collaboration contexts for primer/initial architecture; fresh read-only ephemeral Codex contexts for remaining seats after the host thread limit. Reports remain in typed evidence and this existing record.

- `red-team` — full adversarial primer completed independently. Public wide-table baseline: 4 exact, 1 superset, 2 empty; all-generated mapped helper input also exposes the early-return hole. Strongest challenge: header compaction can conceal a missing generated-window filter. Separate filter, compaction and payload-preservation proofs are required at delivery.
- `architecture-reviewer` — independent readiness review reproduced the wide-table baseline, an ordinary-table control, and a noncompactable generated-preamble control. `READY-MIGRATION-1` requires accurate migration disclosure: re-chunk eligible files, reuse content-identical embeddings when model/walker are unchanged. Same-phase independent verification resolved the finding; typed architecture readiness approval is recorded. No remaining architecture findings in the reviewed scope.
- Packet: the admitted change plus four named review targets. SHA-1 Git blob fingerprints at this review: chunker.py `d07e4727330b2e2e314f4597de5d435873888d56`; test_chunker.py `f5344fabf282809871354f159d73a970e7fea568`; chunking-and-indexing-pipeline.md `64c7faa5b0d07a28d6a91893310b840311c7bdeb`; CHANGELOG.md `dc32134d03391dee993fd6f853bd3f22cecaf39d`; repaired change doc `f02a3f036ffb96e70597ccc6e3d25eeb26809a0e`.
- Evidence scope: current-tree readiness and finite local fixtures only; future filter/compaction behavior and the full repository census remain delivery work. The canonical council declaration is full; a derived standard-depth receipt does not describe seats actually run.

## Progress Log

Observe (2026-09-06): change 1x81x implemented. Complete table rows retain headers even above the normal cap; generated-only mapped wrapping is filtered before numbering. Delivery repair cycle 4 keeps ordinary prelude/postlude under the universal cap when a small table is present; readiness repair cycle 5 applies atomic-row handling to every later table in the same section. Eight original mutation controls plus the two-sided and three-table public regressions pass. Final framework run: 8,521 tests / 75 files / 200.697 seconds / three skips, green receipt. Full docs validation and diff checks pass. Existing records hold the evidence; no per-seat Markdown reports were added. Delivery review is pending; the wave remains open and uncommitted.

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-05 | Thought: reproduce via chunk_file, pin generated-only and copied-header boundaries, then ready before code. | MCP outlines and targeted reads of both helpers, dispatcher and coordinate oracle. |
| 2026-09-05 | Observe: a 780-character padded header with three 1,600-character rows emits two header-only chunks. | Public chunk_file fixture: 4 exact, 1 superset, 2 empty. Generated-only chunks cite ranges extending beyond the nine-line source. |

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| CODE-1X81X-002 | do_now | no | completed | code-reviewer, qa-reviewer, architecture-reviewer, performance-reviewer |
| CODE-TREE-MOVED-1 | do_now | no | completed | code-reviewer |
| PERF-1X81X-003 | do_now | no | completed | code-reviewer, qa-reviewer, architecture-reviewer, performance-reviewer |
| QA-1X81X-001 | do_now | no | completed | qa-reviewer, architecture-reviewer, release-reviewer |
| READY-MIGRATION-1 | do_now | no | completed | wave-council-readiness, architecture-reviewer |
| READY-ROW-TEST-1 | do_now | no | completed | qa-reviewer, wave-council-readiness |
| READY-TEST-1 | do_now | no | completed | qa-reviewer, wave-council-readiness |
| RED-PREP-IRREDUCIBLE-H2-1 | do_now | no | completed | code-reviewer, qa-reviewer, architecture-reviewer, performance-reviewer |
| RED-PREP-MULTI-TABLE-1 | do_now | no | completed | code-reviewer, architecture-reviewer, qa-reviewer, performance-reviewer |

*Machine review state — 9 findings; current: do_now 9, maybe_later 0, dont_do_later 0, not_issue 0*
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
| release-reviewer | approved | current executed approval follows every affected repair | none |
| performance-reviewer | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 358 | 1,686,309 |
| implement | 32 | 292,154 |
| review | 416 | 9,360,797 |
| **Total** | **806** | **11,339,260** |

<!-- wave:context-efficiency-state {"generation":492,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":32,"content_source_credit":334744,"derived_artifact_credit":0,"direct_net":292154,"estimated_tokens_saved":292154,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1548,"response_debit":43207,"source_credit_count":6,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2165},"plan":{"calls":358,"content_source_credit":3187636,"derived_artifact_credit":3351,"direct_net":1686309,"estimated_tokens_saved":1686309,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":28039,"response_debit":1486715,"source_credit_count":211,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":10076},"review":{"calls":416,"content_source_credit":10409755,"derived_artifact_credit":4996,"direct_net":9360797,"estimated_tokens_saved":9360797,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":69927,"response_debit":1405946,"source_credit_count":360,"source_credit_drop_count":0,"structural_source_credit":417600,"workflow_prompt_credit":4319}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":806,"content_source_credit":13932135,"derived_artifact_credit":8347,"direct_net":11339260,"estimated_tokens_saved":11339260,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":99514,"response_debit":2935868,"source_credit_count":577,"source_credit_drop_count":0,"structural_source_credit":417600,"workflow_prompt_credit":16560},"wave_id":"1xa00 table-chunk-source-coverage"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 5 | 0 | 5 | 4,261,782 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":5,"estimated_exploration_avoided":4261782,"surfaced_events":5} -->
<!-- wave:exploration-avoided end -->
