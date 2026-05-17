# Question-Type-Aware Retrieval: Scaffolding Layer Partition and RRF Weight Bias

Change ID: `12mns-enh question-type-aware-retrieval`
Change Status: `complete`
Owner: Engineering
Status: planned
Last verified: 2026-05-14
Wave: `12mns code-ask-retrieval-quality`

## Rationale

Every codebase has a scaffolding layer: files that declare, wire up, or route to resources without containing business logic. In AWS CDK projects these are `constructs/` and `stacks/`; in Terraform they are `modules/` and `resources/`; in Spring Boot they are `config/` and `beans/`; in Express/NestJS they are `routes/` and `controllers/`. Scaffolding files consistently crowd out business logic for explanatory questions because they carry resource-name strings ("CreateTenant", "GenerateTenant") that score well on term overlap with both the vector index and the cross-encoder — yet contain zero logic about how the operation actually works. The `question_type` classifier already identifies explanatory vs. navigational questions correctly; its output is not used to modulate candidate scoring or retrieval weighting. Applying a post-rerank scaffolding-layer partition for explanatory questions and an RRF weight bias favoring code for navigational questions will use the existing classifier to improve candidate quality without changing the reranker model.

## Requirements

1. `search_combined()` on `WaveIndex` must accept an optional `question_type: str` parameter (default `""`). When provided, it is used to modulate the RRF merge and post-rerank filtering steps — it must not change the vector fetch or reranker inference steps.
2. For `question_type == "navigational"`: apply an RRF score bias that increases the weight of code-index candidates relative to docs-index candidates before pooling. Implement as a multiplier on the `1/(k + rank)` score per source: code candidates get a `1.5×` multiplier, docs candidates get `1.0×`. Constants `RRF_NAVIGATIONAL_CODE_WEIGHT = 1.5` and `RRF_NAVIGATIONAL_DOCS_WEIGHT = 1.0` must be defined as module-level constants.
3. For `question_type == "explanatory"`: after reranking, apply a post-rerank soft penalty to any citation whose path matches a scaffolding-layer path pattern. The pattern covers path segments that universally indicate wiring/routing/declaration layers across common frameworks and infrastructure tools: `constructs`, `stacks`, `api-gateways`, `infra`, `infrastructure`, `cdk`, `modules`, `resources`, `providers`, `config`, `beans`, `routes`, `wiring`, `scaffolding`. Penalty: move matched citations to after all non-matched citations (preserving relative order within each group). This is a sort-stable partition, not a score adjustment.
4. The scaffolding-layer path patterns must be defined as a module-level constant `INFRASTRUCTURE_PATH_SEGMENTS` (frozenset of strings) so they are easy to extend without touching logic. The frozenset must be documented with a comment grouping entries by framework family: cloud IaC (CDK, Terraform, Pulumi), JVM frameworks (Spring), Node/TS frameworks (Express, NestJS, Next.js), and general infrastructure conventions.
5. `code_ask_response` must pass `question_type` from `_classify_question()` into `search_combined()`.
6. When the post-rerank partition fires (at least one citation was moved), `code_ask_response` must add `"infrastructure_demoted": true` to the response payload. When no citations were moved, the field must be absent (not `false`).
7. The `reranked` flag in the response must remain accurate — it reflects whether the cross-encoder ran, not whether the post-rerank partition fired.

## Scope

**Problem statement:** Scaffolding and wiring files — which declare or route to resources but contain no logic — outrank business logic for explanatory questions across all framework families because `question_type` classification output is not used to modulate the candidate pool or post-rerank ordering.

**In scope:**

- `RRF_NAVIGATIONAL_CODE_WEIGHT`, `RRF_NAVIGATIONAL_DOCS_WEIGHT`, `INFRASTRUCTURE_PATH_SEGMENTS` constants in `server.py`
- `search_combined(question_type=...)` parameter and RRF weight bias for navigational
- Post-rerank infrastructure partition for explanatory questions
- `code_ask_response` passing `question_type` to `search_combined`
- `infrastructure_demoted` flag in `code_ask` response
- Tests in `test_server_tools.py`

**Out of scope:**

- Changing VECTOR_TOP_K (separate change: `12mns-enh dynamic-vector-top-k`)
- Per-project configurable path patterns via `workflow-config.json`
- Applying path penalties to `docs_search` or `code_search` single-index paths

## Acceptance Criteria

