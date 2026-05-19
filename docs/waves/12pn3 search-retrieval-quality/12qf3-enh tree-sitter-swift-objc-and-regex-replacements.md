# Tree-Sitter — Swift, ObjC, and Regex Chunker Replacements

Change ID: `12qf3-enh tree-sitter-swift-objc-and-regex-replacements`
Change Status: `implemented`
Owner: framework-engineer
Status: implemented
Last verified: 2026-05-18
Wave: 12pn3 search-retrieval-quality

## Rationale

Wave `12c86` replaced regex structured chunkers with tree-sitter for JS/TS, Go, Rust, Java, C/C++, C#, Bash, Kotlin, and SQL (with regex fallback). **Swift** (`.swift`) and **Objective-C** (`.m`, `.mm`) were deliberately left on regex because `tree-sitter-swift` was 0.0.1 at implementation time. Swift is now **0.7.2** on PyPI with platform wheels; `tree-sitter-objc` is **3.0.2** under tree-sitter-grammars. Several other indexed languages still use regex-only or line-window chunking despite mature tree-sitter grammars on PyPI.

Poor chunk boundaries directly hurt retrieval quality in this wave: `code_search` and `code_ask` surface chunk text from the index. Declaration-accurate AST chunking reduces missed symbols, oversized windows, and false splits compared to regex heuristics.

This change adds tree-sitter chunkers (with existing regex/line-window fallbacks) for eight work packages in one implementation pass, bumps `CHUNKER_VERSION` to force reindex, and updates architecture docs and `eval_chunker.py` dispatch reporting.

## Requirements

### Work package 1 — Swift (tree-sitter)

1. Add `tree-sitter-swift` to `setup_index.py` `REQUIRED_IMPORTS` (same optional-at-runtime pattern as other grammars: index works without it; regex fallback when absent).
2. Register `"swift"` in `_get_ts_lang()` → `tree_sitter_swift`.
3. Implement `chunk_swift_treesitter(source, path) -> Optional[list[Chunk]]` following the Kotlin/Go pattern: top-level and nested declarations (`class`, `struct`, `enum`, `protocol`, `extension`, `func`, `init`, `deinit`), `///` doc comments as `kind="doc"`, imports chunk, `_merge_small_chunks(..., scoped=True)`, `split_large_code_chunks`, `_ts_collapse_body` for large bodies.
4. Update `chunk_file()` for `.swift`: try `chunk_swift_treesitter` first; on `None` or parse failure use existing `chunk_swift`; preserve `_with_summary`.

### Work package 2 — Objective-C (tree-sitter)

5. Add `tree-sitter-objc` to `setup_index.py` `REQUIRED_IMPORTS`.
6. Register `"objc"` in `_get_ts_lang()` → `tree_sitter_objc`.
7. Implement `chunk_objc_treesitter(source, path) -> Optional[list[Chunk]]`: `@interface` / `@implementation` / `@protocol`, instance and class methods, doc comments, imports; handle `.m` and `.mm` (Objective-C++; fall back to regex on parse failure).
8. Update `chunk_file()` for `OBJC_EXTENSIONS`: try tree-sitter first, then `chunk_objc`. Consider adding `_with_summary` for ObjC (parity with Swift) if symbol extraction is straightforward.

### Work package 3 — Integration, version, ABI

9. Pre-implementation: verify all new grammar wheels load under `tree-sitter>=0.24,<0.26` (project pin; record resolved versions in Decision Log).
10. Bump `CHUNKER_VERSION` in `chunker.py` (triggers full reindex via `meta.json`).
11. Extend `eval_chunker.py` `_determine_dispatch()` labels for new tree-sitter paths.
12. Per-language tests in `test_chunker.py`: at least one representative file per new tree-sitter chunker; tests skipped when grammar not installed (same pattern as `test_chunker.py` Kotlin/Swift tests).
13. All existing framework tests pass (`python3 .wavefoundry/framework/scripts/run_tests.py`).

### Work package 4 — HCL / Terraform

14. Add `tree-sitter-hcl` (PyPI ≥ 1.0).
15. Implement `chunk_hcl_treesitter` (or shared HCL chunker) for `.tf` and `.hcl` extensions currently routed to `chunk_line_window` via `CODE_EXTENSIONS` / `TERRAFORM_EXTENSIONS` / `HCL_EXTENSIONS`.
16. **Do not** replace `chunk_secrets_file` for `.tfvars` or `.env` — values stay redacted.

### Work package 5 — SCSS

17. Add `tree-sitter-scss` (PyPI 1.0.0).
18. Implement `chunk_scss_treesitter` for `.scss`; fall back to line-window. (`.sass` may remain line-window unless a sass grammar is added.)

### Work package 6 — Makefile

