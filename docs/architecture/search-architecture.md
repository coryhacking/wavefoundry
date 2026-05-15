# Search Architecture

Owner: Engineering
Status: active
Last verified: 2026-05-14

## The Problem

Agents navigating a project through Wavefoundry's MCP server face two distinct retrieval problems:

**Discovery**: "I don't know where this is documented" — finding relevant docs, prompts, or code without knowing the exact filename or keyword. A query like "how do I start a wave?" should surface the prepare-wave prompt even though that doc uses the word "prepare," not "start." Lexical search fails here; semantic similarity handles it.

**Navigation**: "I know what I'm looking for, find it exactly" — reading a specific file, searching for a known function name, jumping to a definition. Semantic search is worse than useless here: it introduces noise, requires a model to be available, and is non-deterministic. An exact grep is better in every way.

These are different enough problems that they warrant different tools. Trying to solve both with a single approach (pure semantic, pure lexical, or pure AST) produces a system that handles neither well.

---

## The Three-Layer Model

The MCP search surface is organized into three layers, each solving a narrower and more precise version of the navigation problem:

```
Layer 1: Semantic search   — docs_search, code_search
Layer 2: Exact navigation  — code_keyword_search, code_read, code_list_files
Layer 3: Symbol navigation — code_definition, code_references, code_dependencies
Layer 4: Codebase Q&A      — code_ask
```

They are ordered from broadest to narrowest:

| Layer | Input | Output | When to use | Always available? |
|-------|-------|--------|-------------|-------------------|
| Semantic | Natural language query | Ranked relevant chunks | Orientation, discovery, "find something like X" | No — requires model cache |
| Exact | Literal text substring | File path + line + snippet | Known keyword, function name, exact string | Yes — always |
| Symbol | Symbol name or position | Definition/reference locations; import graph | Jump-to-definition, find-all-references, dependency tracing | Partial — Python AST; other languages use keyword fallback |
| Codebase Q&A | Natural language question | Grounded answer with citations | Open-ended questions spanning multiple files | No — requires semantic index |

The layering matters because agents should reach for the narrowest tool that fits the task. Using semantic search to find a function you know the name of is slower, less reliable, and wastes tokens. Using exact keyword search to find documentation about a concept you can't name exactly is fruitless.

---

## Design Decisions

### Decision 1: Offline-first semantic search

The MCP server runs embedded inside the IDE process. Network calls during agent sessions are unacceptable — they introduce latency spikes, fail silently in restricted environments, and make query results non-deterministic across sessions. The embedding model must run fully locally.

This is the constraint that shapes everything about Layer 1:
- The model is pre-cached by `setup_index.py` (explicit setup step, network allowed)
- All queries use `local_files_only=True` and `HF_HUB_OFFLINE=1`
- The model choice (`BAAI/bge-base-en-v1.5`) was driven in part by reliable offline support in fastembed
- When the model is unavailable, the system falls back to lexical search rather than failing

See `docs/architecture/embedding-model.md` for the model choice rationale.

### Decision 2: Transparent fallback, not silent degradation

When semantic search is unavailable, `docs_search` automatically falls back to `search_docs_lexical`. The response always includes `data.mode: "semantic" | "lexical"` so agents know which path they got. This matters because the quality difference is significant — an agent acting on lexical results as if they were semantic results may miss the right document entirely.

The fallback is intentional rather than accidental: a useful-but-lower-quality answer is better than an error. But it must be transparent.

### Decision 3: No external search service

A vector database (Pinecone, Weaviate, Chroma, etc.) would offer richer query features, filtering, and scaling. It was rejected because:

1. **Wavefoundry is a local developer tool.** There is no server to host an external service, and requiring one would make installation significantly more complex.
2. **The corpus is small.** A Wavefoundry docs corpus tops out at a few thousand chunks. Cosine search over a float32 numpy matrix is fast enough at this scale that query latency is dominated by model embedding time, not the search itself.
3. **Operational simplicity beats features.** A `.npy` file and a `.json` file can be inspected, deleted, and rebuilt with a single command. A running database process cannot.

