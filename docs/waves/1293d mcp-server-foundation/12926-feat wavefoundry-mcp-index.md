# Wavefoundry MCP Index Server

Change ID: `12926-feat wavefoundry-mcp-index`
Change Status: `ready`
Owner: Engineering
Status: planned
Last verified: 2026-04-29
Wave: `1293d mcp-server-foundation`

## Rationale

Three specific, measurable problems motivate this feature:

**1. Large project navigation.** Target projects using the Wave Framework include large
codebases where file-by-file navigation is not viable. Agents using `find`/`grep`/`read`
against a large repo burn significant tokens and frequently miss relevant context. Semantic
search over a pre-built index is the only path that scales.

**2. Framework operation token cost.** Running framework maintenance today requires an
agent to: discover the script path, understand its CLI, construct the command, invoke it,
and parse stdout — every session, every operation. `lifecycle_id.py`, `docs_lint.py`,
`docs_gardener.py`, and `render_platform_surfaces.py` are each a multi-step agent
workflow that could be a single structured tool call returning structured output.
Standardizing these as MCP tools reduces token cost and eliminates a class of navigation
and parsing errors.

**3. Session startup cost.** Every session currently loads several mandatory files before
any work begins. Targeted retrieval via `wave.current()`, `wave.get_prompt()`, and
`seed.get()` lets agents pull only what is relevant to the current task rather than
loading the full operating surface upfront.

This server ships as part of the standard Wavefoundry install so any project running the
framework gets it automatically. The startup instructions in AGENTS.md will be updated
alongside this feature to route through the MCP tools; otherwise the index exists but
agents do not use it.

## Requirements

1. The framework install and upgrade flow initializes and updates the MCP server and its
   dependencies without operator intervention beyond the existing install/upgrade commands.
2. The index is stored at `.wavefoundry/index/` within the target repository root.
   It must not be stored at any path that would conflict with target repository source.
3. Embedding models are cached globally on the host machine using fastembed's default
   platform-appropriate cache directory (`~/.cache/fastembed` on Linux/macOS,
   `%LOCALAPPDATA%\fastembed` on Windows). Models are downloaded once and reused
   across all projects on the same machine.
4. Markdown, plain text, and seed prompt files are embedded using `bge-small-en-v1.5`
   (~25MB). Source code chunks (function bodies, class definitions, code blocks) are
   embedded using `nomic-embed-code` (~137MB). Model assignment is per chunk kind, not
   per file extension.
5. Framework seed prompts (`.wavefoundry/framework/seeds/`) are indexed as kind `seed`
   and are retrievable via `seed.get(name)` and included in general `docs.search` results.
6. The index builder performs incremental rebuilds: unchanged files (detected by content
   hash stored in `meta.json`) are skipped. A full rebuild is always available via
   `python3 .wavefoundry/framework/scripts/build_index.py --full`.
7. The index covers: all files not excluded by `.gitignore` or `.aiignore`, with a
   hardcoded default exclusion list (`node_modules/`, `.git/`, `__pycache__/`, `*.pyc`,
   common build output dirs, binary file extensions).
8. The index is automatically maintained after file edits via the Claude Code post-edit
   hook (incremental rebuild of changed paths). The hook must not block the edit
   pipeline; it runs as a background subprocess.
9. An optional file-system watcher mode (`build_index.py --watch`) is available for
   non-Claude-Code environments (Cursor, terminal). It uses `watchdog` if installed;
   if not installed it exits with a clear install instruction rather than failing silently.
10. The MCP server (`server.py`) uses stdio transport and exposes the read-only tool
    surface defined in the Tool Surface section. It is registered in `.claude/settings.json`
    by `render_platform_surfaces.py` during install/upgrade.
11. The server supports a configurable `--root` argument (defaults to CWD) so it can
    serve any target repository, including Wavefoundry's own self-hosted surface.
12. All scripts and the server are cross-platform: Windows (x64), macOS (arm64, x64),
    Linux (x64, arm64). No C extension compilation is required at install time; all
    native code is delivered via pre-built pip wheels.
13. Change creation tools (`wave.new_feature`, `wave.new_bug`, `wave.new_enhancement`,
    `wave.new_refactor`) combine lifecycle ID generation and change doc scaffolding into
    a single call. Each wraps `lifecycle_id.py` and writes the scaffolded change doc to
    `docs/plans/` in one operation.
