# MCP Docs Search Reliability

Change ID: `129p7-bug mcp-docs-search-reliability`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-04-30
Wave: `129p8 mcp-docs-search-reliability`

## Rationale

Wavefoundry's MCP inspection tools can resolve plans and prompts directly from repository files (`wave_list_plans`, `wave_get_change`), but semantic docs retrieval (`docs_search`) is currently unreliable in exactly the situations where agents need it most.

Two separate failures were observed:

**1. The project index can silently go stale outside hook-driven clients.** The current project index under `.wavefoundry/index/` did not include the newly created plan `129p7-bug mcp-docs-search-reliability.md` because the incremental reindex path is primarily triggered by Claude/Cursor post-edit hooks. In a Codex/apply-patch session, those hooks did not run, so the semantic index stopped reflecting repository reality.

**2. `docs_search` can crash instead of returning a structured diagnostic.** Query-time embedding in `server.py` constructs a `fastembed.TextEmbedding` instance on demand. When the model cache is missing and the environment is offline, fastembed attempts a network fetch and raises a transport exception. `docs_search_response()` currently catches `IndexNotReadyError`, but not model-download/network failures, so the MCP contract breaks instead of returning a recovery-oriented error.

These two failures combine badly: even when the index files exist, a user cannot tell whether the problem is stale content, missing model cache, or a broken search contract. The server needs explicit index health checks, offline-safe error handling, and a degraded-mode retrieval path that remains useful when the semantic layer is unavailable.

## Requirements

1. `docs_search` must never crash the server or raise raw fastembed / HTTP transport exceptions to the caller. All model-initialization, model-cache, and network-related failures must be converted into structured MCP diagnostics.
2. The server must distinguish at least three failure classes in search diagnostics:
   - index missing
   - index stale relative to repository files
   - semantic query model unavailable offline
3. The project index health check must detect when repository files relevant to docs search have changed since the last successful project-index build. The diagnostic must point to a concrete recovery command.
4. The stale-index check must work in self-hosted Wavefoundry and in seeded target repositories without assuming any specific editor hook integration.
5. When semantic query embedding is unavailable but searchable text artifacts exist, `docs_search` must provide a degraded-mode fallback rather than a total failure. The fallback may be lexical/keyword based, but it must be explicitly labeled as non-semantic.
6. The degraded-mode search must search the same logical content classes that `docs_search` is responsible for: project docs plus framework docs/seeds when those layers are present.
7. The fallback result envelope must preserve the current MCP response discipline:
   - structured JSON
   - trust labels
   - explicit diagnostics
   - clear next-tool or recovery guidance
8. `setup_index.py` must explicitly verify that required embedding models are locally usable after setup, not merely that Python packages are importable. The setup flow must own model prewarming or equivalent cache population so a successful setup implies the local model artifacts are present.
9. The index metadata or index-health path must be extended as needed so the server can determine whether the project layer or framework layer is stale without relying on vague timestamps alone.
10. Hook-driven indexing may remain an optimization, but the architecture and docs must stop implying that hook execution is universal. Non-hook environments need an explicit supported refresh/recovery path.
11. Query-time semantic search must run in explicit offline-only mode once setup has succeeded. When the local model cache is absent, incomplete, or corrupted, `docs_search` must fail or degrade gracefully without attempting a network fetch during the MCP request.
12. `docs_search` contract changes, degraded-mode behavior, and recovery guidance must be documented in the MCP tool contract and architecture docs.
13. This change must not expand into broader embedding-model replacement work, code-navigation work, or wave lifecycle mutation work. It is a reliability fix for the existing docs search surface.

## Scope

**Problem statement:** `docs_search` cannot currently be relied on as the primary MCP docs retrieval path because the index can go stale in some agent environments and semantic query embedding can fail offline with an uncaught runtime exception.

**In scope:**

- structured offline-safe error handling for semantic docs search
- project/framework index staleness detection
- degraded-mode fallback docs retrieval when semantic embedding is unavailable
- setup flow hardening so model usability is verified, not assumed, and required model artifacts are prewarmed into local cache
- explicit offline-only query behavior after setup so MCP requests do not unexpectedly fall through to network download attempts
- tests covering stale index, missing cache, and degraded-mode behavior
- contract and architecture documentation updates for the changed behavior

**Out of scope:**

- changing the embedding model family or acceleration path
- redesigning `code_search`
- adding general exact code-navigation tools (covered by `12991-feat mcp-code-navigation-tools`)
- adding remote model hosting, hosted indexing, or network-required search
- changing wave lifecycle tooling

## Acceptance Criteria

- AC-1: `docs_search` returns a structured MCP error or degraded-mode result when the embedding model cannot be initialized offline; no raw transport exception escapes.
- AC-2: A stale project index is detected when a newly created or modified docs file is not reflected in `.wavefoundry/index/`; the diagnostic includes an actionable rebuild/recovery command.
- AC-3: `docs_search` can still return useful degraded-mode results for a query like `agent catalog expansion` when semantic embedding is unavailable, provided the underlying text artifacts are present.
- AC-4: Degraded-mode results are clearly labeled so clients can distinguish semantic retrieval from lexical fallback.
- AC-5: `setup_index.py` or its delegated build path prewarms and verifies local model usability strongly enough that a successful setup implies later query-time initialization should not require a network call.
- AC-6: Tests cover:
  - missing index
  - stale index
  - missing model cache / embedder initialization failure
  - offline-only query mode when cache is present
  - degraded-mode fallback results
  - unchanged semantic success path
