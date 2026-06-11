# Chunk TS enum / const-enum members (+ namespace const, declare const)

Change ID: `1p4q4-enh chunk-ts-enum-members`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-11
Wave: `1p4hi code-ask-agent-rerank`

## Rationale

The wave's `1p4mf` AC-2 *claimed* "enum members are distinct nodes for **TS + Swift**", but only **Swift** enum cases shipped — TS got nothing. The JS/TS chunker (`chunk_js_ts_treesitter`) has **no `enum_declaration` branch at all**, so a TS `enum Status { OK = 0, FAIL = 1 }` produces **zero chunks** for its members: their values are unretrievable by `code_ask`/`code_search`/`code_constants`, and they are absent from the graph (`code_definition`/`code_references`/`graph_related`). The delivery review corrected the over-claim (scoped TS enums OUT as a known gap). This change **delivers** them instead — TS is a major language and enums are how TS expresses named constants, so the gap is real for the pending TS validators. `namespace`-scoped const and `declare const` are folded in (cheap once inside the same chunker pass).

This **changes the chunk + graph shape**, so it bumps `CHUNKER_VERSION` 27→28→29 and `GRAPH_BUILDER_VERSION` 26→27→28 (the second step is the in-wave review re-bump — see the Progress Log; and supersedes the `p4pu` test pack — rebuild + re-validate). As a folded-in fix, `.mts`/`.cts` are now first-class across the MAIN pipeline (indexer `SOURCE_CODE_EXTENSIONS`, chunker `JS_TS_EXTENSIONS` + language map + `chunk_js_ts_treesitter`, graph_indexer code-extensions + language map) — not only `code_constants` — and parse as TypeScript (their enum members chunk and carry `language='typescript'`).

## Requirements

1. **Chunk lane:** `chunk_js_ts_treesitter` emits each **enum member** of a TS `enum` / `const enum` (incl. `export enum`) as a constant chunk — `path::Enum.Member`, breadcrumb `{stem} > Enum.Member`, `" [const]"` marker, text = `{breadcrumb}\n\n{member decl}`. A bare member (no initializer) is still chunked. Enum members nested in a namespace carry the namespace prefix.
2. **Chunk lane (folded in):** a `namespace`/`module` block's top-level `const` value declarations are chunked (qualified by the namespace name) — including the `module M { … }` keyword form (a top-level `module` node, not `internal_module`), NON-export `const` inside a namespace, `export namespace`, and the ambient `declare namespace` / `declare enum` forms; a `declare const` value declaration is chunked. JS (non-TS) is unaffected (JS has no `enum`).
3. **Graph lane:** the TS `enum_declaration` branch in `graph_indexer.walk_definitions` (the `is_definition` path, after `register_symbol`) emits each member as a `kind="constant"` node (the enum TYPE stays a class node above it), carrying the member's literal value where present; namespace-scoped members recover the enclosing namespace prefix from the AST so same-named enums in different namespaces don't collide. Constant nodes are EXEMPT from the ≤2-char short-symbol prune, so short members (`Status.OK`, `Dir.Up`) remain resolvable. The 1p4ls faithfulness gates (kind-aware resolve, reads opt-in, cluster exclusion) apply unchanged.
4. **Version bumps in the same change:** `CHUNKER_VERSION` 27→28 (chunk shape changed) and `GRAPH_BUILDER_VERSION` 26→27 (node shape changed). `CLUSTER_BUILDER_VERSION` unchanged (constants already excluded from clustering).
5. **Faithfulness:** an enum member is chunked/noded only as a member of its enum (qualified `Enum.Member`); no leakage of non-enum identifiers; `const enum` treated identically to `enum`.

## Scope

**In scope:** TS `enum`/`const enum` member chunking (chunk + graph), `export enum`, namespace-scoped const, `declare const`; the two version bumps; tests; correcting the `1p4mf` AC-2 / `1p4ls` AC-1 / `graph_indexer` version-comment claims that scoped TS enums OUT (now delivered).

