# Graph Index System

Owner: Engineering
Status: active
Last verified: 2026-07-06

Architecture reference for Wavefoundry's code and documentation graph index: how it is generated, stored, traversed, clustered, and surfaced through MCP tools.

> **Line citations** in older sections reference the `GRAPH_BUILDER_VERSION="29"`-era source (waves 1p4ls/1p4q4/1p4up); the current constant is `"38"` (wave `1p9qi`). Line numbers shift on builder version bumps — use function names as stable anchors when citing across versions.

---

## Quick Reference

| I want to… | Use this |
|---|---|
| Callers or callees of a function (one hop) | `code_callhierarchy(symbol, direction="incoming"/"outgoing")` |
| Full call tree to arbitrary depth | `code_callgraph(symbol, depth=N)` |
| Upstream blast radius of a change | `code_impact(symbol, max_hops=3)` |
| Shortest path between two symbols (forward dependency chain) | `code_graph_path(from_symbol=..., to_symbol=...)` |
| Reverse dependency chain ("who reaches me?") | `code_graph_path(from_symbol=..., to_symbol=..., direction="backward")` |
| Are two symbols connected at all (direction-agnostic) | `code_graph_path(from_symbol=..., to_symbol=..., direction="either")` |
| Members of a community cluster | `code_graph_community(community_id=...)` |
| Structural health report (fan-in/out, chokepoints, betweenness) | `wave_graph_report(sections=["betweenness"])` |
| Graph index metadata (ambient) | MCP resource `wavefoundry://graph/status` |
| Community catalog (ambient — id, label, size, top members) | MCP resource `wavefoundry://graph/communities` |

**Single graph layer**: there is one project graph. Wave `1p4ww` removed the separate
`framework` graph and the `union` (merged) mode; the
`layer` argument on the graph tools is retained as a back-compat no-op that always resolves to
`project`.

**When the graph is absent**: `read_graph_payload()` returns `present=False`. All graph-backed tools degrade gracefully — `code_references` falls back to a full repository walk; `code_callhierarchy`, `code_callgraph`, `code_impact`, and `wave_graph_report` return a diagnostic response. The graph is absent until explicitly built. To build: `wave_index_build(content='graph')` (graph only) or `wave_index_build(content='all')` (graph + semantic index).

---

## Overview

The graph index is a persisted directed graph of nodes (files, symbols, and docs) and typed edges (calls, imports, defines, doc references, DI wiring). It is built separately from the semantic embedding index and stored as gzip-compressed compact JSON artifacts on disk (readers sniff the gzip magic bytes and transparently fall back to legacy plain JSON). The graph enables structural queries — call hierarchies, upstream impact analysis, cross-layer traversal, community detection — that semantic similarity search cannot answer.

The graph is **not** used for semantic search. It is used exclusively by graph-backed MCP tools and by `code_references` as a candidate-file restrictor to avoid full repository walks.

---

## Graph Schema

### Node Fields

Every node is a dict with these six fields, produced by `_node()` in `graph_indexer.py:490-506`:

| Field | Type | Description |
|---|---|---|
| `id` | str | Unique node identifier (e.g. `src/billing.py::charge`) |
| `label` | str | Short human-readable name |
| `kind` | str | Node type; see table below |
| `source_file` | str | Repo-relative path of the owning file |
| `source_location` | str | `"line:col"` offset within `source_file` |
| `layer` | str | `"project"` (the only graph layer) |

Three boolean annotations are written directly onto module-level node dicts during `finalize()` at `graph_indexer.py:2076-2123`:

| Field | Meaning |
|---|---|
| `is_entry_point` | Module imported by nothing external but has outgoing edges |
| `dead_code_risk` | Module whose symbols are never externally called or imported |
| `is_chokepoint` | Articulation point in the undirected executable subgraph (requires `igraph`) |

### Node Kinds

| Kind | Source |
|---|---|
| `module` | Every file's root node; also namespaces and packages |
| `function` | Functions, methods, async functions, constructors |
| `class` | Classes, interfaces, structs, enums, traits |
| `constant` | Module-/type-level named constant declarations (wave 1p4ls). Carries an optional `value` field when the RHS is a simple literal. Detected per-language by the shared chunk-lane predicates (one detector, two consumers): Python `UPPER_SNAKE`/`Final`; JS/TS `const` value-bindings + per-declarator; Java `static final` + interface constants; Kotlin `const val`; C# `const`/`static readonly`; Go `const` (per-member, incl. grouped blocks); Rust `const`/`static`; Swift `static let`/file `let` + enum cases; Ruby `constant`-LHS assignments; PHP `const`. JS/TS `enum` / `const enum` MEMBERS are also constant nodes (wave 1p4q4; label `Enum.Member`, namespace-prefixed when nested — `NSA.Inner.AAA` vs `NSB.Inner.AAA`, no cross-namespace collision) while the enum type itself stays a `class` node. Constant nodes are EXEMPT from the `<=2`-char short-symbol prune (1p4q4 review), so short members like `Status.OK` / `Dir.Up` survive and resolve via `code_definition`. Function/method-body locals are excluded by scope. |
| `doc` | Markdown and plain-text doc files |
| `seed` | Files under `.wavefoundry/framework/seeds/` |

External symbols (imported from outside the repo) are represented as nodes with ids prefixed `external::` (e.g. `external::pathlib.Path`). There is no explicit `kind` field for external nodes; they are identified and filtered by the `external::` id prefix.

### Edge Fields

Every edge is a dict produced by `_edge()` at `graph_indexer.py:509-525`:

| Field | Type | Description |
|---|---|---|
| `source` | str | Node id of the edge origin |
| `target` | str | Node id of the edge destination |
| `relation` | str | Edge type; see table below |
| `confidence` | str | `"EXTRACTED"`, `"AMBIGUOUS"`, or `"INFERRED"` |
| `evidence` | str? | Optional provenance string |

### Edge Relations

| Relation | Produced by | Meaning |
|---|---|---|
| `defines` | `graph_indexer.py:1179, 1344, 1511` | Module declares a symbol |
| `calls` | `graph_indexer.py:1297, 1597` | Symbol invokes another symbol |
| `imports` | `graph_indexer.py:1197, 1208, 1372, 1380, 1529` | Module imports an internal or external module |
| `reads` | `graph_indexer.py` (`_extract_python_artifact` CallCollector + the tree-sitter `buffered_reads` resolution; SQL: `_sql_apply_file_extraction`) | A function/method READS a constant's value (wave 1p4ls). Faithfulness-gated: binds only a same-scope constant uniquely resolvable by `symbol_lookup` (never a coincidental same-name twin; Python adds a local-shadow guard). **OPT-IN** for default 1-hop traversal (`graph_query._NEIGHBOR_OPT_IN_RELATIONS`) so a hot constant does not balloon neighbor sets/1p4hu expansion, and excluded from `_DEFAULT_IMPACT_RELATIONS`/`_DEFAULT_CALL_RELATIONS` + from clustering (`graph_cluster`). Surfaced via `code_references`' distinct `reads` bucket (not callers). _Resolves **same-scope** (same-module) reads AND **explicitly-imported cross-module** constant reads — an imported read binds only a UNIQUE constant matched by the qualified import name (kind-checked) or is DROPPED, never a coincidental same-name twin or a 3rd-party value. The local-shadow guard is Python-only; tree-sitter languages may over-fire on a function-local that shadows a same-named constant (uncommon)._ Wave 1p4up: also resolves **qualified member-access reads** (`Status.ACTIVE`, `Outer.Inner.TOKEN`, `A::B::C`) by EXACT qname match (const-kind-gated) — the qualifier disambiguates, with an F4 guard dropping a read whose head is a function param/local. **Wave `1p9qi` (`1p9qd`): `reads` is ALSO the read-direction SQL table reference** — FROM/JOIN sources, MERGE USING, FK `REFERENCES`, `CREATE INDEX ... ON`, and view lineage (`CREATE VIEW v AS SELECT ... FROM t` emits `v reads t`, making view → table lineage traversable). SQL-origin reads (source file is SQL) are recognized in cross-file resolution and routed through the CALL machinery — qualified-first / unique-bare / refuse-on-ambiguity, `sql_kind`-gated so a same-name host-language twin is refused — and STAY EXTERNAL when unresolved (never tombstoned; the constant-read DROP contract applies only to non-SQL sources). They inherit the opt-in 1-hop and clustering exclusions deliberately, but join **default `code_impact` traversal** via the data-layer exception (a `reads`/`writes` edge touching a `sql_kind` node) so "what breaks if I change table X" includes dependent views. |
| `doc_references_code` | `graph_indexer.py:1699` | Doc node mentions a code node |
| `doc_references_doc` | `graph_indexer.py:1735` | Doc node links or path-references another doc |
| `binds` | `graph_di_signals.py:285-293` | DI interface bound to an implementation |
| `injects` | `graph_di_signals.py:329-337` | DI consumer depends on an injected type |
| `extends` | `graph_indexer.py` (`_java_supertype_facts` / `_csharp_supertype_facts` → the `buffered_supertypes` drain) | Subtype → superclass (class extends class; interface extends interfaces). Wave `1p9qh` (`1p9qa`), Java + C# (Kotlin deferred). Targets resolve through the same import/unique-candidate machinery as calls (incl. wildcard-import facts); an unresolved supertype stays `external::<Name>` qualified as declared — never dropped. Interface declarers carry `declared_kind: "interface"` on their node so consumers can tell class from interface (both normalize to kind `class`). |
| `implements` | same extraction path as `extends` | Class/enum/record/struct → implemented interface. C#'s flat `base_list` uses the language rule (at most one base class, listed first): first base `extends`, rest `implements` — corrected to the TRUE kind for project-resolved bases by the finalize output pass (`_apply_inheritance_output_passes`); the positional label persists only for `external::` bases, where both relations traverse identically. |
| `writes` | `graph_indexer.py` (`_sql_analyze_program` → `_sql_apply_file_extraction`) | WRITE-direction SQL table reference (wave `1p9qi` / `1p9qd`): the source INSERTs INTO / UPDATEs / DELETEs FROM / MERGEs INTO / ALTERs / DROPs / TRUNCATEs the target table. A distinct relation (not a property on `reads`) so relation-filtering consumers distinguish read from write without per-edge inspection — the `extends`/`implements` precedent. Resolves through the same call-machinery route as SQL reads (`sql_kind`-gated, stays external when unresolved). NOT opt-in for 1-hop traversal (write edges are sparse and high-value); joins default `code_impact` via the data-layer exception; participates in the `code_ask` graph signal (`writers` bucket); clusters at the dict-default weight 1. |
| `maps_to` | `graph_indexer.py` (finalize ORM entity-mapping bind pass; captures via the shared annotation/attribute-argument seam + the EF `ToTable` call sink) | ORM entity→table mapping (wave `1p9qi` / `1p9qg`): a JPA/EF entity class with a **declared** table name — Java `@Entity` + `@Table(name = "…"[, schema = "…"])` or `@Entity(name = "…")`; C# `[Table("…"[, Schema = "…"])]` or origin-checked fluent `ToTable("…"[, "schema"])` — maps onto its SQL table node at `LITERAL_DERIVED` confidence, unique-match-or-drop against `sql_kind` nodes (qualified-exact first, then unique bare/leaf); no match mints the namespaced `external::sql::<name>`. A distinct relation (not `reads`/`writes`) because a mapping is a declaration fact, not query evidence. **Standing decision — declared names only:** convention-derived names (JPA implicit naming/snake_casing, EF pluralization) are REFUSED and counted (`merge_stats.entity_mapping.convention_refused`), and only string literals bind (constant references/`nameof` refuse as `dynamic_refused`) — re-litigate only with a measured per-ORM strategy proposal. Finalize-only (never in fragments); NOT opt-in for 1-hop traversal; joins default `code_impact` via the data-layer exception (table → mapped entities → their callers); `code_ask` graph signal buckets: `mapped_entities`/`maps_to`; clusters at the dict-default weight 1. |