14. Wave lifecycle state mutation tools (create wave, admit change, remove change,
    prepare, pause, review, close) are explicitly out of scope and will be planned as
    a follow-on feature.

## Scope

**Problem statement:** Large target projects make file-by-file agent navigation
unscalable. Framework maintenance operations (lifecycle ID, linting, gardening, surface
rendering) cost unnecessary tokens because agents re-discover and re-invoke CLI scripts
every session. Session startup loads more context than any single task requires.

**In scope:**
- Language-aware chunker: `ast`-based for Python, header-split for markdown, regex
  fallback for JS/TS/other code, line-window fallback for unknown types
- Index builder script with incremental and full rebuild modes
- Two-model embedding pipeline (bge-small-en-v1.5, nomic-embed-code) via fastembed
- Flat-file index format at `.wavefoundry/index/` (`.npy` vectors, `.json` metadata)
- MCP server with tool surface defined below (stdio transport)
- Change creation tools: `wave.new_feature`, `wave.new_bug`, `wave.new_enhancement`,
  `wave.new_refactor` — each generates ID and scaffolds change doc in one call
- Framework script tools: `wave.validate()`, `wave.garden()`, `wave.sync_surfaces()`
- Claude Code post-edit hook integration for automatic incremental rebuild
- Optional file-system watcher mode via `watchdog`
- `render_platform_surfaces.py` updated to emit MCP server config into `.claude/settings.json`
- Framework install and upgrade scripts updated to initialize the index on first run
- AGENTS.md startup instructions updated to route through MCP tools
- Architecture doc updates for current-state, domain-map, data-and-control-flow
- Framework tests for chunker, index builder, and MCP tool contracts

**Out of scope:**
- Wave lifecycle state mutations (create wave, admit change, remove change, prepare,
  pause, review, close) — follow-on feature
- Remote or cloud deployment of the index or server
- Multi-repository indexing from a single server instance
- Authentication or access control on the MCP server
- Custom embedding model configuration by the operator (future)
- IDE integrations beyond Claude Code and Cursor (future)
- Keyword-only (BM25) hybrid search (designed for, deferred to avoid scope creep)

## Tool Surface

### Search and retrieval

**`docs.search(query, kind?)`**
Semantic search over markdown, text, and seed chunks. Optional `kind` filter:
`doc`, `seed`, `architecture`, `prompt`. Returns top-N results with path, section,
and excerpt. Query embedded with bge-small-en-v1.5.

**`code.search(query, language?)`**
Semantic search over source code chunks. Optional `language` filter (`python`, `js`,
etc.). Returns top-N results with path, line range, and excerpt. Query embedded with
nomic-embed-code.

**`seed.get(name)`**
Resolve a seed prompt by name or partial slug (e.g. `"plan-feature"`,
`"020-run-contract"`). Returns full text of the matching seed file. Backed by exact
match on chunk metadata, not semantic search.

### Wave inspection

**`wave.current()`**
Returns active wave ID, lifecycle stage, and list of admitted change IDs, parsed from
`docs/waves/` and `docs/workflow-config.json`.

**`wave.list_waves()`**
List all waves with ID, status, and change count.

**`wave.get_change(id)`**
Return full text of a change doc by ID prefix, searched across `docs/plans/` and
`docs/waves/`.

**`wave.get_prompt(shortcut)`**
Resolve a shortcut phrase (e.g. `"Prepare wave"`) to the full rendered prompt content
from `docs/prompts/`. Returns text ready for agent consumption without further file reads.

### Change creation

Each tool generates a lifecycle ID via `lifecycle_id.py`, scaffolds a change doc from
`docs/plans/plan-template.md`, writes it to `docs/plans/<id>.md`, and returns the
path and ID. One call replaces: generate ID, read template, write file.

**`wave.new_feature(slug)`** — kind `feat`
**`wave.new_bug(slug)`** — kind `bug`
**`wave.new_enhancement(slug)`** — kind `enh`
**`wave.new_refactor(slug)`** — kind `refactor`

### Framework operations

**`wave.validate()`**
Run `docs_lint.py` against the project and return structured pass/fail with error list.
Replaces: invoke script, parse stdout.

**`wave.garden()`**
Run `docs_gardener.py` against the project docs tree. Returns count of files updated
and a summary of changes made.

