# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-08-29
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1wl7u retrieval-loose-ends`
Title: Retrieval Loose Ends

## Objective

Close the three retrieval loose ends the 1wik9 arc recorded and deliberately
deferred: route notebook code cells into the docs table as `doc-code` (ending
the last recorded both-tables content drop), give duplicate-titled prose
sections collision-free repeat ordinals (ending silent index-row loss, live in
this corpus today), and close the `.drawio` walk-membership question with a
census-grounded recorded decision. All three are small now because 1whup built
the doc-code plumbing this wave reuses.

## Changes

Change ID: `1wh1b-enh retrieval-loose-ends-notebook-prose-ids-drawio`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator (session agent)
- Write-owning roles: implementer (chunker/indexer/tests), performance-reviewer
  (censuses, golden queries, measurement), qa-reviewer (regressions,
  differentials), docs-contract-reviewer (carriers, seed parity)
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer

Completed At: 2026-08-29

## Wave Summary

Wave `1wl7u` (Retrieval Loose Ends) delivered one change: Retrieval Loose Ends: Notebook Cells, Prose Section Ids, drawio Decision. Notable adjustments during implementation: Retrieval Loose Ends: Notebook Cells, Prose Section Ids, drawio Decision: Differentials regenerated as a versioned step (`evidence/regen_differentials_1wh1b.py/.json`): the three pre-existing markdown sources verified BYTE-IDENTICAL old-vs-new (single-title stability); a duplicate-titled source and a notebook source ADDED (the council-proven blindness repair); every changed row classified — 1 repeat-title-ordinal-id, 2 notebook-cell-kind, 0 unclassified; revert-simulation discriminates (the re-armed snapshot mismatches the pre-change chunker); specs-negatives asserted zero-delta. Coverage differential (`evidence/coverage_differential_1wh1b.py/.json`, Requirement 6): per-line coverage computed over id-collapse SURVIVING rows (the `_plan_lance_delta_rows`/registry last-writer-wins model) across the committed notebook fixture and dup-titled md/rst/adoc fixtures — zero lines lost vs the pre-change chunker, all 23 notebook code-cell lines docs-eligible, dup-titled prose survives the collapse; revert-simulation FAILS against the old chunker (23 code-cell lines invisible, rst/adoc rows lost to collapse), proving non-vacuity.; Retrieval Loose Ends: Notebook Cells, Prose Section Ids, drawio Decision: Post-change measurement (`evidence/eval_prose_after_1wh1b.json`) against the frozen baseline: ipynb 0.2 to 1.0 recall at 5 (bar 0.75 — all five queries hit; the four previously-invisible code-cell queries rank 1-3), fence-md/rst/adoc hold at 1.0, md 0.688 to 0.750 (improved), adoc holds 0.750. One movement recorded and dispositioned: rst 0.750 to 0.688 — p10:rst ("automatically retry write requests") slipped rank 4 to 6 with ZERO notebook rows in its top 5; the slots went to byte-identical cross-format twins of the same content (md/adoc `#retry-semantics-and-backoff` at ranks 4-5, the answer content present twice in the top 5), rst chunking is differential-proven byte-identical, and rst MRR improved 0.532 to 0.560 (p09 rank 2 to 1); for symmetric disclosure, adoc MRR moved 0.408 to 0.336 over the same pair while adoc recall holds at 0.750 (the bar metric) — near-tie reordering among same-content cross-format twins under embedding batch-boundary changes from the corpus growing 174 to 178 rows, not crowding by notebook content. Carriers updated: seed-211 + guru.md Index Scope (byte-identical mirror edit behind `seed_edit_allowed`, parity re-verified at 5,764 bytes), search-architecture doc-code bullet (supersession + walk-excluded drawio), pipeline doc (kind-table row, notebook chunking entry, ordinal note, drawio walk section, stale `"34"` pins and walker pins refreshed to 38/14), performance-budget lint-bound pin 37 to 38, testing-architecture (superseded phrase + new 1wl7u tier row), build-and-verification and mcp-tool-surface doc-code enumerations.; Retrieval Loose Ends: Notebook Cells, Prose Section Ids, drawio Decision: Delivery review executed (three isolated lanes per the receipt; no delivery council required). Docs-contract: 0 blocking, 3 advisory, all repaired (session-handoff rewritten to the open-wave truth; the Risks-table reinclude-hatch claim aligned with the corrected Decision Log; symmetric MRR disclosure added). QA: 0 blocking, 3 advisory, all repaired (regen evidence JSON re-captured parseable from a bare run; the coverage differential's md leg strengthened to exclude the doc-summary sliver — the revert simulation now shows md collapse loss too; chunk_jupyter gained isinstance shape guards so valid-JSON non-notebook payloads fall back to the line window instead of raising, with `test_wrong_shape_json_falls_back`); QA also mutation-proved the four load-bearing regressions with byte-verified restores. Code: 1 blocking — CODE-DEL-1: the DEFAULT tree-sitter HTML path (`_ts_markup_chunker`, ids `{slug}-L{start}`) collided for SAME-LINE sibling elements (compact/minified HTML), falsifying this log's earlier census generalization "the tree-sitter HTML path is line-anchored (no collision)" — that claim is SUPERSEDED: it held only for the census's one-element-per-line fixture. Repaired by threading `_dedupe_id_base` over the `{slug}-L{start}` base (executed: `#section-L1` / `#section-L1~2`; multi-line control unchanged), pinned by `test_treesitter_html_same_line_siblings_dedupe`, the census script extended with a same-line probe and the post-change census re-captured (zero collisions), the CHUNKER 38 rationale and pipeline-doc ordinal note extended to name the site. Suite 523 chunker tests green post-repair.