**Decision note — SQL clause-aware extraction (wave `1p9qi` / `1p9qd`).** SQL extraction runs through a dedicated statement-analysis unit (`_sql_analyze_program` + the public `sql_statement_references(sql_text)` — the frozen contract `1p9qe` body recovery and `1p9qf` embedded-SQL binding consume): definitions come only from CREATE statements (`sql_kind` node property distinguishes `table`/`view`/`procedure`/`function`/`trigger`; tables and views keep kind `class` so existing consumers ingest unchanged), references come only from `object_reference` clause positions with statement-derived direction, and the legacy substring-matched import/call node selection + regex candidate fallback are fully retired for SQL mode (SQL emits **no** `imports`/`calls` edges). Query-local names never become graph nodes: CTE names, table aliases, derived-table aliases, and temp-object forms (`#t`/`##t`/`@t` sigils, `TEMPORARY`/`TEMP TABLE` creations) are excluded at the unit — temp objects are session-scoped, not schema objects. Qualified names register dotted (`analytics.events`) so resolution is qualified-first, unique-bare-name fallback, refusal on ambiguity. When a reference does not resolve in-project the external id it mints is identifier-quote-normalized at the file-path emit site via `_sql_normalize_object_name` (wave `1rrx5` R4) — a bracket/backtick/quote-quoted reference (`[dbo].[users]`) yields a clean `external::dbo.users` id, not the mangled raw form, mirroring the embedded-SQL bind normalization in the next note; the statement unit's names-as-written output is itself untouched, and binding stays unique-match-or-drop so two differently-quoted forms collapse onto one external node (never a wrong bind). Statements inside top-level ERROR regions are counted loudly (`sql_error_regions` module-node property) and routed through the recovery tier below. Short-symbol pruning exempts `sql_kind` nodes (a 2-char view name is a real schema object).

**Decision note — SQL ERROR-region DDL recovery tier (wave `1p9qi` / `1p9qe`).** Dialect forms the tree-sitter-sql grammar cannot parse (T-SQL/MySQL procedure headers, triggers, `DELIMITER` blocks — live-verified as top-level ERROR nodes) no longer vanish: each ERROR region gets a bounded, line-anchored recovery scan (`_sql_recover_error_region`) over comment-/string-masked region text (`_sql_recovery_mask_noncode` space-masks `--`, `/* */`, `'...'`, `"..."`, and `$$...$$` spans so commented-out DDL and string-literal DDL can never mint schema objects — a prepare-council security commitment). The scan recovers `CREATE [OR REPLACE] {PROCEDURE|FUNCTION|TRIGGER|TABLE|VIEW|MATERIALIZED VIEW}` definitions — every one marked `extraction: "sql_recovery"` (node property; the honest-degradation provenance marker whose convention family — marker shape, per-file counts, byte/line ceilings — other loud-degradation tiers mirror) — plus `ALTER TABLE` write and `CREATE INDEX`/trigger `ON <table>` read references; `CREATE INDEX` deliberately emits no definition (parity with the parsed path — recovered files can never claim more than parsed ones). Body references re-attach to the recovered routine two ways: a dangling `block` following a single-routine ERROR region attributes its parsed statements to that routine, and region text after the recovered header re-parses once through the statement unit (`recover=False`) with owner re-attribution; multi-routine regions refuse attribution (module scope) rather than guess. Loudness: module-node `sql_recovered_definitions`/`sql_unrecovered_regions` beside `sql_error_regions`, plus a per-file verbose build-log line (`_sql_recovery_log_line`); regions over the 128 KiB ceiling and lines over 4,096 chars degrade to counted-unrecovered, never silence. Recovery is strictly additive: parsed extraction wins name collisions, and files with zero ERROR regions are untouched by construction.

**Decision note — embedded-SQL capture and bind (wave `1p9qi` / `1p9qf`) — the first code→data-layer edge family.** SQL string literals in host-language code are captured only at **known sinks** (never repo-wide literal trawling): Java MyBatis annotations (`@Select`/`@Insert`/`@Update`/`@Delete`), native `@Query(nativeQuery = true)`/`@NamedNativeQuery`, JDBC `prepareStatement`/`prepareCall`, `JdbcTemplate`/`NamedParameterJdbcTemplate` query methods; C# `new SqlCommand(…)`/`CommandText =`, Dapper extension calls, EF `FromSqlRaw`/`ExecuteSqlRaw(Async)`; MyBatis mapper XML statements (source = the mapper interface/namespace). Every capture passes a SQL sniff gate (leading keyword ∈ {SELECT, INSERT, UPDATE, DELETE, WITH, MERGE, CALL, EXEC}) and an origin check (distinctive sink names use a negative project-impostor check; generic names require positive receiver-type resolution to the known library type). At finalize, captured statements run through the frozen statement unit and each referenced table binds source-method → table as `reads`/`writes` at **`LITERAL_DERIVED`** confidence, unique-match-or-drop with identifier-quote normalization (`_sql_normalize_object_name`); no match mints the **relation-scoped** `external::sql::<name>` namespace (minted only on `reads`/`writes`/`maps_to` bind edges; phase-1 resolution passes the ids through untouched — invariant-tested, mirroring the reserved-marker prefixes). Dynamic/concatenated-with-variable SQL **refuses** and is counted per file (`sql_capture_dynamic`), never guessed; only single literals and adjacent literal concatenation bind. Capture candidates ride per-file fragments (`sql_capture_candidates` — in the incremental-merge passthrough list); bind edges are finalize-only. Ships default-on per the standing literal-edge census rule: real-corpus census (Apache Fineract — 11/11 bound edges hand-verified correct; Apache Tomcat negative control — 0 false positives, all-dynamic JDBC surface correctly refused) recorded in the `1p9qf` change doc. **Recorded limitation:** the origin check's receiver/type resolution is same-file `symbol_lookup` only — a project-defined impostor sink class declared in a different file than the call site sits outside its reach at capture time; accepted on real-corpus evidence of zero false positives (`1p9qf` change doc Risks table).

