# Wavefoundry Release Notes

Per-release operator-facing summary, aggregated by semver version
(`MAJOR.MINOR.PATCH`). Build numbers (the `+XXXX` suffix from the lifecycle
id) are traceability stamps, not separate release entries — multiple builds of
the same semver version share one section. The latest release appears first.

---

## 1.2.1 — 2026-06-01

**Wave 13129 — Graph Tools Field Feedback Rounds 2 and 3**

Multi-build iteration on wave 130rj (1.2.0+312f). The 1.2.1 release aggregates
twelve operator-feedback fixes spanning two iteration cycles (round-2 → round-3)
from Solaris (Swift) and Aceiss (Java/ByteBuddy). Earlier 1.2.1 builds shipped
the round-2 changes; later builds added the round-3 follow-ons after operators
round-tripped to validate.

### Action required on upgrade

**Two graph rebuilds were bumped over the course of 1.2.1 builds:**
- `GRAPH_BUILDER_VERSION` 12 → 13 (round-2, 1312l): Java receiver-type
  attribution at index time.
- `GRAPH_BUILDER_VERSION` 13 → 14 (round-3, 1316l): Swift class/module merge
  at index time.

Operators upgrading from `1.2.0+312f` or any pre-`+316*` 1.2.1 build need ONE
rebuild on the latest build via `wave_index_build(content='graph')` to pick up
the v14 graph. Wave 13129's `1316n` adds a `graph_rebuilt` field and clarifying
notice on `wave_index_build` responses so this step is observable inline.

### Headline change — Java receiver-type resolution moved to the graph builder

`code_impact` and `code_callhierarchy` previously returned **contradictory
answers on the same Java symbol** when wave 130rj's receiver-type filter was a
per-tool wrapper. Aceiss's reproducer: `code_impact("writeObject")` returned
19 callers across 3 communities; `code_callhierarchy("writeObject")` returned
2 callers in 1 community. The underlying graph carried phantom `calls` edges
from simple-name attribution at index time, which `code_callhierarchy` filtered
on the way out but `code_impact` did not.

Wave 13129 promotes receiver-type resolution into the **graph builder**. The
phantoms are eliminated at index construction time — every consumer (`code_impact`,
`code_callhierarchy`, `code_callgraph`, `code_graph_path`, `wave_graph_report`)
sees the cleaned-up edges automatically.

**Action required on upgrade:** `GRAPH_BUILDER_VERSION` bumps 12 → 13, forcing a
one-time graph rebuild on the next `wave_index_build` after upgrade. Allow
2–5 minutes on Java-heavy repos.

For Java method invocations like `oos.writeObject(...)` where `oos` is an
`ObjectOutputStream`, the graph now correctly attributes the edge to
`external::ObjectOutputStream.writeObject` rather than the project's
simple-name-matching `JSON.writeObject`. Bare calls (`method()`) and `this.method()`
inside the same class continue to attribute to the enclosing project class.

### Decomposed `name_collision_count` diagnostic

The single `name_collision_count` field shipped in wave 130rj missed both
operator field reports' actual signals:
- Solaris's `StatusBarManager` case: count 72 was 100% same-file aggregation
  (nested types inside one file). Misleading without a cross-file/same-file
  discriminator.
- Aceiss's `JSON.writeObject` case: count 1 ignored the actual collision with
  `java.io.ObjectOutputStream.writeObject` (external symbol). False-safe for
  the common Java case (`run`, `close`, `equals`, `writeObject`).

Each `fan_in` / `fan_out` / `chokepoints` / `file_hubs` / `betweenness` entry
on `wave_graph_report` now carries three fields:
- `same_name_node_count` — project-only count (existing semantics; preserved)
- `cross_file_collision: bool` — true when 2+ project files own a same-name node
- `external_name_collision_count: int` — count of `external::*` nodes sharing the simple name

`name_collision_count` is preserved as a **deprecated alias** for
`same_name_node_count` for one release. Operators should migrate to the
decomposed fields.

