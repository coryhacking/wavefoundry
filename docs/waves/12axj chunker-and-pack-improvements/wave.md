# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-05-02

wave-id: `12axj chunker-and-pack-improvements`
Title: Chunker And Pack Improvements

## Changes

Change ID: `12avt-enh exclude-tests-from-framework-pack`
Change Status: `complete`

Change ID: `12avx-enh markdown-chunker-heading-hierarchy`
Change Status: `complete`

Change ID: `12aw5-enh structure-aware-code-chunker`
Change Status: `complete`

Change ID: `12b0v-enh imports-chunk-all-languages`
Change Status: `complete`

Change ID: `12b0w-enh swift-objc-chunker`
Change Status: `complete`

Change ID: `12b1a-enh indexer-stat-cache-change-detection`
Change Status: `complete`

Change ID: `12b1h-enh indexer-exclusion-and-file-type-coverage`
Change Status: `complete`

## Participants

| Role                   | Lane      | Owns                                                                                     |
| ---------------------- | --------- | ---------------------------------------------------------------------------------------- |
| implementer            | implement | `12avt`, `12avx`, `12aw5`, `12b0v`, `12b0w`, `12b1a`, `12b1h` |
| architecture-reviewer  | review    | `12avt`, `12avx`, `12aw5`, `12b0v`, `12b0w` — pack exclusion scope, chunker version trigger, chunk ID namespace, `__namespace__`/`__imports__` design, Swift/ObjC chunker structure; `12b1a` — stat cache schema, inode handling, backward compat; `12b1h` — blanket dot-dir rule, allowlist design, `chunk_plain_text` abstraction |
| code-reviewer          | review    | `12avx`, `12aw5`, `12b0v`, `12b0w` — `chunker.py` and tests; `12b1a` — `indexer.py` and `test_indexer.py`; `12b1h` — walker logic, `.env` pattern, `chunk_plain_text` correctness |
| qa-reviewer            | review    | `12avt`, `12avx`, `12aw5`, `12b0v`, `12b0w` — test coverage completeness and regression risk; `12b1a` — stat cache test coverage; `12b1h` — AC coverage including nested dot-dir and AC-7 |
| performance-reviewer   | review    | `12aw5`, `12b0v`, `12b0w` — O(n) per-file model, import scan pre-pass cost, regex backtracking; `12b1a` — stat pre-filter I/O cost, clean-pass performance; `12b1h` — walk_repo check complexity |

Completed At: 2026-05-02

## Wave Summary

Seven improvements to the framework packaging and indexing pipeline: exclude the test suite from the distribution zip and correct downstream seed guidance; add H1 breadcrumb context injection and threshold-gated `###` splitting to the markdown chunker; add structure-aware declaration-boundary chunking across 15+ languages with doc-comment extraction, annotation handling, multiline block-comment-aware `_decl_line_ends`, and `CHUNKER_VERSION` rebuild signal; add `__imports__` and `__namespace__` chunks across all structured-language chunkers for dependency and package-membership search; add dedicated `chunk_swift` and `chunk_objc` chunkers covering type declarations, methods, doc comments, and import surfaces; replace the full-hash incremental scan with an mtime+size+inode stat pre-filter that skips file reads on clean passes (hash only on stat miss; inode=0 on Windows/FAT skips inode check safely); and replace the per-name dot-dir blocklist with a blanket rule excluding all `.`-prefix directories except `.wavefoundry/`, add `.env`/`.env.*` exclusion, route `.txt` and extensionless `README`/`LICENSE`/`CHANGELOG`/`CONTRIBUTING`/`NOTICE` files to a new `chunk_plain_text` doc chunker, and add `.xml`, `.graphql`, `.gql`, `.proto`, `.sql` to `SOURCE_CODE_EXTENSIONS`.

## Review Evidence

- architecture-reviewer: approved with notes 2026-05-01 (round 3) — `_decl_line_ends` `/* */` fix correct; multiline block-comment spanning boundary is pre-existing informational gap; JS/TS window search consistent; `CHUNKER_VERSION = "8"` present.
- code-reviewer: approved 2026-05-01 (round 3) — `/* */` strip correct; all JS/TS doc paths use consistent window; 5 new tests genuine; 620 tests pass.
- qa-reviewer: approved with notes 2026-05-01 (round 3) — all new tests genuine and load-bearing; multiline `/*` and JS/TS class `__decl__` omission are pre-existing informational gaps.
- architecture-reviewer: approved with notes 2026-05-01 (round 5) — `12b0v`/`12b0w` ID namespace consistent; `__namespace__` design architecturally justified; ObjC body loop fix confirmed; `CHUNKER_VERSION = "10"` present. Notes: `@MainActor class` prefix not matched by `_SWIFT_TYPE_RE` (documented inline); Go aliased imports not captured (documented inline); `lines=(1,1)` on `__namespace__` cosmetically imprecise for files with copyright headers — informational, not blocking.
- code-reviewer: approved 2026-05-01 (round 5) — `deinit` fix correct (`keyword` fallback produces `Cache.deinit`); `@end` resets `current_class`; single-line ObjC body loop uses `body_open` flag and does not capture `@end`; 3 new tests genuine; 649 tests pass.
- qa-reviewer: approved 2026-05-01 (round 5) — `test_swift_deinit_chunk_id`, `test_objc_single_line_method_body_no_end_leak`, `test_objc_multiple_implementations` all present and load-bearing; version floor asserts `>= 10`; 649 tests pass.
- performance-reviewer: approved 2026-05-01 (round 5) — all 12 import scan patterns hoisted to module-level pre-compiled constants; ObjC body loop O(n) with `body_open` flag; no O(n²) paths introduced; overall O(n) per-file model intact.
- architecture-reviewer: approved-with-notes 2026-05-01 (round 6, 12b1h) — blanket dot-dir rule correct after trailing-slash fix on `_DOT_DIR_ALLOWLIST_PREFIX`; `.env` at walker layer is correct; `DOCS_EXTENSIONLESS_NAMES` duplication noted with coupling comments added; `chunk_plain_text` standalone function justified (divergent semantics from `chunk_line_window`); no callers broken.
- code-reviewer: approved-with-notes 2026-05-01 (round 6, 12b1h) — `parts[:-1]` correctly targets dirs only; `.env` pattern correct (`.envrc` not excluded by design); `chunk_plain_text` section/text body prepend fixed; `stem` variable comment fixed; 6 indexer + 7 chunker tests genuine and load-bearing. 668 tests pass.
- qa-reviewer: approved-with-notes 2026-05-01 (round 6, 12b1h) — AC-1/AC-2 now covered at nested depth; AC-3 through AC-6 covered; AC-7 covered by `test_new_code_extensions_in_source_set`. Notes: `.envrc` not explicitly tested (excluded by design); lowercase `readme` not in allowlist (intentional). 668 tests pass.
- performance-reviewer: approved-with-notes 2026-05-01 (round 6, 12b1h) — all new walk_repo checks O(depth) per file; `any(part.startswith("."))` short-circuits correctly; `chunk_plain_text` O(n) in file length. Note: `_DOT_DIR_ALLOWLIST_PREFIX` is a single string — adding a second allowlist entry would require logic change (noted for future maintainability).

