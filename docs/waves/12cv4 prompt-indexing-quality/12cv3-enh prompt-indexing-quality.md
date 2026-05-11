# Prompt Indexing Quality

Change ID: `12cv3-enh prompt-indexing-quality`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-05-04
Wave: `12cv4 prompt-indexing-quality`

## Rationale

Wavefoundry prompts are the primary agent navigation surface — agents rely on `docs_search` to find what commands exist, how to run lifecycle operations, and what guidance applies. Currently all `docs/` content shares `kind="doc"`, so a query for "how do I prepare a wave" competes against wave records, architecture docs, design system, and agent journals. There is no search scope that returns only runnable prompt guidance. Additionally, the markdown chunker fragments long prompt step sequences at `###` boundaries and extracts fenced code blocks away from their surrounding instructional prose — both of which reduce retrieval coherence for prompt content specifically.

## Requirements

1. **`kind="prompt"` for prompt files**: All `.md` files under `docs/prompts/` (including `docs/prompts/agents/`) must be chunked with `kind="prompt"`. The `chunk_markdown` dispatcher and `chunk_file` must support this.
2. **`docs_search` kind filter**: `docs_search` must accept `kind="prompt"` as a valid filter value, returning only prompt-kind chunks. Existing `kind="doc"` and `kind="seed"` filters must continue to work.
3. **No H3 re-splitting for prompt chunks**: When `kind="prompt"`, `chunk_markdown` must not re-split oversized `##` sections at `###` boundaries regardless of section size. Step sequences inside a single `##` section must remain a single chunk.
4. **No fenced code extraction for prompt chunks**: When `kind="prompt"`, `chunk_markdown` must not extract fenced code blocks as separate chunks. Code blocks stay inline with the surrounding prose.
5. **Exclude `prompt-surface-manifest.json` from indexing**: The file `docs/prompts/prompt-surface-manifest.json` is a machine-generated metadata artifact and must be excluded from both doc and code indexing. Add it to `HARDCODED_EXCLUDE_FILENAMES` in `indexer.py`.
6. **`seed_get` vs `docs_search` routing guidance**: Add a short routing note to `docs/prompts/index.md` (and a matching seed) explaining when agents should use `seed_get` (direct retrieval by known ID) vs `docs_search(kind="prompt")` (discovery when the exact prompt is unknown).
7. **Bump `CHUNKER_VERSION`**: Increment `CHUNKER_VERSION` in `chunker.py` after any change to chunk content or kind assignment, to force a full index rebuild.

## Scope

**Problem statement:** Prompt retrieval quality is degraded by three structural issues: (1) `kind="doc"` is shared with non-prompt docs making scoped search impossible; (2) `###` re-splitting fragments instructional step sequences; (3) fenced code extraction separates commands from the prose explaining when and why to run them.

**In scope:**

- `chunker.py`: new `PROMPT_PATH_MARKERS`, `kind="prompt"` assignment, H3 re-split disabled for prompts, fenced code extraction disabled for prompts, `CHUNKER_VERSION` bump
- `indexer.py`: `prompt-surface-manifest.json` added to `HARDCODED_EXCLUDE_FILENAMES`
- `server.py`: `docs_search` kind filter extended to accept `"prompt"`
- `docs/prompts/index.md`: routing note for `seed_get` vs `docs_search`
- Tests: `test_chunker.py` for `kind="prompt"` assignment and chunking behavior; `test_server_tools.py` for kind filter

**Out of scope:**

- Seeds — `kind="seed"` assignment and behavior unchanged
- Code search — no changes to code chunking or code index
- Embedding model — no change
- New MCP tools — no new tools added; only existing `docs_search` extended

## Acceptance Criteria

- AC-1: `chunk_file("# Title\n## Step 1\n...", "docs/prompts/foo.md")` returns chunks with `kind="prompt"`
- AC-2: `chunk_file("# Title\n## Step 1\n...", "docs/prompts/agents/foo.md")` returns chunks with `kind="prompt"`
- AC-3: A `##` section in a prompt file that exceeds 2000 chars and contains `###` headings is returned as a single chunk (not split)
- AC-4: A fenced code block inside a prompt file is not extracted as a separate chunk — it remains in the prose chunk
- AC-5: `docs_search(query="prepare wave", kind="prompt")` returns only `kind="prompt"` chunks
- AC-6: Existing `docs_search(kind="doc")` and `docs_search(kind="seed")` still return correct results
- AC-7: `prompt-surface-manifest.json` does not appear in any index layer
- AC-8: `docs/prompts/index.md` contains routing guidance for `seed_get` vs `docs_search`
- AC-9: `CHUNKER_VERSION` is incremented
- AC-10: All pre-existing framework tests pass