- AC-1: For a navigational question, code-index candidates receive the `1.5×` RRF weight bias; docs candidates receive `1.0×` before pooling.
- AC-2: For an explanatory question with infrastructure-path citations in the reranked results, those citations appear after all non-infrastructure citations in the final list (stable partition).
- AC-3: When the partition fires, `infrastructure_demoted: true` appears in the `code_ask` response.
- AC-4: For a question type of `""` or `"instructional"`, neither the RRF bias nor the partition is applied.
- AC-5: `reranked` flag is unaffected by whether the partition fired.
- AC-6: `search_combined` with no `question_type` argument behaves identically to the current implementation.

## Tasks

- [ ] Add `RRF_NAVIGATIONAL_CODE_WEIGHT = 1.5`, `RRF_NAVIGATIONAL_DOCS_WEIGHT = 1.0`, `INFRASTRUCTURE_PATH_SEGMENTS = frozenset({...})` constants to `server.py`
- [ ] Add `question_type: str = ""` parameter to `search_combined()` signature
- [ ] In `_rrf_merge()` (or the RRF loop inside `search_combined()`): apply source-weight multiplier when `question_type == "navigational"`
- [ ] After reranking in `search_combined()`: apply stable partition when `question_type == "explanatory"`, check each result's `path` for any segment in `INFRASTRUCTURE_PATH_SEGMENTS`
- [ ] Update `code_ask_response` to pass `question_type` into `search_combined()`; include `infrastructure_demoted` in response when partition fired
- [ ] Update tests: navigational bias applied; explanatory partition applied; other types unaffected; `infrastructure_demoted` flag correct; `reranked` unaffected

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
|---|---|---|---|
| constants | implementer | — | `server.py` module-level constants |
| search-combined-update | implementer | constants | `search_combined` parameter + RRF bias + partition |
| code-ask-update | implementer | search-combined-update | pass `question_type`, add `infrastructure_demoted` |
| tests | implementer | code-ask-update | `test_server_tools.py` |

## Serialization Points

- `framework_edit_allowed` gate required for `server.py` and `test_server_tools.py`.
- Must be implemented before `12mns-enh dynamic-vector-top-k` (both modify `search_combined`).

## Affected Architecture Docs

`docs/architecture/search-architecture.md` — update the combined retrieval section to document question-type-aware RRF weighting and post-rerank infrastructure partition.

## AC Priority

| AC   | Priority  | Rationale |
|------|-----------|-----------|
| AC-1 | required  | RRF weight bias is the navigational path core — without it the change has no effect |
| AC-2 | required  | Stable partition for explanatory questions is the primary deliverable |
| AC-3 | important | `infrastructure_demoted` flag is observability — useful for validation but not a correctness gate |
| AC-4 | required  | Neutral and instructional questions must not be affected — regression risk if partition fires unconditionally |
| AC-5 | required  | `reranked` flag semantics must not be altered — downstream consumers depend on it |
| AC-6 | required  | Default (no question_type) must be backward-compatible — all existing call sites are uncategorized |

## Progress Log

| Date | Update | Evidence |
|------|--------|----------|
| 2026-05-14 | Change scoped from CDK monorepo field feedback | CDK constructs crowding out business logic; `question_type` unused in retrieval path |
| 2026-05-15 | Generalized from CDK-specific to framework-agnostic scaffolding layer pattern | `INFRASTRUCTURE_PATH_SEGMENTS` expanded to cover Terraform, Spring Boot, Express/NestJS, and general IaC conventions; rationale updated to describe universal scaffolding-layer problem |

## Decision Log

| Date | Decision | Reason | Alternatives |
|------|----------|--------|--------------|
| 2026-05-14 | Stable partition (not score adjustment) for post-rerank penalty | Partition is transparent and reversible; score adjustment would require rescaling the reranker output | Multiply reranker score by 0.5 for infrastructure paths — opaque, interacts with RRF fallback scores differently |
| 2026-05-14 | `INFRASTRUCTURE_PATH_SEGMENTS` as frozenset constant | Framework-agnostic heuristic; segments are grouped by framework family for maintainability; easy to extend without logic changes | Per-project config via workflow-config.json — adds config surface before the pattern is validated across diverse repo layouts |

## Risks

| Risk | Mitigation |
|------|------------|
| Scaffolding path segment matches legitimate business logic paths in some projects | Partition only applies for explanatory questions; agents can still read demoted citations — they appear last, not excluded; frozenset is designed conservatively and grouped by framework family for auditability |
| RRF weight bias over-suppresses docs for navigational questions | Bias is multiplicative (1.5×), not exclusive; docs candidates still enter pool and reranker evaluates all candidates |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