**Out of scope:**
- TS `enum` member **reads** edges (a `reads` edge from a function that uses `Status.OK`) — the 1p4ls `reads` extraction is identifier-based; enum-member access is `Enum.Member` (a member expression), a separate resolution concern. Members become NODES (resolvable/listable); read-edge attribution is a follow-up.
- Kotlin bare `val` as a constant (semantically not a compile-time const — won't-do, per the delivery review).
- Other documented limitations (tree-sitter shadow guard, nested-mod, generic-walker owner, etc.) — separate.

## Acceptance Criteria

- [x] AC-1: **Enum members chunked.** `enum Status { OK = 0, FAIL = 1 }`, `const enum Dir { Up, Down }`, and `export enum Color { Red = "r" }` each produce one `" [const]"` chunk per member (`Status.OK`, `Status.FAIL`, `Dir.Up`, `Dir.Down`, `Color.Red`) with the member text. A bare member (`Dir.Up`, no initializer) is chunked. Verified by a `.ts` fixture (FAIL-not-skip).
- [x] AC-2: **Namespace const + declare const.** `namespace NS { export const NS_LIMIT = 5 }` → `NS.NS_LIMIT` const chunk; `declare const AMBIENT = 5` → an `AMBIENT` const chunk. Verified.
- [x] AC-3: **Graph nodes.** On a graph built over a `.ts` file, each enum member is a `kind="constant"` node (`Status.OK` etc.) with its value where literal; `code_definition("OK")` / a graph query resolves it — including SHORT (≤2-char) members like `Status.OK`/`Dir.Up`, which are exempt from the short-symbol prune (review D2/F1). Same-named enums in two namespaces produce distinct member nodes (review D1). Verified by `ConstantGraphTests` subtests (long, short, and namespace-scoped).
- [x] AC-4: **Version bumps.** `CHUNKER_VERSION` is `"29"`, `GRAPH_BUILDER_VERSION` is `"28"` (the in-wave review re-bump completed the namespace/module chunking and the namespace-prefixed / short-symbol-exempt member nodes — see the Progress Log); the version tests assert the new values; an index built at a prior version auto-escalates. Verified.
- [x] AC-5: **No regression / faithfulness.** JS files (no enum) unchanged; existing JS/TS const chunking (`API_URL`, arrow-const functions) unchanged; a non-enum identifier is never chunked as an enum member; full `run_tests.py` green.
- [x] AC-6: **Claim corrections.** `1p4mf` AC-2, `1p4ls` AC-1, and the `graph_indexer` `GRAPH_BUILDER_VERSION` comment are updated — TS enum members are now SHIPPED (no longer "deferred follow-up"). docs-lint green.
- [x] AC-7 (**value**): `code_constants(["OKAY"])` on a `.ts` `enum Status { OKAY = 0 }` returns `"0"` (verified live — the chunk lane → code_constants third-consumer path); `code_ask`/`code_search` surface the member chunk once the v28 index is built. Real-world confirm rides the next pack.

## Tasks

- [x] `chunk_js_ts_treesitter`: add an `enum_declaration` branch (member-per-chunk, `Enum.Member` qname, marker) + handle it inside `export_statement`; add `internal_module` (namespace) recursion with a name prefix; add `ambient_declaration` (declare const) handling.
- [x] `graph_indexer.walk_definitions` (`is_definition` path): emit the TS `enum_declaration` → per-member constant node case (the enum type node stays a class; members are children). Note: the emission is inline in the walker, NOT in `_ts_constant_decls` (which has no enum branch).
- [x] Bump `CHUNKER_VERSION` 27→28 (chunker.py) + `GRAPH_BUILDER_VERSION` 26→27 (graph_indexer.py); update the version-assertion tests.
- [x] Tests: enum-member chunking (AC-1), namespace/declare (AC-2), graph nodes (AC-3), versions (AC-4), no-regression (AC-5).
- [x] Claim corrections (AC-6): `1p4mf` AC-2, `1p4ls` AC-1, `graph_indexer:28` comment.

## Affected Architecture Docs

`docs/architecture/chunking-and-indexing-pipeline.md` + `graph-index-system.md` (constant-chunk / constant-node language coverage now includes TS enum members; `.mts`/`.cts` now first-class across the main pipeline; version table → CHUNKER 29 / GRAPH_BUILDER 28). `mcp-tool-surface.md` constant note may get a one-line touch.

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-11 | Spun up (operator) to DELIVER the TS enum members the wave's `1p4mf` AC-2 claimed but scoped out in the delivery review. Changes chunk + graph shape → CHUNKER 27→28, GRAPH_BUILDER 26→27; supersedes `p4pu`. Batched with the pending pack rebuild + Swift/JS-TS validation. | This doc. |
| 2026-06-11 | Post-implementation adversarial re-review (6 dimensions) found Requirement 2's namespace/module coverage under-delivered + graph gaps. Fixed in-session (no extra version bump — same pre-publish v28/v27): chunker now handles the `module M{}` keyword form, NON-export namespace `const`, `export namespace`, `declare namespace`, `declare enum` (review C1–C3); graph carries the namespace prefix on member nodes (D1) and exempts constant nodes from the ≤2-char short-symbol prune so `Status.OK`/`Dir.Up` resolve (D2/F1); doc points at the real `walk_definitions` emission site, not `_ts_constant_decls` (F2). +5 chunker/graph regression tests. Full suite 3121 green. | Review wf_69990b0f-6f7; chunker.py `_process_node`; graph_indexer.py member emission + short-symbol prune. |
| 2026-06-11 | Version re-bump for the review fixes above: the chunk/node-set shape DID change, so `CHUNKER_VERSION` 28→29 (completing the `module M{}` keyword form, NON-export namespace const, `export namespace`, `declare namespace`, `declare enum` chunking) and `GRAPH_BUILDER_VERSION` 27→28 (namespace-prefixed enum member nodes + constant short-symbol-prune exemption). `CLUSTER_BUILDER_VERSION` still 9 (constants excluded from clustering). Also folded `.mts`/`.cts` into the MAIN pipeline (indexer + chunker + graph), not just `code_constants`. Rebuilt the graph index over the venv and re-stamped `builder_version` 28. Suite green. | chunker.py `CHUNKER_VERSION = "29"`; graph_indexer.py `GRAPH_BUILDER_VERSION = "28"`; indexer/chunker/graph_indexer `.mts`/`.cts` extension + language maps. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-11 | Enum members become NODES + chunks now; member READ edges deferred. | The node/chunk (retrievability + listability) is the high-value, contained win; `Enum.Member`-access read-edge attribution is a separate identifier-resolution concern. | Ship reads too — rejected: scope creep into member-expression resolution. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Bumping a chunk shape after p4pu/27 repeats the dual-version mistake | This change OWNS the 27→28→29 bump (the second step is the in-wave review re-bump, both pre-publish); p4pu is a pre-publish test pack, consumers re-upgrade. No interim same-version reshape that ships to consumers. |
| TS enum tree-sitter node shapes differ from assumption | Fixture-driven AC-1/AC-3 verify the real `enum_body`/`enum_assignment` shapes under the venv. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