**Changes delivered:**

- **Retrieval Loose Ends: Notebook Cells, Prose Section Ids, drawio Decision** (`1wh1b-enh retrieval-loose-ends-notebook-prose-ids-drawio`) — 6 ACs completed. Key decisions: Repeat-only ordinals for prose ids (first occurrence keeps its current id).; Ordinal suffix shape: `~k` (a reserved non-slug character), via `_dedupe_id_base`.
## Watchpoints

- Watchpoint: the ordinal suffix must NOT be bare `-N`: a legal `_slugify` tail (1,647
  same-shaped ids in this corpus). Non-slug-alphabet character or
  collision-aware assignment, per repaired Requirement 2.
- Watchpoint: the census is the authority and sweeps ALL un-anchored slug-id
  emitters (HTML/XML fallbacks, config chunker), not only md/rst/adoc; census
  sites not fixed in this wave must be explicitly dispositioned as follow-up.
- Baselines freeze BEFORE any chunker edit; differential sources must gain a
  duplicate-titled source or the declared delta classes are vacuous.
- Seed-211 edits land inside the `GuruIndexScopeParityTests`-guarded
  `## Index Scope` region: open `seed_edit_allowed`, byte-identical guru.md
  mirror edit, close the gate immediately.
- The `CHUNKER_VERSION` bump hard-fails the docs gate until the lint-bound
  `performance-budget.md` pin refreshes; refresh the two stale `"34"` pins in
  the pipeline doc in the same pass.
- `chunker.py` and `test_chunker.py` serialize through one lane.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-08-29: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the plan's ordinal-suffix safety argument does not transfer from SDL — `-N` is a legal `_slugify` tail with 1,647 same-shaped ids in this corpus, so the mitigation as written was unachievable; strongest-alternative: collision-aware ordinal assignment against the file's literal slugs instead of a reserved non-slug suffix character — both admitted by the repaired Requirement 2, implementation chooses with census evidence)
- Council seat evidence — red-team (2026-08-29): all nine load-bearing claims verified by executed probes (`chunk_jupyter` emission shape, both-tables drop via `_is_docs_kind`/`SOURCE_CODE_EXTENSIONS`, id collisions across md/rst/adoc/H3-split/line-window, silent last-writer-wins in `_plan_lance_delta_rows` and the registry upsert, `.drawio` walk-in/zero-rows, SDL `crumb_counts` mechanics, golden-set harness fit, seven kind mirrors resolve, CHUNKER 37 + differential fixtures); falsified the suffix reserved-shape claim and the differential-source coverage; found the `chunk_html` fallback collision class and three notebook kind-pinning tests; repairs applied to Requirements 1, 2, 5, AC-1, AC-2, Tasks, and Risks.
- Council seat evidence — docs-contract-reviewer (2026-08-29): carrier sweep found the missed lint-bound `docs/architecture/performance-budget.md` chunker pin (AC-6 mechanically unsatisfiable without it) and the `CHANGELOG.md` `[Unreleased]` carrier; confirmed the seed edit lands inside the parity-guarded `## Index Scope` region with byte-identical mirror discipline; identified the two stale `"34"` pipeline-doc pins and the two-part testing-architecture edit; scaffolding cross-references verified clean; repairs applied to Scope, AC-6, and Affected Architecture Docs.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| CODE-DEL-1 | do_now | no | completed | — |

*Machine review state — 1 findings; current: do_now 1, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| code-reviewer | approved | current executed approval follows every affected repair | none |
| qa-reviewer | approved | current executed approval follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 16 | 0 |
| implement | 80 | 1,650,764 |
| review | 22 | 56,540 |
| **Total** | **118** | **1,707,304** |

<!-- wave:context-efficiency-state {"generation":119,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":80,"content_source_credit":1808793,"derived_artifact_credit":0,"direct_net":1650764,"estimated_tokens_saved":1650764,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3307,"response_debit":157766,"source_credit_count":29,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3044},"plan":{"calls":16,"content_source_credit":17713,"derived_artifact_credit":1128,"direct_net":-202,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3404,"response_debit":19145,"source_credit_count":10,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3506},"review":{"calls":22,"content_source_credit":90342,"derived_artifact_credit":1586,"direct_net":56540,"estimated_tokens_saved":56540,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":8916,"response_debit":27818,"source_credit_count":19,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1346}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":118,"content_source_credit":1916848,"derived_artifact_credit":2714,"direct_net":1707102,"estimated_tokens_saved":1707304,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":15627,"response_debit":204729,"source_credit_count":58,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":7896},"wave_id":"1wl7u retrieval-loose-ends"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 1 | 0 | 1 | 183,556 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":1,"estimated_exploration_avoided":183556,"surfaced_events":1} -->
<!-- wave:exploration-avoided end -->
