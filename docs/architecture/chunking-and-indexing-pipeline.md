# Chunking and Indexing Pipeline

Owner: Engineering
Status: active
Last verified: 2026-07-06

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
  Filter                -- prefix filters; the `.wavefoundry/` blanket is excluded
      |                    (framework seeds + README fold into the docs table)
      v
  Project index         -- /.wavefoundry/index/   (docs + code tables)
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

## The Project Index

Wavefoundry maintains a **single** semantic index — the project index — stored at
`/.wavefoundry/index/`. It contains two Lance tables: `docs` and `code`.

There is no separately built or shipped "framework" index. Before wave `1p4ww` the framework
seeds/docs were embedded into their own layer at `/.wavefoundry/framework/index/` and packaged in
the distribution; that layer was **eliminated** (ADR `1p4xx`). Distributions now ship framework
**source only**, and the framework's seeds + top-level `README` are **folded into the project
`docs` table** at setup/upgrade (this is the `WALKER_VERSION` 6 change) so the framework methodology
is searchable from any consumer project. Any leftover `/.wavefoundry/framework/index/` from an old
install is a deprecated artifact that the upgrade removes.

The rest of `.wavefoundry/` (framework scripts, operational docs, dashboard, install/release) is
framework-internal and excluded from a consumer project's index by default. The Wavefoundry
repository's own self-hosting case re-includes the framework subpaths it needs (e.g.
`.wavefoundry/framework/scripts`) via `indexing.project_include_prefixes` in
`docs/workflow-config.json`.

---

## Index Update Triggers (Entry Points)

The pipeline described in the stages below is initiated from several distinct entry points. They
fall into four groups; all of them ultimately run `build_index` — directly or via a spawned
`indexer.py` / `setup_index.py` process — and all coordinate through the single build lock described
in **Build Coordination** below.

### Operator / CLI (explicit, foreground)

- **`wf setup` / `wf update-indexes`** → `setup_index.py` `main` → dependency ensure, model prewarm,
  then `build_index`. Docs, code, and graph build in the foreground by default. `--background-code`
  builds docs/graph first and detaches code; `--background-docs` builds code first and detaches docs.
- **Direct indexer CLI** — `python3 .wavefoundry/framework/scripts/indexer.py --root <root>
  --content {docs|code|graph|all} [--full]`. The low-level build entry a manual full rebuild uses.

### Upgrade

- **`wave_upgrade` phase 4** (the `upgrade_wavefoundry.py` index phases) invokes `setup_index.py`
  for the semantic rebuild and graph refresh. It auto-escalates an incremental update to a full rebuild
  when `CHUNKER_VERSION`/model or `GRAPH_BUILDER_VERSION` advanced.

### MCP — explicit

- **`wave_index_build`** spawns `indexer.py` for a deterministic docs / code / graph
  build · update · rebuild.

### Automatic / reactive

Two index-refresh triggers are **reconciled** (wave `1p9am`) so they never churn the index on top of
each other: a prompt **turn-end** trigger and a slow **quiet-period safety net**.

- **Post-edit hook → turn-end reindex (primary).** On an index-worthy edit the rendered post-edit hook
  **marks a `reindex-pending` sentinel** (`indexer.mark_reindex_pending`) and does **not** spawn a
  reindex per edit. On **Claude** the **`Stop` hook** flushes it once per turn
  (`consume_reindex_pending` + one detached `indexer.py` spawn, skipped while a build is live) — so a
  whole turn's edits collapse into a single incremental pass. Hosts without a turn-end hook
  (Cursor/Copilot/…) consume the marker under a long leading-edge debounce
  (`HOOK_REINDEX_DEBOUNCE_SECONDS`, 45 s). Trade-off: mid-turn semantic search sees the pre-turn index
  until the turn ends (agents read their own just-written files directly).
- **In-session staleness monitor → quiet-period safety net.** The MCP server's daemon thread
  (`_start_staleness_monitor` → `_maybe_refresh_if_stale`) polls every ~20 s but only *acts* once the
  repo has been quiet for the **quiet-period** (`indexing.monitor.quiet_period_seconds`, default 300 s):
  it defers while a `reindex-pending` marker is fresh (the turn-end hook owns the next reindex) and for
  `quiet_period` seconds after the last build's `ended_at`. It fires only for drift the turn-end path
  missed — external (non-agent) edits, a turn that ended without the `Stop` hook flushing, or a
  non-Stop host — so it never competes with active editing.
