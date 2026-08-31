# Index Quality Audit Dispositions

Owner: Engineering
Status: active
Last verified: 2026-08-30

## Purpose

Classify the 2026-08-30 semantic, FTS5, and structural-graph audit findings by user impact and scheduling value, and map every actionable finding to a consolidated change plan.

## Framework Interpretation

The canonical review gate in `.wavefoundry/framework/seeds/209-agent-harness-core.prompt.md` derives `not_issue`, `do_now`, `maybe_later`, or `dont_do_later`. Its `maybe_later` means optional-but-worth-doing-now, not deferred work; `dont_do_later` deliberately creates no backlog item. Because this audit occurred before wave admission, the table below uses an operator scheduling layer while preserving those semantics:

- **Needs fixed now:** a real public-contract or materially observable supported-path defect; it would derive `do_now` once admitted.
- **Should fix now:** positive, bounded, safe work whose benefit exceeds repair risk; it corresponds to the semantic facts behind `maybe_later` once admitted.
- **Fix later:** operator-directed planned research or relevance improvement whose current impact is bounded or whose correction must first be selected by measurement. This is a scheduling label, not a redefinition of canonical `maybe_later`.
- **Do not fix:** invalid, conforming, intentional, adequately served by another public tool, or unsupported by enough user-impact evidence. No plan is created.

## Needs Fixed Now

| Finding | Why | Plan |
| --- | --- | --- |
| Flat tree-sitter IDs collapse distinct CSS/JS/TOML chunks | Supported-path semantic and FTS content loss; health can still say covered | `1wngv-bug chunk-identity-source-range-integrity` |
| Oversized prose uses section-relative source lines | Incorrect citations and distinct-evidence collapse | `1wngv-bug chunk-identity-source-range-integrity` |
| FTS can be missing while reconcile and queries report healthy state | Exact-token retrieval silently unavailable with false diagnostics | `1wpag-bug fts-reconciliation-query-honesty` |
| Language and per-file filters run after bounded retrieval | Public filters produce false zeroes and underfilled results | `1wpah-bug retrieval-candidate-generation-correctness` |
| External calls can bind to non-callable JSON keys | Phantom calls contaminate hierarchy, impact, path, risk, and communities | `1wpai-bug graph-edge-resolution-guards` |
| Generic schema reads bind to unrelated config fixtures | False configuration dependencies and ownership | `1wpai-bug graph-edge-resolution-guards` |
| Graph-report filters run after top-N truncation | Reproduced regression against a completed public requirement | `1wpaj-bug graph-query-contract-correctness` |
| Call hierarchy omits per-edge trust metadata | Public guidance cannot be followed using the preferred tool | `1wpaj-bug graph-query-contract-correctness` |
| Standing retrieval benchmark cannot load or exercise production retrieval | Ranking changes lack a valid shipped-path gate | Existing admitted `1sear-enh golden-query-retrieval-eval-suite`, extended by this audit |

## Should Fix Now

| Finding | Why | Plan |
| --- | --- | --- |
| Declared Lance `nprobes` and `refine_factor` are not applied | Bounded integration defect; runtime and documented tuning disagree | `1wpah-bug retrieval-candidate-generation-correctness` |
| Nested Python methods exhaust the top-level summary cap | Bounded orientation recall loss; body chunks remain available | `1wngv-bug chunk-identity-source-range-integrity` |
| `code_ask` candidate-window description and rerank comments drift from runtime | Small public/maintainer contract cleanup adjacent to candidate repair | `1wpah-bug retrieval-candidate-generation-correctness` |
| Current architecture still names retired Tantivy indexes | Small current-state documentation correction adjacent to FTS repair | `1wpag-bug fts-reconciliation-query-honesty` |

## Fix Later

| Finding | Why later | Plan |
| --- | --- | --- |
| First-twelve-token policy can drop a tail identifier | Synthetic but credible recall weakness; safety cap should remain and selection needs evaluation | `1wpid-enh lexical-ranking-robustness` |
| Raw BM25 is compared across independent docs/code tables | Healthy reranking mitigates most impact; direct/degraded fusion still merits measured repair | `1wpid-enh lexical-ranking-robustness` |
| Machine evidence JSON dominates architectural communities | Orientation quality concern with no content-loss requirement; policy needs topology measurement | `1wpie-enh graph-quality-evaluation-and-evidence-isolation` |
| Graph fidelity lacks a representative cross-relation evaluation | Valuable standing evidence, but isolated tests and live tools remain usable today | `1wpie-enh graph-quality-evaluation-and-evidence-isolation` |

## Do Not Fix

| Investigated behavior | Disposition rationale |
| --- | --- |
| File paths are not FTS MATCH terms | This is intentional corpus design; `code_list_files`, `code_keyword`, `code_definition`, and exact navigation serve the user need without adding path noise to BM25. |
| Unicode accent folding and indivisible underscore identifiers | Intentional `unicode61` tokenizer behavior; observed results conform to the documented lexical contract. |
| FTS operator-like or malformed input | Tokens are quoted and parameterized; bounded probes found no query-language injection or failure. |
| Empty lexical queries | Correctly rejected with typed invalid-argument behavior. |
| Summary chunks can outrank implementation bodies for some multi-token queries | BM25 length normalization explains the result; no relevance regression was established. The standing eval may promote a measured case later. |
| Irrelevant semantic query neighbors | `code_ask` correctly returned low confidence and abstained; raw `code_search` is a browsing tool and does not promise abstention. |
| Reranker batch-composition concern | Previously measured and withdrawn as `1v455`; the proposed repair worsened top-10 misses. No new evidence supports reopening it. |
| Incremental semantic/graph publication, cache invalidation, MATCH safety, and graph path weighting | Audit probes and existing tests did not reproduce defects. |

## Planning Decisions

Seven new consolidated plans were chosen instead of one plan per symptom. Each groups findings that share an implementation boundary and verification strategy. The existing `1sear` plan was extended rather than duplicated.

The operator subsequently admitted the plans into three waves:

- `1wpif index-content-and-retrieval-correctness`: `1wngv`, `1wpag`, `1wpah`
- `1wpig graph-correctness-and-trust-contracts`: `1wpai`, `1wpaj`
- `1wpih index-quality-evaluation-and-ranking`: `1wpid`, `1wpie`

All three remain `planned`; Prepare is still required before implementation.
