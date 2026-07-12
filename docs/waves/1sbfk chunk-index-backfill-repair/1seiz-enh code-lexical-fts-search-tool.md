# `code_lexical` — Direct BM25 Exact-Token Search Over the Indexed Chunk Corpus

Change ID: `1seiz-enh code-lexical-fts-search-tool`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-11
Wave: `1sbfk chunk-index-backfill-repair`

## Rationale

Operator-directed for the 1.12.0 release (2026-07-11), motivated by the field retest of wave 1sbfk: the field investigator needed to answer "is this chunk actually in the lexical layer?" and had no tool for it — they resorted to opening `index-state.sqlite` directly. The internal API already exists (`index_state_store.fts_search(index_dir, table, query, limit, kind=...)`, shipped in 1rsh9/1sauc); nothing exposes it over MCP. A thin `code_lexical` tool gives agents:

1. **BM25-ranked exact-token search over the SAME corpus retrieval uses** — `code_keyword` matches live files (unranked, line-granular); `code_lexical` ranks indexed chunks by BM25, so it answers "what does the lexical layer say for this token?" — the exact-identifier lookups (error strings, compound identifiers, rare tokens) that are the FTS layer's documented purpose.
2. **A retrieval diagnostic surface** — verifying lexical-layer contents no longer requires sqlite access; combined with the 1sbfj coverage advisory it makes the whole lexical layer observable in-band.

Explicitly NOT a regex tool: FTS5 is a token-based inverted index (tokens, phrases, prefix, NEAR — no patterns), and the query builder treats FTS operators as literals by design. Regex remains `code_pattern`'s job; live-file exact match remains `code_keyword`'s.

## Requirements

1. **New read-only MCP tool `code_lexical(query, table="both", kind="", limit=20)`** wrapping `fts_search`: `table` selects `code`, `docs`, or `both` (merged best-first by BM25); `kind` is the exact chunk-kind filter the store already supports; `limit` defaults 20, hard-capped at 50. Results carry `{id, path, kind, language, lines, text, bm25, table}` with per-result text capped (~700 chars, `text_truncated: true` when cut) so prevalent tokens cannot blow the response cap.
2. **Loud, structured degrade:** absent store / FTS5-unavailable interpreter / FTS-hostile query all return `status: ok` with empty results plus a diagnostic naming the cause and recovery (`wf setup` / `wave_index_build`) — never a crash, matching the fusion path's degrade posture.
3. **Coverage tie-in:** when a searched table is materially under-covered (the same exact-first compare `wave_index_health` uses), the response carries a diagnostic that results may be partial until the next build heals the store — a zero-result answer on a broken store must not read as "not in the corpus".
4. **Routing discipline in the docstring:** prefer `code_definition`/`code_keyword`/`code_pattern`/`code_search` for their jobs; `code_lexical` is for BM25-ranked exact-token retrieval and lexical-layer verification. Compound identifiers are single tokens (tokenchars `_`) — the docstring states it.
5. **Docs weave (new-primitive discoverability):** spec tool table + Tool Detail section; `AGENTS.md` tool list + Code Navigation quick chooser; seed-211 lexical-signals block gains the tool pointer; seed-180 exploration order names it; rendered guru subagent allowlist(s) gain `mcp__wavefoundry__code_lexical`; re-render agent surfaces.
6. **Host note:** a new tool requires MCP client reconnect to appear (documented hot-reload limitation); upgrade docs already cover reconnect-after-upgrade, no new step needed.

## Scope

**Problem statement:** the FTS5 lexical layer is queryable only indirectly (fused inside `code_search`/`code_ask`) — there is no direct, ranked, filterable MCP view of it for exact-token lookups or layer verification.

**In scope:**

- `server_impl.py`: `code_lexical_response(...)` + `@mcp.tool` registration.
- Tests: shape/ranking/filters/limit-cap/text-cap; hostile-query and absent-store degrades; under-coverage diagnostic.
- Docs weave per Requirement 5.

**Out of scope:**

- Regex over FTS (impossible on an inverted index; `code_pattern` owns regex).
- Prefix/NEAR/boolean FTS syntax passthrough (the safe literal-quoting query builder is unchanged).
- Sub-token/camelCase indexing (separate eval-gated consideration, recorded in the quality log).

## Acceptance Criteria

- [x] AC-1: `code_lexical` returns BM25-ranked results from the selected table(s) with `kind` filter and merged best-first ordering; each result carries `id/path/kind/language/lines/text/bm25/table`; `limit` defaults 20 and hard-caps at 50; oversized chunk text is capped with `text_truncated: true`.
- [x] AC-2: FTS operators in the query are treated as literals (hostile queries return empty results, never an error), and the docstring routes regex to `code_pattern` and live-file exact match to `code_keyword`.
- [x] AC-3: Absent store / FTS-unavailable degrade to `ok` + empty results + a recovery diagnostic; an under-covered searched table adds a partial-results diagnostic (fixture-proven).
- [x] AC-4: Docs weave complete — spec table + Tool Detail, `AGENTS.md` list + chooser, seed-211 + seed-180 pointers, guru subagent allowlist rendered with the new tool.
- [x] AC-5: Full framework tests pass bytecode-free; docs validation passes; the tool is exercised live against this repo's backfilled store (exact compound identifier returns the defining chunk at rank 1 or with a clear BM25 lead).

