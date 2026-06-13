# Member-access constant reads (graph `reads` for `A.B.C` qualified constant access)

Change ID: `1p4up-enh member-access-constant-reads`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-11
Wave: `1p4u5 hardware-aware-embedding-providers`

## Rationale

The 1p4ls function→constant `reads` edge is **identifier-based**: it resolves a bare leaf (`return LIMIT`) to a constant by unique simple name. A constant accessed via **member expression** — `Status.ACTIVE` (a TS enum member), `SolarisConstants.Network.userAgent` (a Swift nested `static let`), `Outer.Inner.TOKEN` (any 2+-level-nested const) — did **not** produce a `reads` edge, so `code_ask`'s `graph_related.readers` / `code_references`' `reads` bucket were silent for those readers. 1p4q4 explicitly **deferred** this ("enum-member access is `Enum.Member`, a member expression — a separate resolution concern"). The **Solaris (Swift)** p4su validation surfaced it as the one open finding (F/H1), and it is the JS-TS team's namespace-enum surface. This change delivers it faithfully.

A prior one-line attempt (`_simple_name` first-dot → last-dot) was **reverted**: an adversarial review proved it over-binds bare calls + reads (it widens bare-leaf resolution). The faithful mechanism is to resolve the **qualified path** by exact qname, never widening bare-leaf resolution.

## Requirements

