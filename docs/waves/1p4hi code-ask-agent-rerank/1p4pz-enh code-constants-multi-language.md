# code_constants — multi-language constant lookup

Change ID: `1p4pz-enh code-constants-multi-language`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-11
Wave: `1p4hi code-ask-agent-rerank`

## Rationale

`code_constants` (the MCP tool literally named for constants) is **Python-only**: it scans for an *unindented* column-0 `NAME = value` / `NAME: TYPE = value` assignment (`server_impl.py` `code_constants_response`). Java's `private static final int MAX_JSON = …` (indented, inside a class), Go `const X = …`, C#/Kotlin/Rust/Swift/TS/Ruby/PHP forms all miss — the tool returns `value: null` for every non-Python constant. Real consumer feedback (the `javaagent` p4pu test, 2026-06-11) confirmed: `code_constants` returns 0 for genuine Java `static final` constants.

Wave `1p4hi` already built the fix's substrate: `1p4mf` made the **per-language chunk-lane constant detector** authoritative across all 11 languages, and `1p4ls` made the graph a **second consumer** of it (one detector, two consumers — Req-7). `code_constants` is the obvious **third consumer**. The wave's Req-7 "four-surface reconciliation" watchpoint anticipated exactly this and deferred it as "complementary, leave as-is" — a call made *before* the consumer gap was demonstrated. This change completes the wave's own stated scope.

## Requirements

