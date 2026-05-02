# Imports Chunk — All Languages

Change ID: `12b0v-enh imports-chunk-all-languages`
Change Status: `complete`
Owner: Engineering
Status: planned
Last verified: 2026-05-01
Wave: `12axj chunker-and-pack-improvements`

## Rationale

Dependency searches ("which files import UserRepository?") currently fail for all structured-language chunkers because import/use/package declarations fall outside every captured chunk body. Adding a `__imports__` chunk per file makes the import surface searchable via `code_search` and `code_keyword_search`.

## Requirements

1. Each structured-language chunker (Java, Scala, C#, JS/TS, Go, Rust, C/C++, Swift, Objective-C) must emit a `__imports__` chunk when the file contains at least one import/use/include/using statement or package/module declaration.
2. The chunk must carry `kind="code"`, the file's language, and `id="{path}::__imports__"`.
3. The chunk text must include a breadcrumb (`{stem} > imports`) followed by all collected import lines joined with newlines.
4. Package/module declarations (Java `package`, Rust `mod`, Go `package`, Swift import) are included.
5. No `__imports__` chunk is emitted for files that have none.
6. Existing chunk IDs and chunk content are unaffected.

## Scope

**Problem statement:** Import lines are unchunked, making dependency searches unreliable.

**In scope:**

- `__imports__` emission in: `_chunk_java_like`, `chunk_csharp`, `chunk_js_ts`, `chunk_go`, `chunk_rust`, `chunk_c_cpp`, `chunk_swift`, `chunk_objc`
- Package and `#include` lines treated as part of the imports surface
- Tests for each language asserting `__imports__` chunk content

**Out of scope:**

- Python (AST-based; `import` nodes are in the AST but not yet surfaced — follow-on)
- SQL, Shell, Markdown chunkers

## Acceptance Criteria

- AC-1: Java file with `package` and `import` lines emits `__imports__` chunk containing both
- AC-2: C# file with `using` directives emits `__imports__` chunk
- AC-3: JS/TS file with `import` statements emits `__imports__` chunk
- AC-4: Go file with `package` and `import` block emits `__imports__` chunk
- AC-5: Rust file with `use` declarations emits `__imports__` chunk
- AC-6: C++ file with `#include` lines emits `__imports__` chunk
- AC-7: Swift file with `import` statements emits `__imports__` chunk
- AC-8: File with no import lines emits no `__imports__` chunk
- AC-9: `CHUNKER_VERSION` is incremented after this change

## Tasks

- Add `__imports__` collection loop to each chunker (scan leading lines before first class/func)
- Emit chunk at end of each chunker when collected lines non-empty
- Increment `CHUNKER_VERSION`
- Add one test per language

## Agent Execution Graph

| Workstream       | Owner       | Depends On | Notes                          |
| ---------------- | ----------- | ---------- | ------------------------------ |
| imports-chunkers | implementer | —          | Edit chunker.py, test_chunker  |

## Serialization Points

- `chunker.py` and `test_chunker.py` shared with `12b0w` (Swift/ObjC) — must not run concurrently; complete `12b0w` first or merge in one pass

## Affected Architecture Docs

N/A — confined to `chunker.py` index pipeline; no boundary/flow change.

## AC Priority

| AC   | Priority    | Rationale                                   |
| ---- | ----------- | ------------------------------------------- |
| AC-1 | required    | Java is primary platform                    |
| AC-2 | required    | C# is primary platform                      |
| AC-3 | required    | JS/TS is primary platform                   |
| AC-4 | required    | Go in active use                            |
| AC-5 | required    | Rust in active use                          |
| AC-6 | important   | C++ common but headers complicate it        |
| AC-7 | required    | Swift is primary platform per user          |
| AC-8 | required    | Guard against noise chunks                  |
| AC-9 | required    | Rebuild trigger                             |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
|      |        |          |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
|      |          |        |              |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Over-capture of non-import lines (e.g. C++ preprocessor macros) | Restrict to `#include` and `#import` only for C/C++ |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
