# Chunk Tags — Multi-Label Retrieval Axis

Change ID: `12dv9-enh chunk-tags`
Change Status: `draft`
Owner: Engineering
Status: draft
Last verified: 2026-05-05
Wave: `12dv9 chunk-tags`

## Rationale

Search results are currently classified along a single axis: `kind` (`doc`, `doc-summary`, `code`, `code-summary`, `prompt`, `seed`). This is sufficient for broad filtering but leaves no way to express cross-cutting concerns — a lifecycle prompt is findable as `kind="prompt"` but not as "lifecycle-related", a wave doc is findable as `kind="doc"` but not as "wave-related". Agents must either omit filters (returning noisy results) or rely entirely on embedding similarity to surface the right material.

The PageIndex filesystem research (2025) introduced "virtual nodes" — labels that let content be reachable via multiple ancestor paths simultaneously. Adapted to Wavefoundry's offline, embedding-based model, the same idea becomes a `tags` list on each `Chunk`: a small controlled vocabulary of classification labels inferred at index time from path-pattern heuristics. No LLM call is required; no project configuration is required.

With `tags` populated, `docs_search` and `code_search` gain an optional `tags` filter parameter. A CIA agent looking for lifecycle-related docs can call `docs_search(query, tags=["lifecycle"])` and get tightly scoped results on the first pass. A `wave` tag makes all wave records and change docs reachable together. An `agent` tag surfaces all agent prompts and journals regardless of their `kind`.

The tag vocabulary is conservative — only labels that are directly inferable from path patterns without any heuristic ambiguity. Additions are safe post-ship; removals are breaking.

## Requirements

1. `Chunk` dataclass gains a `tags: list[str]` field (default empty list). `to_dict` must include it; deserialization must handle missing `tags` key (old index compatibility).
2. A `_infer_tags(path: str) -> list[str]` function in `chunker.py` returns a list of zero or more tags for a given file path, using the controlled vocabulary defined below.
3. Every `Chunk` produced by the chunker receives tags inferred from its path. Tags are the same for all chunks from the same file.
4. Controlled tag vocabulary (initial set):

   | Tag | Path pattern(s) |
   |-----|-----------------|
   | `wave` | `docs/waves/` subtree |
   | `agent` | `docs/prompts/agents/` or `docs/agents/` subtree |
   | `lifecycle` | path is under `docs/` AND contains `lifecycle`, `install`, or `onboarding` |
   | `reference` | `docs/references/` subtree |
   | `journal` | `docs/agents/journals/` subtree |
   | `prompt` | `docs/prompts/` subtree (any) **or** filename ends with `.prompt.md` (anywhere) |
   | `seed` | `.wavefoundry/framework/seeds/` subtree |
   | `framework` | `.wavefoundry/framework/` subtree |
   | `test` | path contains `/tests/` or `/test/`, OR filename matches `test_*.py`, `*_test.go`, `*.test.ts`, `*.test.js`, `*.spec.ts`, `*.spec.js` |
   | `config` | extension is `.yaml`, `.yml`, `.toml`, `.env`, or filename matches `.env.*` |

5. Tags may be empty (`[]`) — no forced assignment when no pattern matches.
6. A single file may receive multiple tags (e.g., a seed file gets both `seed` and `framework`).
   Note: `prompt` and `seed` tags intentionally overlap with `kind="prompt"` and `kind="seed"` on `docs_search`. The tags add value because they also work on `code_search` (cross-index) and compose with other tags (e.g., `tags=["prompt", "agent"]`).
7. `docs_search` gains an optional `tags: list[str]` parameter; results are filtered to chunks where the intersection of `chunk.tags` and the requested tags is non-empty. If `tags` is empty or omitted, behavior is unchanged. When both `kind` and `tags` are provided, both filters apply (AND semantics — a chunk must satisfy both).
8. `code_search` gains the same optional `tags: list[str]` parameter with the same AND semantics relative to the existing `language` and `kind` filters.
9. `CHUNKER_VERSION` must be incremented to trigger a full index rebuild.
10. Existing tests must continue to pass. New tests must cover tag inference and tag filter behavior.

## Scope

