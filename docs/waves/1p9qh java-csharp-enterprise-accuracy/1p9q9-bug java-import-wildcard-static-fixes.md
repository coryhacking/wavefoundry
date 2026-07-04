# Java imports: fix wildcard-import truncation and spurious static-import edges; resolve static-import members

Change ID: `1p9q9-bug java-import-wildcard-static-fixes`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-04
Wave: `1p9qh java-csharp-enterprise-accuracy`

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

- [x] AC-1: A fixture with `import com.foo.*;` and an ambiguous simple-name receiver whose `com.foo` twin exists resolves to the wildcard-imported twin; with two wildcard imports both matching, it stays `external::`. Unit-tested both ways. — `JavaImportWildcardStaticTests.test_wildcard_import_disambiguates_ambiguous_receiver` + `test_two_wildcard_imports_both_matching_stay_external`; plus explicit-precedence and own-package-shadow guards (risk table).
- [x] AC-2: A fixture using `import static com.foo.Bar.baz;` produces no `external::static` node or edge anywhere in the payload (asserted over the whole edge set). Unit-tested. — `test_static_import_produces_no_external_static_anywhere` (whole edge set + node ids).
- [x] AC-3: After `import static com.foo.Bar.baz;`, a bare `baz()` call binds to project symbol `Bar.baz` when it exists (correct confidence per existing taxonomy) and to `external::Bar.baz` when it does not; wildcard static import resolves analogously with unique-survivor refusal. Unit-tested. — `test_static_member_bare_call_binds_project_symbol` (RECEIVER_RESOLVED), `test_static_member_bare_call_external_stays_qualified`, `test_static_wildcard_resolves_unresolved_bare_call`, `test_two_static_wildcards_refuse`, `test_same_file_definition_takes_precedence_over_static_import`.
- [x] AC-4: Non-Java candidate extraction is byte-identical on a representative multi-language fixture set (regression guard on the shared regex path). Unit-tested. — `NonJavaImportCandidateRegressionTests` (Kotlin/C#/Go/TypeScript baselines captured on the pre-change tree 2026-07-04 and pinned exactly; shared regex + `_RELATION_KEYWORD_NOISE` untouched).
- [x] AC-5: `GRAPH_BUILDER_VERSION` bumped; `python3 .wavefoundry/framework/scripts/run_tests.py` passes; `wave_validate` clean; no `__pycache__` under `scripts/`. — bumped `"36"` → `"37"` with a changelog entry covering the whole wave (single coordinated bump; later lanes do not re-bump); full suite 4373 tests OK (42 files, incl. 15 new); `__pycache__` clean.

## Tasks

- [x] Implement Java import-declaration structured capture (explicit / wildcard / static / static-wildcard) replacing or preceding the regex fallback for Java. — `_java_import_facts` + Java branch in the `is_import` block of `walk_definitions` (returns before the shared regex path; grammar shape verified empirically against tree-sitter-java).
- [x] Wire wildcard package prefixes into the import-disambiguation pass; wire static-import members into bare-call resolution; strip the `static` token. — `_build_imports_by_file` now also returns `wildcard_imports_by_file`; wildcard-participation block in `_resolve_external_call_target` (after explicit-import check, unique-survivor + own-package-shadow guard); `java_static_members`/`java_static_wildcards` feed `_resolve_java_call_target` for bare calls; the `static` modifier is structural in the Java path, never a candidate (no `_RELATION_KEYWORD_NOISE` change — AC-4 forbids touching the shared filter).
- [x] Tests per AC-1..AC-4; bump `GRAPH_BUILDER_VERSION` with changelog entry. — 11 tests in `JavaImportWildcardStaticTests`, 4 in `NonJavaImportCandidateRegressionTests`; version-pin test updated 36→37.
- [x] Run `run_tests.py` + `wave_validate`; clean `__pycache__`. — 4373 tests OK; `wave_validate` clean; no `__pycache__`.

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
| 2026-07-04 | Both defects reproduced live pre-change (`import com.foo.*;` → `['com.foo.']`; `import static com.foo.Bar.baz;` → `['static', 'com.foo.Bar.baz']`); AC-4 baselines (Kotlin/C#/Go/TS) captured on the pre-change tree. Implemented: `_java_import_facts` structured parser + Java `is_import` branch, wildcard map in `_build_imports_by_file` → wildcard-participation pass in `_resolve_external_call_target` (unique-survivor + own-package-shadow guard), static-import member/wildcard maps → `_resolve_java_call_target` bare-call resolution, `GRAPH_BUILDER_VERSION` 36→37 (single wave-covering bump). 15 new tests; full suite 4373 OK; `wave_validate` clean. Change implemented. | `graph_indexer.py` (`_java_import_facts`, `_resolve_java_call_target`, `_build_imports_by_file`, `_resolve_external_call_target`, `_extract_tree_sitter_artifact`); `tests/test_graph_indexer.py::JavaImportWildcardStaticTests` + `NonJavaImportCandidateRegressionTests`; `run_tests.py` 4373 tests OK. |
| 2026-07-04 | **Adversarial finding F2 fixed (fix lane).** Finding: the wildcard own-package-shadow guard derived the source's own package from its DIRECTORY (`src_file.rsplit("/",1)[0]`) while the same-package tier 40 lines below keys on the parsed `package` declaration — a source whose declared package lives outside its mirroring directory bound a wildcard twin that Java shadowing forbids (probe A9), and on an `extends` target the wrong-twin supertype minted wrong inherited call binds in untouched files (probe F2-AMP). Fix: `_pkg_key` (declared package, `pkg:`/`dir:` disjoint keying, directory fallback) hoisted and shared by BOTH the wildcard guard and the same-package tier — own-package identity for the source and for candidate matching now keys on the declared package, consistent with the 1p9qb stance. Probes A9 + F2-AMP flip to correct (own-package twin binds; wildcard twin refused); A1/A1b/A2/A3/A6/A7 and all other probe scenarios byte-identical. Tests: `test_own_package_shadow_keys_on_declared_package_not_directory` (A9 shape) + `test_wildcard_shadow_guard_on_extends_target_uses_declared_package` (F2-AMP shape) in `JavaImportWildcardStaticTests`; existing ambiguity suite untouched; full suite 4435 OK. No `GRAPH_BUILDER_VERSION` re-bump (v37 covers the wave; pre-release fix to unreleased behavior). | `graph_indexer.py::_resolve_external_call_target` (hoisted `_pkg_key`, guard rekeyed); probe diffs `/tmp/probe1_before.txt` vs `/tmp/probe1_after.txt` (only A8/A8b/A9 lines changed); `run_tests.py` 4435 tests OK. |
| 2026-07-04 | Capability note (adversarial A9b + architecture finding): wildcard/explicit import disambiguation matches path-derived module strings, so under nested source roots (`src/main/java`) the wildcard tier is inert — it fails closed (candidates stay `external::`), a recall-only limitation with no precision risk. Flagged for external-pack release validation. | Probe A9b + architecture review lane, 2026-07-04. |


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