The verification trigger documented in seed-211 becomes:
`(same_name_node_count > 1 AND cross_file_collision: true)` OR
`(external_name_collision_count > 0)`. Same-file-only collisions are
file-tree-shape noise and trustworthy without verification.

### New `file_hubs` section on `wave_graph_report`

`chokepoints` previously mixed function-level call-graph bottlenecks with
file-level fan-out hubs (different semantics, same ranking). Operators had to
inspect each entry's `kind` field to know what the number meant.

`chokepoints` now contains only `kind: "function"` / `"method"` / `"class"`
entries. File-level (`kind: "module"`) entries moved to a new `file_hubs`
section. Both sections are in the default `sections` set.

**Migration note:** if you previously queried `sections=["chokepoints"]` to
find both file-level and function-level hubs, switch to
`sections=["chokepoints", "file_hubs"]`. Default callers get both views
automatically.

### `large_community_advisory` diagnostic on `code_graph_community`

Querying a 3000-member community via `pagination_hint` burns 60+ round-trips
for what one hub-targeted `code_callhierarchy` call answers. The response
now carries:
- `community_size_class: "small" | "medium" | "large"` — always present;
  thresholds <50 / 50–200 / 200+.
- When `total_node_count > 200`: a structured `large_community_advisory`
  diagnostic with `recovery_tools: ["code_callhierarchy", "code_graph_path"]`
  and `recovery_usage` pointing at the community's hub `code_callhierarchy`
  call.

The advisory complements `pagination_hint` (both surface on large communities)
rather than replacing it.

### `collapse_class_module_pairs` on `wave_graph_report` (Swift-first)

When a Swift `Foo.swift` defines a top-level `class Foo` / `struct Foo` /
`actor Foo` / `enum Foo` / `protocol Foo`, the file node and the class node
are conceptually one entity but appear as two distinct graph nodes. Operators
investigating "what depends on StatusBarManager?" hit a discovery problem
when querying the module path vs the class node.

New `collapse_class_module_pairs: bool = False` parameter on
`wave_graph_report` (and dashboard graph-render endpoints) merges the pair
into a single node for report consumption. The collapsed node carries
`collapsed_pair: true` and the class label.

**Scope:** Swift only. Java/Kotlin/C# extension is operator-validation-driven
via the `_CLASS_MODULE_COLLAPSE_LANGUAGES` dispatch in
`.wavefoundry/framework/scripts/graph_query.py`.

Per-symbol navigation tools (`code_callhierarchy`, `code_impact`, etc.)
deliberately do NOT support the flag — they need the full per-symbol view.

### Documented module fan_out semantics

`wave_graph_report.fan_out` docstring previously read "symbols that call the
most others" — accurate for function nodes, misleading for module/file nodes.
The new docstring spells out the kind-aware decomposition explicitly: `count`
is the number of distinct outgoing `calls`-relation edges; for module entries,
this excludes `imports` and `defines`. A locked unit test
(`TestModuleFanOutCountSemantics`) gates future drift.

### Pre-existing fix bundled inline

While shipping 1312l, discovered a pre-existing duplicate bug in the
cross-file resolution pass's `qualified_index` — same node_id was added under
both the direct qualified key and its dotted suffix key when the file path
ended up producing the same suffix. The duplicate broke `len(candidates) == 1`
checks for legitimate single-candidate rewrites.

Fixed inline with `dict.fromkeys` dedup. Operators on legacy code may see
slightly more cross-file edges resolve correctly post-rebuild.

### Round-3 follow-ons (added in later 1.2.1 builds)

After operators round-tripped the round-2 changes (1.2.1+315o), six additional
fixes were admitted to wave 13129. They split into one bug fix, one structural
graph-builder change, and four operator-facing observability improvements.

#### `same_name_node_count` constant bug fix (1316j)

