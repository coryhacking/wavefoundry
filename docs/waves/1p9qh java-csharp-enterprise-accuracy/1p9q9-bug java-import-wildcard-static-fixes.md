# Java imports: fix wildcard-import truncation and spurious static-import edges; resolve static-import members

Change ID: `1p9q9-bug java-import-wildcard-static-fixes`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-07-03
Wave: TBD

## Rationale

Two confirmed defects in Java import extraction (guru investigation, 2026-07-03):

1. **Wildcard imports are truncated into useless candidates.** Java's `import_declaration` node exposes no field matching `_ts_relation_field_names` (`graph_indexer.py:2462`), so import targets fall to the generic regex fallback (`_ts_relation_candidates`, `graph_indexer.py:5240`: `re.findall(r"[A-Za-z_][A-Za-z0-9_.$:#/\-]*", text)`). The character class has no `*`, so `import com.foo.*;` yields the candidate `com.foo.` (trailing dot, truncated at the asterisk). Wildcard imports therefore never participate in import-edge disambiguation — a receiver type imported via wildcard looks import-less and either stays `external::` or leans on the same-directory fallback.
2. **Static imports emit a spurious edge and resolve nothing.** `static` is not in `_RELATION_KEYWORD_NOISE` (`graph_indexer.py:284-287`), so `import static com.foo.Bar.baz;` produces two candidates: the real `com.foo.Bar.baz` and a bare `static` token that becomes a fake `imports → external::static` edge in every file using static imports. Additionally, statically-imported members are not used to resolve bare calls (`baz()` after the static import), which currently depend on the uppercase-first-letter heuristic (`_resolve_java_identifier_type`, `graph_indexer.py:2663-2664`) that only covers `ClassName.method()` shapes.

Both defects are graph-pollution and recall bugs in the most enterprise-critical language. No test today covers wildcard or static imports (test-suite census confirmed).

## Requirements

1. **Wildcard import capture.** `import com.foo.*;` produces a usable package-prefix import fact (e.g. target `com.foo` marked as wildcard) instead of the truncated `com.foo.` token. The import-disambiguation pass uses it: an ambiguous simple-name candidate whose qualified name/package matches a wildcard-imported package prefix is preferred exactly as an explicit import would be, with the same unique-survivor rule (two candidates both matching wildcard imports → stay `external::`).
2. **No spurious `static` token.** `import static ...;` never emits an `external::static` edge; the modifier is stripped (via `_RELATION_KEYWORD_NOISE` or a Java-specific pre-filter, whichever is idiomatic to the extraction path).
3. **Static-import member resolution.** `import static com.foo.Bar.baz;` records that bare `baz(...)` calls in this file may target `Bar.baz`; resolution binds through the existing unique-candidate machinery (if `Bar.baz` resolves to a project symbol, bind; else `external::Bar.baz` — qualified, not bare). `import static com.foo.Bar.*;` is captured as a wildcard static import and used analogously for otherwise-unresolved bare calls, unique-survivor rule intact.
4. **No cross-language drift.** The regex fallback change (if made in shared code) must not alter candidates for any other language; prefer a Java-scoped path if the shared regex cannot change safely.
5. **Version bump + tests.** `GRAPH_BUILDER_VERSION` bumped; adversarial tests pin: wildcard disambiguation (positive + two-wildcard refusal), no-`external::static` assertion, static member bind, static wildcard bind, and unchanged non-Java behavior.

## Scope

**Problem statement:** Wildcard imports are invisible to disambiguation and static imports pollute the graph with fake external nodes while resolving nothing — both silently degrade Java accuracy on exactly the import styles enterprise codebases use heavily.

**In scope:**

- Wildcard and static import capture in Java import extraction; participation in import-edge disambiguation and bare-call resolution as specified.
- Removal of the spurious `static` candidate.
- Adversarial tests + `GRAPH_BUILDER_VERSION` bump.

**Out of scope:**

- Kotlin/other-language import semantics (Kotlin has no `import static`; its aliasing is already handled).
- Inheritance-based resolution (`1p9qa`), receiver-form extensions (`1p9qb`).
- Any change to explicit (non-wildcard, non-static) import handling, which works today.

## Acceptance Criteria

