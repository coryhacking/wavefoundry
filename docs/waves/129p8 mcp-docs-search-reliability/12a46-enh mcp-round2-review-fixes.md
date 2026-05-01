# MCP Round-2 Review Fixes

Change ID: `12a46-enh mcp-round2-review-fixes`
Change Status: `complete`
Owner: implementer
Status: complete
Last verified: 2026-04-30
Wave: 129p8 mcp-docs-search-reliability

## Rationale

A second mcp-builder design review of `server.py` identified 8 new gaps after the round-1 fixes (12a0x) landed. These range from a semantically incorrect `status: "error"` on a healthy-but-absent index, to dry-run mode silently writing docs, to missing pagination metadata and stale workflow hints. Addressing them brings the server to full correctness and consistency.

## Requirements

1. `wave_index_health_response` must return `status: "ok"` when the health check succeeds but the index is absent or stale; `status: "error"` is reserved for health check failures (I-1).
2. `code_search_response` must catch `SemanticModelUnavailableOfflineError` explicitly and emit `"semantic_model_unavailable_offline"` as the diagnostic code, not `"index_not_ready"` (I-2).
3. `wave_prepare_response` and `wave_close_response` must not call `run_garden()` when `mode == "dry_run"` (I-3).
4. `wave_list_waves_response` and `wave_list_plans_response` must include `"total"` (the untruncated count) alongside `has_more` in their data payloads (I-4).
5. `wave_index_health` tool docstring must mention `wave_index_build` as the recovery action when the index is non-ready (A-1).
6. `docs_search_response` must omit `"kind"` from the response data (or return `""`) when no filter is applied, rather than returning `"kind": null` (A-2).
7. The `status: "dry_run"` third envelope status used by mutating tools must be documented in the response contract comment; alternatively, normalise to `status: "ok"` with `"mode": "dry_run"` in data (A-3).
8. The `maintain_framework` workflow entry in `_help_catalog` must update its usage hint to reflect that `wave_garden` and `wave_sync_surfaces` now require `mode='run'` (A-4).

## Scope

**Problem statement:** The MCP server has several correctness and consistency gaps discovered in a second design review: a health-check tool that cries wolf on normal absent-index state; a code search path with a wrong diagnostic code; dry-run lifecycle tools that silently write docs; list tools missing total counts; and a workflow catalogue with stale usage hints.

**In scope:**

- `wave_index_health_response` status logic (`server.py`)
- `code_search_response` exception handling (`server.py`)
- `wave_prepare_response` and `wave_close_response` dry-run garden calls (`server.py`)
- `wave_list_waves_response` and `wave_list_plans_response` total count (`server.py`)
- `wave_index_health` tool docstring (`server.py`)
- `docs_search_response` kind field normalisation (`server.py`)
- Dry-run status documentation or normalisation (`server.py`)
- `_help_catalog` maintain_framework usage hint (`server.py`)

**Out of scope:**

- Full cursor/offset pagination (limit + has_more + total is sufficient)
- `outputSchema` / `structuredContent` migration (requires FastMCP version bump)
- Changing the `"dry_run"` status to `"ok"` if that requires broad test changes (document it instead)

## Acceptance Criteria

- AC-1: `wave_index_health_response` returns `status: "ok"` when health data is successfully computed, regardless of `readiness_overview` value; `status: "error"` only when the `except` branch fires.
- AC-2: `code_search_response` catches `SemanticModelUnavailableOfflineError` separately and uses `"semantic_model_unavailable_offline"` as the diagnostic code.
- AC-3: `wave_prepare_response` only calls `run_garden()` when `mode_s == "create"`.
- AC-4: `wave_close_response` only calls `run_garden()` when `mode_s == "create"`.
- AC-5: `wave_list_waves_response` data includes `"total": len(all_waves)`.
- AC-6: `wave_list_plans_response` data includes `"total": len(all_plans)`.
- AC-7: `wave_index_health` tool docstring includes a sentence directing agents to `wave_index_build` when the result is non-ready.
- AC-8: `docs_search_response` returns `"kind": k` (empty string `""`) rather than `"kind": null` when no kind filter is applied.
- AC-9: `"dry_run"` envelope status is documented in a comment near `_response()` (or normalised — decision at implementation time).
- AC-10: `_help_catalog` `maintain_framework` workflow `usage` hint updated to `wave_garden(mode='run')`.
- AC-11: Tests pass; `docs-lint` clean.

## Tasks

- Fix `wave_index_health_response` status logic: always `"ok"` on success path
- Add `SemanticModelUnavailableOfflineError` explicit catch to `code_search_response`
- Gate `run_garden()` in `wave_prepare_response` on `mode_s == "create"`
- Gate `run_garden()` in `wave_close_response` on `mode_s == "create"`
- Add `"total"` to `wave_list_waves_response` and `wave_list_plans_response`
- Update `wave_index_health` tool docstring with recovery hint
- Normalise `kind` in `docs_search_response` empty-filter path to `""`
- Document `"dry_run"` status in comment near `_response()`
- Update `_help_catalog` maintain_framework usage hint
- Run tests + docs-lint

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
|------------|-------|------------|-------|
| correctness | implementer | — | I-1 through I-4 (server logic fixes) |
| polish | implementer | — | A-1 through A-4 (docstring / catalog / contract doc) |
| verification | implementer | both above | tests + docs-lint |

## Serialization Points

- All changes are in `server.py`; implement in a single sequential pass.

## Affected Architecture Docs

N/A — MCP surface polish confined to `server.py`.

## AC Priority

| AC | Priority | Rationale |
|----|----------|-----------|
| AC-1 | required | Health tool returning `error` on normal absent-index state breaks agent flows |
| AC-2 | required | Wrong diagnostic code misleads recovery instructions |
| AC-3 | required | Dry-run prepare must not write docs |
| AC-4 | required | Dry-run close must not write docs |
| AC-5 | important | Agents need total count for pagination UX |
| AC-6 | important | Consistent with AC-5 |
| AC-7 | nice-to-have | Self-directing docstring improves agent discoverability |
| AC-8 | nice-to-have | Null vs empty string inconsistency confuses pattern-matching agents |
| AC-9 | nice-to-have | Documents the dry_run envelope contract for future developers |
| AC-10 | nice-to-have | Stale usage hint causes agents to call garden with wrong default |
| AC-11 | required | Verification gate |

## Progress Log

| Date | Update | Evidence |
|------|--------|----------|
| 2026-04-30 | Created from mcp-builder round-2 review | Review findings in session |
| 2026-04-30 | All 11 ACs implemented and verified | 305 tests pass; docs-lint clean |

## Decision Log

| Date | Decision | Reason | Alternatives |
|------|----------|--------|--------------|
| 2026-04-30 | Document "dry_run" status rather than normalise (TBD at impl) | Normalising requires test updates; documenting is lower risk | Normalise to "ok" + mode in data |

## Risks

| Risk | Mitigation |
|------|------------|
| Gating garden calls in prepare/close changes behaviour for existing callers | Only removes writes in dry-run; create mode is unchanged |
| AC-1 status change may affect tests asserting `status: "error"` on absent index | Update those assertions to `status: "ok"` + check `readiness_overview` |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
