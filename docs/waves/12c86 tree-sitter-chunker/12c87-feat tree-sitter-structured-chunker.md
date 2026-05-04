# Tree-Sitter Structured Chunker

Change ID: `12c87-feat tree-sitter-structured-chunker`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-05-03
Wave: `12c86 tree-sitter-chunker`

## Rationale

The current regex-based structured chunkers miss patterns they don't explicitly handle — `export const` blocks, styled-component expressions, complex destructuring, multiline generics. Regex heuristics are also fragile: they break on valid code patterns the author didn't anticipate. Production code intelligence tools (Continue.dev, Cursor) use tree-sitter for this reason: it provides a language-accurate AST for 100+ languages from a single interface, eliminating the regex gap class entirely.

The wave `12c7n` fixes patch the most visible regressions. Tree-sitter is the structural fix — moving from "regex approximation of AST" to actual AST — and is the path to genuinely best-in-class chunking quality.

## Requirements

1. **Dependency**: `tree-sitter~=0.24` plus `tree-sitter-{language}` packages for TypeScript, JavaScript, Go, Rust, Java, C, C++, C# (csharp), and Bash must be added to `setup_index.py` `REQUIRED_IMPORTS` and installation guidance. Verify ABI compatibility for each grammar package before implementation.
2. **Language coverage**: tree-sitter chunkers must cover: TypeScript (`.ts`, `.tsx`), JavaScript (`.js`, `.jsx`, `.mjs`, `.cjs`), Go, Rust, Java, Kotlin (if grammar available), C, C++, C#, Bash/Shell. Python retains its existing `ast`-based chunker. Swift and ObjC retain regex fallback until `tree-sitter-swift` ≥ 1.0.
3. **Chunking strategy** (following Continue.dev's approach): extract top-level symbol nodes — function definitions, class declarations, method definitions, interface/struct/type declarations, `export const` at column 0. Group contiguous import/require/use declarations into a single imports chunk. Emit one chunk per top-level or class-member symbol.
4. **Minimum chunk size**: reuse `CHUNK_MIN_LINES` and `_merge_small_chunks()` from wave `12c7n` (`chunker.py`). Sub-minimum chunks are merged into their predecessor.
5. **Maximum chunk size**: if a symbol body exceeds 150 lines, collapse the body to `{ ... }` in the chunk text (preserve the signature and first/last line). Do not hard-truncate.
6. **Offline**: all tree-sitter grammar packages must be installed wheels (no on-demand downloads). `tree-sitter-language-pack` is ruled out — it downloads parsers at first use.
7. **Fallback**: if a grammar package is not installed or parsing fails, fall back to the existing regex chunker for that language. Log a warning. Do not crash.
8. **`chunk_file` dispatch**: update the dispatcher to route to tree-sitter chunkers when available, regex chunkers as fallback.
9. **Metadata**: chunks must carry correct `language`, `path`, `kind="code"`, `section` (symbol name or qualified name), and `lines` fields — same contract as current chunkers.
10. **Test coverage**: per-language tests asserting correct symbol extraction for at least one representative file per language.

## Scope

**Problem statement:** Regex-based chunkers miss valid code patterns (export const, styled components, complex generics) and are fragile by design. Tree-sitter provides language-accurate AST parsing and is the standard approach for production code intelligence tools.

**In scope:**

- `tree-sitter` + grammar packages: version verification, `setup_index.py` additions
- New `chunk_ts_treesitter`, `chunk_go_treesitter`, `chunk_rust_treesitter`, `chunk_java_treesitter`, `chunk_c_cpp_treesitter`, `chunk_csharp_treesitter`, `chunk_shell_treesitter` functions in `chunker.py`
- Updated `chunk_file` dispatch: prefer tree-sitter, fall back to regex
- Per-language `.scm` query patterns OR Python tree traversal (decision at implementation time based on API ergonomics)
- Minimum/maximum chunk size enforcement reusing `CHUNK_MIN_LINES` from wave `12c7n`
- Tests for each new chunker

**Out of scope:**

- Python chunker — `ast`-based, already accurate, no change
- Swift and ObjC chunkers — `tree-sitter-swift` 0.0.1 is pre-1.0; retain regex fallback
- Embedding model change — research shows `bge-base-en-v1.5` remains the best fastembed offline option; no action until a code-specific INT8 ONNX model in fastembed outperforms it on the ground truth set
- Cross-reference / symbol graph — out of scope for chunking; would require a separate wave

## Acceptance Criteria

- AC-1: `chunk_js_ts` replacement handles `export const Foo = styled(...)` — all declarations indexed, not just the import block.
- AC-2: `chunk_go_treesitter` extracts top-level functions and type declarations.
- AC-3: `chunk_rust_treesitter` extracts `fn`, `struct`, `impl`, `trait` items.
- AC-4: `chunk_java_treesitter` extracts class and method declarations.
- AC-5: Single-expression nodes (`super(scope, id)`, one-line stubs) are merged via `_merge_small_chunks`, not emitted standalone.
- AC-6: If a grammar package is absent, `chunk_file` falls back to the regex chunker for that language without crashing.
- AC-7: `setup_index.py` prints clear installation instructions when tree-sitter packages are missing.
- AC-8: All chunks carry correct `language`, `section`, `lines`, `kind` metadata.
- AC-9: All pre-existing chunker tests pass.
- AC-10: All pre-existing framework tests pass.

## Tasks

**Pre-implementation gate:**
- [ ] Verify ABI compatibility: install `tree-sitter~=0.24` alongside each grammar package; confirm no version resolution errors
- [ ] Confirm `nomic-embed-text-v1.5-Q` and `jina-v2-base-code` INT8 status unchanged (no better fastembed option available)

**Implementation:**
- [ ] Add `tree-sitter` and grammar packages to `setup_index.py` dependency checks and install instructions
- [ ] Implement tree-sitter chunker dispatch helper (`_ts_chunker(language, source, path)`)
- [ ] Implement JS/TS tree-sitter chunker (replaces `chunk_js_ts` for TS/JS/TSX/JSX)
- [ ] Implement Go, Rust, Java, C/C++, C#, Bash tree-sitter chunkers
- [ ] Implement minimum/maximum chunk size post-processing (reuse `CHUNK_MIN_LINES`, `_merge_small_chunks`)
- [ ] Update `chunk_file` dispatch to prefer tree-sitter, fall back to regex
- [ ] Add per-language tests (at minimum one representative file per language)
- [ ] Update `docs/architecture/embedding-model.md` and `current-state.md` to note tree-sitter dependency

## Agent Execution Graph

| Workstream     | Owner       | Depends On        | Notes                                              |
| -------------- | ----------- | ----------------- | -------------------------------------------------- |
| pre-impl-gate  | Engineering | wave 12c7n closed | ABI verification + embedding model confirmation    |
| dep-setup      | Engineering | pre-impl-gate     | setup_index.py + install guidance                  |
| ts-chunker     | Engineering | dep-setup         | JS/TS/TSX/JSX — highest impact language            |
| other-chunkers | Engineering | dep-setup         | Go, Rust, Java, C/C++, C#, Bash — parallel safe    |
| dispatch       | Engineering | ts-chunker, other-chunkers | chunk_file routing + fallback          |
| tests          | Engineering | dispatch          | Per-language + regression                          |
| docs           | Engineering | tests             | Architecture doc updates                           |

## Serialization Points

- `chunk_file` dispatch is a single-author surface — cannot be updated piecemeal.
- `CHUNK_MIN_LINES` and `_merge_small_chunks` from wave `12c7n` must be in place before this wave begins.
- Grammar package ABI verification must complete before any implementation work starts.

## Affected Architecture Docs

- `docs/architecture/current-state.md`: add tree-sitter to dependency list in Index build flow
- `docs/architecture/embedding-model.md`: add note that chunking quality now depends on tree-sitter; embedding model unchanged

## AC Priority

(Populated at Prepare wave.)

| AC    | Priority    | Rationale |
| ----- | ----------- | --------- |
| AC-1  | required    | Fixes the highest-impact known gap (export const truncation) |
| AC-2  | required    | Go chunker correctness |
| AC-3  | required    | Rust chunker correctness |
| AC-4  | required    | Java chunker correctness |
| AC-5  | required    | Micro-chunk elimination (reuses wave 12c7n work) |
| AC-6  | required    | Fallback prevents hard dependency failure |
| AC-7  | required    | Operational — setup must be self-documenting |
| AC-8  | required    | Metadata contract unchanged |
| AC-9  | required    | Non-regression gate |
| AC-10 | required    | Non-regression gate |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
|      |        |          |

## Decision Log

| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-05-03 | Use individual `tree-sitter-{language}` packages, not `tree-sitter-language-pack` | `language-pack` downloads parsers on first use — incompatible with offline-first MCP constraint | `tree-sitter-language-pack` (rejected: download model); `regex` chunkers (rejected: miss valid patterns) |
| 2026-05-03 | Keep Python `ast` chunker, do not replace with tree-sitter-python | Python AST chunker already produces accurate function/class boundaries; tree-sitter-python adds no marginal quality | tree-sitter-python (rejected: no quality improvement, adds dependency) |
| 2026-05-03 | Keep Swift/ObjC on regex fallback | `tree-sitter-swift` 0.0.1 is pre-1.0 and unreliable | tree-sitter-swift (deferred until ≥ 1.0) |
| 2026-05-03 | No embedding model change | `bge-base-en-v1.5` INT8 remains best fastembed offline option. `SFR-Embedding-Code-400M_R` (CoIR 61.9) has no official INT8 ONNX. `Qwen3-Embedding-0.6B` hardcodes batch_size=1. Revisit when a code-specific INT8 ONNX model outperforms bge-base on the ground truth set. | nomic-Q (fragile on macOS), jina-v2-code (FP32 only in fastembed), Qwen3 (batch=1 throughput blocker) |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Grammar packages pin conflicting tree-sitter minor versions | Pre-implementation ABI verification gate; pin `tree-sitter~=0.24`; document exact compatible grammar package versions |
| tree-sitter parse errors on malformed/partial source files | Wrap all parsing in try/except; fall back to regex chunker on parse failure |
| `tree-sitter-swift` (0.0.1) is included transitively | Do not add `tree-sitter-swift` to dependencies; retain regex chunker for Swift explicitly |
| Installation surface increases (new packages in setup_index.py) | Group tree-sitter packages as optional but recommended; print clear diagnostics when absent |
| `_merge_small_chunks` merges across different parent scopes | Extend merge logic to be symbol-identity-aware when implementing tree-sitter chunkers: only merge a sub-minimum chunk into a predecessor that shares the same parent class/impl/interface. Tree-sitter AST parent context makes this straightforward; do not reuse the regex-chunker merge as-is. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
