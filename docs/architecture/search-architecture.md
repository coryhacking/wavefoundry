# Search Architecture

Owner: Engineering
Status: active
Last verified: 2026-05-03

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
Layer 3: Symbol navigation — code_definition, code_references
```

They are ordered from broadest to narrowest:

| Layer | Input | Output | When to use | Always available? |
|-------|-------|--------|-------------|-------------------|
| Semantic | Natural language query | Ranked relevant chunks | Orientation, discovery, "find something like X" | No — requires model cache |
| Exact | Literal text substring | File path + line + snippet | Known keyword, function name, exact string | Yes — always |
| Symbol | Symbol name or position | Definition/reference locations | Jump-to-definition, find-all-references | Partial — Python only |

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

### Decision 6: Symbol navigation starts Python-only with explicit unsupported responses

Language-aware symbol navigation (jump-to-definition, find-references) requires parsing, which requires language-specific infrastructure. Rather than shipping a degenerate implementation that works partially for many languages, the initial scope is deliberately narrow:

- **Python**: AST-based, using `ast.walk()` to find `FunctionDef`, `AsyncFunctionDef`, and `ClassDef` nodes by name. Reliable and dependency-free.
- **Other languages**: explicit `"unsupported language"` response with a `code_keyword_search` fallback hint.

The alternative — shipping "best effort" regex-based symbol lookup for many languages — produces subtly wrong results that agents may trust. An explicit unsupported response is more useful than a wrong answer.

Future expansion (tree-sitter, LSP integration) is a natural extension of this layer without changing the public tool API.

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
  "kind":     "doc | seed | python | ...",
  "language": "python | null",
  "lines":    [start_line, end_line],
  "section":  "Header text or null",
  "text":     "chunk text — what was embedded"
}
```

The `text` field is what was embedded. The `path` and `lines` fields are what the agent sees in results. Keeping the two separate means the embedded text can be a normalized or chunked version of the file without changing what's reported back.

---

## Relationship to Other Architecture Docs

- **`embedding-model.md`** — the specific model choice, its properties, regression tests, and upgrade procedure
- **`data-and-control-flow.md`** — the runtime control paths for index build and MCP query calls
- **`current-state.md`** — the deployed MCP topology, including which tools belong to each search layer