**Decision note — inheritance model (wave `1p9qh` / `1p9qa`).** The graph models inheritance as class-level `extends`/`implements` edges plus a **single-definer** inherited-method resolution: a call `receiver.m()` whose method lives only on a supertype binds via a bounded BFS over PROJECT-RESOLVED inheritance edges (`_INHERITANCE_WALK_MAX_DEPTH` hops, never through `external::`) **only when exactly one supertype in the walk defines `m`**; multiple definers refuse (`external::Receiver.m`) — the model deliberately does not answer override-winner/virtual-dispatch questions (unsound without whole-program analysis). `super.foo()` / `base.Foo()` emit the reserved marker `external::super.<Class>.<method>` and bind via the enclosing class's single project-resolved `extends` target. Every inherited bind carries `via_supertype` (the supertype-hop chain) as audit provenance — a wrong supertype edge amplifies into many wrong call binds, and the property makes that failure mode visible in calibration and adversarial review. Note that the receiver's identity is NOT recoverable from `via_supertype` alone — the chain starts at the first supertype hop, so the provenance is the hop chain, not full call provenance (census observation). Inherited binds are recomputed fresh each build from the merged output maps (fragments stay pristine; incremental == full by construction).

**Decision note — Java receiver forms and package keying (wave `1p9qh` / `1p9qb`).** Java receiver-type resolution covers, beyond bare identifiers: single-segment `field_access` receivers — `this.repo.save()` and `Enclosing.STATIC_FIELD.m()` (static field via the enclosing class name) — resolved through a field-declaration-ONLY lookup (`_search_java_field_declarations`) so a local/parameter shadow never diverts `this.<field>` (Java semantics: `this.f` always denotes the field). Deeper chains (`this.a.b.m()`), non-`this` field paths, casts, and lambdas stay uncertain (documented give-ups). Java `@interface` declarations classify as kind `class` (type declarations, like interface/enum/record), which makes the basename merge apply to annotation-type files. The Java/Kotlin same-package disambiguation tier keys on the **parsed `package` declaration** (`declared_package` on the file's module node, patterns mirroring `graph_query`'s package-collapse mechanism) with directory fallback for declaration-less files — the language fact, not directory layout, consistent with the C# declared-namespace stance; Go keeps directory keying because a Go package IS its directory.

**Decision note — same-scope disambiguation tier by language (wave `1p9q5` adds Rust).** The same-scope disambiguation tier — an ambiguous receiver type binds to a same-name candidate ONLY when a language-defined scope key matches, unique-survivor, refuse-on-ambiguity — now covers **Java/Kotlin/Go/C#/Rust**. Python/JS/TS deliberately **refuse** this tier (no directory/scope proxy for visibility; a standing decision, not a gap). For **Rust** (wave `1p9q5`), the scope key is a **crate-relative module path**, not a directory: `_build_rust_module_index` BFS-maps files to module paths from `mod foo;` declarations (harvested onto each `.rs` module node as `rust_mod_decls`) and `_rust_module_key` composes the file-module path with an inline-`mod {}` nesting suffix (`rust_inline_mods`), also honoring `#[path]` relocation, the crate root, and a per-file identity fallback for unreachable/ambiguous files (never a guessed parent). The `.rs` tier binds a receiver to a same-module definition only, ordered AFTER explicit-import disambiguation (which wins first). **Bounds:** no cross-crate resolution and no re-export (`pub use`) graph — a `use` re-export chain is not followed. On current-era repos the tier produces near-zero productive end-to-end binds (a Rust module ≈ one file, and same-file same-module calls already resolve at extraction via `symbol_lookup`); the durable deliverable is the module-path model plus the `rust_mod_decls`/`rust_inline_mods` node properties. C# was verify-and-close in the same wave (`_cs_ns`/`cs_file_ns` already normalize `namespace A.B;`, block, and nested declaration styles to one key; a file-scoped-namespace class carries no namespace prefix and does not participate in the C# tier).

---

## Generation Pipeline (`graph_indexer.py`)

### Versioning

Four constants gate incremental reuse (`graph_indexer.py:27-37`):

```
GRAPH_SCHEMA_VERSION  = "1"
GRAPH_BUILDER_VERSION = "40"   # 40: 1p9q8 coordinated single bump — Python receiver-type resolution (annotations incl. string forward-refs / attrs / module globals + constructor assignments → RECEIVER_RESOLVED / CONSTRUCTION_RESOLVED, unique-match-or-external) (1p9q4), Rust module-path model + `.rs` same-module tier (1p9q5), oversized-file line-scan tier (1p9q6), AST-anchored Python/TS DI `injects`/`binds` (1p9q7); 38: 1p9qi coordinated single bump — SQL keyword-noise suppression (1p9qc), clause-aware statement-unit extraction + new `writes` relation + `sql_kind` (1p9qd), ERROR-region recovery tier + `sql_recovery` provenance (1p9qe), embedded-SQL capture/bind fragment keys + `external::sql::` externals (1p9qf), entity `maps_to` mapping + orm_entity fragment keys (1p9qg); 37: 1p9qh coordinated single bump — structured Java imports (1p9q9), extends/implements inheritance edges + inherited-method resolution (1p9qa), this.field receivers + annotation-type kind + package-declaration keying (1p9qb); 36: 1p9q3 compact+gzip+atomic persistence, build-time betweenness, incremental merge state store (see the constant's in-code changelog for the full history)
```

The community-clustering layer (`graph_cluster.py`) carries its own `CLUSTER_BUILDER_VERSION = "11"` (10: seeded-RNG determinism + grab-bag split; 11: build-time betweenness section + `input_fingerprint` key, wave `1p9q3`).

A full re-extraction is forced whenever any of `schema_version`, `builder_version`, `walker_version`, or `chunker_version` changes — detected when the session opens the per-file state store (`GraphStateStore.ensure_current()`, wave `1p9q2`): any version-key mismatch resets the whole store (file records + merge sidecar), `_load_state()` then reports an empty `files` set, and `update_graph_index()` expands the changed set to the full corpus.

### Entry Point

`update_graph_index()` at `graph_indexer.py:7761-8077` is the public entry point. It instantiates a `GraphIndexSession`, detects version bumps, calls `session.record_file()` for each changed file, and calls `session.finalize()` to produce the final graph payload.