1. `code_constants` detects constant declarations across **all 11 languages** (Python, JS/TS, Go, Java, Kotlin, C#, Rust, Swift, Ruby, PHP) by reusing the `1p4mf` chunk-lane detector via the `_chunker_module()` lazy import (the same seam `1p4ls` uses) — NOT a Python-shaped column-0 regex.
2. **Per-language value extraction:** for each located constant, return the right-hand-side value — the text after `=` (any indentation), trailing `;`/`,` trimmed (Java/C#/Rust/Swift/PHP); PHP `define('NAME', <value>)` returns the second argument. Multiline literals (frozenset/list/dict/array) are preserved via the existing bracket-depth continuation; over-long values return `kind="multiline-truncated"`.
3. **Performance:** chunk only files that contain a requested symbol as a substring (cheap pre-filter) — never chunk the whole repo for a targeted lookup.
4. **Backward-compatible response shape** — `{name, value, file, line, kind}` per match, input `symbols` order, `value: null` for not-found, all matches when a symbol appears in multiple files. Existing Python results are preserved or improved (no regression).
5. Scope-faithful: report a constant only where the chunk-lane detector recognizes one (so a function-local / non-constant assignment is NOT returned as a constant — the scope gate that `1p4mf` enforces carries through).

## Scope

**Problem statement:** `code_constants` only finds Python-style module-level constants; for every other language it returns null, despite `1p4mf` having built a per-language detector the tool could reuse.

**In scope:**
- Rewrite `code_constants_response` detection to drive the chunk-lane const detector (one detector, three consumers).
- A language-agnostic value extractor (RHS after `=`, multiline continuation, trailing-`;` trim, PHP `define()`).
- Per-language tests; `mcp-tool-surface.md` + the tool docstring updated.

**Out of scope:**
- No `CHUNKER_VERSION` / `GRAPH_BUILDER_VERSION` bump — `code_constants` is a query-time read tool, produces no index artifacts, and needs no re-index.
- No graph dependency — detection is a per-file chunk pass, independent of whether the graph is built.
- `code_outline` constant reconciliation (the other half of the Req-7 watchpoint) — separate.

## Acceptance Criteria

- [x] AC-1: **Multi-language detection.** `code_constants(["MAX_SIZE"])` on a Java `static final` (indented, in a class), Go `const`, C# `const`/`static readonly`, Kotlin `const val`, Rust `const`, Swift `static let`, Ruby capitalized const, PHP `const`/`define()`, and JS/TS `const` each return `{name, value, file, line}` with the correct value. Verified by a per-language test (FAIL-not-skip under `~/.wavefoundry/venv`).
- [x] AC-2: **Value extraction correctness.** Java `… = 1048576;` → `"1048576"` (trailing `;` trimmed); PHP `define('X', 42)` → `"42"`; a multiline Python `frozenset({...})` → the full literal (`kind="multiline"`); an unterminated value → `kind="multiline-truncated"`. Verified.
- [x] AC-3: **Python backward-compat.** Every constant the old column-0 path returned still returns, with the same `value`/`line`/`kind`; the existing `CodeConstants*` tests pass unchanged (or are updated only where the new path is strictly better). No regression.
- [x] AC-4: **Performance — candidate pre-filter.** Only files containing a requested symbol substring are chunked (asserted via a spy/counter or a fixture repo where an unrelated file is never parsed). A lookup on a large tree does not chunk every file.
- [x] AC-5: **Faithfulness + not-found.** A function-local assignment that shares a requested name is NOT returned (scope gate). A symbol absent everywhere returns `{value: null}`; a symbol in 2 files returns 2 matches.
- [x] AC-6: **Surface docs.** The `code_constants` docstring + `docs/specs/mcp-tool-surface.md` describe multi-language support (no longer "unindented Python-style only"). docs-lint green; full `run_tests.py` green.
- [x] AC-7 (**value**): the exact `javaagent` gap (a Java `static final` returned `null`) is closed — `test_multi_language_detection`'s Java case (`static final int MAX_SIZE = 1048576` → `"1048576"`) verifies it on a synthetic-but-equivalent Java file, and a live run on this repo returns real constant values (`RERANKER_MODEL`, `CHUNKER_VERSION`, …). Real-world re-confirmation by the `javaagent` team rides the next pack (not in `p4pu`).

## Tasks

- [x] Add a `_chunker_module()`-backed per-file constant locator (reuse the chunk-lane `[const]` detection; return `(name, line)` per constant in a file).
- [x] Add a language-agnostic value extractor: RHS after `=` at the located line, bracket-depth continuation for multiline, trailing `;`/`,` trim, PHP `define()` second-arg.
- [x] Rewrite `code_constants_response` to: glob-filter → substring pre-filter → chunk candidate files → match requested symbols → extract values. Preserve the response contract.
- [x] Tests: per-language detection (AC-1), value extraction incl. multiline + `define()` (AC-2), Python backward-compat (AC-3), pre-filter perf (AC-4), faithfulness + not-found + multi-file (AC-5).
- [x] Update the `code_constants` docstring + `mcp-tool-surface.md` (AC-6). Live Java check (AC-7).

## Affected Architecture Docs

`docs/specs/mcp-tool-surface.md` (the `code_constants` entry — multi-language). No data/control-flow or layering change (the tool's detection swaps to the existing chunk-lane detector; no new boundary). `data-and-control-flow.md` Path-6 code-navigation note may get a one-line touch if it characterizes `code_constants` as Python-only.

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-11 | **IMPLEMENTED — all 7 ACs.** `code_constants_response` now unions the column-0 regex (Python module, rich multiline) with a chunk-lane pass: a per-extension dispatch (`_CONST_CHUNKER_BY_EXT`) calls the specific tree-sitter chunker directly (the generic `chunk_file` dispatch silently falls back to a whole-file chunk for Go/JS-TS — discovered + worked around), filters `" [const]"` chunks, and extracts the RHS value via `_extract_const_value`/`_take_balanced_value` (after `=` at any indent; trailing `;`/`,` trim; PHP `define()` 2nd arg; multiline; per-declarator). Range-containment dedup vs the regex (chunk spans can include a leading comment). Live: Java/Go/C#/Kotlin/Rust/Swift/Ruby/PHP/TS all resolve their value; Python module + **class-level** + multiline preserved; function/block locals excluded; real-repo `RERANKER_MODEL`/`CHUNKER_VERSION` resolve. **+4 net `CodeConstantsTests` (22 total): multi-language (9 langs), value-extraction edge cases, candidate pre-filter, class-level-found / function-local-ignored.** Full suite **3106 green**; docs-lint ok. Docstrings + `mcp-tool-surface.md` updated. No version bump. | `server_impl.py` (`_extract_const_value`/`_take_balanced_value`/`_CONST_CHUNKER_BY_EXT` + the chunk-lane pass in `code_constants_response`); `tests/test_server_tools.py` (CodeConstantsTests); `docs/specs/mcp-tool-surface.md`. |
| 2026-06-11 | **Adversarial re-review fixes (5, all in `server_impl.py`, no version bump — read tool):** (A1) `_take_balanced_value` is now string-aware via a shared `_string_literal_end` primitive — a `,`/`;`/`}` INSIDE a quoted value no longer truncates it (`CSV_SEP = ","` → `","`, Java `"a;b;c"` kept whole, dict value past an in-string `}` complete). (B1) leading comment block stripped before the NAME search so a `# THRESHOLD = 10` comment above `THRESHOLD = 99` no longer poisons the value. (B2) a Go grouped `const (...)`/iota block (ONE chunk) now resolves EVERY member to its own line+value, not just the first. (B3) qualified lookup works — the substring pre-filter uses the bare leaf so `Status.OK` chunks the file, and both `OK` and `Status.OK` resolve (short no longer shadows qualified). (B4) `.mts`/`.cts` are now **first-class across the main pipeline** (not just `code_constants`): added to indexer `SOURCE_CODE_EXTENSIONS`, chunker `JS_TS_EXTENSIONS` + `_EXT_TO_LANGUAGE` + `chunk_js_ts_treesitter` lang_key (→`typescript`), and graph_indexer `_CODE_EXTENSIONS` + `_TS_EXTENSION_TO_LANGUAGE` — so `code_ask`/`code_search`/`code_outline`/the graph index all handle them, riding the `CHUNKER_VERSION` 29 bump. **+6 `CodeConstantsTests`.** Full suite 3121 green. | Review wf_69990b0f-6f7; `server_impl.py` `_string_literal_end`/`_take_balanced_value`/`_strip_leading_comment_lines`/`_extract_const_value`/`_CONST_CHUNKER_BY_EXT` + the chunk-lane pass; `tests/test_server_tools.py`. |
| 2026-06-11 | Spun up from operator follow-up on the `javaagent` p4pu feedback (`code_constants` returns 0 for Java). Completes the wave's Req-7 "one detector, three consumers" — `code_constants` becomes the third consumer of the `1p4mf` chunk-lane detector. No version bump (read tool). | This doc. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-11 | Reuse the `1p4mf` chunk-lane detector (not the graph constant nodes) for detection. | Keeps `code_constants` graph-independent (works with no graph built) and reuses the authoritative per-language detector directly; the graph `value` is simple-literal-only and would lose multiline capture. | (a) Graph-backed (query `1p4ls` constant nodes) — rejected: graph dependency + lossy values. (b) Extend the Python regex per language — rejected: re-implements detection the chunk lane already owns. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Chunking is slower than a line scan | Substring pre-filter (AC-4) — chunk only candidate files; targeted lookups stay cheap. |
| Value extraction wrong for an exotic declaration shape | Per-language AC-2 tests + return the raw RHS verbatim (don't over-parse); `kind` flags multiline/truncated. |
| Python regression | AC-3 pins the existing `CodeConstants*` tests; the new path must be a superset. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
