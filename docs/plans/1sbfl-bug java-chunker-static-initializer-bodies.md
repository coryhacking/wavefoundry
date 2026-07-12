# Java Chunker Drops Static/Instance Initializer Bodies (Retrieval Blind Spot for Literal-Rich Init Blocks)

Change ID: `1sbfl-bug java-chunker-static-initializer-bodies`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-07-11
Wave: TBD

## Rationale

Field-confirmed during the 1.12.0 RC retest (2026-07-11, Java consumer repo): the operator's error-string lookup ("Unable to find unambiguous method") missed in BOTH the vector and lexical layers — and the root cause is chunker coverage, not retrieval. The Java chunker never captures static (or instance) initializer bodies: the field repo's `MessagesResourceBundle` chunks contain only the symbols outline, namespace, imports, and the field declaration truncated at `= new Ha…` — the ~40 `messages.put("...", "...")` string literals in the static initializer exist in **no chunk**, so they are invisible to dense retrieval and to the FTS5 lexical layer **by construction**. The 1sbfj backfill repair made the lexical layer complete over what is chunked; this closes the gap in what gets chunked.

The pattern is common in real Java code: message/error catalogs, lookup-map registration, driver/handler registration, and constant tables all live in `static { … }` blocks — exactly the literal-rich content that exact-string lookups (error messages, config keys) target, which is the lexical layer's documented reason for existing.

## Requirements

1. **Java initializer bodies become chunk content:** `static { … }` and instance `{ … }` initializer blocks in Java are captured into chunks (either as their own chunk per block, or attached to the enclosing class chunk — decide by the chunker's existing granularity conventions), so their string literals and calls are retrievable by both the dense and lexical layers.
2. **Long field-initializer expressions are not truncated to invisibility:** a field declaration whose initializer expression is large (e.g. a builder chain or array/map literal spanning many lines) retains its literal content in chunk text within the chunker's normal size limits — the field-repo symptom showed `= new Ha…` truncation hiding everything after the constructor name. Audit whether this is the same defect (initializer body dropped by the declaration node's text extraction) or a separate truncation rule, and fix or explicitly document the boundary.
3. **Census before fix:** verify whether the same gap exists in the other tree-sitter chunker languages that have initializer-like constructs (C# static constructors, Kotlin `init` blocks if supported) and record the findings; fix Java at minimum, others if the same mechanism covers them cheaply.
4. **`CHUNKER_VERSION` bump:** chunk content changes for existing files → the version bump triggers the full re-chunk/re-embed on upgrade per the established contract (upgrade seed step 10 already documents the rebuild path).
5. **Regression fixture:** a Java class with a static initializer containing distinctive string literals (mirroring the field shape: map-registration catalog) must surface those literals via chunk text, and an exact-string lexical search must hit it.

## Scope

**Problem statement:** literal-rich Java initializer blocks are invisible to all retrieval layers because the chunker never emits their bodies.

**In scope:**

- `chunker.py` Java handling (tree-sitter node selection for initializer blocks; field-declaration initializer text).
- Census of the sibling languages' initializer constructs.
- `CHUNKER_VERSION` bump + fixture.

**Out of scope:**

- Retrieval-layer changes (1sbfj made lexical complete over chunked content; nothing to do there).
- New languages.

## Acceptance Criteria

- [ ] AC-1: A fixture Java class with a `static { … }` block of `map.put("literal-key", "literal message")` entries produces chunk text containing those literals, and `fts_search`/`code_search` exact-string lookup hits the class.
- [ ] AC-2: The field symptom is reproduced pre-fix by the fixture (literals in no chunk) and gone post-fix — pinned as a test, not a manual check.
- [ ] AC-3: The census findings for C#/other supported languages' initializer constructs are recorded in this doc (fixed or explicitly deferred with rationale).
- [ ] AC-4: `CHUNKER_VERSION` is bumped in the same change; the upgrade path's rebuild contract covers existing repos.
- [ ] AC-5: Full framework tests pass bytecode-free; docs validation passes.

## Tasks

- [ ] Census: how the Java grammar exposes initializer blocks; whether the field-declaration truncation is the same mechanism.
- [ ] Capture initializer bodies into chunks per the chunker's granularity conventions.
- [ ] Sibling-language census (C# static constructors at minimum); fix or defer with rationale.
- [ ] Bump `CHUNKER_VERSION`; add the catalog-class fixture; run suite + validation.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| census | implementer | — | Grammar/node evidence first |
| chunker-fix | implementer | census | Java capture + version bump |
| tests-docs | qa-reviewer | chunker-fix | Fixture + suite + census record |


## Serialization Points

- Single-change scope; the pre-fix reproduction fixture (AC-2) gates the fix landing.

## Affected Architecture Docs

- `docs/architecture/chunking-and-indexing-pipeline.md` — initializer-body coverage note.
- N/A otherwise: chunker-internal coverage fix, no boundary change.

## AC Priority

(Populated at Prepare wave.)


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The field-reported blind spot. |
| AC-2 | required | Reproduce-then-fix discipline. |
| AC-3 | important | Same mechanism likely spans languages; census is cheap. |
| AC-4 | required | Chunk-content change without the bump leaves field repos stale silently. |
| AC-5 | required | Standard verification gate. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-11 | Drafted from the operator's 1.12.0 RC retest finding: `MessagesResourceBundle`'s ~40 `messages.put(...)` literals exist in no chunk (chunks = symbols outline, namespace, imports, field declaration truncated at `= new Ha…`); error-string lookup missed both layers by construction. Explicitly pre-existing and unrelated to the RC-blocking backfill defect (1sbfj). | Field retest report 2026-07-11; field repo chunk inspection. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
|      |          |        |              |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| `CHUNKER_VERSION` bump forces a fleet-wide full re-embed | The established, documented upgrade cost for chunk-content changes; batch with other pending chunker work if any exists when this is scheduled. |
| Initializer chunks bloat classes with huge static tables | Existing chunk-size limits apply; the census decides own-chunk vs class-attached granularity. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