**In scope:**
- `Chunk` dataclass in `.wavefoundry/framework/scripts/chunker.py` — add `tags` field, update `to_dict`
- `_infer_tags(path: str) -> list[str]` helper in `chunker.py`
- All `Chunk(...)` construction sites in `chunker.py` — pass `tags=_infer_tags(path)`
- `CHUNKER_VERSION` increment
- `WaveIndex.search_docs` and `WaveIndex.search_code` in `.wavefoundry/framework/scripts/server.py` — add `tags` filter parameter
- `docs_search_response` and `code_search_response` in `server.py` — thread `tags` parameter through to index methods
- MCP tool schemas in `server.py` — add `tags` as optional array parameter for both search tools
- Deserialization in `.wavefoundry/framework/scripts/indexer.py` or wherever chunks are loaded from JSON — handle missing `tags` key gracefully (default to `[]`)
- Tests in `.wavefoundry/framework/scripts/tests/test_chunker.py` — tag inference cases
- Tests in `.wavefoundry/framework/scripts/tests/test_server.py` (if it exists) or equivalent — tags filter behavior

**Out of scope:**
- LLM-based tag inference — path heuristics only
- Per-project tag configuration — controlled vocabulary is global
- Tag display in search result output — tags are filter inputs, not output annotations (for now)
- Changes to `kind` values or `_doc_matches_kind` logic
- Reindexing existing projects (happens automatically on next `setup_index.py` run due to `CHUNKER_VERSION` bump)

## Affected Architecture Docs

N/A — chunker and server implementation only.

## Acceptance Criteria

| AC | Description |
|----|-------------|
| AC-1 | `Chunk` dataclass has a `tags: list[str]` field |
| AC-2 | `Chunk.to_dict()` includes `"tags"` key |
| AC-3 | Loading a chunk dict without a `"tags"` key (old index) does not raise an error — `tags` defaults to `[]` |
| AC-4 | `_infer_tags` returns `["wave"]` for a path under `docs/waves/` |
| AC-5 | `_infer_tags` returns `["agent", "prompt"]` for a path under `docs/prompts/agents/` |
| AC-6 | `_infer_tags` returns `["journal", "agent"]` for a path under `docs/agents/journals/` |
| AC-7 | `_infer_tags` returns `["seed", "framework"]` for a path under `.wavefoundry/framework/seeds/` |
| AC-8 | `_infer_tags` returns `["prompt"]` for any file whose name ends with `.prompt.md`, regardless of location |
| AC-9 | `_infer_tags` returns `["test"]` for a path matching test file conventions (`test_*.py`, `*_test.go`, `/tests/`, `*.spec.ts`, etc.) |
| AC-10 | `_infer_tags` returns `["config"]` for `.yaml`, `.yml`, `.toml`, `.env`, `.env.*` files |
| AC-11 | `_infer_tags` returns `[]` for a path that matches no pattern |
| AC-12 | A file may receive more than one tag |
| AC-13 | All Chunk construction sites pass `tags=_infer_tags(path)` |
| AC-14 | `docs_search` accepts optional `tags` parameter; results filtered when tag list is non-empty |
| AC-15 | `code_search` accepts optional `tags` parameter; results filtered when tag list is non-empty |
| AC-16 | Passing `tags=[]` or omitting `tags` returns unfiltered results (no behavior change) |
| AC-17 | MCP tool schema for `docs_search` documents `tags` as optional array of strings |
| AC-18 | MCP tool schema for `code_search` documents `tags` as optional array of strings |
| AC-19 | `CHUNKER_VERSION` is incremented |
| AC-20 | All existing tests pass |
| AC-21 | New tests cover: `_infer_tags` for each tag in the controlled vocabulary, multi-tag assignment, no-match path, `.prompt.md` anywhere gets `prompt`, tags filter narrows results, empty tags filter returns all results |
| AC-22 | Framework test suite passes |

## AC Priority

| AC | Priority | Rationale |
|----|----------|-----------|
| AC-1 through AC-3 | required | Dataclass and serialization foundation; backward compat required for existing indexes |
| AC-4 through AC-13 | required | Tag inference correctness — these are the core behavior |
| AC-14 through AC-18 | required | Search filter integration — the primary user-facing value |
| AC-19 | required | Without version bump, existing indexes won't rebuild |
| AC-20 through AC-22 | required | Non-regression and explicit coverage |

