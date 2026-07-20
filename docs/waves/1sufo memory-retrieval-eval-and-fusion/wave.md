# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-07-20
review-evidence-source: events.jsonl

wave-id: `1sufo memory-retrieval-eval-and-fusion`
Title: Memory Retrieval Eval And Fusion

## Objective

Fix the validated relevance-overrides-policy defect in memory search (`wave_memory_search_response`, where a semantic re-sort wholesale overrides the decay/centrality order) with the minimal correct fix: policy primary, semantic as tie-break. Land a hermetic memory-retrieval eval baseline as a standing guard. The full lexical+semantic RRF fusion is deferred (`1sufn`, back in `docs/plans/`) until a real corpus exists and the eval proves fusion beats a real baseline — both council seats found RRF disproportionate for the current empty/sparse typed corpus.

## Changes

Change ID: `1sufm-enh memory-retrieval-eval-baseline`
Change Status: `implemented`

Change ID: `1svuj-bug memory-search-semantic-override-policy-fix`
Change Status: `implemented`

Completed At: 2026-07-18

## Wave Summary

Wave `1sufo` (Memory Retrieval Eval And Fusion) delivered two changes: Memory-retrieval evaluation baseline and Memory search: semantic rank should tie-break within policy, not override it.

**Changes delivered:**

- **Memory-retrieval evaluation baseline** (`1sufm-enh memory-retrieval-eval-baseline`) — 6 ACs completed. Key decisions: Eval baseline before any fusion change; Memory-specific harness, hermetic fixtures
- **Memory search: semantic rank should tie-break within policy, not override it** (`1svuj-bug memory-search-semantic-override-policy-fix`) — 4 ACs completed. Key decisions: Semantic-as-tie-break, not full RRF fusion; Leave the pre-filter as-is
## Journal Watchpoints

- `server_impl.py` edited under `framework_edit_allowed`; open before editing, close immediately after.
- Watchpoint: `1svuj` is a ~2-line ordering fix (policy order primary, semantic rank a secondary tie-break) — anchor by symbol `wave_memory_search_response`, NOT line, because a concurrent session is editing `server_impl.py` and the re-sort has drifted. Prove a high-trust record is not demoted by text relevance, and that the no-index path is byte-identical.
- Watchpoint: `1sufm` is measurement-only and corpus-independent (hermetic fixtures) — it must not perturb ranking.
- Deferred: full lexical+semantic RRF fusion `1sufn` was split out to `docs/plans/`; revisit only once a real corpus exists and the eval proves fusion beats a real (not synthetic) baseline.
- Related but separate: the code/docs golden-query eval is wave `1seaw`/`1sear`; this is the memory-specific analog.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

<details class="wavefoundry-review-evidence">
<summary>Machine review evidence — 5 records; 2 runs; 0 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 0</summary>
</details>
<!-- wave:finding-synthesis end -->

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-07-17: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, code-reviewer; rotating-seat: code-reviewer; strongest-challenge: re-prepared after a council descope — the original scope's full RRF fusion (`1sufn`) was disproportionate for an empty/sparse typed corpus and its adoption gate only proves anything on synthetic fixtures — resolved by splitting `1sufn` out to `docs/plans/` (deferred) and keeping the minimal ~2-line policy-override fix (`1svuj`) plus the corpus-independent eval (`1sufm`); strongest-alternative: keep full RRF now — rejected by both the red-team and reality-checker seats.)
- prepare-council seat — red-team: the descope removes the over-built machinery; remaining scope is `1sufm` (measurement-only, corpus-independent) + `1svuj` (minimal fix). Verified the defect at `wave_memory_search_response` — `_memory_ranked(...)` then a wholesale `ranked.sort(… semantic_hit_order …)` (~server_impl.py:8008-8010) overriding the policy order; the fix (policy primary, semantic tie-break) is minimal, leaves the pre-filter and the no-index text-containment path untouched, and correctly does not touch `brief` (context-driven, no free-text re-sort). No blocking concerns.
- prepare-council seat — code-reviewer: `1sufm` reuses `wave_memory_search_response` (:7951) / `wave_memory_brief_response` (:8032) / `_memory_ranked` (:7653) / `load_memory_records` / `match_targets` as the measured surface, with hermetic fixtures (corpus-independent, no dependency on the empty live corpus). `1svuj` touches only the search re-sort, anchored by symbol (line drift under concurrent `server_impl.py` edits). No new index or primitive required. The clarified defect framing (a non-matching high-trust record is filtered OUT by the pre-filter, not demoted) is captured in `1svuj`'s scope.

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- wave-council-readiness: approved 2026-07-17 — eval-before-fusion sequencing is explicit and blocking; the fusion change is gated on beating a measured baseline and ships default-off otherwise; relevance/policy separation is the load-bearing design and is guarded by AC-3 (trust records not demoted). The defect being fixed is verified in the tree (`wave_memory_search_response`, semantic re-sort over `_memory_ranked`). No blocking concerns.
- operator-signoff: pending operator closure confirmation

## Dependencies

- No external wave dependencies.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| close | 2 | 503 |
| implement | 2 | 680 |
| **Total** | **4** | **1,183** |

<!-- wave:context-efficiency-state {"generation":4,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"close":{"calls":2,"content_source_credit":0,"direct_net":503,"estimated_tokens_saved":503,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":18,"response_debit":476,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":997},"implement":{"calls":2,"content_source_credit":0,"direct_net":680,"estimated_tokens_saved":680,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":18,"response_debit":727,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1425}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":4,"content_source_credit":0,"direct_net":1183,"estimated_tokens_saved":1183,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":36,"response_debit":1203,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2422},"wave_id":"1sufo memory-retrieval-eval-and-fusion"} -->
<!-- wave:context-efficiency end -->