## Tasks

- [x] Implement `code_lexical_response` + tool registration (text cap, limit cap, degrade paths, coverage diagnostic).
- [x] Tests: ranking/filter/cap/degrade/coverage fixtures in `test_server_tools.py` (+ store-side additions if needed).
- [x] Docs weave: spec, AGENTS.md, seed-211, seed-180 (seed gate), render agent surfaces.
- [x] Live probe on this repo; full suite; `wave_validate`.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| tool | implementer | — | Thin wrapper over existing `fts_search` |
| tests-docs | qa-reviewer | tool | Fixtures + weave + suite |


## Serialization Points

- Single-change scope; lands in wave `1sbfk` (late admission, operator-directed) so the tool ships in 1.12.0.

## Affected Architecture Docs

- `docs/specs/mcp-tool-surface.md` — tool table + Tool Detail (Requirement 5).
- N/A otherwise: additive query-layer tool over an existing store API; no boundary change.

## AC Priority

(Proposed; confirmed at admission review.)


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The tool's contract. |
| AC-2 | required | Safety posture + routing discipline. |
| AC-3 | required | A zero-result on a degraded store must never read as "absent from corpus". |
| AC-4 | required | New-primitive discoverability (weave feedback rule). |
| AC-5 | required | Standard verification gate + live proof. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-11 | Drafted, operator-directed ("let's do the new tool before we release 1.12"). Motivated by the 1sbfk field retest (investigator needed sqlite access to inspect the lexical layer) and the fusion-signal documentation gap closed the same day. | Operator direction; field retest report; `fts_search` API in `index_state_store.py`. |
| 2026-07-11 | Implemented: `code_lexical_response` + read-only `@mcp.tool` registration (limit cap 50, text cap 700 + `text_truncated`, literal-token safety via the fusion path's expression builder, absent-store `lexical_layer_unavailable` recovery diagnostic, `chunk_index_undercovered` partial-results warning reusing the health compare, healthy-zero-hit token-semantics note). 7 new tests green (`CodeLexicalToolTests`). Docs weave: spec quick-chooser + Code Navigation entry + decision-table row; AGENTS.md tool list/chooser/backstop; seed-211 + rendered guru.md tool pointer; seed-180 exploration order slot 8; guru template (`render_agent_surfaces.py`) + all five local `.claude/agents` allowlists; `wave_sync_surfaces` clean. Live AC-5 probe: `code_lexical_response(query="code_lexical_response", table="code")` returns the function's own definition at rank 1 (bm25 −5.47) with exact coverage attached. | `server_impl.py`; `test_server_tools.py::CodeLexicalToolTests` (7 OK); spec/AGENTS/seed diffs; live probe output. |
| 2026-07-12 | Verification complete: full suite 4,854 OK — five consecutive clean passes; two earlier intermittent test_indexer failures reproduced ONLY while concurrent live index builds ran on this machine (the code-index recovery `--rechunk` and post-edit-hook reindexes) and never in quiescent runs — machine-contention flake, not a code defect (no traceback captured; watch item). `wave_validate` clean; `server.py --dry-run` OK with 73 tool registrations including `code_lexical`. Separately: the AC-5 live-probe work EXPOSED a major pre-existing staleness defect cluster (code edits invisible to the code index; `content=code` update a no-op recovery) — root-caused and ticketed as `1sek8-bug content-scoped-builds-poison-code-index-freshness` (docs/plans, NOT in this wave); this repo's index recovered via `--content code --rechunk`. | Suite logs (5× OK); dry-run output; `1sek8` change doc with full source-line evidence. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-11 | No regex/FTS-syntax passthrough — the safe literal-quoting query builder is reused unchanged. | FTS5 cannot regex (inverted index); exposing raw MATCH syntax invites injection-shaped breakage the fusion path deliberately closed; regex has a dedicated tool. | **Raw MATCH passthrough:** weakness — hostile-syntax errors and operator surprises for marginal power. **LIKE/regex table scan:** weakness — full scan, strictly worse than `code_pattern` on live files. |
| 2026-07-11 | Ship in 1.12.0 via late admission to wave 1sbfk rather than post-release. | Operator-directed; the tool is a thin wrapper over shipped, field-verified store machinery, and the release retest already validated that machinery — incremental risk is the wrapper, which is fully unit-tested. | **Post-1.12 wave:** weakness per operator priority — field agents diagnosing lexical issues need it with the release that fixed the layer. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Response bloat on prevalent tokens | limit cap 50 + per-result text cap + `text_truncated` flag. |
| Agents route semantic queries here | Docstring routing discipline + seed-180 exploration-order placement (after `code_keyword`). |
| New tool invisible until reconnect | Known host behavior, documented; `wave_mcp_reload` sends the tool-list-changed notification. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