1. A function/method-body **member-access node** (`member_expression` TS/JS; `navigation_expression` Swift/Kotlin; `field_access` Java; `member_access_expression` C#; `selector_expression` Go; `scoped_identifier` Rust; `scope_resolution` Ruby; `class_constant_access_expression` PHP) whose text is a **pure static dotted/`::` path** buffers that path; it resolves to a `reads` edge by **EXACT qname match** against a `kind="constant"` node (`::` normalized to `.`).
2. **Faithfulness (no wrong-bind):** the qualified path must equal the constant's FULL qname, not a `_simple_name` partial key (F1); `this`/`self`/`super`/`cls` heads are rejected (F2); a member-access read whose **head qualifier is a function param/local** is dropped — the access is on the local, not the type's const (F4); the **property/trailing side** of a member access is not also buffered as a bare leaf (so a trailing `value` can't wrong-bind a same-named const).
3. **No regression / reads-only:** no existing `reads`/`calls` edge is lost or changed; the member-access path is reads-only and `const_node_ids`-gated. Bare-leaf reads and the object/array-constant **head** read (`FRAMEWORK_FLOW.length` → the const) are preserved.
4. **Version bump:** the graph node/edge set changes (new `reads` edges) → `GRAPH_BUILDER_VERSION` 28→29 so consumer graphs auto-re-extract. `CHUNKER_VERSION` unchanged (no chunk-shape change); `CLUSTER_BUILDER_VERSION` unchanged (`reads` excluded from clustering).

## Scope

**Problem statement:** member-accessed constants (enum members, nested/type-level consts) produced no `reads` edge, so the wave-1p4hi `graph_related.readers` feature was silent for the most common way those constants are referenced.

**In scope:** the member-access read mechanism + the F1/F2/F4 + property-leaf faithfulness guards across all 8 member-access languages (+ Python via its own extractor, unchanged); the `GRAPH_BUILDER_VERSION` bump; tests.

**Out of scope:**
- TS namespace **plain** const read via `NS.LIMIT` (the namespace const node is stored bare `LIMIT`, not `NS.LIMIT`) — pre-existing node-qname inconsistency, not this mechanism.
- Rust **impl-associated** const detection (registered `kind="function"`, never reaches `const_node_ids`) — a pre-existing constant-DETECTION gap in another part of the indexer.
- The pre-existing bare-leaf local-shadow limitation (a bare local shadowing a const) — documented, unchanged.

## Acceptance Criteria

- [x] AC-1: **Member-access reads fire.** A `reads` edge is produced for `Status.ACTIVE` (TS enum member), `SC.Net.userAgent` (Swift nested static — Solaris's case), `Outer.Inner.TOKEN` (Java 2-level), and the Ruby/PHP `::` forms, by exact qname. Verified by `ConstantGraphTests` subtests.
- [x] AC-2: **No qualifier-shadow over-bind.** A param/local named like a type with a static const, accessed as `Name.MEMBER`, produces NO edge (Swift/Kotlin param, Java/C# local) — while a genuine `Type.MEMBER` (not shadowed) still fires. Verified.
- [x] AC-3: **Object/array const HEAD reads preserved.** `CONST.member` / `CONST.length` where the head is the constant (`FRAMEWORK_FLOW.length`, `GRAPH_KIND_COLORS.external`) still emits the reads edge (regression for the property-leaf-skip `is`→`==` blocker the final review caught). Verified.
- [x] AC-4: **No wrong-bind / no regression.** F1 (full-qname), F2 (`this`/`self`), const-kind gate, cross-class twin, computed/dynamic-path rejection all hold; NEW-vs-baseline reads diff over real `dashboard.js` + a multi-language corpus shows **LOST=NONE**, **calls unchanged**. Verified.
- [x] AC-5: **Version + suite.** `GRAPH_BUILDER_VERSION` is `"29"`; the version test asserts it; full `run_tests.py` green.

## Tasks

- [x] `graph_indexer`: `_TS_MEMBER_ACCESS_TYPES` + `_ts_member_access_path` (pure-static path, `::`→`.`); buffer the path in `walk_definitions`; resolve by exact qname (F1 full-qname gate in the reads loop).
- [x] F2: reject `this`/`self`/`super`/`cls` heads in `_ts_member_access_path`.
- [x] F4 qualifier-shadow guard: `_TS_BINDING_NODE_TYPES` + `_ts_binding_names` (name/pattern/left fields; never a type); collect per-function `func_locals`; drop a member-access read whose head is a local. Property-leaf skip: `_ts_is_member_property_leaf` (object = first named child; `==` not `is`).
- [x] Bump `GRAPH_BUILDER_VERSION` 28→29 (graph_indexer.py) + update the version-assertion test.
- [x] Tests: member-access reads per language; qualifier-shadow suppressed + legit fires; instance-access clean; object/array head read; `_simple_name`-stays-split guard.

## Affected Architecture Docs

`docs/architecture/graph-index-system.md` — constant detection / `reads` edge: member-access qualified reads now produce a `reads` edge; `GRAPH_BUILDER_VERSION` 29.

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-11 | Implemented after reverting the unfaithful `_simple_name` rsplit one-liner (a review found it over-binds calls + reads, incl. dropping 5 correct `external::url` import-reads on a real file). Member-access PATH approach: exact-qname, const-gated, never widens bare-leaf resolution. **Two adversarial faithfulness reviews:** the first found F1 (minor over-fire) + F2 (nit) + F4 (qualifier-shadow major) — all fixed; the final review found a **blocker** (`_ts_is_member_property_leaf` used `is` on tree-sitter wrappers → blanket-skip → dropped object/array const HEAD reads like `FRAMEWORK_FLOW.length`) — fixed `is`→`==`. Final state CLEAN: false-suppress + residual-over-fire dimensions clean, regression LOST=NONE (incl. real dashboard.js), calls unchanged. Full suite **3138 green**. | Reviews wf_0119a242-52d (rsplit, reverted), wf_4d20893f-ca1 (member-path F1/F2/F4), wf_112af632-40c (final, blocker); `graph_indexer.py`; `tests/test_graph_indexer.py`. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-11 | Resolve member-access reads by EXACT QUALIFIED PATH (not bare-leaf widening). | A path keyed by its full qname can't be matched by a same-leaf param/import/bare-call, so it introduces none of the over-binds the `_simple_name` rsplit did. | rsplit `_simple_name` — REVERTED (3 verified over-binds + a real-repo import-read regression). |
| 2026-06-11 | Skip the property/trailing leaf of a member access (member-path resolves it instead). | Removes the pre-existing trailing-member leaf over-fire; the member-path is a faithful, regression-free replacement (LOST=NONE). | Leave the leaf — keeps a trailing-member shadow over-fire. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| A graph-resolution change silently over/under-fires (the rsplit lesson) | Two adversarial faithfulness reviews (NEW-vs-baseline diffs on real + crafted corpora, long names to dodge the short-symbol prune); regression diff LOST=NONE; +regression tests for the patterns the suite didn't cover. |
| Per-language member-access / binding node-type coverage gaps | Node types probed empirically per language; binding-name extraction uses name/pattern/left fields (never a type → no false-suppress); residual gaps (Rust impl-const detection, TS namespace plain-const) scoped OUT + documented. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
