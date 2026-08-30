# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-08-29
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1wl7w diagram-label-retrieval`
Title: Diagram Label Retrieval

## Objective

Make draw.io and Excalidraw diagrams searchable: extract their node, edge, and
frame labels into docs-routed `doc-code` units and re-admit both extensions at
the walk layer, superseding the 1wl7u `.drawio` exclusion now that the operator
has confirmed real `.drawio` files in their repositories. Raw serializations
stay unindexed; degenerate inputs degrade to zero chunks.

## Changes

Change ID: `1wl7v-enh drawio-excalidraw-label-retrieval`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator (session agent)
- Write-owning roles: implementer (chunker/indexer/tests), performance-reviewer
  (fixtures, golden queries, measurement), qa-reviewer (regressions,
  differentials), docs-contract-reviewer (carriers, seed parity)
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer
  (delivery council REQUIRED per the review-policy receipt)

Completed At: 2026-08-29

## Wave Summary

Wave `1wl7w` (Diagram Label Retrieval) delivered one change: Diagram Label Retrieval: drawio and excalidraw. Notable adjustments during implementation: Diagram Label Retrieval: drawio and excalidraw: Phase A executed (before any chunker edit). Fixtures built through the CANONICAL producer algorithms (`evidence/build_fixtures_1wl7v.py`): a compressed multi-page drawio (URL-encode, raw deflate, base64 per page) carrying an `object label` wrapper and an HTML-tagged value, a plain-XML drawio with the auto `Page-1` name, and a real-schema excalidraw with bound container text, a frame, an `isDeleted` ghost sentinel, and an empty-string element. Nine golden queries added (5 drawio, 4 excalidraw) with prefix-grouped ids; the diagrams eval branch gained the per-format id-prefix grouping (mirroring the shipped specs branch; the one admitted harness change) BEFORE the freeze. Baseline FROZEN (`evidence/eval_diagrams_before_1wl7v.json`): core d01-d09 hold 1.0/1.0 with the new fixtures in the corpus; drawio 0.0 and excalidraw 0.0 (structurally zero). Raw-text anchor scan recorded (`evidence/nb_anchor_uniqueness_raw.json`; compressed drawio anchors are raw-invisible by design, proven at chunk level below).; Diagram Label Retrieval: drawio and excalidraw: Pins flipped and regressions landed: `test_excludes_snap_keeps_generated_layer_non_vacuous` + `test_readmits_drawio_and_excalidraw_with_extraction` replace the two exclusion pins (WALKER >= 15), `GENERATED_EXT_LAYER` keeps `.snap`, the reinclude pin drops the drawio row, `test_extensions_registered_chunker_only` gains the extraction sets in the disjointness census, `test_excluded_formats_do_not_dispatch_to_diagram_chunker` narrows to `.d2`/`.dsl`, the version ratchet moves to 39 with the history line. New `DrawioChunkerTests` (10) and `ExcalidrawChunkerTests` (5): form equivalence, wrapper labels, two-layer decode, multi-page ids, auto-name fallback, the under-disk-cap deflate bomb, degenerate zero classes, docs membership/language/cap, oversized-split composition, injection idempotence, committed-fixture pins incl. the ghost. test_chunker 538 green, test_indexer 312 green. Label-coverage differential (`evidence/label_coverage_1wl7v.py/.json`): every authored label docs-eligible, ghost never leaks, compressed/plain identical by executed re-inflation, all 9 chunk-level anchors unique, revert-simulation FAILS against the pre-change chunker (4 violations) proving non-vacuity.; Diagram Label Retrieval: drawio and excalidraw: Carriers updated: seed-211 + guru.md Index Scope (byte-identical mirror edit behind `seed_edit_allowed`; twins byte-identical: 5,931 bytes by the parity oracle's heading-inclusive extraction (5,916 excluding the heading line), 18 parity tests green) now teach the extracted-label contract; search-architecture doc-code bullet (supersession of both walk exclusions, per-page/per-board units, bomb cap); pipeline doc (diagram-section extraction family, kind-table row, 39/15 pins); build-and-verification and mcp-tool-surface enumerations; testing-architecture (1wl7u row supersession clause + new 1wl7w tier row).

**Changes delivered:**

- **Diagram Label Retrieval: drawio and excalidraw** (`1wl7v-enh drawio-excalidraw-label-retrieval`) — 6 ACs completed. Key decisions: Chunk text is the EXTRACTED labels, never the raw serialization; degenerate inputs emit zero chunks.; Per-page `.drawio` ids ride `_dedupe_id_base` on the `diagram` base (`#diagram`, `#diagram~2`).
## Watchpoints