19. Add `tree-sitter-make` (PyPI ≥ 1.0).
20. For extensionless `Makefile` (and `CODE_EXTENSIONLESS_NAMES` make targets), try tree-sitter make grammar before `chunk_line_window`.

### Work package 7 — Scala, HTML, XML

21. Add `tree-sitter-scala`, `tree-sitter-html`, `tree-sitter-xml` to `setup_index.py`.
22. Implement `chunk_scala_treesitter`, `chunk_html_treesitter`, `chunk_xml_treesitter`; dispatch before existing `chunk_scala`, `chunk_html`, `chunk_xml`.

### Work package 8 — Line-window languages

23. Add grammar packages: `tree-sitter-ruby`, `tree-sitter-php`, `tree-sitter-yaml`, `tree-sitter-toml`, `tree-sitter-json`, `tree-sitter-css`, `tree-sitter-powershell`.
24. Implement corresponding `chunk_*_treesitter` functions and update `chunk_file()` so `.rb`, `.php`, `.yaml`, `.yml`, `.toml`, `.json`, `.jsonc`, `.css`, `.ps1`, `.psm1` prefer tree-sitter, then `chunk_line_window`.
25. Carve these extensions out of blind `CODE_EXTENSIONS` line-window dispatch (same pattern as Kotlin).

### Cross-cutting

26. **Offline-first:** only PyPI wheels in `setup_index.py`; no `tree-sitter-language-pack` or runtime grammar downloads.
27. **Fallback:** any missing grammar, parse error, or empty chunk list → existing regex or line-window chunker; log one warning per language per process (existing `_ts_parse` behavior).
28. Reuse `CHUNK_MIN_LINES`, `_merge_small_chunks`, `split_large_code_chunks`, `_ts_collapse_body` consistently.
29. Update `docs/architecture/chunking-and-indexing-pipeline.md` language table and Swift/ObjC decision notes.
30. Supersede wave `12c87` decision “defer Swift until tree-sitter-swift ≥ 1.0” — adopt **≥ 0.7.2 + corpus tests** instead.

## Scope

**Problem statement:** Indexed Swift, ObjC, Scala, HTML, XML, and many config/script extensions use regex or fixed line windows. That produces weaker chunk boundaries than tree-sitter-backed languages, reducing code retrieval precision for `code_search` / `code_ask` in wave `12pn3`.

**In scope:**

- `chunker.py` — new tree-sitter chunkers and `chunk_file` dispatch for packages 1–8
- `setup_index.py` — grammar dependencies
- `tests/test_chunker.py`, `eval_chunker.py`
- `docs/architecture/chunking-and-indexing-pipeline.md`
- `CHUNKER_VERSION` bump

**Out of scope:**

- Embedding model changes (separate changes in this wave)
- MCP `code_definition` / `code_references` tree-sitter expansion (optional follow-on; not required for indexing)
- New file extensions not already in `SOURCE_CODE_EXTENSIONS` / `CODE_EXTENSIONS` (e.g. Solidity, Zig, Dart — no PyPI package or not indexed)
- `.fish` shell (no `tree-sitter-fish` on PyPI)
- `.sass`, `.proto`, `.graphql` unless trivially included while touching dispatch
- Replacing Python `ast` chunker with tree-sitter-python

## Acceptance Criteria

- AC-1: `.swift` files use `chunk_swift_treesitter` when `tree-sitter-swift` is installed; otherwise `chunk_swift` (regex).
- AC-2: `.m` / `.mm` files use `chunk_objc_treesitter` when `tree-sitter-objc` is installed; otherwise `chunk_objc`.
- AC-3: `.tf` / `.hcl` use tree-sitter HCL chunker when installed; `.tfvars` still uses `chunk_secrets_file` with redacted values.
- AC-4: `.scss` uses tree-sitter when installed; falls back to line-window.
- AC-5: `Makefile` uses tree-sitter-make when installed; falls back to line-window.
- AC-6: `.scala`, `.html`/`.htm`, `.xml` (+ related XML extensions in `XML_EXTENSIONS`) use tree-sitter when installed; fall back to regex chunkers.
- AC-7: `.rb`, `.php`, `.yaml`, `.yml`, `.toml`, `.json`, `.jsonc`, `.css`, `.ps1`, `.psm1` use tree-sitter when installed; fall back to line-window.
- AC-8: `CHUNKER_VERSION` incremented; `meta.json` comparison forces rechunk on next index build.
- AC-9: `setup_index.py` lists all new grammar packages; install instructions remain offline wheel-based.
- AC-10: ABI smoke test documented in Decision Log (all grammars load with project `tree-sitter` pin).
- AC-11: `eval_chunker.py` reports correct dispatch paths for each language family.
- AC-12: Per-language tests pass when grammars installed; skip cleanly when absent.
- AC-13: Full framework test suite passes.
- AC-14: `docs/architecture/chunking-and-indexing-pipeline.md` updated for new AST coverage.