**`wave.sync_surfaces()`**
Run `render_platform_surfaces.py` to regenerate `.claude/`, `.cursor/`, and hook
configs from framework templates. Returns list of files written.

### Framework operation tools as building blocks

`wave.validate()`, `wave.garden()`, and `wave.sync_surfaces()` are exposed as
standalone tools for inspection and manual recovery. They are also the internal
implementation that wave lifecycle tools delegate to. Agents should prefer lifecycle
tools for normal workflow; standalone operation tools are for diagnosis and repair.

### Wave lifecycle state mutations (follow-on — `1293b-feat mcp-wave-lifecycle`)

`wave.create_wave`, `wave.admit_change`, `wave.remove_change`, `wave.prepare`,
`wave.pause`, `wave.review`, `wave.close`.

These are transactional: each tool checks preconditions, runs relevant validations
internally (lint, gardener, section checks), advances state only on full pass, and
returns structured pass/fail. The follow-on feature is a state machine with embedded
validation, not a set of thin doc-writing operations. See
`docs/waves/1293d mcp-server-foundation/1293b-feat mcp-wave-lifecycle.md` for the stub.

## Index File Layout

```
.wavefoundry/
  index/
    docs.npy        # float32 vectors for text/doc/seed chunks
    docs.json       # [{id, path, kind, language, lines, section, text}]
    code.npy        # float32 vectors for source code chunks
    code.json
    meta.json       # {built_at, model_versions: {docs: "...", code: "..."}, file_hashes: {path: sha256}}
```

Files are named by content type, not by model. `meta.json` records which model
produced each file. If the model changes, the builder detects a version mismatch
and triggers a full rebuild of the affected content type.

## Acceptance Criteria

- [ ] AC-1: `python3 .wavefoundry/framework/scripts/build_index.py` runs to completion
  on a fresh clone with no index present, on Windows, macOS, and Linux.
- [ ] AC-2: Incremental rebuild skips unchanged files; only modified paths produce new
  chunks. Verified by timing a second run against a first run on the same repo.
- [ ] AC-3: `docs.search("how does prepare wave work")` returns the prepare-wave prompt
  doc in the top 3 results.
- [ ] AC-4: `code.search("lifecycle ID epoch calculation")` returns the relevant function
  from `lifecycle_id.py` in the top 3 results.
- [ ] AC-5: `seed.get("plan-feature")` returns the full text of the plan-feature seed
  prompt without additional file reads by the agent.
- [ ] AC-6: `wave.current()` returns the correct active wave and stage when a wave is
  open; returns a clear "no active wave" message when none exists.
- [ ] AC-7: `wave.get_prompt("Prepare wave")` returns the full prompt content.
- [ ] AC-8: `wave.validate()` returns a structured pass/fail matching the output of
  running `docs_lint.py` directly.
- [ ] AC-9: `wave.new_feature("my-slug")` creates a scaffolded change doc at
  `docs/plans/<generated-id>.md` and returns the path and ID. The doc contains all
  required plan-template sections with the correct change ID populated.
- [ ] AC-10: `wave.new_bug`, `wave.new_enhancement`, and `wave.new_refactor` produce
  change docs with the correct kind prefix (`bug`, `enh`, `refactor`) in the ID.
- [ ] AC-11: `wave.garden()` returns a structured summary matching the output of running
  `docs_gardener.py` directly.
- [ ] AC-12: `wave.sync_surfaces()` regenerates platform surface files and returns the
  list of written paths without operator needing to know the script path or CLI.
- [ ] AC-13: After a file edit in Claude Code, the index reflects the change within the
  same session (post-edit hook fired incremental rebuild). The hook does not block
  the edit pipeline.
- [ ] AC-14: After `render_platform_surfaces.py` runs, `.claude/settings.json` contains
  a valid MCP server entry pointing to `server.py`.
- [ ] AC-15: Embedding models are downloaded to the global fastembed cache on first run
  and reused on subsequent runs. A second `build_index.py` run on a different project
  on the same machine does not re-download models.
- [ ] AC-16: All framework tests pass: `python3 .wavefoundry/framework/scripts/run_tests.py`
- [ ] AC-17: `watchdog` absence produces a clear install instruction; it does not cause
  `build_index.py` to fail when `--watch` is not requested.

## Tasks

Tasks are grouped into implementation slices. Each slice has a defined stopping point.
Two hard serialization gates must pass before downstream slices begin.