- Watchpoint: the `[Unreleased]` version numerals MUST refresh in the SAME
  landing as the CHUNKER/WALKER bumps (claims-engine red window: every
  intermediate full docs-gate run fails otherwise).
- Watchpoint: label sources include `object`/`UserObject` wrapper `label`
  attributes, with a wrapper-bearing fixture; value-only extraction silently
  drops them on well-formed real files.
- Watchpoint: the decompression cap is a per-page bounded `decompressobj` seam;
  the on-disk walk cap does not bound inflation (executed 64 KB bomb inflates
  past 10 MB). Over-cap inflate degrades to zero chunks.
- Baselines freeze BEFORE any chunker edit; the diagrams-branch per-format
  grouping (the one admitted harness change) lands with the fixtures so the
  frozen baseline is already per-format readable.
- Seed-211 edits land inside the `GuruIndexScopeParityTests`-guarded
  `## Index Scope` region: open `seed_edit_allowed`, byte-identical guru.md
  mirror edit, close the gate immediately.
- `chunker.py` and `test_chunker.py` serialize through one lane; the walk
  supersession lands WITH the chunkers, never separately.
- Delivery review requires the delivery COUNCIL in addition to the three lanes
  (per the receipt), a step up from the 1wl7u wave; plan the review pass
  accordingly as a follow-up obligation, not a surprise.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-08-29: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: draw.io's `object`/`UserObject` wrapper labels are silently dropped by `mxCell` value-only extraction on well-formed real-world files, defeating the degrade-to-zero spirit and blinding the label-coverage oracle — repaired by naming the wrapper attributes in Requirement 1 and requiring a wrapper-bearing fixture; strongest-alternative: accepting manual per-format computation over the aggregate-only diagrams eval readout instead of adding the id-prefix grouping — rejected in favor of the narrow, specs-branch-mirroring grouping so the bar reads off the committed JSON)
- Council seat evidence — red-team (2026-08-29; first attempt killed by host sleep, retried clean): all eight claim families verified by execution (compression chain round-trip with multi-page/plain/empty edges and the two-layer HTML decode; Excalidraw schema incl. bound containers; complete pin census with three sites neither the plan nor the sibling seat named; `_dedupe_id_base`/`chunk_diagram`/cap/injection idempotence mechanics; golden-harness fit with the aggregate-only readout gap; dispatch fallthrough plus an executed in-process supersession simulation re-admitting both files; bounded-inflate proof on a crafted 64 KB deflate bomb); misses found: wrapper labels, `isDeleted` ghosts and empty strings, auto `Page-N` breadcrumbs, over-cap boards walk-invisible, unpinned language values, export dual-extension symmetry — all repaired into Requirements 1, 2, 4, 5, 7 and the ACs.
- Council seat evidence — docs-contract-reviewer (2026-08-29): carrier sweep found the claims-engine red window (numerals refresh must ride the bump landing), the two chunker-side pins missing from the census, the 1wl7u testing-architecture row needing superseded framing, the pipeline kind-table row, and the mcp-tool-surface completeness edit; executed the parity extraction (twins byte-identical at 5,745 bytes) and located the falsified walk-excluded sentence inside the guarded region; verified no pre-existing stale pins in in-scope carriers and that the plan touches no closed-wave history; scaffolding cross-references verified clean; repairs applied to Requirements 4, 6, the tasks, and Affected Architecture Docs.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| QA-DEL-1 | do_now | no | completed | — |

*Machine review state — 1 findings; current: do_now 1, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | approved | current executed approval follows every affected repair | none |
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
| plan | 28 | 1,630,622 |
| implement | 60 | 1,438,222 |
| review | 13 | 80,091 |
| **Total** | **101** | **3,148,935** |

<!-- wave:context-efficiency-state {"generation":101,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":60,"content_source_credit":1516302,"derived_artifact_credit":180,"direct_net":1438222,"estimated_tokens_saved":1438222,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2711,"response_debit":78687,"source_credit_count":37,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3138},"plan":{"calls":28,"content_source_credit":1694251,"derived_artifact_credit":2020,"direct_net":1630622,"estimated_tokens_saved":1630622,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3827,"response_debit":65328,"source_credit_count":43,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3506},"review":{"calls":13,"content_source_credit":108380,"derived_artifact_credit":1663,"direct_net":80091,"estimated_tokens_saved":80091,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":6890,"response_debit":24408,"source_credit_count":20,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1346}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":101,"content_source_credit":3318933,"derived_artifact_credit":3863,"direct_net":3148935,"estimated_tokens_saved":3148935,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":13428,"response_debit":168423,"source_credit_count":100,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":7990},"wave_id":"1wl7w diagram-label-retrieval"} -->
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