The current implementation is explicitly designed to be replaceable. The `WaveIndex` class encapsulates the semantic search path; `search_docs` and `search_code` are the only entry points. If the corpus grows to a size where numpy cosine search is measurably slow, swapping in a vector DB behind those methods is straightforward.

### Decision 4: Two-layer index (project + framework)

The index merges two separate index layers at query time:

- **Project index** (`.wavefoundry/index/`) — built from the user's own docs, code, and seeds
- **Framework index** (`.wavefoundry/framework/index/`) — packaged with the framework, covers framework seeds and prompts

This separation exists because framework content is versioned and shipped in the framework zip, while project content changes with each doc edit. They have different rebuild triggers: project index is rebuilt by `setup_index.py` or the post-edit hook; framework index is rebuilt by `build_pack.py` when cutting a release. Merging them into a single index would require either rebuilding the framework index on every project doc edit or rebuilding the project index on every framework upgrade.

Layers are only merged if their vector dimensions and model names match. A mismatched layer is silently skipped rather than crashing — this is the safety net for partial upgrades and version mismatches between framework and project index builds.

### Decision 5: Exact navigation uses live file walks, not an index

`code_keyword_search`, `code_read`, and `code_list_files` operate directly on the filesystem rather than querying a pre-built index. This was a deliberate choice:

**Staleness is not acceptable for exact navigation.** An agent using `code_keyword_search` to find a function definition must get the current state of the file, not a cached state from the last index build. Doc search can tolerate some staleness; exact code navigation cannot.

**The cost is acceptable.** A `rg`-style substring walk over a typical repository is fast enough (milliseconds to low seconds) that the simplicity of no-index-required outweighs the marginal latency cost.

**It keeps the two concerns separate.** The semantic index is for concepts; the filesystem is for facts. Blurring this boundary would require the index to be rebuilt on every code edit and kept perfectly in sync — a reliability problem that adds complexity without benefit.

All file walks reuse the same ignore/exclusion rules as the indexer (`walk_repo()`, `.gitignore`, `.aiignore`, hardcoded excludes) to keep results consistent.

### Decision 6: Symbol navigation uses Python AST plus targeted tree-sitter-backed languages

Language-aware symbol navigation (jump-to-definition, find-references) benefits from parsing where available, but the tool surface does not need to wait for full LSP coverage. The implementation uses a tiered approach:

- **Python**: AST-based, using `ast.walk()` to find `FunctionDef`, `AsyncFunctionDef`, and `ClassDef` nodes by name. Reliable and dependency-free. Returns `method: "ast"`.
- **Tree-sitter-backed languages**: JavaScript, TypeScript, Java, and C# use the existing chunker parser stack for structural definitions and identifier-level references. Returns `method: "treesitter"` or per-result `treesitter_*`.
- **Additional supported definition languages**: Go, Rust, Kotlin, and Swift use structural regex matching for top-level symbols. Returns `method: "regex"`.
- **References across the remaining known code languages**: language-filtered text matching. Returns `method: "text"`.
- **Fallback**: broad repo keyword matching when no structural/text layer finds a result. Returns `method: "keyword_fallback"`.

These tiers keep one public tool API while making provenance explicit via the `method` field. Future tree-sitter or LSP upgrades can improve precision without changing the tool names or call shape.

### Decision 7: Orientation chunks (`code-summary`, `doc-summary`) enable fast first-pass retrieval

A full semantic search over all file chunks is expensive when the agent only needs to know which files are relevant. Two orientation chunk kinds solve this:

- **`kind="code-summary"`**: one chunk per source file — module docstring (or leading comment) + top-level symbol names (capped at 20). Produced by `_chunk_code_summary` in `chunker.py`; routes to the code index. Queried with `code_search(kind="code-summary")` to get a file-level orientation map without reading full source chunks.
- **`kind="doc-summary"`**: one chunk per markdown file — first non-heading paragraph + all H1/H2/H3 headings concatenated as `Sections: A · B · C`. Produced by `_chunk_doc_summary`; routes to the docs index (via `_is_docs_kind`). Queried with `docs_search(kind="doc-summary")` for documentation orientation.