## Review Checkpoints

- **Full wave review (2026-05-01): PASS** (round 3 — changes 12avt/12avx/12aw5)

  620 tests pass. 12avt pack exclusion verified; 12avx H1/H3 splitting covered; 12aw5 structure-aware chunking across 15+ languages, `CHUNKER_VERSION = "9"`.

  **Informational (not blocking):** `_decl_line_ends` multiline `/*` pre-existing gap; JS/TS class emits no `__decl__` chunk — consistent design.

- **Full wave review (2026-05-01): PASS** (round 5 — changes 12b0v/12b0w, all 5 changes complete)

  649 tests pass. Docs gate clean. All lanes signed off.

  **12b0v**: `__imports__` chunks (Java, Scala, C#, JS/TS, Go, Rust, C/C++, Swift, ObjC) and `__namespace__` chunks (Java, C#, Go). All 12 scan patterns pre-compiled at module level.

  **12b0w**: `chunk_swift` (type `__decl__`, func/init/deinit, `///` docs, imports) and `chunk_objc` (`@interface`/`@implementation`, `-`/`+` methods, `/** */` docs, imports, `@end` reset, `body_open` single-line fix). `CHUNKER_VERSION = "10"`.

  **Informational (not blocking):**
  - `_SWIFT_TYPE_RE` does not match `@MainActor`/`@preconcurrency` class prefixes — documented inline, falls back to line-window.
  - Go aliased single-line imports (`import alias "pkg"`) not captured — documented inline.
  - `__namespace__` chunk `lines=(1,1)` is cosmetically imprecise for files with copyright headers.

- **Full wave review (2026-05-02): PASS** (round 6 — changes 12b1a/12b1h, all 7 changes complete)

  668 tests pass. Docs gate clean. All four lanes signed off.

  **12b1a** (addendum): `file_hashes` backward-compat shim removed — `meta.json` now writes only `file_meta`; `_build_file_hashes` and `_file_meta_to_hashes` helpers deleted.

  **12b1h**: Blanket dot-dir exclusion (`.`-prefix dirs except `.wavefoundry/`); `.env`/`.env.*` exclusion; `.txt` and extensionless `README`/`LICENSE`/`CHANGELOG`/`CONTRIBUTING`/`NOTICE` routed to `chunk_plain_text` (kind=doc); `.xml`, `.graphql`, `.gql`, `.proto`, `.sql` added to `SOURCE_CODE_EXTENSIONS`.

  **Informational (not blocking):**
  - `DOCS_EXTENSIONLESS_NAMES` is duplicated between `indexer.py` and `chunker.py` — coupling comments added; consolidation deferred to a future shared-constants change.
  - `.envrc` is not excluded (direnv config, not a secrets file — intentional).
  - `_DOT_DIR_ALLOWLIST_PREFIX` is a single string; adding a second allowlist entry requires logic change.

## Journal Watchpoints

- **`12avx` blocks `12aw5`** — `12avx` introduces `CHUNKER_VERSION` in `chunker.py`; `12aw5` increments it. Both edit `chunker.py` and `test_chunker.py`; do not run them concurrently.
- **`framework_edit_allowed` and `seed_edit_allowed` guard windows** — `12avt` edits seeds and `build_pack.py`; `12avx` and `12aw5` edit framework scripts. Flip guards before each, restore after.
- **`12avt` is independent** — no dependency on `12avx` or `12aw5`; can run in parallel with either.
- **Index rebuild after `12avx`/`12aw5`** — `CHUNKER_VERSION` change triggers automatic full rebuild on next `build_index` call; no manual intervention needed, but note this in the closure checklist.

## Dependencies

- No external wave dependencies.
- Internal ordering: `12avx` must complete before `12aw5` begins (both edit `chunker.py`/`test_chunker.py`; `12avx` introduces `CHUNKER_VERSION`). `12avt` is independent of both.