## Tasks

1. Add `tags: list[str] = field(default_factory=list)` to `Chunk` dataclass
2. Update `Chunk.to_dict()` to include `"tags": self.tags`
3. Add `_infer_tags(path: str) -> list[str]` to `chunker.py` with full controlled vocabulary
4. Update all `Chunk(...)` construction sites in `chunker.py` to pass `tags=_infer_tags(path)`
5. Update chunk deserialization (wherever `Chunk` objects are reconstructed from stored JSON) to use `.get("tags", [])` 
6. Add `tags` filter parameter to `WaveIndex.search_docs` and `WaveIndex.search_code`
7. Thread `tags` through `docs_search_response` and `code_search_response` in `server.py`
8. Update MCP tool schemas for `docs_search` and `code_search` to advertise `tags` parameter
9. Increment `CHUNKER_VERSION`
10. Add tests for `_infer_tags` and tags filter behavior
11. Run `python3 .wavefoundry/framework/scripts/run_tests.py`

## Decision Log

| Date | Decision | Reason | Alternatives |
|------|----------|--------|--------------|
| 2026-05-05 | Path heuristics only, no LLM | Wavefoundry's index build is fully offline; LLM calls at index time are out of scope | Could call LLM to classify chunks — breaks offline model and adds latency |
| 2026-05-05 | Tags as filter inputs, not output annotations | Keeps the search API surface minimal; annotating results would require UI changes and adds noise to current tool output | Could add tags to result dicts — useful for debugging, can be added later |
| 2026-05-05 | Conservative initial vocabulary (10 tags: 8 doc-centric + test/config) | Tag vocabulary is part of the public tool contract; additions are safe, removals break agent prompts and CIA guidance — better to ship narrow and extend | Could infer topic tags from content (tech, architecture, etc.) — ambiguous, LLM-dependent |
| 2026-05-05 | `prompt` tag triggers on `.prompt.md` suffix anywhere, not just `docs/prompts/` subtree | Prompt files may live in project-specific locations; the suffix is the authoritative signal for prompt identity | Could restrict to `docs/prompts/` only — would miss prompt files outside that path |
| 2026-05-05 | `test` tag uses filename pattern matching, not just directory | Test files may not be in a `tests/` directory (e.g., co-located test files in Go, Jest); filename pattern is more universal | Could require `tests/` directory only — too restrictive for polyglot projects |
| 2026-05-05 | `script` tag excluded from initial vocabulary | The `/bin/` and `/scripts/` directory patterns are too project-convention-dependent; `.sh`/`.bash` files are already handled by `language` filter; no clear agent use case for isolating scripts in the current tool surface | Could add in a follow-up wave if a use case emerges |
| 2026-05-05 | No `api`, `routes`, `middleware` tags in initial vocabulary | These depend on per-project naming conventions and cannot be inferred reliably from path alone; wrong inference is worse than no tag | Could add with a broad heuristic — false positives would make the filter unreliable |
| 2026-05-05 | Any-intersection filter semantics (OR across requested tags) | Most agent use cases are "give me things tagged X" not "give me things tagged X and Y simultaneously"; AND semantics would be too narrow for the initial vocabulary | Could require all requested tags to match — too restrictive for multi-tag files |
| 2026-05-05 | `tags` and `kind`/`language` filters compose with AND semantics | Each filter is an independent narrowing pass; combining them with OR would make `kind` and `tags` redundant with each other; AND matches user mental model ("prompt chunks that are also agent-related") | Could make composition configurable — adds API surface with no clear demand |
| 2026-05-05 | `lifecycle` tag restricted to `docs/` subtree and excludes `setup` keyword | `setup` matches `setup.py`, `setup_index.py`, `setup.cfg` — code files with no lifecycle meaning; restricting to `docs/` prevents false positives across the entire code index | Could use `lifecycle` keyword alone — too broad; `setup` keyword alone never reliably means lifecycle |
| 2026-05-05 | Tags same for all chunks from same file | Simplifies inference; path is the only reliable signal; intra-file tag variation would require content-level classification | Could vary tags by chunk kind within a file — adds complexity with no clear benefit at current vocabulary size |