## Tasks

- [ ] Add `PROMPT_PATH_MARKERS` tuple to `chunker.py` (paths containing `docs/prompts/`)
- [ ] Update `chunk_file` to detect prompt path and set `kind="prompt"` before dispatching to `chunk_markdown`
- [ ] Add `kind_override` passthrough in `chunk_markdown` to suppress H3 re-splitting when `kind="prompt"`
- [ ] Add `kind_override` passthrough in `chunk_markdown` to suppress fenced code extraction when `kind="prompt"` — **apply to both call sites**: the preamble block and the standard section block each call `_extract_fenced_code` independently
- [ ] Decide and document the line-window fallback for oversized prompt `##` sections with no `###` headings (lines 666-672 in `chunk_markdown`): either suppress the fallback for prompts (keeping the whole section as one chunk regardless of size), or explicitly accept it with a rationale note. The H3-suppression requirement (AC-3) implies suppression is the intent, but the change doc does not address this path.
- [ ] Restructure `_doc_matches_kind` in `server.py`: move `kind == "prompt"` handling **before** the `if chunk_kind != "doc": return False` early-exit so prompt-kind chunks are not silently blocked; remove the now-dead path-based branch (`normalized_path.startswith("docs/prompts/")`). The existing path-based branch works today (filtering on `kind="doc"` chunks by path) but will return zero results after prompt chunks gain their own kind.
- [ ] Add `prompt-surface-manifest.json` to `HARDCODED_EXCLUDE_FILENAMES` in `indexer.py`
- [ ] Add routing note to `docs/prompts/index.md`
- [ ] Bump `CHUNKER_VERSION`
- [ ] Add tests to `test_chunker.py`: kind assignment, no H3 split, no code extraction for prompts (both preamble and standard sections), line-window fallback decision
- [ ] Add test to `test_server_tools.py`: `kind="prompt"` filter returns only prompt chunks; `kind="doc"` does not return prompt chunks (non-regression)

## Agent Execution Graph

| Workstream       | Owner       | Depends On    | Notes                                               |
| ---------------- | ----------- | ------------- | --------------------------------------------------- |
| chunker          | Engineering | —             | PROMPT_PATH_MARKERS, kind="prompt", H3 + code flags |
| indexer-exclude  | Engineering | —             | manifest.json exclusion — independent of chunker    |
| server-filter    | Engineering | chunker       | kind="prompt" filter needs kind assigned at index   |
| docs-routing     | Engineering | —             | docs/prompts/index.md note — independent            |
| tests            | Engineering | chunker, server-filter | test_chunker.py + test_server_tools.py    |

## Serialization Points

- `chunk_file` dispatch is a single-author surface — chunker and server-filter workstreams must coordinate on kind values before server filter is implemented.

## Affected Architecture Docs

- `docs/architecture/embedding-model.md`: note that `kind="prompt"` is now a valid chunk kind alongside `"doc"`, `"seed"`, `"code"`

## AC Priority

(Populated at Prepare wave.)

| AC    | Priority | Rationale |
| ----- | -------- | --------- |
| AC-1  | required | Core kind assignment |
| AC-2  | required | Agent sub-prompts must also be kind="prompt" |
| AC-3  | required | Prevents step-sequence fragmentation |
| AC-4  | required | Keeps instructional prose coherent |
| AC-5  | required | Primary user-facing improvement |
| AC-6  | required | Non-regression |
| AC-7  | required | Exclude noisy artifact |
| AC-8  | important | Improves agent routing, not blocking |
| AC-9  | required | Forces rebuild after kind change |
| AC-10 | required | Non-regression gate |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
|      |        |          |

## Decision Log

| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-05-04 | Suppress H3 re-split entirely for prompts rather than raising threshold | Step sequences in prompts should not be fragmented regardless of size; a higher threshold is still fragmentation-prone | Raise H3_SPLIT_THRESHOLD_CHARS for prompts only (rejected: still allows fragmentation on very long steps) |
| 2026-05-04 | Keep fenced code inline for prompts | Commands shown in prompt docs are instructional — their value is the surrounding context; separate code chunks lose that | Extract code separately (rejected: severs command from its explanation) |
| 2026-05-04 | Extend existing docs_search kind filter rather than adding a new prompt_search tool | One fewer MCP tool surface; kind filter already handles doc/seed distinction cleanly | New prompt_search tool (rejected: unnecessary surface growth) |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Prompt files with very large `##` sections become oversized chunks | Maximum chunk char limit still applies; collapse body if needed; prompt `##` sections are typically well-scoped |
| Kind filter change in server.py breaks existing agent queries using kind=doc | AC-6 non-regression test covers this; kind filter is additive |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