## Tasks

**Pre-implementation gate**

- [ ] Open `framework_edit_allowed`; close after all framework edits.
- [ ] ABI verification: install new grammars in tool venv with `tree-sitter>=0.24,<0.26`; import each `language()` and parse a minimal sample file; record versions in Decision Log.

**Implementation (serialize on `chunker.py` + `CHUNKER_VERSION`)**

- [ ] Packages 1–2: Swift + ObjC tree-sitter chunkers and dispatch
- [ ] Packages 4–6: HCL, SCSS, Make
- [ ] Package 7: Scala, HTML, XML
- [ ] Package 8: Ruby, PHP, YAML, TOML, JSON, CSS, PowerShell
- [ ] Package 3: `setup_index.py`, `CHUNKER_VERSION`, `eval_chunker.py`, architecture doc
- [ ] Tests for each package; run `run_tests.py`

**Post-implementation**

- [ ] Operator note: full index rebuild required after merge (`wave_index_build` or `setup_index.py --full`) because `CHUNKER_VERSION` changes.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| abi-gate | framework-engineer | — | Verify grammars vs tree-sitter 0.24–0.25.x |
| ts-swift-objc | framework-engineer | abi-gate | Packages 1–2 |
| ts-infra-config | framework-engineer | abi-gate | Packages 4–6 (HCL, SCSS, Make) |
| ts-scala-html-xml | framework-engineer | abi-gate | Package 7 |
| ts-line-window-langs | framework-engineer | abi-gate | Package 8 |
| integration | framework-engineer | ts-* | setup_index, CHUNKER_VERSION, eval_chunker, arch doc |
| tests | framework-engineer | integration | test_chunker + run_tests |

## Serialization Points

- Single owner for `chunk_file()` dispatch edits — merge workstreams sequentially or one PR to avoid dispatch conflicts.
- `CHUNKER_VERSION` bump once at end of chunker work (not per language).
- `framework_edit_allowed` gate for entire effort.

## Affected Architecture Docs

- `docs/architecture/chunking-and-indexing-pipeline.md` — Stage 3 code chunking table, Swift/ObjC notes, grammar dependency list
- `docs/ARCHITECTURE.md` — index entry if chunking doc summary changes

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| --- | -------- | --------- |
| AC-1 | required | Primary ask — Swift AST |
| AC-2 | required | Primary ask — ObjC AST |
| AC-3 | required | HCL/Terraform indexing quality |
| AC-4 | required | SCSS in CODE_EXTENSIONS |
| AC-5 | required | Makefile extensionless path |
| AC-6 | required | Replace regex Scala/HTML/XML |
| AC-7 | required | Replace line-window bucket languages |
| AC-8 | required | Reindex signal |
| AC-9 | required | Install path |
| AC-10 | required | Avoid silent ABI breakage |
| AC-11 | nice-to-have | Operator visibility |
| AC-12 | required | Regression safety |
| AC-13 | required | Regression safety |
| AC-14 | required | Doc truth |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-18 | Change doc created; admitted to wave `12pn3 search-retrieval-quality` | This file |
| 2026-05-18 | Implemented packages 1–8: tree-sitter chunkers, setup_index deps, CHUNKER_VERSION=21, tests | `chunker.py`, `setup_index.py`, `test_chunker.py` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-05-18 | Single change doc for packages 1–8 | One `CHUNKER_VERSION` bump and one reindex; shared chunker patterns | Eight separate changes (rejected: redundant rebuilds) |
| 2026-05-18 | Adopt Swift at 0.7.2 despite semver &lt; 1.0 | Grammar matured since 12c87 deferral; wheels on all platforms | Wait for 1.0 (rejected: unnecessary delay) |
| 2026-05-18 | Keep regex/line-window fallbacks for every new grammar | Offline-first; optional grammars; parse resilience | Hard-require all grammars (rejected: install fragility) |
| 2026-05-18 | Do not add fish/dart/proto in this change | No PyPI grammar or not in index set | Expand scope (rejected) |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Grammar ABI mismatch with `tree-sitter` 0.25.x | Pre-implementation ABI gate; pin compatible versions in setup_index |
| Swift grammar incomplete on edge syntax | Regex fallback; extend corpus tests from `test_chunker.py` Swift fixtures |
| `.mm` Objective-C++ parse failures | Fall back to `chunk_objc` regex |
| Install size / cold-install time grows | Document optional grammars; same pattern as existing tree-sitter set |
| Large diff in `chunker.py` | Single workstream owner; follow existing `chunk_kotlin_treesitter` template |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
