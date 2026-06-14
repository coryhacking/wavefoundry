# Chunking and Indexing Pipeline

Owner: Engineering
Status: active
Last verified: 2026-06-13

This document describes how Wavefoundry builds and maintains its search indexes. It covers
every stage of the pipeline: file discovery, change detection, chunking, embedding, and
storage. The intended audience is a developer who is new to the system.

---

## Overview

```
Repository files
      |
      v
  walk_repo()           -- respects .gitignore / .wavefoundryignore
      |
      v
  Filter & split        -- prefix filters separate framework vs. project files
      |
      +---> Framework layer    /.wavefoundry/framework/index/
      |
      +---> Project layer      /.wavefoundry/index/
                |
                v
        _detect_changes()     -- stat cache, then SHA-256 on cache miss
                |
                v
          Chunking             -- markdown, code, plain-text, notebooks
                |
                v
          Embedding            -- docs model / code model (768-dim each)
                |
                v
          Provider selection   -- CUDA, verified CoreML, named secondary provider, or CPU
                |
                v
          LanceDB write        -- chunk-delta update or full overwrite
                |
                v
          Index build          -- HNSW vector index + FTS (BM25)
                |
                v
          meta.json update
```

---

## Two Index Layers

Wavefoundry maintains two independent search indexes that are built and stored separately.

**Framework layer** covers seeds and framework documentation. Its artifacts live at
`/.wavefoundry/framework/index/`.

**Project layer** covers the project's own source code and documentation. Its artifacts live at
`/.wavefoundry/index/`.

Each layer contains two Lance tables: `docs` and `code`. The layers use separate embedding
models so that framework and project content can be versioned independently.

---

## Stage 1: File Discovery

`walk_repo(root)` walks the repository tree and collects every file that is not excluded by
`.gitignore` or `.wavefoundryignore`. After the walk, three filters narrow the list:

1. **`_filter_by_prefixes`** — keeps only paths that start with a configured
   `include_prefixes` list. This is the primary mechanism for telling Wavefoundry which
   directories belong to docs vs. code.

2. **`_filter_project_index_excludes`** — removes `.wavefoundry/framework/` from the project
   layer by default, so framework files are not double-indexed. This default can be overridden
   by setting `indexing.project_include_prefixes.docs` or
   `indexing.project_include_prefixes.code` inside `docs/workflow-config.json`.

3. **`_filter_framework_pack_artifacts`** — used only when building the framework layer;
   strips packaging artifacts that should not appear in search results.

The output of this stage is two lists of absolute file paths: one for docs files and one for
code files, each scoped to the appropriate layer.

**Hard size guard (wave 1p5c4).** During the walk, any file whose size exceeds
`indexing.max_file_bytes` (default 5 MB) is skipped entirely — never read, never parsed — and
logged once. This stops a pathologically large file (e.g. a multi-GB SQL backup) from being read
into memory and handed to tree-sitter, which would spin the indexer. A separate, smaller
**tree-sitter parse cap** (`indexing.max_treesitter_parse_bytes`, default 2 MB) is published to
the chunker and graph extractor via `WAVEFOUNDRY_MAX_TS_PARSE_BYTES`: a code file over that cap is
still indexed as plain-text chunks but skips the AST parse (and graph extraction), degrading to the
regex/line fallback instead of spinning. Set either key to `0` to disable that cap.

---

## Stage 2: Change Detection

Running a full embed-and-store cycle on every file at every build would be slow. The change
detection step determines which files actually need to be re-processed.

`_detect_changes(files, root, old_meta)` applies a two-stage filter:

### Stat cache (cheap)

For each file, the OS-level metadata is compared against the values stored in `meta.json`
from the previous build: `mtime` (modification time), `size`, and `inode` number. If all
three match, the file is considered unchanged and is skipped without reading its contents.

### SHA-256 hash (on cache miss)

If any stat field differs, the file is read and hashed with SHA-256. The hash is compared
against the stored value. The file is only marked as changed if the hash also differs. This
handles cases where mtime is updated without the content actually changing (for example, a
`git checkout` or a `touch` command).

### Results

`_detect_changes` returns three sets:

- **`changed_paths`** — files whose content has changed (new hash differs from stored hash)
- **`removed_paths`** — files present in the old metadata but missing from the current file list
- **`current_file_meta`** — updated stat+hash records for all current files

From `changed_paths` and the old metadata keys, two further sets are derived:

- **`added`** = `changed_paths` minus the set of previously known paths (new files)
- **`updated`** = `changed_paths` intersected with the set of previously known paths

### Forced full rebuild

A full rebuild is triggered automatically when any of the following values differ from
the stored `meta.json`:

- The embedding model name or version
- `CHUNKER_VERSION` (currently `"29"`) — bumped whenever the chunk format changes
- `WALKER_VERSION` (currently `"5"`) — bumped when the file-walk logic changes

On a forced rebuild, change detection is bypassed and every file is re-processed.

---

## Stage 3: Chunking

Chunking converts a file into a list of small, semantically coherent text units. Each unit
carries enough context to be useful as a standalone search result.

Implementation lives in `.wavefoundry/framework/scripts/chunker.py`. The indexer calls
`chunk_file(content, rel_path)` and routes each chunk to the `docs` or `code` Lance table
by `kind` (see below).

### Chunk metadata

Every chunk includes:

| Field | Purpose |
|-------|---------|
| `text` | Embedded and searched (may be collapsed for very large symbol bodies) |
| `path` | Repo-relative source file path |
| `kind` | Routes to docs vs code table and signals chunk role |
| `section` | Breadcrumb, e.g. `file_stem > ClassName > method` |
| `language` | Canonical language name for `code_search(language=...)` (code paths) |
| `lines` | 1-based `(start, end)` line range in the source file |
| `id` | Stable key, e.g. `path::QualifiedName` or `path#L10-L80` |
| `chunk_hash` | Index-row fingerprint for fields that affect retrieval semantics; used for chunk-level vector reuse |

**Chunk kinds:**

| `kind` | Lance table | Typical source |
|--------|-------------|----------------|
| `doc` | `docs` | Markdown prose, docstrings, HTML/XML element text |
| `doc-summary` | `docs` | One file-level summary per markdown doc |
| `seed` / `prompt` | `docs` | Framework seeds and `docs/prompts/` (special markdown rules) |
| `code` | `code` | Source declarations, config blocks, Makefile rules |
| `code-summary` | `code` | File-level symbol list + module comment (many languages) |

### Dispatch (`chunk_file`)

`chunk_file` selects a chunker from the file extension and path (seeds, prompts, design JSON,
extensionless `Makefile`, secrets files, etc.). For most code extensions the order is:

1. **Tree-sitter** — if the grammar is installed and parsing succeeds
2. **Regex / AST fallback** — language-specific regex chunker or Python `ast`
3. **Line window** — `chunk_line_window` (120-line windows, logical break points)

Tree-sitter grammars are **optional at runtime**: missing wheels log a one-time warning per
language and step down to regex or line-window chunking. `setup_index.py` lists all grammar
packages in `REQUIRED_IMPORTS` so a normal install pulls them into the tool venv.

### Markdown chunking (`chunk_markdown`)

Markdown files are split at heading boundaries, not at a fixed character count.

1. **Primary heading detection** — `_detect_primary_heading_level` scans the document. If
   any `##` headings exist, `##` is used as the split boundary. Otherwise `###` is used.

2. **Section splitting** — each top-level section becomes one chunk. The document's H1 title
   is injected into every chunk's text so that embeddings carry document-level context even
   when the chunk comes from the middle of the file.

3. **Sub-section splitting** — long sections that contain `###` sub-headings are split
   further, subject to a length threshold. This prevents very long sections from producing
   oversized chunks.

4. **Code block extraction** — fenced code blocks inside sections are pulled out as
   separate `kind="code"` chunks. The surrounding prose remains as a `kind="doc"` chunk.

5. **Breadcrumbs** — the `section` field is set to `"Document Title > Section Name"`.

Other text formats use dedicated chunkers:
- **Plain text** — `chunk_plain_text` applies a simpler line-based strategy.
- **Secrets/env files** — `chunk_secrets_file` handles `KEY=VALUE` formats.
- **Jupyter notebooks** — each cell is treated as its own chunk.