**Finalize output-pass order** (the sequence `finalize()` applies to the assembled output edge map, each pass building on the previous one's edge set): inheritance-aware output passes (`_apply_inheritance_output_passes` — C# base-relation kind correction + single-definer inherited-method/`super.` binding) → config-key→reader bind (`reads_config`) → embedded-SQL bind (`1p9qf` — `reads`/`writes` from captured sink literals) → ORM entity→table bind (`1p9qg` — `maps_to`) → reverse-invalidation prune (drops edges left dangling by deletions/renames before the final payload is written). Every pass in this chain is recomputed FRESH from the merged per-file fragments/output maps on every build — none of them write back into fragments — so an incremental build's finalize output is identical to a full rebuild's (the fragments-stay-pristine invariant the `1p9qh` inheritance passes established and every later finalize-only pass in this wave follows).

### File Types Processed

Doc extensions: `.md`, `.markdown`, `.txt`.

Code extensions: approximately 50 suffixes including `.py`, `.js`/`.jsx`/`.mjs`/`.cjs`, `.ts`/`.tsx`, `.go`, `.rs`, `.java`, `.scala`, `.cs`, `.c`/`.cpp`, `.h`/`.hpp`, `.sh`/`.bash`/`.zsh`/`.fish`, `.tf`/`.hcl`, `.kt`/`.swift`, `.rb`, `.php`, `.yaml`/`.yml`, `.toml`, `.json`/`.jsonc`, `.css`/`.scss`, `.html`/`.htm`, `.sql` variants, `.xml`/`.svg`, and special filenames (`Makefile`, `Dockerfile`, `Gemfile`). Minified files (`.min.`, `.prod.`, `.production.`, `.bundle.`, `.chunk.` in filename) are excluded (`graph_indexer.py:125-127, 271-274`).

### Call Edge Extraction

Three strategies are selected by file type (`graph_indexer.py:1621-1654`):

**Python** (`_extract_python_artifact`, `graph_indexer.py:10304-11073`): Full `ast` module walk via `CallCollector(ast.NodeVisitor)`. Resolves `ast.Call` nodes by matching `ast.Name` and `ast.Attribute` nodes against `import_aliases` and `symbol_lookup`. A bare / same-file `symbol_lookup` bind lands `EXTRACTED` (promoted to `RECEIVER_RESOLVED` when the target is a unique project node, wave `1p7dg`); an unresolved receiver stays `external::…` at `EXTRACTED`.

**Python receiver-type resolution (wave `1p9q4`).** Beyond the bare-name path, `CallCollector` binds a method call through the receiver's *inferred type* from two deterministic, AST-local signals, feeding a per-scope type table (`local_types`/`attr_types`/`module_types`):

- **Annotations → `RECEIVER_RESOLVED`.** Parameter / attribute / class-body / local annotations, including **string forward-refs** (`x: 'Foo'`) and a faithful `Optional[T]` / union / generic unwrap (a *non-Optional* multi-type union or generic **refuses** — never over-binds).
- **Constructor assignments → `CONSTRUCTION_RESOLVED`.** `x = Foo()` locals, `self.attr = Foo()` attributes, and module-global constructions. On agreement with an annotation, the annotation (stronger) wins → `RECEIVER_RESOLVED`.

The bind is gated **unique-match-or-drop**: `{receiver_type}.{method}` must resolve to exactly one project node that actually defines the method. There is **no inheritance/MRO walk** (a method inherited from a base class is not resolved), conflicting reassignment demotes (no bind), and a `getattr(...)` / non-class-factory / star-imported / shadowed receiver does not bind. A typed-receiver CROSS-FILE bind emits `external::{Type}.{method}` WITH its resolution confidence and relies on the finalize cross-file rewrite to swap the target onto the real project node (preserving the confidence). **Honesty rule (wave `1p9q8`):** when that target never binds a project node — the method is absent from the resolved class, or the receiver type is an ambiguous cross-file same-name twin — the edge stays `external::` and is downgraded to `EXTRACTED` in the finalize pass (`_downgrade_unresolved_typed_calls`); `RECEIVER_RESOLVED` means "bound to a receiver-typed project node", so an unresolved external target must not carry it. This pass runs on the FINAL edge map for every `calls` edge, not just Python's: it also honests-out Java's `super.`/`staticorinherited#` markers (see the inheritance-model decision note above) when the finalize inheritance pass cannot bind them to a unique project supertype definer — those refusal paths re-emit a dotted `external::` target while keeping the marker's `RECEIVER_RESOLVED` confidence, which was itself a pre-existing over-claim on a genuinely-unresolved (e.g. library-superclass) target.

**JS/TS without tree-sitter** (`graph_indexer.py:1406-1419`): Regex `_JS_CALL_RE` scans each line. Fires only when the tree-sitter grammar is unavailable.

**All other languages with tree-sitter** (`graph_indexer.py:1479-1619`): `_extract_tree_sitter_artifact()` performs a two-pass AST walk: `walk_definitions()` builds the symbol table, then `walk_calls()` traverses call-node types identified by `_ts_is_call_node()`. Target resolution via `_ts_resolve_target()` checks `import_aliases`, then `symbol_lookup`, then falls back to an `external::name` node (`graph_indexer.py:986-1003`).

### Import Edge Extraction

- **Python**: `ast.Import` and `ast.ImportFrom` statements in `collect_imports_and_defs()` (`graph_indexer.py:1187-1208`). Creates `external::module.name` target nodes.
- **JS/TS regex fallback**: `_JS_IMPORT_RE` and `_JS_REQUIRE_RE` patterns (`graph_indexer.py:1349-1381`).
- **Tree-sitter**: `_ts_is_import_node()` pattern matching, then `_ts_relation_candidates()` extracts target names (`graph_indexer.py:1525-1530, 1567-1571`).

### `doc_references_code` Edge Extraction (`graph_indexer.py:1660-1749`)

`_extract_doc_artifact()` uses two-step symbol matching:

1. **Simple terms** (no dots): Looked up in a `simple_lower` dict (label → node id set). Only fires for terms appearing inside backtick inline spans. Minimum term length: 6 chars (`_MIN_DOC_MATCH_TERM_LEN`, `graph_indexer.py:123`). Common stop-terms are excluded (`graph_indexer.py:98-115`).

2. **Complex terms** (dotted or path-like): A combined compiled regex matches across all code contexts (fenced blocks and inline backticks), built by `_compile_doc_matcher()` (`graph_indexer.py:1787-1816`).

Confidence is `"EXTRACTED"` for unique matches of long or underscore-containing terms, `"AMBIGUOUS"` otherwise (`graph_indexer.py:390-397`).

Markdown links and backtick file paths to known files produce `doc_references_doc` edges (`graph_indexer.py:1729-1735`).

### Disk Artifacts

Written by `_write_json()` as gzip-compressed compact JSON with sorted keys (wave 1p9q3 / `1p9py`): compact separators, gzip level 6 (`GRAPH_GZIP_LEVEL`), and an atomic same-directory temp file + `os.replace` so concurrent readers never observe a torn artifact. Readers (`_read_json()` / the public `read_json_artifact`) sniff the gzip magic bytes (`0x1f 0x8b`) and transparently read legacy plain-JSON artifacts from pre-upgrade indexes; the next build rewrites them compressed. Filenames keep their `.json` names — content is sniffed, not the extension:

| Artifact | Path |
|---|---|
| Project graph | `.wavefoundry/index/graph/project-graph.json` |
| Project state store | `.wavefoundry/index/graph/project-graph-state.sqlite` |

**Per-file state store (wave `1p9q2`).** The state is a stdlib-`sqlite3` database (`GraphStateStore`), not a JSON artifact: a `files` table holds one row per source file (`path`, `source_hash`, and a gzip compact-JSON record `{"source_hash":…, "artifact":…}` — the same record shape and byte format the artifacts use), a `meta` table carries the store/schema/builder/walker/chunker/layer versions plus the payload crash-consistency binding, and a `blobs` table carries the `merge_state` sidecar (the persistent merged maps: per-file raw node lists + resolved edge fragments with provenance). `journal_mode=WAL`, `synchronous=NORMAL`, `busy_timeout` for concurrent hook-spawned builds; all per-build mutations commit in one transaction. A one-file build reads and writes O(changed) rows instead of parsing and rewriting a monolithic state document. The legacy monolithic `project-graph-state.json` is **discarded** one-time when the store first opens (a full re-extract follows, matching the established version-bump upgrade cost); it also remains the pre-upgrade fallback for the version-staleness probe (`read_state_builder_version()`, used by `graph_query`'s auto-rebuild check).

### Determinism and the input fingerprint (wave 1p66e)

Graph extraction is **reproducible**: the same source tree yields the same resolved node/edge set across from-scratch rebuilds. Artifacts are assembled in sorted path order, and the cross-file resolution pass is order-independent — every binding requires a *unique* (`len == 1`) candidate, and the three sites that pick among ties use explicit stable tie-breaks rather than dict/set iteration order: the per-`(file, simple_name)` choice (`_pick_shorter_node_id` — shortest then lexicographic), the per-file import-collision choice (lexicographically smallest FQN), and the rewrite-collapse apply order (sorted by `(new_key, old_key)`). The graph payload and state carry an `input_fingerprint` (sha256 over the sorted node-set + sorted resolved edge-set, excluding the volatile `generated_at`); two identical-input rebuilds produce the same fingerprint, so non-reproducibility is observable. Faithfulness is preserved — the tie-breaks only stabilize genuinely-ambiguous choices and never change a `len == 1` resolution or bind a wrong same-name twin.

### `read_graph_payload()` (`graph_indexer.py:8079`)

Returns a dict with: `layer`, `schema_version`, `nodes` (list), `edges` (list), `counts` (files/nodes/edges ints), `present` (bool), `graph_path` (repo-relative string). When the file is absent or empty: `present=False`, empty `nodes`/`edges`.

---

## DI Signal Extraction (`graph_di_signals.py`)

### Scope

Extracts dependency-injection wiring and resolves it into `"binds"` and `"injects"` graph edges. Coverage: **Java/Kotlin** (`.java`, `.kt`, `.kts`) and **C#** (`.cs`) via regex signal collection (unchanged), plus **Python** and **TypeScript** via **AST-anchored** collection (wave `1p9q7`). Python/TS signals are gathered from the parse tree (idiom text inside strings/comments emits nothing) and route through the shared `resolve_di_edges` machinery, which stays byte-identical for the JVM/.NET path (the AST collectors' faithfulness is opt-in per-signal via `faithful_external`/`*_token` flags). Unresolved, string-token, or ambiguous Python/TS targets stay plain `external::` (unique-match-or-external; no reserved `external::di::` namespace) (`graph_di_signals.py`).

### Signals

`collect_di_signals()` dispatches to two language handlers:

**Java/Kotlin** (`graph_di_signals.py:56-134`):
- `bind().<to>()` Guice/Dagger patterns → `kind: "binds"`, confidence `"EXTRACTED"`.
- Spring stereotypes (`@Component`, `@Service`, `@Repository`, `@Controller`, etc.) on classes implementing interfaces → `kind: "binds"`, confidence `"INFERRED"`.
- Injectable constructor parameters in annotated classes → `kind: "injects"`, confidence `"INFERRED"`.
- `@Bean` methods → `kind: "binds"`, confidence `"EXTRACTED"`.

**C#** (`graph_di_signals.py:137-191`):
- `AddSingleton<I,C>()`, `AddScoped<I,C>()`, `AddTransient<I,C>()`, `AddHostedService<I,C>()` → `kind: "binds"`, confidence `"EXTRACTED"`.
- Autofac `RegisterType<C>().As<I>()` → `kind: "binds"`, confidence `"EXTRACTED"`.
- Constructor parameter injection patterns → `kind: "injects"`, confidence `"INFERRED"`.

**Python** (AST-anchored, wave `1p9q7`; `collect_python_di_signals`): FastAPI `Depends(ref)` in parameter defaults and `Annotated[T, Depends(ref)]` forms → `kind: "injects"` to the resolved callable (same-file and imported); bare `Depends()` and non-idiom decorators emit nothing; ambiguous refs stay `external::`. Alias-imported `Depends` (`from fastapi import Depends as D`) is recognized; a same-named non-FastAPI `Depends` is refused (distinctive→negative / generic→positive origin check).

**TypeScript** (AST-anchored, wave `1p9q7`; `collect_ts_di_signals`): NestJS `@Injectable` constructor params and `@Inject(TOKEN)` params → `kind: "injects"`; `@Module` `{ provide, useClass }` providers and Inversify `bind(X).to(Y)`/`.toClass()` → `kind: "binds"`. String tokens (`@Inject('CONFIG')`) and ambiguous targets stay `external::`; undecorated classes emit nothing. Alias-imported idioms (`import { Inject as I } from 'inversify'`) are recognized and same-named user-defined impostors refused, mirroring the Python origin check.

### Integration

DI signals are collected from `_extract_code_artifact()` and stored as `artifact["di_signals"]`. During `session.finalize()`, `resolve_di_edges()` (`graph_di_signals.py:245-338`) receives the full artifact map and node map, builds a `type_index` from all class/function nodes, resolves `binds` signals first (building `binds_map`), then resolves `injects` signals using `binds_map` to find concrete implementations. Output is a list of `{source, target, relation, confidence, evidence}` dicts appended to the global edge list.

---

## Query Layer (`graph_query.py`)

### In-Memory Index (`GraphQueryIndex.__init__()`, `graph_query.py:123-141`)

Builds three structures from the payload:

| Structure | Type | Purpose |
|---|---|---|
| `_node_by_id` | `dict[str, dict]` | O(1) node lookup by id |
| `_out` | `dict[str, list[dict]]` | Source id → outgoing edges |
| `_in` | `dict[str, list[dict]]` | Target id → incoming edges |

### `resolve_symbol()` (`graph_query.py:152-176`)

Three-tier resolution:

1. **Exact match**: `symbol in _node_by_id` — returns immediately.
2. **Suffix match**: Scans all node ids for those ending with `f"::{symbol}"`. One match returns it; multiple matches return the shortest id (most-specific path prefix).
3. **Label match**: Scans all nodes for `node["label"] == symbol` or `nid.split("::")[-1] == symbol`. Returns the single result, or `None` if ambiguous.

### `traverse()` (`graph_query.py:178-225`)

BFS over the adjacency index. Parameters:

| Parameter | Default | Meaning |
|---|---|---|
| `start_id` | required | Seed node |
| `relations` | `None` (all) | Optional set filter on `edge["relation"]` |
| `max_hops` | `1` | Stops enqueuing at `depth >= max_hops` |
| `direction` | `"callees"` | `"callees"` (`_out`), `"callers"` (`_in`), `"both"` |

Returns `(visited: set[str], traversed: list[dict], has_cycles: bool)`. Edges are deduplicated by `(source, target, relation)`. When a neighbor already in `visited` is re-encountered, `has_cycles=True` and the back-edge is still included in `traversed`.

### `one_hop_neighbors()` (`graph_query.py:227-263`)

Accepts multiple seed node ids. For each seed, collects all edges from both `_out` and `_in` (optionally filtered by relations) and includes both endpoints in the result nodes dict. Does not recurse. Returns `{present, layer, nodes, edges, note}`. Used by `code_references` graph-neighbor expansion when `graph=True`.

### `graph_impact()` (`graph_query.py:265-307`)

Resolves `symbol` → `node_id`, calls `traverse(direction="callers", relations=("imports","calls"), max_hops=max_hops)`. Default `max_hops=3`. Discards the start node from `visited`. Returns `{symbol, resolved, node_id, affected, affected_files, edges, has_cycles, max_hops, relations}`.

### `callgraph()` (`graph_query.py:309-335`)

Resolves `symbol` → `node_id`, calls `traverse(relations=("calls",), max_hops=depth, direction=direction)`. Default `depth=1`, `direction="both"`. Returns `{symbol, resolved, node_id, depth, direction, nodes, edges, has_cycles}`.

### `report()` (`graph_query.py:337-425`)

Iterates `self.edges` once, counting only `relation == "calls"` edges, then computes the requested sections:

| Section | What it computes |
|---|---|
| `fan_in` | Top-`limit` nodes by incoming call count |
| `fan_out` | Top-`limit` nodes by outgoing call count |
| `orphan_docs` | Doc/seed nodes (`_DOC_KINDS = {"doc","seed"}`) with no `doc_references_code` outgoing edge, or zero edges total |
| `chokepoints` | Nodes with `fan_out >= chokepoint_threshold` (default `_CHOKEPOINT_FAN_OUT = 20`) |

> Wave `1p4ww` removed the `cross_layer` section (project×framework boundary edges) and the
> `load_union()` merge along with the framework graph layer. There is one project graph.

### Server-process query cache (wave `1p9q3`)

Inside the long-lived MCP server, graph tools obtain the constructed index through `graph_query.get_query_index(root, layer="project")` rather than a fresh `GraphQueryIndex.from_root()` per call. The accessor holds a single-entry, module-level cache per `(resolved root, layer)`, validated on every access against the payload file's `(st_mtime_ns, st_size)`; construction and replacement run under `_QUERY_INDEX_CACHE_LOCK` (single-flight — concurrent tool calls never observe a half-built index); the in-query version-rebuild path and `server_impl`'s inline graph refresh invalidate explicitly (covering same-stat rewrites in-process); per-call diagnostics ride an O(1) slot-copy view so the shared cached index is never mutated. `WAVEFOUNDRY_DISABLE_GRAPH_QUERY_CACHE=1` restores load-per-call. Stat-keying is safe because all artifact writes are atomic (temp + `os.replace`, wave `1p9q3`). CLI/offline consumers (dashboard, `gen_codebase_map.py`) still construct per run — the cache is server-process-internal.

---

## Community Clustering (`graph_cluster.py`)

### Versioning

```
CLUSTER_SCHEMA_VERSION  = "1"
CLUSTER_BUILDER_VERSION = "11"   # 10: 1p65m seeded-RNG determinism + grab-bag split; 11: 1p9q3 build-time betweenness section + input_fingerprint key
```

### Input Projection (`graph_cluster.py:319-348`)

`_project_undirected_projection()` converts the directed graph to a weighted undirected adjacency dict. External nodes (id starts with `external::`) are excluded. Edge weights are accumulated per undirected pair:

| Relation | Weight |
|---|---|
| `calls` | 3 |
| `imports` | 2 |
| `defines` | 1 |
| `doc_references_code` | 1 |
| any other relation (incl. `extends`/`implements`, wave `1p9qh`) | 1 (dict default — the projection is relation-agnostic by design) |

**Recorded rationale — SQL `writes`/`maps_to` are deliberately NOT excluded from community detection (wave `1p9qi` delivery review, architecture seat).** Unlike `reads` (constant AND SQL read edges — excluded from clustering so a hot constant/table does not balloon communities), the `writes` and `maps_to` relations fall through to the dict-default weight 1 and participate in the projection. This is intentional: write/mapping edges are sparse and high-value, so they legitimately shape data-layer communities. **Known consideration:** a hot write-target table (an audit/log table written by many routines) can bridge otherwise-unrelated modules into one community at weight 1 — accepted at the current weight; revisit (a write-hub cap or a `reads`-style exclusion for `sql_kind` write targets) only if community quality is observed to degrade on write-hub-heavy schemas. The read-only `sql_hot_data_layer_nodes(payload, threshold=_SQL_HOT_DATA_INDEGREE_THRESHOLD)` diagnostic (wave `1rrx5` R7; default in-degree threshold `8`) is the measurement tool for that trigger: it surfaces the high-in-degree `sql_kind` write targets that would bridge communities, so the "observed to degrade" decision is made on data rather than guessed. It is projection-inert (a diagnostic readout, not a clustering input — no `CLUSTER_BUILDER_VERSION` bump).

### Fixed Communities (`graph_cluster.py:228-293`)

Before the clustering algorithm runs, nodes are pre-assigned to fixed communities based on `node["kind"]` (for docs) and source file path patterns:

- **Documentation** — doc and seed kind nodes
- **Tests** — files matching test path patterns
- **Benchmarks** — benchmark path patterns
- **CI/CD** — CI/CD path patterns
- **Generated** — generated file path patterns
- **Scripts** — script path patterns
- **Configuration** — config file path patterns

Fixed community nodes are removed from the adjacency dict before the algorithm runs, then appended to the result with `kind: "fixed"` (`graph_cluster.py:799-800`).

### Clustering Algorithm (`graph_cluster.py:296-305, 351-427`)

**Primary**: Leiden algorithm via `leidenalg.find_partition` with `RBConfigurationVertexPartition`, `seed=0`. Requires both `igraph` and `leidenalg` Python packages.

**Fallback**: Label propagation (`_label_propagation()`, `graph_cluster.py:430-485`). Runs 24 fixed iterations, processing nodes in descending degree order and picking the highest-weight neighbor label. Used when the Leiden backend is unavailable.

The `cluster_algorithm` field in the output artifact records which algorithm ran (`graph_cluster.py:806`).

### Post-Processing

Four passes run after the algorithm (`graph_cluster.py:504-758`):

1. **Remap** (`_remap_clusters()`): Assigns stable `community_id` strings (e.g. `"project:c0"`) by matching new clusters to previous by node-set overlap. Preserves user-edited labels when a match is found.
2. **Merge same-stem** (`_merge_same_stem_communities()`): Merges communities whose seed nodes share the same directory and filename stem.
3. **Merge small** (`_merge_small_communities()`): Iteratively absorbs non-fixed communities below `MIN_COMMUNITY_SIZE = 12` into their most-connected neighbor.
4. **Disambiguate** (`_disambiguate_labels()`): Qualifies duplicate labels with parent directory, then adds numeric suffixes.

### Cluster Artifacts

The cluster artifact shares the graph artifact persistence contract (gzip-compressed compact JSON, atomic write, sniffing reader with legacy plain-JSON fallback — `graph_cluster.py` mirrors the `graph_indexer.py` helpers):

| Artifact | Path |
|---|---|
| Project clusters | `.wavefoundry/index/graph/project-graph-clusters.json` |

Each community record contains: `community_id`, `label`, `seed_node_id`, `node_ids`, `node_count`, `edge_count`, `boundary_node_count`, and optionally `kind: "fixed"`.

---

## MCP Integration (`server_impl.py`)

### Graph-Assisted `code_references`

`_graph_references_candidate_files()` at `server_impl.py:9326-9352` is called unconditionally from `code_references_response()` at line 8588. It loads the project graph, resolves the queried symbol to a `node_id`, reads `index._in[node_id]` (incoming edges), and extracts `source_file` from each edge's source node. Returns a `frozenset[str]` of repo-relative paths, or `None` when the graph is absent, the symbol is unresolvable, or there are no incoming edges.

When `restrict_files` is non-`None`, all three reference searchers (`_python_references`, `_treesitter_references`, `_non_python_references`) receive a pre-built `_files` list of `Path` objects, bypassing `_walk_repo_for_navigation()` entirely. The response includes `"graph_assisted": True/False` at `server_impl.py:8667, 8700`.

### `code_callhierarchy_response()` (`server_impl.py:8896-9047`)

1. Obtains the index via `graph_query.get_query_index(root, layer="project")` (the server-process cache above; `GraphQueryIndex.from_root` under the kill switch or outside the server).
2. Resolves the symbol, optionally qualifying with the `file` param by trying `file::symbol` first (`server_impl.py:8938-8943`).
3. **Outgoing** (callees): `index.traverse(node_id, relations=["calls"], max_hops=1, direction="callees")`. Collects all non-external callee names, calls `_scan_all_call_sites_in_file()` once on `definition_file`, uses `_first_call_site_at_or_after()` to pick the first call site at or after the caller's `source_location` line.
4. **Incoming** (callers): `index.traverse(node_id, relations=["calls"], max_hops=1, direction="callers")`. Groups callers by source file. Calls `_scan_call_sites_in_file()` once per unique source file for the target symbol. Attributes call sites to callers in ascending-definition-line order using a `used_lines` set to prevent double-attribution.
5. Each node entry carries a `community` field populated from `_load_cluster_lookup(root)`.
6. When `context_depth > 0`, all immediate caller/callee node ids are gathered into a set, then a single combined `traverse(max_hops=1, direction="both")` is called per immediate neighbor; expanded neighbors (not already known) are appended as a `context` list.
7. When the symbol is unresolvable, `_suggest_near_symbols(index, symbol)` populates a `suggestions` list in the response.

### `code_callgraph_response()` (`server_impl.py:9610-9716`)

Calls `index.callgraph(symbol, depth=max(1,depth), direction=direction_value)`. When `include_tests=False` (default), nodes whose `source_file` matches `_is_test_path()` patterns are dropped, and edges referencing those filtered nodes are also dropped — keeping the subgraph internally consistent. Symmetric with `code_impact`'s filter. Enriches each remaining `"calls"` edge with a `"line"` field: groups all edges by source file, calls `_scan_all_call_sites_in_file()` once per unique source file, then calls `_first_call_site_at_or_after()` per edge using the source node's `source_location` as the start line.

### `code_definition_response()` — graph-narrowed lookup

Calls `_graph_definition_candidate_files(root, symbol)` first. The helper iterates the project graph's `_node_by_id` and collects `source_file` paths from nodes whose `label == symbol`, whose id ends with `::<symbol>`, or whose label contains the symbol as a substring — mirroring the scanner predicate `name == symbol or symbol in name`. Returns `None` when the graph is absent or fails to load; returns an empty frozenset when graph is present but no candidates match.

The response carries a `lookup_method` field with one of five values:

- `graph_narrowed` — graph candidate set was non-empty on the first query; the four scanners (`_python_definitions`, `_treesitter_definition_results`, `_regex_definitions`, `_css_definitions`) skipped the full repo walk entirely and constructed file paths directly from the restriction set. Typical latency: <300ms on this repo (down from 38–43s pre-change).
- `graph_narrowed_after_refresh` — first query returned an empty candidate set, so an incremental graph refresh (`wave_index_build_response(content="graph", mode="update")`) ran (~4ms when nothing has changed); after refresh the candidate set was non-empty and scanners ran on the restricted set. This handles the recently-added-code case.
- `graph_definitive_not_found` — refresh ran and the candidate set was still empty; since the structural scanners share the same file scope the graph extractor uses, walking the tree again would burn 40+s for nothing. The graph is treated as the source of truth and a fast not-found response is returned with a diagnostic suggesting `code_keyword` for symbols in file types the graph does not index. Typical latency: <300ms.
- `graph_index_missing_degraded` — graph never built; the structural scanners run their existing four-pass repo walk (pre-1301h behavior, 40+s cold). The response carries a `graph_index_missing_degraded` advisory diagnostic telling the operator to run `wave_index_build(content="graph")` once to switch all subsequent calls to the sub-300ms `graph_narrowed` path. The walk still runs so callers that depend on `name`-bearing structural definitions (the existing test suite, for example) keep working through initial setup.
- `keyword_fallback` — structural scanners produced no result and the broad `_keyword_fallback_definitions` walker ran as a last resort. Reachable when the graph is absent and the symbol has no structural definition anywhere, or when the graph is present and refers to a stale candidate file that no longer contains the symbol.

Substring-match semantics are preserved across all paths because the candidate helper uses the same `name == symbol or symbol in name` predicate the scanners use. The graph-narrowed path is guaranteed (by `TestCodeDefinitionGraphNarrowed.test_graph_narrowed_path_finds_correct_definition` and `test_missing_symbol_with_graph_returns_definitive_not_found`) to return the same definition set as the structural walk for symbols the graph knows about. (Wave `12xr3`, change `1301h`.)

### Graph-Tool Miss Behavior — Refresh-and-Instruct Contract (wave `1304x`, change `1304r`)

The pattern established by `1301h` for `code_definition` is now applied uniformly across the seven other graph-using MCP tools: `code_references`, `code_callhierarchy`, `code_callgraph`, `_code_impact_graph_response` (graph mode of `code_impact`), `code_graph_path`, `code_graph_community`, and `wave_graph_report`. Every miss path attempts an incremental graph refresh before emitting suggestions or not-found.

**Shared helpers in `server_impl.py`:**

- `_graph_refresh_then_recheck(root, recheck_fn)` — generic primitive that calls `wave_index_build_response(root, content='graph', mode='update')` then invokes the supplied `recheck_fn()`. Returns `recheck_fn`'s result on success, or `None` on any exception. The refresh side-effect is centralized here; the six call sites only own the recheck closure.
- `_graph_refresh_and_resolve(root, symbol, layer)` — convenience for the common symbol-resolution case. Refreshes, reloads `GraphQueryIndex`, calls `resolve_symbol(symbol)`, and returns `(fresh_index, node_id)` on hit or `(None, None)` on miss / refresh failure. `code_callhierarchy_response`, `code_callgraph_response`, and `_code_impact_graph_response` consume this helper.

**Per-tool miss behavior:**

- `code_references_response()` — when `_graph_references_candidate_files()` returns `None` on first query, retries via `_graph_refresh_then_recheck`. Preserves the existing 176ms-range fast path; the refresh only fires when the symbol isn't in the graph.
- `code_callhierarchy_response()`, `code_callgraph_response()`, `_code_impact_graph_response()` — when `index.resolve_symbol(symbol)` returns `None`, calls `_graph_refresh_and_resolve()`. On hit, swaps in the fresh index and proceeds normally; on miss, emits a `graph_symbol_not_found` diagnostic with `recovery_tools=["code_definition", "code_keyword"]` and the existing suggestions list.
- `code_graph_path_response()` — when either `from_id` or `to_id` is `None`, runs an inline refresh-then-recheck that resolves BOTH symbols against the freshly loaded index (the generic helper rather than `_graph_refresh_and_resolve` is used here, because the helper's return contract discards the fresh index when its single target symbol still misses post-refresh). When at least one symbol remains unresolved, emits `graph_symbol_not_found` with a message that names the missing symbol(s).
- `code_graph_community_response()` — when the requested `community_id` is absent from the cluster artifact, `_graph_refresh_then_recheck` re-reads the (possibly re-clustered) artifact. On hit, proceeds normally; on miss, emits `not_found` with the existing community-suggestions list.
- `wave_graph_report_response()` — when `index.present` is `False` on first load, refresh-then-recheck reloads the index. On hit, the report proceeds normally; on miss, emits the existing `graph_not_ready` diagnostic.

**Diagnostic vocabulary** — three codes carry consistent recovery hints across all seven tools:

- `graph_index_missing_degraded` — graph index never built; advisory in `code_definition` `1301h` path; recovery: `wave_index_build(content='graph')`.
- `graph_not_ready` — graph layer absent and no fallback exists; emitted by `code_callhierarchy`, `code_callgraph`, `code_impact` (graph mode), `code_graph_path`, `wave_graph_report` via `gq.graph_not_ready_diagnostic(layer)`; recovery: `wave_index_build(content='graph')`.
- `graph_symbol_not_found` — incremental refresh ran and the symbol still doesn't resolve; emitted by the four symbol-resolution tools; recovery: `code_definition` (try a broader symbol lookup) or `code_keyword` (try literal-text search for symbols in file types the graph extractor doesn't cover).

**Latency budget** — incremental graph refresh is ~4ms when nothing has changed (measured during wave `12xr3` close-review). The fast path (symbol-in-graph on first query) pays zero overhead because the refresh branch is gated behind the miss. The miss-plus-refresh path stays well under 1s on this repo (live smoke at wave close: 304ms for `code_callhierarchy` triggering a real refresh; 753ms for a never-resolves bogus symbol including the suggestions scan).

Test coverage: `TestGraphRefreshThenRecheck`, `TestGraphRefreshAndResolve`, and `TestGraphToolRefreshOnMiss` in `tests/test_server_tools.py` cover the helpers' unit behavior and verify each of the seven tools triggers exactly one refresh call on its miss path. The 1301h regression suite continues to pass, confirming `code_definition` was not affected by the helper extraction.

### `code_impact_response()` (`server_impl.py:9579-9604`)

Two modes:

- **Graph mode** (`symbol=` param): `_code_impact_graph_response()` calls `index.graph_impact(symbol, max_hops=max(1,max_hops), relations=relations)`. Default relations: `("imports","calls")`, `max_hops=3`. The `layer` param is a back-compat no-op (project graph only). Truncates `affected` at `max_results=50`. Each affected node carries a `community` field from `_load_cluster_lookup(root)`. When `include_tests=False` (default), nodes whose `source_file` matches `_is_test_path()` patterns are excluded from `affected`.
- **Heuristic mode** (`path=` param): File-based reverse-import search. Does not use `graph_query.py`.

### `code_graph_path_response()`

Resolves both `from_symbol` and `to_symbol` via `index.resolve_symbol()`. When either is unresolvable, returns `found=False` with `suggestions` from `_suggest_near_symbols()`. Otherwise calls `index.shortest_path(from_id, to_id, relations=relations, max_hops=max_hops, direction=direction)`. Always returns the consistent shape `{found, path_nodes, path_edges, hop_count, direction, suggestions}`.

The `direction` parameter (added in wave `12xr3`) controls which adjacency lists BFS may walk: `forward` (default — outgoing edges only, byte-identical to pre-13006 behavior), `backward` (incoming edges only, answering "who reaches me?"), or `either` (both — for general coupling questions). In `either` mode, every entry in `path_edges` carries an extra `traversal_direction` field (`"forward"` or `"backward"`) so the chain is unambiguous. Candidate edges at each BFS step are sorted by neighbor-id length so output is deterministic when multiple equal-length paths exist. Invalid direction values return `invalid_arguments` with the consistent shape preserved.

### `code_graph_community_response()`

Loads the cluster artifact via `_load_cluster_lookup()` / `graph_cluster.read_cluster_payload()`. Validates `community_id` is non-empty (returns `invalid_arguments` otherwise — closes the empty-string-matches-null-id edge case). Looks up the requested `community_id`; returns `{community_id, label, node_count, nodes}` where `nodes` are sorted by degree descending. On not-found, returns `suggestions: [{community_id, label, node_count}, …]` ranked by id/label substring match then node count — up to 5 entries — via `_suggest_near_communities()`. For ambient catalog discovery without a tool call, prefer the `wavefoundry://graph/communities` resource.

### `wave_graph_report_response()`

Obtains the index via `get_query_index(root, layer=layer_value)` (cached; see the query-cache section), calls `index.report(limit=max(1, min(limit, 100)), sections=sections)`. Limit is clamped to `[1, 100]`. Defaults to all five standard sections when `sections=None`. The `betweenness` section (opt-in via `sections=["betweenness"]`) is **served from the ranking persisted at build time** in the clusters artifact (`graph_cluster.compute_betweenness_ranking()`, wave `1p9q3`): a size-tiered computation over the directed calls-only subgraph — exact igraph betweenness below `BETWEENNESS_EXACT_MAX_NODES` (default 25,000), bounded-path `cutoff` approximation below `BETWEENNESS_CUTOFF_MAX_NODES` (default 100,000), and a deterministic degree/fan-out fallback above that or when igraph is unavailable (all thresholds env-overridable via `WAVEFOUNDRY_GRAPH_BETWEENNESS_*`). The response surfaces `betweenness_method` and `betweenness_metadata` (node_count, edge_count, top_n, elapsed_ms, cutoff when applicable). There is no per-query computation and no graph-size cap; a clusters artifact predating the build-time pass returns `betweenness_skipped_reason: "betweenness_not_in_artifact"` with a rebuild hint until the next graph rebuild.

### `_scan_all_call_sites_in_file()` (`server_impl.py:9373-9426`)

Scans a single file exactly once for a list of callee labels:

- **Python**: Parses with `ast`, walks all `ast.Call` nodes, matches against the full `label_set` in one pass. Returns `{label: [sorted call-site dicts]}`.
- **Non-Python**: Iterates `callee_labels` and calls `_treesitter_references()` then `_non_python_references()` per label against the single restricted file.

Called from `code_callhierarchy_response()` (outgoing direction, `server_impl.py:8993`) and `code_callgraph_response()` (per source file, `server_impl.py:9677`).

---

## Build Pipeline

### Wiring

`wave_index_build(content='graph')` invokes `setup_index.py --graph-only --root <root>` (`server_impl.py:2479-2480`). The `--graph-only` flag (`setup_index.py:757, 787-792`) routes to `run_index_rebuild(content="graph")` inside `setup_index.py`, which calls `_build_graph_artifacts()` in `indexer.py:1582-1642`:

```
wave_index_build(content='graph')
  → setup_index.py --graph-only
    → indexer._build_graph_artifacts()
      → graph_indexer.update_graph_index()   → project-graph.json + state
      → graph_cluster.update_graph_clusters() → project-graph-clusters.json
```

Semantic embedding (LanceDB) is skipped entirely in graph mode (`indexer.py:1938-1939`).

### Incremental vs. Full Rebuild

The graph build is **incremental at extraction AND at merge** (wave `1p9q2`). `update_graph_index()` receives `changed` and `removed` file sets and only calls `session.record_file()` for files in `changed`; unchanged files reuse their cached artifact rows in the per-file state store. `session.finalize()` then runs one unified merge pipeline in one of three modes:

- **Zero-change fast path** — nothing pending, nothing removed, and the store's payload binding matches the on-disk payload: the existing payload is returned with no merge work and no artifact rewrite.
- **Incremental delta merge** — the persistent `merge_state` sidecar (per-file raw node lists + resolved edge fragments) is loaded; changed/removed files' fragments are retracted and changed files' fragments recomputed from their fresh artifacts. **Symbol-scoped cross-file invalidation** then re-runs resolution for exactly (a) all edges of changed files and (b) any untouched file's edges whose resolution consults a candidate-index key in the *symbol delta* — the keys contributed by the old+new nodes of changed/removed files (plus the DI-synthesized-node delta). Fragment edges carry provenance (`_x` original external name, `_c` original confidence, `_d` dropped-read tombstone) so their raw form is recoverable without reading any unchanged row — promotion (external → bound) AND demotion (bound → external) both propagate into untouched files. State I/O per build is O(changed) rows plus the sidecar. Candidate indexes are rebuilt from the assembled node map each build (measured ~43 ms at 11k nodes — cheaper than incrementally persisting them).
- **Full re-merge** — a missing/inconsistent sidecar (crash window, pre-upgrade store) loads every stored row and recomputes all fragments through the same code path, loudly (stderr). This is also the differential oracle: the **equivalence invariant** — an incremental build produces the same node set, edge-key set, and `input_fingerprint` as a from-scratch build of the same tree — is enforced by a randomized differential harness in `test_graph_incremental_merge.py`.

Crash consistency: the store commits rows + sidecar + a `payload_stat_state='pending'` binding in one transaction, then the payload is written atomically, then the binding stat is committed. A crash in any window leaves a detectable mismatch and the next build degrades to a loud full re-merge — never a silently inconsistent graph. Downstream, `update_graph_clusters()` skips the clusters/betweenness recompute AND artifact rewrite when the merged `input_fingerprint` (recorded in the clusters artifact) is unchanged under the same cluster/graph builder versions.

A full re-extraction is forced when:
1. The state store is absent or empty (first build, or post-legacy-discard).
2. Any version constant changes (`schema_version`, `builder_version`, `walker_version`, `chunker_version`) — the store resets itself on open (`GraphStateStore.ensure_current()`).
3. The store's file listing is empty after loading — `update_graph_index()` expands `changed_set` to all files.

Additionally, when code files change, doc artifacts whose cached `mentioned_symbols` intersect the changed symbol ids are automatically re-scanned via the `impacted_docs` pass inside `finalize()`.

### Staleness Check

`_index_is_up_to_date()` always returns `False` for `content="graph"` (`server_impl.py:2194-2196`). The staleness gate is bypassed so the build always enters the incremental extraction logic — but this does not mean every file is re-extracted. Within that logic, only files in the `changed_set` are re-extracted; unchanged files reuse their cached state artifacts. Bypassing the gate means the caller never short-circuits before entering the logic, not that the logic discards incremental state.

### Separation from Semantic Index

`content="graph"` and `content="docs"` / `content="code"` are completely independent pipelines. The graph pipeline writes JSON artifacts only. The semantic pipeline runs LanceDB embedding and does not call `_build_graph_artifacts()`. `content="all"` (the default setup path) runs both.

---

## Implementation Paths

| Concern | Entry point | Key file |
|---|---|---|
| Build the graph | `update_graph_index()` | `graph_indexer.py:7761` |
| Read the graph from disk | `read_graph_payload()` | `graph_indexer.py:8079` |
| Load into memory | `GraphQueryIndex.__init__()` | `graph_query.py:123` |
| Resolve a symbol | `GraphQueryIndex.resolve_symbol()` | `graph_query.py:152` |
| BFS traversal | `GraphQueryIndex.traverse()` | `graph_query.py:178` |
| Cluster communities | `update_graph_clusters()` | `graph_cluster.py` |
| Extract DI edges | `resolve_di_edges()` | `graph_di_signals.py:245` |
| MCP: callers/callees | `code_callhierarchy_response()` | `server_impl.py:8896` |
| MCP: call tree | `code_callgraph_response()` | `server_impl.py:9610` |
| MCP: blast radius | `code_impact_response()` | `server_impl.py:9579` |
| MCP: shortest path | `code_graph_path_response()` | `server_impl.py:9864` |
| MCP: community members | `code_graph_community_response()` | `server_impl.py:9951` |
| MCP: structural report | `wave_graph_report_response()` | `server_impl.py:9719` |
| MCP: reference restriction | `_graph_references_candidate_files()` | `server_impl.py:9326` |
| MCP: definition narrowing | `_graph_definition_candidate_files()` | `server_impl.py` |
| MCP resource: graph status | `wavefoundry://graph/status` | `server_impl.py` |
| MCP resource: community catalog | `wavefoundry://graph/communities` | `server_impl.py` |

## Codebase Map (`gen_codebase_map.py`)

The **codebase map** (`docs/references/codebase-map.md`) is a generated, read-only consumer of the graph + cluster artifacts (wave 1p5tl). `gen_codebase_map.py` runs **offline** — no live server, no re-parse — and collapses the flat Leiden/label-prop communities to their representative package/directory so the top tier stays **bounded regardless of repo size** (a small repo is near-flat; a monorepo with hundreds of communities yields a capped, paged top tier with leveled per-area drill-down). Each area carries a one-line responsibility, key files + entry-point symbols, and a drill-in handle using the **stable `hub_node_id`** (never the renumbering `community_id`) for `code_graph_community`. It is a read-only consumer (no `GRAPH_BUILDER_VERSION` bump) and records `CLUSTER_BUILDER_VERSION` for staleness. `compute_areas(root, layer)` returns the structured area model (reused by per-area `AGENTS.md` scaffolding); `render_markdown(model)` produces the docs-lint-clean markdown.

**Ranking and labeling signals (wave `1p5zr`).** Entry points are ranked by **cross-area/cross-file fan-in** (callers outside the symbol's own file) rather than raw degree, so the map surfaces real entry points/chokepoints, not ubiquitous leaf helpers; trivial private helpers and config-key nodes are filtered. Config-only areas (predominantly `.json`/`.yaml`/etc. members) are demoted and rendered files-only (no fake entry points). An oversized representative directory is subdivided into its contributing communities. Labels are **tiered**: Tier-1 auto (a meaningful directory segment → dominant shared code token → central code symbol, never a doc/spec/config representative); Tier-2 authoritative (when the area's `representative_path/AGENTS.md` exists, its first `# heading` becomes the label and its first content line the responsibility, overriding the auto-label — re-read every generation, so human knowledge in `AGENTS.md` is folded in without ever living in the generated map). Symbol-kind tags are accurate or **omitted** (never a blanket `(function)`); non-code (`.html`/styleguide/asset) files are excluded from areas; each `hub_node_id` is a member of the area's representative package and appears in its key-files.

**repo-index feed (Option A, wave `1p5zr`).** The generator also refreshes a marker-delimited structural block (`<!-- waveframework:repo-index-modules begin/end -->`) in `docs/repo-index.md` from the area data, keeping the structural module list fresh; the human/agent narrative outside the markers is untouched. The marker is seed-rooted (`seed-030`) so any consuming project carries it. Idempotent + fail-safe (a missing file/markers is a safe no-op).

**Regeneration hook + MCP surface + idempotence (wave `1p601`).** Regeneration is hooked fail-safe into **`indexer.py::build_index`** (after the graph/cluster write), so **every** rebuild path — the freshness monitor, background refresh, and `wave_index_build content="docs"/"code"/"all"`/upgrade — refreshes the map (the old `setup_index` hook was relocated here). It is **change-only / idempotent**: a regeneration with unchanged inputs writes nothing — the render is skipped when a fingerprint over the graph + cluster artifacts **and** the per-area `AGENTS.md` is unchanged, and the write is skipped when the rendered content (ignoring the `Last verified` date line) matches the existing file (preserving the date). The map is exposed over MCP as the resource **`wavefoundry://codebase-map`** (served fresh from the generated file, regenerated fail-safe if missing) and refreshable on demand via **`wave_index_build(content="map")`** (map-only, no full rebuild). New MCP resources/tool options require a **server reconnect** to appear (FastMCP limitation). Also available as a CLI: `wf codebase-map --root .`.

**Per-area `AGENTS.md` context (wave 1p5xc).** Vendor-neutral per-area context files live at major areas' representative paths. `gen_codebase_map.py --scaffold-area-contexts` is an **opt-in** command that scaffolds an empty **stub** `AGENTS.md` for each major area (idempotent; never overwrites an existing file; never auto-authors conventions — humans write the content). `render_markdown` links each area to its `AGENTS.md` when one exists. Discovery is agent-agnostic: the map link, a standing convention line woven into the run-contract seed (`020`) and rendered into every host agent surface, and the doc index (a subdirectory `AGENTS.md` is a normal `.md` file, picked up by the index walk and surfaced in `docs_search` / `code_ask`). The only `@import` the framework adopts is the root `CLAUDE.md` → `@AGENTS.md` bridge (rendered by `render_agent_surfaces.py`); there are no per-folder `CLAUDE.md` bridge files and no nested `@import`.

## Related Docs

- `docs/architecture/search-architecture.md` — semantic index layers; how graph and semantic search are separate pipelines
- `docs/architecture/chunking-and-indexing-pipeline.md` — semantic embedding pipeline that runs alongside graph extraction in `content="all"` mode
- `docs/specs/mcp-tool-surface.md` — MCP tool surface specification; see "Navigation Tools" section for graph-backed tool descriptions and "Which Code Tool To Use" table for selection guidance