### Pre-implementation: resolve open design questions

- [ ] Decide chunk ID format (see Decision Log — open question)
- [ ] Decide framework ops invocation strategy: direct import vs subprocess (see Decision Log — open question)
- [ ] Add `fastembed`, `numpy`, `mcp[cli]` to framework dependency manifest
- [ ] Add `watchdog` as optional dependency with install instruction

### Slice 1 — Chunk interface + chunker
*Gate 1 passes at end of this slice. No downstream slice may begin until Gate 1 passes.*

- [ ] Define `Chunk` dataclass: `id`, `path`, `kind`, `language`, `lines: tuple[int,int]`,
  `section`, `text` — agree format before writing any index or server code
- [ ] Write `test_chunker.py` fixtures first: Python function/class, markdown section,
  unknown type, seed prompt file — nail the interface via tests before implementation
- [ ] Implement `chunker.py`: Python/ast splitter, markdown/header splitter, code/regex
  fallback, line-window fallback for unknown types
- [ ] **GATE 1:** Chunk dataclass interface and chunker output verified by tests

### Slice 2 — Index builder
*Gate 2 passes at end of this slice. Server and hook-integration slices may not begin until Gate 2 passes.*
*Highest-risk slice — incremental rebuild correctness and cross-platform path normalization.*

- [ ] Implement file walker in `build_index.py`: respects `.gitignore`, `.aiignore`, and
  hardcoded exclusion list; normalizes all paths to forward slashes on all platforms
- [ ] Integrate fastembed: docs embedding (bge-small-en-v1.5) first; verify model downloads
  to global cache and is reused on second run before adding code model
- [ ] Add code embedding (nomic-embed-code); verify correct model-per-chunk-kind dispatch
- [ ] Implement flat-file write: `docs.npy`, `docs.json`, `code.npy`, `code.json`, `meta.json`
- [ ] Implement incremental rebuild: load existing embeddings → filter rows for
  changed/deleted files by chunk ID → embed new/changed chunks → concatenate → write back
- [ ] Add `--full` flag (force full rebuild) and `--watch` mode (optional `watchdog` import)
- [ ] Write `test_build_index.py`: fixture repo in temp dir; verify hash-based skip,
  cross-platform paths, model version mismatch triggers full rebuild; mock fastembed
  embedding step to avoid 162MB download in test suite
- [ ] **GATE 2:** Index file format (npy shape, chunks.json schema, meta.json schema)
  verified stable by tests; chunk ID format confirmed consistent across platforms

### Slice 3 — MCP server: search and inspection tools
*Depends on Gate 2. Can begin in parallel with Slice 4 once Gate 2 passes.*

- [ ] Implement `server.py` skeleton: learn `mcp` SDK stdio transport pattern; server
  startup loads `docs.npy`/`code.npy` into memory; handle missing or stale index gracefully
- [ ] Implement `docs.search`, `code.search`, `seed.get`
- [ ] Implement `wave.current`, `wave.list_waves`, `wave.get_change`, `wave.get_prompt`
- [ ] Write `test_server_tools.py` for these tools using fixture index from Slice 2 tests

### Slice 4 — MCP server: framework operation tools
*Depends on Gate 2. Can run in parallel with Slice 3.*

- [ ] Implement `wave.new_feature`, `wave.new_bug`, `wave.new_enhancement`,
  `wave.new_refactor`: import `lifecycle_id.build_id` directly; scaffold from
  `docs/plans/plan-template.md`; write to `docs/plans/<id>.md`; return path and ID
- [ ] Implement `wave.validate`: import from `wave_lint_lib` directly; return structured
  pass/fail dict matching linter output
- [ ] Implement `wave.garden`: import from `docs_gardener` directly; return structured
  summary of files updated
- [ ] Implement `wave.sync_surfaces`: invoke `render_platform_surfaces` directly; return
  list of written paths
- [ ] Extend `test_server_tools.py` for framework operation tools

### Slice 5 — Integration
*Depends on Slices 3 and 4 complete.*

- [ ] Add `.wavefoundry/index/` to `.gitignore` and `.aiignore` via install/upgrade flow
- [ ] Update `render_platform_surfaces.py` to emit MCP server entry in `.claude/settings.json`
- [ ] Update post-edit hook to trigger incremental `build_index.py` as background
  subprocess; must not block edit pipeline
