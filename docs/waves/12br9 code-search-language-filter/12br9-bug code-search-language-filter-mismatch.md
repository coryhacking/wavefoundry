# Code Search Language Filter Mismatch

Change ID: `12br9-bug code-search-language-filter-mismatch`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-05-02
Wave: `12br9 code-search-language-filter`

## Rationale

`code_search(language="typescript")` returns zero results despite the index containing TypeScript chunks. The chunkers (`chunk_js_ts`, `chunk_c_cpp`, `chunk_shell`) store raw file extensions as the language tag (`"tsx"`, `"ts"`, `"cpp"`, `"sh"`) while the search filter compares against canonical language names (`"typescript"`, `"cpp"`, `"shell"`). These never match, silently returning empty results for any language-filtered query.

## Requirements

1. All code chunks produced by `chunk_js_ts` must store `language="typescript"` for `.ts`/`.tsx`/`.mjs`/`.cjs` files and `language="javascript"` for `.js`/`.jsx` files.
2. All code chunks produced by `chunk_c_cpp` must store `language="cpp"` for `.cpp`/`.hpp` files and `language="c"` for `.c`/`.h` files.
3. All code chunks produced by `chunk_shell` must store `language="shell"` for `.sh`/`.bash`/`.zsh` files and `language="fish"` for `.fish` files.
4. The canonical language names stored by chunkers must match those recognized by `_detect_language` in `server.py` — a test must assert this.
5. A single `_EXT_TO_LANGUAGE` map in `chunker.py` must be the authoritative source for extension → canonical name; no scattered `language=ext` raw assignments.

## Scope

**Problem statement:** Chunkers stored raw file extensions as language tags; the server's language filter used canonical names. They never matched.

**In scope:**

- `chunker.py`: add `_EXT_TO_LANGUAGE` map and `_ext_language()` helper; update `chunk_js_ts`, `chunk_c_cpp`, `chunk_shell`, and the `CODE_EXTENSIONS` fallback
- `server.py`: extract `_EXT_TO_LANG` as a module-level constant (was inline in `_detect_language`); add shell/fish/mjs/cjs/hpp mappings to align with chunker
- Tests asserting correct language values per extension for all three affected chunkers
- Cross-map consistency test asserting server and chunker maps agree for shared extensions

**Out of scope:**

- Backfilling existing indexes — existing indexes need a full rebuild; that is an operational note, not a code change
- Language tags for chunkers not affected by this bug (Python, Go, Rust, Java, etc. — already used hardcoded canonical strings)

## Acceptance Criteria

- AC-1: `.tsx` and `.ts` files produce chunks with `language="typescript"`.
- AC-2: `.js` and `.jsx` files produce chunks with `language="javascript"`.
- AC-3: `.cpp` and `.hpp` files produce chunks with `language="cpp"`; `.c` and `.h` produce `language="c"`.
- AC-4: `.sh`, `.bash`, `.zsh` files produce chunks with `language="shell"`; `.fish` produces `language="fish"`.
- AC-5: A test asserts that `server._EXT_TO_LANG` and `chunker._EXT_TO_LANGUAGE` agree on every shared extension.
- AC-6: All 709 pre-existing framework tests continue to pass.

## Tasks

- [x] Add `_EXT_TO_LANGUAGE` map and `_ext_language()` helper to `chunker.py`
- [x] Fix `chunk_js_ts` to use `_ext_language(ext)` instead of raw `ext`
- [x] Fix `chunk_c_cpp` to use `_ext_language(ext)` instead of raw `ext`
- [x] Fix `chunk_shell` to use `_ext_language(ext)` instead of raw `ext or "sh"`
- [x] Fix `CODE_EXTENSIONS` fallback in `chunk_file` dispatcher
- [x] Extract `_EXT_TO_LANG` as module-level constant in `server.py`; align mappings
- [x] Add per-extension language tests to `JsTsChunkerTests`, `CCppChunkerTests`, `ShellChunkerTests`
- [x] Add cross-map consistency test to `CodeSearchLanguageNormalizationTests`

## Agent Execution Graph

| Workstream       | Owner       | Depends On | Notes                              |
| ---------------- | ----------- | ---------- | ---------------------------------- |
| chunker-fix      | Engineering | —          | `_EXT_TO_LANGUAGE` map + 3 chunkers |
| server-fix       | Engineering | —          | `_EXT_TO_LANG` extraction + align  |
| chunker-tests    | Engineering | chunker-fix | Language field assertions          |
| cross-map-test   | Engineering | server-fix, chunker-fix | Consistency gate        |

## Serialization Points

- `chunker.py` and `server.py` must use the same canonical names — cross-map test is the gate.

## Affected Architecture Docs

N/A — bug fix confined to chunker and server internals; no boundary, flow, or verification architecture impact. Index rebuild note captured in wave watchpoints.

## AC Priority

| AC   | Priority   | Rationale |
| ---- | ---------- | --------- |
| AC-1 | required   | Core correctness — TypeScript is the primary affected language |
| AC-2 | required   | Core correctness — JavaScript equally affected |
| AC-3 | required   | Core correctness — C/C++ affected |
| AC-4 | required   | Core correctness — shell affected |
| AC-5 | required   | Prevents future drift between the two maps |
| AC-6 | required   | Non-regression gate |

## Progress Log

| Date       | Update                                                                 | Evidence                        |
| ---------- | ---------------------------------------------------------------------- | ------------------------------- |
| 2026-05-02 | All fixes implemented and tested. 734 tests passing (up from 709).     | `run_tests.py` output           |

## Decision Log

| Date       | Decision                                                               | Reason                                                              | Alternatives |
| ---------- | ---------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------ |
| 2026-05-02 | Add `_EXT_TO_LANGUAGE` map rather than inline per-chunker mapping      | Single source of truth; cross-map test can enforce server alignment | Per-chunker hardcoded strings (rejected: already caused this bug)  |

## Risks

| Risk                                                                 | Mitigation                                                              |
| -------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| Existing indexes have stale language tags — language filter still broken until rebuilt | Documented in wave watchpoints; operational note only |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