### Code chunking

Code files are split at **declaration or block boundaries** where possible, not at fixed
character counts. Three parsing strategies apply:

| Strategy | Used for | Mechanism |
|----------|----------|-----------|
| **Python `ast`** | `.py` | `chunk_python` — classes, functions, module/method docstrings |
| **Tree-sitter AST** | See table below | Walk parse tree; optional regex fallback per language |
| **Line window** | Remaining indexed extensions | `chunk_line_window` — 120 lines per window (`WINDOW_SIZE`) |

**Module-/type-level constants are chunked** (wave 1p4mf, all 11 languages): each named module- or
type-level constant produces its own `" [const]"`-marked, breadcrumb-prefixed chunk so a constant's
NAME and VALUE are independently retrievable (`RERANKER_MODEL` → its `"BAAI/bge-reranker-base"`
value). Detection is per-language by real mechanism + scope (the keyword/grammar node + an
ancestor gate to module/file/type top level), **never** a uniform `UPPER_SNAKE` casing filter —
camelCase/PascalCase/MixedCaps constants (Swift `apiURL`, C# `MaxRetries`, Go `StatusOK`) are
included and function/block locals are excluded by scope. Casing gates apply for Python only.

#### Tree-sitter installation

- Runtime: `tree-sitter>=0.24,<0.26` (pinned in `setup_index.py`)
- Grammars: individual `tree-sitter-{language}` wheels (offline; no `tree-sitter-language-pack`)
- Entry point: `_ts_parse(lang_key, source)` in `chunker.py` — returns `None` if grammar missing or parse fails

#### Tree-sitter chunking modes

1. **Structured** (`_ts_generic_structured_chunker`) — classes, methods, imports, namespaces.
   Used for Swift, ObjC, Scala, Ruby, PHP, PowerShell, and the original JS/TS/Go/Rust/Java/C/C#/Kotlin/Bash set.
2. **Flat config** (`_ts_flat_emit_chunker`) — one chunk per top-level block/attribute/pair.
   Used for HCL (`.tf`, `.hcl`), YAML, TOML, JSON, CSS, SCSS, Makefile rules.
3. **Markup** (`_ts_markup_chunker`) — shallow `element` nodes.
   Used for HTML and XML (fallback: landmark-regex `chunk_html` / `chunk_xml`).

#### Post-processing (all structured tree-sitter paths)

- **`_merge_small_chunks`** — sub-2-line code chunks merge into predecessor (scoped merge inside classes for tree-sitter)
- **`split_large_code_chunks`** — `kind="code"` chunks over `MAX_CODE_CHUNK_CHARS` (4000) split into sub-ranges
- **`_ts_collapse_body`** — symbol bodies over ~150 lines collapse to signature + `// ... N lines ...` + closing line
- **`_chunk_code_summary`** — optional file-level `code-summary` chunk prepended when symbols or module comment exist

#### Language coverage (tree-sitter → fallback)

| Language | Extensions | PyPI grammar | Tree-sitter entry | Fallback |
|----------|------------|--------------|-------------------|----------|
| TypeScript / JS | `.ts`, `.tsx`, `.js`, `.jsx`, `.mjs`, `.cjs`, `.mts`, `.cts` | `tree-sitter-typescript`, `tree-sitter-javascript` | `chunk_js_ts_treesitter` | `chunk_js_ts` |
| Go | `.go` | `tree-sitter-go` | `chunk_go_treesitter` | `chunk_go` |
| Rust | `.rs` | `tree-sitter-rust` | `chunk_rust_treesitter` | `chunk_rust` |
| Java | `.java` | `tree-sitter-java` | `chunk_java_treesitter` | `chunk_java` |
| Kotlin | `.kt`, `.kts` | `tree-sitter-kotlin` | `chunk_kotlin_treesitter` | line window |
| C / C++ | `.c`, `.h`, `.cpp`, `.hpp`, … | `tree-sitter-c`, `tree-sitter-cpp` | `chunk_c_cpp_treesitter` | `chunk_c_cpp` |
| C# | `.cs` | `tree-sitter-c-sharp` | `chunk_csharp_treesitter` | `chunk_csharp` |
| Bash | `.sh`, `.bash`, `.zsh` | `tree-sitter-bash` | `chunk_bash_treesitter` | `chunk_shell` |
| SQL | `.sql`, `.psql`, … | `tree-sitter-sql` | `_chunk_sql_treesitter` (in `chunk_sql`) | regex `chunk_sql` |
| Swift | `.swift` | `tree-sitter-swift` | `chunk_swift_treesitter` | `chunk_swift` |
| Objective-C | `.m`, `.mm` | `tree-sitter-objc` | `chunk_objc_treesitter` | `chunk_objc` |
| Scala | `.scala` | `tree-sitter-scala` | `chunk_scala_treesitter` | `chunk_scala` |
| Ruby | `.rb` | `tree-sitter-ruby` | `chunk_ruby_treesitter` | line window |
| PHP | `.php` | `tree-sitter-php` | `chunk_php_treesitter` | line window |
| PowerShell | `.ps1`, `.psm1` | `tree-sitter-powershell` | `chunk_powershell_treesitter` | line window |
| Terraform / HCL | `.tf`, `.hcl` | `tree-sitter-hcl` | `chunk_hcl_treesitter` | line window |
| YAML | `.yaml`, `.yml` | `tree-sitter-yaml` | `chunk_yaml_treesitter` | line window |
| TOML | `.toml` | `tree-sitter-toml` | `chunk_toml_treesitter` | line window |
| JSON | `.json`, `.jsonc` | `tree-sitter-json` | `chunk_json_treesitter` | line window |
| CSS | `.css` | `tree-sitter-css` | `chunk_css_treesitter` | line window |
| SCSS | `.scss` | `tree-sitter-scss` | `chunk_scss_treesitter` | line window |
| Makefile | `Makefile`, `GNUmakefile` | `tree-sitter-make` | `chunk_make_treesitter` | line window |
| HTML | `.html`, `.htm` | `tree-sitter-html` | `chunk_html_treesitter` | `chunk_html` |
| XML | `.xml`, `.jsp`, … | `tree-sitter-xml` | `chunk_xml_treesitter` | `chunk_xml` |

**Python** — always `chunk_python` (`ast`); syntax errors fall back to line window.

**No tree-sitter path today:**

| Case | Behavior |
|------|----------|
| `.fish` shell | `chunk_shell` (regex) |
| `.sass` | line window |
| `.tfvars`, `.env` | `chunk_secrets_file` (keys indexed, values redacted) |
| Helm `.tpl`, batch `.bat`/`.cmd` | line window via `CODE_EXTENSIONS` |
| Extensionless `Dockerfile`, `Jenkinsfile`, … | line window (except `Makefile` → make grammar) |

#### Doc comments with code

Many structured chunkers emit **two** chunks per symbol when a doc comment exists:

- `kind="code"` — declaration body (possibly collapsed)
- `kind="doc"` — docstring / `///` / `/** */` only (stored in the **docs** table)

Breadcrumb format: `file_stem > ClassName > method_name`. Import blocks may appear as
`file_stem > imports`.

#### Change history note

Wave `12c86` introduced the tree-sitter chunker set (JS/TS through Kotlin/SQL). Wave `12pn3`
change `12qf3-enh tree-sitter-swift-objc-and-regex-replacements` extended coverage to Swift,
ObjC, Scala, config/markup languages above, and bumped `CHUNKER_VERSION` to `"21"`.

Wave `1p4q4` (and its review) extends constant chunking into TypeScript enums and
namespaces: each `enum` / `const enum` / `export enum` **member** becomes its own
`Enum.Member` constant chunk, and each namespace-scoped `const` (export and non-export)
becomes a `Namespace.CONST` constant chunk. The `module M{}` keyword form, `export namespace`,
`declare namespace`, `declare enum`, and `declare const` are all chunked. `CHUNKER_VERSION`
is now `"29"`. The same wave makes `.mts` / `.cts` **first-class** across the main pipeline —
they are added to the chunker `JS_TS_EXTENSIONS` set and the indexer `SOURCE_CODE_EXTENSIONS`
set, both mapped to TypeScript, so these files are walked, chunked, and indexed like any
other `.ts` source.

---

## Stage 4: Embedding

Chunks are converted to dense vectors using ONNX-based sentence-transformer models. Two
separate models are used — one per content type — both producing 768-dimensional vectors:

| Table  | Model (current in `indexer.py`) | Dimensions |
|--------|----------------------------------|------------|
| `docs` | `BAAI/bge-small-en-v1.5`         | 384        |
| `code` | `BAAI/bge-small-en-v1.5`         | 384        |

Both tables currently share the same symmetric model. Planned wave `12pn3` changes may swap
the code table to a code-specific model (e.g. `jina-embeddings-v2-base-code`) and/or upgrade
the docs model; when `CODE_MODEL` or `DOCS_MODEL` in `indexer.py` changes, `meta.json`
`model_versions` mismatch forces a full re-embed.

Docstrings and other `kind="doc"` chunks from source files are embedded with the **docs**
model even though they originate from `.py`, `.java`, etc.

### Provider Selection

`setup_index.py` and `indexer.py` share provider-selection policy through
`provider_policy.py`. The policy chooses ONNX Runtime execution providers in this order:

1. `CUDAExecutionProvider` for NVIDIA/CUDA when ONNX Runtime exposes it.
2. `CoreMLExecutionProvider` on Apple Silicon only after a bounded active-model probe produces
   valid embeddings and beats the CPU path by a material margin.
3. Named secondary ONNX providers such as `DmlExecutionProvider`, `OpenVINOExecutionProvider`,
   `MIGraphXExecutionProvider`, or `ROCMExecutionProvider`, only after explicit availability and
   model probing.
4. `CPUExecutionProvider` as the safe fallback.

There is intentionally no generic GPU provider tier. Each non-CPU provider has different package,
driver, and model-compatibility constraints, so setup diagnostics report the actual provider name
and fallback reason. On NVIDIA machines, setup plans the `fastembed-gpu` dependency path when local
`nvidia-smi` detection succeeds. If hardware is present but `CUDAExecutionProvider` is missing after
installation, setup keeps CPU execution and prints remediation guidance instead of failing the
index build.

### Sliding sort buffer

Embedding batches are assembled via a sliding sort buffer to minimise wasted computation
caused by padding in the ONNX runtime.

The buffer keeps a window of `SORT_WINDOW_SIZE` (2048) chunks. Within that window, chunks
are sorted by text length, and each batch of `EMBED_BATCH_SIZE` (256) chunks is drawn from
the shortest sequences available. This means sequences within a batch are similar in length,
reducing the amount of zero-padding needed to make them uniform — which reduces ONNX
inference time.

The entire chunk list is never loaded into memory at once. Vectors are written to LanceDB
incrementally after each batch completes.

Progress is reported as:

```
build_index: embedding docs chunks 1–256/1500
```

---

## Stage 5: LanceDB Write

LanceDB stores the chunks and their vectors. Each index layer has two tables: `docs` and
`code`. Writes follow different paths depending on whether the build is incremental or a full
rebuild.

### Incremental write

Incremental writes are file-scoped for change detection but chunk-scoped for embedding work.
For each stale path, the indexer reads existing LanceDB rows from the relevant table and
compares them with the freshly generated chunks:

1. **Read current rows** — existing rows are fetched by `path` from the `docs` and/or `code`
   table, including vectors.
2. **Classify chunks** — new chunks are matched against existing rows by stable `id` plus
   `chunk_hash`. Unchanged chunks keep their existing row. Changed, added, removed, and
   ambiguous chunks are identified per path.
3. **Reuse vectors where safe** — when chunk text and retrieval-relevant metadata are
   unchanged, no embedding call is made. If the vector is reusable but row metadata such as
   `lines`, `section`, or `id` changed, the row is rewritten with current metadata and the
   reused vector.
4. **Embed only the delta** — only added or changed chunks are sent to the embedder.
5. **Delete and append** — removed/changed old rows are deleted by `id`; changed/new rows
   are appended. If existing rows lack compatible `chunk_hash` metadata, the path falls back
   to the previous delete-all-for-path replacement behavior.

Line-window fallback chunks are treated conservatively because their IDs include line ranges.
When matching is ambiguous, correctness wins and the affected chunk is re-embedded.

### Full rebuild

On a forced rebuild, the first batch is written with `mode="overwrite"`, which replaces the
entire table. Subsequent batches use `.add()` to append to the now-empty table.

### Index creation

After all rows have been written, two secondary indexes are created if the total row count
reaches `LANCEDB_INDEX_THRESHOLD` (1000 rows):

- **HNSW** — approximate nearest-neighbour vector index, used for semantic search queries.
- **FTS (Tantivy/BM25)** — full-text search index, used for keyword queries.

Below the threshold, queries fall back to a brute-force scan, which is fast enough at small
scale and avoids the overhead of index construction on near-empty tables.

---

## Stage 6: Finish and Metadata Update

When all tables have been written and indexed, the build emits a summary line per built layer:

```
build_index: finished docs — 0 added, 4 updated, 46 removed | chunks: 0 added, 164 updated, 0 removed
build_index: finished code — 3 added, 1 updated, 0 removed | chunks: 12 added, 5 updated, 0 removed
```

The file-level counts (`3 added, 1 updated`) reflect source files processed. The chunk-level
counts reflect rows written to or removed from LanceDB.

`meta.json` is then updated with:

| Field              | Contents                                              |
|--------------------|-------------------------------------------------------|
| `file_meta`        | Stat cache: mtime, size, inode, and SHA-256 per file  |
| `model_versions`   | Names/versions of the embedding models used           |
| `chunker_versions` | The `CHUNKER_VERSION` value at build time             |
| `walker_version`   | The `WALKER_VERSION` value at build time              |
| `built_at`         | ISO 8601 timestamp of the completed build             |

On the next incremental build, `_detect_changes` reads this file to determine what has
changed since the last run.

---

## Key Constants

| Constant                  | Value  | Effect of change                                 |
|---------------------------|--------|--------------------------------------------------|
| `CHUNKER_VERSION`         | `"29"` | Forces full rebuild of the affected layer        |
| `WALKER_VERSION`          | `"5"`  | Forces full rebuild of all layers                |
| `WINDOW_SIZE`             | 120    | Line-window fallback window (lines per chunk)    |
| `WINDOW_OVERLAP`          | 10     | Reserved; structured fallbacks often advance without overlap |
| `MAX_CODE_CHUNK_CHARS`    | 4000   | Triggers sub-split of oversized `kind="code"` chunks |
| `CHUNK_MIN_LINES`         | 2      | Minimum code chunk size before merge             |
| `EMBED_BATCH_SIZE`        | 256    | Affects throughput only                          |
| `SORT_WINDOW_SIZE`        | 2048   | Affects padding efficiency only                  |
| `LANCEDB_INDEX_THRESHOLD` | 1000   | Below: brute-force scan; at/above: HNSW+FTS used |

Whenever `CHUNKER_VERSION` is bumped — for example because a breadcrumb format changes or a
new tree-sitter language is added — every file in the affected layer is re-chunked and
re-embedded on the next build. The same applies when the embedding model name changes.

An index whose existing LanceDB rows predate `chunk_hash` triggers a one-time **full rebuild**
automatically (the 1p4n4 legacy-fallback preflight) so rows carry `chunk_hash` consistently
before chunk-level vector reuse applies; you can also force it (e.g.
`python3 .wavefoundry/framework/scripts/setup_wavefoundry.py --full` or `wave_index_build`
with full mode).

---

## Configuration Reference

`docs/workflow-config.json` controls which paths are included in each index table.

```json
{
  "indexing": {
    "project_include_prefixes": {
      "docs": ["docs/", "README.md"],
      "code": ["src/", "lib/"]
    }
  }
}
```

Setting `project_include_prefixes.docs` and `project_include_prefixes.code` tells
`_filter_project_index_excludes` which paths to treat as project content. Without these
keys, the defaults apply: `.wavefoundry/framework/` is excluded from the project layer, and
all other paths passing `.gitignore` rules are eligible.