- [ ] Update install/upgrade scripts to run `build_index.py --full` on first install
- [ ] Update `AGENTS.md` startup instructions to route through MCP tools

### Slice 6 — Architecture docs
*No code dependency; can run in parallel with any slice after Gate 2.*

- [ ] Update `docs/architecture/current-state.md`: planned MCP topology → implemented;
  close risk row for "MCP server not yet designed"
- [ ] Update `docs/architecture/domain-map.md`: Future MCP/Index rows → active domains
  with correct paths; close open questions
- [ ] Update `docs/architecture/data-and-control-flow.md`: add index build path and
  MCP query path as primary control paths

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
|-----------|-------|-----------|-------|
| chunker | implementer | — | Defines `Chunk` interface; all other workstreams depend on it |
| index-builder | implementer | chunker (interface stable) | Incremental build, flat-file write, hash tracking |
| mcp-server-search | implementer | index-builder (index format stable) | Search/retrieval and wave inspection tools |
| mcp-server-ops | implementer | index-builder (CLI stable) | Change creation and framework operation tools |
| hook-integration | implementer | index-builder (CLI stable) | Post-edit hook, render_platform_surfaces update |
| tests | implementer | mcp-server-search, mcp-server-ops | Fixtures, unit and integration tests |
| architecture-docs | implementer | — | Parallel; no code dependency |

## Serialization Points

- **Gate 1** (end of Slice 1): `Chunk` dataclass interface and chunk ID format agreed
  and verified by tests. Blocks index-builder, server, and all downstream slices.
- **Gate 2** (end of Slice 2): Index file format (`docs.npy`/`code.npy` shape,
  `chunks.json` schema, `meta.json` schema) stable and verified by tests. Blocks
  Slices 3, 4, and 5.
- `render_platform_surfaces.py` MCP config entry format must be agreed before
  Slice 5 hook-integration and Slice 3/4 server entry point are finalized.

## Affected Architecture Docs

- `docs/architecture/current-state.md` — planned MCP topology becomes implemented;
  risk row for "MCP server not yet designed" closes
- `docs/architecture/domain-map.md` — "Future MCP Server" and "Future Code Index" rows
  become active domains with correct paths; open questions close
- `docs/architecture/data-and-control-flow.md` — two new primary control paths: index
  build and MCP query

## AC Priority

| AC | Priority | Rationale |
|----|----------|-----------|
| AC-1 | required | Cross-platform build is a hard delivery gate; failure here means the feature ships to no one |
| AC-2 | required | Incremental rebuild is the primary maintenance path for large repos; without it the feature is unusable on its target use case |
| AC-3 | required | Core doc search quality signal; if prepare-wave doesn't surface, semantic search is not working |
| AC-4 | required | Core code search quality signal; if lifecycle_id function doesn't surface, code search is not working |
| AC-5 | required | Seed retrieval is a primary token-reduction goal; must work correctly |
| AC-6 | required | wave.current is the anchor inspection tool; wrong state read is worse than no tool |
| AC-7 | required | wave.get_prompt is a primary session startup cost reduction; must return full content |
| AC-8 | required | wave.validate correctness is the foundation for lifecycle tools in the follow-on feature |
| AC-9 | required | Change creation is a primary framework operation tool; scaffolding must be correct |
| AC-10 | important | Kind prefix correctness is important but covered by AC-9 pattern; failure is visible and recoverable |
| AC-11 | important | wave.garden structured output is useful but agents can fall back to direct script invocation |
| AC-12 | required | sync_surfaces correctness is required for install/upgrade to function; a wrong .claude/settings.json breaks MCP registration |
| AC-13 | important | Auto-maintenance via hook improves quality but agents can rebuild manually; not a hard gate |
| AC-14 | required | MCP server must be registered in .claude/settings.json or Claude Code cannot discover it |
| AC-15 | required | Global model cache is a core design constraint; per-project re-download is a blocker for multi-project operators |
| AC-16 | required | Framework test suite must pass; regressions in existing scripts are a hard gate |
| AC-17 | important | Graceful watchdog absence is good UX but the primary auto-maintenance path is the post-edit hook |

## Progress Log

| Date | Update | Evidence |
|------|--------|---------|
| 2026-04-29 | Change doc authored | This file |

## Decision Log

