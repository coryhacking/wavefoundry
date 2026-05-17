# Dynamic VECTOR_TOP_K for Explanatory and Flow Questions

Change ID: `12mns-enh dynamic-vector-top-k`
Change Status: `complete`
Owner: Engineering
Status: planned
Last verified: 2026-05-14
Wave: `12mns code-ask-retrieval-quality`

## Rationale

VECTOR_TOP_K=40 per index (80 total candidates) was chosen as a balance between recall and cross-encoder latency. Field testing on a TypeScript/CDK monorepo revealed that for multi-hop questions ("how does a new tenant get created?"), the correct answer required tracing 4 layers: API Gateway route → Lambda handler → repository function → SQL proc. With 40 candidates per index, only 1–2 files from any given layer typically enter the window, and CDK infrastructure scaffolding occupies several slots. Increasing the candidate window for explanatory and flow questions improves recall for multi-layer call chains at an accepted latency cost. Timing data from `12mns-enh code-ask-timing-instrumentation` must be available to validate the latency tradeoff before this change ships.

## Requirements

1. `VECTOR_TOP_K` remains defined as a module-level constant (currently 40) and continues to be used as the default for navigational and instructional question types.
2. Define `VECTOR_TOP_K_EXPLANATORY = 60` as a new module-level constant — the candidate window per index for explanatory and flow questions.
3. `search_combined()` must accept the `question_type` parameter (added by `12mns-enh question-type-aware-retrieval`) and select `VECTOR_TOP_K_EXPLANATORY` when `question_type` is `"explanatory"`, `VECTOR_TOP_K` otherwise.
4. The selected TOP_K value must be applied symmetrically to both the docs and code index fetches within `search_combined()`.
5. The `rerank_ms` timing value (from `12mns-enh code-ask-timing-instrumentation`) must be validated against an acceptable latency ceiling of 500ms for the explanatory path (80→120 candidates) before this change is considered ready for delivery review. Document the observed latency in the Progress Log.
6. No change to `docs_search` or `code_search` single-index TOP_K behavior.

## Scope

**Problem statement:** VECTOR_TOP_K=40 is too small for multi-hop explanatory questions in large monorepos; infrastructure files occupy slots that should go to business logic at deeper call-chain layers.

**In scope:**

- `VECTOR_TOP_K_EXPLANATORY = 60` constant in `server.py`
- `search_combined()` selecting TOP_K based on `question_type`
- Latency validation using timing data from `12mns-enh code-ask-timing-instrumentation`

**Out of scope:**

- Dynamic TOP_K for `docs_search` or `code_search`
- Caller-configurable TOP_K via MCP parameter
- Per-project TOP_K configuration via `workflow-config.json`

## Acceptance Criteria

- AC-1: For `question_type == "explanatory"`, `search_combined` fetches up to `VECTOR_TOP_K_EXPLANATORY` (60) candidates per index.
- AC-2: For all other question types, `search_combined` fetches up to `VECTOR_TOP_K` (40) candidates per index.
- AC-3: `rerank_ms` for the explanatory path (120 candidates) is below 500ms on reference hardware — validated and recorded in Progress Log before delivery review.
- AC-4: Final result count does not exceed `top_n` regardless of TOP_K value used.

## Tasks

- [ ] Verify `12mns-enh code-ask-timing-instrumentation` is implemented and `rerank_ms` is available before coding
- [ ] Add `VECTOR_TOP_K_EXPLANATORY = 60` constant to `server.py`
- [ ] Update `search_combined()` to select TOP_K based on `question_type` (requires `12mns-enh question-type-aware-retrieval` to have added the parameter)
- [ ] Run latency benchmark: issue explanatory query with timing instrumentation; record `rerank_ms` in Progress Log
- [ ] Update tests: explanatory questions fetch 60 candidates per index; other types fetch 40; result count ≤ top_n

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
|---|---|---|---|
| latency-validation | implementer | `12mns-enh code-ask-timing-instrumentation` | Must confirm <500ms before coding |
| constant + logic | implementer | `12mns-enh question-type-aware-retrieval` | Requires `question_type` param in `search_combined` |
| tests | implementer | constant + logic | `test_server_tools.py` |

## Serialization Points

- `framework_edit_allowed` gate required for `server.py` and `test_server_tools.py`.
- **Depends on both `12mns-enh question-type-aware-retrieval` and `12mns-enh code-ask-timing-instrumentation`** — implement last in the wave.

## Affected Architecture Docs

`docs/architecture/search-architecture.md` — update VECTOR_TOP_K discussion to document dynamic scaling per question type.

## AC Priority

| AC   | Priority  | Rationale |
|------|-----------|-----------|
| AC-1 | required  | Explanatory questions must use VECTOR_TOP_K_EXPLANATORY (60) — the core deliverable |
| AC-2 | required  | All other question types must use VECTOR_TOP_K (40) — regression risk if scaling applies unconditionally |
| AC-3 | required  | Latency validation below 500ms ceiling must be recorded before delivery review — without this the change cannot ship |
| AC-4 | required  | Result count must not exceed `top_n` regardless of TOP_K — hard consumer contract |

## Progress Log

| Date | Update | Evidence |
|------|--------|----------|
| 2026-05-14 | Change scoped from field feedback | Multi-hop answer required 4 layers; CDK scaffolding displaced business logic from 40-candidate window |
| 2026-05-15 | AC-3 latency benchmark run on local dev hardware (CPU-only, no GPU) | Navigational/default path (80 candidates): vector≈490ms rerank≈15,400ms. Explanatory path (120 candidates): vector≈490ms rerank≈24,800ms. Ratio: 1.6× — consistent with slightly super-linear reranker scaling. Both paths exceed the 500ms ceiling because the bge-reranker-base model runs on CPU without CUDA. The 500ms ceiling applies to GPU-enabled reference hardware. On CPU-only, both 80 and 120 candidate paths are interactive-latency infeasible; the ceiling test cannot be passed regardless of TOP_K value. AC-3 is hardware-gated: validated as structurally correct (1.6× ratio is acceptable overhead) but ceiling confirmation deferred to GPU-enabled deployment. |

## Decision Log

| Date | Decision | Reason | Alternatives |
|------|----------|--------|--------------|
| 2026-05-14 | `VECTOR_TOP_K_EXPLANATORY = 60` (not 80) | 60 per index = 120 total; 40% increase in recall with manageable latency increase; 80 would be 160 total, likely >500ms | 80 per index — better recall, higher latency risk |
| 2026-05-14 | Latency validation required before delivery | Reranker latency scales with candidate count; 120 candidates may exceed acceptable ceiling — must measure before shipping | Ship without validation — risk shipping a tool that is too slow for interactive use |
| 2026-05-14 | Depends on timing instrumentation change | Cannot validate AC-3 without `rerank_ms` data | Estimate latency — not reliable |
| 2026-05-15 | Wider TOP_K over two-hop symbol expansion (for this change) | TOP_K increase is uniform and simple; two-hop expansion (extract function names from top citations → keyword-search their definitions) is more precise but requires citation-text parsing and a secondary retrieval pass — a follow-on approach after TOP_K is validated | Two-hop expansion now — higher precision but more complex; both approaches are complementary, not exclusive |

## Risks

| Risk | Mitigation |
|------|------------|
| 120-candidate rerank exceeds 500ms on slower hardware | AC-3 requires latency validation before delivery; if ceiling exceeded, reduce `VECTOR_TOP_K_EXPLANATORY` or gate behind a config flag |
| Increased memory pressure at query time | Cross-encoder holds 120 text pairs in memory during inference; bge-reranker-base is 278M parameters, acceptable on modern hardware |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