- [ ] AC-1: A fixture with `import com.foo.*;` and an ambiguous simple-name receiver whose `com.foo` twin exists resolves to the wildcard-imported twin; with two wildcard imports both matching, it stays `external::`. Unit-tested both ways.
- [ ] AC-2: A fixture using `import static com.foo.Bar.baz;` produces no `external::static` node or edge anywhere in the payload (asserted over the whole edge set). Unit-tested.
- [ ] AC-3: After `import static com.foo.Bar.baz;`, a bare `baz()` call binds to project symbol `Bar.baz` when it exists (correct confidence per existing taxonomy) and to `external::Bar.baz` when it does not; wildcard static import resolves analogously with unique-survivor refusal. Unit-tested.
- [ ] AC-4: Non-Java candidate extraction is byte-identical on a representative multi-language fixture set (regression guard on the shared regex path). Unit-tested.
- [ ] AC-5: `GRAPH_BUILDER_VERSION` bumped; `python3 .wavefoundry/framework/scripts/run_tests.py` passes; `wave_validate` clean; no `__pycache__` under `scripts/`.

## Tasks

- [ ] Implement Java import-declaration structured capture (explicit / wildcard / static / static-wildcard) replacing or preceding the regex fallback for Java.
- [ ] Wire wildcard package prefixes into the import-disambiguation pass; wire static-import members into bare-call resolution; strip the `static` token.
- [ ] Tests per AC-1..AC-4; bump `GRAPH_BUILDER_VERSION` with changelog entry.
- [ ] Run `run_tests.py` + `wave_validate`; clean `__pycache__`.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| ws1-import-capture | implementer | — | Structured Java import parsing (explicit/wildcard/static forms); spurious-token removal. |
| ws2-resolution-wiring | implementer | ws1-import-capture | Wildcard prefixes in disambiguation; static members in bare-call resolution. |
| ws3-tests | implementer | ws2-resolution-wiring | Adversarial + regression tests; version bump verification. |


## Serialization Points

- Shares the Java import/disambiguation region of `graph_indexer.py` with `1p9qa` (inheritance) and `1p9qb` (receivers) — land this change first within the wave; it is smallest and the other two build on correct import facts.
- Single coordinated `GRAPH_BUILDER_VERSION` bump at wave integration.

## Affected Architecture Docs

N/A beyond the per-language capability notes audit shared by the wave — defect fix restoring intended import semantics; no boundary, flow, or contract change.

## AC Priority

(Populated at Prepare wave.)


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | Wildcard participation is the recall half of the fix. |
| AC-2 | required | The fake `external::static` node is the pollution half; it must be provably gone. |
| AC-3 | required | Static-import member resolution is what makes the fix complete rather than cosmetic. |
| AC-4 | required | The shared regex path serves every language; silent drift there is a cross-language regression. |
| AC-5 | required | Standing version-bump and merge gates. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-03 | Scoped from the Java/SQL accuracy investigation. Both defects confirmed by code trace: regex character class lacks `*` (`graph_indexer.py:5240`), `static` absent from `_RELATION_KEYWORD_NOISE` (`graph_indexer.py:284-287`); no field-name match for Java `import_declaration` (`graph_indexer.py:2462`); no wildcard/static-import tests exist. | Guru investigation 2026-07-03; `graph_indexer.py:284-287,2462,2663-2664,5240`. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-03 | Structured Java import parsing (walk the `import_declaration` node) rather than widening the shared regex (approach A). | The defect root is regex-over-AST for a node the grammar fully structures; parsing the node gives exact explicit/wildcard/static classification and cannot perturb other languages. | (B) Add `*` to the shared regex character class — weakness: changes candidate extraction for every language and still cannot distinguish static from regular imports; the cheap fix creates a cross-language risk the structured fix avoids. (C) Only strip the `static` token, defer wildcard/static resolution — weakness: removes pollution but leaves both recall gaps; half a fix for the same test surface. |
| 2026-07-03 | Wildcard imports participate in disambiguation with the same unique-survivor rule as explicit imports. | A wildcard import is genuine visibility evidence in Java; treating it weaker than the same-directory heuristic (which already binds) would be incoherent. Two matching wildcards refuse — never guess. | Treat wildcard as no-evidence — rejected: leaves the recall gap; weaker than the directory heuristic already trusted. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Wildcard-based binding binds a twin that the author shadowed by an explicit import elsewhere in the file. | Explicit imports keep precedence (checked first, as today); wildcard participates only when explicit resolution fails; precedence is unit-tested. |
| Static-import bare-call resolution collides with same-file function names. | Same-file definitions keep precedence (existing scope-first order); static-import binding applies only to otherwise-unresolved bare calls; tested. |
| Shared-regex refactor perturbs another language's candidates. | Approach A avoids touching the shared regex; AC-4 regression fixture guards the fallback path regardless. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