| Date | Decision | Reason | Alternatives |
|------|----------|--------|-------------|
| 2026-04-29 | `.wavefoundry/index/` is gitignored, not committed | Index files are binary (`.npy`); merge conflicts would be unrecoverable. Each developer and CI environment builds locally. Consistent with "runtime artifact" classification already noted in Outputs. `.wavefoundry/index/` must be added to `.gitignore` and `.aiignore` by the install flow. | Commit index (binary merge conflicts, large binary diffs, no benefit over local rebuild) |
| **OPEN** | Chunk ID format — must be decided before Slice 1 begins | Two candidates: (A) `src/foo.py::MyClass.my_method` (semantic, human-readable, but fragile if function is renamed); (B) `src/foo.py:42-67` (stable line range, but meaningless after edits). Option A is better for search result display; Option B is better for incremental rebuild stability. Hybrid: `src/foo.py::MyClass.my_method@42-67` gives both but is more complex. Decision needed before any index or server code is written — this string is a key in meta.json and changing it invalidates all existing indexes. | —
| **OPEN** | Framework ops invocation strategy — direct import vs subprocess | Direct import (`from lifecycle_id import build_id`) is faster, no subprocess overhead, structured error handling, already importable in `lifecycle_id.py`, `docs_gardener.py`, `wave_lint_lib`. Subprocess is simpler isolation but adds latency and requires stdout parsing. Recommendation is direct import for all four scripts since they already expose clean function interfaces. Confirm before Slice 4 begins. | —
| 2026-04-29 | Flat files (.npy + .json) over sqlite or Chroma | No C extension compilation; cross-platform pip wheels only; corpus size does not require ANN index | sqlite-vec (C extension, compilation risk on Windows); chromadb (hnswlib, same issue) |
| 2026-04-29 | Two models (bge-small-en + nomic-embed-code) | Model assignment by chunk kind not file type; docstrings/comments treated as text | Single model for all content (lower retrieval quality on code) |
| 2026-04-29 | Global fastembed model cache | Models shared across all projects on same machine; no per-project re-download | Per-project cache (wastes disk, slower onboarding) |
| 2026-04-29 | Post-edit hook for auto-maintenance (primary); watchdog optional | Zero new hard deps for primary use case; hook infrastructure already exists | watchdog as hard dep (cross-platform friction); no auto-maintenance (degrades quality) |
| 2026-04-29 | Tool surface organized by intent not by script | `wave.new_feature(slug)` replaces discover-script + understand-CLI + invoke + parse-stdout; one call, structured result | Thin script wrappers (agent still bears CLI knowledge burden each session) |
| 2026-04-29 | Change creation tools included; wave lifecycle state mutations deferred | Change creation wraps already-tested scripts, low blast radius; state mutations (admit, close, prepare) touch wave lifecycle and warrant separate safety design pass | All mutations in one feature (higher blast radius, harder to review) |
| 2026-04-29 | Wave lifecycle tools are transactional: embed lint/garden validation internally | Lifecycle tools (prepare, close, admit) enforce process correctness without requiring agents to chain separate validation calls; partial state advance is not possible | Thin wrappers that write docs and leave validation to agent (agent can skip or mis-sequence) |
| 2026-04-29 | Standalone framework operation tools exposed as building blocks | Agents need inspect-without-advance for diagnosis and manual recovery; lifecycle tools delegate to the same implementations internally | Internal-only (no standalone access makes debugging harder) |
| 2026-04-29 | Index files named by content type (docs.npy, code.npy), not by model | Decouples layout from implementation; supports many models without artificial nesting; model recorded in meta.json | Per-model subdirs (couples directory structure to model choice) |

## Risks

| Risk | Mitigation |
|------|-----------|
| nomic-embed-code 137MB download surprises users on first install | Surface download size in install output; download is one-time per machine |
| fastembed wheel unavailable for a target platform | fastembed publishes wheels for Win x64, macOS arm64/x64, Linux x64/arm64; document supported platforms; fallback error message |
| Index diverges from repo state if post-edit hook is disabled | `build_index.py` CLI always available for manual rebuild; server warns if meta.json is stale |
| Large repos (>10k files) make full rebuild slow | Incremental rebuild is the default path; full rebuild documented as infrequent operation |
| `watchdog` optional import pattern breaks on some Python versions | Guard with try/except ImportError; tested in CI fixture |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