- **MCP mutating tools → background project refresh** — most doc-writing wave-lifecycle tools
  (`wave_new_*`, `wave_add_change`, `wave_set_handoff`, prepare / pause / review / close / reopen,
  docs gardening) call `_trigger_background_index_refresh_for_paths` → `_start_background_index_refresh`
  after they write, launching a detached project reindex.
- **First-query lazy auto-rebuild** — a query that hits a stale or missing graph (e.g. a version bump
  the upgrade's graph phase did not cover) triggers an in-process rebuild on first access
  (`graph_query` auto-rebuild coordination). This is a safety net, not the primary path.

### Not a trigger (by design)

The **dashboard watcher** is **read-only**: it watches files only to *display* index staleness and
deliberately never initiates a build (`dashboard_server.py`). It imports the indexer module solely
for the staleness *check* (`project_index_inputs_stale`), never `build_index`. All reindexing is done
by the CLI, upgrade, MCP, and hook paths above.

## Build Coordination (single-lock lifecycle)

Every entry point above coordinates through one **whole-index build lock**
(`.wavefoundry/index/index-build.lock`, `indexer._index_build_lock`) so concurrent triggers never
corrupt the index or run two builds at once. The pattern:

- **The OS lock is the authority.** Acquisition takes a **`fcntl` record lock** (POSIX) / **`msvcrt`
  byte lock** (Windows) on a single **sentinel byte** (kept off the byte-0 metadata so the JSON stays
  readable while held); it is released automatically when the holder exits, even on a crash. A second
  builder that finds the lock held fails fast with `IndexBuildAlreadyRunning`.
- **Status tests the lock non-destructively.** `wave_index_build_status` reports an authoritative
  `held` by *testing* the OS lock — POSIX `fcntl` `F_GETLK` (queries without acquiring and returns the
  holder PID) / a momentary non-blocking `msvcrt` acquire on Windows — never by inferring from the
  lock file's presence. Read `lock.held`, not the file.
- **The lock file is a durable "last owner" breadcrumb, reclaimed lazily — not deleted on exit.** The
  metadata file (owner PID, `started_at`, `cmdline`, and `ended_at` written best-effort on a clean
  exit) is intentionally *not* unlinked when a build finishes; it is reclaimed on the next acquire only
  when the prior owner is classified stale (`classify_index_build_lock_owner`, retained solely for that
  reclaim decision). This is crash-safe: a hard-killed build can never leave a permanently-blocking
  lock. **`ended_at` distinguishes a clean finish from an interrupted build** — its absence (with the
  lock not held) means the last build was killed and the index may be partial.
- **Detached background builds are reaped.** The long-lived MCP server launches its reactive background
  builds detached (`start_new_session` on POSIX), which does **not** reparent them — so a finished build
  would linger as a zombie until the server exits. The server therefore tracks the PIDs it launches and
  reaps the finished ones on the next spawn. Short-lived launchers (the CLIs, the host-spawned post-edit
  hook) do not need this: their children reparent to init, which reaps them.

All process-state / command-line probes run through the windowless subprocess helper
(`subprocess_util.isolated_run`), so no console window appears on Windows — under either cmd or
PowerShell — and reaping is POSIX-only (Windows detached processes do not create zombies).

---

## Stage 1: File Discovery

`walk_repo(root)` walks the repository tree and collects every file that is not excluded by
`.gitignore` or `.wavefoundryignore`. After the walk, two filters narrow the list:

1. **`_filter_by_prefixes`** — keeps only paths that start with a configured
   `include_prefixes` list. This is the primary mechanism for telling Wavefoundry which
   directories belong to docs vs. code.

2. **`_filter_project_index_excludes`** — applies the `.wavefoundry/` blanket exclusion so
   framework-internal files (scripts, operational docs, dashboard, the deprecated
   `.wavefoundry/framework/index/`) do not enter a consumer project's index. Framework seeds and
   the top-level `README` are the deliberate exception — they fold into the `docs` table. A project
   can re-include specific framework subpaths by setting `indexing.project_include_prefixes.docs`
   or `indexing.project_include_prefixes.code` inside `docs/workflow-config.json` (this is how the
   self-hosting repo indexes its own `.wavefoundry/framework/scripts`).

The output of this stage is two lists of absolute file paths — one for docs files and one for
code files — for the single project index.

**Hard size guard (wave 1p5c4).** During the walk, any file whose size exceeds
`indexing.max_file_bytes` (default 5 MB) is skipped entirely — never read, never parsed — and
logged once. This stops a pathologically large file (e.g. a multi-GB SQL backup) from being read
into memory and handed to tree-sitter, which would spin the indexer. A separate, smaller
**tree-sitter parse cap** (`indexing.max_treesitter_parse_bytes`, default 2 MB) is published to
the chunker and graph extractor via `WAVEFOUNDRY_MAX_TS_PARSE_BYTES`: a code file over that cap is
still indexed as plain-text chunks but skips the AST parse, degrading to the regex/line fallback
instead of spinning. Set either key to `0` to disable that cap.

For **graph extraction**, a file in the window between the tree-sitter parse cap and the walk cap no
longer contributes zero nodes (which left a silent hole — everything importing an oversized
generated/vendored file dangled to `external::`). It degrades to a bounded **line-scan tier** (wave
1p9q6): a whole-file, AST-free, comment/string-masked, line-anchored scan that recovers the file's
imports and top-level definitions only (module node + definition nodes + `defines`/`imports` edges,
every node marked `extraction: "line_scan"`), at `EXTRACTED` confidence. It emits no `calls`/`reads`
edges — a line scan cannot resolve those faithfully — but its definitions do participate as
cross-file resolution candidates (binding inbound references and correctly forcing twin-refusal). The
scan is single-pass with a per-line length guard and a whole-file scan-byte ceiling
(`WAVEFOUNDRY_MAX_LINE_SCAN_BYTES`); past the ceiling it degrades to a logged skip. Per-file counts
(`line_scan_defines`/`line_scan_imports`/`line_scan_skipped`) land on the module node with a verbose
build-log line — mirroring the SQL ERROR-region recovery convention (wave 1p9qe).

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
- `WALKER_VERSION` (currently `"6"`) — bumped when the file-walk logic or the project-index include
  set changes (version 6 folded the framework seeds + `README` into the docs table)

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
   valid embeddings (accepted on correctness alone — CoreML partitions unsupported ops back to
   CPU, so no speedup margin is required). A CoreML probe failure matching the known macOS
   temp-working-directory shape (`Failed to create a working directory …` under
   `/var/folders/…/T/`) gets one bounded repair-and-retry inside the probe window — before the
   decision is recorded — so a transient temp-dir failure no longer pins the whole build to CPU;
   a persistent failure still falls back to CPU with an actionable recovery diagnostic.
3. Named secondary ONNX providers such as `DmlExecutionProvider`, `OpenVINOExecutionProvider`,
   `MIGraphXExecutionProvider`, or `ROCMExecutionProvider`, only after explicit availability and
   model probing (these keep the CPU-speedup gate).
4. `CPUExecutionProvider` as the safe fallback.

There is intentionally no generic GPU provider tier. Each non-CPU provider has different package,
driver, and model-compatibility constraints, so setup diagnostics report the actual provider name
and fallback reason. Every provider decision also names its source (`decision-source=` /
`decision_provenance`): `setup-cache` when a process honors the decision setup recorded in
`WAVEFOUNDRY_EMBED_PROVIDER_SELECTED`, `fresh-probe` when the availability/probe chain ran in that
process, or `operator-request` when `WAVEFOUNDRY_EMBED_PROVIDER` forced it — setup/index-build and
`wave_gpu_doctor` share the same probe chain, and process-scoped cache state is the one intentional
difference between their reports. On NVIDIA machines, setup plans the `fastembed-gpu` dependency path when local
`nvidia-smi` detection succeeds. If hardware is present but `CUDAExecutionProvider` is missing after
installation, setup keeps CPU execution and prints remediation guidance instead of failing the
index build.

### Sliding sort buffer (incremental path)

On the incremental path, embedding batches are assembled via a sliding sort buffer to
minimise wasted computation caused by padding in the ONNX runtime.

The buffer keeps a window of `SORT_WINDOW_SIZE` (2048) chunks. Within that window, chunks
are sorted by text length, and each batch of `EMBED_BATCH_SIZE` (256) chunks is drawn from
the shortest sequences available. This means sequences within a batch are similar in length,
reducing the amount of zero-padding needed to make them uniform — which reduces ONNX
inference time. Vectors are written to LanceDB incrementally after each batch completes; the
entire chunk list is never loaded into memory at once.

### Bounded-buffer streaming (full rebuild)

The full rebuild does **not** pre-accumulate the layer's chunks or count a total upfront.
Instead it streams the whole pipeline file-by-file through a bounded buffer
(`_run_streaming_full_rebuild` → `_StreamingLayerWriter`):

1. Iterate the eligible files in walk order; chunk each file into docs/code chunks.
2. Push chunks into a per-layer buffer. When a buffer reaches `embed_buffer_chunks`
   (`EMBED_BUFFER_CHUNKS_DEFAULT` = `SORT_WINDOW_SIZE`, configurable via
   `indexing.embed_buffer_chunks`, floored at `EMBED_BATCH_SIZE` (64) to keep GPU batches
   full), embed one batch and append the rows to LanceDB, then flush the buffer.
3. Flush the remainder at the end and build the secondary indexes **once** (see Stage 5).

Peak memory is bounded by the buffer rather than the corpus, so very large repositories index
without materializing every chunk and vector at once. The produced index is byte-identical to
the batch path (same chunks, vectors, and rows) — guarded by an output-parity test.

Progress is file-oriented (the file total is known cheaply from the walk; there is no
total-chunk pre-count):

```
build_index: indexed file 50/1044 files
```

---

## Stage 5: LanceDB Write

LanceDB stores the chunks and their vectors. The project index has two tables: `docs` and
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

On a forced rebuild, the streaming writer (`_StreamingLayerWriter`, see Stage 4) writes the
first buffered batch with `mode="overwrite"`, which replaces the entire table, then appends
each subsequent flush with `.add()`. The table lock is acquired lazily on the first append, so
a layer that produces zero chunks creates no table or lock directory (this keeps the
incremental path's missing-table handling intact). The secondary indexes are built once at
finalize, after every flush has been appended.

### Index creation

After all rows have been written, two secondary indexes are created if the total row count
reaches `LANCEDB_INDEX_THRESHOLD` (1000 rows):

- **HNSW** — approximate nearest-neighbour vector index, used for semantic search queries.
- **FTS (Tantivy/BM25)** — full-text search index, used for keyword/candidate-recall
  queries. The index is built without positional data (`with_position=False`), so
  server-side query shaping must avoid phrase queries that require positions.

Below the threshold, queries fall back to a brute-force scan, which is fast enough at small
scale and avoids the overhead of index construction on near-empty tables.

### Compaction and reclaim (bloat recovery)

Incremental appends leave superseded data fragments, stale FTS artifacts, and old table versions
behind; `optimize(cleanup_older_than=0)` reclaims them. When the table hits the Lance list-offset
corruption bug (`Max offset … exceeds length of values`, lance-format/lance #7538 — see the
`1p9aj-lance-list-offset-corruption` journal), in-place `optimize()` can no longer decode the table and
the bloat grows unbounded. The **reclaim ladder** (`indexer.reclaim_lance_table`) recovers it without a
re-embed:

1. **optimize** — compact in place (the normal path).
2. **compact by rewrite** — on an `optimize()` failure, read the still-readable rows (`to_arrow()`) and
   rewrite the table fresh with `create_table(mode="overwrite")`, which recomputes the list-column
   offsets from clean in-memory data and sidesteps the bug, then rebuild the vector + FTS indices. The
   swap uses `create_table(mode="overwrite")` — **never `db.rename_table`**, which is unsupported in
   LanceDB OSS and would leave the table missing on failure.
3. **full rebuild** — only when a table is entirely unreadable (a re-embed is unavoidable).

Both the finalize path and the incremental compaction path **self-heal**: a failed `optimize()`
escalates to the rewrite automatically (never raising), so a corrupted table reclaims itself on the next
build/update. The ladder is exposed as the `wave_index_optimize` MCP tool and runs automatically at the
end of `setup`/`upgrade` (reclaim-only). Proven: `docs.lance` 1.6 GB → 55 MB, zero re-embed.

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
| `CHUNKER_VERSION`         | `"29"` | Forces a full rebuild (re-chunk + re-embed)      |
| `WALKER_VERSION`          | `"6"`  | Forces a full rebuild (re-walk the include set)  |
| `WINDOW_SIZE`             | 120    | Line-window fallback window (lines per chunk)    |
| `WINDOW_OVERLAP`          | 10     | Reserved; structured fallbacks often advance without overlap |
| `MAX_CODE_CHUNK_CHARS`    | 4000   | Triggers sub-split of oversized `kind="code"` chunks |
| `CHUNK_MIN_LINES`         | 2      | Minimum code chunk size before merge             |
| `EMBED_BATCH_SIZE`        | 256    | Affects throughput only                          |
| `SORT_WINDOW_SIZE`        | 2048   | Affects padding efficiency only                  |
| `LANCEDB_INDEX_THRESHOLD` | 1000   | Below: brute-force scan; at/above: HNSW+FTS used |

Whenever `CHUNKER_VERSION` is bumped — for example because a breadcrumb format changes or a
new tree-sitter language is added — every file is re-chunked and re-embedded on the next build.
The same applies when the embedding model name changes.

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