- AC-7: `docs/specs/mcp-tool-surface.md` and architecture docs describe the revised `docs_search` behavior, diagnostics, and fallback semantics.
- AC-8: Operator-facing docs identify the supported recovery path for non-hook environments so stale indexing is understandable rather than surprising.

## Tasks

- Confirm the current hook-driven indexing assumptions and document which environments do and do not trigger automatic project reindex.
- Add an index-health helper in `server.py` that can report missing/stale project and framework layers.
- Decide the stale-index signal source:
  - lightweight mtime comparison
  - file-hash comparison against `meta.json`
  - hybrid approach
- Harden embedder initialization so fastembed/network/cache failures are normalized into `IndexNotReadyError` or an equivalent structured failure path.
- Implement degraded-mode docs search fallback for cases where text artifacts are present but semantic embedding is unavailable.
- Decide whether degraded-mode fallback should activate only on embedder failure or also on known stale-index conditions.
- Update `setup_index.py` to prewarm the required model cache, verify model usability after dependency checks, and document the expected cache state.
- Update `server.py` query-time embedder creation to use explicit offline-only behavior after setup (for example `local_files_only=True` or equivalent environment control), and convert cache-miss/corruption conditions into structured diagnostics.
- Update or add tests in `.wavefoundry/framework/scripts/tests/` for stale-index detection and offline-safe search behavior.
- Update `docs/specs/mcp-tool-surface.md`.
- Update `docs/architecture/current-state.md` and `docs/architecture/data-and-control-flow.md`.
- Update `docs/contributing/build-and-verification.md` or the most relevant operator-facing doc to explain manual reindex recovery in non-hook environments.

## Agent Execution Graph


| Workstream          | Owner       | Depends On     | Notes                                                                 |
| ------------------- | ----------- | -------------- | --------------------------------------------------------------------- |
| failure-analysis    | planner     | —              | Lock down stale-index and offline-model failure modes                 |
| contract-design     | planner     | failure-analysis | Settle diagnostics, degraded-mode behavior, and recovery semantics |
| server-hardening    | implementer | contract-design | `server.py` search reliability and index-health changes              |
| setup-hardening     | implementer | contract-design | `setup_index.py` model prewarm, cache verification, and recovery UX |
| tests               | implementer | server-hardening, setup-hardening | Reliability regression coverage                      |
| docs                | implementer | contract-design, tests | Spec + architecture + operator recovery docs                    |


## Serialization Points

- `server.py` search behavior and diagnostics should be settled before test expectations are written broadly, because MCP response shape is a contract surface.
- Any index-health metadata change must be coordinated between writer paths (`indexer.py` / `setup_index.py`) and reader paths (`server.py`).
- If degraded-mode fallback introduces new response fields or trust labels, `docs/specs/mcp-tool-surface.md` must be updated in the same change.

## Affected Architecture Docs

- `docs/architecture/current-state.md`
- `docs/architecture/data-and-control-flow.md`
- `docs/specs/mcp-tool-surface.md`

`docs/architecture/testing-architecture.md` may also need a small update if the verification flow adds a new offline-safe search test seam.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority                                             | Rationale |
| ---- | ---------------------------------------------------- | --------- |
| AC-1 | required | Raw transport or model-init exceptions break the MCP contract and leave the primary bug unfixed. |
| AC-2 | required | The observed failure included a stale project index; detection and recovery guidance are core to the fix. |
| AC-3 | important | Useful fallback retrieval matters when semantic search is unavailable, but server safety and diagnostics come first. |
| AC-4 | important | Clients should be able to distinguish degraded lexical fallback from semantic results, but this is secondary to having a fallback at all. |
| AC-5 | required | Explicit offline-only query behavior and cache prewarming were directly requested and prevent network-time regressions. |
| AC-6 | required | Search reliability now spans multiple runtime states; regression coverage is needed to keep the contract stable. |
| AC-7 | required | `docs_search` behavior is a documented tool contract and must stay aligned with architecture and spec docs. |
| AC-8 | important | Manual recovery guidance is important for non-hook environments, but it does not determine runtime correctness by itself. |


## Progress Log


| Date       | Update         | Evidence                 |
| ---------- | -------------- | ------------------------ |
| 2026-04-30 | Plan authored. | This conversation thread |
| 2026-04-30 | Prepare wave completed; change relocated into active wave and marked ready. | `docs/waves/129p8 mcp-docs-search-reliability/wave.md` |


## Decision Log


| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-04-30 | Treat stale-index detection and offline-safe semantic search as one reliability bug rather than two unrelated fixes. | In practice the user experiences them together as “docs search didn’t work,” and the recovery UX should cover both. | Split into separate bug plans; rejected because it would fragment one user-facing failure mode. |
| 2026-04-30 | Keep embedding-model replacement work out of scope. | Reliability should be fixed before model experimentation or acceleration work proceeds. | Fold into `1297p-feat embedding-model-ane-eval`; rejected as a scope collision. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Degraded-mode lexical fallback becomes noisy or misleading compared to semantic search. | Label fallback results explicitly and keep diagnostics clear that ranking quality is degraded. |
| Stale-index detection is too expensive if it hashes the whole repo on every search call. | Prefer a lightweight health check first; use targeted metadata only where needed. |
| Setup hardening still leaves query-time surprises because fastembed cache semantics differ by host/runtime. | Add tests and explicit diagnostics for model-unavailable paths even after setup succeeds. |
| Response-shape changes break assumptions in existing tests or future MCP clients. | Update the tool contract doc and keep the envelope backward-compatible where possible. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