Both kinds are prepended to their file's chunk list so they appear first in retrieval results when the query matches the file-level summary.

### Decision 8: `code_ask` does mechanical retrieval routing, not LLM synthesis

`code_ask` is a structured routing tool, not an LLM-in-the-loop summarizer. Given a question, it:

1. Classifies the question type (navigational / explanatory / instructional) using a keyword heuristic
2. Runs a broad semantic pass (`code_search` + `docs_search`)
3. If fewer than 2 citations, runs a keyword fallback pass (`code_keyword_search`)
4. Returns `{answer, citations, confidence, gaps, question_type, index_freshness}`

The `answer` field is mechanically assembled from the top citation — it names the file and line range, not a synthesized prose response. This is intentional: the tool is designed to be called by an agent that will read the cited sources and reason over them, not to replace that reasoning. Synthesis is the caller's job; retrieval and citation is `code_ask`'s job.

`confidence` is heuristic: `high` = 2+ citations, `medium` = 1 citation, `low` = 0. `index_freshness` is `"stale"` when any indexed chunker version differs from the current `CHUNKER_VERSION`.

### Decision 9: `max_per_file` cap in `code_search` for result diversity

Without a per-file cap, `code_search` can return many chunks from a single large file when that file dominates cosine similarity scores — useful for deep dives into one file, but unhelpful for orientation across the codebase. The `max_per_file` parameter caps how many chunks from the same file can appear in results. Order is: rank (cosine score descending) → language filter → kind filter → per-file cap → `[:top_n]`. The highest-scoring chunk per file is always retained when the cap is applied.

---

## Fallback Chain

The complete search fallback chain for `docs_search`:

```
1. docs_search(query)
     ↓
2. WaveIndex.search_docs()  [semantic: embed query → cosine search]
     ↓ if IndexNotReadyError or SemanticModelUnavailableOfflineError
3. WaveIndex.search_docs_lexical()  [lexical: token overlap over live chunks]
     ↓ if no results
4. Empty result set + diagnostics explaining what failed
```

At every step, the response data includes `mode: "semantic" | "lexical"` and diagnostics describing what triggered any fallback. Agents should check `mode` when reasoning about result completeness.

For code navigation (Layer 2 and 3), there is no fallback: the tools either return results or return a clear empty/unsupported response. This is intentional — exact and symbol navigation are not degraded by missing infrastructure, only by missing language support.

---

## Index Format

```
.wavefoundry/index/
  docs.npy       float32 matrix [n_chunks × dim]
  docs.json      list of chunk dicts, row-parallel with docs.npy
  code.npy       float32 matrix [n_code_chunks × dim]
  code.json      list of code chunk dicts
  meta.json      { model_versions, content, file_hashes, built_at }
```

**Chunk schema:**

```json
{
  "id":       "unique string",
  "path":     "repo-relative/path/to/file.md",
  "kind":     "doc | doc-summary | seed | prompt | code | code-summary | python | ...",
  "language": "python | null",
  "lines":    [start_line, end_line],
  "section":  "Header text or null",
  "text":     "chunk text — what was embedded"
}
```

The `kind` field now includes two orientation kinds:
- `code-summary` — file-level symbol index for source files; routes to code index
- `doc-summary` — heading index for markdown files; routes to docs index

The `text` field is what was embedded. The `path` and `lines` fields are what the agent sees in results. Keeping the two separate means the embedded text can be a normalized or chunked version of the file without changing what's reported back.

---

## Relationship to Other Architecture Docs

- **`embedding-model.md`** — the specific model choice, its properties, regression tests, and upgrade procedure
- **`data-and-control-flow.md`** — the runtime control paths for index build and MCP query calls
- **`current-state.md`** — the deployed MCP topology, including which tools belong to each search layer
- **`docs/agents/code-insight-agent.md`** — the CIA agent role doc: retrieval loop, citation format, confidence model, and per-agent usage guidance
