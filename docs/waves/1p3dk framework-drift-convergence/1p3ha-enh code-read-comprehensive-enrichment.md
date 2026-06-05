# code_read Comprehensive Enrichment

Change ID: `1p3ha-enh code-read-comprehensive-enrichment`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-05
Wave: TBD

## Rationale

The `code_read` MCP tool today returns line-numbered file content and three metadata fields (`path`, `start_line`, `end_line`, `total_lines`). It does its job — but in the read-then-edit workflow that agents actually run, it leaves significant friction on the table:

1. **Internal I/O is wasteful on large files.** `code_read_response` (server_impl.py:8186) calls `resolved.read_text()` — slurps the entire file regardless of the requested range. Reading 10 lines of a 15745-line file (`server_impl.py` itself) reads all 15745 lines. The fix is straightforward: use `itertools.islice` over the line iterator and stop at `end_line + 1`.

2. **Response payload carries forced overhead.** The `"%5d\t"` line-number prefix is always emitted, adding ~6 bytes per line. For agents using `code_read` to extract content for regex matching, JSON parsing, or any non-line-numbered use case, the prefix is noise that must be stripped — but they've already paid the bytes-on-wire cost.

3. **The follow-on `Read()` call is repeated guesswork.** Because the built-in `Read` tool (which satisfies the harness's "must read before Edit" precondition) requires absolute paths and accepts `offset`/`limit`, every read-then-edit flow requires the agent to: (a) reconstruct the absolute path from the repo-relative path `code_read` returned, (b) calculate `limit = end_line - start_line + 1`, (c) reissue effectively the same read against the same file. We could hand the agent the exact invocation in the original response.

4. **Edit boundary safety is invisible until after the Edit fails.** When an agent reads lines 100-110 to inspect a partial function body and then edits, the framework currently provides no hint that the function actually spans lines 95-130 and the edit risks mangling closing structure. Tree-sitter parses already power `code_definition` and `code_outline` — the same parse can flag "your range starts mid-construct" or "the smallest clean edit boundary covering your range is lines 95-130."

5. **Edit governance gates are discovered the hard way.** `.wavefoundry/framework/seeds/` requires the `seed_edit_allowed` gate; `.wavefoundry/framework/scripts/` requires `framework_edit_allowed`; `docs/design-system/` may require `design_system_edit_allowed` per policy. Agents routinely forget to open the gate, attempt Edit, get bounced by the post-edit hook, then have to back up and open the gate. Surfacing the gate requirement at read time prevents the wall-bounce.

6. **Renderer-owned marker regions look like editable content.** `<!-- waveframework:* begin --> ... <!-- end -->` blocks in `CLAUDE.md`, `.cursor/rules/auto-guru.mdc`, etc. are rewritten on every `render_platform_surfaces.py` invocation. An agent who edits inside the markers loses the work on the next render. `code_read` could flag these spans when they overlap the requested range.

7. **No per-call cache.** Navigation-heavy flows read the same file multiple times in quick succession. Each call pays full I/O + parse cost.

This change turns `code_read` from "give me text" into "give me text and everything the agent needs to do an informed Edit in one round-trip plus one targeted Read." Internal-efficiency wins (1, 2, 7) and follow-on-tool effectiveness wins (3, 4, 5, 6) are bundled because they share the same response surface and the same code path — splitting them creates redundant ceremony around a single function.

## Requirements

1. **Range-aware streaming read.** When `start_line` or `end_line` is provided, the implementation reads at most `end_line + 1` lines from the file (the `+1` is to detect `has_more`). The full file is read only when both bounds are unset.
2. **Optional line-number prefix.** A new parameter `with_line_numbers: bool = True` controls the `"%5d\t"` prefix. Default `True` preserves existing behavior; passing `False` returns raw lines joined with `\n`.
3. **Backwards-compat `total_lines` semantics.** `total_lines` is returned only when the call read the whole file (no bounds, or `end_line` reached EOF). For mid-file partial reads, `total_lines` is omitted and `has_more: bool` is returned instead.
4. **Follow-on Read invocation hint.** The response includes `read_invocation` carrying `{file_path: <absolute>, offset: <start_line>, limit: <end_line - start_line + 1>, satisfies_edit_precondition_for_range: true}`. The agent can pass these three fields directly to the built-in `Read` tool to satisfy Edit's read-first precondition with minimal re-read.
5. **Absolute path surfaced.** `absolute_path` field returns the resolved absolute path (already computed internally via `_resolve_repo_path`).
6. **File metadata surfaced.** `mtime` (ISO-8601 UTC timestamp) and `size_bytes` returned for staleness detection and paging decisions. `is_binary` returned when the read failed UTF-8 decoding with replacement characters present in critical density.
7. **Edit governance hint.** When the resolved path falls under a known gated area, `edit_governance` returns `{requires_gate: <name>, current_state: "open"|"closed", open_with: "wave_gate_open(gate=<name>)"}`. Gate detection map (initial): `.wavefoundry/framework/seeds/*` → `seed_edit_allowed`; `.wavefoundry/framework/scripts/*` → `framework_edit_allowed`; `.wavefoundry/framework/dashboard/*` → `framework_edit_allowed`. The current gate state is read from `.wavefoundry/guard-overrides.json` (the same source `wave_gate_status` consults). Omitted entirely for paths not under a gated area.
8. **Marker region detection.** When the requested range overlaps `<!-- waveframework:* begin --> ... <!-- end -->` blocks, `marker_regions` returns a list of `{name, start_line, end_line, warning}` entries. `warning` is a fixed string: `"renderer-owned region; edits will be overwritten on next render_platform_surfaces.py invocation"`. Detected via line-by-line scan with a marker-state machine (the same pattern `check_deprecated_role_references` uses). Returned as `marker_regions: []` (empty list) when none overlap — keeps the field always present for shape consistency.
9. **Structural block via tree-sitter.** When the file extension matches a language supported by the existing tree-sitter integration (`.py`, `.js`, `.ts`, `.tsx`, `.java`, `.cs`, `.go`, `.rs`, `.kt`, `.swift`, `.cpp`, `.c`, `.bash`, `.sql`), `structural` returns:
   - `containing_symbol`: the smallest symbol whose range fully contains the requested range, with `{name, kind, start_line, end_line, complete_in_range: bool}`. `complete_in_range` is `false` when the requested range is a strict subset of the symbol — a hint to the agent to expand before editing.
   - `range_analysis`: `{starts_mid_construct: bool, ends_mid_construct: bool, construct_kind_at_start: str | null, construct_kind_at_end: str | null, suggested_clean_range: [start, end] | null}`. The "suggested_clean_range" is the smallest tree-sitter AST node range that fully contains the requested range — i.e., "the safe edit boundary."
   - Omitted entirely (no `structural` field) for non-code files, files where tree-sitter parse failed, or files larger than a configurable budget (default 500KB).
10. **Tree-sitter parse cache with mtime invalidation.** A bounded in-process LRU cache (default 32 entries) stores `(file_path) → (mtime, parsed_tree, symbol_index)`. On lookup, the current file mtime is compared against the cached mtime. **Mismatch invalidates the entry and triggers a fresh parse.** This handles the case where the agent edits the file during the session: subsequent `code_read` calls see the new mtime, invalidate, and reparse against the current file state. Cache hits cost microseconds; misses cost the full parse time (~10-50ms typical).
11. **Cache scope.** The cache is process-local to the MCP server (no shared state across MCP-server-process boundaries). This is the same isolation model `_last_assigned_prefix` uses in `lifecycle_id.py`. Multi-process MCP setups each maintain independent caches; no inter-process invalidation is required because each agent talks to one server process at a time.
12. **Graceful degradation.** Every enrichment field is optional in the response surface. If tree-sitter parse fails, structural is omitted. If mtime fetch fails, mtime is omitted. If gate-state read fails, edit_governance returns `current_state: "unknown"` and surfaces an inline note. Existing callers reading only the previously-documented fields (`path`, `start_line`, `end_line`, `total_lines`, `content`) continue to work unchanged.
13. **Backward compatibility.** All existing tests pass without modification. The response shape is purely additive — no field removed, no field changed in meaning. `total_lines` is the one field whose presence/absence semantics shift (omitted on mid-file partial reads); existing callers that read it on full-file or EOF-reaching reads see the same behavior.
14. **Docstring updates.** The `code_read` tool docstring (visible via `tools/list`) explicitly documents: (a) the new fields, (b) the "does not satisfy Edit precondition" caveat (the cross-cutting tool-quality finding from session 2 of the MCP-dogfooding log), (c) the `read_invocation` hint as the recommended path to a follow-on `Read` call.

## Scope

**Problem statement:** `code_read` does its job but leaves significant value on the table in the read-then-edit workflow. Internal I/O is wasteful on large files; response payload carries forced overhead; the follow-on `Read` is repeated guesswork; edit-boundary safety, gate requirements, and renderer-owned regions are all invisible until after an Edit fails. This change bundles internal efficiency, response enrichment, and tree-sitter-powered structural awareness into one comprehensive enhancement.

**In scope:**

- `code_read_response` in `server_impl.py` — range-aware streaming, `with_line_numbers` parameter, all new response fields
- `code_read` MCP tool registration in `server_impl.py` — updated signature, docstring with new fields and Edit-precondition caveat
- Tree-sitter integration helpers — reuse the existing infrastructure that powers `code_definition` / `code_outline`; new module function for "smallest containing AST node" and "range overlap analysis"
- LRU cache module — small, focused, with mtime-based invalidation
- Edit-governance gate detection helper — path-prefix → gate name map; state read from `guard-overrides.json`
- Marker-region detection — reuses the line-by-line state-machine pattern from `check_deprecated_role_references`
- Tests in `test_server_tools.py` covering each new field, each tier, and the cache invalidation behavior
- CHANGELOG bullet describing the new response fields

**Out of scope:**

- Changes to other `code_*` MCP tools (`code_keyword`, `code_pattern`, `code_search`, etc.) — they have their own enrichment opportunities but warrant their own scoping
- Changes to the built-in `Read` tool (it's part of the Claude Code harness, not this framework)
- A harness-side fix for the Edit-precondition tracking gap (upstream — out of our scope per the previous session's analysis)
- A `code_read_batch` tool for reading multiple ranges in one call (orthogonal — could be a follow-on)
- New tree-sitter language support (this change uses whatever the existing integration supports)
- Streaming response chunks (the MCP transport doesn't support streaming in the current shape)

## Acceptance Criteria

- [x] AC-1: `code_read` with `start_line` and `end_line` set reads at most `end_line - start_line + 2` lines from the file (the +2 is for the start offset plus the `has_more` peek). Verified by mocking `Path.open()` and asserting the read count.
- [x] AC-2: `code_read` with no bounds reads the full file; behavior unchanged from current.
- [x] AC-3: Response includes `has_more: bool` for partial reads in the middle of a file; `has_more` is `false` when `end_line` reached EOF or beyond.
- [x] AC-4: Response includes `total_lines` only when the call read the full file (or when `end_line` >= actual EOF); omitted on mid-file partial reads.
- [x] AC-5: `code_read(with_line_numbers=False)` returns content without the `"%5d\t"` prefix. Each line is the raw file line text, joined with `\n`.
- [x] AC-6: `code_read(with_line_numbers=True)` (default) preserves the existing prefix behavior exactly. No existing test that asserts the prefix format requires modification.
- [x] AC-7: Response includes `absolute_path` field carrying the resolved absolute path (matches `_resolve_repo_path` output).
- [x] AC-8: Response includes `read_invocation: {file_path, offset, limit, satisfies_edit_precondition_for_range: true}` where `file_path == absolute_path`, `offset == start_line`, `limit == end_line - start_line + 1`. When the read was a full-file read with no bounds, `offset` is 1 and `limit` is `total_lines`.
- [x] AC-9: Response includes `mtime` as ISO-8601 UTC string and `size_bytes` as int. When the stat call fails, both are omitted.
- [x] AC-10: When the path falls under `.wavefoundry/framework/seeds/`, response includes `edit_governance: {requires_gate: "seed_edit_allowed", current_state: <state>, open_with: "wave_gate_open(gate='seed_edit_allowed')"}` where `current_state` is read from `.wavefoundry/guard-overrides.json`.
- [x] AC-11: When the path falls under `.wavefoundry/framework/scripts/` or `.wavefoundry/framework/dashboard/`, response includes `edit_governance` with `requires_gate: "framework_edit_allowed"`.
- [x] AC-12: When the path falls under no gated area, `edit_governance` is omitted entirely.
- [~] AC-13: When `guard-overrides.json` is missing or unreadable, `current_state` is `"unknown"`. **Partial — `"unknown"` state is implemented (defensive exception catch in `_edit_governance_for_path`); explicit diagnostic note field on `edit_governance` deferred to a follow-up.** The `"unknown"` state itself is the actionable signal — agents see ambiguity at read time and can probe with `wave_gate_status` to resolve.
- [x] AC-14: When the requested range overlaps a `<!-- waveframework:* begin --> ... <!-- end -->` block, response includes `marker_regions: [{name, start_line, end_line, warning}]`. `warning` matches the exact string specified in Requirement 8.
- [x] AC-15: When no marker regions overlap, `marker_regions: []` (empty list, not omitted).
- [x] AC-16: For a `.py` file, `structural.containing_symbol` returns the smallest symbol whose range fully contains the requested line range. Python uses stdlib `ast` via the shared cache; tree-sitter-supported languages use `chunker._ts_parse` via the shared cache. Verified by `test_structural_returns_containing_symbol_for_python_function`.
- [x] AC-17: When the requested range is a strict subset of the containing symbol, `structural.containing_symbol.complete_in_range == false`. When the range exactly equals or supersets the symbol, `complete_in_range == true`. Verified by `test_structural_complete_in_range_when_range_covers_symbol` and the partial-range assertion in `test_structural_starts_mid_construct_when_range_partial`.
- [x] AC-18: `structural.range_analysis.starts_mid_construct == true` when the requested `start_line` falls inside an AST node that started earlier. Verified by `test_structural_starts_mid_construct_when_range_partial`.
- [x] AC-19: `structural.range_analysis.suggested_clean_range == [<start>, <end>]` is the containing symbol's range. Test asserts `[1, 5]` for a partial read of a 5-line function. Operator passes these as new `start_line`/`end_line` to expand to a clean boundary.
- [x] AC-20: For a non-code file (`.md`, `.json`), `structural` is omitted from the response entirely. Verified by `test_structural_omitted_on_markdown` and `test_structural_omitted_on_json`.
- [x] AC-21: For a code file larger than 500KB, `structural` returns a `note` field (`"file_too_large_for_structural_parse"`) with `size_bytes` and `budget_bytes` for operator visibility. Verified by `test_structural_returns_note_when_file_too_large` (builds a ~700KB Python file via mocked content).
- [x] AC-22: Tree-sitter cache returns the same `containing_symbol` on two consecutive calls reading the same file with no mtime change, without re-parsing. Verified by mocking the parser and asserting it's called exactly once.
- [x] AC-23: When the file is edited (mtime advances) between two `code_read` calls, the cache is invalidated and the parser is called a second time. Verified by mocking mtime to advance and asserting a fresh parse.
- [x] AC-24: Cache size is bounded; when it exceeds 32 entries, the least-recently-used entry is evicted. Verified by reading 33 different files and asserting the first-read entry is no longer cached.
- [x] AC-25: Existing `code_read` tests (`test_code_read_rejects_absolute_path`, `test_code_read_rejects_traversal`, `test_code_read_rejects_missing_file`) pass without modification.
- [x] AC-26: Tool docstring (visible via `tools/list`) documents the new fields, the Edit-precondition caveat ("`code_read` does NOT satisfy Edit/Write's read-first precondition; use `read_invocation` to call the built-in `Read` tool when planning to subsequently edit"), and the `read_invocation` recommendation.
- [x] AC-27: CHANGELOG bullet under `## [1.5.0]` describes the new fields and the Edit-precondition guidance.
- [x] AC-28: Full framework test suite passes (additional ~30 tests).
- [x] AC-29: docs-lint clean.

## Tasks

- [x] Open `framework_edit_allowed` gate
- [x] Refactor `code_read_response` to use `itertools.islice` over `open()` for partial reads; preserve full-file behavior for unbounded reads
- [x] Add `with_line_numbers: bool = True` parameter; thread through to response formatting
- [x] Add `absolute_path`, `mtime`, `size_bytes`, `has_more` fields; preserve `total_lines` for full-file/EOF reads
- [x] Add `read_invocation` field with the structured Read-call hint
- [x] Add `_edit_governance_for_path(root, resolved) -> dict | None` helper; consult guard-overrides.json
- [x] Add `_marker_regions_in_range(text, start, end) -> list[dict]` helper using the line-state-machine pattern
- [x] Add `_treesitter_cache` module (or section) with LRU + mtime-keyed invalidation
- [x] Add `_structural_for_range(absolute_path, start, end) -> dict | None` helper that consults the cache, parses on miss, returns containing_symbol + range_analysis
- [x] Update the `code_read` MCP tool registration: new parameter, expanded docstring (including Edit-precondition caveat)
- [x] Add ~30 tests covering each AC; reuse existing fixture patterns
- [x] Update CHANGELOG under `## [1.5.0]`
- [x] Run framework test suite
- [x] Run docs-lint
- [x] Close `framework_edit_allowed` gate

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| streaming-read | implementer | — | itertools.islice refactor; AC-1, AC-2, AC-3, AC-4 |
| response-shape | implementer | streaming-read | New fields: absolute_path, mtime, size_bytes, has_more, read_invocation; AC-5–AC-9 |
| governance-hint | implementer | response-shape | edit_governance detection + state read; AC-10–AC-13 |
| marker-regions | implementer | response-shape | Line-state-machine scan; AC-14, AC-15 |
| structural-block | implementer | response-shape | Tree-sitter integration + LRU cache; AC-16–AC-24 |
| docstring | docs-contract-reviewer | response-shape | Tool description update; AC-26 |
| tests | qa-reviewer | streaming-read, response-shape, governance-hint, marker-regions, structural-block | ~30 new tests covering all ACs |

## Serialization Points

- All implementation work touches `server_impl.py` — single-file change for the bulk of the code. Tree-sitter cache could be its own module (`tree_sitter_cache.py`) under `.wavefoundry/framework/scripts/` to keep the cache and its tests modular; recommended.
- The five workstreams above can land in any order after `streaming-read` lays the foundation, since they're additive response fields. Sequence implementation as: streaming-read → response-shape → (governance-hint || marker-regions || structural-block in parallel) → docstring → tests.

## Affected Architecture Docs

`N/A` for the boundary-level docs (no new modules, no new architectural seams). May warrant a one-line note in `docs/specs/mcp-tool-surface.md` describing the new fields on `code_read`'s response; assess during implementation.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Streaming partial read is the headline internal-efficiency win. |
| AC-2 | required | Full-file path must remain unchanged. |
| AC-3 | required | `has_more` is the replacement signal for `total_lines` on partial reads. |
| AC-4 | required | `total_lines` semantics shift must be precise. |
| AC-5 | required | `with_line_numbers=False` enables zero-overhead text reads. |
| AC-6 | required | Default behavior unchanged is the backward-compat contract. |
| AC-7 | required | `absolute_path` is the foundation of `read_invocation`. |
| AC-8 | required | `read_invocation` is the load-bearing Edit-precondition mitigation. |
| AC-9 | important | mtime/size are useful but not load-bearing. |
| AC-10 | required | seed_edit_allowed gate is the most-tripped gate in this framework. |
| AC-11 | required | framework_edit_allowed is the second-most-tripped gate. |
| AC-12 | required | Omission on non-gated paths prevents noise. |
| AC-13 | important | Graceful degradation when guard-overrides.json is missing. |
| AC-14 | important | Marker-region detection prevents wasted Edit work. |
| AC-15 | important | Empty list (vs omission) is shape-consistency. |
| AC-16 | required | containing_symbol is the structural foundation. |
| AC-17 | required | complete_in_range is the agent's "expand before edit" signal. |
| AC-18 | required | starts_mid_construct is the edit-boundary safety check. |
| AC-19 | important | suggested_clean_range is the actionable next step on a mid-construct hit. |
| AC-20 | required | No tree-sitter parse on non-code files. |
| AC-21 | required | File-size budget prevents pathological parse costs. |
| AC-22 | required | Cache must actually cache. |
| AC-23 | required | mtime invalidation is the load-bearing in-session-edit correctness check. |
| AC-24 | important | LRU bound prevents unbounded memory growth. |
| AC-25 | required | Existing tests must pass. |
| AC-26 | required | Docstring is the discoverability surface for the new fields. |
| AC-27 | required | CHANGELOG bullet. |
| AC-28 | required | Suite must pass. |
| AC-29 | required | docs-lint must pass. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-05 | Change scaffolded; comprehensive design written up. Wave admission decision pending operator direction. | This doc |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-05 | Bundle internal-efficiency, response-enrichment, and structural-awareness into a single change rather than three separate changes | All five tiers touch `code_read_response` and share the same response surface. Splitting forces three separate test passes against the same function, three separate CHANGELOG bullets describing the same shape, and three council passes for what's structurally one design. The cost of bundling is a larger change doc; the cost of splitting is redundant ceremony. | (a) Land Tier 1 (streaming + line numbers) only — rejected; leaves the Edit-precondition Read-hint value unaddressed when it's the highest-impact item per operator framing. (b) Land Tier 1 + Tier 2 (response enrichment) and defer Tier 3 (tree-sitter) — viable; recorded as a fallback if council review judges Tier 3 too large. |
| 2026-06-05 | LRU cache keyed on `(file_path)`, value `(mtime, parsed_tree, symbol_index)`, invalidated on mtime mismatch | Per operator directive ("include LRU with mtime check in case the agent edits the file during the session"). The mtime mismatch IS the in-session-edit invalidation signal. No need for explicit invalidation API or cross-process coordination — each MCP server process owns its cache, and Edits happen through tools that change the file's mtime, which the next `code_read` sees. | (a) Cache keyed on `(path, mtime)` directly — rejected; means the cache always misses on edits (which is correct) but also can't detect that we have a stale entry to evict. The current proposal evicts on mtime change. (b) Time-bounded TTL — rejected; doesn't model the agent's actual edit cadence; could miss edits that happen faster than TTL. |
| 2026-06-05 | Structural block uses graph-index lookup when available, fresh tree-sitter parse when not | The graph index is already tree-sitter-derived. A point-in-range query against it is essentially free. Fresh parse is reserved for files not in the index or when the graph layer is stale. | (a) Always fresh parse — rejected; adds ~10-50ms per call when the index already has the answer. (b) Always graph index — rejected; graph staleness on un-indexed changes would surface wrong symbol boundaries; fresh parse is the fallback. |
| 2026-06-05 | `with_line_numbers=True` is the default | Backwards compat. Existing callers and existing tests rely on the prefix format. Changing the default would force every caller to migrate. | Default to `False` — rejected; backward incompatibility. |
| 2026-06-05 | `total_lines` omitted on mid-file partial reads, replaced with `has_more: bool` | The internal-efficiency win of streaming requires not reading past `end_line + 1`. Returning `total_lines` would force a full file read; defeating the streaming win. `has_more` is the minimum signal the agent needs to decide whether to page. | (a) Read to EOF to compute total_lines unconditionally — rejected; defeats streaming. (b) Return `total_lines: null` instead of omitting the field — would work; omission is the project convention for absent metadata (compare gate-state omission on non-gated paths). |
| 2026-06-05 | Edit-precondition caveat documented in tool docstring rather than embedded in every response | Docstring is the discoverability surface; embedding the caveat in every response would be repetitive noise. The `read_invocation` field is the actionable per-response counterpart to the docstring's general note. | (a) Embed in every response — rejected; redundant. (b) Embed only on first call per process — rejected; complicates the response surface for marginal benefit. |
| 2026-06-05 | `structural` block omitted entirely on non-code files instead of returning `null` | Project convention is omission for absent enrichments (matches gate-state omission, mtime-fetch-failure omission). Keeps the response surface clean. | Return `structural: null` — rejected; convention is omission. |
| 2026-06-05 | 500KB file-size budget for tree-sitter parse | Tree-sitter parse time grows roughly linearly with file size; ~50ms on 500KB is the rough cost on the test machine. Beyond that, the cost becomes user-noticeable for navigation flows. The budget is configurable via a constant; can be tuned. | (a) No budget — rejected; pathological files would block. (b) Hard error on oversized files — rejected; graceful degradation (omit the field, add a `note`) preserves the rest of the response. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Tree-sitter parse cost adds noticeable latency to `code_read` calls on first-touch of a file | LRU cache hits on repeat reads; for first-touch on small-to-medium files (~< 100KB), parse is < 20ms. Budget of 500KB caps the worst case. If field telemetry shows this is a problem, the budget can be tightened or `structural` can become opt-in via parameter. |
| LRU cache memory growth across agent sessions | Bounded at 32 entries by default. Each entry holds a parsed tree (typically 100KB-1MB for a code file) — worst case ~32MB. Acceptable for an MCP server process. Configurable. |
| `read_invocation` hint encourages the agent to skip `code_read` entirely and only use `Read` | This is the intended use when `code_read`'s structural enrichment isn't needed. The agent should use `code_read` when they want the enrichment, `Read` when they don't. The hint makes the chain easier; it doesn't change which tool is right for which case. |
| `edit_governance` gate state read races with concurrent `wave_gate_open`/`wave_gate_close` calls | The gate state is a hint, not a binding contract. The actual Edit will be blocked by the post-edit hook if the gate is closed; surfaced state is a courtesy. Race window is tiny (state read is one fopen + json parse). Acceptable. |
| Tree-sitter cache returns stale results if mtime is unchanged but content changed (e.g., touch with no edit, then real edit also using touch) | Filesystem `mtime` is reliable enough for this use case. Editors and the framework's own write tools all advance mtime on write. The edge case of an operator-edit-then-touch-back-to-old-mtime is implausible. |
| Backward-compat regressions from `total_lines` omission | Existing tests assert `total_lines` on full-file reads only. Mid-file partial-read tests don't exist (the current implementation reads the whole file anyway, so existing partial-read tests happen to get `total_lines` — but no test asserts it specifically on a partial read). Verified by reading the existing test suite during implementation. |
| The change is large enough (~180 LOC + ~30 tests) that bundling it into a single change risks scope explosion | The bundling decision is recorded above. If during implementation any tier reveals unexpected complexity, the fallback is to split off Tier 3 (tree-sitter + cache) as a separate change. Recorded explicitly in the Decision Log. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state. Change doc scaffolded 2026-06-05 in response to operator directive ("write these changes up as a comprehensive enhancement to code_read"). Awaiting wave-admission decision before implementation begins.
