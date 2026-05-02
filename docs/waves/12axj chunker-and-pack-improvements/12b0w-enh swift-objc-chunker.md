# Swift and Objective-C Chunker

Change ID: `12b0w-enh swift-objc-chunker`
Change Status: `complete`
Owner: Engineering
Status: planned
Last verified: 2026-05-01
Wave: `12axj chunker-and-pack-improvements`

## Rationale

Swift and Objective-C are primary iOS/macOS platforms with significant active codebases. Without dedicated chunkers, `.swift` and `.m`/`.mm` files fall through to the line-window fallback, producing poor search granularity. Swift has class/struct/enum/protocol/extension declarations, `func` methods, and `///` doc comments — all structure-chunkable for precise retrieval.

## Requirements

1. `chunk_swift` must detect `class`, `struct`, `enum`, `protocol`, `extension` declarations and emit a `__decl__` chunk per type via `_collect_decl_text`.
2. `chunk_swift` must detect `func` declarations (including `init`, `deinit`) and emit a code chunk per function/method, qualified with the containing type name when inside a type scope.
3. `chunk_swift` must extract `///` doc comments immediately preceding a declaration and emit `__doc__` chunks.
4. `chunk_objc` must detect `@interface`, `@implementation`, `@protocol` sections and emit code chunks per method (`-` and `+` selectors).
5. `chunk_objc` must extract `/** */` Doxygen and `///` doc comments immediately preceding a method and emit `__doc__` chunks.
6. Both chunkers must fall back to `_fallback_with_stem` on parse exception and when zero chunks produced.
7. Both chunkers must pass through `split_large_code_chunks`.
8. `SWIFT_EXTENSIONS = {".swift"}` and `OBJC_EXTENSIONS = {".m", ".mm"}` must be registered in `chunk_file`.
9. `.h` headers already in `C_CPP_EXTENSIONS` are unaffected.

## Scope

**Problem statement:** `.swift` and `.m` files produce line-window chunks with no structural resolution.

**In scope:**

- `chunk_swift`: type declarations, `func`/`init`/`deinit`, `///` docs, `__decl__` for types, `__imports__` for `import` lines (via `12b0v`)
- `chunk_objc`: `@interface`/`@implementation`/`@protocol`, `-`/`+` method selectors, `/** */` and `///` docs
- Extension registration in `chunk_file`
- Tests: type chunk, method chunk, doc chunk, decl chunk, fallback, dispatch

**Out of scope:**

- SwiftUI `View` body special-casing
- Objective-C category syntax (`@interface Foo (Category)`) beyond basic detection
- Swift property observers (`didSet`, `willSet`) as separate chunks

## Acceptance Criteria

- AC-1: Swift `class Foo { func bar() {} }` emits `Foo.__decl__` and `Foo.bar` code chunks
- AC-2: Swift `///` doc comment on a `func` produces a `.__doc__` chunk
- AC-3: Swift `struct`, `enum`, `protocol` each emit `__decl__` chunks
- AC-4: Swift `extension` emits a `__decl__` chunk with the extended type name
- AC-5: ObjC `@implementation Foo` with `- (void)doThing` emits a `Foo.doThing` code chunk
- AC-6: ObjC `/** */` on a method produces a `.__doc__` chunk
- AC-7: Empty Swift file returns `[]`
- AC-8: Exception in Swift chunker falls back to line-window, no crash
- AC-9: `.swift` files route to `chunk_swift` via `chunk_file`
- AC-10: `.m`/`.mm` files route to `chunk_objc` via `chunk_file`
- AC-11: `CHUNKER_VERSION` is incremented after this change

## Tasks

- Implement `chunk_swift` with type/func detection, `///` doc extraction, `__decl__` emission
- Implement `chunk_objc` with `@interface`/`@implementation`, selector detection, doc extraction
- Register `SWIFT_EXTENSIONS = {".swift"}` and `OBJC_EXTENSIONS = {".m", ".mm"}` in `chunk_file`
- Add `split_large_code_chunks` pass at end of each chunker
- Add tests covering all ACs
- Increment `CHUNKER_VERSION`

## Agent Execution Graph

| Workstream    | Owner       | Depends On | Notes                                  |
| ------------- | ----------- | ---------- | -------------------------------------- |
| swift-chunker | implementer | —          | chunk_swift + tests                    |
| objc-chunker  | implementer | —          | chunk_objc + tests                     |
| dispatcher    | implementer | both above | chunk_file routing + CHUNKER_VERSION   |

## Serialization Points

- `chunker.py` and `test_chunker.py` are shared with `12b0v` (imports chunk) — implement in same pass or complete `12b0w` first

## Affected Architecture Docs

N/A — confined to `chunker.py` index pipeline; no boundary/flow change.

## AC Priority

| AC    | Priority  | Rationale                               |
| ----- | --------- | --------------------------------------- |
| AC-1  | required  | Core Swift type+method chunking         |
| AC-2  | required  | Doc extraction standard across all langs|
| AC-3  | required  | Struct/enum/protocol are idiomatic Swift|
| AC-4  | important | Extensions are idiomatic Swift          |
| AC-5  | required  | ObjC method chunking                    |
| AC-6  | important | ObjC doc comments                       |
| AC-7  | required  | Empty file guard                        |
| AC-8  | required  | Fallback safety                         |
| AC-9  | required  | Dispatcher routing for Swift            |
| AC-10 | required  | Dispatcher routing for ObjC             |
| AC-11 | required  | Rebuild trigger                         |

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
| Swift closures increase brace depth unexpectedly | Depth counter handles nested braces; closure bodies captured in enclosing func chunk |
| ObjC method selector syntax unlike C-style | Dedicated `_OBJC_METHOD_RE` matching `-`/`+` prefix |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