Solaris reported every Swift module entry in `file_hubs` carried the identical
`same_name_node_count: 72` — their total Swift module count. Root cause: the
simple-name extraction for module nodes (no `::` separator in the id) took the
file extension `"swift"` instead of the file basename. Fixed by routing module
nodes through a basename-without-extension extraction. Distinct Swift modules
now report distinct collision counts.

#### Swift class/module merge at the graph builder (1316l)

Solaris's `code_callhierarchy("StatusBarManager")` returned empty incoming
despite a known constructor call in `AppDelegate.swift`. Root cause: the graph
treated `StatusBarManager.swift` (kind: module) and `StatusBarManager.swift::StatusBarManager`
(kind: class) as separate nodes; the constructor call's edge targeted the class
node, but the symbol resolver picked the module node.

Fixed by merging at the index layer (mirrors 1312l's pattern). When a Swift
file `Foo.swift` contains exactly one top-level type declaration named `Foo`
(class / struct / actor / enum / protocol), the indexer merges the file node
and the type node into a single node at the file id with the type's label and
kind, plus `collapsed_pair: true`. Every per-symbol tool (`code_callhierarchy`,
`code_impact`, `code_callgraph`, `code_graph_path`) sees the unified node
automatically.

Bumps `GRAPH_BUILDER_VERSION` 13 → 14. Swift-only scope.

#### `external_name_collision_count` switched to a stdlib allowlist (1316p)

After 1312l shipped receiver-type resolution at the graph builder, the
`external_name_collision_count` field stopped firing for the common Java case
(`run`, `close`, `equals`, `writeObject`) because the indexer no longer
created the spurious `external::*` nodes the count depended on. Aceiss reported
`SpringUserListJob.run` and `JdbcUserListJob.run` both showed
`external_name_collision_count: 0` despite obvious Runnable collisions.

Switched the field from a graph-state-based count to a curated Java
stdlib/framework allowlist (~30 names covering `Object`, `Runnable`,
`AutoCloseable`, `java.util.function`, `Comparator`, `Iterator`,
`java.lang.reflect`, `java.io`, `Map.Entry`, and common Spring patterns).
When a project symbol's simple name is in the allowlist, the field reports `1`.
Otherwise `0`. The seed-211 verification trigger now fires correctly for the
common Java cases. The deprecated alias `name_collision_count` is unaffected.

#### Stable community identifier via hub anchor (1316r)

Aceiss reported community ids (`project:cN`) change between graph rebuilds
because Leiden numbering is emergent — an agent that cached `project:c12`
from a wave_graph_report call and drilled in later got `not_found`.

Added `community_hub_node_id` to `code_graph_community` responses and a new
`hub_node_id` parameter on `code_graph_community`. The hub is the community's
highest-degree member, identified by node id (stable across rebuilds — node
ids don't churn even when Leiden ids do). When `hub_node_id` is provided, the
tool resolves to the current community containing that node. When both
`community_id` and `hub_node_id` are provided, `community_id` wins.

Seed-211 updated to recommend `hub_node_id` for cached / persisted references.

#### Graph rebuild discoverability (1316n)

Aceiss reported `wave_index_build(content='code'|'all', mode='rebuild')` didn't
touch the graph, but the operator-facing surfaces gave no signal — the
response said `"passed": true`, `wave_index_health` said everything was
current. Operators thought they had rebuilt the graph.

`wave_index_health` now carries a `graph` object per layer with `present` /
`last_built_at` / `node_count` / `edge_count`. `wave_index_build` responses
carry the same graph counts when the graph artifact exists, plus a
`graph_rebuilt: bool` field and a clarifying notice when `content` is not
`'graph'` ("The graph layer was NOT rebuilt by this call. Run
wave_index_build(content='graph') if graph-layer refresh is required.").
Seed-160 (upgrade) carries the semantic-vs-graph callout for upgrade flows.

#### Empty-section diagnostic fields (1316t)

`wave_graph_report.file_hubs: []` could mean "no file-level hubs exist" or
"file_hubs not populating" — no way to tell. Now each report section that
can legitimately be empty (`chokepoints`, `file_hubs`, `orphan_docs`,
`cross_layer`) carries a `<section>_candidates_total` field indicating how
many candidates were considered before filtering, plus `chokepoints_threshold`
and `file_hubs_threshold` for sections with a configurable cutoff.

`betweenness` already had `betweenness_computed` + `betweenness_skipped_reason`
from wave 130rj; this brings the other sections to parity.

### Multi-language extensions (added in later 1.2.1 builds)

After the round-3 changes shipped, operator direction extended three of them to additional languages — all three multi-language extensions land in the same release with no additional graph rebuild beyond the 1316l v14 bump (the resolver and allowlist extensions stay within the v14 schema).

#### Class/module merge — extended to Java, Kotlin, C# (13190)

`1316l` shipped Swift-only. Now extended to Java (`Foo.java` with `class Foo` / `interface Foo` / `enum Foo` / `record Foo` / `@interface Foo`), Kotlin (`Foo.kt` with `class Foo` / `interface Foo` / `object Foo` / `enum class Foo`), and C# (`Foo.cs` with `class Foo` / `interface Foo` / `struct Foo` / `record Foo` / `enum Foo`). Detection remains name-based (file basename == top-level type name); multi-top-level-types files only merge the basename-matching type and leave others as separate `<file>::<typename>` nodes. `code_callhierarchy` on the unified node now returns constructor / instantiation callers correctly across all four languages.

#### Stdlib allowlist — extended to C#, Kotlin, Swift, Python (13192)

`1316p` shipped Java-only. The `external_name_collision_count` field now dispatches per-language via source-file extension to curated allowlists for C# (`Equals`, `GetHashCode`, `Dispose`, `Compare`, `MoveNext`, etc.), Kotlin (Java common names + `let`, `apply`, `also`, `with`, `invoke`), Swift (`init`, `description`, `encode`, `forEach`, `map`, etc.), and Python (`__init__`, `__str__`, `__enter__`, `close`, `read`, etc.). Languages without an allowlist (Go, Rust, JS, TS) return 0 — operator-validation-driven additions.

#### Receiver-type resolution — extended to Kotlin and C# (13194)

`1312l` shipped Java-only. The Aceiss-reproduced phantom-caller suppression now applies on Kotlin (`call_expression` + `navigation_expression` shape) and C# (`invocation_expression` + `member_access_expression` shape) graphs as well. Conservative coverage: this/super/base/bare calls, explicit type annotations (`val foo: Foo` in Kotlin, `Type foo` in C#), simple identifiers, static-style `ClassName.Method()`. Deferred cases (return None, no phantom suppression): var-typed locals with inferred types, nullable receivers, extension functions, generic methods, property-access chains.

### Wave summary

**Round 2 (six changes, all implemented):**
- **1312f** — module fan_out semantics doc + locked test
- **1312j** — `community_size_class` + `large_community_advisory` diagnostic
- **1312d** — `file_hubs` section split out of `chokepoints`
- **1312b** — decompose `name_collision_count` into 3 fields + deprecated alias
- **1312h** — `collapse_class_module_pairs` Swift-first opt-in view (superseded by 1316l/13190 at v14+)
- **1312l** — graph-builder Java receiver-type attribution; `GRAPH_BUILDER_VERSION` 12→13

**Round 3 (six changes):**
- **1316j** — module simple-name extraction (basename, not extension)
- **1316l** — graph-builder Swift class/module merge; `GRAPH_BUILDER_VERSION` 13→14
- **1316n** — graph rebuild discoverability (health breakout + build response + seed-160)
- **1316p** — `external_name_collision_count` switched to Java stdlib allowlist (extended to multi-language in 13192)
- **1316r** — stable community identifier via `community_hub_node_id` and `hub_node_id` parameter
- **1316t** — empty-section diagnostic fields on chokepoints/file_hubs/orphan_docs/cross_layer

**Multi-language extensions — round 1 (three changes):**
- **13190** — class/module merge extended to Java/Kotlin/C#
- **13192** — stdlib allowlist extended to C#/Kotlin/Swift/Python
- **13194** — receiver-type resolution extended to Kotlin/C#

**Multi-language extensions — round 2 (three changes):**
- **13196** — class/module merge extended to JavaScript/TypeScript/Scala/PHP
- **13198** — stdlib allowlist extended to JavaScript/TypeScript/Go/Rust/Scala/PHP/Ruby
- **1319a** — receiver-type resolution extended to Go/Rust/Scala

**Multi-language extensions — round 3 (three changes):**
- **1319g** — receiver-type resolution extended to Swift (constructor discriminated by case)
- **1319i** — class/module merge extended to Rust (snake-to-PascalCase basename conversion)
- **1319k** — class/module merge extended to Ruby (snake-to-PascalCase + Ruby definition wiring)

### Final language coverage matrix

| Pattern | Java | Kotlin | C# | Swift | JS | TS | Go | Rust | Scala | PHP | Python | Ruby |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Class/module merge (basename-match → unified node) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | ✓ | — | ✓ |
| Stdlib allowlist (`external_name_collision_count`) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Receiver-type resolution (graph-builder) | ✓ | ✓ | ✓ | ✓ | — | — | ✓ | ✓ | ✓ | — | — | — |

**Remaining exclusions:**
- **Go class/module merge** — Go's grouping model is `package = directory`, not file. A "merge" for Go would aggregate all `.go` files in a directory into one node — a different feature (`collapse_package_to_directory`); separate design pass.
- **JS class/module merge** — JS has no top-level `class` convention; ES modules export anything. Literal exact-basename matching works when present but the convention strength is too varied to flag as fully supported here — listed as ✓ on the strength of the match-when-present case.
- **JS/TS/PHP/Python/Ruby receiver-type** — dynamic, optional, or inference-driven type systems. JS has no type system; TS, PHP, Python have optional annotations; Ruby is fully dynamic. Reliable per-call-site resolution requires symbol-table work (TS), JSDoc parsing (JS), Sorbet/RBS integration (Ruby), or operator-validation that partial-coverage UX is acceptable. Defer.

~100 new regression tests across the wave; 2094 total tests pass.

### MCP wrapper signature cache (carryover note)

New parameter `collapse_class_module_pairs` on `wave_graph_report` requires a
full MCP server restart (not just `/mcp` reconnect) to expose at the protocol
layer. FastMCP captures wrapper signatures at server startup; response-shape
changes hot-reload but parameter signatures don't. Same limitation observed
in wave 130rj's `exclude_external` rollout.

---

## 1.2.0 — 2026-06-01

**Wave 130rj — Graph Tools Field Feedback Tier 1 + Tier 2**

14 changes addressing initial Solaris (Swift) + Aceiss (Java) field reports:

- Question-type pattern library in seeds 180/211/213/214/221
- Graph tool shape consistency (community_id dual return, pagination,
  per-hop attribution on code_impact, communities overview)
- Generated-code classifier (Java + C# headers, path heuristics,
  `.gitattributes`) + `exclude_generated` filter + collapse mode
- AOP/advice empty-incoming detection (`caller_pattern: "advice"`,
  Java + C# attribute extraction)
- Java `method_reference` (`Foo::bar`) classified as call_sites
- Kotlin reference resolution enabled end-to-end
- `name_collision_count` diagnostic, `betweenness_computed` field,
  large-community `pagination_hint`, `exclude_external` filter
- Java receiver-type filter at `code_callhierarchy` query time
  (promoted to graph builder in 1.2.1)

See `docs/waves/130rj graph-tools-field-feedback-tier-1-and-2/wave.md` in the
project repository for the full change-by-change detail.

---

## Earlier releases

See `git log` on the project repository for releases prior to 1.2.0.
