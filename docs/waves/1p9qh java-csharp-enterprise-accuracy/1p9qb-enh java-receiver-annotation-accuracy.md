# Java accuracy: this.field receivers, annotation-type kind fix, and package-declaration-keyed disambiguation

Change ID: `1p9qb-enh java-receiver-annotation-accuracy`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-04
Wave: `1p9qh java-csharp-enterprise-accuracy`

## Rationale

Three verified Java accuracy gaps below the inheritance tier (guru investigation, 2026-07-03):

1. **`this.field.method()` and `field.method()` via `field_access` receivers give up.** `_resolve_java_receiver_type` resolves a bare identifier receiver through scope-walked declarations (`_search_java_declarations_in_scope`, `graph_indexer.py:2618`), but `field_access` receivers (`this.repo.save()`, and any qualified field path) hit the catch-all "uncertain" branch (`graph_indexer.py:2690-2691`) — even though the field's declared type is exactly what the scope walk already finds for the bare form. Enterprise Java style guides commonly mandate `this.` for field access, so idiomatic code loses receiver resolution that non-`this.` code gets.
2. **`@interface` declarations are misclassified and a merge path is dead.** `annotation_type_declaration` matches `_ts_is_definition_node` (ends `_declaration`, `graph_indexer.py:2045`) but no substring in `_ts_kind_for_definition` (`graph_indexer.py:1968-2015`), so annotation types get kind `"function"`. Separately, the Java merge-kind set at `graph_indexer.py:6463` lists `"annotation_type"`, a kind string never produced — the merge condition at `:6598` can never fire for it (dead code masking the misclassification).
3. **Same-package disambiguation keys on directory strings, not the parsed `package` declaration.** The v25 tier compares `cfile.rsplit("/", 1)[0]` (`graph_indexer.py:7896-7926`); Java packages usually mirror directories, but the package-collapse mechanism (`test_java_matching_package_collapses`, `test_graph_indexer.py:3141`) already parses real `package` statements — the disambiguation tier should key on the same declared fact, making the bind semantics-backed rather than layout-backed (and consistent with `1p9q5`'s declared-namespace stance for C#).

## Requirements

1. **`this.<field>` and single-segment `field_access` receivers.** `this.repo.save()` resolves `repo` through the same scope-walked declaration lookup as the bare form; a `field_access` whose object is `this` (or the enclosing class name for static fields) and whose field is a declared field binds identically to the bare-identifier path, same confidence. Deeper chains (`a.b.c.method()`) and non-`this` objects remain in the give-up branch (documented).
2. **Annotation-type kind.** `annotation_type_declaration` classifies as kind `"class"` (consistent with interface treatment) or a dedicated `annotation` kind — pick whichever the existing kind consumers handle without special-casing (decide at implementation; default `"class"`); the `graph_indexer.py:6463` merge-kind set entry is corrected to the kind actually produced, reviving the basename-merge path for annotation types.
3. **Package-declaration keying.** The same-package disambiguation tier keys Java/Kotlin candidates on the parsed `package` declaration (reusing the collapse mechanism's extraction) with directory comparison as fallback when no declaration exists; Go keeps its existing directory semantics (Go packages ARE directories). Behavior change is narrow: files whose declared package differs from their directory no longer falsely disambiguate; split-directory same-package files now correctly do.
4. **Version bump + tests + calibration.** `GRAPH_BUILDER_VERSION` bumped; adversarial tests for each item; pack Java fixture counts before/after recorded.

## Scope

**Problem statement:** Idiomatic `this.`-qualified field calls lose resolution that bare calls get; annotation types are mis-kinded with a dead merge path; and package disambiguation trusts directory layout instead of the declared package fact the indexer already parses elsewhere.

**In scope:**

- `this.field` / declared-field `field_access` receiver resolution (single segment).
- Annotation-type kind correction + merge-kind set fix.
- Package-declaration keying for the Java/Kotlin disambiguation tier (Go unchanged).
- Adversarial tests, calibration counts, version bump.

**Out of scope:**

- Deep chained receivers (`a.b.c.m()`), cast/lambda receivers, generics (documented give-ups; candidates for a later change with its own calibration).
- Inheritance-based resolution (`1p9qa`), import fixes (`1p9q9`).
- Annotation-*argument* capture (owned by `1p9qg`'s ORM mapping and future annotation-edge work).

## Acceptance Criteria

- [x] AC-1: `this.repo.save()` with `repo` a declared field of known type binds identically (target + confidence) to the bare `repo.save()` form; static-field access via the enclosing class name binds likewise; a deeper chain (`this.a.b.m()`) still refuses. Unit-tested all three. — `JavaFieldReceiverResolutionTests`: `test_this_field_receiver_binds_identically_to_bare_form` (same target AND same confidence as the bare-form twin fixture), `test_static_field_via_enclosing_class_name_binds`, `test_deeper_chain_still_refuses`, plus `test_non_this_object_field_path_still_refuses` and `test_undeclared_this_field_refuses` (inherited/ghost field never guessed).
- [x] AC-2: An `@interface` declaration produces the corrected kind; a file whose basename matches its annotation type merges via the revived path; no other language's kind classification changes (regression fixture). Unit-tested. — kind `"class"` (see Decision Log); `JavaAnnotationTypeKindTests`: `test_annotation_type_declaration_classifies_as_class`, `test_annotation_basename_match_merges_via_revived_path` (collapsed_pair fires for `Cacheable.java` + `@interface Cacheable`), `test_kind_classification_regression_pins_other_languages` (Java neighbors, `annotation_type_element_declaration` stays `function`, Rust/TS/JS pins, sql/config/markup modes).
- [x] AC-3: Two same-named classes in different directories with the SAME declared package now disambiguate (split-directory case); two in the same directory with DIFFERENT declared packages now refuse; Go behavior byte-identical on its existing fixtures. Unit-tested all three. — `JavaPackageDeclarationKeyingTests`: both flip directions + declaration-less directory fallback (pre-1p9qb behavior preserved), plus pure-function pins: Go keying ignores the package map entirely, and `pkg:`/`dir:` key spaces never cross-match. Existing Go fixtures (`test_go_qualified_receiver_*`, `test_go_cross_package_method_resolves`) green unmodified — the Go branch is byte-for-byte the former code path.
- [x] AC-4: Existing Java resolution suite (`test_java_cross_file_member_call`, ambiguity suite) stays green unmodified; pack Java fixture before/after counts recorded in the Progress Log. — full suite green with zero edits to existing tests (the 1p4er same-package tests pass under declared-package keying because their fixtures' declarations match their directories); calibration on an external enterprise Java corpus in the Progress Log (this repo has zero Java files — change inert on the self-hosted index by construction).
- [x] AC-5: `GRAPH_BUILDER_VERSION` bumped; adversarial review lane covers the new receiver form (wrong-field-shadowing cases); `python3 .wavefoundry/framework/scripts/run_tests.py` passes; `wave_validate` clean; no `__pycache__` under `scripts/`. — *version + suite halves DONE:* v37 coordinated single wave bump already covers `1p9qb` in its changelog (audit-and-skip: no re-bump); 4,423 tests OK across 42 files (16 new); `wave_validate` clean; no `__pycache__`. Shadowing adversarial cases are ALSO unit-pinned in-lane (`test_local_shadow_never_diverts_this_field`, `test_parameter_shadow_never_diverts_this_field`). *Adversarial review lane runs at wave review, not in this lane — left unchecked until dispositioned.* — Adversarial clause DISCHARGED 2026-07-04 (consolidated lane): the new receiver form survived the shadowing adversarials in both directions (local shadow: `this.x` uses the FIELD, bare `x` the local — divergence is Java-correct), ambiguous-twin field types and wrong-class static receivers refused; package keying held both flips plus the layout-vs-semantics trap and Kotlin parity (probe C6 + unit pin added in the fix batch); package-declaration-only edits in untouched files re-keyed oracle-equivalently both directions. The one seam finding attributable to this change's stance (the 1p9q9 wildcard guard still keying on directory) was fixed in-session — one shared `_pkg_key` closure now serves both tiers.

## Tasks

- [x] Extend `_resolve_java_receiver_type` for `this.<field>` / declared-field single-segment `field_access` (and enclosing-class static fields); keep deeper chains refusing. — new `field_access` branch (before the catch-all; the sibling `super.` branch untouched) + `_search_java_field_declarations` (direct class-body `field_declaration` members ONLY — no descent, so locals/params/initializer-block locals can never divert) + `_find_enclosing_java_class_node` (node-returning sibling of the existing name helper, which now delegates to it).
- [x] Fix `_ts_kind_for_definition` classification for `annotation_type_declaration` + correct the `graph_indexer.py:6463` merge-kind entry. — EXACT-match branch returns `"class"` (`annotation_type_element_declaration` members deliberately keep the `function` fallthrough); the dead `"annotation_type"` merge-kind token is removed — annotation types now produce kind `"class"`, so the existing `"class"` entry carries the revived basename merge.
- [x] Rekey the Java/Kotlin same-package tier on parsed `package` declarations (reuse the collapse mechanism's parse; directory fallback); leave Go on directory keying. — `_JAVA_PKG_DECL_RE`/`_KOTLIN_PKG_DECL_RE` mirror `graph_query._DIRECTORY_AGG_LANGUAGES` (the package-collapse mechanism; sync comment at both definitions is one-sided here to avoid touching `graph_query`); extraction stores `declared_package` on the file's module node (node-borne → incremental merges recover it from per-file fragments, no new state); `_build_candidate_indexes` returns a fourth `pkg_by_file` map threaded through the finalize ctx into `_resolve_external_call_target`; `pkg:`/`dir:` prefixes keep declared and fallback key spaces disjoint; the Go branch is the former code verbatim.
- [x] Adversarial + regression tests per AC-1..AC-4; calibration counts. — 16 new tests: `JavaFieldReceiverResolutionTests` (7, incl. both shadow adversarials), `JavaAnnotationTypeKindTests` (3, incl. the cross-language kind-pin fixture), `JavaPackageDeclarationKeyingTests` (5, incl. two pure-resolver adversarial pins), `JavaPackageKeyingIncrementalTests` (1, in the 1p9q2 differential harness: a package-declaration-only flip in a candidate file demotes/rebinds an UNTOUCHED caller, oracle-equivalent both directions — the new keying shape the harness didn't previously drive). Calibration in the Progress Log.
- [x] Bump `GRAPH_BUILDER_VERSION`; run `run_tests.py` + `wave_validate`; clean `__pycache__`. — audit-and-skip: v37 coordinated single wave bump landed with `1p9q9`, its changelog already names `1p9qb`'s three mechanisms (no re-bump); 4,423 tests OK; `wave_validate` clean; no `__pycache__` under `scripts/`.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| ws1-field-receivers | implementer | — | `this.field`/`field_access` receiver extension in the Java resolver. |
| ws2-annotation-kind | implementer | — | Kind classification + merge-kind fix (independent of ws1). |
| ws3-package-keying | implementer | — | Declared-package keying for the disambiguation tier (independent). |
| ws4-tests-calibration | implementer | ws1-field-receivers, ws2-annotation-kind, ws3-package-keying | Adversarial/regression tests; calibration counts. |


## Serialization Points

- Shares `_resolve_java_receiver_type` with `1p9qa`'s `super.`/inherited-method work — land `1p9qa` ws3 and this ws1 in a coordinated order (disjoint branches of the same dispatch function).
- Shares the disambiguation tier region with `1p9q9` — land after it.
- Single wave-level `GRAPH_BUILDER_VERSION` bump.

## Affected Architecture Docs

Per-language capability notes (shared wave audit of `docs/specs/mcp-tool-surface.md` and any capability matrix): Java receiver-form coverage and the package-declaration keying stance. No boundary/flow impact.

## AC Priority

(Populated at Prepare wave.)


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The `this.` idiom gap penalizes exactly the style enterprise guides mandate. |
| AC-2 | required | Mis-kinded nodes and dead merge paths are latent wrongness; small, verifiable fix. |
| AC-3 | required | Semantics-backed keying is the faithfulness upgrade; both flip directions must be tested. |
| AC-4 | required | The existing ambiguity suite is the regression oracle for any resolver change. |
| AC-5 | required | Standing version/adversarial/merge gates. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-03 | Scoped from the Java/SQL accuracy investigation. Confirmed: `field_access` in the give-up catch-all (`graph_indexer.py:2690-2691`) while scope walk (`:2618`) already finds field types; `annotation_type_declaration` falls through to kind `"function"` (`:1968-2015,2045`) with a dead `"annotation_type"` merge entry (`:6463,6598`); same-package tier compares directory strings (`:7896-7926`) though package parsing exists in the collapse mechanism. | Guru investigation 2026-07-03. |
| 2026-07-04 | Implemented all three workstreams in `graph_indexer.py`: `field_access` receiver branch + field-only lookup (`_search_java_field_declarations`, `_find_enclosing_java_class_node`); annotation-type kind `"class"` (exact node-type match) + dead merge-kind entry removed; declared-package keying (`declared_package` module-node property, `pkg_by_file` via `_build_candidate_indexes` 4-tuple, `pkg:`/`dir:` disjoint keys, Go branch verbatim). Grammar shapes probed live before coding (field_access object/field fields; deep-chain inner object is itself a `field_access` → refusal by construction). 16 new tests incl. an incremental differential scenario (package-declaration-only flip re-keys an untouched caller, oracle-equivalent). Full suite 4,423 OK. | `JavaFieldReceiverResolutionTests`, `JavaAnnotationTypeKindTests`, `JavaPackageDeclarationKeyingTests` (test_graph_indexer.py), `JavaPackageKeyingIncrementalTests` (test_graph_incremental_merge.py); `run_tests.py` 2026-07-04. |
| 2026-07-04 | Calibration. HONESTY NOTE: this repo has zero Java files, so the self-hosted index is inert to this change by construction; the multi-language consumer pack is an external oracle, so calibration ran on a local enterprise Java corpus — Apache Tomcat 9.0.84 `java/` tree, 1,794 files. Before → after: calls 69,802 → 69,527 (dedup: a `this.x.m()` call now produces the same typed target as its bare twin instead of a separate fallthrough attribution); project-resolved 36,131 → 36,063; external 33,671 → 33,464; RECEIVER_RESOLVED 49,551 → 49,708 (+157); EXTRACTED 13,746 → 13,314 (−432); nodes 49,771 → 49,732 (−39: basename-matching `@interface` files now merge; kinds `function` 21,669 → 21,630, `class` 2,488 → 2,527, `module` 1,764 → 1,725). Package rekeying is largely neutral on Tomcat (conventional package↔directory layout) — both flip directions are pinned by unit tests instead, which is exactly why the counts alone under-state the semantics change. | `/tmp/wf_1p9qb_calibration.py` runs on tomcat-9.0.84/java, before (pre-edit working tree, siblings landed) vs after, 2026-07-04. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-03 | Single-segment `this.field` receivers only; deeper chains keep refusing (approach A). | The single-segment case is the idiom-mandated form with zero new inference (the field's declared type is already scope-resolvable); chains require intermediate-type tracking — a different risk class needing its own calibration. | (B) Full chain resolution — weakness: each hop multiplies wrong-type risk without the explicit-declaration guarantee; deferred. (C) Skip and let `1p9qa`'s walk handle it — weakness: inheritance walk solves supertype methods, not receiver-form parsing; different gap. |
| 2026-07-03 | Package-declaration keying with directory fallback; Go unchanged. | Keys the bind to the language fact (declared package) the indexer already parses, aligning with `1p9q5`'s declared-namespace stance; fallback preserves behavior for package-less files; Go's packages are directory-defined so directory keying IS its semantics. | Keep directory keying — rejected: layout-backed binding is the exact stance `1p9q5` rejects for C#; consistency matters for the adversarial review. |
| 2026-07-04 | Annotation-type kind = `"class"` (the doc's default), decided against kind-consumer reality. | Every kind consumer already treats type declarations as `"class"` (interface/enum/record all normalize to it): the merge-kind sets, the 1p9qa inheritance kind-gate, clustering, and map rendering handle `"class"` with zero special-casing. The fix is an EXACT match on `annotation_type_declaration` so the method-shaped `annotation_type_element_declaration` body members keep `"function"`. | Dedicated `"annotation"` kind — rejected: every consumer surface (merge sets, kind gates, cluster exclusions, map legends) would need a new case for a node class with no distinct consumer behavior. |
| 2026-07-04 | Declared-package fact rides the file's module node (`declared_package` property) rather than a new threaded per-file map or finalize-time file reads. | Node-borne facts flow through the 1p9q2 per-file fragments automatically, so incremental merges recover the keying with NO new state store shape and the existing symbol-delta machinery already re-resolves affected edges (a changed file's nodes contribute their candidate keys to the delta on both sides) — differential-tested. Mirrors how `cs_file_ns` derives from C# namespace nodes. | (a) Finalize-time source reads (as the collapse view does) — rejected: finalize must stay a pure function of fragments for incremental == full. (b) Importing `graph_query` for its regex table — rejected: new cross-module dependency for two one-line patterns; mirrored constants with a sync comment instead. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A local variable shadowing a field makes `this.field` and bare `field` resolve differently — and they SHOULD (`this.` explicitly bypasses the shadow). | Resolution order for `this.<field>` consults field declarations only (skips local/param shadow), mirroring Java semantics; shadowing is an explicit adversarial test case. |
| Package rekeying flips existing binds on repos with non-conventional layouts. | Both flip directions are deliberate correctness changes, unit-tested; calibration counts make the delta visible; directory fallback covers missing declarations. |
| Annotation-kind change perturbs node counts/communities. | Version bump forces clean rebuilds; AC-2 regression fixture pins other languages; count deltas visible in calibration. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
