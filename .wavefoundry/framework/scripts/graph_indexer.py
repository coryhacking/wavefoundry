#!/usr/bin/env python3
"""Graph index extraction and persistence for Wavefoundry."""
from __future__ import annotations

import ast
import functools
import gzip
import importlib
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

# Shared subprocess isolation (wave 1p8gu). graph_indexer does not insert SCRIPTS_DIR at module top
# (it does so lazily in spawn paths), so ensure the scripts dir is importable before importing it.
_GI_SCRIPTS_DIR = str(Path(__file__).resolve().parent)
if _GI_SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _GI_SCRIPTS_DIR)
import subprocess_util  # noqa: E402

try:
    from tree_sitter import Language, Parser as _TSParser
    _TS_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised when tree-sitter is not installed
    _TS_AVAILABLE = False
    Language = None  # type: ignore[assignment]
    _TSParser = None  # type: ignore[assignment]

GRAPH_SCHEMA_VERSION = "1"
GRAPH_BUILDER_VERSION = "41"  # Wave 1rvdp (carryover-followups) — 1rs45 PL/pgSQL loop-body DML recovery. A natively-parsed routine whose body holds loop scaffolding (tree-sitter-sql has no plpgsql grammar, so `FOR…LOOP`/`WHILE…LOOP`/`FOREACH…LOOP` shred into nested ERROR nodes) previously dropped the DML statement absorbed after `LOOP` in an inline-query-FOR (`FOR r IN SELECT…FROM src LOOP <DML>` — the parser is still in SELECT/FROM state at `LOOP`, so the write target was swallowed by the header query's `relation` span; `1p9qi`'s statement-dispatch recovered the header read but not the absorbed write). The recovery (Approach B) masks the body, keyword-strips ONLY the loop scaffolding, and reparses the residue through the existing statement unit (`_sql_analyze_program`, `recover=False`) — ZERO new DML/CTE vocabulary; direction/CTE/temp/alias/nested-loop handling all inherited from the reviewed unit. GATED to loop-bearing bodies (masked `\bLOOP\b`); non-loop partial bodies (IF/CASE/RETURN QUERY/EXECUTE) stay on the already-working walk. A loop-bearing body that also holds a sibling non-loop DML (`IF…INSERT…END IF`) keeps that DML — the strip removes only loop scaffolding, so the IF/CASE statements survive into the reparsed residue. New/recovered `reads`/`writes` edges from routine bodies + a new `sql_partial_bodies_recovered` module-node count property (splitting the existing `sql_partial_bodies` loudness signal into recovered-vs-still-partial) → extraction-output + node-property shape change → bump so consumer caches re-extract. NO CLUSTER_BUILDER_VERSION bump: `graph_cluster.py` untouched — recovered edges flow through the identical projection, and the cluster staleness gate already forces a full recluster on any graph_builder_version/input_fingerprint change (same discipline as 1p9q8 / 1p9qi). The sibling `1rqh2` change (tomllib-fallback removal) touches no graph code. Previous bump (Wave 1p9q8, graph-index-accuracy) — coordinated SINGLE bump covering all four changes; `graph_indexer.py` is the shared hub (Python extractor 1p9q4+1p9q7; cross-file pass 1p9q4+1p9q5; size gate 1p9q6), so one increment invalidates every consumer cache once. NO CLUSTER_BUILDER_VERSION bump: `graph_cluster.py` is untouched — its projection (`_project_undirected_projection`) and `_RELATION_WEIGHTS` are unchanged, and the cluster staleness gate (graph_cluster.py:1064-1073) already forces a full recluster whenever the graph's `input_fingerprint` OR `graph_builder_version` changes, both of which this bump changes; the new nodes/edges flow through the identical projection with no clustering-algorithm change (same discipline as 1p7dh config-key nodes / 1p9qd `writes` / 1p9qg `maps_to`, which added projection-visible nodes/edges without a cluster bump). (1p9q4) Python receiver-type resolution: annotated params/attributes/locals (including string forward-refs and faithful `Optional[T]`/union/generic unwrap) and constructor assignments (`local`/`self.attr`/module-global) now bind method calls to the annotated/constructed class's methods at `RECEIVER_RESOLVED` / `CONSTRUCTION_RESOLVED` confidence via the unique-candidate + method-exists-on-class gate — calls the Python extractor previously left `external::` or emitted no edge for. Faithfulness fix: non-Optional unions and generics no longer over-bind (multi-type receivers refuse); conflicting reassignment demotes; ambiguous cross-file twins stay `external::`. New/rebound `calls` edges → edge-set shape change. (1p9q5) Rust module model: `.rs` module nodes gain `rust_mod_decls`/`rust_inline_mods` properties; a crate-relative module-path scope key (`_build_rust_module_index`/`_rust_module_key`: mod-decl file mapping, inline-`mod {}` nesting, `#[path]`, crate-root, per-file identity fallback) feeds a `.rs` same-module disambiguation tier (unique-survivor, refuse-on-ambiguity, ordered after explicit-import disambiguation). Bounds: no cross-crate resolution, no re-export graph. The tier is faithful but produces zero productive end-to-end binds on this-era repos (module ≈ file; same-file same-module already resolves via `symbol_lookup`) — the durable deliverable is the module model + the new node properties (node-property shape change). C# was verify-and-close (namespace-key normalization already correct; no tier change). (1p9q6) Oversized-file line-scan tier: files over the tree-sitter parse cap (between the parse cap and the walk cap) degrade to a bounded line-anchored scan instead of contributing zero nodes — emitting module + top-level definition nodes marked `extraction: "line_scan"` and their `imports`/`defines` edges (no `calls`/`reads` — a line scan cannot resolve those faithfully), at `EXTRACTED` confidence. New module-node count properties `line_scan_defines`/`line_scan_imports`/`line_scan_skipped` (mirroring the 1p9qe recovery convention) plus `line_scan_ceiling_skipped` for whole-file past-ceiling skips. These definitions join the cross-file candidate sets, so referrers reconnect (and a line-scan twin correctly refuses an otherwise-unique bind — faithfulness). New nodes + new node properties + new edges → node-set shape change. (1p9q7) AST-anchored DI expansion to Python/TS: the pre-existing `injects`/`binds` DI relations (JVM/.NET, `graph_di_signals.py`) now also cover Python (FastAPI `Depends(...)` in defaults + `Annotated[...]`, alias-aware, impostor-refusing) and TypeScript (NestJS `@Injectable`/`@Inject(TOKEN)`/`@Module` providers, Inversify `bind().to()`/`toClass()`), collected AST-anchored (idiom text in strings/comments emits nothing) and resolved through the shared `resolve_di_edges` machinery. Unresolved/string-token/ambiguous DI targets stay plain `external::` (NOT a reserved `external::di::` namespace) — unique-match-or-external. The JVM/.NET path is byte-identical (the shared resolver change is opt-in per-signal via `faithful_external`/`*_token` flags set only by the new AST collectors). New Python/TS `injects`/`binds` edges → edge-set shape change. New node properties (1p9q5/1p9q6) + new/rebound `calls` edges (1p9q4) + new `injects`/`binds` edges (1p9q7) + new line-scan nodes (1p9q6) → node/edge/property-set shape change → bump so consumer caches re-extract (a cached fragment from v39 would silently lack the new properties and the new binds). Previous bump (1rrx5, sql-graph-accuracy-followups) — coordinated SINGLE bump covering the bounded 1p9qi statement-unit/capture faithfulness follow-ups; R7 is a read-only diagnostic (no projection change → no CLUSTER_BUILDER_VERSION bump). (R1) trigger `EXECUTE FUNCTION|PROCEDURE <name>` action names no longer mint a phantom `reads external::<fn>` — the action name parses as a trailing object_reference after keyword_execute and is now skipped by a latching flag mirroring the RETURNS-type skip; the ON-table read (before keyword_execute) is preserved. (R2) MERGE `WHEN … THEN` branch subqueries now surface their table reads — the merge loop routes each `subquery` node inside a `when_clause` through the read walk, so a `SET x=(SELECT … FROM lookup_tbl)` assignment read AND a `list`-wrapped `VALUES ((SELECT … FROM seed_tbl))` read are emitted as `reads`; predicate columns, assignment LHS, and merge aliases still mint nothing. (R3) PL/pgSQL `DECLARE <var> <type>` non-builtin type names (`record`, custom types) no longer mint a phantom read — walk_reads skips a function_declaration's direct object_reference type name while still descending into other children, so a `DECLARE x int := (SELECT … FROM t)` default-value read stays preserved (builtin types already parsed as non-object_reference keyword nodes). (R4) bracket/backtick/quote-quoted external ids on the SQL-file path normalize to a clean `external::dbo.users` — node-id hygiene at the external-emit site only (the names-as-written statement unit output is untouched); binding stays unique-match-or-drop so two differently-quoted forms collapse onto the same external node, never a wrong bind. (R5) the embedded-SQL sniff gate now recognizes leading `TRUNCATE`/`ALTER`/`DROP`, so schema-affecting embedded statements at known sinks are captured and bound as `writes` (analyze_statement already handled their write direction). (R6a) the routine body-definition drop is now UNCONDITIONAL on routine nodes so the "routine bodies never define schema objects at module scope" invariant is total — an unnamed-but-parseable `CREATE FUNCTION () RETURNS integer …` (empty name + builtin return type leaves routine_name None) no longer leaks its in-body `CREATE TABLE`. Phantom-edge removals (R1/R3/R4/R6a) + newly-surfaced contained reads (R2/R5) → extraction-output change → bump so consumer caches re-extract. Previous bump (1p9qi, sql-graph-accuracy — coordinated SINGLE bump covering the whole wave; later lanes do not re-bump). (1p9qc) SQL keyword-noise suppression: all-relation, case-insensitive SQL keyword stoplist (`_SQL_RELATION_KEYWORD_STOPLIST` + `_sql_relation_candidate_filter`, SQL mode only) + dotted/bare column-token reduction (structural `field`/`object_reference` disambiguation) + the self-referential CREATE-import skip — previously every SQL file minted fake `external::FROM/JOIN/ON/SELECT/WHERE` nodes and `external::users.id`-style column externals on both `calls` and `imports`. (1p9qd) Clause-aware SQL statement-unit extraction rewrite: the generic substring/regex candidate path is RETIRED for SQL mode (`_sql_apply_file_extraction` + the frozen public unit `sql_statement_references(sql_text)`); references come only from `object_reference` clause positions with statement-derived direction, so SQL emits `reads` and NEW `writes` relation edges instead of `calls`/`imports` (writes = INSERT INTO/UPDATE/DELETE FROM/MERGE INTO/ALTER/DROP/TRUNCATE targets); view/FK/index lineage as reads; new `sql_kind` node property (table/view/procedure/function/trigger; node kind stays class/function); qualified-name (schema.table) resolution; phantom alias/CTE/temp/derived-table definitions no longer minted — relation-set + node-set + property shape change. (1p9qe) ERROR-region DDL recovery tier: top-level ERROR regions route to a bounded, comment/string-masked line-anchored scan recovering CREATE {PROCEDURE|FUNCTION|TRIGGER|TABLE|VIEW|INDEX} definitions with `extraction: "sql_recovery"` provenance, plus module-node `sql_error_regions`/`sql_recovered_definitions`/`sql_unrecovered_regions` count properties; recovered routine bodies re-parse through the statement unit and their references RE-ATTACH to the recovered routine node (previously procedures vanished and body references dangled at module scope). (1p9qf) Embedded-SQL capture at known Java/C#/MyBatis-XML sinks: NEW fragment keys `sql_capture_candidates`/`sql_capture_dynamic` (joined the incremental-merge passthrough list); finalize bind via the statement unit → method→table `reads`/`writes` at LITERAL_DERIVED, unique-match-or-drop with identifier-quote normalization, unmatched tables mint relation-scoped `external::sql::<name>` externals (invariant-tested namespace). (1p9qg) ORM entity→table mapping: NEW `maps_to` relation (JPA `@Entity`+`@Table(name=…)`/`@Entity(name=…)`, EF `[Table("…")]`/`ToTable("…")` positive-origin sinks → table node at LITERAL_DERIVED, declared names only — conventions refused and counted); NEW fragment keys `orm_entity_candidates`/`orm_entity_dynamic`/`orm_entity_convention` (passthrough list). Two new relations + SQL relation migration (calls/imports → reads/writes) + new node properties + new fragment keys + node-set change → bump so consumer caches re-extract (a cached fragment from v37 would silently lack the new keys and the SQL edge model). Previous bump (1p9qh, java-csharp-enterprise-accuracy — coordinated SINGLE bump covering the whole wave; later lanes do not re-bump): (1p9q9) Structured Java import parsing: Java `import_declaration` nodes are parsed structurally (explicit / wildcard / static member / static wildcard) instead of falling to the shared regex fallback, which truncated `import com.foo.*;` into a useless `com.foo.` candidate and emitted a spurious `external::static` edge for every static import. Wildcard imports now emit a package-prefix `imports` edge (`external::com.foo.*`) that participates in ambiguous-receiver disambiguation with the same unique-survivor rule as an explicit import (two matching wildcards → stay external; a same-package twin counts as an implicit match so Java package shadowing is honored); statically-imported members resolve bare calls (`import static com.foo.Bar.baz;` + `baz()` → project `Bar.baz` when it exists, else qualified `external::Bar.baz` — never bare; static wildcard analogous for otherwise-unresolved bare calls); `external::static` never appears. Non-Java candidate extraction is untouched (the shared regex is unchanged; regression-pinned). (1p9qa) Inheritance edges (`extends`/`implements`) + inherited-method resolution for Java/C#. (1p9qb) `this.field` receiver resolution, annotation-type kind fix, and package-declaration-keyed disambiguation. Extraction-output + edge-set shape change → bump so consumer caches re-extract. Previous bump (1p9q3 (1p9py, compact+gzip+atomic persistence)): graph artifacts are now written as gzip-compressed COMPACT JSON (separators=(",", ":"), sort_keys retained) through a same-directory temp file + os.replace atomic write; readers sniff the gzip magic bytes (0x1f 0x8b) and transparently fall back to legacy plain JSON, and a corrupted/truncated gzip degrades to the caller default exactly like corrupted JSON. Serialization-only — node/edge content, counts, and `input_fingerprint` semantics are unchanged — but the on-disk artifact FORMAT changed, so bump per the standing artifact-shape rule (downstream caches and the version-staleness query path treat the transition as a rebuild boundary, rewriting pre-upgrade plain artifacts compressed). This single bump also covers the wave's sibling artifact-shape changes (1p9q1 build-time betweenness, 1p9q2 incremental merge state store) per the coordinated-single-bump serialization point. Previous bump (1p7dh, reads_config Java/Spring file config): extended the config-key->reader `reads_config` edge to Java/Spring FILE config — `.properties`/`.yml`/`.yaml` now emit config-key NODES (`file::dotted.key`, kind "class") and Java artifacts capture `@Value("${key}")` placeholders + `getProperty`/`getRequiredProperty` calls into `config_read_candidates`; the language-agnostic finalize pass binds them on a unique config-file + distinctive-key match. Extraction-output change (new nodes + populated config_read_candidates → new edges) → bump so consumer caches re-extract. Previous bump (1p7de (graph-edge-trust)): coordinated bump for two extractor changes (1p7dg confidence promotion + 1p7dh string-literal binding) so consumers re-extract. (v34 supersedes the in-flight v33 test builds: the 1p7dh `instruments` capture was refined to read `namedOneOf(...)` multi-arg matchers + matchers nested in structural wrappers (`implementsInterface`/`hasSuperType`/`isSubTypeOf`) — an EXTRACTION-OUTPUT change, so it gets its own version increment per the builder-version discipline; without the bump an incremental-update consumer that skips unchanged files would not pick up the broadened `instruments` targets. Downstream-validated: javaagent 24/24 OTel TypeInstrumentation classes carry correct `instruments`; Swift solaris promotion realized EXTRACTED 52.7%→33.4%.) 1p7dg generalizes the v23 TS/JS confidence promotion to ALL languages: a call that binds a UNIQUE non-`external::` project node (same-file `symbol_lookup` match at the extraction site, or an exact-unique cross-file rewrite — exact simple name / exact qualified name / Go package-authoritative / import-edge-disambiguated) is promoted EXTRACTED→RECEIVER_RESOLVED. Target UNCHANGED — only the confidence label moves on an already-unique bind — so no new wrong-twin/zeroed-edge risk; the AC-2 type-guess fallback + same-dir/C# namespace heuristics deliberately stay EXTRACTED. Self-host lift: Python EXTRACTED 90.4%→31.9%, resolved 1,136→8,102. 1p7dh adds a new `reads_config` EDGE (a code site `.get("KEY")`/`cfg["KEY"]` → the config-key node `file.json::key` it reads, at `LITERAL_DERIVED` confidence; triple-gated — config-file basename + key-distinctiveness + unique match — so ubiquitous dict literals don't bind data-JSON keys) and a new `instruments` NODE PROPERTY on OTel `TypeInstrumentation` classes (their `typeMatcher()` ByteBuddy matcher target strings, descriptive metadata — NOT an edge, since instrumentation targets are ~100% third-party by design). Edge-confidence relabels + new relation + new node property → node/edge-set shape change → bump (consumer graph caches re-extract). Previous bump (1p66e, graph-edge-extraction-determinism): cross-file resolution made order-independent so identical input yields an identical resolved edge set across from-scratch rebuilds (a consumer observed 75068 vs 74890 edges on identical source). Three order-dependent sites fixed with explicit stable tie-breaks: (a) `per_file_simple` length-tie now breaks on the lexicographically smaller node_id (was first-seen by node_map iteration order); (b) `imports_by_file` final-segment collision now keeps the lexicographically smallest FQN (was "later import wins" by edge_map order); (c) cross-file edge rewrites are applied sorted by (new_key, old_key) so a `setdefault` collapse onto the same new_key keeps a stable survivor. Plus a persisted `input_fingerprint` (sha256 over the sorted node-set + sorted resolved edge-set) in the graph payload + state for downstream reproducibility verification. Edge-set shape stabilizes → bump so consumer caches re-extract. Faithfulness preserved: every resolution branch still requires a UNIQUE (`len==1`) match, so no `len==1` outcome changes and no wrong same-name twin is newly bound — only genuinely-ambiguous tie choices are made deterministic. Previous bump (1p61v, ts-symbol-kind-extraction-faithfulness): TS/JS type-shape members are no longer mislabeled `function`. A `type_alias_declaration` now extracts as kind="type" and an interface/object-type `property_signature` (a `: T` data member) as kind="property" (method *signatures* keep `function`) — previously both fell through to the default `function`, so `code_outline`-invisible `: string` fields and `export type` aliases rendered as `(function)` entry points in the codebase map (p60n field trace, Issue 1). Plus a registration-site faithfulness guard (`_ts_is_emittable_symbol_name`): a definition whose picked name is the reserved word `function` (anonymous `function (…){}` expressions) or a non-identifier route-path token (`/`) is no longer registered as a junk symbol (Issue 2). Node KIND-set + node-set shape change → bump (consumer graph caches re-extract). Conservative: contextual keywords that are legal identifiers (`type`, `async`, `fn`, …) are NOT rejected, so no real callable is dropped. Previous bump (1p5c4, guard-oversized-files-indexing): files over the tree-sitter parse cap (default 2 MB; override WAVEFOUNDRY_MAX_TS_PARSE_BYTES / `indexing.max_treesitter_parse_bytes`) now SKIP AST graph extraction, and files over the hard size cap are dropped from the walk entirely — so oversized files contribute no graph nodes. Bump forces re-extraction so any large file parsed under v29 has its stale nodes pruned. Wave 1p4up (member-access-constant-reads): a CONSTANT accessed via a qualified member expression (`Status.ACTIVE`, `AppConstants.Network.userAgent`, `Outer.Inner.TOKEN`, Ruby/PHP `A::B::C`) now produces a function→constant `reads` edge by EXACT qualified-name match (const-kind-gated; the qualifier disambiguates so a same-leaf param/import/bare-call can't match). Faithfulness guards: F1 full-qname (not `_simple_name` partial key), F2 reject `this`/`self`/`super`/`cls`, F4 qualifier-shadow (a member-access read whose head is a function param/local is dropped — `func_locals` from per-language binding nodes) + the property/trailing leaf of a member access is no longer also buffered as a bare read (member-path resolves it instead). New `reads` edges → node/edge-set shape change → bump (consumer graph caches re-extract). Wave 1p4q4 review (28) (D1/D2): namespace-scoped enum member nodes now carry the enclosing namespace prefix (`NSA.Inner.AAA` vs `NSB.Inner.AAA` — no cross-namespace collision/clobber), and constant nodes are EXEMPT from the ≤2-char short-symbol prune so short members (`Status.OK`/`Dir.Up`) resolve. Node-set shape change → bump (consumer graph caches re-extract). Wave 1p4q4 (27): TS `enum`/`const enum` members are now `kind="constant"` graph nodes (`Enum.Member`), child of the enum type node. Wave 1p4ls (26) (graph-constant-nodes-and-references): module-/type-level CONSTANT declarations are now graph nodes (kind="constant", carrying a simple-literal `value` where the RHS is a literal) across all core languages, plus a faithfulness-gated function→constant `reads` edge (same-scope + explicitly-imported only; never binds a coincidental same-name twin — symbol_lookup uniqueness + a const-kind gate + a local-shadow guard). Consumers surface them: code_definition resolves a constant name; code_references lists readers in a distinct `reads` bucket (NOT merged into callers); graph_neighbors includes constants when `reads` is requested. `reads` is OPT-IN for default 1-hop traversal (excluded when no explicit relations are passed, so a hot constant does not balloon neighbor sets / 1p4hu expansion) and stays OUT of the impact/call default relations; constant nodes + `reads` edges are excluded from clustering (CLUSTER_BUILDER_VERSION 8→9, no community-label shift). resolve_symbol is kind-aware (a constant sharing a simple name no longer shadows a callable lookup). Detection reuses the 1p4mf chunk-lane per-language predicates (one detector, two consumers — Req-7); the graph lane is BROADER where it lands naturally (class/type-level constants; Swift enum cases; Go grouped-const per member). NOTE: TS `enum`/`const enum` members ARE emitted as constant nodes (`Enum.Member`) — delivered in 1p4q4 (see the v27 line at the top). Kotlin bare top-level/object `val` (no `const`) stays `kind="variable"` (an immutable binding is not a compile-time constant — won't-do). Previous bump (1p4eq, cross-file-resolution-followups): one consolidated bump covering five graph-shaping changes: (1p4ef) fix a leaked `qualified` loop var that injected phantom qualified_index candidates for collapsed/basename-merged nodes (C#/Swift/Rust/Ruby) and silently suppressed unique cross-file resolution; (1p4er) same-package/same-directory disambiguation fallback for ambiguous receivers used WITHOUT an import (Java field miss, `JreCompat.canAccess`), GATED to Java/Kotlin/Go (same-dir ⇒ same-package visibility; Python/JS/TS/Rust/C# excluded); (1p4et) Go methods now keyed `Type.method` (was bare `method`) + package-qualified receiver inference (`var h foo.Helper` → `foo.Helper`, package PRESERVED and resolved by the candidate's package directory); (1p4eu) Rust `Type::assoc_fn()` resolution + struct-literal/`::new()` let-binding type inference; (1p4ev) C# namespace-membership disambiguation (own-namespace ∪ `using`), the namespace derived from each file's DECLARED namespace nodes by longest-prefix (nesting-proof), NOT by fixed-segment qname stripping. FAITHFULNESS FIXES (1p4eq adversarial verification): the 1p4et/1p4ev paths above already incorporate the over-resolution fixes the verification caught — dropping the Go package qualifier bound a co-located cross-package twin, and fixed-segment C# namespace stripping mis-derived a nested-class caller's namespace and bound a coincident sibling twin; both now stay external unless a unique package/namespace-faithful candidate matches. COVERAGE SCOPE — synthetic-fixture tests only, NOT yet validated against a real consumer project: same-package = Java; cross-file method/assoc-fn = Go + Rust; ambiguous-receiver namespace membership = C#. Each carries an adversarial "never binds the wrong twin / stays external" test. **Correction to the v24 line below:** v24 advertised its `imports`-edge disambiguation as "language-agnostic (Python + Java/Kotlin/C#/Go)" — that was over-stated; it fired ONLY for Python + Java (per-type imports), and was dead code for C#/Go/Rust (their import heads are namespaces/packages, not type names) until v25 supplied the per-language mechanisms above. Previous bump (1p47e 1p470): Python sibling-loader return-type inference + cross-file import disambiguation. v24 resolves the lazy-loader blast-radius hole — `gq = _load_graph_query()` (→ `_load_script("graph_query")`) and direct `v = _load_script("mod")` now bind `v.Class.method()` / `v.func()` to the loaded module's symbols (previously emitted NO edge because `v` had no known type; e.g. `GraphQueryIndex.from_root` was called from 14 sites with 0 incoming edges). Also adds import-edge-based disambiguation in the cross-file rewrite pass: an ambiguous `external::Type.method` (multiple same-simple-name candidates) is disambiguated via the source file's `imports` edge for `Type`, language-agnostically (Python + Java/Kotlin/C#/Go). Previous bump (1p2q3 / 1p2tz post-ship-5 1.3.16): TS/JS symbol-table promotion. Intra-file (and cross-file unique-simple-name) calls where `_ts_resolve_target` bound directly to a project node previously landed as `EXTRACTED` even though the binding required an exact match in `symbol_lookup`. Field validation on the v22 stable state showed `getRootToken` and similar intra-file arrow-const targets had only `EXTRACTED` incoming edges — invisible to the `receiver_resolved` attribution bucket — despite the symbol being correctly resolved at extraction time. v23 promotes these to `RECEIVER_RESOLVED` for TS/JS only: when `_ts_resolve_target` returns a non-`external::` project node (i.e. the call site bound to a locally-defined symbol or to the unique cross-file simple-name match) the edge is high-confidence by construction. Affects TS/JS only — other languages route through their per-language receiver resolvers + the cross-file rewrite pass and are out of scope for this round. Previous bump (1.3.12 v21→v22): TS/JS relative-import path resolution into import_targets. v21 emitted arrow-const function nodes but +9,379 of the new TS edges landed as EXTRACTED rather than RECEIVER_RESOLVED because intra-package callers using relative imports (`import { foo } from './events'`) had `import_targets[foo]` populated with the lossy `external::events` form. The cross-file rewrite pass then promoted the edge to the right project node but kept it at EXTRACTED confidence. v22 extracts the raw module specifier before `_ts_clean_name` strips the `./` prefix, resolves relative imports against the source file's directory, then runs the same barrel walk + import_targets binding as the aliased path. The +9,379 EXTRACTED edges observed in the field in v21 → v22 should migrate to RECEIVER_RESOLVED for any intra-package direct call to a relatively-imported arrow-const. Affects TS/JS only. Previous bump (1.3.11 v20→v21) was the arrow-const node-emission half — v22 completes the receiver-type attribution half. Modern TS code uses `export const foo = async (args) => { ... }` as the dominant function shape (field-confirmed: ALL backend functions on a 12k-node Nx monorepo are arrow-const, zero `function` declarations). Tree-sitter parses these as `lexical_declaration → variable_declarator → arrow_function`, not `function_declaration`, so the default name-from-descendants extractor returned empty and the symbol never registered. v21 detects arrow-const bindings explicitly and registers each as a function symbol; walks scope through the arrow body so calls FROM inside arrow-const-bound functions get attributed to the const name rather than the file. Expected impact on barrel-export-heavy + arrow-const-heavy codebases: TS resolved-share rises from 6% range into 30–60% (per field estimate). Affects TS/JS only — other languages unchanged. Previous bump (1.3.10 v19→v20) covered direct-function-call import_targets promotion + bundler-mode .js→.ts swap + community-label barrel deprioritization
GRAPH_DIRNAME = "graph"

# Wave 1p9q3 (1p9py): graph artifacts persist as gzip-compressed COMPACT JSON.
# Level 6 (the zlib default) is the write-speed balance point — within a few
# percent of level 9's ratio on JSON text at a fraction of the CPU, keeping the
# post-edit hook's graph refresh cheap. Readers sniff the gzip magic bytes and
# fall back to legacy plain JSON, so pre-upgrade artifacts stay readable. The
# `.json` filenames are intentionally kept: content is sniffed, not the extension.
GRAPH_GZIP_LEVEL = 6
_GZIP_MAGIC = b"\x1f\x8b"


def _pick_shorter_node_id(existing: str | None, candidate: str) -> str:
    """Deterministic per-``(file, simple_name)`` winner (wave 1p66e).

    Keeps the shortest qualified node id (the outer/real definition), breaking a
    length tie by the lexicographically smaller id. Pure and **order-independent**:
    ``_pick_shorter_node_id(a, b) == _pick_shorter_node_id(b, a)`` for any pair, so
    the cross-file resolution candidate set no longer depends on ``node_map``
    iteration order (the source of identical-input edge-count drift). The previous
    inline rule (``len(candidate) < len(existing)``) kept the first-seen id on a
    length tie, which IS order-dependent.
    """
    if existing is None:
        return candidate
    return candidate if (len(candidate), candidate) < (len(existing), existing) else existing


# Wave 1p4ww: single project graph — the framework graph layer was removed.
GRAPH_FILENAMES = {
    "project": "project-graph.json",
}
GRAPH_STATE_FILENAMES = {
    "project": "project-graph-state.json",
}
# Wave 1p9q3 (1p9q2): the per-file state store superseded the monolithic JSON
# state document. `GRAPH_STATE_FILENAMES` is retained ONLY as the legacy
# filename (discarded one-time at store open; also the pre-upgrade fallback for
# the version-staleness probe). A distinct `.sqlite` name is used so nothing
# ever gzip-sniffs the database file.
GRAPH_STORE_FILENAMES = {
    "project": "project-graph-state.sqlite",
}
GRAPH_STORE_SCHEMA_VERSION = "1"

_DOC_EXTENSIONS = {".md", ".markdown", ".txt"}
_CODE_EXTENSIONS = {
    ".py",
    ".js", ".jsx", ".mjs", ".cjs",
    ".ts", ".tsx", ".mts", ".cts",
    ".go",
    ".rs",
    ".java",
    ".scala",
    ".cs",
    ".c",
    ".cpp",
    ".cc",
    ".cxx",
    ".h",
    ".hpp",
    ".sh",
    ".bash",
    ".zsh",
    ".fish",
    ".tf",
    ".tfvars",
    ".hcl",
    ".tpl",
    ".kt",
    ".kts",
    ".swift",
    ".m",
    ".mm",
    ".rb",
    ".php",
    ".yaml",
    ".yml",
    ".properties",
    ".toml",
    ".json",
    ".jsonc",
    ".css",
    ".scss",
    ".ps1",
    ".psm1",
    ".html",
    ".htm",
    ".sql",
    ".psql",
    ".pgsql",
    ".ddl",
    ".dml",
    ".tsql",
    ".hql",
    ".xml",
    ".jsp",
    ".xsd",
    ".xsl",
    ".xslt",
    ".svg",
    ".php",
}
_CODE_FILENAMES = {
    "Jenkinsfile", "Makefile", "GNUmakefile", "Dockerfile", "Vagrantfile", "Brewfile",
    "Fastfile", "Appfile", "Podfile", "Gemfile", "Procfile",
}
_STOP_TERMS = {
    "self", "cls", "main", "test", "tests", "run", "get", "set", "new",
}
_DOC_MATCH_STOP_TERMS = _STOP_TERMS | {
    "accept", "action", "active", "apply", "assert", "buffer", "caller",
    "client", "config", "create", "cursor", "define", "delete", "enable",
    "enabled", "errors", "export", "filter", "format", "handle", "header", "helper",
    "import", "insert", "length", "logger", "lookup", "method", "object",
    "option", "output", "params", "parser", "plugin", "reader", "record",
    "reduce", "remove", "render", "report", "result", "return", "runner",
    "schema", "search", "select", "sender", "server", "signal", "simple",
    "single", "source", "static", "status", "stream", "string", "struct",
    "suffix", "target", "update", "values", "verify", "worker", "writer",
    # Common config / JSON field names — too ambiguous for doc→code keyword edges.
    "auto_index", "change", "dashboard", "entrypoint", "host", "include_dirs",
    "poll_interval_ms", "port_range_end", "port_range_start", "preferred_port",
    "project_label", "task", "terminology", "version", "wave",
}
_DOC_PATH_SUFFIXES = (
    ".md", ".markdown", ".py", ".json", ".jsonc", ".js", ".jsx", ".mjs", ".cjs",
    ".ts", ".tsx", ".css", ".html", ".txt", ".yaml", ".yml", ".toml",
)
_DOC_SCAN_EXCLUDE_PREFIXES = frozenset({
    "docs/waves/", "docs/plans/", "docs/contributing/", "docs/reports/",
})
_MIN_DOC_MATCH_TERM_LEN = 6
_SHORT_SYMBOL_MAX_LEN = 2
_MINIFIED_FILE_RE = re.compile(
    r"(?:\.min\.|\.prod\.|\.production\.|\.bundle\.|\.chunk\.)", re.IGNORECASE
)

_PY_DEF_RE = re.compile(r"^(\s*)(async\s+def|def|class)\s+([A-Za-z_][A-Za-z0-9_]*)\b")
_JS_DEF_RE = re.compile(
    r"^\s*(?:export\s+)?(?:async\s+)?(?:function|class)\s+([A-Za-z_][A-Za-z0-9_]*)\b"
)
_JS_CONST_FN_RE = re.compile(
    r"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?:async\s*)?(?:\([^)]*\)|[A-Za-z_][A-Za-z0-9_]*)\s*=>"
)
_JS_REQUIRE_RE = re.compile(
    r"^\s*(?:const|let|var)\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*require\(['\"]([^'\"]+)['\"]\)"
)
_JS_IMPORT_RE = re.compile(
    r"^\s*import\s+(.+?)\s+from\s+['\"]([^'\"]+)['\"]"
)
_JS_CALL_RE = re.compile(r"(?<![\w.])([A-Za-z_][A-Za-z0-9_]*)\s*\(")
_FENCED_CODE_RE = re.compile(r"```[^\n]*\n(.*?)^```", re.DOTALL | re.MULTILINE)
_INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
_MD_LINK_RE = re.compile(r"!?\[([^\]]*)\]\(([^)]+)\)")

_TS_LANGUAGE_MODULES: dict[str, tuple[str, str]] = {
    "javascript": ("tree_sitter_javascript", "language"),
    "typescript": ("tree_sitter_typescript", "language_typescript"),
    "go": ("tree_sitter_go", "language"),
    "rust": ("tree_sitter_rust", "language"),
    "java": ("tree_sitter_java", "language"),
    "c": ("tree_sitter_c", "language"),
    "cpp": ("tree_sitter_cpp", "language"),
    "csharp": ("tree_sitter_c_sharp", "language"),
    "bash": ("tree_sitter_bash", "language"),
    "kotlin": ("tree_sitter_kotlin", "language"),
    "swift": ("tree_sitter_swift", "language"),
    "objc": ("tree_sitter_objc", "language"),
    "hcl": ("tree_sitter_hcl", "language"),
    "scss": ("tree_sitter_scss", "language"),
    "make": ("tree_sitter_make", "language"),
    "scala": ("tree_sitter_scala", "language"),
    "html": ("tree_sitter_html", "language"),
    "ruby": ("tree_sitter_ruby", "language"),
    "yaml": ("tree_sitter_yaml", "language"),
    "toml": ("tree_sitter_toml", "language"),
    "json": ("tree_sitter_json", "language"),
    "css": ("tree_sitter_css", "language"),
    "powershell": ("tree_sitter_powershell", "language"),
    "sql": ("tree_sitter_sql", "language"),
    "xml": ("tree_sitter_xml", "language_xml"),
    "php": ("tree_sitter_php", "language_php"),
}

_TS_PARSERS: dict[str, Any | None] = {}
_TS_LANGS: dict[str, Any | None] = {}
_TS_WARNED: set[str] = set()

_TS_EXTENSION_TO_LANGUAGE: dict[str, str] = {
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".mts": "typescript",
    ".cts": "typescript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".c": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".h": "c",
    ".hpp": "cpp",
    ".cs": "csharp",
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "bash",
    ".fish": "bash",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".swift": "swift",
    ".m": "objc",
    ".mm": "objc",
    ".hcl": "hcl",
    ".tf": "hcl",
    ".tfvars": "hcl",
    ".scss": "scss",
    ".sass": "scss",
    ".make": "make",
    ".mk": "make",
    ".scala": "scala",
    ".html": "html",
    ".htm": "html",
    ".rb": "ruby",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".json": "json",
    ".jsonc": "json",
    ".css": "css",
    ".ps1": "powershell",
    ".psm1": "powershell",
    ".sql": "sql",
    ".psql": "sql",
    ".pgsql": "sql",
    ".ddl": "sql",
    ".dml": "sql",
    ".tsql": "sql",
    ".hql": "sql",
    ".xml": "xml",
    ".jsp": "xml",
    ".xsd": "xml",
    ".xsl": "xml",
    ".xslt": "xml",
    ".svg": "xml",
    ".php": "php",
}

_TS_DEF_KEYWORDS = (
    "class", "interface", "struct", "enum", "trait", "record", "module",
    "namespace", "package", "function", "method", "constructor", "procedure",
    "macro", "rule", "resource", "object", "target", "task", "command",
    "table", "view", "trigger", "query", "block", "type", "definition",
    "declaration", "implementation", "item", "property", "attribute", "pair",
    "selector", "element", "tag", "pair", "entry",
)
_TS_IMPORT_KEYWORDS = ("import", "using", "include", "require", "source", "use", "load")
_TS_CALL_KEYWORDS = ("call", "invoke", "invocation", "command", "expression", "query", "access", "reference")
# Wave 1p4eu: language statement keywords the multi-token relation fallback (a
# regex over a node's text) would otherwise emit as junk `external::<kw>` import
# edges — e.g. Java/Kotlin `import`, Kotlin `as`/`package`, Rust `use`/`pub`/`fn`.
# None is ever a valid import or call TARGET in any supported language.
_RELATION_KEYWORD_NOISE = frozenset({
    "import", "use", "using", "package", "as", "from", "pub", "fn", "fun",
    "mod", "export", "include", "require",
})
# Wave 1p9qi (1p9qc): SQL keyword stoplist — originally the relation-candidate
# noise filter for the generic regex-fallback path (statement keywords leaked
# into BOTH call and import candidates and minted fake `external::FROM`-style
# nodes from every SQL file; `_RELATION_KEYWORD_NOISE` above is import-only AND
# case-sensitive, so uppercase `FROM` slipped past it even there). That
# transitional filter (`_sql_relation_candidate_filter`) was removed at the
# 1p9qi review once 1p9qd's clause-aware statement unit made SQL bypass the
# generic candidate path entirely; the stoplist's LIVE consumer is now the
# statement unit's `make_ref` refusal (a grammar mis-parse that lands a keyword
# token in an `object_reference` position must still never mint a reference).
# Membership is checked case-insensitively via `.casefold()` — SQL keywords are
# case-insensitive. STRICTLY SQL-GATED: `select`/`update`/`delete`/`values`/…
# are legitimate identifier names in host languages, so this stoplist must
# never touch non-SQL candidate streams.
# A sane common ANSI + mainstream-dialect superset, deliberately extensible;
# a rare dialect straggler leaking is strictly better than systematic noise.
# Known limitation (accepted in the change doc): an unquoted table literally
# named like a keyword (e.g. `values`) is suppressed as a bare reference; it
# still survives schema-qualified (`schema.values`).
_SQL_RELATION_KEYWORD_STOPLIST = frozenset({
    # core DML/query
    "select", "from", "join", "on", "where", "group", "order", "by", "having",
    "insert", "into", "update", "delete", "set", "values", "as", "distinct",
    "limit", "offset", "top", "fetch", "merge", "matched", "output", "returning",
    # operators / predicates
    "and", "or", "not", "null", "is", "in", "like", "between", "exists", "any",
    "all", "some", "case", "when", "then", "else", "end", "escape", "collate",
    "asc", "desc", "true", "false", "unknown",
    # joins / set ops
    "left", "right", "inner", "outer", "full", "cross", "natural", "union",
    "intersect", "except", "with", "using",
    # DDL
    "create", "table", "view", "index", "primary", "key", "foreign",
    "references", "constraint", "unique", "default", "check", "drop", "alter",
    "add", "column", "rename", "truncate", "replace", "temp", "temporary",
    "if", "cascade", "restrict", "comment",
    # procedural / transactional
    "begin", "commit", "rollback", "transaction", "declare", "cursor", "open",
    "close", "while", "loop", "for", "to", "return", "returns", "procedure",
    "function", "trigger", "call", "execute", "exec", "grant", "revoke",
    # windowing / misc functions that read as bare identifiers in clause text
    "over", "partition", "row", "rows", "range", "window", "current",
    "cast", "convert", "coalesce", "nullif", "count", "sum", "min", "max", "avg",
    # common column type keywords (leak from DDL/CAST spans)
    "int", "integer", "smallint", "bigint", "tinyint", "decimal", "numeric",
    "float", "real", "double", "precision", "char", "character", "varchar",
    "nvarchar", "text", "date", "time", "timestamp", "datetime", "interval",
    "boolean", "bool", "blob", "clob", "binary", "varbinary", "serial", "uuid",
    "json", "jsonb", "array",
})
_TS_NAME_FIELD_PRIORITY = (
    "name", "identifier", "declarator", "target", "module", "path", "label",
    "field", "table", "view", "procedure", "function", "selector", "key", "attribute",
    "pattern", "object", "callee", "member", "alias",
)
_TS_MARKUP_ATTRS = ("id", "name", "role", "href", "src", "action", "for", "data", "path", "target")
_TS_SQL_DEF_KEYWORDS = ("create", "table", "view", "function", "procedure", "trigger", "schema")
_TS_SQL_REF_KEYWORDS = ("from", "join", "into", "update", "delete", "insert", "call", "with", "use")
_TS_CONFIG_NAME_HINTS = (
    "name", "id", "module", "class", "function", "task", "job", "step", "route", "path",
    "template", "script", "command", "resource", "provider", "output", "variable",
    "selector", "include", "import", "query", "table", "view", "procedure", "target",
    "workflow", "action", "handler", "entry", "rule",
)


def _repo_rel(path: str | Path) -> str:
    return str(path).replace("\\", "/")


def _is_minified_file(rel_path: str) -> bool:
    """Return True for bundled/minified artifacts that have no semantic graph value."""
    name = Path(rel_path).name
    return bool(_MINIFIED_FILE_RE.search(name))


def _extract_code_contexts(source_text: str) -> str:
    """Return concatenated text from fenced code blocks and inline backtick spans."""
    parts: list[str] = []
    fenced_ranges: list[tuple[int, int]] = []
    for m in _FENCED_CODE_RE.finditer(source_text):
        parts.append(m.group(1))
        fenced_ranges.append((m.start(), m.end()))
    for m in _INLINE_CODE_RE.finditer(source_text):
        if any(fs <= m.start() < fe for fs, fe in fenced_ranges):
            continue
        parts.append(m.group(1))
    return " ".join(parts)


def _extract_inline_code_contexts(source_text: str) -> str:
    """Inline backtick spans only — excludes fenced blocks (e.g. JSON config examples)."""
    parts: list[str] = []
    fenced_ranges: list[tuple[int, int]] = []
    for m in _FENCED_CODE_RE.finditer(source_text):
        fenced_ranges.append((m.start(), m.end()))
    for m in _INLINE_CODE_RE.finditer(source_text):
        if any(fs <= m.start() < fe for fs, fe in fenced_ranges):
            continue
        parts.append(m.group(1))
    return " ".join(parts)


def _resolve_doc_path_ref(href: str, rel_path: str, current_paths: set[str]) -> str | None:
    href = href.strip().split("#")[0].strip()
    if not href or href.startswith(("http://", "https://", "mailto:", "ftp://")):
        return None
    if href.startswith("/"):
        raw = href.lstrip("/")
    elif href.startswith(("./", "../")) or (href.startswith(".") and "/" in href):
        raw = href
    else:
        doc_dir = rel_path.rsplit("/", 1)[0] if "/" in rel_path else ""
        raw = (doc_dir + "/" + href) if doc_dir else href
    parts: list[str] = []
    for part in raw.split("/"):
        if part == "..":
            if parts:
                parts.pop()
        elif part and part != ".":
            parts.append(part)
    resolved = "/".join(parts)
    if not resolved or resolved == rel_path or resolved not in current_paths:
        return None
    return resolved


def _extract_doc_backtick_paths(source_text: str, rel_path: str, current_paths: set[str]) -> list[str]:
    """Repo-relative paths written in backticks (Cross-Links, path callouts)."""
    targets: list[str] = []
    seen: set[str] = set()
    for m in _INLINE_CODE_RE.finditer(source_text):
        raw = m.group(1).strip()
        if not raw or " " in raw:
            continue
        looks_like_path = (
            "/" in raw
            or raw.startswith(".")
            or any(raw.endswith(suffix) for suffix in _DOC_PATH_SUFFIXES)
        )
        if not looks_like_path:
            continue
        resolved = _resolve_doc_path_ref(raw, rel_path, current_paths)
        if resolved and resolved not in seen:
            seen.add(resolved)
            targets.append(resolved)
    return targets


def _is_module_node_id(node_id: str) -> bool:
    return bool(node_id) and "::" not in node_id


def _is_json_config_node_id(node_id: str) -> bool:
    if "::" not in node_id:
        return False
    # Wave 1p7dh: `.properties`/`.yml`/`.yaml` config-key nodes join `.json`/`.jsonc`.
    return node_id.split("::", 1)[0].endswith((".json", ".jsonc", ".properties", ".yml", ".yaml"))


# Wave 1p7dh: a config FILE (vs an arbitrary data/fixture .json) for the
# config-key->reader binding. Restricting the match target to config files —
# plus a key-distinctiveness gate (below) — is what keeps `reads_config` faithful:
# without it, ubiquitous dict literals (`["source"]`, `.get("kind")`) coincidentally
# match keys in data JSON (retrieval_eval.json, source-map.json) and bind the wrong
# target. Declared default set + a `config`/`profile` basename pattern; a fully
# project-tunable catalog (like code_navigation_hints) is the follow-on.
_CONFIG_FILE_DECLARED = frozenset({"workflow-config.json", "repo-profile.json"})


def _is_config_file_path(file_part: str) -> bool:
    base = file_part.rsplit("/", 1)[-1].lower()
    if base in _CONFIG_FILE_DECLARED:
        return True
    # Wave 1p7dh: accept `.properties`/`.yml`/`.yaml` (Java/Spring file config) in
    # addition to `.json`/`.jsonc`. Beyond the `config`/`profile` basename pattern,
    # also treat Spring convention files (basename `application*` / `bootstrap*`,
    # e.g. `application.yml`, `application-prod.properties`, `bootstrap.yml`) as
    # config so their keys bind. Same triple-gating bounds faithfulness downstream.
    if not base.endswith((".json", ".jsonc", ".properties", ".yml", ".yaml")):
        return False
    if "config" in base or "profile" in base:
        return True
    return base.startswith("application") or base.startswith("bootstrap")


def _config_literal_is_distinctive(literal: str) -> bool:
    # A bare (single-segment) config key must be specific enough to bind: a
    # dotted path is inherently specific; a single segment must be >=10 chars or
    # contain "_" (mirrors `_doc_term_allows_json_target`). Drops generic keys
    # like "source"/"kind"/"id" that collide across surfaces.
    if "." in literal:
        return True
    return len(literal) >= 10 or "_" in literal


def _parse_properties_keys(text: str) -> list[str]:
    """Wave 1p7dh: stdlib line parse of a Java `.properties` file → its keys.

    Recognizes `key=value` and `key:value`; skips blank lines and comments
    (`#`/`!` line prefixes). The key is the trimmed LHS; dotted keys (`a.b.c`)
    are kept verbatim (already in the dotted node-id form). Line-continuation and
    full unicode-escape handling are intentionally out of scope — the keys are
    binding targets, not values."""
    keys: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line[0] in "#!":
            continue
        # First unescaped '=' or ':' (or whitespace) separates key from value.
        idx = len(line)
        for sep in ("=", ":"):
            pos = line.find(sep)
            if pos != -1:
                idx = min(idx, pos)
        key = line[:idx].strip()
        if key:
            keys.append(key)
    return keys


def _parse_yaml_keys(text: str) -> list[str]:
    """Wave 1p7dh: `.yml`/`.yaml` → dotted config keys via the declared
    `tree-sitter-yaml` grammar — the indexer's native parser (NO pyyaml, which is
    not a declared dependency). Walks `block_mapping_pair` nodes, threading the
    nesting prefix so `{a:{b:1}}` yields `a` and `a.b`; emits intermediate + leaf
    keys. Returns [] when the grammar is unavailable or the file does not parse
    (the keys are binding targets only)."""
    tree = _ts_parse("yaml", text)
    if tree is None:
        return []
    source_bytes = text.encode("utf-8", errors="replace")
    keys: list[str] = []

    def _walk(node, prefix: str) -> None:
        for child in getattr(node, "named_children", []):
            if str(getattr(child, "type", "") or "") == "block_mapping_pair":
                kn = child.child_by_field_name("key")
                k = _ts_node_text(kn, source_bytes).strip().strip("'\"") if kn is not None else ""
                if k:
                    dotted = f"{prefix}.{k}" if prefix else k
                    keys.append(dotted)
                    vn = child.child_by_field_name("value")
                    _walk(vn if vn is not None else child, dotted)
                else:
                    _walk(child, prefix)
            else:
                _walk(child, prefix)

    _walk(tree.root_node, "")
    return keys


def _doc_term_allows_json_target(term: str, target_id: str) -> bool:
    if not _is_json_config_node_id(target_id):
        return True
    key = target_id.split("::", 1)[1]
    lower_term = term.lower()
    if "." in lower_term:
        return True
    key_tail = key.rsplit(".", 1)[-1].lower()
    if lower_term != key_tail:
        return False
    return len(lower_term) >= 10 or "_" in lower_term


def _filter_doc_code_targets(term: str, targets: set[str]) -> list[str]:
    if term in _DOC_MATCH_STOP_TERMS:
        return []
    path_like = (
        "/" in term
        or any(term.endswith(suffix) for suffix in _DOC_PATH_SUFFIXES)
    )
    kept: list[str] = []
    for target in sorted(targets):
        if not _doc_term_allows_json_target(term, target):
            continue
        if path_like and not _is_module_node_id(target):
            continue
        kept.append(target)
    return kept


def _doc_code_reference_confidence(term: str, target_id: str, *, match_count: int) -> str:
    if _is_module_node_id(target_id) and (
        "/" in term or any(term.endswith(suffix) for suffix in _DOC_PATH_SUFFIXES)
    ):
        return "EXTRACTED"
    if match_count == 1 and (len(term) >= 12 or "_" in term):
        return "EXTRACTED"
    return "AMBIGUOUS"


_DOC_MATCH_TERM_STRIP = ".,;:!?)]}\"'"


def _extract_doc_match_terms(code_ctx: str) -> set[str]:
    """Whole-token terms from markdown code spans for symbol lookup.

    Keeps hyphenated names and path segments intact — never splits
    ``project-context-memory`` into ``context``.
    """
    terms: set[str] = set()
    if not code_ctx:
        return terms
    for raw in re.split(r"\s+", code_ctx):
        chunk = raw.strip(_DOC_MATCH_TERM_STRIP)
        if not chunk:
            continue
        terms.add(chunk.lower())
        if "/" in chunk:
            base = chunk.rsplit("/", 1)[-1].strip(_DOC_MATCH_TERM_STRIP)
            if base:
                terms.add(base.lower())
                if "." in base:
                    stem = base.rsplit(".", 1)[0]
                    if stem:
                        terms.add(stem.lower())
        elif "." in chunk and not chunk.startswith("."):
            parts = chunk.split(".")
            for end in range(1, len(parts)):
                prefix = ".".join(parts[:end])
                if prefix:
                    terms.add(prefix.lower())
    return terms


def _extract_doc_links(source_text: str, rel_path: str, current_paths: set[str]) -> list[str]:
    """Return repo-relative paths of known files explicitly linked from this document."""
    targets: list[str] = []
    seen: set[str] = set()
    for m in _MD_LINK_RE.finditer(source_text):
        resolved = _resolve_doc_path_ref(m.group(2).strip(), rel_path, current_paths)
        if resolved and resolved not in seen:
            seen.add(resolved)
            targets.append(resolved)
    return targets


def _gitignored_paths(root: Path) -> frozenset[str]:
    try:
        result = subprocess_util.isolated_run(
            ["git", "ls-files", "--others", "--ignored", "--exclude-standard"],
            capture_output=True, text=True, cwd=str(root), timeout=30,
        )
        if result.returncode == 0:
            return frozenset(
                line.replace("\\", "/") for line in result.stdout.splitlines() if line.strip()
            )
    except Exception:
        pass
    return frozenset()


# ---------------------------------------------------------------------------
# Generated-code classifier (wave 130rj — field feedback §6)
# ---------------------------------------------------------------------------
#
# Tags graph nodes from machine-generated source files with `generated: true`.
# Downstream consumers (wave_graph_report `exclude_generated`, `community_type`,
# `betweenness_dominated_by_generated`, and the 130su collapse mode) read this
# tag to filter or aggregate generated nodes out of architectural views without
# discarding the underlying graph edges.
#
# Three signal sources, in priority order: in-file header marker (matched in
# first 200 bytes), path heuristic (directory segments or filename suffix),
# `.gitattributes` `linguist-generated=true` annotation.
#
# Coverage in this change: Java/JVM + C#. Multi-language follow-up (Go, TS/JS,
# Rust, Swift, Kotlin, Python) is deferred per the change doc — operator
# validation of Java+C# coverage informs the follow-up's architectural shape.

# Header substrings matched in the first 200 bytes (case-sensitive).
_GENERATED_HEADER_SIGNATURES = (
    # Java / JVM ecosystem
    "Generated By:JJTree",
    "Generated By:JavaCC",
    "DO NOT EDIT",
    "Code generated by",
    "@javax.annotation.Generated",
    "@jakarta.annotation.Generated",
    "@javax.annotation.processing.Generated",
    # C# / .NET ecosystem
    "<auto-generated>",
    "<auto-generated/>",
    "[GeneratedCode(",
    "[GeneratedCodeAttribute(",
)

# Regex patterns for headers that need pattern matching (e.g. ANTLR's version-flexible header).
_GENERATED_HEADER_PATTERNS = (
    re.compile(rb"Generated from .* by ANTLR"),
    # bare `@Generated(` annotation form (avoid catching `@Generated...` in javadoc prose by
    # requiring an opening paren or a newline immediately after).
    re.compile(rb"^[\s\*]*@Generated\b\s*[(\n]", re.MULTILINE),
)

# Directory segment matches (any segment in the path counts).
_GENERATED_DIR_SEGMENTS = (
    "generated-sources",
    "build/generated",
    "generated",
    "Service References",
    "Connected Services",
    # Wave 1p2q3 (1p2q9 Workstream C): JS/TS conventional generated-output directories.
    "__generated__",
    ".generated",
)

# Filename suffix matches (case-insensitive).
_GENERATED_FILENAME_SUFFIXES = (
    ".designer.cs",
    ".g.cs",
    ".g.i.cs",
    # Wave 1p2q3 (1p2q9 Workstream C): JS/TS naming conventions for codegen output.
    # Covers TanStack Router (routeTree.gen.ts), GraphQL codegen (*.graphql.ts when
    # paired with .gen suffix), Apollo, OpenAPI generators, Prisma client output.
    # Operators with hand-written files matching the suffix can opt out via the
    # standard exclude_generated=false filter.
    ".gen.ts",
    ".gen.tsx",
    ".gen.js",
    ".gen.jsx",
    ".generated.ts",
    ".generated.tsx",
    ".generated.js",
    ".generated.jsx",
)


def _load_gitattributes_generated_paths(root: Path) -> frozenset[str]:
    """Parse .gitattributes for `linguist-generated=true` annotations once per session.

    Returns a frozenset of relative-path patterns (forward-slash). Patterns may include
    glob characters (`*`, `?`); the consumer checks via fnmatch-style match.
    """
    paths: list[str] = []
    gitattrs = root / ".gitattributes"
    if not gitattrs.is_file():
        return frozenset()
    try:
        for raw in gitattrs.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            # Expected shape: <pattern> linguist-generated=true [...other attrs]
            if "linguist-generated=true" not in line and "linguist-generated" not in line:
                continue
            # First whitespace-separated token is the pattern.
            parts = line.split()
            if not parts:
                continue
            pattern = parts[0].replace("\\", "/")
            if pattern:
                paths.append(pattern)
    except OSError:
        return frozenset()
    return frozenset(paths)


def _path_matches_gitattributes(rel_path: str, patterns: frozenset[str]) -> bool:
    if not patterns:
        return False
    import fnmatch
    rel = rel_path.replace("\\", "/")
    for p in patterns:
        # Anchored patterns (starting with /) match from repo root only.
        if p.startswith("/"):
            if fnmatch.fnmatchcase(rel, p[1:]):
                return True
            continue
        # Unanchored: match against the full path AND any path suffix (matching git's behavior).
        if fnmatch.fnmatchcase(rel, p):
            return True
        # Also try matching just the basename for simple patterns like *.designer.cs.
        if "/" not in p and fnmatch.fnmatchcase(Path(rel).name, p):
            return True
    return False


def _classify_generated(rel_path: str, source_bytes: bytes | None, gitattrs_patterns: frozenset[str]) -> bool:
    """Return True when the file is machine-generated (wave 130rj).

    Three signal sources (any-of):
    1. In-file header marker — substring or regex match within first 200 bytes.
    2. Path heuristic — directory segment or filename suffix.
    3. `.gitattributes` `linguist-generated=true` pattern match.
    """
    rel = rel_path.replace("\\", "/")
    # Filename suffix (case-insensitive)
    lower_name = Path(rel).name.lower()
    for suffix in _GENERATED_FILENAME_SUFFIXES:
        if lower_name.endswith(suffix):
            return True
    # Directory segment (any segment)
    parts = rel.split("/")
    for seg in _GENERATED_DIR_SEGMENTS:
        # Multi-segment patterns like "build/generated" need a sliding-window check.
        seg_parts = seg.split("/")
        if len(seg_parts) == 1:
            if seg in parts:
                return True
        else:
            for i in range(len(parts) - len(seg_parts) + 1):
                if parts[i:i + len(seg_parts)] == seg_parts:
                    return True
    # .gitattributes
    if _path_matches_gitattributes(rel, gitattrs_patterns):
        return True
    # In-file header markers (limit to first 200 bytes to avoid false positives on
    # docstrings, comments, or in-file string literals far below the file head).
    if source_bytes is not None:
        head = source_bytes[:200]
        for sig in _GENERATED_HEADER_SIGNATURES:
            if sig.encode("utf-8", errors="replace") in head:
                return True
        for pattern in _GENERATED_HEADER_PATTERNS:
            if pattern.search(head):
                return True
    return False


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _file_stem(path: str) -> str:
    return Path(path).stem


def _kind_for_path(rel_path: str) -> str:
    rel = rel_path.replace("\\", "/")
    if rel.startswith(".wavefoundry/framework/seeds/"):
        return "seed"
    name = Path(rel).name
    suffix = Path(rel).suffix.lower()
    if name in _CODE_FILENAMES:
        return "code"
    if suffix in _CODE_EXTENSIONS:
        return "code"
    if rel.startswith("docs/") or rel.startswith(".wavefoundry/framework/seeds/"):
        return "doc"
    if suffix in _DOC_EXTENSIONS or rel.endswith(".prompt.md"):
        return "doc"
    return "doc"


# Wave 1p4ls: constant graph nodes + the `reads` edge.
GRAPH_CONST_KIND = "constant"
GRAPH_READS_RELATION = "reads"

# Wave 1p9qi (1p9qd): SQL clause-aware statement extraction.
# `writes` is the WRITE-direction table-reference relation: a statement (or the
# object owning it) INSERTs/UPDATEs/DELETEs/MERGEs-into/ALTERs/DROPs/TRUNCATEs
# the target table. Chosen as a distinct RELATION (not a `mode` property on
# `reads`) so relation-filtering consumers (impact, path, graph-signal
# grouping, report queries) can distinguish read from write without
# per-edge property inspection — the same reasoning that made
# `extends`/`implements` relations rather than properties (wave 1p9qh).
# Read-direction table references (FROM/JOIN sources, MERGE USING, view
# lineage, FK REFERENCES) reuse GRAPH_READS_RELATION; their SQL origin is
# recognized by source-file suffix (see `_sql_table_reference_edge`) because the
# 1p4ls constant-read resolution (unique-constant-or-DROP) must not apply to
# table references — a table reference resolves through the same
# unique-candidate machinery as calls and STAYS EXTERNAL when unresolved
# (an `external::audit_log` reference is real evidence, not a tombstone).
GRAPH_WRITES_RELATION = "writes"

# Wave 1p9qi (1p9qg): ORM entity→table mapping edges. An entity class with a
# DECLARED table name (JPA `@Table(name = "…")`/`@Entity(name = "…")`, EF
# `[Table("…")]`/`ToTable("…")`) maps onto the SQL table it rides. Chosen as
# a distinct RELATION (not a property on `reads`, and not a reads+writes
# pair) for the same consumer-sweep reasons that made `writes` a relation:
# every downstream consumer (impact, path, graph-signal grouping, report)
# filters by relation, and a mapping is neither a read nor a write — it is a
# declaration fact with no query text behind it, so emitting `reads`/`writes`
# would overstate the evidence. Minted ONLY by the finalize bind pass at
# LITERAL_DERIVED confidence (never in per-file fragments); declared names
# only — convention-derived names (snake_cased class names, EF pluralization)
# are refused and counted (standing wave-1p9qi decision).
GRAPH_MAPS_TO_RELATION = "maps_to"

# Wave 1p7dh: string-literal binding surfaces.
# `reads_config` is an EDGE binding a code site to the config-key node
# (`file.json::key`) it reads by literal name, carrying the honest
# LITERAL_DERIVED confidence — self-bounding: emitted ONLY when the captured
# literal matches an existing config-key node, so no literal becomes a node and
# the index does not bloat on an open string scan.
# AOP advice registration is captured as a NODE PROPERTY (`instruments`), NOT an
# edge: the Phase-0 recon on the OTel/ByteBuddy consumer (`aceiss/javaagent`)
# found instrumentation targets are ~100% THIRD-PARTY types by design (0%
# project), so an advice->project-type edge would bind nothing. Instead the
# OTel `TypeInstrumentation.typeMatcher()` matcher strings are attached as
# descriptive metadata on the enclosing class node — answering "what does this
# instrument" without inventing nodes or risking false binding edges.
GRAPH_CONFIG_READS_RELATION = "reads_config"
GRAPH_LITERAL_DERIVED_CONFIDENCE = "LITERAL_DERIVED"

# ByteBuddy / ElementMatchers TYPE matchers whose string-literal arg(s), when
# used inside an OTel `typeMatcher()`, name an instrumentation target type. The
# `*OneOf` forms take MULTIPLE type strings (so capture ALL args, not just the
# first). The structural wrappers (`implementsInterface`/`hasSuperType`/
# `isSubTypeOf`/…) carry no string directly — their inner `named`/`namedOneOf`
# call is itself a buffered invocation inside `typeMatcher()`, so its strings are
# captured without explicit unwrapping (verified by the structural-matcher tests).
_AOP_TYPE_MATCHERS = frozenset({
    "named", "namedIgnoreCase", "namedOneOf", "namedOneOfIgnoreCase",
    "nameStartsWith", "nameStartsWithIgnoreCase",
    "nameEndsWith", "nameEndsWithIgnoreCase", "nameContains", "nameContainsIgnoreCase",
    "nameMatches", "hasSuperType", "isSubTypeOf", "implementsInterface",
    "extendsClass", "hasSuperClass",
})

# Wave 1p7dh: declared config-getter attribute names whose string-literal first
# argument is a candidate config key. Bounded — capture is cheap and transient;
# only a literal matching an existing config-key node emits an edge. Subscript
# reads (`cfg["key"]`) are captured separately. (A project-tunable catalog,
# like code_navigation_hints, is a follow-on; this declared default covers the
# dominant getter shape across languages.)
_CONFIG_GETTER_ATTRS = frozenset({"get", "getString", "getInteger", "getBoolean", "getValue"})


@functools.lru_cache(maxsize=1)
def _chunker_module():
    """Lazily import chunker.py for its per-language constant-detection predicates so the graph
    lane (1p4ls) and the chunk lane (1p4mf) share ONE detector (Req-7 — no divergent detection).
    Robust to both the standalone-subprocess and the _load_script(MCP) load contexts: ensures the
    scripts directory is importable before the import. The predicates are pure (stateless), so a
    second module instance under the plain `chunker` key is harmless."""
    _dir = str(Path(__file__).resolve().parent)
    if _dir not in sys.path:
        sys.path.insert(0, _dir)
    import chunker  # noqa: E402 — lazy by design (heavy tree-sitter deps load on first use)
    return chunker


def _py_const_literal_value(value_node: "ast.AST | None") -> str | None:
    """Short source-faithful value for a Python constant RHS when it is a SIMPLE literal
    (str/num/bool/None, or a 1-level list/tuple/set/dict of literals). None for anything computed
    (calls, names, comprehensions, f-strings) — the node still exists, it just carries no value."""
    if value_node is None:
        return None

    def _lit(n: "ast.AST") -> "str | None":
        if isinstance(n, ast.Constant):
            return repr(n.value)
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.USub, ast.UAdd)) and isinstance(n.operand, ast.Constant):
            return ("-" if isinstance(n.op, ast.USub) else "") + repr(n.operand.value)
        return None

    direct = _lit(value_node)
    if direct is not None:
        return direct[:200]
    if isinstance(value_node, (ast.List, ast.Tuple, ast.Set)):
        parts = [_lit(e) for e in value_node.elts]
        if parts and all(p is not None for p in parts):
            brackets = {"List": ("[", "]"), "Tuple": ("(", ")"), "Set": ("{", "}")}[type(value_node).__name__]
            return (brackets[0] + ", ".join(parts) + brackets[1])[:200]
    if isinstance(value_node, ast.Dict):
        keys = [_lit(k) for k in value_node.keys]
        vals = [_lit(v) for v in value_node.values]
        if keys and all(k is not None for k in keys) and all(v is not None for v in vals):
            return ("{" + ", ".join(f"{k}: {v}" for k, v in zip(keys, vals)) + "}")[:200]
    return None


def _py_local_names(owner_node: "ast.AST") -> set[str]:
    """Names BOUND locally inside a Python function — parameters + every Store/Del-context Name in
    its body (assignments, for-targets, with-as, nested def/class names) — NOT descending into
    nested scopes. Wave 1p4ls reads-edge faithfulness: a read of such a name is the LOCAL binding,
    not a module/class constant of the same name, so it must NOT emit a reads edge to the constant."""
    names: set[str] = set()
    a = getattr(owner_node, "args", None)
    if a is not None:
        for arg in [*getattr(a, "posonlyargs", []), *a.args, *a.kwonlyargs]:
            names.add(arg.arg)
        if a.vararg:
            names.add(a.vararg.arg)
        if a.kwarg:
            names.add(a.kwarg.arg)
    stack: list[Any] = list(getattr(owner_node, "body", []))
    while stack:
        n = stack.pop()
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(n.name)  # the nested def/class name binds locally; don't descend
            continue
        if isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del)):
            names.add(n.id)
        for child in ast.iter_child_nodes(n):
            stack.append(child)
    return names


def _node(
    node_id: str,
    label: str,
    kind: str,
    source_file: str,
    source_location: str,
    *,
    layer: str,
) -> dict[str, Any]:
    return {
        "id": node_id,
        "label": label,
        "kind": kind,
        "source_file": source_file,
        "source_location": source_location,
        "layer": layer,
    }


def _edge(
    source: str,
    target: str,
    relation: str,
    *,
    confidence: str,
    evidence: str | None = None,
    self_edge_kind: str | None = None,
) -> dict[str, Any]:
    payload = {
        "source": source,
        "target": target,
        "relation": relation,
        "confidence": confidence,
    }
    if evidence:
        payload["evidence"] = evidence
    # Wave 1p2q3 (1p2td): tag self-edges on overloaded methods so consumers can
    # distinguish recursion from overload-forwarding.
    if self_edge_kind:
        payload["self_edge_kind"] = self_edge_kind
    return payload


def _read_json(path: Path, default: Any) -> Any:
    """Read a graph artifact — gzip-compressed compact JSON (current format) or
    legacy plain JSON, sniffed via the gzip magic bytes (wave 1p9q3 / 1p9py).

    Any failure — missing file, truncated/corrupted gzip stream, invalid JSON —
    returns ``default``, preserving the pre-existing corrupted-artifact contract
    (the version-staleness path then triggers re-extraction).
    """
    try:
        raw = path.read_bytes()
        if raw[:2] == _GZIP_MAGIC:
            raw = gzip.decompress(raw)
        return json.loads(raw.decode("utf-8"))
    except Exception:
        return default


# Public alias for consumers outside this module (graph_query version checks,
# server_impl summaries, tests): every reader of a graph artifact path must go
# through a sniffing reader — never `json.loads(path.read_text())` directly.
read_json_artifact = _read_json


# ---------------------------------------------------------------------------
# Per-file graph state store (wave 1p9q3 / 1p9q2)
# ---------------------------------------------------------------------------


def _encode_state_record(payload: Any) -> bytes:
    """Encode one state record as gzip-level-6 compact JSON bytes.

    Same byte format `_write_json` produces for artifacts (wave 1p9py):
    compact separators, sorted keys, ``mtime=0`` for byte-stable output.
    Used for both per-file records and the merge-state blob in the store.
    """
    data = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return gzip.compress(data, compresslevel=GRAPH_GZIP_LEVEL, mtime=0)


def _decode_state_record(raw: bytes, default: Any = None) -> Any:
    try:
        if raw[:2] == _GZIP_MAGIC:
            raw = gzip.decompress(raw)
        return json.loads(raw.decode("utf-8"))
    except Exception:
        return default


class GraphStateStore:
    """SQLite-backed per-file graph state store (wave 1p9q3 / 1p9q2).

    Replaces the monolithic ``project-graph-state.json`` document with per-file
    write granularity: a one-file build reads/writes O(changed) records instead
    of parsing and rewriting the whole state per build. Backend selected by the
    AC-7 spike (stdlib ``sqlite3`` vs per-file gzip blobs + manifest): SQLite
    won every per-build criterion on a 5k-file corpus — dominant 1-file update
    cycle 0.71 ms vs 22.65 ms, ~4 KB written vs ~337 KB — because the blob
    manifest is itself an O(repo-count) document. Per-file gzip blobs remain
    the documented fallback behind this abstraction (see the change doc's
    Decision Log for the full rationale and overturn conditions).

    Layout:
      - ``meta``  — key/value store metadata: store/schema/builder/walker/
        chunker versions + layer (whole-store invalidation), and the payload
        binding (``payload_fingerprint``/``payload_size``/``payload_mtime_ns``/
        ``payload_stat_state``) used for crash-consistency detection.
      - ``files`` — one row per source file: ``path`` (PK), ``source_hash``,
        and ``record`` = gzip compact-JSON ``{"source_hash":…, "artifact":…}``
        (the same record shape the monolithic state carried per file).
      - ``blobs`` — named auxiliary records; carries the ``merge_state``
        sidecar (persistent merged maps + per-file resolved fragments).

    Durability: ``journal_mode=WAL`` + ``synchronous=NORMAL`` — atomic commit
    and rollback on an app crash; an OS-level crash can at worst lose the last
    commit (a lost build is re-buildable; never a torn store). ``busy_timeout``
    covers concurrent hook-spawned builds. Version mismatch resets the whole
    store (rows + blobs), preserving the historical ``_load_state``
    whole-store invalidation semantics.

    Error posture (intentionally asymmetric): read-side probes used for
    staleness/decision-making (``meta_all``, ``paths_with_hashes``,
    ``get_blob``) swallow ``sqlite3.Error`` and degrade to empty — the caller
    then takes the full-re-extract path. Mutating/build-critical operations
    (``get_record``, ``iter_records``, ``apply_build``, ``set_meta``)
    propagate — a mid-build store failure crashes the build loudly rather
    than committing partial state. Both directions end at "loud crash or
    full rebuild", never a silently wrong graph; corruption at open time is
    handled by ``__init__``'s reset-and-recreate.
    """

    _VERSION_KEYS = (
        "store_schema_version",
        "schema_version",
        "builder_version",
        "walker_version",
        "chunker_version",
        "layer",
    )

    def __init__(
        self,
        path: Path,
        *,
        layer: str,
        walker_version: str,
        chunker_version: str,
    ) -> None:
        self.path = Path(path)
        self.layer = layer
        self.walker_version = walker_version
        self.chunker_version = chunker_version
        # AC-1 instrumentation: per-build state-I/O counters (record granularity).
        self.record_reads = 0
        self.record_writes = 0
        self.record_deletes = 0
        # Blob (merge_state sidecar) I/O is tracked separately — it is
        # O(graph) per changed build, not O(changed), and hiding it in the
        # row counters would under-report exactly the dominant byte term
        # (delivery-review finding).
        self.blob_reads = 0
        self.blob_writes = 0
        self.blob_bytes_written = 0
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._conn = self._open()
        except sqlite3.Error:
            # Corrupted/unreadable database file: loudly delete and recreate.
            # The empty store then forces a full re-extract (never a silently
            # wrong graph).
            print(
                f"build_index: graph state store unreadable at {self.path} — "
                "resetting store (a full re-extract follows)",
                file=sys.stderr,
                flush=True,
            )
            self._delete_store_files()
            self._conn = self._open()

    def _open(self) -> "sqlite3.Connection":
        conn = sqlite3.connect(str(self.path), timeout=10.0)
        # WAL can be silently refused (e.g. some network filesystems fall
        # back to a rollback journal, where multi-process locking is
        # unreliable) — check the pragma's RESULT and warn loudly so a field
        # report of store contention has a diagnostic to point at.
        journal_mode = str(
            (conn.execute("PRAGMA journal_mode=WAL").fetchone() or [""])[0]
        )
        if journal_mode.lower() != "wal":
            print(
                f"[graph-state-store] WARNING: journal_mode=WAL refused "
                f"(got {journal_mode!r}); store at {self.path} may be on a "
                f"filesystem with unreliable locking",
                file=sys.stderr,
            )
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=10000")
        with conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS files ("
                "path TEXT PRIMARY KEY, source_hash TEXT NOT NULL, record BLOB NOT NULL)"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS blobs (key TEXT PRIMARY KEY, value BLOB NOT NULL)"
            )
        return conn

    def _delete_store_files(self) -> None:
        for suffix in ("", "-wal", "-shm"):
            try:
                os.unlink(f"{self.path}{suffix}")
            except OSError:
                pass

    def _expected_versions(self) -> dict[str, str]:
        return {
            "store_schema_version": GRAPH_STORE_SCHEMA_VERSION,
            "schema_version": GRAPH_SCHEMA_VERSION,
            "builder_version": GRAPH_BUILDER_VERSION,
            "walker_version": self.walker_version,
            "chunker_version": self.chunker_version,
            "layer": self.layer,
        }

    def meta_all(self) -> dict[str, str]:
        try:
            rows = self._conn.execute("SELECT key, value FROM meta").fetchall()
        except sqlite3.Error:
            return {}
        return {str(k): str(v) for k, v in rows}

    def versions_current(self) -> bool:
        meta = self.meta_all()
        expected = self._expected_versions()
        return all(meta.get(key) == expected[key] for key in self._VERSION_KEYS)

    def ensure_current(self) -> bool:
        """Reset the whole store when any version key mismatches.

        Preserves the historical `_load_state` semantics: a builder/walker/
        chunker/schema mismatch invalidates everything and forces a full
        re-extraction (the caller sees an empty ``files`` table). Returns
        True when the store was already current.
        """
        if self.versions_current():
            return True
        self.reset()
        return False

    def reset(self) -> None:
        expected = self._expected_versions()
        with self._conn:
            self._conn.execute("DELETE FROM files")
            self._conn.execute("DELETE FROM blobs")
            self._conn.execute("DELETE FROM meta")
            self._conn.executemany(
                "INSERT INTO meta (key, value) VALUES (?, ?)",
                sorted(expected.items()),
            )

    def paths_with_hashes(self) -> dict[str, str]:
        """Cheap manifest read: every known path with its source hash.

        Reads two small columns only — never decodes record blobs — so the
        per-build removed-path detection stays O(paths), not O(bytes).
        """
        try:
            rows = self._conn.execute("SELECT path, source_hash FROM files").fetchall()
        except sqlite3.Error:
            return {}
        return {str(p): str(h) for p, h in rows}

    def get_record(self, rel_path: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT record FROM files WHERE path = ?", (rel_path,)
        ).fetchone()
        if row is None:
            return None
        self.record_reads += 1
        record = _decode_state_record(row[0])
        return record if isinstance(record, dict) else None

    def iter_records(self):
        """Yield ``(path, record_dict)`` for every stored file record.

        Full-scan decode — the full-(re)merge path only; incremental builds
        must not call this (AC-1: state I/O touches only changed files).
        """
        cursor = self._conn.execute("SELECT path, record FROM files ORDER BY path")
        for path, raw in cursor:
            record = _decode_state_record(raw)
            if isinstance(record, dict):
                self.record_reads += 1
                yield str(path), record

    def get_blob(self, key: str) -> Any:
        try:
            row = self._conn.execute(
                "SELECT value FROM blobs WHERE key = ?", (key,)
            ).fetchone()
        except sqlite3.Error:
            return None
        if row is None:
            return None
        self.blob_reads += 1
        return _decode_state_record(row[0])

    def apply_build(
        self,
        *,
        puts: dict[str, dict[str, Any]],
        deletes: list[str],
        blobs: dict[str, Any],
        meta: dict[str, str],
    ) -> None:
        """Apply one build's state mutations in a single transaction.

        Crash consistency (AC-5): everything commits atomically or not at all;
        an interrupted build rolls back to the previous consistent state and
        the payload-binding meta keys detect the payload/store windows (see
        finalize's persist step for the crash-window analysis).
        """
        with self._conn:
            if deletes:
                self._conn.executemany(
                    "DELETE FROM files WHERE path = ?", [(p,) for p in deletes]
                )
            for rel, record in puts.items():
                self._conn.execute(
                    "INSERT INTO files (path, source_hash, record) VALUES (?, ?, ?) "
                    "ON CONFLICT(path) DO UPDATE SET source_hash=excluded.source_hash, "
                    "record=excluded.record",
                    (rel, str(record.get("source_hash") or ""), _encode_state_record(record)),
                )
            for key, value in blobs.items():
                encoded = _encode_state_record(value)
                self._conn.execute(
                    "INSERT INTO blobs (key, value) VALUES (?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    (key, encoded),
                )
                self.blob_writes += 1
                self.blob_bytes_written += len(encoded)
            for key, value in meta.items():
                self._conn.execute(
                    "INSERT INTO meta (key, value) VALUES (?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    (key, value),
                )
        self.record_writes += len(puts)
        self.record_deletes += len(deletes)

    def set_meta(self, updates: dict[str, str]) -> None:
        with self._conn:
            for key, value in updates.items():
                self._conn.execute(
                    "INSERT INTO meta (key, value) VALUES (?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    (key, value),
                )

    def close(self) -> None:
        try:
            self._conn.close()
        except sqlite3.Error:
            pass

    def __del__(self):  # pragma: no cover - GC timing dependent
        try:
            self._conn.close()
        except Exception:
            pass


def read_state_builder_version(index_dir: Path, layer: str = "project") -> str:
    """Cheap builder-version probe for the version-staleness check.

    Wave 1p9q3 (1p9q2): the graph state lives in the SQLite store; read its
    ``meta`` table via a read-only URI open (no file creation, ~sub-ms) and
    fall back to the legacy monolithic JSON state for pre-upgrade repos.
    Returns ``""`` when the version cannot be determined — callers treat that
    exactly like the historical missing/corrupted-state contract.
    """
    if layer not in GRAPH_STORE_FILENAMES:
        return ""
    store_path = index_dir / GRAPH_DIRNAME / GRAPH_STORE_FILENAMES[layer]
    if store_path.exists():
        try:
            conn = sqlite3.connect(
                f"file:{store_path.as_posix()}?mode=ro", uri=True, timeout=2.0
            )
            try:
                row = conn.execute(
                    "SELECT value FROM meta WHERE key = 'builder_version'"
                ).fetchone()
            finally:
                conn.close()
            if row and row[0]:
                return str(row[0])
        except sqlite3.Error:
            return ""
        return ""
    legacy_path = index_dir / GRAPH_DIRNAME / GRAPH_STATE_FILENAMES[layer]
    if legacy_path.exists():
        state = _read_json(legacy_path, None)
        if isinstance(state, dict):
            return str(state.get("builder_version") or "")
    return ""


_DI_SIGNALS_MOD = None


def _load_di_signals_module():
    global _DI_SIGNALS_MOD
    if _DI_SIGNALS_MOD is None:
        import importlib.util

        di_path = Path(__file__).resolve().parent / "graph_di_signals.py"
        spec = importlib.util.spec_from_file_location("graph_di_signals", di_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Unable to load graph_di_signals from {di_path}")
        mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = mod
        spec.loader.exec_module(mod)
        _DI_SIGNALS_MOD = mod
    return _DI_SIGNALS_MOD


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write a graph artifact as gzip-compressed compact JSON, atomically.

    Wave 1p9q3 (1p9py): compact separators drop the indentation whitespace that
    dominated the pretty-printed artifacts; ``sort_keys=True`` is retained for
    deterministic output (the ``input_fingerprint`` reproducibility contract).
    ``mtime=0`` keeps the gzip header byte-stable for identical payloads. The
    bytes land in a same-directory temp file promoted via ``os.replace`` so a
    concurrently-reading process (the MCP server reads while hook-spawned builds
    write) can never observe a torn artifact.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(gzip.compress(data, compresslevel=GRAPH_GZIP_LEVEL, mtime=0))
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def _normalize_symbol_name(name: str) -> str:
    return re.sub(r"\s+", " ", name).strip()


def _simple_name(symbol_id: str) -> str:
    # INTENTIONALLY split('.', 1) (FIRST dot), NOT rsplit. Do NOT "fix" this to the bare leaf:
    # folding a 2+-level-nested symbol's bare leaf into simple_names -> symbol_lookup over-binds the
    # UNGUARDED bare-call and bare-read paths. An adversarial review verified three regressions from
    # rsplit: (1) a receiver-less bare `run()` wrong-binds to a unique nested `Outer.Inner.run`
    # (TS/JS/Rust; promoted to RECEIVER_RESOLVED on TS/JS); (2) a bare PARAMETER read (`TOKEN`)
    # wrong-binds to a same-leaf nested constant `Outer.Inner.TOKEN` (Java/Kotlin/C#/Swift — the
    # tree-sitter reads path has no local-shadow guard); (3) a bare read of an EXPLICITLY-IMPORTED
    # symbol gets shadowed by a same-leaf nested member, which on a real repo file (http2.d.ts)
    # silently DROPPED 5 correct `external::url` import-reads. The faithful fix for nested
    # member-access CONSTANT reads is exact qualified-PATH capture (const-gated), not bare-leaf
    # widening — see the member-access-reads follow-on. Keep this split('.', 1).
    if "::" not in symbol_id:
        return symbol_id
    return symbol_id.rsplit("::", 1)[-1].split(".", 1)[-1]


def _path_term(path: str) -> str:
    stem = _file_stem(path)
    return stem if stem else path


def _is_module_graph_node(node: dict[str, Any]) -> bool:
    node_id = str(node.get("id") or "")
    if not node_id or "::" in node_id:
        return False
    if str(node.get("kind") or "") == "module":
        return True
    source_file = str(node.get("source_file") or "")
    return bool(source_file) and node_id == source_file


@dataclass(frozen=True)
class _TsLanguageProfile:
    mode: str
    # Explicit per-language call-node grammar names (wave 130ol). When non-empty,
    # _ts_is_call_node consults this set instead of the legacy substring-match
    # heuristic on "expression" — which over-matched try_expression, await_expression,
    # binary_expression, etc., producing edges to language keywords.
    call_node_types: frozenset[str] = frozenset()
    # Per-language reserved-word stop terms (wave 130ol). Augments the global
    # _STOP_TERMS set. Identifiers in this set are never emitted as call candidates
    # from the regex fallback path.
    stop_terms: frozenset[str] = frozenset()
    # Per-language builtin-and-common-value denylist (wave 130ol). The cross-file
    # resolution pass refuses to rewrite `external::<name>` to a project-internal
    # node when <name> is in this set — even if a project file happens to define
    # a symbol with the same simple name. Prevents mis-resolving stdlib calls
    # (Python `len`/`range`, JS `Object`/`Array`, Swift `String`, etc.) to
    # same-named project definitions.
    builtin_denylist: frozenset[str] = frozenset()


# Tree-sitter call-node grammar names per language (AC-3). The legacy
# substring-match on "expression" matched many non-call node types
# (try_expression, await_expression, binary_expression, ...) and produced
# `external::<keyword>` edges via the regex-fallback candidate extractor.
_TS_CALL_NODES_DEFAULT = frozenset({"call_expression"})
_TS_CALL_NODES_JS = frozenset({"call_expression", "new_expression"})
# Wave 131bt (1319s): added composite_literal to Go and struct_expression to
# Rust so that construction-shape AST nodes are visited by walk_calls and routed
# to the class node via _resolve_construction_target.
_TS_CALL_NODES_GO = frozenset({"call_expression", "composite_literal"})
_TS_CALL_NODES_RUST = frozenset({"call_expression", "macro_invocation", "struct_expression"})
_TS_CALL_NODES_JAVA = frozenset({"method_invocation", "object_creation_expression"})
_TS_CALL_NODES_KOTLIN = frozenset({"call_expression"})
_TS_CALL_NODES_C = frozenset({"call_expression"})
_TS_CALL_NODES_CPP = frozenset({"call_expression"})
_TS_CALL_NODES_CSHARP = frozenset({"invocation_expression", "object_creation_expression"})
_TS_CALL_NODES_SWIFT = frozenset({"call_expression"})
_TS_CALL_NODES_OBJC = frozenset({"message_expression"})
_TS_CALL_NODES_SCALA = frozenset({"call_expression"})
_TS_CALL_NODES_RUBY = frozenset({"call", "method_call", "command"})
_TS_CALL_NODES_PHP = frozenset({
    "function_call_expression",
    "member_call_expression",
    "scoped_call_expression",
    # Wave 131bt (1319s): added so PHP `new Foo()` construction shapes are
    # visited by walk_calls and routed to the class node.
    "object_creation_expression",
})
_TS_CALL_NODES_BASH = frozenset({"command"})

# Per-language reserved-word stop terms (AC-5).
_TS_STOP_PYTHON = frozenset({
    "self", "cls", "True", "False", "None", "if", "elif", "else", "for", "while",
    "return", "yield", "break", "continue", "pass", "raise", "try", "except",
    "finally", "with", "as", "import", "from", "def", "class", "lambda", "global",
    "nonlocal", "and", "or", "not", "in", "is",
})
_TS_STOP_JS = frozenset({
    "var", "let", "const", "function", "class", "extends", "implements", "interface",
    "type", "enum", "typeof", "instanceof", "void", "await", "async", "yield",
    "return", "if", "else", "for", "while", "do", "switch", "case", "default",
    "break", "continue", "throw", "try", "catch", "finally", "new", "delete",
    "in", "of", "this", "super",
})
_TS_STOP_GO = frozenset({
    "func", "var", "const", "type", "struct", "interface", "package", "import",
    "return", "if", "else", "for", "range", "switch", "case", "default", "break",
    "continue", "go", "defer", "select", "chan", "map", "fallthrough", "goto",
})
_TS_STOP_RUST = frozenset({
    "fn", "let", "mut", "pub", "mod", "use", "struct", "enum", "impl", "trait",
    "type", "const", "static", "if", "else", "match", "for", "while", "loop",
    "break", "continue", "return", "as", "in", "where", "ref", "move", "async",
    "await", "self", "Self", "super", "crate",
})
_TS_STOP_JAVA = frozenset({
    "public", "private", "protected", "static", "final", "abstract", "synchronized",
    "transient", "volatile", "class", "interface", "enum", "extends", "implements",
    "import", "package", "return", "if", "else", "for", "while", "do", "switch",
    "case", "default", "break", "continue", "throw", "throws", "try", "catch",
    "finally", "new", "this", "super", "instanceof", "void",
})
_TS_STOP_KOTLIN = frozenset({
    "fun", "val", "var", "class", "interface", "object", "enum", "data", "sealed",
    "open", "override", "abstract", "final", "private", "protected", "internal",
    "public", "import", "package", "return", "if", "else", "for", "while", "do",
    "when", "is", "in", "as", "throw", "try", "catch", "finally", "this", "super",
    "init", "constructor", "by", "lateinit", "vararg", "inline", "noinline",
    "crossinline", "reified", "tailrec", "operator", "infix", "suspend",
})
_TS_STOP_C = frozenset({
    "int", "char", "short", "long", "float", "double", "void", "signed", "unsigned",
    "const", "volatile", "static", "extern", "auto", "register", "struct", "union",
    "enum", "typedef", "sizeof", "return", "if", "else", "for", "while", "do",
    "switch", "case", "default", "break", "continue", "goto",
})
_TS_STOP_CSHARP = frozenset({
    "public", "private", "protected", "internal", "static", "abstract", "virtual",
    "override", "sealed", "readonly", "const", "class", "interface", "struct",
    "enum", "namespace", "using", "return", "if", "else", "for", "foreach", "in",
    "while", "do", "switch", "case", "default", "break", "continue", "throw",
    "try", "catch", "finally", "new", "this", "base", "is", "as", "typeof",
    "void", "var", "async", "await",
})
_TS_STOP_SWIFT = frozenset({
    "func", "let", "var", "class", "struct", "enum", "protocol", "extension",
    "import", "public", "private", "internal", "fileprivate", "open", "static",
    "final", "lazy", "weak", "unowned", "mutating", "nonmutating", "inout",
    "throws", "rethrows", "if", "else", "for", "while", "repeat", "do", "catch",
    "defer", "guard", "switch", "case", "default", "break", "continue", "return",
    "where", "as", "is", "in", "init", "deinit", "self", "Self", "super",
    "Type", "associatedtype", "typealias", "try", "await", "async",
})
_TS_STOP_OBJC = _TS_STOP_C | frozenset({"@interface", "@implementation", "@end", "@property", "@synthesize", "self", "super", "id", "nil", "YES", "NO", "BOOL", "nonatomic", "atomic", "strong", "weak", "copy", "assign", "readonly", "readwrite"})
_TS_STOP_RUBY = frozenset({
    "def", "end", "class", "module", "if", "elsif", "else", "unless", "case",
    "when", "then", "for", "while", "until", "do", "break", "next", "redo", "retry",
    "return", "yield", "begin", "rescue", "ensure", "raise", "require", "include",
    "extend", "self", "super", "nil", "true", "false", "and", "or", "not", "in",
})
_TS_STOP_PHP = frozenset({
    "function", "class", "interface", "trait", "extends", "implements", "namespace",
    "use", "public", "private", "protected", "static", "final", "abstract", "const",
    "var", "return", "if", "else", "elseif", "for", "foreach", "as", "while", "do",
    "switch", "case", "default", "break", "continue", "throw", "try", "catch",
    "finally", "new", "self", "parent", "this", "instanceof", "echo", "print",
    "isset", "unset", "empty",
})
_TS_STOP_SCALA = frozenset({
    "def", "val", "var", "lazy", "class", "object", "trait", "case", "match",
    "extends", "with", "import", "package", "return", "if", "else", "for", "while",
    "do", "yield", "throw", "try", "catch", "finally", "new", "this", "super",
    "implicit", "private", "protected", "abstract", "override", "final", "sealed",
    "type",
})
_TS_STOP_BASH = frozenset({
    "if", "then", "elif", "else", "fi", "for", "while", "until", "do", "done",
    "case", "esac", "function", "in", "select", "time", "return", "exit", "break",
    "continue", "local", "export", "readonly", "declare", "typeset",
})

# Per-language builtin / common-value denylist (AC-1a). These names stay
# `external::*` even when a project node defines a same-named symbol.
_TS_DENY_PYTHON = frozenset({
    "len", "range", "str", "int", "float", "bool", "list", "dict", "set", "tuple",
    "bytes", "bytearray", "frozenset", "print", "input", "open", "iter", "next",
    "enumerate", "zip", "map", "filter", "sorted", "reversed", "sum", "min", "max",
    "abs", "round", "pow", "divmod", "hash", "id", "type", "isinstance", "issubclass",
    "super", "object", "Exception", "ValueError", "TypeError", "KeyError",
    "IndexError", "AttributeError", "RuntimeError", "StopIteration", "True",
    "False", "None", "callable", "hasattr", "getattr", "setattr", "delattr",
    "vars", "dir", "globals", "locals", "repr", "format",
})
_TS_DENY_JS = frozenset({
    "Object", "Array", "String", "Number", "Boolean", "Promise", "Map", "Set",
    "Date", "Math", "JSON", "RegExp", "Error", "TypeError", "RangeError", "Symbol",
    "Proxy", "Reflect", "Function", "globalThis", "console", "undefined", "null",
    "NaN", "Infinity", "parseInt", "parseFloat", "isNaN", "isFinite",
    "encodeURIComponent", "decodeURIComponent",
})
_TS_DENY_GO = frozenset({
    "len", "cap", "make", "new", "panic", "recover", "append", "copy", "delete",
    "close", "print", "println", "error", "string", "int", "int8", "int16",
    "int32", "int64", "uint", "uint8", "uint16", "uint32", "uint64", "uintptr",
    "float32", "float64", "complex64", "complex128", "bool", "byte", "rune",
    "true", "false", "nil",
})
_TS_DENY_RUST = frozenset({
    "Some", "None", "Ok", "Err", "Box", "Vec", "String", "Option", "Result",
    "panic", "println", "print", "eprintln", "eprint", "format", "vec", "assert",
    "assert_eq", "assert_ne", "debug_assert", "unreachable", "todo", "unimplemented",
    "matches", "write", "writeln", "dbg",
})
_TS_DENY_JAVA = frozenset({
    "String", "Integer", "Boolean", "Double", "Float", "Long", "Short", "Byte",
    "Character", "Object", "List", "Map", "Set", "Collection", "Iterable",
    "Exception", "RuntimeException", "IllegalArgumentException",
    "IllegalStateException", "NullPointerException", "IndexOutOfBoundsException",
    "System", "Math", "Thread", "Class", "Number", "Optional", "Stream",
    "Arrays", "Collections", "Objects",
})
_TS_DENY_KOTLIN = _TS_DENY_JAVA | frozenset({
    "Any", "Unit", "Nothing", "Pair", "Triple", "Sequence", "Array", "IntArray",
    "DoubleArray", "BooleanArray", "ByteArray", "CharArray", "FloatArray",
    "LongArray", "ShortArray", "MutableList", "MutableMap", "MutableSet",
    "listOf", "mapOf", "setOf", "mutableListOf", "mutableMapOf", "mutableSetOf",
    "println", "print", "error", "TODO", "require", "check", "let", "run",
    "with", "apply", "also",
})
_TS_DENY_CSHARP = frozenset({
    "String", "Int32", "Int64", "Int16", "Boolean", "Double", "Single", "Decimal",
    "Object", "List", "Dictionary", "HashSet", "IEnumerable", "Exception",
    "ArgumentException", "InvalidOperationException", "NullReferenceException",
    "ArgumentNullException", "Console", "Math", "DateTime", "TimeSpan", "Guid",
    "Task", "ValueTask", "Action", "Func", "Tuple",
})
_TS_DENY_SWIFT = frozenset({
    "String", "Int", "Int8", "Int16", "Int32", "Int64", "UInt", "UInt8", "UInt16",
    "UInt32", "UInt64", "Double", "Float", "Bool", "Array", "Dictionary", "Set",
    "Optional", "Result", "Date", "Data", "URL", "URLRequest", "URLSession",
    "Error", "Never", "Void", "Any", "AnyObject", "AnyHashable", "Range",
    "ClosedRange", "Character",
})
_TS_DENY_OBJC = frozenset({
    "NSString", "NSNumber", "NSArray", "NSDictionary", "NSSet", "NSObject",
    "NSError", "NSData", "NSDate", "NSURL", "NSMutableArray", "NSMutableDictionary",
    "NSMutableString", "NSMutableSet", "NSException", "BOOL", "id", "Class",
    "SEL", "IMP",
})
_TS_DENY_RUBY = frozenset({
    "String", "Integer", "Float", "Array", "Hash", "Symbol", "Range", "Regexp",
    "Object", "Class", "Module", "Proc", "Lambda", "NilClass", "TrueClass",
    "FalseClass", "Exception", "StandardError", "RuntimeError", "ArgumentError",
    "TypeError", "NameError", "NoMethodError", "puts", "print", "p", "raise",
    "require", "require_relative", "attr_accessor", "attr_reader", "attr_writer",
})
_TS_DENY_PHP = frozenset({
    "true", "false", "null", "array", "string", "int", "float", "bool", "object",
    "callable", "iterable", "void", "Exception", "Error", "TypeError",
    "ValueError", "RuntimeException", "InvalidArgumentException",
    "LogicException", "OutOfRangeException", "Closure", "Generator",
    "ArrayObject", "stdClass", "Iterator", "Traversable",
})
_TS_DENY_SCALA = frozenset({
    "String", "Int", "Long", "Double", "Float", "Boolean", "Char", "Byte", "Short",
    "Unit", "Nothing", "Any", "AnyRef", "AnyVal", "Null", "Option", "Some", "None",
    "Either", "Left", "Right", "List", "Seq", "Set", "Map", "Vector", "Array",
    "Tuple1", "Tuple2", "Tuple3", "Exception", "RuntimeException", "Throwable",
    "Future", "println", "print",
})
_TS_DENY_BASH = frozenset({
    "echo", "printf", "read", "cd", "pwd", "ls", "rm", "cp", "mv", "mkdir", "rmdir",
    "touch", "cat", "head", "tail", "grep", "sed", "awk", "find", "test", "true",
    "false", "exit", "source", "exec", "trap", "set", "unset", "shift", "let",
    "eval", "alias", "history", "type", "which", "command",
})

_TS_CODE_PROFILE = _TsLanguageProfile(mode="code")  # generic fallback for code mode
_TS_MARKUP_PROFILE = _TsLanguageProfile(mode="markup")
_TS_SQL_PROFILE = _TsLanguageProfile(mode="sql")
_TS_CONFIG_PROFILE = _TsLanguageProfile(mode="config")

_TS_LANGUAGE_PROFILES: dict[str, _TsLanguageProfile] = {
    "javascript": _TsLanguageProfile(mode="code", call_node_types=_TS_CALL_NODES_JS, stop_terms=_TS_STOP_JS, builtin_denylist=_TS_DENY_JS),
    "typescript": _TsLanguageProfile(mode="code", call_node_types=_TS_CALL_NODES_JS, stop_terms=_TS_STOP_JS, builtin_denylist=_TS_DENY_JS),
    "go": _TsLanguageProfile(mode="code", call_node_types=_TS_CALL_NODES_GO, stop_terms=_TS_STOP_GO, builtin_denylist=_TS_DENY_GO),
    "rust": _TsLanguageProfile(mode="code", call_node_types=_TS_CALL_NODES_RUST, stop_terms=_TS_STOP_RUST, builtin_denylist=_TS_DENY_RUST),
    "java": _TsLanguageProfile(mode="code", call_node_types=_TS_CALL_NODES_JAVA, stop_terms=_TS_STOP_JAVA, builtin_denylist=_TS_DENY_JAVA),
    "c": _TsLanguageProfile(mode="code", call_node_types=_TS_CALL_NODES_C, stop_terms=_TS_STOP_C, builtin_denylist=frozenset()),
    "cpp": _TsLanguageProfile(mode="code", call_node_types=_TS_CALL_NODES_CPP, stop_terms=_TS_STOP_C, builtin_denylist=frozenset()),
    "csharp": _TsLanguageProfile(mode="code", call_node_types=_TS_CALL_NODES_CSHARP, stop_terms=_TS_STOP_CSHARP, builtin_denylist=_TS_DENY_CSHARP),
    "bash": _TsLanguageProfile(mode="code", call_node_types=_TS_CALL_NODES_BASH, stop_terms=_TS_STOP_BASH, builtin_denylist=_TS_DENY_BASH),
    "kotlin": _TsLanguageProfile(mode="code", call_node_types=_TS_CALL_NODES_KOTLIN, stop_terms=_TS_STOP_KOTLIN, builtin_denylist=_TS_DENY_KOTLIN),
    "swift": _TsLanguageProfile(mode="code", call_node_types=_TS_CALL_NODES_SWIFT, stop_terms=_TS_STOP_SWIFT, builtin_denylist=_TS_DENY_SWIFT),
    "objc": _TsLanguageProfile(mode="code", call_node_types=_TS_CALL_NODES_OBJC, stop_terms=_TS_STOP_OBJC, builtin_denylist=_TS_DENY_OBJC),
    "scala": _TsLanguageProfile(mode="code", call_node_types=_TS_CALL_NODES_SCALA, stop_terms=_TS_STOP_SCALA, builtin_denylist=_TS_DENY_SCALA),
    "ruby": _TsLanguageProfile(mode="code", call_node_types=_TS_CALL_NODES_RUBY, stop_terms=_TS_STOP_RUBY, builtin_denylist=_TS_DENY_RUBY),
    "php": _TsLanguageProfile(mode="code", call_node_types=_TS_CALL_NODES_PHP, stop_terms=_TS_STOP_PHP, builtin_denylist=_TS_DENY_PHP),
    "html": _TS_MARKUP_PROFILE,
    "xml": _TS_MARKUP_PROFILE,
    "sql": _TS_SQL_PROFILE,
    "yaml": _TS_CONFIG_PROFILE,
    "toml": _TS_CONFIG_PROFILE,
    "json": _TS_CONFIG_PROFILE,
    "css": _TS_CONFIG_PROFILE,
    "scss": _TS_CONFIG_PROFILE,
    "make": _TS_CONFIG_PROFILE,
    "hcl": _TS_CONFIG_PROFILE,
    "powershell": _TS_CONFIG_PROFILE,
}

# Aggregate denylist across all known languages — used by the cross-file
# resolution pass when the target node's source language is unknown (e.g. edges
# without a source-file context). Conservative: a name is denied if ANY language
# considers it a builtin.
_TS_GLOBAL_DENYLIST: frozenset[str] = frozenset().union(*(
    profile.builtin_denylist for profile in _TS_LANGUAGE_PROFILES.values()
))


def _ts_language_key_for_path(rel_path: str) -> str | None:
    path = Path(rel_path)
    name = path.name
    if name in {"Makefile", "GNUmakefile"}:
        return "make"
    if name in {"Fastfile", "Appfile", "Podfile", "Gemfile", "Procfile", "Vagrantfile", "Brewfile"}:
        return "ruby"
    suffix = path.suffix.lower()
    return _TS_EXTENSION_TO_LANGUAGE.get(suffix)


# Wave 1p2q3 (1p2q9 A): TypeScript `tsconfig.json` path-alias resolution.
# Nx and other monorepos configure cross-package import aliases via the
# `compilerOptions.paths` field. The graph indexer previously dropped those
# imports to `external::*` because the resolver treated specifiers literally;
# field validation surfaced this as near-zero per-function
# `calls` coverage on TypeScript monorepos. This block discovers the nearest
# tsconfig with `paths`, applies the alias substitution, and probes the
# resolved candidate against project files so the import edge binds to the
# real project node id instead of `external::@scope/...`.

_TS_PATH_RESOLVE_EXTS: tuple[str, ...] = (".ts", ".tsx", ".d.ts", ".js", ".jsx", ".mjs", ".cjs")
_TS_PATH_RESOLVE_INDEX_FILES: tuple[str, ...] = ("index.ts", "index.tsx", "index.js", "index.jsx", "index.mjs", "index.cjs")

# tsconfig path → (tsconfig_dir, paths_map, base_url_dir) or None when no `paths` configured.
_TSCONFIG_PATHS_CACHE: dict[str, tuple[Path, dict[str, list[str]], Path] | None] = {}
# (root_str, file_dir_str) → discovered tsconfig path string, or None when no tsconfig with paths exists above this dir.
_TSCONFIG_DISCOVERY_CACHE: dict[tuple[str, str], str | None] = {}


def _strip_jsonc_comments(text: str) -> str:
    """Strip JSONC comments and trailing commas so json.loads can parse.

    Handles /* */ block and // line comments. Both strips track string-literal
    state so `/*` or `//` appearing inside `"..."` (e.g. tsconfig path patterns
    like `"@scope/*"`, URLs like `"https://..."`) are preserved verbatim.
    """
    out: list[str] = []
    in_str = False
    escape = False
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if escape:
            out.append(ch)
            escape = False
            i += 1
            continue
        if in_str:
            if ch == "\\":
                out.append(ch)
                escape = True
                i += 1
                continue
            if ch == '"':
                in_str = False
            out.append(ch)
            i += 1
            continue
        if ch == '"':
            in_str = True
            out.append(ch)
            i += 1
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "/":
            # Line comment — skip to newline (preserve the newline).
            j = text.find("\n", i)
            if j == -1:
                break
            i = j
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "*":
            # Block comment — skip to closing */.
            j = text.find("*/", i + 2)
            if j == -1:
                break
            i = j + 2
            continue
        out.append(ch)
        i += 1
    result = "".join(out)
    result = re.sub(r",(\s*[}\]])", r"\1", result)
    return result


def _load_tsconfig_paths(tsconfig_path: Path) -> tuple[Path, dict[str, list[str]], Path] | None:
    """Read tsconfig.json, return (tsconfig_dir, paths_map, base_url_dir) or None."""
    key = str(tsconfig_path)
    if key in _TSCONFIG_PATHS_CACHE:
        return _TSCONFIG_PATHS_CACHE[key]
    try:
        raw = tsconfig_path.read_text(encoding="utf-8")
    except OSError:
        _TSCONFIG_PATHS_CACHE[key] = None
        return None
    try:
        data = json.loads(_strip_jsonc_comments(raw))
    except (ValueError, TypeError):
        _TSCONFIG_PATHS_CACHE[key] = None
        return None
    if not isinstance(data, dict):
        _TSCONFIG_PATHS_CACHE[key] = None
        return None
    compiler = data.get("compilerOptions")
    if not isinstance(compiler, dict):
        _TSCONFIG_PATHS_CACHE[key] = None
        return None
    paths = compiler.get("paths")
    if not isinstance(paths, dict) or not paths:
        _TSCONFIG_PATHS_CACHE[key] = None
        return None
    paths_clean: dict[str, list[str]] = {}
    for pattern, replacements in paths.items():
        if not isinstance(pattern, str) or not isinstance(replacements, list):
            continue
        clean_repls = [r for r in replacements if isinstance(r, str) and r]
        if clean_repls:
            paths_clean[pattern] = clean_repls
    if not paths_clean:
        _TSCONFIG_PATHS_CACHE[key] = None
        return None
    tsconfig_dir = tsconfig_path.parent
    base_url_raw = compiler.get("baseUrl") if isinstance(compiler.get("baseUrl"), str) else "."
    base_url_dir = (tsconfig_dir / base_url_raw).resolve()
    result = (tsconfig_dir, paths_clean, base_url_dir)
    _TSCONFIG_PATHS_CACHE[key] = result
    return result


def _discover_tsconfig_for_file(file_path: Path, root: Path) -> str | None:
    """Walk upward from file_path to root, return the path of the nearest
    tsconfig (preferring `tsconfig.base.json` for Nx) that has `paths`
    configured. Caches per (root, file_dir)."""
    try:
        file_dir = file_path.parent.resolve() if file_path.is_file() else file_path.resolve()
        root_resolved = root.resolve()
    except OSError:
        return None
    cache_key = (str(root_resolved), str(file_dir))
    if cache_key in _TSCONFIG_DISCOVERY_CACHE:
        return _TSCONFIG_DISCOVERY_CACHE[cache_key]
    current = file_dir
    while True:
        for name in ("tsconfig.base.json", "tsconfig.json"):
            candidate = current / name
            if candidate.is_file() and _load_tsconfig_paths(candidate) is not None:
                _TSCONFIG_DISCOVERY_CACHE[cache_key] = str(candidate)
                return str(candidate)
        if current == root_resolved:
            break
        parent = current.parent
        if parent == current:
            break
        current = parent
    _TSCONFIG_DISCOVERY_CACHE[cache_key] = None
    return None


def _ts_path_alias_match(specifier: str, pattern: str) -> str | None:
    """Match an import specifier against a tsconfig paths pattern.

    Returns the wildcard substitution portion (or "" for exact matches), or
    None when the pattern doesn't match. Patterns may contain at most one `*`.
    """
    if "*" in pattern:
        head, _, tail = pattern.partition("*")
        if specifier.startswith(head) and (not tail or specifier.endswith(tail)):
            return specifier[len(head): len(specifier) - len(tail) if tail else None]
        return None
    return "" if specifier == pattern else None


# Wave 1p2q3 (1p2tz post-ship-3 perf): LRU cache for probe/relative-import
# resolution. Both are pure functions of `(args, filesystem state)`. Filesystem
# state changes infrequently relative to call volume during a single graph
# build, so caching pays for itself many times over on barrel-export-heavy
# codebases where each unique import specifier is hit dozens of times across
# different callers. Caches are NOT cleared per-build by design — LRU pressure
# handles eviction and stale-result risk is low (deleted files don't appear in
# the per-build file list so they're not extracted regardless of cached probe
# results).
@functools.lru_cache(maxsize=20000)
def _probe_ts_alias_target(candidate: Path, root: Path) -> str | None:
    """Probe a candidate path with TS resolution rules; return rel_path or None.

    TS bundler-mode resolution (TS 5.x `moduleResolution: "Bundler"`, used by
    Vite / esbuild / Nx defaults) allows source code to write `./foo.js` and
    have it resolve to `./foo.ts` at compile time. When the candidate's
    explicit `.js`/`.jsx`/`.mjs`/`.cjs` extension doesn't exist on disk, also
    try the matching `.ts`/`.tsx` form. Without this swap, every barrel
    re-export of the shape `export { x } from './foo.js'` would silently
    fail to resolve through.
    """
    try:
        candidate_resolved = candidate.resolve()
        root_resolved = root.resolve()
    except OSError:
        return None
    paths_to_try: list[Path] = []
    if candidate_resolved.suffix:
        paths_to_try.append(candidate_resolved)
        # Bundler-mode fallback for js → ts swap.
        suffix = candidate_resolved.suffix.lower()
        if suffix == ".js":
            paths_to_try.append(candidate_resolved.with_suffix(".ts"))
        elif suffix == ".jsx":
            paths_to_try.append(candidate_resolved.with_suffix(".tsx"))
        elif suffix == ".mjs":
            paths_to_try.append(candidate_resolved.with_suffix(".mts"))
            paths_to_try.append(candidate_resolved.with_suffix(".ts"))
        elif suffix == ".cjs":
            paths_to_try.append(candidate_resolved.with_suffix(".cts"))
            paths_to_try.append(candidate_resolved.with_suffix(".ts"))
    else:
        for ext in _TS_PATH_RESOLVE_EXTS:
            paths_to_try.append(candidate_resolved.with_suffix(ext))
    if candidate_resolved.is_dir():
        for idx in _TS_PATH_RESOLVE_INDEX_FILES:
            paths_to_try.append(candidate_resolved / idx)
    for probe in paths_to_try:
        if not probe.is_file():
            continue
        try:
            rel = probe.relative_to(root_resolved)
        except ValueError:
            continue
        return rel.as_posix()
    return None


def _resolve_ts_import_via_tsconfig(specifier: str, rel_path: str, root: Path) -> str | None:
    """Resolve `specifier` through nearest tsconfig `paths` aliases; return
    the project rel_path or None when no alias matches or the candidate is
    missing on disk."""
    if not specifier:
        return None
    if specifier.startswith(".") or specifier.startswith("/"):
        return None
    file_path = root / rel_path
    tsconfig_path_str = _discover_tsconfig_for_file(file_path, root)
    if tsconfig_path_str is None:
        return None
    loaded = _load_tsconfig_paths(Path(tsconfig_path_str))
    if loaded is None:
        return None
    _tsconfig_dir, paths_map, base_url_dir = loaded
    for pattern, replacements in paths_map.items():
        middle = _ts_path_alias_match(specifier, pattern)
        if middle is None:
            continue
        for repl in replacements:
            substituted = repl.replace("*", middle) if "*" in repl else repl
            candidate = base_url_dir / substituted
            resolved = _probe_ts_alias_target(candidate, root)
            if resolved is not None:
                return resolved
    return None


# Wave 1p2q3 (1p2tz): barrel re-export resolution. tsconfig.paths aliases on
# Nx-shaped monorepos point at `src/index.ts` barrel files that re-export
# from `./lib/<name>`. Stopping at the barrel collapses every aliased import
# onto the same N hub nodes; following re-exports to the definition file is
# what produces RECEIVER_RESOLVED edges with per-symbol granularity.

_TS_BARREL_PARSE_CACHE: dict[tuple[str, float], dict[str, str]] = {}
_TS_BARREL_WILDCARDS_CACHE: dict[tuple[str, float], list[str]] = {}
_TS_BARREL_RESOLVE_MAX_HOPS = 5

# Match `export { Foo, Bar as Baz, default as Qux } from './path'`. Group 1 is
# the brace clause body; group 2 is the module specifier.
_TS_REEXPORT_NAMED_RE = re.compile(
    r"export\s*\{\s*([^}]+?)\s*\}\s*from\s*['\"]([^'\"]+)['\"]"
)
# Match `export * from './path'`.
_TS_REEXPORT_WILDCARD_RE = re.compile(
    r"export\s*\*\s*from\s*['\"]([^'\"]+)['\"]"
)


def _parse_barrel(barrel_path: Path) -> tuple[dict[str, str], list[str]]:
    """Return ({local_name: (module_specifier, source_name)}, [wildcard_modules]).

    Cached per file path + mtime. `local_name` is the name as exposed by the
    barrel; `source_name` is the original name in the re-exported module.
    Default re-exports (`{ default as Foo }`) appear with source_name="default".
    """
    try:
        stat = barrel_path.stat()
    except OSError:
        return ({}, [])
    cache_key = (str(barrel_path), stat.st_mtime)
    if cache_key in _TS_BARREL_PARSE_CACHE:
        return (_TS_BARREL_PARSE_CACHE[cache_key], _TS_BARREL_WILDCARDS_CACHE.get(cache_key, []))
    named_map: dict[str, str] = {}
    sourcename_map: dict[str, str] = {}  # local_name -> original name in source module
    wildcards: list[str] = []
    try:
        text = barrel_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        _TS_BARREL_PARSE_CACHE[cache_key] = {}
        _TS_BARREL_WILDCARDS_CACHE[cache_key] = []
        return ({}, [])
    for m in _TS_REEXPORT_NAMED_RE.finditer(text):
        clause = m.group(1)
        module_spec = m.group(2)
        for part in clause.split(","):
            item = part.strip()
            if not item:
                continue
            # Three shapes: "Foo", "Foo as Bar", "default as Foo".
            if " as " in item:
                left, right = [s.strip() for s in item.split(" as ", 1)]
                source_name = left
                local_name = right
            else:
                source_name = local_name = item
            if not local_name:
                continue
            named_map[local_name] = module_spec
            sourcename_map[local_name] = source_name
    for m in _TS_REEXPORT_WILDCARD_RE.finditer(text):
        wildcards.append(m.group(1))
    _TS_BARREL_PARSE_CACHE[cache_key] = named_map
    _TS_BARREL_WILDCARDS_CACHE[cache_key] = wildcards
    # Stash the rename info under the same key as a small attached dict so the
    # resolver can recover the original source name for the next hop.
    _TS_BARREL_PARSE_CACHE[(str(barrel_path), stat.st_mtime, "_rename")] = sourcename_map  # type: ignore[assignment]
    return (named_map, wildcards)


@functools.lru_cache(maxsize=20000)
def _resolve_relative_ts_import(specifier: str, from_file: Path, root: Path) -> str | None:
    """Resolve a relative TS import specifier (`./foo`, `../bar`) against the
    containing file. Returns the repo-relative project path or None when the
    target doesn't probe to a real file."""
    if not specifier:
        return None
    if not (specifier.startswith(".") or specifier.startswith("/")):
        return None
    candidate = (from_file.parent / specifier).resolve()
    return _probe_ts_alias_target(candidate, root)


# Wave 1p2q3 (1p2tz post-ship-3 perf): cache the set of top-level declared
# names per file (keyed on path + mtime) so `_file_declares_name` becomes a
# hash-set membership check after the first parse rather than re-reading the
# file and re-running the regex for every name. On barrel-export-heavy codebases
# (field report: 14 aliases, each pointing at a barrel that re-exports 10–100 symbols,
# each re-export potentially walking through 2–3 hops to reach a definition
# file), the prior implementation triggered tens of thousands of redundant file
# reads + regex runs during a single graph build.
_TS_FILE_DECLARED_NAMES_CACHE: dict[tuple[str, float], frozenset[str]] = {}

# Single combined regex matching any top-level declaration's binding name.
# Captures the identifier as group(1).
_TS_DECLARED_NAMES_RE = re.compile(
    r"(?m)^\s*(?:export\s+)?(?:default\s+)?"
    r"(?:abstract\s+|async\s+)?"
    r"(?:class|function|const|let|var|interface|type|enum)\s+"
    r"([A-Za-z_][A-Za-z0-9_]*)"
)


def _file_declared_names(file_rel: str, root: Path) -> frozenset[str]:
    """Return the set of top-level binding names declared in a TS/JS file.

    Cached per (file path, mtime). The cache is module-level — populated
    lazily during graph extraction and naturally invalidated when source
    files change mtime."""
    if not file_rel:
        return frozenset()
    path = root / file_rel
    try:
        stat = path.stat()
    except OSError:
        return frozenset()
    key = (str(path), stat.st_mtime)
    cached = _TS_FILE_DECLARED_NAMES_CACHE.get(key)
    if cached is not None:
        return cached
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        result: frozenset[str] = frozenset()
        _TS_FILE_DECLARED_NAMES_CACHE[key] = result
        return result
    names = frozenset(m.group(1) for m in _TS_DECLARED_NAMES_RE.finditer(text))
    _TS_FILE_DECLARED_NAMES_CACHE[key] = names
    return names


def _file_declares_name(file_rel: str, name: str, root: Path) -> bool:
    """Return True when the file declares `name` at the top level via class /
    function / const / let / var / interface / type / enum syntax. Reads
    through `_file_declared_names`, so the file's declaration set is parsed
    at most once per (path, mtime)."""
    if not name:
        return False
    return name in _file_declared_names(file_rel, root)


def _resolve_through_barrel(
    imported_name: str,
    target_rel_path: str,
    root: Path,
    _seen: set[str] | None = None,
    _depth: int = 0,
) -> str:
    """Walk barrel re-exports until the symbol's actual definition file is found.

    Returns the repo-relative project path. Falls back to ``target_rel_path``
    (the input barrel) when no chain terminates at a declaration of
    ``imported_name``. Recursion is bounded at ``_TS_BARREL_RESOLVE_MAX_HOPS``;
    cycles in the resolved-paths chain are detected via ``_seen``.
    """
    if _depth >= _TS_BARREL_RESOLVE_MAX_HOPS:
        return target_rel_path
    if _seen is None:
        _seen = set()
    if target_rel_path in _seen:
        return target_rel_path
    _seen = _seen | {target_rel_path}
    barrel_path = root / target_rel_path
    if not barrel_path.is_file():
        return target_rel_path
    # If the current file declares the name directly, stop here.
    if _depth > 0 and _file_declares_name(target_rel_path, imported_name, root):
        return target_rel_path
    named_map, wildcards = _parse_barrel(barrel_path)
    # Named / renamed re-exports.
    if imported_name in named_map:
        try:
            stat = barrel_path.stat()
            sourcename_map = _TS_BARREL_PARSE_CACHE.get(
                (str(barrel_path), stat.st_mtime, "_rename")  # type: ignore[arg-type]
            ) or {}
        except OSError:
            sourcename_map = {}
        next_module_spec = named_map[imported_name]
        next_name = sourcename_map.get(imported_name, imported_name)
        next_rel = _resolve_relative_ts_import(next_module_spec, barrel_path, root)
        if next_rel is not None:
            # Recurse with the source-side name (post-rename).
            return _resolve_through_barrel(next_name, next_rel, root, _seen, _depth + 1)
    # Wildcard re-exports: probe each. Stop at first hit where the name is
    # declared; otherwise fall back to the barrel.
    for wild_spec in wildcards:
        wild_rel = _resolve_relative_ts_import(wild_spec, barrel_path, root)
        if wild_rel is None:
            continue
        if _file_declares_name(wild_rel, imported_name, root):
            return wild_rel
        # Recurse into the wildcard target — it might itself be a barrel.
        wild_resolved = _resolve_through_barrel(imported_name, wild_rel, root, _seen, _depth + 1)
        if wild_resolved != wild_rel:
            return wild_resolved
    # No re-export chain produced a declaration; stay at the (last) barrel.
    return target_rel_path


def _ts_get_language(lang_key: str):
    if not _TS_AVAILABLE:
        return None
    if lang_key in _TS_LANGS:
        return _TS_LANGS[lang_key]
    module_info = _TS_LANGUAGE_MODULES.get(lang_key)
    if not module_info:
        _TS_LANGS[lang_key] = None
        return None
    module_name, language_fn = module_info
    try:
        module = importlib.import_module(module_name)
        language_factory = getattr(module, language_fn)
        raw_language = language_factory()
        lang = Language(raw_language)
    except Exception:
        _TS_LANGS[lang_key] = None
        return None
    _TS_LANGS[lang_key] = lang
    return lang


def _ts_get_parser(lang_key: str):
    if lang_key in _TS_PARSERS:
        return _TS_PARSERS[lang_key]
    lang = _ts_get_language(lang_key)
    if lang is None:
        _TS_PARSERS[lang_key] = None
        return None
    try:
        parser = _TSParser(lang)
    except Exception:
        _TS_PARSERS[lang_key] = None
        return None
    _TS_PARSERS[lang_key] = parser
    return parser


# Wave 1p5c4: skip tree-sitter graph extraction on very large files (a full AST over a multi-MB/GB
# file spins). Over the cap → no extraction for that file (graceful, same as tree-sitter-unavailable).
# Override via WAVEFOUNDRY_MAX_TS_PARSE_BYTES (the indexer sets it from
# `indexing.max_treesitter_parse_bytes` in workflow-config.json). 0/negative disables the cap.
MAX_TREESITTER_PARSE_BYTES_DEFAULT = 2_000_000


def _ts_parse(lang_key: str, source_text: str):
    _cap = int(os.environ.get("WAVEFOUNDRY_MAX_TS_PARSE_BYTES") or MAX_TREESITTER_PARSE_BYTES_DEFAULT)
    if _cap > 0 and len(source_text) > _cap:
        return None
    parser = _ts_get_parser(lang_key)
    if parser is None:
        if lang_key not in _TS_WARNED:
            _TS_WARNED.add(lang_key)
            # Wave 1p9io: stderr, not stdout. _ts_parse runs in-process during the MCP server's graph
            # auto-rebuild (build_index → update_graph_index → _extract_tree_sitter_artifact), where
            # sys.stdout is the JSON-RPC channel. Missing grammar wheels are more common on Windows,
            # so this warning is more likely to fire there — exactly where a stdout write breaks framing.
            if not _TS_AVAILABLE:
                print(
                    f"build_index: tree-sitter unavailable; using fallback graph extraction for {lang_key}",
                    file=sys.stderr,
                    flush=True,
                )
            else:
                print(
                    f"build_index: tree-sitter grammar for {lang_key} unavailable; using fallback graph extraction",
                    file=sys.stderr,
                    flush=True,
                )
        return None
    try:
        return parser.parse(source_text.encode("utf-8", errors="replace"))
    except Exception:
        return None


def _over_ts_parse_cap(source_text: str) -> bool:
    """True when a file exceeds the tree-sitter AST parse cap (the SAME cap
    ``_ts_parse`` enforces, computed identically on character length).

    Wave 1p9q6: a file in the (parse-cap, walk-cap] window returns True and
    routes to the bounded line-scan degraded-extraction tier instead of
    contributing zero graph nodes. Cap of 0/negative disables the guard, in
    which case nothing is ever "over cap" (parity with ``_ts_parse``)."""
    cap = int(os.environ.get("WAVEFOUNDRY_MAX_TS_PARSE_BYTES") or MAX_TREESITTER_PARSE_BYTES_DEFAULT)
    return cap > 0 and len(source_text) > cap


def _ts_node_text(node, source_bytes: bytes) -> str:
    try:
        return source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace").strip()
    except Exception:
        return ""


def _ts_clean_name(text: str) -> str:
    value = re.sub(r"\s+", " ", str(text or "")).strip()
    if not value:
        return ""
    value = value.strip("`'\"")
    value = value.rstrip(";,)")
    value = value.strip()
    # Wave 1p2q3 (1p2tz field follow-up): preserve a leading `@` so scoped npm /
    # Nx package specifiers (`@scope/hooks`, `@acme/backend`, `@scope/pkg`)
    # survive into the alias resolver. Without this, `@scope/hooks` would be
    # cleaned to `scope/hooks` and fail to match the tsconfig.paths pattern
    # `@scope/hooks` — which is the silent root cause of every scoped-import
    # resolution failing on Nx monorepos. The leading `@` is the only special
    # case; bare `@` mid-string is not a valid identifier prefix in TS/JS.
    if value.startswith("@"):
        rest_match = re.search(r"[A-Za-z_][A-Za-z0-9_.$:#/\-]*", value[1:])
        if rest_match:
            return "@" + rest_match.group(0)
    match = re.search(r"[A-Za-z_][A-Za-z0-9_.$:#/\-]*", value)
    if match:
        return match.group(0)
    return value


def _ts_name_from_fields(node, source_bytes: bytes, *, field_names: tuple[str, ...] = _TS_NAME_FIELD_PRIORITY) -> str:
    for field_name in field_names:
        try:
            child = node.child_by_field_name(field_name)
        except Exception:
            child = None
        if child is None:
            continue
        candidate = _ts_clean_name(_ts_node_text(child, source_bytes))
        if candidate:
            return candidate
    return ""


def _ts_name_from_descendants(node, source_bytes: bytes) -> str:
    identifier_types = {
        "identifier",
        "field_identifier",
        "property_identifier",
        "type_identifier",
        "scoped_identifier",
        "qualified_identifier",
        "namespace_identifier",
        "tag_name",
        "object_reference",
        "key",
        "string",
        "string_literal",
        "raw_string_literal",
        "attribute",
        "pair",
    }
    try:
        for child in getattr(node, "named_children", []):
            child_type = str(getattr(child, "type", "") or "")
            if child_type in identifier_types:
                candidate = _ts_clean_name(_ts_node_text(child, source_bytes))
                if candidate:
                    return candidate
    except Exception:
        pass
    return ""


def _ts_markup_name_candidates(node, source_bytes: bytes) -> list[str]:
    text = ""
    try:
        for child in getattr(node, "named_children", []):
            if str(getattr(child, "type", "") or "") == "start_tag":
                text = _ts_node_text(child, source_bytes)
                break
    except Exception:
        text = ""
    if not text:
        text = _ts_node_text(node, source_bytes)
    candidates: list[str] = []
    for attr in ("id", "name", "role", "for"):
        for match in re.finditer(rf"\b{attr}\s*=\s*['\"]([^'\"]+)['\"]", text, re.IGNORECASE):
            candidate = _ts_clean_name(match.group(1))
            if candidate and candidate not in candidates:
                candidates.append(candidate)
    tag_match = re.match(r"\s*<\s*([A-Za-z_][A-Za-z0-9:_-]*)", text)
    if tag_match:
        tag = tag_match.group(1).casefold()
        if tag in {"a", "form", "button", "input", "label", "select", "option", "textarea"}:
            tag_value = _ts_clean_name(tag_match.group(1))
            if tag_value and tag_value not in candidates:
                candidates.append(tag_value)
    return candidates


def _ts_markup_import_nodes(node, source_bytes: bytes) -> bool:
    lower = str(getattr(node, "type", "") or "").lower()
    if any(token in lower for token in ("script", "style", "link", "iframe", "img", "source", "embed")):
        return True
    text = ""
    try:
        for child in getattr(node, "named_children", []):
            if str(getattr(child, "type", "") or "") == "start_tag":
                text = _ts_node_text(child, source_bytes)
                break
    except Exception:
        text = ""
    if not text:
        text = _ts_node_text(node, source_bytes)
    return bool(re.search(r"\b(?:src|href|action|xlink:href)\s*=\s*['\"][^'\"]+['\"]", text, re.IGNORECASE))


def _ts_name_candidates(node, source_bytes: bytes, mode: str | None = None) -> list[str]:
    candidates: list[str] = []
    if mode == "markup":
        for candidate in _ts_markup_name_candidates(node, source_bytes):
            if candidate not in candidates:
                candidates.append(candidate)
        return [candidate for candidate in candidates if candidate]
    field_candidate = _ts_name_from_fields(node, source_bytes)
    if field_candidate:
        candidates.append(field_candidate)
    fallback_candidate = _ts_name_from_descendants(node, source_bytes)
    if fallback_candidate and fallback_candidate not in candidates:
        candidates.append(fallback_candidate)
    return [candidate for candidate in candidates if candidate]


def _ts_kind_for_definition(node_type: str, current_scope_kind: str | None, mode: str) -> str:
    lower = node_type.lower()
    if mode == "markup":
        if "script" in lower or "style" in lower:
            return "module"
        if "tag" in lower or "element" in lower or "attribute" in lower:
            return "class"
        return "module"
    if mode == "sql":
        if any(token in lower for token in ("table", "view", "schema", "cte", "data", "column")):
            return "class"
        if any(token in lower for token in ("procedure", "function", "trigger", "query", "statement")):
            return "function"
        return "module"
    if mode == "config":
        if any(token in lower for token in ("rule", "target", "job", "step", "command", "script", "resource", "provider", "workflow")):
            return "function"
        if any(token in lower for token in ("selector", "block", "property", "attribute", "pair", "entry", "key")):
            return "class"
        return "module"
    # Variable bindings (Swift/Kotlin `property_declaration`, TS/JS/C# `variable_declaration`,
    # Java `local_variable_declaration`/`field_declaration`, Rust `let_declaration`, Go
    # `var_declaration`/`const_declaration`/`short_var_declaration`) are NOT scope-pushing.
    # The kind ``variable`` is excluded from ``_ts_is_scope_node`` so calls inside
    # ``let result = foo()`` are correctly attributed to the enclosing function (wave 130ol).
    if lower in _TS_VARIABLE_DEFINITION_TYPES:
        return "variable"
    # Wave 1p61v: TS/JS type-shape members are NOT callables and must not fall
    # through to the default `function`. A type alias is a `type`; an interface /
    # object-type DATA member (`property_signature`) is a `property`. Method
    # *signatures* keep `function` via the `method` branch below. Without this,
    # `: string` fields and `export type X = …` aliases rendered as `(function)`
    # entry points in the codebase map (p60n field trace, Issue 1) — the
    # graph diverged from `code_outline`, which yields zero callable symbols for
    # the same pure-type files.
    if "type_alias" in lower:
        return "type"
    if lower == "property_signature":
        return "property"
    # Wave 1p9qh (1p9qb): Java `@interface` (annotation_type_declaration) is a
    # TYPE declaration — classify as "class", consistent with how interface/
    # enum/record declarations normalize (their tokens hit the class branch
    # below; "annotation_type" matches none of them, so it previously fell
    # through to the default "function"). EXACT match on purpose: the body's
    # `annotation_type_element_declaration` members (`String value();`) are
    # method-shaped and must KEEP the "function" fallthrough.
    if lower == "annotation_type_declaration":
        return "class"
    if any(token in lower for token in ("method", "constructor", "member")):
        return "function"
    if any(token in lower for token in ("class", "interface", "struct", "enum", "trait", "record")):
        return "class"
    if any(token in lower for token in ("module", "namespace", "package", "object")):
        return "module"
    if any(token in lower for token in ("table", "view", "schema", "resource")):
        return "class"
    return "function"


# Per-language variable-binding node types — never push scope (wave 130ol).
# Without this, a call inside ``let result = foo()`` gets attributed to
# ``…enclosingFunction.result`` instead of ``…enclosingFunction``, and when
# ``result`` is short or has no external users the short-symbol pruning pass
# silently drops the call edge with the local-variable node.
_TS_VARIABLE_DEFINITION_TYPES = frozenset({
    # Swift / Kotlin
    "property_declaration",
    # Java
    "local_variable_declaration",
    "field_declaration",
    # C#
    "variable_declaration",
    # JS / TS
    "lexical_declaration",
    "variable_statement",
    # Rust
    "let_declaration",
    # Go
    "var_declaration",
    "const_declaration",
    "short_var_declaration",
    # C / C++ — note: `declaration` is too generic (also covers function decls)
    # so we don't catch those here. Calls in C/C++ initializers are rare in practice.
})


def _ts_is_definition_node(node_type: str, mode: str) -> bool:
    lower = node_type.lower()
    if mode == "markup":
        return any(token in lower for token in ("element", "tag", "document", "fragment"))
    if mode == "sql":
        # Wave 1p9qi (1p9qd): SQL extraction is clause-aware — definitions come
        # from the structured statement analysis (`_sql_analyze_program`), never
        # from node-type substring matching (which registered CTE names, temp
        # tables, and even MERGE aliases as schema objects). The generic walk
        # no longer runs for SQL files at all; keep the classifier honest for
        # any other caller.
        return False
    if mode == "config":
        return any(token in lower for token in ("block", "pair", "property", "attribute", "rule", "selector", "entry", "key", "directive"))
    if any(token in lower for token in _TS_IMPORT_KEYWORDS) or "require" in lower or "source" in lower:
        return False
    def_context = any(token in lower for token in ("declaration", "definition", "specifier", "statement", "item", "declarator", "signature", "impl"))
    if lower.endswith("_declaration") or lower.endswith("_definition") or lower.endswith("_item"):
        return True
    # Wave 1319k: Ruby grammar uses bare `class`, `module`, `method`,
    # `singleton_method` node types (no `_declaration`/`_definition`/`_item`
    # suffix). Recognize these explicitly.
    if lower in ("class", "module", "method", "singleton_method"):
        return True
    return def_context and any(token in lower for token in (
        "class", "interface", "struct", "enum", "trait", "record", "module", "namespace", "package",
        "function", "method", "constructor", "procedure", "macro", "rule", "resource", "object",
        "target", "task", "command", "table", "view", "trigger", "query", "type", "block",
        "property", "attribute", "selector", "element", "tag", "entry",
    ))


# Wave 1p4ls: tree-sitter literal node types whose source text we capture as a constant's `value`.
_TS_CONST_LITERAL_TYPES = frozenset({
    "integer_literal", "int_literal", "integer", "float_literal", "decimal_integer_literal",
    "decimal_floating_point_literal", "number", "numeric_literal", "string_literal",
    "interpreted_string_literal", "raw_string_literal", "line_string_literal", "string",
    "true", "false", "null", "nil", "boolean_literal", "character_literal", "char_literal",
    "rune_literal", "encapsed_string", "unary_expression", "prefix_expression",
})


# Wave 1p4ls: leaf node types that can be a constant READ (name-use) for the `reads` edge.
# `constant` is Ruby's capital-initial reference node; `name` is PHP's bare const/callee reference;
# the rest are the per-grammar identifiers. The const-target gate keeps non-constant uses harmless.
_TS_READ_IDENT_TYPES = frozenset({"identifier", "simple_identifier", "field_identifier", "constant", "name"})

# Member-access read attribution: the node type of a qualified reference `A.B.C` / `A::B::C` per
# language. A read of a CONSTANT via member access (`Status.ACTIVE`, `AppConstants.Network.userAgent`,
# `Outer.Inner.TOKEN`) is resolved by EXACT qualified-name match against constant nodes — faithful (the
# qualifier disambiguates), const-gated, and it NEVER widens bare-leaf resolution (so it introduces none
# of the bare-call / param-shadow / import-shadow over-binds that a `_simple_name` rsplit would).
_TS_MEMBER_ACCESS_TYPES = frozenset({
    "member_expression",                  # TS / JS  (A.B.C)
    "navigation_expression",              # Swift, Kotlin  (A.B.C)
    "field_access",                       # Java  (A.B.C)
    "member_access_expression",           # C#  (A.B.C)
    "selector_expression",                # Go  (A.B.C)
    "scoped_identifier",                  # Rust  (A::B::C)
    "scope_resolution",                   # Ruby  (A::B::C)
    "class_constant_access_expression",   # PHP  (A::B)
})

# A PURE static qualified path: identifiers joined by `.` / `::` only — no calls, subscripts, `this`,
# literals, or whitespace (which would signal a computed/dynamic member access, not a resolvable name).
_TS_MEMBER_PATH_RE = re.compile(r"^[A-Za-z_$][\w$]*(?:(?:\.|::)[A-Za-z_$][\w$]*)+$")

# Parameter + local-variable BINDING nodes per language. Their bound NAME (never the type) is collected
# per function so a member-access constant read whose head qualifier is a local/param shadow is suppressed
# (member-access review F4: `func reader(Config: Holder){ return Config.value }` reads the param, not the
# struct's static const). Suppressing is FAITHFUL — if the head is a local binding, the access is on that
# local, never the type's constant.
_TS_BINDING_NODE_TYPES = frozenset({
    "formal_parameter", "spread_parameter",                  # Java
    "parameter",                                             # Swift, C#, Rust, Kotlin
    "required_parameter", "optional_parameter",              # TS / JS
    "parameter_declaration",                                 # Go
    "simple_parameter", "variadic_parameter",               # PHP
    "function_value_parameter",                              # Kotlin
    "variable_declarator",                                   # Java / TS / JS / C#  (function-local only — gated to fn scope)
    "property_declaration", "variable_declaration",          # Swift / Kotlin
    "let_declaration",                                       # Rust
    "short_var_declaration", "var_spec", "const_spec",       # Go
    "assignment", "assignment_expression",                  # Ruby / PHP (implicit locals)
})


def _ts_is_member_property_leaf(node) -> bool:
    """True when ``node`` is the PROPERTY/field side of a member access (the trailing `C` in `A.B.C`).
    Such leaves are NOT buffered as bare reads — the member-access PATH branch resolves the qualified
    read instead (by exact qname, const-gated, with the F4 qualifier-shadow guard). This removes the
    pre-existing trailing-member over-fire where a bare leaf `value` from an instance access
    `local.value` wrong-binds a same-named top-level constant `Type.value`."""
    p = getattr(node, "parent", None)
    if p is None:
        return False
    pt = str(getattr(p, "type", "") or "")
    if pt == "navigation_suffix":   # Swift trailing `.member` wrapper
        return True
    if pt in _TS_MEMBER_ACCESS_TYPES:
        # The object/operand is the FIRST named child of a member-access node; any OTHER identifier
        # under it is the trailing property/field side (works uniformly whether the grammar uses a
        # `property`/`field` field, a bare trailing identifier (Kotlin), or a `field_identifier` (Go)).
        kids = list(getattr(p, "named_children", []))
        # NOTE: `==` not `is` — tree-sitter's Python binding returns a NEW wrapper object on every
        # `.named_children`/`.parent` access, so `is` is ALWAYS False (a blanket skip that would also
        # drop the legit HEAD read, e.g. the const in `FRAMEWORK_FLOW.length`). `Node.__eq__` compares
        # the underlying AST node.
        if kids and kids[0] != node:
            return True
    return False


def _ts_binding_names(node) -> set[str]:
    """The NAME(s) bound by a parameter / local-variable node — extracted from the ``name``/``pattern``/
    ``left`` field (never the type), so the qualifier-shadow guard cannot accidentally suppress a real
    read of a type's constant."""
    names: set[str] = set()
    fields: list = []
    for fld in ("name", "pattern", "left"):
        try:
            c = node.child_by_field_name(fld)
        except Exception:
            c = None
        if c is not None:
            fields.append(c)
    if not fields:  # Kotlin parameter / variable_declaration carry the name as a bare leading identifier
        for c in getattr(node, "named_children", []):
            if str(getattr(c, "type", "") or "") in ("simple_identifier", "identifier"):
                fields.append(c)
                break
    for c in fields:
        ct = str(getattr(c, "type", "") or "")
        leaves = [c] if ct in ("identifier", "simple_identifier", "variable_name") else [
            g for g in getattr(c, "named_children", [])
            if str(getattr(g, "type", "") or "") in ("identifier", "simple_identifier", "variable_name")
        ]
        for leaf in leaves:
            try:
                nm = leaf.text.decode().strip()
            except Exception:
                nm = ""
            if nm:
                names.add(nm)
    return names


def _ts_member_access_path(node, source_bytes: bytes) -> str | None:
    """The dotted qualified name of a member-access node (``::`` normalized to ``.``), or ``None`` when
    it is not a pure static path (e.g. ``foo().bar``, ``arr[0].x``, ``this.x``). Used to resolve a
    qualified CONSTANT read by exact qname match."""
    try:
        text = source_bytes[node.start_byte:node.end_byte].decode("utf-8", "replace").strip()
    except Exception:
        return None
    if not _TS_MEMBER_PATH_RE.match(text):
        return None
    norm = text.replace("::", ".")
    # A receiver-relative access (`this.X`, `self.X`, `super.X`, `cls.X`) is not a static type path;
    # no constant qname begins with these, but reject them so the contract is explicit (not reliant
    # on an unstated qname-mismatch invariant).
    if norm.split(".", 1)[0] in ("this", "self", "super", "cls"):
        return None
    return norm


def _ts_literal_value(value_node, source_bytes: bytes) -> str | None:
    if value_node is None:
        return None
    if str(getattr(value_node, "type", "") or "") in _TS_CONST_LITERAL_TYPES:
        try:
            return source_bytes[value_node.start_byte:value_node.end_byte].decode("utf-8", "replace")[:200]
        except Exception:
            return None
    return None


def _ts_declarator_value(decl_node, source_bytes: bytes) -> str | None:
    """RHS value of a declarator / const_spec / element node when it is a simple literal."""
    v = None
    try:
        v = decl_node.child_by_field_name("value")
    except Exception:
        v = None
    if v is None:
        kids = list(getattr(decl_node, "children", []) or [])
        for i, c in enumerate(kids):
            if str(getattr(c, "type", "") or "") == "=" and i + 1 < len(kids):
                v = kids[i + 1]
                break
    # Go wraps the RHS in an `expression_list`; unwrap a single-element list to its literal.
    if v is not None and str(getattr(v, "type", "") or "") == "expression_list":
        named = [c for c in getattr(v, "children", []) if getattr(c, "is_named", False)]
        if len(named) == 1:
            v = named[0]
    return _ts_literal_value(v, source_bytes)


def _ts_constant_decls(lang_key, node, node_type, source_bytes, source_lines, *, in_type_body):
    """Wave 1p4ls: the constant(s) DECLARED directly by ``node`` for the graph lane — a list of
    ``(name, value_or_None)``. Reuses the 1p4mf chunk-lane detection predicates (Req-7 — ONE
    detector, two consumers). Returns [] when ``node`` is not a constant declaration. The caller
    scope-gates (function/method-body locals are never passed). ``in_type_body`` is True when the
    enclosing scope is a class/struct/type member body (used by Swift's static-vs-instance rule)."""
    ck = _chunker_module()
    out: list[tuple[str, str | None]] = []
    try:
        if lang_key == "java":
            if node_type == "field_declaration" and not ck._java_field_is_static_final(node):
                return []
            if node_type in ("field_declaration", "constant_declaration"):
                for d in node.children:
                    if str(getattr(d, "type", "") or "") == "variable_declarator":
                        nm = ck._java_declarator_name(d, source_lines)
                        if nm:
                            out.append((nm, _ts_declarator_value(d, source_bytes)))
        elif lang_key == "csharp":
            if node_type == "field_declaration" and ck._csharp_is_const_field(node, source_lines):
                for d in node.children:
                    if str(getattr(d, "type", "") or "") == "variable_declaration":
                        for vd in d.children:
                            if str(getattr(vd, "type", "") or "") == "variable_declarator":
                                ident = next((c for c in vd.children if str(getattr(c, "type", "") or "") == "identifier"), None)
                                if ident is not None:
                                    out.append((ident.text.decode(), _ts_declarator_value(vd, source_bytes)))
        elif lang_key == "kotlin":
            if node_type == "property_declaration" and ck._kotlin_property_is_const(node):
                nm = ck._kotlin_property_name(node, source_lines)
                if nm:
                    out.append((nm, _ts_declarator_value(node, source_bytes)))
        elif lang_key == "go":
            if node_type == "const_declaration":
                for spec in node.children:
                    if str(getattr(spec, "type", "") or "") == "const_spec":
                        for nm in ck._go_const_spec_names(spec, source_lines):
                            if nm != "_":
                                out.append((nm, _ts_declarator_value(spec, source_bytes)))
        elif lang_key == "rust":
            if node_type in ck._RUST_CONST_NODE_TYPES:
                nm = ck._rust_const_name(node, source_lines)
                if nm:
                    out.append((nm, _ts_declarator_value(node, source_bytes)))
        elif lang_key == "swift":
            if node_type == "property_declaration":
                if ck._swift_property_is_computed(node):
                    return []
                if in_type_body and not ck._swift_property_has_static(node):
                    return []  # instance let/var = a field, not a constant
                for nm in ck._swift_property_names(node):
                    out.append((nm, _ts_declarator_value(node, source_bytes)))
            elif node_type == "enum_entry":
                for c in node.children:
                    if str(getattr(c, "type", "") or "") == "simple_identifier":
                        out.append((c.text.decode().strip(), None))
        elif lang_key == "ruby":
            if node_type == "assignment":
                lhs = node.child_by_field_name("left")
                if lhs is not None and str(getattr(lhs, "type", "") or "") not in ck._RUBY_LOCAL_LHS_TYPES:
                    for nm in ck._ruby_const_lhs_names(lhs):
                        if nm:
                            out.append((nm, _ts_declarator_value(node, source_bytes)))
        elif lang_key == "php":
            if node_type == "const_declaration":
                for el in node.children:
                    if str(getattr(el, "type", "") or "") == "const_element":
                        nm_node = next((c for c in el.children if str(getattr(c, "type", "") or "") == "name"), None)
                        if nm_node is not None:
                            out.append((nm_node.text.decode().strip(), _ts_declarator_value(el, source_bytes)))
        elif lang_key in ("typescript", "javascript"):
            if node_type == "lexical_declaration" and ck._js_is_const_decl(node):
                for d in node.children:
                    if str(getattr(d, "type", "") or "") == "variable_declarator":
                        if ck._js_const_value_type(d) in ck._JS_VALUE_CONST_TYPES:
                            nm_node = d.child_by_field_name("name")
                            if nm_node is not None and str(getattr(nm_node, "type", "") or "") == "identifier":
                                out.append((nm_node.text.decode(), _ts_declarator_value(d, source_bytes)))
    except Exception:
        return []
    return out


# Wave 131bt (1319v): languages where the indexer should recover an ERROR-wrapped
# top-level class declaration. Tree-sitter occasionally fails to parse a class body
# (parse-resistant interior construct) and emits an ERROR node wrapping the entire
# class declaration. Without recovery the class node is never registered, the
# basename-match class/module merge can't fire, and cross-file `external::ClassName`
# construction edges (CONSTRUCTION_RESOLVED) have no project node to bind to.
# Limited to languages that use file-level type declarations.
_TS_ERROR_CLASS_RECOVERY_LANGS: frozenset[str] = frozenset({
    "swift", "kotlin", "scala", "java", "csharp",
})

# Match the prefix of an ERROR-wrapped class declaration after stripping leading
# attributes/modifiers. Captures the keyword and the type name; the type name must
# be PascalCase to keep this conservative (avoid recovering e.g. ERROR nodes that
# happen to start with `class` in some other context).
_TS_ERROR_CLASS_PREFIX_RE = re.compile(
    r"^(class|struct|actor|enum|protocol|interface|object|record|trait)\s+([A-Z]\w*)"
)
# Strips one or more leading attribute (`@Foo`, `@Foo(...)`) or access/final
# modifier tokens before the class keyword. Run iteratively so it doesn't have to
# enumerate every modifier combination.
_TS_ERROR_CLASS_MODIFIER_RE = re.compile(
    r"^\s*(?:@\w+(?:\([^)]*\))?\s+|"
    r"(?:public|private|internal|fileprivate|open|final|sealed|abstract|static)\s+)+"
)


def _ts_recover_error_class(node, source_bytes: bytes, lang_key: str) -> tuple[str, str] | None:
    """Recover (name, kind) from an ERROR node that wraps a class declaration.

    Returns a tuple when the ERROR node's source-text prefix matches a recognizable
    class-declaration shape AND the node contains an identifier named child whose
    text matches the recovered name. Both conditions are required so that ERROR
    nodes containing the word "class" in some other context (e.g. a property of
    type `class`) are NOT recovered as types.

    The accepted identifier child kinds are ``type_identifier``, ``simple_identifier``,
    and ``identifier`` — different tree-sitter grammars use different node-type
    names for the same role, and recovery-state ERROR nodes don't always preserve
    the same identifier-kind label the successful parse would carry. The
    prefix-match + name-match-to-child-text pair keeps false positives narrow
    even with the broader child-kind acceptance.
    """
    if lang_key not in _TS_ERROR_CLASS_RECOVERY_LANGS:
        return None
    if str(getattr(node, "type", "") or "") != "ERROR":
        return None
    start = getattr(node, "start_byte", 0)
    end = min(getattr(node, "end_byte", start), start + 512)
    prefix = source_bytes[start:end].decode("utf-8", errors="replace")
    stripped = _TS_ERROR_CLASS_MODIFIER_RE.sub("", prefix, count=8)
    match = _TS_ERROR_CLASS_PREFIX_RE.match(stripped)
    if not match:
        return None
    name = match.group(2)
    # Second gate: the ERROR node must carry an identifier child whose text matches
    # the recovered name. Broad identifier-kind acceptance (type_identifier,
    # simple_identifier, identifier) covers grammar variants and recovery-state
    # node-type relabeling. Name-match-to-child-text replaces the prior
    # type_identifier-presence-only check — that check missed the production case
    # where tree-sitter-swift's recovery emits the identifier as simple_identifier.
    identifier_kinds = ("type_identifier", "simple_identifier", "identifier")
    has_matching_identifier = False
    for child in getattr(node, "named_children", []) or []:
        if str(getattr(child, "type", "") or "") not in identifier_kinds:
            continue
        child_start = getattr(child, "start_byte", 0)
        child_end = getattr(child, "end_byte", child_start)
        child_text = source_bytes[child_start:child_end].decode("utf-8", errors="replace")
        if child_text == name:
            has_matching_identifier = True
            break
    if not has_matching_identifier:
        return None
    return (name, "class")


def _ts_is_import_node(node_type: str, mode: str) -> bool:
    lower = node_type.lower()
    if mode == "markup":
        return any(token in lower for token in ("script", "style", "link", "include", "import", "resource"))
    if mode == "sql":
        # Wave 1p9qi (1p9qd): SQL never emits `imports` edges anymore — table
        # references are clause-aware `reads`/`writes` edges from the
        # structured statement analysis. The substring match here was too
        # broad by construction (`object_reference` matched "reference",
        # `keyword_from` matched "from") — 1p9qc finding (c).
        return False
    if mode == "config":
        return any(token in lower for token in ("include", "import", "source", "path", "file", "template", "script", "command"))
    # Wave 1p4eu: the grammar ROOT node (`source_file` for Rust/Kotlin/Go/Swift/
    # C/…) is NEVER an import, but the `source` import-keyword substring-matches
    # it — so the generic relation fallback regexed the ENTIRE file into junk
    # `external::<token>` import edges (every keyword/identifier on every line:
    # `use`/`pub`/`fn`/`as`/`package`/function names). Java's root (`program`)
    # never matched, which is why only the `source_file` languages were noisy.
    if lower == "source_file":
        return False
    return any(token in lower for token in _TS_IMPORT_KEYWORDS) or "import" in lower or "use" in lower or "include" in lower


def _ts_is_call_node(node_type: str, mode: str, profile: _TsLanguageProfile | None = None) -> bool:
    """Detect tree-sitter call nodes (wave 130ol).

    For code mode with a known per-language profile, consults the explicit
    ``call_node_types`` set. The legacy substring-match heuristic on
    ``"expression"`` matched every ``*_expression`` node type
    (``try_expression``, ``await_expression``, ``binary_expression``, etc.)
    and produced ``external::<keyword>`` edges via the regex-fallback path.
    """
    lower = node_type.lower()
    if mode == "markup":
        return any(token in lower for token in ("script", "style", "form", "link", "anchor", "event", "handler"))
    if mode == "sql":
        # Wave 1p9qi (1p9qd): SQL table references come from the structured
        # statement analysis (clause positions, read/write direction), never
        # from clause-node substring matching + the regex candidate fallback.
        return False
    if mode == "config":
        return any(token in lower for token in ("command", "action", "script", "target", "task", "job", "step", "run"))
    if profile is not None and profile.call_node_types:
        return node_type in profile.call_node_types
    return any(token in lower for token in _TS_CALL_KEYWORDS) or "call" in lower or "invoke" in lower or "access" in lower


def _ts_is_scope_node(node_type: str, kind: str, mode: str) -> bool:
    """Whether a definition node should push a new scope frame.

    Variable bindings (kind ``variable``) are intentionally excluded so calls
    inside ``let x = foo()`` attribute to the enclosing function rather than
    creating a fragile ``…fn.x`` scope that the short-symbol pruning pass
    can silently drop (wave 130ol).
    """
    if mode == "markup":
        return kind in {"module", "class"}
    if mode == "sql":
        return kind in {"module", "class", "function"}
    if mode == "config":
        return kind in {"module", "class", "function"}
    return kind in {"module", "class", "function"}


def _ts_relation_field_names(relation: str, mode: str) -> tuple[str, ...]:
    if relation == "import":
        if mode == "markup":
            return ("src", "href", "action", "path", "target", "name", "value", "file", "module", "resource")
        if mode == "sql":
            return ("name", "table", "view", "schema", "target", "source", "from", "join", "into", "using", "call")
        if mode == "config":
            return ("path", "file", "template", "script", "command", "source", "include", "import", "name", "value")
        return ("module", "path", "source", "name", "value", "alias", "import", "target", "path_specifier")
    if relation == "call":
        if mode == "markup":
            return ("name", "href", "src", "action", "target", "handler", "value", "path")
        if mode == "sql":
            return ("name", "function", "procedure", "target", "source", "table", "view", "schema", "expression", "query")
        if mode == "config":
            return ("name", "command", "action", "task", "job", "step", "script", "target", "value")
        return ("callee", "function", "name", "object", "member", "value", "target", "path", "selector", "method")
    return _TS_NAME_FIELD_PRIORITY


def _ts_candidate_rejected(candidate: str) -> bool:
    """Reject candidates that are language artifacts, not real callees (wave 130ol).

    - ``_`` (Swift underscore wildcard) — produced degenerate paths in code_graph_path
    - ``foo:`` (Swift named-argument label / general label suffix) — not a callable
    - Empty / whitespace-only strings
    """
    if not candidate or not candidate.strip():
        return True
    if candidate == "_":
        return True
    if candidate.endswith(":"):
        return True
    return False


# Node types that wrap a call's argument list — skip these when walking
# named_children for the positional-callee fallback. The callee is the FIRST
# non-argument child of the call expression.
_TS_ARGS_NODE_TYPES = frozenset({
    "call_suffix",            # Swift
    "value_arguments",        # Kotlin
    "argument_list",          # Java, C#, C, C++, Ruby
    "arguments",              # Scala, JS/TS, Python (when via tree-sitter)
    "parameter_list",         # rare grammars
    "parenthesized_expression",  # some grammars wrap args this way
    "trailing_closure",       # Swift trailing closure (not the callee)
    "lambda_literal",         # Kotlin lambda arg
})

# Node types whose text is itself an identifier we can use as a call target.
_TS_IDENTIFIER_TYPES = frozenset({
    "identifier",
    "simple_identifier",
    "type_identifier",
    "name",
    "variable_name",
    "field_identifier",
    "scoped_identifier",
    "shorthand_identifier",
})

# Node types that represent a member-access / navigation chain. For
# ``f.bar()`` the call-expression's callee child is a navigation_expression
# whose RIGHTMOST identifier child (``bar``) is the method name we want as
# the call target.
_TS_NAVIGATION_TYPES = frozenset({
    "navigation_expression",          # Swift
    "navigation_suffix",              # Kotlin (nested)
    "member_access_expression",       # C#
    "member_expression",              # JS/TS
    "field_access",                   # Java
    "field_expression",               # C/C++
    "field_access_expression",        # generic
    "scoped_call_expression",         # PHP
    "qualified_identifier",           # C++ namespace::name
    "selector_expression",            # Go: x.Method
    "method_expression",              # rare
    "binary_expression",              # some grammars treat `a.b` as binary
})


def _ts_extract_callee_recursive(node, source_bytes: bytes) -> str | None:
    """Find the rightmost identifier in a callee expression (wave 130ol).

    For ``f.bar()`` the callee child is a navigation/member-access expression
    whose RIGHTMOST identifier (``bar``) is the method name. For chained
    ``a.b.c()`` we pick ``c``. For a bare ``helper()`` the callee child is
    already a simple identifier — return its text directly.
    """
    if node.type in _TS_IDENTIFIER_TYPES:
        text = _ts_node_text(node, source_bytes)
        return text if text and not _ts_candidate_rejected(text) else None
    if node.type in _TS_NAVIGATION_TYPES:
        # Prefer the rightmost identifier — that's the method/property name.
        children = list(node.named_children)
        for child in reversed(children):
            result = _ts_extract_callee_recursive(child, source_bytes)
            if result:
                return result
        return None
    # Unknown structure — try named children in order and pick the first
    # identifier-like result. Cheap best-effort.
    for child in node.named_children:
        result = _ts_extract_callee_recursive(child, source_bytes)
        if result:
            return result
    return None


# =============================================================================
# Java receiver-type resolution (wave 13129 — 1312l).
#
# Source of truth — graph_indexer.py owns these helpers; server_impl.py's
# code_callhierarchy defense-in-depth filter (for cached pre-bump graphs)
# imports them via `_load_script("graph_indexer")` rather than duplicating.
# Single implementation; no drift risk.
#
# The resolver must short-circuit on first uncertain branch (wave 13129 council
# action item: performance-reviewer). It returns None as soon as the receiver
# expression can't be classified into one of the three handled cases (this/bare,
# simple identifier, ClassName static).
# =============================================================================


def _extract_simple_java_type_name(type_node, source_bytes: bytes) -> str | None:
    """Extract the simple class name from a Java type AST node."""
    n_type = getattr(type_node, "type", "")
    if n_type == "type_identifier":
        return source_bytes[type_node.start_byte:type_node.end_byte].decode("utf-8", errors="replace")
    if n_type == "generic_type":
        for child in (getattr(type_node, "children", []) or []):
            if getattr(child, "type", "") in ("type_identifier", "scoped_type_identifier"):
                return _extract_simple_java_type_name(child, source_bytes)
        return None
    if n_type == "scoped_type_identifier":
        last_name = None
        for child in (getattr(type_node, "children", []) or []):
            if getattr(child, "type", "") == "type_identifier":
                last_name = child
        if last_name is not None:
            return source_bytes[last_name.start_byte:last_name.end_byte].decode("utf-8", errors="replace")
        return None
    if n_type == "array_type":
        elem = type_node.child_by_field_name("element")
        if elem is not None:
            return _extract_simple_java_type_name(elem, source_bytes)
        return None
    return None


# Wave 1p9qh (1p9qb): declared-package extraction for Java/Kotlin files.
# Mirrors the package-collapse mechanism's patterns in
# `graph_query._DIRECTORY_AGG_LANGUAGES` (Java requires the trailing `;`,
# Kotlin's is optional) — keep the two sites in sync. The parsed declaration
# is stored as `declared_package` on the file's module node so the
# same-package disambiguation tier keys on the LANGUAGE FACT (the declared
# package) rather than directory layout, consistent with the C#
# declared-namespace stance.
_JAVA_PKG_DECL_RE = re.compile(r"^\s*package\s+([A-Za-z_][\w.]*)\s*;", re.MULTILINE)
_KOTLIN_PKG_DECL_RE = re.compile(r"^\s*package\s+([A-Za-z_][\w.]*)", re.MULTILINE)


def _find_enclosing_java_class_node(node):
    """Walk up the AST to the nearest enclosing ``class_declaration`` node.

    Wave 1p9qh (1p9qb): node-returning sibling of
    ``_find_enclosing_java_class_name`` — the ``this.<field>`` receiver branch
    needs the class NODE to run a field-declaration-only search against its
    body.
    """
    cur = getattr(node, "parent", None)
    while cur is not None:
        if getattr(cur, "type", "") == "class_declaration":
            return cur
        cur = getattr(cur, "parent", None)
    return None


def _find_enclosing_java_class_name(node, source_bytes: bytes) -> str | None:
    """Walk up the AST to the enclosing class_declaration's name."""
    cur = _find_enclosing_java_class_node(node)
    if cur is not None:
        name_node = cur.child_by_field_name("name")
        if name_node is not None:
            return source_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace")
    return None


def _search_java_declarations_in_scope(scope_node, name: str, source_bytes: bytes) -> str | None:
    """Search descendants of scope_node for a matching variable/parameter/field declaration."""
    stack = [scope_node]
    while stack:
        n = stack.pop()
        n_type = getattr(n, "type", "")
        if n_type in ("local_variable_declaration", "field_declaration"):
            type_node = n.child_by_field_name("type")
            for child in (getattr(n, "children", []) or []):
                if getattr(child, "type", "") == "variable_declarator":
                    name_node = child.child_by_field_name("name")
                    if name_node is not None and type_node is not None:
                        var_name = source_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace")
                        if var_name == name:
                            return _extract_simple_java_type_name(type_node, source_bytes)
        elif n_type == "formal_parameter":
            type_node = n.child_by_field_name("type")
            name_node = n.child_by_field_name("name")
            if name_node is not None and type_node is not None:
                param_name = source_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace")
                if param_name == name:
                    return _extract_simple_java_type_name(type_node, source_bytes)
        # Don't descend into nested method/class bodies — they're separate scopes.
        if n_type in ("method_declaration", "constructor_declaration", "class_declaration") and n is not scope_node:
            continue
        stack.extend(reversed(getattr(n, "children", []) or []))
    return None


def _search_java_field_declarations(class_node, name: str, source_bytes: bytes) -> str | None:
    """Declared type of field ``name`` among ``class_node``'s DIRECT field declarations.

    Wave 1p9qh (1p9qb): the lookup for ``this.<field>`` receivers. Consults
    ``field_declaration`` members of the class body ONLY — never locals or
    parameters — mirroring Java semantics: ``this.f`` always denotes the
    field, explicitly bypassing any local/parameter shadow. Direct class-body
    members only (no descent), so a local inside an instance-initializer
    block can never divert the lookup either. Returns None when the field is
    not declared here (e.g. inherited) — the receiver stays uncertain per the
    false-positive bias.
    """
    body = class_node.child_by_field_name("body") if class_node is not None else None
    for member in (getattr(body, "named_children", []) or []):
        if getattr(member, "type", "") != "field_declaration":
            continue
        type_node = member.child_by_field_name("type")
        if type_node is None:
            continue
        for child in (getattr(member, "children", []) or []):
            if getattr(child, "type", "") == "variable_declarator":
                name_node = child.child_by_field_name("name")
                if name_node is not None:
                    var_name = source_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace")
                    if var_name == name:
                        return _extract_simple_java_type_name(type_node, source_bytes)
    return None


def _resolve_java_identifier_type(name: str, ref_node, source_bytes: bytes) -> str | None:
    """Resolve a Java identifier to its declared simple type name.

    Short-circuits on first uncertain branch per wave 13129 performance-reviewer
    action item.
    """
    cur = getattr(ref_node, "parent", None)
    while cur is not None:
        cur_type = getattr(cur, "type", "")
        if cur_type in ("method_declaration", "constructor_declaration", "class_declaration"):
            resolved = _search_java_declarations_in_scope(cur, name, source_bytes)
            if resolved is not None:
                return resolved
            if cur_type == "class_declaration":
                break
        cur = getattr(cur, "parent", None)
    if name and name[:1].isupper():
        return name
    return None


def _resolve_java_receiver_type(invocation_node, source_bytes: bytes) -> str | None:
    """Resolve the simple type name of a Java method_invocation's receiver.

    Returns the simple class name when resolvable, or None when uncertain
    (preserve the candidate per false-positive bias). Per wave 13129 council
    action item (performance-reviewer), short-circuits as soon as the receiver
    expression can't be classified — no exhaustive scope walks past the first
    identifiable ambiguity.
    """
    if invocation_node is None or getattr(invocation_node, "type", "") != "method_invocation":
        return None
    obj = invocation_node.child_by_field_name("object")
    if obj is None:
        return _find_enclosing_java_class_name(invocation_node, source_bytes)
    obj_type = getattr(obj, "type", "")
    if obj_type == "this":
        return _find_enclosing_java_class_name(invocation_node, source_bytes)
    if obj_type == "super":
        return None  # uncertain — defer inheritance walk
    if obj_type == "identifier":
        ident_text = source_bytes[obj.start_byte:obj.end_byte].decode("utf-8", errors="replace")
        return _resolve_java_identifier_type(ident_text, invocation_node, source_bytes)
    if obj_type == "field_access":
        # Wave 1p9qh (1p9qb): single-segment field receivers — `this.repo.save()`
        # and `Enclosing.STATIC_FIELD.m()` (static field via the enclosing class
        # name). The field's DECLARED type is an explicit in-file fact, exactly
        # the guarantee the bare-identifier path rides on, so the bind carries
        # identical confidence. Lookup is field-declaration-ONLY (`this.`
        # bypasses local/param shadows by Java semantics — see
        # `_search_java_field_declarations`). Deeper chains (`this.a.b.m()`)
        # and non-`this` objects require intermediate-type inference — a
        # different risk class — and stay uncertain (documented give-up).
        inner_obj = obj.child_by_field_name("object")
        field_node = obj.child_by_field_name("field")
        if inner_obj is not None and getattr(field_node, "type", "") == "identifier":
            inner_type = getattr(inner_obj, "type", "")
            qualifies = inner_type == "this"
            if not qualifies and inner_type == "identifier":
                ident_text = source_bytes[inner_obj.start_byte:inner_obj.end_byte].decode("utf-8", errors="replace")
                qualifies = bool(ident_text) and ident_text == _find_enclosing_java_class_name(invocation_node, source_bytes)
            if qualifies:
                cls_node = _find_enclosing_java_class_node(invocation_node)
                if cls_node is not None:
                    field_name = source_bytes[field_node.start_byte:field_node.end_byte].decode("utf-8", errors="replace")
                    return _search_java_field_declarations(cls_node, field_name, source_bytes)
        return None
    # cast_expression, method_invocation chains, lambdas → uncertain.
    return None


def _java_import_facts(import_node, source_bytes: bytes) -> tuple[str, bool, bool] | None:
    """Wave 1p9qh (1p9q9): structured parse of a Java ``import_declaration``.

    Returns ``(fqn, is_static, is_wildcard)`` or None when the node carries no
    name (defensive). The tree-sitter Java grammar fully structures the node:
    the ``static`` modifier is an anonymous ``static`` token child, the trailing
    ``.*`` is a NAMED ``asterisk`` child, and the dotted name is the first
    ``scoped_identifier``/``identifier`` named child (verified 2026-07-04):

      import com.foo.Bar;           -> ("com.foo.Bar", False, False)
      import com.foo.*;             -> ("com.foo", False, True)
      import static com.foo.Bar.baz;-> ("com.foo.Bar.baz", True, False)
      import static com.foo.Bar.*;  -> ("com.foo.Bar", True, True)

    Replaces the generic regex fallback for Java imports, which truncated the
    wildcard form at the asterisk (`com.foo.` — a useless trailing-dot token)
    and emitted the bare `static` keyword as a spurious import candidate.
    """
    is_static = any(
        getattr(c, "type", "") == "static"
        for c in (getattr(import_node, "children", []) or [])
    )
    is_wildcard = False
    name_node = None
    for child in (getattr(import_node, "named_children", []) or []):
        c_type = getattr(child, "type", "")
        if c_type == "asterisk":
            is_wildcard = True
        elif name_node is None and c_type in ("scoped_identifier", "identifier"):
            name_node = child
    if name_node is None:
        return None
    fqn = source_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace")
    fqn = re.sub(r"\s+", "", fqn)  # normalize `com . foo . Bar` formatting oddities
    if not fqn:
        return None
    return fqn, is_static, is_wildcard


# =============================================================================
# Inheritance extraction (wave 1p9qh / 1p9qa) — Java + C# `extends`/`implements`.
#
# Declaration-derived supertype facts join the relation vocabulary as
# `extends` (class → superclass; interface → extended interfaces) and
# `implements` (class/enum/record/struct → interface). Targets resolve through
# the SAME import/unique-candidate machinery as calls edges (including the
# 1p9q9 wildcard-import facts); an unresolved supertype stays
# `external::<Name>` qualified exactly as declared — never dropped, never
# guessed. Inherited-method and `super.`/`base.` call binding runs as a
# finalize OUTPUT pass (see `_apply_inheritance_output_passes`).
# =============================================================================

# Relations forming the inheritance sub-graph. Language-neutral by design —
# only Java and C# emit them today (Kotlin deferred: its supertype syntax
# deserves its own calibration).
_INHERITANCE_RELATIONS = ("extends", "implements")

# Bounded BFS depth (supertype hops from the receiver class) for
# inherited-method resolution. Deep enterprise hierarchies rarely exceed
# 3-4 project-local levels; the cap bounds worst-case walk cost and any
# pathological cycle interaction (visited-set already handles diamonds).
_INHERITANCE_WALK_MAX_DEPTH = 5

# Synthetic external-name prefix marking a Java `super.foo()` / C# `base.Foo()`
# call: `external::super.<EnclosingClass>.<method>`. C# reuses the SAME marker
# (its own reserved word is `base`) so the finalize pass has one handler.
# NOTE (1p9qh red-team F4): the prefix is NOT globally unmintable — Rust
# `use super::…` imports already mint `external::super.*` ids (as `imports`
# edges). The actual safety contract, pinned by test
# (`SuperMarkerCallsInvariantTests`): (a) the finalize inheritance pass
# examines only `calls`-relation edges, so import-minted ids are never
# touched; and (b) every language's CALLS extraction independently refuses
# `super` receivers (Java/C# emit this marker; Kotlin/Scala/Swift/TS/JS
# return None), so the only `calls` targets carrying the prefix are these
# markers. Phase-1 cross-file resolution passes them through untouched —
# only the finalize inheritance pass may bind them.
_SUPER_CALL_PREFIX = "super."

# Wave 1p9qh adversarial fix (F1). Synthetic external-name prefix marking a
# Java bare call that a static-import fact would bind while the enclosing
# class ALSO has a supertype clause:
#
#   external::staticorinherited#<EnclosingClass>.<method>#<Class.member>
#
# (the segment after the LAST `#` is the deferred static-import claim).
# JLS 6.4.1: members in class scope INCLUDING INHERITED ones shadow
# single-static and static-on-demand imports — but whether a supertype
# defines the member is a cross-file fact unavailable at extraction time,
# so the claim is deferred and the finalize inheritance pass arbitrates
# (`_arbitrate_static_or_inherited`: inherited definer wins; multi-definer
# refuses; no definer → the static claim stands).
#
# RESERVED / UNMINTABLE INVARIANT: the `#` separator cannot appear in an
# identifier of any indexed language, and every other emitter builds `calls`
# targets from identifier/AST text — so no source construct in any language
# can mint a target matching this prefix. (A Java class literally named
# `staticorinherited` yields `external::staticorinherited.<m>`, which does
# NOT match the `#`-terminated prefix.) The invariant is pinned by test.
#
# Phase-1 cross-file resolution passes these through untouched — and unlike
# the `super.` marker, the finalize pass rewrites every emitter-mintable
# marker (bind inherited / refuse / claim stands), so none appears in an
# output payload; malformed lookalikes pass through untouched (unmintable,
# invariant-tested).
_STATIC_OR_INHERITED_PREFIX = "staticorinherited#"
_STATIC_OR_INHERITED_SEP = "#"


def _java_supertype_name(type_node, source_bytes: bytes) -> str | None:
    """Raw supertype name from a Java type node in a supertype clause.

    Dotted paths are PRESERVED (`extends com.foo.Base` emits the qualified
    name as declared); generic arguments are stripped to the raw type
    (`extends Base<Foo>` → `Base`). Returns None for shapes that are not
    plain named types (never guessed).
    """
    n_type = getattr(type_node, "type", "")
    if n_type == "type_identifier":
        return source_bytes[type_node.start_byte:type_node.end_byte].decode("utf-8", errors="replace") or None
    if n_type == "scoped_type_identifier":
        text = source_bytes[type_node.start_byte:type_node.end_byte].decode("utf-8", errors="replace")
        return re.sub(r"\s+", "", text) or None
    if n_type == "generic_type":
        for child in (getattr(type_node, "named_children", []) or []):
            if getattr(child, "type", "") in ("type_identifier", "scoped_type_identifier"):
                return _java_supertype_name(child, source_bytes)
    return None


def _java_supertype_facts(decl_node, source_bytes: bytes) -> list[tuple[str, str]]:
    """(supertype_name, relation) facts from a Java type declaration node.

    Grammar shapes (probed against tree-sitter-java, 2026-07-04):

      class_declaration     → `superclass` ("extends" _type)          → extends
                              `super_interfaces` ("implements" type_list) → implements
      interface_declaration → `extends_interfaces` ("extends" type_list)  → extends
      enum_declaration      → `super_interfaces`                       → implements
      record_declaration    → `super_interfaces`                       → implements
    """
    facts: list[tuple[str, str]] = []
    for child in (getattr(decl_node, "named_children", []) or []):
        c_type = getattr(child, "type", "")
        if c_type == "superclass":
            relation = "extends"
            type_nodes = list(getattr(child, "named_children", []) or [])
        elif c_type in ("super_interfaces", "extends_interfaces"):
            relation = "extends" if c_type == "extends_interfaces" else "implements"
            type_nodes = []
            for tl in (getattr(child, "named_children", []) or []):
                if getattr(tl, "type", "") == "type_list":
                    type_nodes = list(getattr(tl, "named_children", []) or [])
                    break
        else:
            continue
        for t in type_nodes:
            name = _java_supertype_name(t, source_bytes)
            if name:
                facts.append((name, relation))
    return facts


def _java_enclosing_has_supertype_clause(node) -> bool:
    """True when the nearest enclosing ``class_declaration`` carries any
    supertype clause (``superclass`` / ``super_interfaces``).

    Wave 1p9qh adversarial fix (F1): gates the static-or-inherited deferred
    marker. A class with no supertype clause cannot have inherited members
    shadowing a static import (JLS 6.4.1), so extraction-time static binds
    stay direct for it — no marker, no behavior change. Scoped to
    ``class_declaration`` exactly like ``_find_enclosing_java_class_name``
    (which supplies the marker's enclosing-class segment): declarations that
    helper cannot name never reach the marker path in the first place.
    """
    cls_node = _find_enclosing_java_class_node(node)
    if cls_node is None:
        return False
    for child in (getattr(cls_node, "named_children", []) or []):
        if getattr(child, "type", "") in ("superclass", "super_interfaces"):
            return True
    return False


# =============================================================================
# Kotlin receiver-type resolution (wave 13194).
#
# Mirrors the Java helpers. Conservative coverage: this/super/bare,
# explicit type annotations (`val foo: Foo = ...`), simple identifiers, and
# `ClassName.method()` static-style. Deferred: var-typed locals with type
# inference, nullable receivers (`foo?.bar()`), extension functions, lambdas.
# Uncertain cases return None (false-positive bias preserved).
# =============================================================================


def _extract_simple_kotlin_type_name(type_node, source_bytes: bytes) -> str | None:
    """Extract simple class name from a Kotlin type AST node.

    Verified Kotlin grammar (2026-06-01):
    - ``user_type`` wraps a child of type ``identifier`` (not ``type_identifier``).
    - ``nullable_type`` wraps a ``user_type``.
    """
    n_type = getattr(type_node, "type", "")
    if n_type == "user_type":
        # Kotlin user_type wraps an `identifier` child carrying the type name.
        for child in (getattr(type_node, "children", []) or []):
            if getattr(child, "type", "") in ("identifier", "type_identifier"):
                return source_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="replace")
        return None
    if n_type == "type_identifier":
        return source_bytes[type_node.start_byte:type_node.end_byte].decode("utf-8", errors="replace")
    if n_type == "nullable_type":
        for child in (getattr(type_node, "children", []) or []):
            if getattr(child, "type", "") in ("user_type", "type_identifier"):
                return _extract_simple_kotlin_type_name(child, source_bytes)
        return None
    return None


def _find_enclosing_kotlin_class_name(node, source_bytes: bytes) -> str | None:
    """Walk up to the enclosing Kotlin class_declaration / object_declaration."""
    cur = getattr(node, "parent", None)
    while cur is not None:
        if getattr(cur, "type", "") in ("class_declaration", "object_declaration", "interface_declaration"):
            # Kotlin class declaration: first child is `class` / `object`,
            # then `type_identifier` (the name).
            for child in (getattr(cur, "children", []) or []):
                if getattr(child, "type", "") == "type_identifier":
                    return source_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="replace")
            return None
        cur = getattr(cur, "parent", None)
    return None


def _search_kotlin_declarations_in_scope(scope_node, name: str, source_bytes: bytes) -> str | None:
    """Search Kotlin scope for `val name: Type = ...` or function parameter.

    Kotlin tree-sitter grammar uses plain `identifier` for binding names and
    type names — NOT `simple_identifier` (which is reserved for other contexts).
    Verified by AST inspection 2026-06-01.
    """
    stack = [scope_node]
    while stack:
        n = stack.pop()
        n_type = getattr(n, "type", "")
        if n_type == "property_declaration":
            # Kotlin: `val name: Type = value` — variable_declaration child holds
            # `identifier <name>` + `:` + `user_type <Type>`.
            for child in (getattr(n, "children", []) or []):
                if getattr(child, "type", "") == "variable_declaration":
                    name_child = None
                    type_child = None
                    for gc in (getattr(child, "children", []) or []):
                        gc_type = getattr(gc, "type", "")
                        if gc_type == "identifier" and name_child is None:
                            name_child = gc
                        elif gc_type in ("user_type", "type_identifier", "nullable_type"):
                            type_child = gc
                    if name_child is not None and type_child is not None:
                        var_name = source_bytes[name_child.start_byte:name_child.end_byte].decode("utf-8", errors="replace")
                        if var_name == name:
                            return _extract_simple_kotlin_type_name(type_child, source_bytes)
        elif n_type == "parameter":
            # Kotlin: `fun foo(name: Type)` — parameter has identifier + user_type.
            name_child = None
            type_child = None
            for child in (getattr(n, "children", []) or []):
                ct = getattr(child, "type", "")
                if ct == "identifier" and name_child is None:
                    name_child = child
                elif ct in ("user_type", "type_identifier", "nullable_type"):
                    type_child = child
            if name_child is not None and type_child is not None:
                param_name = source_bytes[name_child.start_byte:name_child.end_byte].decode("utf-8", errors="replace")
                if param_name == name:
                    return _extract_simple_kotlin_type_name(type_child, source_bytes)
        # Don't recurse into nested function / class bodies.
        if n_type in ("function_declaration", "class_declaration", "object_declaration", "interface_declaration") and n is not scope_node:
            continue
        stack.extend(reversed(getattr(n, "children", []) or []))
    return None


def _resolve_kotlin_identifier_type(name: str, ref_node, source_bytes: bytes) -> str | None:
    """Resolve a Kotlin identifier to its declared simple type name."""
    cur = getattr(ref_node, "parent", None)
    while cur is not None:
        cur_type = getattr(cur, "type", "")
        if cur_type in ("function_declaration", "class_declaration", "object_declaration", "interface_declaration"):
            resolved = _search_kotlin_declarations_in_scope(cur, name, source_bytes)
            if resolved is not None:
                return resolved
            if cur_type in ("class_declaration", "object_declaration", "interface_declaration"):
                break
        cur = getattr(cur, "parent", None)
    if name and name[:1].isupper():
        return name
    return None


def _resolve_kotlin_receiver_type(call_node, source_bytes: bytes) -> str | None:
    """Resolve the simple type name of a Kotlin call_expression's receiver.

    Kotlin tree-sitter grammar shape (verified 2026-06-01):
    - Bare call `bar()`: call_expression has child `identifier "bar"` + `value_arguments`.
    - Member call `foo.bar()`: call_expression has child `navigation_expression`
      (children: `identifier "foo"` + `.` + `identifier "bar"`) + `value_arguments`.
    """
    if call_node is None or getattr(call_node, "type", "") != "call_expression":
        return None
    children = list(getattr(call_node, "children", []) or [])
    if not children:
        return None
    callee = children[0]
    callee_type = getattr(callee, "type", "")
    if callee_type == "identifier":
        # Bare call `bar()` → resolves to enclosing class.
        return _find_enclosing_kotlin_class_name(call_node, source_bytes)
    if callee_type == "navigation_expression":
        # Children: identifier (receiver), '.', identifier (method). Take the
        # first identifier as the receiver.
        nav_children = list(getattr(callee, "children", []) or [])
        receiver = next(
            (c for c in nav_children if getattr(c, "type", "") == "identifier"),
            None,
        )
        if receiver is None:
            return None
        text = source_bytes[receiver.start_byte:receiver.end_byte].decode("utf-8", errors="replace")
        if text == "this":
            return _find_enclosing_kotlin_class_name(call_node, source_bytes)
        if text == "super":
            return None
        return _resolve_kotlin_identifier_type(text, call_node, source_bytes)
    return None


def _resolve_kotlin_call_target(
    call_node, source_bytes: bytes, symbol_lookup: dict[str, str]
) -> str | None:
    """Resolve a Kotlin call_expression to a graph node id (project or external-qualified)."""
    if call_node is None or getattr(call_node, "type", "") != "call_expression":
        return None
    method_name: str | None = None
    children = list(getattr(call_node, "children", []) or [])
    if not children:
        return None
    callee = children[0]
    callee_type = getattr(callee, "type", "")
    if callee_type == "identifier":
        method_name = source_bytes[callee.start_byte:callee.end_byte].decode("utf-8", errors="replace")
    elif callee_type == "navigation_expression":
        # For `foo.bar()`, the method name is the LAST identifier in the
        # navigation_expression (after the `.`).
        nav_children = list(getattr(callee, "children", []) or [])
        identifiers = [c for c in nav_children if getattr(c, "type", "") == "identifier"]
        if len(identifiers) >= 2:
            method_node = identifiers[-1]
            method_name = source_bytes[method_node.start_byte:method_node.end_byte].decode("utf-8", errors="replace")
    if not method_name:
        return None
    receiver_type = _resolve_kotlin_receiver_type(call_node, source_bytes)
    if receiver_type is None:
        return None
    qualified = f"{receiver_type}.{method_name}"
    if qualified in symbol_lookup:
        return symbol_lookup[qualified]
    return f"external::{receiver_type}.{method_name}"


# =============================================================================
# C# receiver-type resolution (wave 13194).
# Mirrors Java; AST node names differ (`invocation_expression`,
# `member_access_expression`, etc.).
# =============================================================================


def _extract_simple_csharp_type_name(type_node, source_bytes: bytes) -> str | None:
    n_type = getattr(type_node, "type", "")
    if n_type == "identifier":
        return source_bytes[type_node.start_byte:type_node.end_byte].decode("utf-8", errors="replace")
    if n_type == "predefined_type":
        return source_bytes[type_node.start_byte:type_node.end_byte].decode("utf-8", errors="replace")
    if n_type == "qualified_name":
        # `System.IO.Stream` → take the last identifier (`Stream`).
        last_ident = None
        for child in (getattr(type_node, "children", []) or []):
            if getattr(child, "type", "") == "identifier":
                last_ident = child
        if last_ident is not None:
            return source_bytes[last_ident.start_byte:last_ident.end_byte].decode("utf-8", errors="replace")
        return None
    if n_type == "generic_name":
        for child in (getattr(type_node, "children", []) or []):
            if getattr(child, "type", "") == "identifier":
                return source_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="replace")
        return None
    if n_type == "nullable_type":
        for child in (getattr(type_node, "children", []) or []):
            t = getattr(child, "type", "")
            if t in ("identifier", "predefined_type", "qualified_name", "generic_name"):
                return _extract_simple_csharp_type_name(child, source_bytes)
        return None
    if n_type == "array_type":
        for child in (getattr(type_node, "children", []) or []):
            t = getattr(child, "type", "")
            if t in ("identifier", "predefined_type", "qualified_name", "generic_name"):
                return _extract_simple_csharp_type_name(child, source_bytes)
        return None
    return None


def _find_enclosing_csharp_class_name(node, source_bytes: bytes) -> str | None:
    cur = getattr(node, "parent", None)
    while cur is not None:
        if getattr(cur, "type", "") in ("class_declaration", "struct_declaration", "interface_declaration", "record_declaration"):
            for child in (getattr(cur, "children", []) or []):
                if getattr(child, "type", "") == "identifier":
                    return source_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="replace")
            return None
        cur = getattr(cur, "parent", None)
    return None


def _search_csharp_declarations_in_scope(scope_node, name: str, source_bytes: bytes) -> str | None:
    stack = [scope_node]
    while stack:
        n = stack.pop()
        n_type = getattr(n, "type", "")
        # Field declaration: `Type field;` or `Type field = value;`
        if n_type in ("field_declaration", "local_declaration_statement"):
            for child in (getattr(n, "children", []) or []):
                if getattr(child, "type", "") == "variable_declaration":
                    # variable_declaration has type child + variable_declarator children.
                    type_child = None
                    declarator = None
                    for gc in (getattr(child, "children", []) or []):
                        gc_type = getattr(gc, "type", "")
                        if gc_type in ("identifier", "predefined_type", "qualified_name", "generic_name", "nullable_type", "array_type") and type_child is None:
                            type_child = gc
                        elif gc_type == "variable_declarator":
                            declarator = gc
                    if type_child is not None and declarator is not None:
                        for dc in (getattr(declarator, "children", []) or []):
                            if getattr(dc, "type", "") == "identifier":
                                var_name = source_bytes[dc.start_byte:dc.end_byte].decode("utf-8", errors="replace")
                                if var_name == name:
                                    return _extract_simple_csharp_type_name(type_child, source_bytes)
        elif n_type == "parameter":
            # C# parameter: `Type name` — type child + identifier.
            type_child = None
            name_child = None
            for child in (getattr(n, "children", []) or []):
                ct = getattr(child, "type", "")
                if ct in ("identifier", "predefined_type", "qualified_name", "generic_name", "nullable_type", "array_type") and type_child is None:
                    type_child = child
                elif ct == "identifier" and type_child is not None:
                    name_child = child
            if type_child is not None and name_child is not None:
                param_name = source_bytes[name_child.start_byte:name_child.end_byte].decode("utf-8", errors="replace")
                if param_name == name:
                    return _extract_simple_csharp_type_name(type_child, source_bytes)
        # Don't recurse into nested method / class bodies.
        if n_type in ("method_declaration", "constructor_declaration", "class_declaration",
                      "struct_declaration", "interface_declaration", "record_declaration") and n is not scope_node:
            continue
        stack.extend(reversed(getattr(n, "children", []) or []))
    return None


def _resolve_csharp_identifier_type(name: str, ref_node, source_bytes: bytes) -> str | None:
    cur = getattr(ref_node, "parent", None)
    while cur is not None:
        cur_type = getattr(cur, "type", "")
        if cur_type in ("method_declaration", "constructor_declaration", "class_declaration",
                        "struct_declaration", "interface_declaration", "record_declaration"):
            resolved = _search_csharp_declarations_in_scope(cur, name, source_bytes)
            if resolved is not None:
                return resolved
            if cur_type in ("class_declaration", "struct_declaration", "interface_declaration", "record_declaration"):
                break
        cur = getattr(cur, "parent", None)
    if name and name[:1].isupper():
        return name
    return None


def _resolve_csharp_receiver_type(invocation_node, source_bytes: bytes) -> str | None:
    """Resolve the simple type name of a C# invocation_expression's receiver.

    C# AST shape: `invocation_expression` with first child being the callee
    (`member_access_expression` for `receiver.Method()` or `identifier` for
    bare `Method()`).
    """
    if invocation_node is None or getattr(invocation_node, "type", "") != "invocation_expression":
        return None
    children = list(getattr(invocation_node, "children", []) or [])
    if not children:
        return None
    callee = children[0]
    callee_type = getattr(callee, "type", "")
    if callee_type == "identifier":
        # Bare call → enclosing class.
        return _find_enclosing_csharp_class_name(invocation_node, source_bytes)
    if callee_type == "member_access_expression":
        # member_access_expression has receiver + identifier (method name).
        ma_children = list(getattr(callee, "children", []) or [])
        if not ma_children:
            return None
        receiver = ma_children[0]
        receiver_type = getattr(receiver, "type", "")
        if receiver_type == "identifier":
            text = source_bytes[receiver.start_byte:receiver.end_byte].decode("utf-8", errors="replace")
            if text == "this":
                return _find_enclosing_csharp_class_name(invocation_node, source_bytes)
            if text == "base":
                return None  # defer inheritance walk
            return _resolve_csharp_identifier_type(text, invocation_node, source_bytes)
    return None


def _resolve_csharp_call_target(
    invocation_node, source_bytes: bytes, symbol_lookup: dict[str, str]
) -> str | None:
    if invocation_node is None or getattr(invocation_node, "type", "") != "invocation_expression":
        return None
    method_name: str | None = None
    children = list(getattr(invocation_node, "children", []) or [])
    if not children:
        return None
    callee = children[0]
    callee_type = getattr(callee, "type", "")
    if callee_type == "identifier":
        method_name = source_bytes[callee.start_byte:callee.end_byte].decode("utf-8", errors="replace")
    elif callee_type == "member_access_expression":
        ma_children = list(getattr(callee, "children", []) or [])
        # Last identifier in member_access_expression is the method name.
        for child in reversed(ma_children):
            if getattr(child, "type", "") == "identifier":
                method_name = source_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="replace")
                break
        # Wave 1p9qh (1p9qa): `base.Foo()` — C#'s super-call form. The
        # receiver node type is the anonymous `base` keyword token (probed
        # 2026-07-04; it is NOT an identifier, so the identifier branch in
        # `_resolve_csharp_receiver_type` never sees it). Emit the shared
        # reserved-prefix marker so the finalize inheritance pass resolves it
        # via the enclosing class's single project-resolved `extends` target.
        if (
            method_name
            and ma_children
            and getattr(ma_children[0], "type", "") == "base"
        ):
            enclosing = _find_enclosing_csharp_class_name(invocation_node, source_bytes)
            if enclosing:
                return f"external::{_SUPER_CALL_PREFIX}{enclosing}.{method_name}"
            return None
    if not method_name:
        return None
    receiver_type = _resolve_csharp_receiver_type(invocation_node, source_bytes)
    if receiver_type is None:
        return None
    qualified = f"{receiver_type}.{method_name}"
    if qualified in symbol_lookup:
        return symbol_lookup[qualified]
    return f"external::{receiver_type}.{method_name}"


def _csharp_supertype_name(type_node, source_bytes: bytes) -> str | None:
    """Raw base name from a C# `base_list` entry.

    `qualified_name` is preserved dotted (emit qualified as declared); a
    `generic_name` strips to the raw identifier; `predefined_type` is
    rejected — an enum's underlying-type clause (`enum E : byte`) is a
    storage declaration, not inheritance.
    """
    n_type = getattr(type_node, "type", "")
    if n_type == "identifier":
        return source_bytes[type_node.start_byte:type_node.end_byte].decode("utf-8", errors="replace") or None
    if n_type == "qualified_name":
        text = source_bytes[type_node.start_byte:type_node.end_byte].decode("utf-8", errors="replace")
        text = re.sub(r"\s+", "", text)
        if "<" in text:  # generic tail on a qualified name (`Foo.Bar<T>`)
            text = text.split("<", 1)[0].rstrip(".")
        return text or None
    if n_type == "generic_name":
        for child in (getattr(type_node, "named_children", []) or []):
            if getattr(child, "type", "") == "identifier":
                return source_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="replace") or None
    return None


def _csharp_supertype_facts(decl_node, node_type: str, source_bytes: bytes) -> list[tuple[str, str]]:
    """(base_name, relation) facts from a C# type declaration's `base_list`.

    The C# grammar does NOT structurally distinguish the base class from the
    implemented interfaces — `base_list` is a flat type list. Relation
    assignment uses the language rules that ARE deterministic:

    - interface declarer: bases can only be interfaces → all `extends`
      (interface inheritance).
    - struct declarer: bases can only be interfaces → all `implements`.
    - class/record declarer: C# permits AT MOST ONE base class and requires
      it to be listed FIRST (language rule), so the FIRST base is emitted
      `extends` and the rest `implements`. This positional labeling is the
      convention for UNRESOLVED (`external::`) bases only: a project-resolved
      base gets its true kind-based relation in the finalize output pass
      (a first base resolving to a project interface flips to `implements`),
      and the two relations traverse identically in impact/path, so the
      convention mislabel on a genuinely-external first interface is inert.
    """
    base_list = None
    for child in (getattr(decl_node, "named_children", []) or []):
        if getattr(child, "type", "") == "base_list":
            base_list = child
            break
    if base_list is None:
        return []
    names: list[str] = []
    for t in (getattr(base_list, "named_children", []) or []):
        name = _csharp_supertype_name(t, source_bytes)
        if name:
            names.append(name)
    if node_type == "interface_declaration":
        return [(n, "extends") for n in names]
    if node_type == "struct_declaration":
        return [(n, "implements") for n in names]
    return [(n, "extends" if i == 0 else "implements") for i, n in enumerate(names)]


# =============================================================================
# Go receiver-type resolution (wave 1319a).
# =============================================================================


def _find_enclosing_go_method_receiver_type(node, source_bytes: bytes) -> str | None:
    """Walk up to enclosing method_declaration; return the receiver's type.

    Go method shape: `func (h Helper) Method() {...}` — the first parameter_list
    after `func` is the receiver. We extract its type_identifier.
    """
    cur = getattr(node, "parent", None)
    while cur is not None:
        if getattr(cur, "type", "") == "method_declaration":
            children = list(getattr(cur, "children", []) or [])
            # First parameter_list is the receiver (between func and name).
            for child in children:
                if getattr(child, "type", "") == "parameter_list":
                    pl_children = list(getattr(child, "children", []) or [])
                    for pl_child in pl_children:
                        if getattr(pl_child, "type", "") == "parameter_declaration":
                            for pd_child in (getattr(pl_child, "children", []) or []):
                                if getattr(pd_child, "type", "") in ("type_identifier", "pointer_type"):
                                    # Handle pointer types: `*Helper` wraps type_identifier.
                                    if getattr(pd_child, "type", "") == "pointer_type":
                                        for pc in (getattr(pd_child, "children", []) or []):
                                            if getattr(pc, "type", "") == "type_identifier":
                                                return source_bytes[pc.start_byte:pc.end_byte].decode("utf-8", errors="replace")
                                    else:
                                        return source_bytes[pd_child.start_byte:pd_child.end_byte].decode("utf-8", errors="replace")
                    return None  # parameter_list found but no type
            return None
        cur = getattr(cur, "parent", None)
    return None


def _go_simple_type_name(type_node, source_bytes: bytes) -> str | None:
    """Type name from a Go type node (wave 1p4et; package-preserving since 1p4eq).

    `type_identifier` → itself; `pointer_type` (`*T`) → inner type; `qualified_type`
    (`pkg.Type`) → the PACKAGE-QUALIFIED `pkg.Type`. Returns None for shapes we
    don't model (slices, maps, func types, generics).

    Wave 1p4eq faithfulness fix: a `qualified_type` previously returned only the
    bare trailing `Type`, dropping the package. That collapsed `foo.Helper` and a
    co-located `bar.Helper` to the same `Helper` receiver key, so the 1p4er
    same-directory fallback could bind the caller's OWN-package twin even though
    the source explicitly named a DIFFERENT package — a wrong RECEIVER_RESOLVED
    edge (caught by the 1p4eq adversarial verification). Preserving `pkg.Type`
    lets the cross-file rewrite pass resolve by the candidate's package directory,
    and stay external when no project package matches `pkg`.
    """
    tt = getattr(type_node, "type", "")
    if tt == "type_identifier":
        return source_bytes[type_node.start_byte:type_node.end_byte].decode("utf-8", errors="replace")
    if tt == "pointer_type":
        for c in (getattr(type_node, "children", []) or []):
            inner = _go_simple_type_name(c, source_bytes)
            if inner:
                return inner
    if tt == "qualified_type":
        pkg = None
        typ = None
        for c in (getattr(type_node, "children", []) or []):
            ct = getattr(c, "type", "")
            if ct == "package_identifier" and pkg is None:
                pkg = source_bytes[c.start_byte:c.end_byte].decode("utf-8", errors="replace")
            elif ct == "type_identifier":
                typ = source_bytes[c.start_byte:c.end_byte].decode("utf-8", errors="replace")
        if typ:
            return f"{pkg}.{typ}" if pkg else typ
    return None


def _go_method_node_receiver_type(method_node, source_bytes: bytes) -> str | None:
    """Receiver type of a Go `method_declaration` node directly (wave 1p4et).

    `func (h Helper) M()` / `func (h *Helper) M()` → 'Helper'. The FIRST
    `parameter_list` (between `func` and the name) is the receiver.
    """
    for child in (getattr(method_node, "children", []) or []):
        if getattr(child, "type", "") == "parameter_list":
            for pl_child in (getattr(child, "children", []) or []):
                if getattr(pl_child, "type", "") == "parameter_declaration":
                    for pd_child in (getattr(pl_child, "children", []) or []):
                        if getattr(pd_child, "type", "") in ("type_identifier", "pointer_type", "qualified_type"):
                            return _go_simple_type_name(pd_child, source_bytes)
            return None  # first parameter_list is the receiver; stop
    return None


def _search_go_declarations_in_scope(scope_node, name: str, source_bytes: bytes) -> str | None:
    """Search Go scope for `var name Type` declarations or function parameters."""
    stack = [scope_node]
    while stack:
        n = stack.pop()
        n_type = getattr(n, "type", "")
        if n_type == "var_spec":
            # var_spec: identifier <name> + type_identifier <Type>
            name_child = None
            type_child = None
            for child in (getattr(n, "children", []) or []):
                ct = getattr(child, "type", "")
                if ct == "identifier" and name_child is None:
                    name_child = child
                elif ct in ("type_identifier", "pointer_type", "qualified_type"):
                    type_child = child
            if name_child is not None and type_child is not None:
                var_name = source_bytes[name_child.start_byte:name_child.end_byte].decode("utf-8", errors="replace")
                if var_name == name:
                    # Wave 1p4et: + qualified_type so `var h foo.Helper` infers `Helper`
                    # (the dominant cross-package receiver shape; previously returned None).
                    return _go_simple_type_name(type_child, source_bytes)
        elif n_type == "parameter_declaration":
            # parameter_declaration: identifier <name> + type_identifier <Type>
            name_child = None
            type_child = None
            for child in (getattr(n, "children", []) or []):
                ct = getattr(child, "type", "")
                if ct == "identifier" and name_child is None:
                    name_child = child
                elif ct in ("type_identifier", "pointer_type", "qualified_type"):
                    type_child = child
            if name_child is not None and type_child is not None:
                param_name = source_bytes[name_child.start_byte:name_child.end_byte].decode("utf-8", errors="replace")
                if param_name == name:
                    return _go_simple_type_name(type_child, source_bytes)  # wave 1p4et: + qualified_type
        # Don't descend into nested function bodies.
        if n_type in ("method_declaration", "function_declaration") and n is not scope_node:
            continue
        stack.extend(reversed(getattr(n, "children", []) or []))
    return None


def _resolve_go_identifier_type(name: str, ref_node, source_bytes: bytes) -> str | None:
    """Resolve a Go identifier to its declared simple type name."""
    cur = getattr(ref_node, "parent", None)
    while cur is not None:
        cur_type = getattr(cur, "type", "")
        if cur_type in ("method_declaration", "function_declaration"):
            resolved = _search_go_declarations_in_scope(cur, name, source_bytes)
            if resolved is not None:
                return resolved
            break
        cur = getattr(cur, "parent", None)
    if name and name[:1].isupper():
        # Likely a static-style call to a type (TypeName.Method()).
        return name
    return None


def _resolve_go_receiver_type(call_node, source_bytes: bytes) -> str | None:
    """Resolve Go call_expression receiver type.

    Shape: call_expression → selector_expression (`h.Method`) or identifier (bare).
    """
    if call_node is None or getattr(call_node, "type", "") != "call_expression":
        return None
    children = list(getattr(call_node, "children", []) or [])
    if not children:
        return None
    callee = children[0]
    callee_type = getattr(callee, "type", "")
    if callee_type == "identifier":
        # Bare call → enclosing method's receiver type (Go has no explicit "this").
        return _find_enclosing_go_method_receiver_type(call_node, source_bytes)
    if callee_type == "selector_expression":
        # First child is the receiver identifier.
        nav_children = list(getattr(callee, "children", []) or [])
        if not nav_children:
            return None
        receiver = nav_children[0]
        receiver_type = getattr(receiver, "type", "")
        if receiver_type == "identifier":
            text = source_bytes[receiver.start_byte:receiver.end_byte].decode("utf-8", errors="replace")
            return _resolve_go_identifier_type(text, call_node, source_bytes)
    return None


def _resolve_go_call_target(call_node, source_bytes: bytes, symbol_lookup: dict[str, str]) -> str | None:
    if call_node is None or getattr(call_node, "type", "") != "call_expression":
        return None
    children = list(getattr(call_node, "children", []) or [])
    if not children:
        return None
    callee = children[0]
    callee_type = getattr(callee, "type", "")
    method_name: str | None = None
    if callee_type == "identifier":
        method_name = source_bytes[callee.start_byte:callee.end_byte].decode("utf-8", errors="replace")
    elif callee_type == "selector_expression":
        # The method name is the field_identifier child.
        for child in (getattr(callee, "children", []) or []):
            if getattr(child, "type", "") == "field_identifier":
                method_name = source_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="replace")
                break
    if not method_name:
        return None
    receiver_type = _resolve_go_receiver_type(call_node, source_bytes)
    if receiver_type is None:
        return None
    qualified = f"{receiver_type}.{method_name}"
    if qualified in symbol_lookup:
        return symbol_lookup[qualified]
    return f"external::{receiver_type}.{method_name}"


# =============================================================================
# Rust receiver-type resolution (wave 1319a).
# =============================================================================


def _rust_mod_path_attr(mod_node, source_bytes: bytes) -> str | None:
    """The `#[path = "…"]` file override for a `mod name;` decl, or None (wave 1p9q5).

    The `attribute_item` is a PRECEDING SIBLING of the `mod_item` (not a child).
    Scans back over adjacent attribute siblings for `path = "<literal>"` and
    returns the unquoted literal. Bounded: only a plain string literal is read
    (raw/byte-string/escape edge cases fall to None → the default file-mapping
    rule, never a wrong path).
    """
    sib = getattr(mod_node, "prev_named_sibling", None)
    while sib is not None and getattr(sib, "type", "") == "attribute_item":
        for attr in getattr(sib, "children", []) or []:
            if getattr(attr, "type", "") != "attribute":
                continue
            kids = list(getattr(attr, "children", []) or [])
            has_path = any(
                getattr(c, "type", "") == "identifier"
                and source_bytes[c.start_byte:c.end_byte] == b"path"
                for c in kids
            )
            if not has_path:
                continue
            for c in kids:
                if getattr(c, "type", "") == "string_literal":
                    raw = source_bytes[c.start_byte:c.end_byte].decode("utf-8", "replace").strip()
                    return raw.strip('"') or None
        sib = getattr(sib, "prev_named_sibling", None)
    return None


def _rust_use_imports(use_node, source_bytes: bytes) -> list[tuple[str, str]]:
    """Wave 1p4eu: clean (head, dotted_target) pairs from a Rust `use_declaration`.

    Replaces the generic relation-candidate fallback, which emitted lossy
    `::`-joined paths (`external::crate::services::Helper`) plus `use`/`as`
    keyword-noise edges. Each pair's dotted target's FINAL segment is the
    imported type name (so `imports_by_file`, which keys by the target's last
    segment, is consumable); an `as` alias becomes the head while the target
    keeps the REAL type name (the caller registers the alias in `import_aliases`).

      use crate::services::Helper;            -> [("Helper", "crate.services.Helper")]
      use super::util::{Reader, Writer as W}; -> [("Reader","super.util.Reader"),
                                                  ("W","super.util.Writer")]
      use foo::Bar as Baz;                    -> [("Baz", "foo.Bar")]
      use crate::x::*;                        -> []   (glob — no specific symbol)
    """
    try:
        arg = use_node.child_by_field_name("argument")
    except Exception:
        arg = None
    if arg is None:
        return []
    out: list[tuple[str, str]] = []
    _rust_walk_use_tree(arg, "", source_bytes, out)
    return out


def _rust_walk_use_tree(node, prefix: str, source_bytes: bytes, out: list[tuple[str, str]]) -> None:
    """Recursive helper for `_rust_use_imports` — accumulates (head, target) pairs.

    `prefix` is the accumulated dotted path from any enclosing `scoped_use_list`
    (`use a::b::{...}`), without a trailing dot.
    """
    def _txt(n) -> str:
        return source_bytes[n.start_byte:n.end_byte].decode("utf-8", errors="replace")

    def _dotted(n) -> str:
        return _txt(n).replace("::", ".")

    def _join(p: str, seg: str) -> str:
        return f"{p}.{seg}" if (p and seg) else (p or seg)

    t = getattr(node, "type", "")
    if t == "scoped_identifier":
        name = node.child_by_field_name("name")
        if name is not None:
            out.append((_txt(name), _join(prefix, _dotted(node))))
    elif t == "identifier":
        nm = _txt(node)
        if nm:
            out.append((nm, _join(prefix, nm)))
    elif t == "use_as_clause":
        path = node.child_by_field_name("path")
        alias = node.child_by_field_name("alias")
        if path is not None and alias is not None:
            # head = alias; target keeps the REAL type/path (final segment = type)
            out.append((_txt(alias), _join(prefix, _dotted(path))))
    elif t == "scoped_use_list":
        path = node.child_by_field_name("path")
        lst = node.child_by_field_name("list")
        new_prefix = _join(prefix, _dotted(path)) if path is not None else prefix
        if lst is not None:
            for c in (getattr(lst, "children", []) or []):
                if getattr(c, "type", "") in (
                    "identifier", "scoped_identifier", "use_as_clause", "scoped_use_list",
                ):
                    _rust_walk_use_tree(c, new_prefix, source_bytes, out)
    # use_wildcard (`::*`) and punctuation: skip — no specific imported symbol.


def _find_enclosing_rust_impl_type(node, source_bytes: bytes) -> str | None:
    """Walk up to enclosing impl_item; return its target type."""
    cur = getattr(node, "parent", None)
    while cur is not None:
        if getattr(cur, "type", "") == "impl_item":
            for child in (getattr(cur, "children", []) or []):
                if getattr(child, "type", "") == "type_identifier":
                    return source_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="replace")
            return None
        cur = getattr(cur, "parent", None)
    return None


def _rust_value_type(value_node, source_bytes: bytes) -> str | None:
    """Infer the type of a Rust let-binding value (wave 1p4eu).

    `Bar { .. }` (struct_expression) → 'Bar'; `Bar::new()` / `Type::from()` /
    `Type::with_capacity()` / `Type::default()` (a call to a scoped_identifier
    whose final segment is a constructor-convention name) → the type prefix.
    Anything else → None (conservative — only the syntactically-named-type cases,
    never an inter-procedural return type).
    """
    vt = getattr(value_node, "type", "")
    if vt == "struct_expression":
        for c in (getattr(value_node, "children", []) or []):
            ct = getattr(c, "type", "")
            if ct == "type_identifier":
                return source_bytes[c.start_byte:c.end_byte].decode("utf-8", errors="replace")
            if ct == "scoped_type_identifier":
                last = None
                for cc in (getattr(c, "children", []) or []):
                    if getattr(cc, "type", "") == "type_identifier":
                        last = cc
                if last is not None:
                    return source_bytes[last.start_byte:last.end_byte].decode("utf-8", errors="replace")
        return None
    if vt == "call_expression":
        children = list(getattr(value_node, "children", []) or [])
        callee = children[0] if children else None
        if callee is not None and getattr(callee, "type", "") == "scoped_identifier":
            text = source_bytes[callee.start_byte:callee.end_byte].decode("utf-8", errors="replace")
            parts = text.split("::")
            ctor = parts[-1] if parts else ""
            if (
                len(parts) >= 2
                and parts[-2][:1].isupper()
                and (ctor in ("new", "from", "default") or ctor.startswith("with_"))
            ):
                return parts[-2]
    return None


def _search_rust_declarations_in_scope(scope_node, name: str, source_bytes: bytes) -> str | None:
    """Search Rust scope for `let name: Type = ...` or function parameter."""
    stack = [scope_node]
    while stack:
        n = stack.pop()
        n_type = getattr(n, "type", "")
        if n_type == "let_declaration":
            # let_declaration: let identifier <name> : type_identifier <Type> = ...
            name_child = None
            type_child = None
            for child in (getattr(n, "children", []) or []):
                ct = getattr(child, "type", "")
                if ct == "identifier" and name_child is None:
                    name_child = child
                elif ct == "type_identifier":
                    type_child = child
            if name_child is not None:
                var_name = source_bytes[name_child.start_byte:name_child.end_byte].decode("utf-8", errors="replace")
                if var_name == name:
                    if type_child is not None:
                        return source_bytes[type_child.start_byte:type_child.end_byte].decode("utf-8", errors="replace")
                    # Wave 1p4eu: no explicit annotation — infer from the value
                    # (`let x = Bar{..}` / `let x = Bar::new()`).
                    try:
                        value_node = n.child_by_field_name("value")
                    except Exception:
                        value_node = None
                    if value_node is not None:
                        inferred = _rust_value_type(value_node, source_bytes)
                        if inferred:
                            return inferred
        elif n_type == "parameter":
            # parameter: identifier <name> : type_identifier <Type>
            name_child = None
            type_child = None
            for child in (getattr(n, "children", []) or []):
                ct = getattr(child, "type", "")
                if ct == "identifier" and name_child is None:
                    name_child = child
                elif ct == "type_identifier":
                    type_child = child
            if name_child is not None and type_child is not None:
                param_name = source_bytes[name_child.start_byte:name_child.end_byte].decode("utf-8", errors="replace")
                if param_name == name:
                    return source_bytes[type_child.start_byte:type_child.end_byte].decode("utf-8", errors="replace")
        # Don't descend into nested function bodies.
        if n_type == "function_item" and n is not scope_node:
            continue
        stack.extend(reversed(getattr(n, "children", []) or []))
    return None


def _resolve_rust_identifier_type(name: str, ref_node, source_bytes: bytes) -> str | None:
    cur = getattr(ref_node, "parent", None)
    while cur is not None:
        cur_type = getattr(cur, "type", "")
        if cur_type == "function_item":
            resolved = _search_rust_declarations_in_scope(cur, name, source_bytes)
            if resolved is not None:
                return resolved
            break
        cur = getattr(cur, "parent", None)
    if name and name[:1].isupper():
        return name
    return None


def _resolve_rust_receiver_type(call_node, source_bytes: bytes) -> str | None:
    """Resolve Rust call_expression receiver type.

    Shape: call_expression → field_expression (`h.method`) or identifier (bare).
    """
    if call_node is None or getattr(call_node, "type", "") != "call_expression":
        return None
    children = list(getattr(call_node, "children", []) or [])
    if not children:
        return None
    callee = children[0]
    callee_type = getattr(callee, "type", "")
    if callee_type == "identifier":
        return _find_enclosing_rust_impl_type(call_node, source_bytes)
    if callee_type == "field_expression":
        nav_children = list(getattr(callee, "children", []) or [])
        if not nav_children:
            return None
        receiver = nav_children[0]
        receiver_type = getattr(receiver, "type", "")
        if receiver_type == "self":
            return _find_enclosing_rust_impl_type(call_node, source_bytes)
        if receiver_type == "identifier":
            text = source_bytes[receiver.start_byte:receiver.end_byte].decode("utf-8", errors="replace")
            if text == "self":
                return _find_enclosing_rust_impl_type(call_node, source_bytes)
            return _resolve_rust_identifier_type(text, call_node, source_bytes)
    return None


def _resolve_rust_call_target(call_node, source_bytes: bytes, symbol_lookup: dict[str, str]) -> str | None:
    if call_node is None or getattr(call_node, "type", "") != "call_expression":
        return None
    children = list(getattr(call_node, "children", []) or [])
    if not children:
        return None
    callee = children[0]
    callee_type = getattr(callee, "type", "")
    method_name: str | None = None
    if callee_type == "identifier":
        method_name = source_bytes[callee.start_byte:callee.end_byte].decode("utf-8", errors="replace")
    elif callee_type == "field_expression":
        for child in (getattr(callee, "children", []) or []):
            if getattr(child, "type", "") == "field_identifier":
                method_name = source_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="replace")
                break
    # Wave 1p4eu: associated-function call `Type::assoc_fn()` — callee is a
    # scoped_identifier (`new` is owned by the construction resolver, excluded
    # here). The `::` form is never indexed; emit the DOTTED `external::Type.fn`
    # so the rewrite pass's qualified_index can resolve it cross-file. The
    # PascalCase guard makes a module-fn call like `io::stdin()` fall through to
    # None (stays external) — never mis-keyed as a type method (faithfulness).
    if callee_type == "scoped_identifier":
        _txt = source_bytes[callee.start_byte:callee.end_byte].decode("utf-8", errors="replace")
        _parts = _txt.split("::")
        if len(_parts) >= 2 and _parts[-1] != "new" and _parts[-2][:1].isupper():
            _rt, _fn = _parts[-2], _parts[-1]
            _q = f"{_rt}.{_fn}"
            return symbol_lookup[_q] if _q in symbol_lookup else f"external::{_rt}.{_fn}"
        return None
    if not method_name:
        return None
    receiver_type = _resolve_rust_receiver_type(call_node, source_bytes)
    if receiver_type is None:
        return None
    qualified = f"{receiver_type}.{method_name}"
    if qualified in symbol_lookup:
        return symbol_lookup[qualified]
    return f"external::{receiver_type}.{method_name}"


# =============================================================================
# Scala receiver-type resolution (wave 1319a).
# =============================================================================


def _find_enclosing_scala_class_name(node, source_bytes: bytes) -> str | None:
    cur = getattr(node, "parent", None)
    while cur is not None:
        if getattr(cur, "type", "") in ("class_definition", "object_definition", "trait_definition"):
            for child in (getattr(cur, "children", []) or []):
                if getattr(child, "type", "") == "identifier":
                    return source_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="replace")
            return None
        cur = getattr(cur, "parent", None)
    return None


def _search_scala_declarations_in_scope(scope_node, name: str, source_bytes: bytes) -> str | None:
    """Search Scala scope for `val name: Type = ...` or function parameter."""
    stack = [scope_node]
    while stack:
        n = stack.pop()
        n_type = getattr(n, "type", "")
        if n_type in ("val_definition", "var_definition"):
            name_child = None
            type_child = None
            for child in (getattr(n, "children", []) or []):
                ct = getattr(child, "type", "")
                if ct == "identifier" and name_child is None:
                    name_child = child
                elif ct == "type_identifier":
                    type_child = child
            if name_child is not None and type_child is not None:
                var_name = source_bytes[name_child.start_byte:name_child.end_byte].decode("utf-8", errors="replace")
                if var_name == name:
                    return source_bytes[type_child.start_byte:type_child.end_byte].decode("utf-8", errors="replace")
        elif n_type == "parameter":
            name_child = None
            type_child = None
            for child in (getattr(n, "children", []) or []):
                ct = getattr(child, "type", "")
                if ct == "identifier" and name_child is None:
                    name_child = child
                elif ct == "type_identifier":
                    type_child = child
            if name_child is not None and type_child is not None:
                param_name = source_bytes[name_child.start_byte:name_child.end_byte].decode("utf-8", errors="replace")
                if param_name == name:
                    return source_bytes[type_child.start_byte:type_child.end_byte].decode("utf-8", errors="replace")
        # Don't descend into nested function/class bodies.
        if n_type in ("function_definition", "class_definition", "object_definition", "trait_definition") and n is not scope_node:
            continue
        stack.extend(reversed(getattr(n, "children", []) or []))
    return None


def _resolve_scala_identifier_type(name: str, ref_node, source_bytes: bytes) -> str | None:
    cur = getattr(ref_node, "parent", None)
    while cur is not None:
        cur_type = getattr(cur, "type", "")
        if cur_type in ("function_definition", "class_definition", "object_definition", "trait_definition"):
            resolved = _search_scala_declarations_in_scope(cur, name, source_bytes)
            if resolved is not None:
                return resolved
            if cur_type in ("class_definition", "object_definition", "trait_definition"):
                break
        cur = getattr(cur, "parent", None)
    if name and name[:1].isupper():
        return name
    return None


def _resolve_scala_receiver_type(call_node, source_bytes: bytes) -> str | None:
    """Resolve Scala call_expression receiver type.

    Shape: call_expression → field_expression (`h.process`) or identifier (bare).
    """
    if call_node is None or getattr(call_node, "type", "") != "call_expression":
        return None
    children = list(getattr(call_node, "children", []) or [])
    if not children:
        return None
    callee = children[0]
    callee_type = getattr(callee, "type", "")
    if callee_type == "identifier":
        return _find_enclosing_scala_class_name(call_node, source_bytes)
    if callee_type == "field_expression":
        nav_children = list(getattr(callee, "children", []) or [])
        if not nav_children:
            return None
        receiver = nav_children[0]
        receiver_type = getattr(receiver, "type", "")
        if receiver_type == "identifier":
            text = source_bytes[receiver.start_byte:receiver.end_byte].decode("utf-8", errors="replace")
            if text == "this":
                return _find_enclosing_scala_class_name(call_node, source_bytes)
            if text == "super":
                return None
            return _resolve_scala_identifier_type(text, call_node, source_bytes)
    return None


def _resolve_scala_call_target(call_node, source_bytes: bytes, symbol_lookup: dict[str, str]) -> str | None:
    if call_node is None or getattr(call_node, "type", "") != "call_expression":
        return None
    children = list(getattr(call_node, "children", []) or [])
    if not children:
        return None
    callee = children[0]
    callee_type = getattr(callee, "type", "")
    method_name: str | None = None
    if callee_type == "identifier":
        method_name = source_bytes[callee.start_byte:callee.end_byte].decode("utf-8", errors="replace")
    elif callee_type == "field_expression":
        # Method name is the LAST identifier child (after the `.`).
        identifiers = [c for c in (getattr(callee, "children", []) or []) if getattr(c, "type", "") == "identifier"]
        if len(identifiers) >= 2:
            method_name = source_bytes[identifiers[-1].start_byte:identifiers[-1].end_byte].decode("utf-8", errors="replace")
    if not method_name:
        return None
    receiver_type = _resolve_scala_receiver_type(call_node, source_bytes)
    if receiver_type is None:
        return None
    qualified = f"{receiver_type}.{method_name}"
    if qualified in symbol_lookup:
        return symbol_lookup[qualified]
    return f"external::{receiver_type}.{method_name}"


# =============================================================================
# Swift receiver-type resolution (wave 1319g).
# =============================================================================


def _extract_simple_swift_type_name(type_node, source_bytes: bytes) -> str | None:
    """Extract simple type name from a Swift type AST node.

    Swift grammar shapes (verified 2026-06-01):
    - `user_type` wraps `type_identifier`.
    - `type_annotation` (`: Foo`) wraps `user_type` after the `:` token.
    - `optional_type` wraps `user_type` for `Foo?`.
    """
    n_type = getattr(type_node, "type", "")
    if n_type == "type_annotation":
        for child in (getattr(type_node, "children", []) or []):
            if getattr(child, "type", "") in ("user_type", "type_identifier", "optional_type"):
                return _extract_simple_swift_type_name(child, source_bytes)
        return None
    if n_type == "user_type":
        for child in (getattr(type_node, "children", []) or []):
            if getattr(child, "type", "") == "type_identifier":
                return source_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="replace")
        return None
    if n_type == "type_identifier":
        return source_bytes[type_node.start_byte:type_node.end_byte].decode("utf-8", errors="replace")
    if n_type == "optional_type":
        for child in (getattr(type_node, "children", []) or []):
            if getattr(child, "type", "") in ("user_type", "type_identifier"):
                return _extract_simple_swift_type_name(child, source_bytes)
        return None
    return None


def _find_enclosing_swift_class_name(node, source_bytes: bytes) -> str | None:
    """Walk up to Swift class/struct/actor/enum/protocol declaration's type_identifier."""
    cur = getattr(node, "parent", None)
    while cur is not None:
        if getattr(cur, "type", "") in (
            "class_declaration", "struct_declaration", "actor_declaration",
            "enum_declaration", "protocol_declaration",
        ):
            for child in (getattr(cur, "children", []) or []):
                if getattr(child, "type", "") == "type_identifier":
                    return source_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="replace")
            return None
        cur = getattr(cur, "parent", None)
    return None


def _search_swift_declarations_in_scope(scope_node, name: str, source_bytes: bytes) -> str | None:
    """Search Swift scope for `let foo: Foo = ...` / `var foo: Foo` / `func bar(foo: Foo)`."""
    stack = [scope_node]
    while stack:
        n = stack.pop()
        n_type = getattr(n, "type", "")
        if n_type == "property_declaration":
            # Swift: `let oos: ObjectOutputStream = ...`
            # children: value_binding_pattern + pattern (simple_identifier) + type_annotation + ...
            name_child = None
            type_child = None
            for child in (getattr(n, "children", []) or []):
                ct = getattr(child, "type", "")
                if ct == "pattern":
                    for gc in (getattr(child, "children", []) or []):
                        if getattr(gc, "type", "") == "simple_identifier":
                            name_child = gc
                            break
                elif ct == "type_annotation" and type_child is None:
                    type_child = child
            if name_child is not None and type_child is not None:
                var_name = source_bytes[name_child.start_byte:name_child.end_byte].decode("utf-8", errors="replace")
                if var_name == name:
                    return _extract_simple_swift_type_name(type_child, source_bytes)
        elif n_type == "parameter":
            # Swift: `func bar(oos: ObjectOutputStream)` — simple_identifier + : + user_type
            name_child = None
            type_child = None
            for child in (getattr(n, "children", []) or []):
                ct = getattr(child, "type", "")
                if ct == "simple_identifier" and name_child is None:
                    name_child = child
                elif ct in ("user_type", "type_identifier", "optional_type"):
                    type_child = child
            if name_child is not None and type_child is not None:
                param_name = source_bytes[name_child.start_byte:name_child.end_byte].decode("utf-8", errors="replace")
                if param_name == name:
                    return _extract_simple_swift_type_name(type_child, source_bytes)
        # Don't descend into nested function/class bodies.
        if n_type in (
            "function_declaration", "class_declaration", "struct_declaration",
            "actor_declaration", "enum_declaration", "protocol_declaration",
        ) and n is not scope_node:
            continue
        stack.extend(reversed(getattr(n, "children", []) or []))
    return None


def _resolve_swift_identifier_type(name: str, ref_node, source_bytes: bytes) -> str | None:
    cur = getattr(ref_node, "parent", None)
    while cur is not None:
        cur_type = getattr(cur, "type", "")
        if cur_type in (
            "function_declaration", "class_declaration", "struct_declaration",
            "actor_declaration", "enum_declaration", "protocol_declaration",
        ):
            resolved = _search_swift_declarations_in_scope(cur, name, source_bytes)
            if resolved is not None:
                return resolved
            if cur_type in (
                "class_declaration", "struct_declaration", "actor_declaration",
                "enum_declaration", "protocol_declaration",
            ):
                break
        cur = getattr(cur, "parent", None)
    if name and name[:1].isupper():
        return name
    return None


def _resolve_swift_receiver_type(call_node, source_bytes: bytes) -> str | None:
    """Resolve Swift call_expression receiver type.

    Swift grammar shapes:
    - Bare method call `bar()`: call_expression has simple_identifier + call_suffix.
    - Constructor call `Foo()`: same AST shape as bare call (Swift has no `new`
      keyword). Discriminated by case — PascalCase identifier → constructor,
      lowerCamelCase → method. Constructor calls return None so the standard
      attribution handles them (target the type's init).
    - Member call `foo.bar()`: call_expression has navigation_expression
      (children: simple_identifier "foo" + navigation_suffix (.bar)) + call_suffix.
    """
    if call_node is None or getattr(call_node, "type", "") != "call_expression":
        return None
    children = list(getattr(call_node, "children", []) or [])
    if not children:
        return None
    callee = children[0]
    callee_type = getattr(callee, "type", "")
    if callee_type == "simple_identifier":
        text = source_bytes[callee.start_byte:callee.end_byte].decode("utf-8", errors="replace")
        if text and text[:1].isupper():
            # Constructor call (`Foo()`) — defer to standard attribution.
            return None
        return _find_enclosing_swift_class_name(call_node, source_bytes)
    if callee_type == "navigation_expression":
        nav_children = list(getattr(callee, "children", []) or [])
        if not nav_children:
            return None
        receiver = nav_children[0]
        receiver_type = getattr(receiver, "type", "")
        if receiver_type == "simple_identifier":
            text = source_bytes[receiver.start_byte:receiver.end_byte].decode("utf-8", errors="replace")
            if text == "self":
                return _find_enclosing_swift_class_name(call_node, source_bytes)
            if text == "super":
                return None
            return _resolve_swift_identifier_type(text, call_node, source_bytes)
    return None


# Wave 131bt (1319s): Construction-call resolution.
#
# Languages with explicit-shape construction nodes — the type identifier is
# extracted directly from the AST.
_CONSTRUCTION_EXPLICIT_NODE_TYPES_BY_LANG: dict[str, frozenset[str]] = {
    "java": frozenset({"object_creation_expression"}),
    "csharp": frozenset({"object_creation_expression"}),
    "typescript": frozenset({"new_expression"}),
    "javascript": frozenset({"new_expression"}),
    "php": frozenset({"object_creation_expression"}),
    "rust": frozenset({"struct_expression"}),
    "go": frozenset({"composite_literal"}),
}

# Languages where bare PascalCase calls indicate construction. The detector
# requires (a) callee is a bare identifier (no navigation/scope prefix), (b)
# the name resolves to a class/struct/enum/actor/protocol symbol via
# symbol_lookup. Per the prepare-council red-team finding, the symbol-lookup
# precondition is scope-aware: the call's resolver consults symbol_lookup which
# tracks lexically reachable definitions, and methods on the enclosing class
# shadow same-named sibling classes (handled by the qname structure of
# symbol_lookup entries).
_CONSTRUCTION_BARE_CALL_LANGS: frozenset[str] = frozenset({
    "swift", "python", "kotlin", "scala",
})

# Kinds that confirm the symbol is a class-like construct (not a function
# whose name happens to be PascalCase). Used by the bare-call resolver.
_CLASS_LIKE_KINDS_FOR_CONSTRUCTION: frozenset[str] = frozenset({
    "class", "struct", "enum", "actor", "protocol", "interface",
    "record", "module",  # Ruby module is namespace-like; allow it as a construction target.
})


def _ts_construction_node_text(node, source_bytes: bytes, field_name: str) -> str | None:
    """Extract field text from a construction node; return None on miss."""
    try:
        child = node.child_by_field_name(field_name)
    except Exception:
        child = None
    if child is None:
        return None
    text = source_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="replace").strip()
    return text or None


def _ts_extract_type_identifier_child(node, source_bytes: bytes) -> str | None:
    """Return the first child of type ``type_identifier`` / ``identifier`` / ``name``.

    Used for AST shapes where the type name appears as a direct named child but
    is not bound to a specific field (Go composite_literal in some grammars, etc.).
    """
    for child in getattr(node, "named_children", []) or []:
        ctype = getattr(child, "type", "") or ""
        if ctype in ("type_identifier", "identifier", "name"):
            text = source_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="replace").strip()
            if text:
                return text
    return None


def _ts_lookup_class_node(simple_name: str, symbol_lookup: dict[str, str]) -> str | None:
    """Resolve a simple class name to a class-like node id, or None.

    The lookup tries (a) the simple name directly (project-internal class merge
    means ``Foo`` often resolves to ``src/Foo.java``), and (b) the import-alias
    chain via cross-file resolution at the post-pass. For consistency with the
    receiver-type resolvers, we return the qname-matched id when present and
    let the cross-file rewrite handle the rest.
    """
    if not simple_name:
        return None
    if simple_name in symbol_lookup:
        return symbol_lookup[simple_name]
    return None


def _resolve_construction_target(
    call_node,
    node_type: str,
    source_bytes: bytes,
    symbol_lookup: dict[str, str],
    symbol_lookup_kinds: dict[str, str],
    lang_key: str,
) -> str | None:
    """Resolve a construction-shaped call to a class-like node id.

    Handles two categories:

    1. Explicit-shape construction (Java/C#/TS/JS ``object_creation_expression``
       / ``new_expression``, PHP ``object_creation_expression``, Rust
       ``struct_expression``, Go ``composite_literal``). The AST node carries
       the type identifier directly.

    2. Bare-call construction (Swift/Python/Kotlin/Scala). The callee is a
       bare PascalCase identifier and the name resolves to a class-like
       symbol via ``symbol_lookup``.

    Also handles two retarget cases:

    3. Rust ``Foo::new()`` convention — the call is captured as a
       ``call_expression`` whose callee is a ``scoped_identifier`` ending in
       ``new``. Retargets to the struct node when the prefix matches a
       ``struct_item``/``enum_item`` in ``symbol_lookup``. Lower-confidence
       convention; the caller still tags with ``CONSTRUCTION_RESOLVED``.

    4. Go ``new(<TypeName>)`` builtin — extract the type-identifier argument
       and retarget to the struct node.

    Returns:
        The resolved class-node id (project or import-aliased), or None when
        the node is not a construction shape or the type is not in scope.

    Per the prepare-council red-team finding, scope-aware symbol lookup is
    enforced by ``symbol_lookup_kinds``: a class symbol only wins when it
    resolves to a class-like kind. Methods or functions with PascalCase names
    do not match.
    """
    if call_node is None or not node_type:
        return None

    # --- Explicit-shape construction nodes (per-language) ---
    explicit_types = _CONSTRUCTION_EXPLICIT_NODE_TYPES_BY_LANG.get(lang_key, frozenset())
    if node_type in explicit_types:
        # Per-language type-name extraction.
        type_name: str | None = None
        if lang_key in ("java", "csharp"):
            # object_creation_expression: ``type`` field carries the class name
            # (Java type_identifier / C# identifier).
            type_name = _ts_construction_node_text(call_node, source_bytes, "type")
        elif lang_key == "php":
            # PHP object_creation_expression has no field names; the class
            # name appears as a named child of type ``name``.
            type_name = _ts_extract_type_identifier_child(call_node, source_bytes)
        elif lang_key in ("typescript", "javascript"):
            # new_expression: ``constructor`` field carries the class name.
            type_name = _ts_construction_node_text(call_node, source_bytes, "constructor")
        elif lang_key == "rust":
            # struct_expression: ``name`` field carries the type identifier.
            type_name = _ts_construction_node_text(call_node, source_bytes, "name")
        elif lang_key == "go":
            # composite_literal: ``type`` field — filter to type_identifier-only
            # to exclude map/slice/array literals.
            try:
                type_child = call_node.child_by_field_name("type")
            except Exception:
                type_child = None
            if type_child is not None:
                tc_type = getattr(type_child, "type", "") or ""
                if tc_type == "type_identifier":
                    type_name = source_bytes[type_child.start_byte:type_child.end_byte].decode("utf-8", errors="replace").strip() or None

        if type_name:
            # Strip generic type-parameter suffix for languages that allow them
            # in construction position (TS ``new Container<Foo>()``, C# ``new
            # List<Foo>()``). Use the outermost type only.
            if "<" in type_name:
                type_name = type_name.split("<", 1)[0].strip()
            resolved = _ts_lookup_class_node(type_name, symbol_lookup)
            if resolved is not None:
                # Scope-aware kind check: ensure the symbol IS a class-like
                # entity, not a function whose name happens to be PascalCase.
                kind = symbol_lookup_kinds.get(type_name, "")
                if not kind or kind in _CLASS_LIKE_KINDS_FOR_CONSTRUCTION:
                    return resolved
                # If kind says it's a function/method, do NOT route as
                # construction; the caller falls back to standard attribution.
                return None
            # When the symbol is not in scope, return None — the cross-file
            # rewrite pass at the end handles import resolution. We return the
            # external-prefixed key so the cross-file pass can promote it.
            return f"external::{type_name}"

    # --- Rust ``Foo::new()`` convention (retarget) ---
    if lang_key == "rust" and node_type == "call_expression":
        target = _resolve_rust_new_convention(call_node, source_bytes, symbol_lookup, symbol_lookup_kinds)
        if target is not None:
            return target

    # --- Go ``new(<TypeName>)`` builtin (retarget) ---
    if lang_key == "go" and node_type == "call_expression":
        target = _resolve_go_new_builtin(call_node, source_bytes, symbol_lookup, symbol_lookup_kinds)
        if target is not None:
            return target

    # --- Ruby ``Foo.new(...)`` shape ---
    if lang_key == "ruby" and node_type in ("call", "method_call"):
        target = _resolve_ruby_new_call(call_node, source_bytes, symbol_lookup, symbol_lookup_kinds)
        if target is not None:
            return target

    # --- Bare-call construction (Swift/Python/Kotlin/Scala) ---
    if lang_key in _CONSTRUCTION_BARE_CALL_LANGS and node_type in ("call_expression", "call"):
        target = _resolve_bare_call_construction(call_node, source_bytes, symbol_lookup, symbol_lookup_kinds, lang_key)
        if target is not None:
            return target

    return None


def _resolve_rust_new_convention(
    call_node, source_bytes: bytes, symbol_lookup: dict[str, str], symbol_lookup_kinds: dict[str, str]
) -> str | None:
    """Retarget Rust ``Foo::new()`` to the struct node when ``Foo`` is in scope.

    Convention only; not language-required. Returns the struct node id when
    the prefix matches a class-like symbol; otherwise None (so the standard
    receiver-type/EXTRACTED path runs).
    """
    if call_node is None or getattr(call_node, "type", "") != "call_expression":
        return None
    try:
        callee = call_node.child_by_field_name("function")
    except Exception:
        callee = None
    if callee is None:
        return None
    if getattr(callee, "type", "") != "scoped_identifier":
        return None
    text = source_bytes[callee.start_byte:callee.end_byte].decode("utf-8", errors="replace").strip()
    if not text or "::" not in text:
        return None
    parts = text.split("::")
    if parts[-1] != "new" or len(parts) < 2:
        return None
    type_name = parts[-2]
    if not type_name or not type_name[:1].isupper():
        return None
    kind = symbol_lookup_kinds.get(type_name, "")
    if kind and kind not in _CLASS_LIKE_KINDS_FOR_CONSTRUCTION:
        return None
    resolved = _ts_lookup_class_node(type_name, symbol_lookup)
    if resolved is not None:
        return resolved
    # Cross-file fallback: return external::<TypeName> so the cross-file
    # rewrite pass can promote to a project node via simple_name_index.
    return f"external::{type_name}"


def _resolve_go_new_builtin(
    call_node, source_bytes: bytes, symbol_lookup: dict[str, str], symbol_lookup_kinds: dict[str, str]
) -> str | None:
    """Retarget Go ``new(<TypeName>)`` to the struct node.

    The ``new`` builtin takes a single type-identifier argument. Returns the
    struct node id when the argument matches a class-like symbol; otherwise
    None.
    """
    if call_node is None or getattr(call_node, "type", "") != "call_expression":
        return None
    try:
        callee = call_node.child_by_field_name("function")
    except Exception:
        callee = None
    if callee is None:
        return None
    callee_text = source_bytes[callee.start_byte:callee.end_byte].decode("utf-8", errors="replace").strip()
    if callee_text != "new":
        return None
    try:
        args = call_node.child_by_field_name("arguments")
    except Exception:
        args = None
    if args is None:
        return None
    for child in getattr(args, "named_children", []) or []:
        if getattr(child, "type", "") == "type_identifier":
            type_name = source_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="replace").strip()
            if not type_name:
                continue
            kind = symbol_lookup_kinds.get(type_name, "")
            if kind and kind not in _CLASS_LIKE_KINDS_FOR_CONSTRUCTION:
                return None
            resolved = _ts_lookup_class_node(type_name, symbol_lookup)
            if resolved is not None:
                return resolved
            return f"external::{type_name}"
    return None


def _resolve_ruby_new_call(
    call_node, source_bytes: bytes, symbol_lookup: dict[str, str], symbol_lookup_kinds: dict[str, str]
) -> str | None:
    """Resolve Ruby ``Foo.new(args)`` to the class/module node when in scope."""
    if call_node is None:
        return None
    # Tree-sitter Ruby: call → receiver, method
    try:
        method = call_node.child_by_field_name("method")
    except Exception:
        method = None
    if method is None:
        return None
    method_name = source_bytes[method.start_byte:method.end_byte].decode("utf-8", errors="replace").strip()
    if method_name != "new":
        return None
    try:
        receiver = call_node.child_by_field_name("receiver")
    except Exception:
        receiver = None
    if receiver is None:
        return None
    receiver_text = source_bytes[receiver.start_byte:receiver.end_byte].decode("utf-8", errors="replace").strip()
    if not receiver_text or not receiver_text[:1].isupper():
        return None
    kind = symbol_lookup_kinds.get(receiver_text, "")
    if kind and kind not in _CLASS_LIKE_KINDS_FOR_CONSTRUCTION:
        return None
    resolved = _ts_lookup_class_node(receiver_text, symbol_lookup)
    if resolved is not None:
        return resolved
    return f"external::{receiver_text}"


def _resolve_bare_call_construction(
    call_node, source_bytes: bytes, symbol_lookup: dict[str, str], symbol_lookup_kinds: dict[str, str], lang_key: str
) -> str | None:
    """Resolve a bare PascalCase call to a class-like node, or None.

    Used for Swift/Python/Kotlin/Scala. Requires the callee to be a bare
    identifier (no navigation/scope prefix) starting with an uppercase letter,
    AND the name to resolve to a class-like symbol in scope.

    For Swift, ``Foo.init(args)`` is also handled (navigation_expression with
    ``init`` selector on a type name).

    Returns None when the callee is not a bare PascalCase identifier or the
    name does not match a class-like symbol — the caller then falls through
    to receiver-type or standard attribution.
    """
    if call_node is None:
        return None
    children = list(getattr(call_node, "children", []) or [])
    if not children:
        return None
    callee = children[0]
    callee_type = getattr(callee, "type", "") or ""

    name: str | None = None
    if callee_type in ("simple_identifier", "identifier", "constant"):
        # Bare identifier callee. Extract the name.
        name = source_bytes[callee.start_byte:callee.end_byte].decode("utf-8", errors="replace").strip()
    elif lang_key == "swift" and callee_type == "navigation_expression":
        # Swift ``Foo.init(args)`` — the type name is the first child and the
        # navigation suffix selector is ``init``.
        nav_children = list(getattr(callee, "children", []) or [])
        if not nav_children:
            return None
        # First child is the type identifier; the navigation_suffix should
        # contain ``init``.
        type_child = nav_children[0]
        type_text = source_bytes[type_child.start_byte:type_child.end_byte].decode("utf-8", errors="replace").strip()
        # Verify the selector is ``init``.
        selector_is_init = False
        for nc in nav_children[1:]:
            if getattr(nc, "type", "") == "navigation_suffix":
                for sc in (getattr(nc, "children", []) or []):
                    sc_text = source_bytes[sc.start_byte:sc.end_byte].decode("utf-8", errors="replace").strip()
                    if sc_text == "init":
                        selector_is_init = True
                        break
                break
        if not selector_is_init:
            return None
        if not type_text or not type_text[:1].isupper():
            return None
        name = type_text

    if not name:
        return None
    # Must start with uppercase (PascalCase discriminator).
    if not name[:1].isupper():
        return None
    # Scope-aware kind check: only route to class-like symbols.
    kind = symbol_lookup_kinds.get(name, "")
    if kind and kind not in _CLASS_LIKE_KINDS_FOR_CONSTRUCTION:
        # The name resolves to a non-class entity (function, method) — don't
        # route as construction; fall through to standard attribution.
        return None
    resolved = _ts_lookup_class_node(name, symbol_lookup)
    if resolved is not None:
        return resolved
    # When the symbol is not in scope locally, return external::<name> so the
    # cross-file rewrite pass can promote to a project node via
    # simple_name_index. The PascalCase + class-kind precondition (above)
    # filters out methods/functions; only legitimate class references reach
    # this fallback.
    return f"external::{name}"


# Wave 131bt (1319q): TypeScript / JavaScript receiver-type resolution.
#
# TS/JS share the same tree-sitter grammar family. Receiver-type resolution
# requires the call to be of the form ``foo.bar()`` where ``foo`` has a known
# type — either from a TS type annotation (``let foo: Foo = ...``,
# ``function m(foo: Foo)``), an ``as`` cast (``(x as Foo).bar()``), or JSDoc
# ``/** @type {Foo} */`` immediately preceding the declaration (JS).
#
# Phase 1 (TS native annotations) is implemented; Phase 2 (JS JSDoc regex
# extraction) is the same dispatch shape with a separate annotation source.
# When no annotation is found, the helper returns None and standard attribution
# proceeds — no false positives from inference, matching ``mypy`` / TSC's
# ``strict`` defaults.


def _extract_simple_ts_type_name(type_node, source_bytes: bytes) -> str | None:
    """Extract a single type identifier from a TS type_annotation subtree.

    Handles `type_annotation > type_identifier`, generic_type (Container<Foo>
    → "Container"), union_type (Foo | null → "Foo"), and nullable shapes.
    """
    if type_node is None:
        return None
    n_type = getattr(type_node, "type", "")
    if n_type == "type_annotation":
        for child in (getattr(type_node, "named_children", []) or []):
            return _extract_simple_ts_type_name(child, source_bytes)
        return None
    if n_type == "type_identifier":
        return source_bytes[type_node.start_byte:type_node.end_byte].decode("utf-8", errors="replace").strip() or None
    if n_type == "generic_type":
        # Container<Foo> — extract the outer type name.
        for child in (getattr(type_node, "named_children", []) or []):
            ct = getattr(child, "type", "")
            if ct == "type_identifier":
                return source_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="replace").strip() or None
        return None
    if n_type in ("union_type", "intersection_type"):
        # Foo | null → extract the first non-null type.
        for child in (getattr(type_node, "named_children", []) or []):
            ct = getattr(child, "type", "")
            if ct in ("type_identifier", "generic_type"):
                inner = _extract_simple_ts_type_name(child, source_bytes)
                if inner and inner not in ("null", "undefined"):
                    return inner
        return None
    if n_type == "nullable_type":
        for child in (getattr(type_node, "named_children", []) or []):
            inner = _extract_simple_ts_type_name(child, source_bytes)
            if inner:
                return inner
        return None
    if n_type == "predefined_type":
        # `void`, `string`, etc. — not class-like.
        return None
    return None


def _find_enclosing_ts_class_name(node, source_bytes: bytes) -> str | None:
    """Walk up to the enclosing TS/JS class_declaration's name."""
    cur = getattr(node, "parent", None)
    while cur is not None:
        ctype = getattr(cur, "type", "") or ""
        if ctype in ("class_declaration", "abstract_class_declaration"):
            try:
                name_node = cur.child_by_field_name("name")
            except Exception:
                name_node = None
            if name_node is not None:
                return source_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace").strip() or None
            return None
        cur = getattr(cur, "parent", None)
    return None


_JSDOC_TYPE_RE = re.compile(r"@type\s*\{\s*([A-Za-z_][\w.]*)")
_JSDOC_PARAM_RE = re.compile(r"@param\s*\{\s*([A-Za-z_][\w.]*)\s*\}\s*([A-Za-z_]\w*)")


def _ts_jsdoc_type_for_lexical_decl(lex_decl, source_bytes: bytes) -> str | None:
    """Return the JS type from a JSDoc `@type {Foo}` comment preceding a
    `lexical_declaration`. JS-only — TS uses native annotations.

    Walks the immediately-preceding sibling looking for a comment shaped
    ``/** @type {Foo} */``. Returns the bare type name or None.
    """
    parent = getattr(lex_decl, "parent", None)
    if parent is None:
        return None
    children = list(getattr(parent, "children", []) or [])
    try:
        idx = children.index(lex_decl)
    except ValueError:
        return None
    # Scan backwards for the nearest comment sibling.
    for prev in reversed(children[:idx]):
        ctype = getattr(prev, "type", "") or ""
        if ctype != "comment":
            break  # Not a comment — JSDoc must be immediately adjacent.
        text = source_bytes[prev.start_byte:prev.end_byte].decode("utf-8", errors="replace")
        if text.startswith("/**"):
            m = _JSDOC_TYPE_RE.search(text)
            if m:
                return m.group(1)
    return None


def _search_ts_declarations_in_scope(scope_node, name: str, source_bytes: bytes) -> str | None:
    """Search TS/JS scope for `let foo: Foo = ...` / parameter `foo: Foo`
    OR (JS only) the preceding JSDoc ``@type {Foo}`` comment."""
    stack = [scope_node]
    while stack:
        n = stack.pop()
        n_type = getattr(n, "type", "") or ""
        # let / const / var declarators
        if n_type == "variable_declarator":
            try:
                name_node = n.child_by_field_name("name")
            except Exception:
                name_node = None
            try:
                type_node = n.child_by_field_name("type")
            except Exception:
                type_node = None
            if name_node is not None:
                var_name = source_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace").strip()
                if var_name == name:
                    # Native annotation (TS) takes precedence.
                    if type_node is not None:
                        resolved = _extract_simple_ts_type_name(type_node, source_bytes)
                        if resolved:
                            return resolved
                    # JS JSDoc fallback: look at the preceding comment on the
                    # enclosing lexical_declaration.
                    lex_decl = getattr(n, "parent", None)
                    if lex_decl is not None and getattr(lex_decl, "type", "") == "lexical_declaration":
                        return _ts_jsdoc_type_for_lexical_decl(lex_decl, source_bytes)
                    return None
            if name_node is not None and type_node is not None:
                var_name = source_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace").strip()
                if var_name == name:
                    return _extract_simple_ts_type_name(type_node, source_bytes)
        # Function parameters with type annotations
        elif n_type in ("required_parameter", "optional_parameter"):
            param_name = None
            type_child = None
            for child in (getattr(n, "named_children", []) or []):
                ct = getattr(child, "type", "") or ""
                if ct == "identifier" and param_name is None:
                    param_name = source_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="replace").strip()
                elif ct == "type_annotation":
                    type_child = child
            if param_name == name and type_child is not None:
                return _extract_simple_ts_type_name(type_child, source_bytes)
        # Don't descend into nested function/class bodies.
        if n_type in (
            "function_declaration", "function_expression", "arrow_function",
            "method_definition", "class_declaration", "abstract_class_declaration",
        ) and n is not scope_node:
            continue
        stack.extend(reversed(getattr(n, "named_children", []) or []))
    return None


def _resolve_ts_identifier_type(name: str, ref_node, source_bytes: bytes) -> str | None:
    """Resolve a TS/JS identifier to its declared type by walking up scopes."""
    cur = getattr(ref_node, "parent", None)
    while cur is not None:
        cur_type = getattr(cur, "type", "") or ""
        if cur_type in (
            "function_declaration", "function_expression", "arrow_function",
            "method_definition", "class_declaration", "abstract_class_declaration",
            "statement_block", "program",
        ):
            resolved = _search_ts_declarations_in_scope(cur, name, source_bytes)
            if resolved is not None:
                return resolved
            if cur_type in ("class_declaration", "abstract_class_declaration", "program"):
                break
        cur = getattr(cur, "parent", None)
    return None


def _resolve_ts_receiver_type(call_node, source_bytes: bytes) -> str | None:
    """Resolve a TS/JS call_expression receiver type.

    Handles:
    - `foo.bar()` where `foo` has a declared type — call_expression with
      function=member_expression(object, property).
    - `this.bar()` — routes to enclosing class.
    - `super.bar()` — uncertain; return None.
    - Bare `bar()` — resolves to enclosing class for non-PascalCase callees.
    """
    if call_node is None or getattr(call_node, "type", "") != "call_expression":
        return None
    try:
        func = call_node.child_by_field_name("function")
    except Exception:
        func = None
    if func is None:
        return None
    func_type = getattr(func, "type", "") or ""
    if func_type == "member_expression":
        try:
            obj = func.child_by_field_name("object")
        except Exception:
            obj = None
        if obj is None:
            return None
        obj_type = getattr(obj, "type", "") or ""
        if obj_type == "identifier":
            text = source_bytes[obj.start_byte:obj.end_byte].decode("utf-8", errors="replace").strip()
            if text == "this":
                return _find_enclosing_ts_class_name(call_node, source_bytes)
            if text == "super":
                return None
            # PascalCase: static call like `Foo.method()` — receiver IS the class.
            if text and text[:1].isupper():
                return text
            return _resolve_ts_identifier_type(text, call_node, source_bytes)
        if obj_type == "this":
            return _find_enclosing_ts_class_name(call_node, source_bytes)
        if obj_type == "as_expression":
            # (x as Foo).bar() — type is on the right side of `as`
            try:
                type_child = obj.child_by_field_name("type")
            except Exception:
                type_child = None
            if type_child is None:
                # Fallback to scanning children
                for c in (getattr(obj, "named_children", []) or [])[::-1]:
                    ct = getattr(c, "type", "") or ""
                    if ct in ("type_identifier", "generic_type", "union_type"):
                        type_child = c
                        break
            if type_child is not None:
                return _extract_simple_ts_type_name(type_child, source_bytes)
            return None
        return None
    if func_type == "identifier":
        # Bare call — `bar()` from inside a class method routes to enclosing class.
        text = source_bytes[func.start_byte:func.end_byte].decode("utf-8", errors="replace").strip()
        if text and text[:1].isupper():
            # Constructor-style call (`Foo()` without `new`) — defer.
            return None
        return _find_enclosing_ts_class_name(call_node, source_bytes)
    return None


def _resolve_ts_call_target(
    call_node,
    source_bytes: bytes,
    symbol_lookup: dict[str, str],
    import_targets: dict[str, str] | None = None,
) -> str | None:
    """Resolve a TS/JS call_expression to a graph node id when receiver type is known.

    Wave 1p2q3 (1p2tf): when the receiver type was imported (e.g.
    `import { Foo } from '@scope/lib'` resolved to a project file via
    tsconfig.paths), `import_targets[receiver_type]` carries the resolved
    project node id. The resolver constructs the cross-file node id directly
    instead of falling through to `external::*`, so receiver-resolved edges
    land on aliased cross-package types without depending on the per-project
    unambiguous-simple-name cross-file rewrite.
    """
    if call_node is None or getattr(call_node, "type", "") != "call_expression":
        return None
    try:
        func = call_node.child_by_field_name("function")
    except Exception:
        func = None
    if func is None:
        return None
    func_type = getattr(func, "type", "") or ""
    method_name: str | None = None
    if func_type == "member_expression":
        try:
            prop = func.child_by_field_name("property")
        except Exception:
            prop = None
        if prop is not None:
            method_name = source_bytes[prop.start_byte:prop.end_byte].decode("utf-8", errors="replace").strip() or None
    elif func_type == "identifier":
        method_name = source_bytes[func.start_byte:func.end_byte].decode("utf-8", errors="replace").strip() or None
    if not method_name:
        return None
    receiver_type = _resolve_ts_receiver_type(call_node, source_bytes)
    if receiver_type is None:
        return None
    qualified = f"{receiver_type}.{method_name}"
    if qualified in symbol_lookup:
        return symbol_lookup[qualified]
    # Wave 1p2q3 (1p2tf): aliased-import receiver-type resolution.
    if import_targets:
        target = import_targets.get(receiver_type)
        if target and not target.startswith("external::"):
            return f"{target}::{receiver_type}.{method_name}"
    return f"external::{receiver_type}.{method_name}"


# Wave 131bt (1319q): PHP receiver-type resolution.
#
# PHP grammars expose native type hints directly. Object method calls use
# ``->`` syntax (member_call_expression). Static calls use ``::``
# (scoped_call_expression). Resolution mirrors TS but reads PHP-specific
# field names.


def _extract_simple_php_type_name(type_node, source_bytes: bytes) -> str | None:
    if type_node is None:
        return None
    n_type = getattr(type_node, "type", "") or ""
    if n_type in ("named_type", "type_list"):
        # PHP wraps types in a `named_type` node; extract the `name` child.
        for child in (getattr(type_node, "named_children", []) or []):
            ct = getattr(child, "type", "") or ""
            if ct == "name":
                text = source_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="replace").strip()
                return text or None
        return None
    if n_type == "name":
        text = source_bytes[type_node.start_byte:type_node.end_byte].decode("utf-8", errors="replace").strip()
        return text or None
    if n_type == "optional_type":
        for child in (getattr(type_node, "named_children", []) or []):
            inner = _extract_simple_php_type_name(child, source_bytes)
            if inner:
                return inner
        return None
    if n_type == "primitive_type":
        return None  # int/string/bool are not class-like.
    return None


def _find_enclosing_php_class_name(node, source_bytes: bytes) -> str | None:
    cur = getattr(node, "parent", None)
    while cur is not None:
        ctype = getattr(cur, "type", "") or ""
        if ctype in ("class_declaration", "interface_declaration", "trait_declaration"):
            try:
                name_node = cur.child_by_field_name("name")
            except Exception:
                name_node = None
            if name_node is not None:
                return source_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace").strip() or None
            return None
        cur = getattr(cur, "parent", None)
    return None


def _search_php_declarations_in_scope(scope_node, name: str, source_bytes: bytes) -> str | None:
    """Search PHP scope for parameter / property declarations matching name."""
    target = "$" + name if not name.startswith("$") else name
    stack = [scope_node]
    while stack:
        n = stack.pop()
        n_type = getattr(n, "type", "") or ""
        if n_type == "simple_parameter":
            param_name = None
            type_child = None
            for child in (getattr(n, "named_children", []) or []):
                ct = getattr(child, "type", "") or ""
                if ct == "variable_name":
                    param_name = source_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="replace").strip()
                elif ct in ("named_type", "optional_type", "primitive_type"):
                    type_child = child
            if param_name == target and type_child is not None:
                return _extract_simple_php_type_name(type_child, source_bytes)
        elif n_type == "property_declaration":
            # PHP 7.4+ typed property: `private Foo $foo;`
            type_child = None
            for child in (getattr(n, "named_children", []) or []):
                ct = getattr(child, "type", "") or ""
                if ct in ("named_type", "primitive_type") and type_child is None:
                    type_child = child
                elif ct == "property_element":
                    for gc in (getattr(child, "named_children", []) or []):
                        if getattr(gc, "type", "") == "variable_name":
                            prop_name = source_bytes[gc.start_byte:gc.end_byte].decode("utf-8", errors="replace").strip()
                            if prop_name == target and type_child is not None:
                                return _extract_simple_php_type_name(type_child, source_bytes)
        # Don't descend into nested function/class bodies.
        if n_type in (
            "method_declaration", "function_definition",
            "class_declaration", "interface_declaration", "trait_declaration",
        ) and n is not scope_node:
            continue
        stack.extend(reversed(getattr(n, "named_children", []) or []))
    return None


def _resolve_php_identifier_type(name: str, ref_node, source_bytes: bytes) -> str | None:
    cur = getattr(ref_node, "parent", None)
    while cur is not None:
        cur_type = getattr(cur, "type", "") or ""
        if cur_type in (
            "method_declaration", "function_definition",
            "class_declaration", "interface_declaration", "trait_declaration",
            "compound_statement",
        ):
            resolved = _search_php_declarations_in_scope(cur, name, source_bytes)
            if resolved is not None:
                return resolved
            if cur_type in ("class_declaration", "interface_declaration", "trait_declaration"):
                break
        cur = getattr(cur, "parent", None)
    return None


def _resolve_php_call_target(call_node, source_bytes: bytes, symbol_lookup: dict[str, str]) -> str | None:
    """Resolve PHP member_call_expression / scoped_call_expression to a node id."""
    if call_node is None:
        return None
    n_type = getattr(call_node, "type", "") or ""
    if n_type == "member_call_expression":
        # $obj->method(args)
        try:
            obj = call_node.child_by_field_name("object")
            method_node = call_node.child_by_field_name("name")
        except Exception:
            return None
        if obj is None or method_node is None:
            return None
        obj_type = getattr(obj, "type", "") or ""
        method_name = source_bytes[method_node.start_byte:method_node.end_byte].decode("utf-8", errors="replace").strip()
        if not method_name:
            return None
        receiver_type: str | None = None
        if obj_type == "variable_name":
            var_text = source_bytes[obj.start_byte:obj.end_byte].decode("utf-8", errors="replace").strip()
            if var_text == "$this":
                receiver_type = _find_enclosing_php_class_name(call_node, source_bytes)
            else:
                # Strip leading $ before searching
                bare = var_text[1:] if var_text.startswith("$") else var_text
                receiver_type = _resolve_php_identifier_type(bare, call_node, source_bytes)
        if receiver_type is None:
            return None
        qualified = f"{receiver_type}.{method_name}"
        if qualified in symbol_lookup:
            return symbol_lookup[qualified]
        return f"external::{receiver_type}.{method_name}"
    if n_type == "scoped_call_expression":
        # Foo::method(args) — static call where receiver is the class itself.
        try:
            scope = call_node.child_by_field_name("scope")
            method_node = call_node.child_by_field_name("name")
        except Exception:
            return None
        if scope is None or method_node is None:
            return None
        method_name = source_bytes[method_node.start_byte:method_node.end_byte].decode("utf-8", errors="replace").strip()
        scope_text = source_bytes[scope.start_byte:scope.end_byte].decode("utf-8", errors="replace").strip()
        if not method_name or not scope_text:
            return None
        if scope_text in ("self", "static", "parent"):
            scope_text = _find_enclosing_php_class_name(call_node, source_bytes) or ""
            if not scope_text:
                return None
        qualified = f"{scope_text}.{method_name}"
        if qualified in symbol_lookup:
            return symbol_lookup[qualified]
        return f"external::{scope_text}.{method_name}"
    return None


# Wave 1p2q3 (1p2td): per-overload parameter-signature extraction so the per-file
# qname-merge that collapses overloads into one node can still be unwound at the
# edge layer. A self-edge on a merged node ambiguously denotes either recursion
# or overload-forwarding; comparing the call-site signature against the enclosing
# overload's signature and the merged node's overload-signature set distinguishes
# them. Swift uses argument labels (native syntax); Java/Kotlin/C#/Scala/C++ use
# arity plus optional named-arg labels.

_OVERLOAD_LANGUAGES: frozenset[str] = frozenset({"swift", "java", "kotlin", "csharp", "scala", "cpp"})


def _swift_param_signature(def_node, source_bytes: bytes) -> str | None:
    """Return Swift parameter-label fingerprint like ``base:offset:customTime:``.

    Tree-sitter Swift exposes parameters as repeated `parameter` siblings
    directly under the `function_declaration` node (no wrapping node).
    Each `parameter` has children: an optional external label identifier,
    then the internal name identifier, then `:`, then the type.
    """
    if def_node is None:
        return None
    labels: list[str] = []
    for child in (getattr(def_node, "children", []) or []):
        if getattr(child, "type", "") == "parameter":
            labels.append(_swift_extract_param_label(child, source_bytes))
    if not labels:
        return "()"
    return "".join(f"{lbl}:" for lbl in labels)


def _swift_extract_param_label(param_node, source_bytes: bytes) -> str:
    """Extract a single Swift parameter's external label (or internal name)."""
    # Tree-sitter Swift exposes parameter children in order:
    #   external_label? (or simple_identifier) simple_identifier ':' type
    # When the first identifier is present and the second is too, the first
    # is the external label. When only one identifier, that IS the label.
    idents: list[str] = []
    for child in (getattr(param_node, "children", []) or []):
        ctype = getattr(child, "type", "") or ""
        if ctype in ("simple_identifier", "identifier", "external_label"):
            text = source_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="replace")
            idents.append(text)
    if not idents:
        return "_"
    if len(idents) >= 2:
        return idents[0] or "_"
    return idents[0] or "_"


def _arity_param_signature(def_node, source_bytes: bytes, lang_key: str) -> str | None:
    """Return ``arity:N`` for Java/Kotlin/C#/Scala/C++ definitions.

    Counts the parameter nodes inside the language-specific parameter list.
    Languages with named arguments at call sites still use this as the
    definition-side signature (named args at call sites are matched against
    arity + label-set during call-signature derivation).
    """
    if def_node is None:
        return None
    param_list_types = {
        "java": ("formal_parameters",),
        "kotlin": ("function_value_parameters", "class_parameters"),
        "csharp": ("parameter_list",),
        "scala": ("parameters", "class_parameters"),
        "cpp": ("parameter_list",),
    }.get(lang_key, ())
    param_child_types = {
        "java": ("formal_parameter", "spread_parameter"),
        "kotlin": ("parameter", "class_parameter"),
        "csharp": ("parameter",),
        "scala": ("parameter", "class_parameter"),
        "cpp": ("parameter_declaration",),
    }.get(lang_key, ())
    for child in (getattr(def_node, "children", []) or []):
        ctype = getattr(child, "type", "") or ""
        if ctype in param_list_types:
            count = 0
            for grandchild in (getattr(child, "children", []) or []):
                gtype = getattr(grandchild, "type", "") or ""
                if gtype in param_child_types:
                    count += 1
            return f"arity:{count}"
    return None


def _extract_definition_signature(def_node, source_bytes: bytes, lang_key: str) -> str | None:
    """Return a per-overload parameter signature for a definition.

    Returns None for languages without overloading or when extraction fails.
    """
    if lang_key not in _OVERLOAD_LANGUAGES:
        return None
    if lang_key == "swift":
        return _swift_param_signature(def_node, source_bytes)
    return _arity_param_signature(def_node, source_bytes, lang_key)


def _swift_call_signature(call_node, source_bytes: bytes) -> str | None:
    """Return Swift call-site argument-label fingerprint.

    Tree-sitter Swift wraps argument labels in a `value_argument_label` node:

        value_argument
          value_argument_label   ← present iff arg has a label
            simple_identifier
          :
          <expression>

    Unlabeled (positional) args have no `value_argument_label` child.
    """
    if call_node is None:
        return None
    value_args = None
    for child in (getattr(call_node, "children", []) or []):
        ctype = getattr(child, "type", "") or ""
        if ctype == "call_suffix":
            for sc in (getattr(child, "children", []) or []):
                if getattr(sc, "type", "") == "value_arguments":
                    value_args = sc
                    break
            if value_args is None:
                value_args = child
            break
        if ctype == "value_arguments":
            value_args = child
            break
    if value_args is None:
        return "()"
    labels: list[str] = []
    any_arg = False
    for child in (getattr(value_args, "children", []) or []):
        ctype = getattr(child, "type", "") or ""
        if ctype != "value_argument":
            continue
        any_arg = True
        label = "_"
        for ac in (getattr(child, "children", []) or []):
            if getattr(ac, "type", "") == "value_argument_label":
                for label_child in (getattr(ac, "children", []) or []):
                    if getattr(label_child, "type", "") in ("simple_identifier", "identifier"):
                        label = source_bytes[label_child.start_byte:label_child.end_byte].decode("utf-8", errors="replace") or "_"
                        break
                break
        labels.append(label)
    if not any_arg:
        return "()"
    return "".join(f"{lbl}:" for lbl in labels)


def _arity_call_signature(call_node, source_bytes: bytes, lang_key: str) -> str | None:
    """Return ``arity:N`` for Java/Kotlin/C#/Scala/C++ call sites."""
    if call_node is None:
        return None
    arg_list_types = {
        "java": ("argument_list",),
        "kotlin": ("value_arguments", "call_suffix"),
        "csharp": ("argument_list",),
        "scala": ("arguments",),
        "cpp": ("argument_list",),
    }.get(lang_key, ())
    arg_child_types = {
        "java": ("expression", "method_invocation", "field_access", "identifier",
                 "decimal_integer_literal", "string_literal", "binary_expression",
                 "null_literal", "true", "false", "lambda_expression", "this",
                 "object_creation_expression", "array_access", "cast_expression",
                 "unary_expression", "ternary_expression", "parenthesized_expression"),
        "kotlin": ("value_argument",),
        "csharp": ("argument",),
        "scala": ("identifier", "integer_literal", "string_literal", "boolean_literal",
                  "call_expression", "field_expression", "infix_expression"),
        "cpp": ("argument", "call_expression", "identifier", "number_literal",
                "string_literal", "binary_expression", "parenthesized_expression",
                "field_expression"),
    }.get(lang_key, ())
    for child in (getattr(call_node, "children", []) or []):
        ctype = getattr(child, "type", "") or ""
        if ctype in arg_list_types:
            # Count the args. For Kotlin/C# we have a wrapper node (value_argument
            # / argument); for Java/Scala/C++ we count any non-trivial child that
            # isn't a comma or paren.
            if lang_key in ("kotlin", "csharp"):
                count = sum(
                    1 for gc in (getattr(child, "children", []) or [])
                    if getattr(gc, "type", "") in arg_child_types
                )
            else:
                # Count all non-punctuation children as args.
                count = sum(
                    1 for gc in (getattr(child, "children", []) or [])
                    if getattr(gc, "type", "") not in ("(", ")", ",", "{", "}")
                    and getattr(gc, "is_named", True)
                )
            return f"arity:{count}"
    return None


def _extract_call_signature(call_node, source_bytes: bytes, lang_key: str) -> str | None:
    """Return a call-site signature derivable from the AST."""
    if lang_key not in _OVERLOAD_LANGUAGES:
        return None
    if lang_key == "swift":
        return _swift_call_signature(call_node, source_bytes)
    return _arity_call_signature(call_node, source_bytes, lang_key)


def _classify_self_edge(
    call_signature: str | None,
    enclosing_signature: str | None,
    overload_signatures: set[str],
) -> str:
    """Classify a self-edge as recursion / overload_forwarding / unknown.

    - call_signature == enclosing_signature → recursion
    - call_signature in (overload_signatures - {enclosing_signature}) → overload_forwarding
    - otherwise → unknown
    """
    if not call_signature or not enclosing_signature:
        return "unknown"
    if call_signature == enclosing_signature:
        return "recursion"
    other_sigs = overload_signatures - {enclosing_signature}
    if call_signature in other_sigs:
        return "overload_forwarding"
    # No overloads registered, or call_signature doesn't match any known overload
    # (same-arity-different-types disambiguation needs type inference).
    if not other_sigs and call_signature != enclosing_signature:
        # Single overload only — anything that doesn't match it is unknown
        # (could be a different-arity call that we mis-counted, or a same-arity
        # different-types case we can't disambiguate without type-checking).
        return "unknown"
    return "unknown"


def _resolve_swift_call_target(call_node, source_bytes: bytes, symbol_lookup: dict[str, str]) -> str | None:
    if call_node is None or getattr(call_node, "type", "") != "call_expression":
        return None
    children = list(getattr(call_node, "children", []) or [])
    if not children:
        return None
    callee = children[0]
    callee_type = getattr(callee, "type", "")
    method_name: str | None = None
    if callee_type == "simple_identifier":
        method_name = source_bytes[callee.start_byte:callee.end_byte].decode("utf-8", errors="replace")
    elif callee_type == "navigation_expression":
        # Method name is in the navigation_suffix's simple_identifier child.
        nav_children = list(getattr(callee, "children", []) or [])
        for nc in nav_children:
            if getattr(nc, "type", "") == "navigation_suffix":
                for sc in (getattr(nc, "children", []) or []):
                    if getattr(sc, "type", "") == "simple_identifier":
                        method_name = source_bytes[sc.start_byte:sc.end_byte].decode("utf-8", errors="replace")
                        break
                break
    if not method_name:
        return None
    receiver_type = _resolve_swift_receiver_type(call_node, source_bytes)
    if receiver_type is None:
        return None
    qualified = f"{receiver_type}.{method_name}"
    if qualified in symbol_lookup:
        return symbol_lookup[qualified]
    return f"external::{receiver_type}.{method_name}"


def _java_aop_matcher_strings(invocation_node, source_bytes: bytes) -> tuple[str, list[str]] | None:
    """For a Java ``method_invocation``, return ``(matcher_name, [string args])``
    or None (wave 1p7dh). Used to capture ByteBuddy/ElementMatchers type-matcher
    target strings (e.g. ``named("org.hibernate.boot.Metadata")`` or the multi-arg
    ``namedOneOf("A", "B")``) as the ``instruments`` node property. Pure syntactic:
    the matcher name is the invocation's ``name`` field; ALL string-literal
    arguments are captured (the ``*OneOf`` forms carry several). A structural
    wrapper like ``implementsInterface(namedOneOf(...))`` carries no string itself —
    its inner matcher call is buffered separately, so its strings are captured there."""
    if invocation_node is None or getattr(invocation_node, "type", "") != "method_invocation":
        return None
    name_node = invocation_node.child_by_field_name("name")
    if name_node is None:
        return None
    matcher_name = name_node.text.decode("utf-8", "replace").strip()
    args = invocation_node.child_by_field_name("arguments")
    if args is None:
        return None
    strings: list[str] = []
    for child in getattr(args, "named_children", []):
        if str(getattr(child, "type", "") or "") == "string_literal":
            raw = child.text.decode("utf-8", "replace").strip()
            val = raw[1:-1] if len(raw) >= 2 and raw[0] in "\"'" else raw
            if val:
                strings.append(val)
    return (matcher_name, strings) if strings else None


def _java_value_annotation_keys(node, source_bytes: bytes) -> list[str]:
    """For a Java declaration node, return the placeholder KEYS of any
    ``@Value("${key:default}")`` annotation on it (wave 1p7dh). Used to capture
    Spring property reads into ``config_read_candidates`` so the finalize pass
    can bind them to ``application.{yml,properties}`` config-key nodes.

    Pure syntactic: walks the node's ``modifiers`` child for an ``annotation``
    whose ``name`` field is ``Value`` (or qualified ``…​.Value``), reads its first
    string-literal argument, and — when that string is a `${…}` placeholder —
    extracts the key (strip ``${``; take up to the first ``:`` default-separator or
    closing ``}``). Non-placeholder ``@Value`` literals (SpEL `#{…}`, constants)
    yield no key. Returns [] for any non-`@Value` node.
    """
    keys: list[str] = []
    try:
        children = list(getattr(node, "named_children", []) or [])
    except Exception:
        return keys
    for child in children:
        if (getattr(child, "type", "") or "") != "modifiers":
            continue
        try:
            mod_children = list(getattr(child, "named_children", []) or [])
        except Exception:
            continue
        for ann in mod_children:
            if (getattr(ann, "type", "") or "") != "annotation":
                continue  # marker_annotation has no args → never a @Value placeholder
            try:
                name_node = ann.child_by_field_name("name")
            except Exception:
                name_node = None
            if name_node is None:
                continue
            ann_name = _ts_node_text(name_node, source_bytes).strip()
            if ann_name.rsplit(".", 1)[-1] != "Value":
                continue
            try:
                args = ann.child_by_field_name("arguments")
            except Exception:
                args = None
            if args is None:
                continue
            for arg in getattr(args, "named_children", []) or []:
                if (getattr(arg, "type", "") or "") != "string_literal":
                    continue
                raw = arg.text.decode("utf-8", "replace").strip()
                val = raw[1:-1] if len(raw) >= 2 and raw[0] in "\"'" else raw
                if not (val.startswith("${") and "}" in val):
                    continue
                inner = val[2:]
                # key is up to the first ':' (default separator) or the closing '}'
                cut = len(inner)
                for sep in (":", "}"):
                    idx = inner.find(sep)
                    if idx != -1:
                        cut = min(cut, idx)
                key = inner[:cut].strip()
                if key and key not in keys:
                    keys.append(key)
    return keys


_JAVA_CONFIG_GETTERS = frozenset({"getProperty", "getRequiredProperty"})


def _java_config_getter_key(invocation_node, source_bytes: bytes) -> str | None:
    """For a Java ``method_invocation``, return the first string-literal argument
    when the invoked method is a Spring ``Environment`` getter
    (``getProperty`` / ``getRequiredProperty`` / ``env.getProperty``) — wave 1p7dh.
    Returns None otherwise. Pure syntactic; the finalize pass's config-file +
    distinctiveness + unique-match gates bound faithfulness, so capturing by
    method NAME (without resolving the receiver type) is safe — a non-config key
    simply finds no matching node and is dropped."""
    if invocation_node is None or getattr(invocation_node, "type", "") != "method_invocation":
        return None
    name_node = invocation_node.child_by_field_name("name")
    if name_node is None:
        return None
    method_name = name_node.text.decode("utf-8", "replace").strip()
    if method_name not in _JAVA_CONFIG_GETTERS:
        return None
    args = invocation_node.child_by_field_name("arguments")
    if args is None:
        return None
    for child in getattr(args, "named_children", []) or []:
        if str(getattr(child, "type", "") or "") == "string_literal":
            raw = child.text.decode("utf-8", "replace").strip()
            val = raw[1:-1] if len(raw) >= 2 and raw[0] in "\"'" else raw
            return val or None
    return None


def _resolve_java_call_target(
    invocation_node, source_bytes: bytes, symbol_lookup: dict[str, str],
    static_import_members: dict[str, str | None] | None = None,
    static_wildcard_imports: list[str] | None = None,
) -> str | None:
    """Resolve a Java method_invocation to a graph node id.

    Deterministic per-call-site dispatch (wave 13129 council action item:
    red-team — no double-emission):

    - Receiver type resolves to a project class (qname found in symbol_lookup)
      → return the project node id.
    - Bare call (no receiver) not defined by the enclosing class, with a
      matching static import (wave 1p9qh / 1p9q9) → return the statically-
      imported ``Class.member`` target (project node when the class is in this
      file, else the QUALIFIED ``external::Class.member`` — never bare; the
      cross-file pass binds a unique project ``Class.member`` or it stays
      external). A single static WILDCARD import (`import static X.*;`)
      resolves otherwise-unresolved bare calls the same way; two static
      wildcards refuse (unique-survivor) and keep enclosing-class attribution.
      Adversarial fix (F1): when the enclosing class ALSO has a supertype
      clause, the static claim is DEFERRED via the reserved
      ``external::staticorinherited#…`` marker — JLS 6.4.1 puts inherited
      members ahead of static imports, and only the finalize pass can see
      cross-file supertype definers (see ``_arbitrate_static_or_inherited``).
    - Receiver type resolves to a non-project type → return the qualified
      external node id (``external::<ResolvedType>.<method>``).
    - Receiver type is uncertain (None) → return None; caller falls through
      to existing simple-name attribution.

    Args:
        invocation_node: Java AST ``method_invocation`` node.
        source_bytes: Source file bytes for text extraction.
        symbol_lookup: Mapping of qname → node_id for project symbols.
        static_import_members: Bare member name → ``Class.member`` from this
            file's explicit static imports (a None value marks a name imported
            from conflicting classes — refused, never guessed).
        static_wildcard_imports: FQNs of static-wildcard-imported classes.
    """
    if invocation_node is None or getattr(invocation_node, "type", "") != "method_invocation":
        return None
    method_name_node = invocation_node.child_by_field_name("name")
    if method_name_node is None:
        return None
    method_name = source_bytes[method_name_node.start_byte:method_name_node.end_byte].decode("utf-8", errors="replace")
    if not method_name:
        return None
    # Wave 1p9qh (1p9qa): `super.foo()` — the true receiver is the enclosing
    # class's superclass, a cross-file fact unavailable at extraction time.
    # Emit the reserved-prefix marker `external::super.<Enclosing>.<method>`
    # (`super` is a Java reserved word — never a real package/class head);
    # phase-1 cross-file resolution passes it through untouched and the
    # finalize inheritance pass binds it via the enclosing class's single
    # project-resolved `extends` target, or refuses. Deliberately NOT bound to
    # `<Enclosing>.<method>`: that would wrong-bind the subclass's own
    # override, the exact method `super.` explicitly skips.
    _obj_node = invocation_node.child_by_field_name("object")
    if getattr(_obj_node, "type", "") == "super":
        enclosing = _find_enclosing_java_class_name(invocation_node, source_bytes)
        if enclosing:
            return f"external::{_SUPER_CALL_PREFIX}{enclosing}.{method_name}"
        return None
    receiver_type = _resolve_java_receiver_type(invocation_node, source_bytes)
    # Same-file precedence (existing scope-first order, unchanged): a method
    # defined by the resolved receiver (for a bare call: the enclosing class)
    # in THIS file wins over any static import.
    if receiver_type is not None:
        qualified = f"{receiver_type}.{method_name}"
        if qualified in symbol_lookup:
            return symbol_lookup[qualified]
    # Wave 1p9qh (1p9q9): static-import member resolution for BARE calls only
    # (an explicit receiver is never a static-import bind).
    if invocation_node.child_by_field_name("object") is None:
        static_claim: str | None = (static_import_members or {}).get(method_name)
        if static_claim is None and method_name not in (static_import_members or {}):
            wilds = list(dict.fromkeys(static_wildcard_imports or []))
            if len(wilds) == 1:
                wild_cls = wilds[0].rsplit(".", 1)[-1]
                if wild_cls:
                    static_claim = f"{wild_cls}.{method_name}"
        if static_claim:
            # Wave 1p9qh adversarial fix (F1): JLS 6.4.1 — members in class
            # scope INCLUDING INHERITED ones shadow single-static and
            # static-on-demand imports. Same-file members already won above;
            # whether a SUPERTYPE defines the member is a cross-file fact,
            # so when the enclosing class has any supertype clause the
            # static claim is DEFERRED via the reserved marker and the
            # finalize inheritance pass arbitrates (inherited definer →
            # bind inherited; multiple definers → refuse; no definer → the
            # claim stands). No supertype clause — or no identifiable
            # enclosing class scope to arbitrate (`receiver_type` is the
            # enclosing class name for a bare call) — keeps today's direct
            # extraction-time static bind.
            if receiver_type is not None and _java_enclosing_has_supertype_clause(invocation_node):
                return (
                    f"external::{_STATIC_OR_INHERITED_PREFIX}"
                    f"{receiver_type}.{method_name}"
                    f"{_STATIC_OR_INHERITED_SEP}{static_claim}"
                )
            return symbol_lookup.get(static_claim) or f"external::{static_claim}"
    if receiver_type is None:
        return None  # Uncertain — fall through to existing attribution.
    # External attribution: qualified external node id.
    return f"external::{receiver_type}.{method_name}"


def _ts_extract_java_annotations(node, source_bytes: bytes) -> list[str]:
    """Extract annotation names from a Java method/class declaration (wave 130rj).

    Walks the ``modifiers`` child for ``marker_annotation`` and ``annotation``
    nodes, reads the ``name`` field of each, and returns the names verbatim
    (e.g. ``["Advice.OnMethodEnter", "Around"]``). Names may be qualified
    (e.g. ``"org.aspectj.lang.annotation.Around"``); downstream consumers match
    by trailing segment.
    """
    annotations: list[str] = []
    try:
        children = list(getattr(node, "named_children", []) or [])
    except Exception:
        return annotations
    for child in children:
        ctype = getattr(child, "type", "") or ""
        if ctype != "modifiers":
            continue
        try:
            mod_children = list(getattr(child, "named_children", []) or [])
        except Exception:
            continue
        for ann in mod_children:
            ann_type = getattr(ann, "type", "") or ""
            if ann_type not in ("marker_annotation", "annotation"):
                continue
            try:
                name_node = ann.child_by_field_name("name")
            except Exception:
                name_node = None
            if name_node is None:
                continue
            name = _ts_node_text(name_node, source_bytes).strip()
            if name and name not in annotations:
                annotations.append(name)
    return annotations


def _ts_extract_csharp_attributes(node, source_bytes: bytes) -> list[str]:
    """Extract attribute names from a C# method/class declaration (wave 130rj — 130tc).

    C# uses `[Attribute]` syntax that lives in ``attribute_list`` children of
    ``method_declaration`` / ``class_declaration`` (sibling to ``modifiers``
    rather than nested inside it as in Java). Each ``attribute_list`` contains
    one or more ``attribute`` nodes; each ``attribute`` exposes its name via
    the ``name`` field. Returns the names verbatim (e.g.
    ``["Around", "OnMethodBoundaryAspect"]``).
    """
    attributes: list[str] = []
    try:
        children = list(getattr(node, "named_children", []) or [])
    except Exception:
        return attributes
    for child in children:
        ctype = getattr(child, "type", "") or ""
        if ctype != "attribute_list":
            continue
        try:
            list_children = list(getattr(child, "named_children", []) or [])
        except Exception:
            continue
        for attr in list_children:
            attr_type = getattr(attr, "type", "") or ""
            if attr_type != "attribute":
                continue
            try:
                name_node = attr.child_by_field_name("name")
            except Exception:
                name_node = None
            if name_node is None:
                continue
            name = _ts_node_text(name_node, source_bytes).strip()
            if name and name not in attributes:
                attributes.append(name)
    return attributes


# =============================================================================
# Embedded-SQL capture at known Java/C# sinks (wave 1p9qi / 1p9qf).
#
# Two-stage design mirroring `reads_config`: a per-language CAPTURE stage
# collects SQL-candidate string literals only at a fixed sink vocabulary
# (MyBatis annotations, native @Query, JDBC prepare*, JdbcTemplate methods,
# C# SqlCommand/CommandText, Dapper, EF raw methods, MyBatis mapper XML),
# buffered per file as `sql_capture_candidates`; the finalize BIND stage runs
# each captured statement through the frozen 1p9qd statement-analysis unit
# (`sql_statement_references`) and binds source → table at LITERAL_DERIVED
# confidence on a UNIQUE match against the SQL-defined node set. Dynamic /
# concatenated-with-variable SQL is refused and counted per file
# (`sql_capture_dynamic`) so the gap stays visible in build stats.
#
# ORIGIN-CHECK CONVENTION (this wave defines it; parallel extractor waves
# mirror it): sinks with DISTINCTIVE names (prepareStatement/prepareCall,
# FromSqlRaw/ExecuteSqlRaw, `new SqlCommand`) use a NEGATIVE origin check —
# refuse only when the receiver/type is resolvable to a PROJECT-defined
# symbol (a user-defined impostor); an unresolvable or external receiver
# captures, bounded by the sniff gate. Sinks with GENERIC names
# (JdbcTemplate `query`/`update`/`execute`) use a POSITIVE origin check —
# capture only when the receiver type resolves to the known library type.
# Dapper's extension methods (`Query`/`Execute` on any IDbConnection
# implementation) have an open receiver-type set, so they take the negative
# check + sniff gate (documented capture-precision tradeoff, census-measured).
#
# RECORDED RESIDUAL LIMITATION (1p9qi review, adversarial finding 2): both
# origin-check arms resolve the receiver/type against THIS FILE's
# `symbol_lookup` only — a same-file impostor is caught at capture time, but
# a project-defined impostor class DEFINED IN ANOTHER FILE (a class literally
# named `JdbcTemplate` with a `query(String)` method, imported/used from a
# different file than its own declaration) is outside the same-file check's
# reach at capture. Accepted, not fixed: the real-corpus census (Fineract +
# Tomcat, `1p9qf`/`1p9qg` Progress Logs) found zero false positives from this
# gap — a cross-file class that merely LOOKS like a sink by name and method
# shape is overwhelmingly a genuine wrapper AROUND the real SQL library (not
# an unrelated same-named type), so the captured literal still sniffs as SQL
# and, when it binds, binds to a real table. Broadening the check to a full
# cross-file symbol resolution is future field-demand work, not a shipped gap.
# =============================================================================

# Sniff gate (Requirement 4): a captured literal enters the pipeline only if
# it LEADS with a SQL statement keyword (after whitespace/parens). Non-SQL
# strings at sinks drop silently; SQL-looking strings NOT at a sink are never
# captured at all (no repo-wide literal trawling).
_SQL_SNIFF_KEYWORDS = frozenset({
    "select", "insert", "update", "delete", "with", "merge", "call", "exec",
    # R5 (wave 1rrx5): schema-affecting DDL leads the analyze_statement write
    # path already handles (`analyze_statement` binds ALTER/DROP/TRUNCATE
    # targets as `writes`). Without these the sniff gate silently dropped
    # embedded `TRUNCATE TABLE t` / `ALTER TABLE t …` / `DROP TABLE t`
    # literals at known sinks (one live Apache Fineract site observed).
    "truncate", "alter", "drop",
})
_SQL_SNIFF_LEAD_RE = re.compile(r"[A-Za-z]+")


def _sql_text_sniffs_as_sql(text: str) -> bool:
    lead = text.lstrip(" \t\r\n(")
    match = _SQL_SNIFF_LEAD_RE.match(lead)
    return bool(match) and match.group(0).casefold() in _SQL_SNIFF_KEYWORDS


def _sql_embedded_parse_has_error(sql_text: str) -> bool:
    """True when embedded SQL parses with a trailing/garbage ERROR region.

    FIX 1 (wave 1rrx5 delivery review, adversarial finding 1) support: guards
    the confidently-wrong TRUNCATE bind. Unlike DELETE/UPDATE (which need a
    `from`/`set` connective), tree-sitter-sql's TRUNCATE production accepts
    `TRUNCATE <ident>` with no connective keyword AND tolerates trailing
    tokens, so non-SQL prose at a SQL sink like `truncate events now` parses as
    a truncate of `events` plus a sibling ERROR `now` — binding a real table at
    LITERAL_DERIVED. Clean `TRUNCATE TABLE events` / `TRUNCATE events` parse
    with zero ERROR nodes. Returns False when the grammar is unavailable (the
    bind pass already handles that case separately).
    """
    tree = _ts_parse("sql", sql_text)
    if tree is None:
        return False
    return _sql_subtree_has_error(tree.root_node)


def _sql_embedded_has_interior_error(sql_text: str) -> bool:
    """True when a parse carries an ERROR node BEFORE the first table reference.

    R8 (wave 1rrx5, added after delivery review) support: generalizes FIX 1's
    clean-parse defense from the TRUNCATE arm to the DELETE/UPDATE/INSERT arm of
    the SAME confidently-wrong class. Non-SQL prose that leads with a sniff
    keyword and carries a mandatory-clause connective — `jdbc.update("delete the
    row from cache")` — mis-parses as a DELETE of `cache` whose interior `the
    row` becomes an ERROR node positioned BEFORE the `from` target. The
    recovered reference is coincidental prose recovery, not a real dependency,
    and must not bind.

    By contrast, VALID trailing dialect clauses tree-sitter-sql does not model
    (`DELETE FROM t RETURNING id`, `INSERT INTO t … ON CONFLICT DO …`, an
    unmodeled `DELETE FROM t USING src …` option tail) parse the core statement
    and its target cleanly and leave any ERROR *after* the first
    `object_reference` — those are TRAILING and are kept.

    Discriminator (empirically validated against the live tree-sitter-sql
    grammar before ship — change-doc R8 / AC-9): refuse when the earliest ERROR
    node starts before the earliest `object_reference` (the statement's target).
    Unlike the TRUNCATE any-ERROR gate, this distinguishes interior corruption
    from an unmodeled trailing clause, so valid dialect is not over-rejected.
    Returns False when the grammar is unavailable (handled separately by the
    bind pass) and when the parse has no ERROR at all; returns True on an ERROR
    with no parsed table target (the recovered reference, if any, is
    untrustworthy).
    """
    tree = _ts_parse("sql", sql_text)
    if tree is None:
        return False
    first_error: int | None = None
    first_ref: int | None = None
    stack = [tree.root_node]
    while stack:
        node = stack.pop()
        ntype = str(getattr(node, "type", "") or "")
        start = int(getattr(node, "start_byte", 0) or 0)
        if ntype == "ERROR":
            if first_error is None or start < first_error:
                first_error = start
        elif ntype == "object_reference":
            if first_ref is None or start < first_ref:
                first_ref = start
        stack.extend(list(getattr(node, "children", []) or []))
    if first_error is None:
        return False
    if first_ref is None:
        return True
    return first_error < first_ref


# Reserved external namespace for unmatched table references:
#   external::sql::<table-name-as-written>
#
# RELATION-SCOPED INVARIANT (mirrors the `_SUPER_CALL_PREFIX` /
# `_STATIC_OR_INHERITED_PREFIX` reserved-marker treatment above): the prefix
# is NOT globally unmintable — nothing stops a future emitter (or an exotic
# language construct) from producing an `external::sql::…`-shaped id on some
# OTHER relation (the nearest real precedent: Rust `use sql::x;` mints the
# DOTTED `external::sql.x` on `imports` — disjoint by form, pinned by test).
# The actual safety contract: (a) the finalize bind passes (embedded-SQL
# 1p9qf + ORM entity mapping 1p9qg) are the ONLY emitters of
# `external::sql::` targets, on `reads`/`writes`/`maps_to` edges, always at
# LITERAL_DERIVED confidence; (b) those edges are minted into the OUTPUT edge
# map only — they never enter per-file fragments, so phase-1 cross-file
# resolution (`_resolve_fragment_edge`) never sees, rewrites, or tombstones
# them; and (c) the bind passes never READ ids by prefix — bind candidates are
# `sql_kind`-carrying node_map entries only, so a source-minted lookalike id
# can never become a bind target. Pinned by ExternalSqlNamespaceInvariantTests.
_SQL_EXTERNAL_TABLE_PREFIX = "sql::"

# MyBatis mapper-XML capture-source marker: `mybatis::<namespace>::<stmt_id>`.
# Resolved at finalize to the mapper interface method / interface node when
# uniquely present in the project, else falls back to the XML file's module
# node (honest: the XML file demonstrably runs the SQL). Not mintable as a
# node id: node ids are `<rel_path>::<qname>` and an indexable file path
# always carries a suffix, so no file yields the bare `mybatis` head.
_MYBATIS_SOURCE_PREFIX = "mybatis::"

# MyBatis `#{param}` placeholders are prepared-statement bind params; replace
# with `?` (grammar-clean) before statement analysis. `${…}` is string
# SUBSTITUTION — dynamic SQL — and is refused at capture time.
_MYBATIS_PLACEHOLDER_RE = re.compile(r"#\{[^}]*\}")


def _sql_sanitize_embedded(sql_text: str) -> str:
    return _MYBATIS_PLACEHOLDER_RE.sub("?", sql_text)


# Quoted-identifier normalization for the BIND match only (census finding,
# Apache Fineract): MySQL dump DDL registers `` `m_loan` `` (backticks kept —
# the 1p9qd unit's names-as-written contract), while embedded Java SQL
# references the bare `m_loan`. The bind stage normalizes BOTH sides of its
# match (and the minted external name) by stripping identifier-quote
# characters; the statement unit's output itself is not touched.
_SQL_IDENT_QUOTE_CHARS = str.maketrans("", "", "`\"[]")


def _sql_normalize_object_name(name: str) -> str:
    return name.translate(_SQL_IDENT_QUOTE_CHARS).strip()


_STRING_ESCAPE_VALUES = {
    "\\n": "\n", "\\t": "\t", "\\r": "\r", "\\\"": '"', "\\'": "'",
    "\\\\": "\\", "\\0": "\0", "\\b": "\b", "\\f": "\f",
}


def _string_escape_value(raw: str) -> str:
    if raw in _STRING_ESCAPE_VALUES:
        return _STRING_ESCAPE_VALUES[raw]
    return raw[-1:] if raw.startswith("\\") and len(raw) == 2 else raw


def _ts_node_raw_text(node, source_bytes: bytes) -> str:
    """Node text WITHOUT the `_ts_node_text` strip — string-literal fragments
    carry significant leading/trailing whitespace (`"SELECT * " + "FROM t"`)."""
    try:
        return source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")
    except Exception:
        return ""


def _java_string_literal_value(node, source_bytes: bytes) -> str | None:
    """Decoded value of a Java ``string_literal`` (incl. text blocks); None otherwise."""
    if getattr(node, "type", "") != "string_literal":
        return None
    parts: list[str] = []
    for child in (getattr(node, "named_children", []) or []):
        ctype = str(getattr(child, "type", "") or "")
        if ctype in ("string_fragment", "multiline_string_fragment"):
            parts.append(_ts_node_raw_text(child, source_bytes))
        elif ctype == "escape_sequence":
            parts.append(_string_escape_value(_ts_node_raw_text(child, source_bytes)))
    return "".join(parts)  # empty literal ("" / """""") → ""


def _java_literal_string_expr(node, source_bytes: bytes) -> str | None:
    """Compile-time string value of a Java expression: a string literal or
    adjacent `+` concatenation of literals (Requirement 6). Anything touching
    a variable, call, or formatter returns None — refused, never guessed."""
    if node is None:
        return None
    n_type = str(getattr(node, "type", "") or "")
    if n_type == "string_literal":
        return _java_string_literal_value(node, source_bytes)
    if n_type == "parenthesized_expression":
        inner = [c for c in (getattr(node, "named_children", []) or [])]
        return _java_literal_string_expr(inner[0], source_bytes) if len(inner) == 1 else None
    if n_type == "binary_expression":
        try:
            op = node.child_by_field_name("operator")
            left = node.child_by_field_name("left")
            right = node.child_by_field_name("right")
        except Exception:
            return None
        if op is None or _ts_node_text(op, source_bytes).strip() != "+":
            return None
        left_val = _java_literal_string_expr(left, source_bytes)
        if left_val is None:
            return None
        right_val = _java_literal_string_expr(right, source_bytes)
        if right_val is None:
            return None
        return left_val + right_val
    return None


def _csharp_string_literal_value(node, source_bytes: bytes) -> str | None:
    """Decoded value of a C# string literal (regular / verbatim / raw); None otherwise."""
    n_type = str(getattr(node, "type", "") or "")
    if n_type == "string_literal":
        parts: list[str] = []
        for child in (getattr(node, "named_children", []) or []):
            ctype = str(getattr(child, "type", "") or "")
            if ctype == "string_literal_content":
                parts.append(_ts_node_raw_text(child, source_bytes))
            elif ctype == "escape_sequence":
                parts.append(_string_escape_value(_ts_node_raw_text(child, source_bytes)))
        return "".join(parts)
    if n_type == "verbatim_string_literal":
        raw = _ts_node_raw_text(node, source_bytes).strip()
        if raw.startswith("@\"") and raw.endswith("\""):
            return raw[2:-1].replace('""', '"')
        return None
    if n_type == "raw_string_literal":
        raw = _ts_node_raw_text(node, source_bytes)
        stripped = raw.strip()
        fence = '"""'
        if stripped.startswith(fence) and stripped.endswith(fence):
            return stripped[len(fence):-len(fence)].strip("\n")
        return None
    return None


def _csharp_literal_string_expr(node, source_bytes: bytes) -> str | None:
    """C# analogue of `_java_literal_string_expr` (interpolated strings → None)."""
    if node is None:
        return None
    n_type = str(getattr(node, "type", "") or "")
    if n_type in ("string_literal", "verbatim_string_literal", "raw_string_literal"):
        return _csharp_string_literal_value(node, source_bytes)
    if n_type == "parenthesized_expression":
        inner = [c for c in (getattr(node, "named_children", []) or [])]
        return _csharp_literal_string_expr(inner[0], source_bytes) if len(inner) == 1 else None
    if n_type == "binary_expression":
        try:
            op = node.child_by_field_name("operator")
            left = node.child_by_field_name("left")
            right = node.child_by_field_name("right")
        except Exception:
            return None
        if op is None or _ts_node_text(op, source_bytes).strip() != "+":
            return None
        left_val = _csharp_literal_string_expr(left, source_bytes)
        if left_val is None:
            return None
        right_val = _csharp_literal_string_expr(right, source_bytes)
        if right_val is None:
            return None
        return left_val + right_val
    return None


def _ts_java_annotation_records(node, source_bytes: bytes) -> list[dict[str, Any]]:
    """Structured annotation records for a Java declaration node.

    THE SHARED ANNOTATION-ARGUMENT SEAM (wave 1p9qi): built by `1p9qf` for the
    SQL sinks; `1p9qg` extends the same records for JPA `@Table`/`@Column`
    entity mappings. Each record is
    ``{"name": str, "args": [value_node, ...], "pairs": {ident: value_node}}``
    where `name` is the annotation name verbatim (possibly qualified), `args`
    are POSITIONAL argument AST nodes in order, and `pairs` maps
    `element_value_pair` identifiers to their value AST nodes. Values stay AST
    nodes (not strings) so each consumer applies its own interpretation —
    string literals via `_java_literal_string_expr`, booleans/arrays via node
    text/type. `marker_annotation` yields a record with empty args/pairs.
    """
    records: list[dict[str, Any]] = []
    try:
        children = list(getattr(node, "named_children", []) or [])
    except Exception:
        return records
    for child in children:
        if (getattr(child, "type", "") or "") != "modifiers":
            continue
        for ann in (getattr(child, "named_children", []) or []):
            ann_type = getattr(ann, "type", "") or ""
            if ann_type not in ("marker_annotation", "annotation"):
                continue
            try:
                name_node = ann.child_by_field_name("name")
            except Exception:
                name_node = None
            if name_node is None:
                continue
            name = _ts_node_text(name_node, source_bytes).strip()
            if not name:
                continue
            record: dict[str, Any] = {"name": name, "args": [], "pairs": {}}
            try:
                args = ann.child_by_field_name("arguments")
            except Exception:
                args = None
            for arg in (getattr(args, "named_children", []) or []):
                arg_type = str(getattr(arg, "type", "") or "")
                if arg_type == "element_value_pair":
                    pair_children = [c for c in (getattr(arg, "named_children", []) or [])]
                    if len(pair_children) >= 2 and getattr(pair_children[0], "type", "") == "identifier":
                        key = _ts_node_text(pair_children[0], source_bytes).strip()
                        if key:
                            record["pairs"][key] = pair_children[1]
                else:
                    record["args"].append(arg)
            records.append(record)
    return records


def _ts_csharp_attribute_records(node, source_bytes: bytes) -> list[dict[str, Any]]:
    """Structured attribute records for a C# declaration node.

    C# side of the shared annotation/attribute-argument seam (see
    `_ts_java_annotation_records`); `1p9qg` consumes it for EF
    `[Table("…")]`/`[Column("…")]` mappings. Same record shape:
    ``{"name": str, "args": [value_node, ...], "pairs": {ident: value_node}}``
    — positional `attribute_argument`s land in `args` (the value node is the
    argument's expression); named arguments (`Name = expr` and `name: expr`)
    land in `pairs`.
    """
    records: list[dict[str, Any]] = []
    try:
        children = list(getattr(node, "named_children", []) or [])
    except Exception:
        return records
    for child in children:
        if (getattr(child, "type", "") or "") != "attribute_list":
            continue
        for attr in (getattr(child, "named_children", []) or []):
            if (getattr(attr, "type", "") or "") != "attribute":
                continue
            try:
                name_node = attr.child_by_field_name("name")
            except Exception:
                name_node = None
            if name_node is None:
                continue
            name = _ts_node_text(name_node, source_bytes).strip()
            if not name:
                continue
            record: dict[str, Any] = {"name": name, "args": [], "pairs": {}}
            arg_list = None
            for ac in (getattr(attr, "named_children", []) or []):
                if getattr(ac, "type", "") == "attribute_argument_list":
                    arg_list = ac
                    break
            for arg in (getattr(arg_list, "named_children", []) or []):
                if str(getattr(arg, "type", "") or "") != "attribute_argument":
                    continue
                named = [c for c in (getattr(arg, "named_children", []) or [])]
                if not named:
                    continue
                head_type = str(getattr(named[0], "type", "") or "")
                if len(named) >= 2 and head_type == "identifier":
                    key = _ts_node_text(named[0], source_bytes).strip()
                    if key:
                        record["pairs"][key] = named[1]
                elif head_type == "name_colon":
                    key = _ts_node_text(named[0], source_bytes).strip().rstrip(":").strip()
                    if key and len(named) >= 2:
                        record["pairs"][key] = named[1]
                else:
                    record["args"].append(named[0])
            records.append(record)
    return records


# Java annotation sinks (Requirement 1): MyBatis statement annotations carry
# SQL directly; Spring/JPA `@Query` only with `nativeQuery = true` (JPQL is
# entity-space — `1p9qg`'s job, Requirement 7); `@NamedNativeQuery` carries
# SQL in its `query` element.
_JAVA_MYBATIS_SQL_ANNOTATIONS = frozenset({"Select", "Insert", "Update", "Delete"})
_JAVA_SQL_SINK_ANNOTATIONS = _JAVA_MYBATIS_SQL_ANNOTATIONS | {"Query", "NamedNativeQuery"}


def _java_annotation_string_value(node, source_bytes: bytes) -> str | None:
    """String value of an annotation element: a literal/concat expression, or
    a MyBatis-style array of literals (`{"…", "…"}` — joined with spaces)."""
    if node is None:
        return None
    if str(getattr(node, "type", "") or "") == "element_value_array_initializer":
        parts: list[str] = []
        for child in (getattr(node, "named_children", []) or []):
            val = _java_literal_string_expr(child, source_bytes)
            if val is None:
                return None  # any non-literal element → dynamic
            parts.append(val)
        return " ".join(parts) if parts else None
    return _java_literal_string_expr(node, source_bytes)


def _java_annotation_sql_captures(node, source_bytes: bytes) -> tuple[list[str], int]:
    """(sql_texts, dynamic_refusals) from a Java declaration's SQL-sink annotations."""
    captures: list[str] = []
    dynamic = 0
    for record in _ts_java_annotation_records(node, source_bytes):
        tail = record["name"].rsplit(".", 1)[-1]
        if tail in _JAVA_MYBATIS_SQL_ANNOTATIONS:
            value_node = record["pairs"].get("value") or (record["args"][0] if record["args"] else None)
        elif tail == "Query":
            native = record["pairs"].get("nativeQuery")
            if native is None or _ts_node_text(native, source_bytes).strip() != "true":
                continue  # JPQL — out of scope by design, not a dynamic refusal
            value_node = record["pairs"].get("value") or (record["args"][0] if record["args"] else None)
        elif tail == "NamedNativeQuery":
            value_node = record["pairs"].get("query")
        else:
            continue
        if value_node is None:
            continue
        text = _java_annotation_string_value(value_node, source_bytes)
        if text is None:
            dynamic += 1  # sink hit with a non-literal value → refused, counted
            continue
        if "${" in text:
            dynamic += 1  # MyBatis string substitution → dynamic SQL
            continue
        if _sql_text_sniffs_as_sql(text):
            captures.append(text)
    return captures, dynamic


# Java call sinks (Requirement 1): JDBC prepare methods (distinctive names —
# negative origin check) and JdbcTemplate query methods (generic names —
# positive origin check on the receiver's declared type).
_JAVA_JDBC_PREPARE_METHODS = frozenset({"prepareStatement", "prepareCall"})
_JAVA_JDBC_TEMPLATE_TYPES = frozenset({"JdbcTemplate", "NamedParameterJdbcTemplate"})
_JAVA_JDBC_TEMPLATE_METHODS = frozenset({
    "query", "queryForObject", "queryForList", "queryForMap", "queryForRowSet",
    "queryForStream", "update", "batchUpdate", "execute",
})


def _java_call_sql_capture(
    invocation_node, source_bytes: bytes, symbol_lookup: dict[str, str]
) -> tuple[str | None, int]:
    """(sql_text | None, dynamic_refusals) for a Java `method_invocation` at a
    JDBC/JdbcTemplate sink. See the section comment for the origin-check
    convention; the sniff gate drops non-SQL strings silently."""
    try:
        name_node = invocation_node.child_by_field_name("name")
    except Exception:
        return None, 0
    if name_node is None:
        return None, 0
    method_name = _ts_node_text(name_node, source_bytes).strip()
    is_prepare = method_name in _JAVA_JDBC_PREPARE_METHODS
    is_template = method_name in _JAVA_JDBC_TEMPLATE_METHODS
    if not (is_prepare or is_template):
        return None, 0
    obj = invocation_node.child_by_field_name("object")
    if obj is None:
        return None, 0  # bare call → own/inherited method, never a JDBC receiver
    receiver_type = _resolve_java_receiver_type(invocation_node, source_bytes)
    if is_template and not is_prepare and receiver_type not in _JAVA_JDBC_TEMPLATE_TYPES:
        return None, 0  # generic method name: positive origin required
    if receiver_type is not None and (
        receiver_type in symbol_lookup or f"{receiver_type}.{method_name}" in symbol_lookup
    ):
        return None, 0  # receiver resolves to a PROJECT type → impostor, refuse
    args = invocation_node.child_by_field_name("arguments")
    first = next(iter(getattr(args, "named_children", []) or []), None)
    if first is None:
        return None, 0
    text = _java_literal_string_expr(first, source_bytes)
    if text is None:
        return None, 1  # sink hit, dynamic argument → refused, counted
    if "${" in text:
        return None, 1
    if not _sql_text_sniffs_as_sql(text):
        return None, 0  # non-SQL string at a sink → silent drop (Requirement 4)
    return text, 0


# C# sinks (Requirement 2): ADO.NET command constructors + CommandText
# assignment, Dapper extension methods, EF Core raw-SQL methods.
_CSHARP_ADO_COMMAND_TYPES = frozenset({
    "SqlCommand", "SqliteCommand", "NpgsqlCommand", "MySqlCommand", "OracleCommand",
})
_CSHARP_DAPPER_METHODS = frozenset({
    "Query", "QueryAsync", "QueryFirst", "QueryFirstAsync",
    "QueryFirstOrDefault", "QueryFirstOrDefaultAsync",
    "QuerySingle", "QuerySingleAsync", "QuerySingleOrDefault",
    "QuerySingleOrDefaultAsync", "QueryMultiple", "QueryMultipleAsync",
    "Execute", "ExecuteAsync", "ExecuteScalar", "ExecuteScalarAsync",
    "ExecuteReader", "ExecuteReaderAsync",
})
_CSHARP_EF_RAW_METHODS = frozenset({
    "FromSqlRaw", "ExecuteSqlRaw", "ExecuteSqlRawAsync", "SqlQueryRaw",
})


def _csharp_first_argument_expr(args_node):
    """The expression of the first argument in a C# `argument_list`
    (arguments are wrapped in `argument` nodes)."""
    first = next(iter(getattr(args_node, "named_children", []) or []), None)
    if first is None:
        return None
    if str(getattr(first, "type", "") or "") == "argument":
        return next(iter(getattr(first, "named_children", []) or []), None)
    return first


def _csharp_call_sql_capture(
    node, node_type: str, source_bytes: bytes, symbol_lookup: dict[str, str]
) -> tuple[str | None, int]:
    """(sql_text | None, dynamic_refusals) for a C# `invocation_expression`
    (Dapper / EF raw) or `object_creation_expression` (ADO.NET command)."""
    if node_type == "object_creation_expression":
        type_name = ""
        for child in (getattr(node, "named_children", []) or []):
            ctype = str(getattr(child, "type", "") or "")
            if ctype in ("identifier", "qualified_name", "generic_name"):
                type_name = _ts_node_text(child, source_bytes).strip()
                break
            if ctype == "argument_list":
                break
        tail = type_name.split("<", 1)[0].rsplit(".", 1)[-1].strip()
        if tail not in _CSHARP_ADO_COMMAND_TYPES:
            return None, 0
        if tail in symbol_lookup:
            return None, 0  # project-defined impostor type
        args = None
        for child in (getattr(node, "named_children", []) or []):
            if str(getattr(child, "type", "") or "") == "argument_list":
                args = child
                break
        expr = _csharp_first_argument_expr(args) if args is not None else None
        if expr is None:
            return None, 0
        text = _csharp_literal_string_expr(expr, source_bytes)
        if text is None:
            return None, 1
        if not _sql_text_sniffs_as_sql(text):
            return None, 0
        return text, 0
    if node_type != "invocation_expression":
        return None, 0
    children = list(getattr(node, "children", []) or [])
    if not children:
        return None, 0
    callee = children[0]
    if str(getattr(callee, "type", "") or "") != "member_access_expression":
        return None, 0  # bare call is never an extension-method / EF sink
    try:
        name_node = callee.child_by_field_name("name")
    except Exception:
        name_node = None
    if name_node is not None and str(getattr(name_node, "type", "") or "") == "generic_name":
        name_node = next(
            (c for c in (getattr(name_node, "named_children", []) or [])
             if str(getattr(c, "type", "") or "") == "identifier"),
            name_node,
        )
    method_name = _ts_node_text(name_node, source_bytes).strip() if name_node is not None else ""
    method_name = method_name.split("<", 1)[0].strip()
    if method_name not in _CSHARP_DAPPER_METHODS and method_name not in _CSHARP_EF_RAW_METHODS:
        return None, 0
    receiver_type = _resolve_csharp_receiver_type(node, source_bytes)
    if receiver_type is not None and (
        receiver_type in symbol_lookup or f"{receiver_type}.{method_name}" in symbol_lookup
    ):
        return None, 0  # receiver resolves to a PROJECT type → impostor, refuse
    args = None
    for child in (getattr(node, "named_children", []) or []):
        if str(getattr(child, "type", "") or "") == "argument_list":
            args = child
            break
    expr = _csharp_first_argument_expr(args) if args is not None else None
    if expr is None:
        return None, 0
    text = _csharp_literal_string_expr(expr, source_bytes)
    if text is None:
        return None, 1  # dynamic (variable / interpolated / builder) → counted
    if not _sql_text_sniffs_as_sql(text):
        return None, 0
    return text, 0


def _csharp_commandtext_sql_capture(assign_node, source_bytes: bytes) -> tuple[str | None, int]:
    """(sql_text | None, dynamic_refusals) for a C# `<expr>.CommandText = <rhs>`
    assignment. The property name is the sink signal (receiver types are
    rarely resolvable for command objects); the sniff gate bounds it."""
    try:
        left = assign_node.child_by_field_name("left")
        right = assign_node.child_by_field_name("right")
    except Exception:
        return None, 0
    if left is None or str(getattr(left, "type", "") or "") != "member_access_expression":
        return None, 0
    try:
        prop = left.child_by_field_name("name")
    except Exception:
        prop = None
    if prop is None or _ts_node_text(prop, source_bytes).strip() != "CommandText":
        return None, 0
    if right is None:
        return None, 0
    text = _csharp_literal_string_expr(right, source_bytes)
    if text is None:
        return None, 1
    if not _sql_text_sniffs_as_sql(text):
        return None, 0
    return text, 0


# MyBatis mapper XML (Requirement 3): `<mapper namespace="…">` files
# contribute `<select>/<insert>/<update>/<delete>` statement text with the
# owning mapper namespace + statement id as the capture source. Statements
# containing dynamic-SQL child elements (`<if>`, `<where>`, `<include>`, …)
# or `${…}` substitution are refused and counted.
_MYBATIS_STATEMENT_TAGS = frozenset({"select", "insert", "update", "delete"})


def _xml_stag_info(element_node, source_bytes: bytes) -> tuple[str, dict[str, str], Any]:
    """(tag_name, attributes, end_tag_node) for an XML `element` node."""
    tag = ""
    attrs: dict[str, str] = {}
    etag = None
    for child in (getattr(element_node, "named_children", []) or []):
        ctype = str(getattr(child, "type", "") or "")
        if ctype in ("STag", "EmptyElemTag"):
            for c in (getattr(child, "named_children", []) or []):
                c_type = str(getattr(c, "type", "") or "")
                if c_type == "Name" and not tag:
                    tag = _ts_node_text(c, source_bytes).strip()
                elif c_type == "Attribute":
                    a_name = ""
                    a_val = ""
                    for ac in (getattr(c, "named_children", []) or []):
                        ac_type = str(getattr(ac, "type", "") or "")
                        if ac_type == "Name":
                            a_name = _ts_node_text(ac, source_bytes).strip()
                        elif ac_type == "AttValue":
                            a_val = _ts_node_text(ac, source_bytes).strip().strip("\"'")
                    if a_name:
                        attrs[a_name] = a_val
        elif ctype == "ETag":
            etag = child
    return tag, attrs, etag


def _mybatis_mapper_captures(root_node, source_bytes: bytes) -> tuple[list[tuple[str, str, str]], int]:
    """([(namespace, stmt_id, sql_text)], dynamic_refusals) for a MyBatis
    mapper XML document; ([], 0) when the root element is not a `<mapper>`."""
    captures: list[tuple[str, str, str]] = []
    dynamic = 0
    mapper_el = None
    namespace = ""
    for child in (getattr(root_node, "named_children", []) or []):
        if str(getattr(child, "type", "") or "") == "element":
            tag, attrs, _ = _xml_stag_info(child, source_bytes)
            if tag == "mapper":
                namespace = (attrs.get("namespace") or "").strip()
                mapper_el = child
            break  # XML has a single root element
    if mapper_el is None or not namespace:
        return captures, dynamic
    content = next(
        (c for c in (getattr(mapper_el, "named_children", []) or [])
         if str(getattr(c, "type", "") or "") == "content"),
        None,
    )
    for el in (getattr(content, "named_children", []) or []):
        if str(getattr(el, "type", "") or "") != "element":
            continue
        tag, attrs, _ = _xml_stag_info(el, source_bytes)
        if tag not in _MYBATIS_STATEMENT_TAGS:
            continue
        stmt_id = (attrs.get("id") or "").strip()
        if not stmt_id:
            continue
        stmt_content = next(
            (c for c in (getattr(el, "named_children", []) or [])
             if str(getattr(c, "type", "") or "") == "content"),
            None,
        )
        if stmt_content is None:
            continue
        if any(
            str(getattr(c, "type", "") or "") == "element"
            for c in (getattr(stmt_content, "named_children", []) or [])
        ):
            dynamic += 1  # dynamic-SQL tags → refused, counted
            continue
        text = _ts_node_text(stmt_content, source_bytes)
        text = text.replace("<![CDATA[", " ").replace("]]>", " ").strip()
        if "${" in text:
            dynamic += 1
            continue
        if text and _sql_text_sniffs_as_sql(text):
            captures.append((namespace, stmt_id, text))
    return captures, dynamic


def _resolve_sql_capture_source(
    marker: str,
    fragment_rel: str,
    node_map: dict[str, dict[str, Any]],
    simple_name_index: dict[str, list[str]],
    qualified_index: dict[str, list[str]],
) -> str | None:
    """Resolve a capture-source marker to a live node id for the bind edge.

    Code captures carry the extraction-time node id (fall back to the file's
    module node when the symbol collapsed — mirrors the `instruments` carrier
    fallback). MyBatis markers (`mybatis::<ns>::<id>`) resolve to the unique
    mapper interface METHOD, then the unique interface, else the XML file's
    module node — unique-or-fallback, never an ambiguous guess."""
    if marker.startswith(_MYBATIS_SOURCE_PREFIX):
        rest = marker[len(_MYBATIS_SOURCE_PREFIX):]
        ns, _, stmt_id = rest.rpartition("::")
        simple_ns = ns.rsplit(".", 1)[-1]
        if ns and stmt_id:
            for key in (f"{ns}.{stmt_id}", f"{simple_ns}.{stmt_id}"):
                hits = qualified_index.get(key) or []
                if len(hits) == 1:
                    return hits[0]
            hits = simple_name_index.get(simple_ns) or []
            if len(hits) == 1:
                return hits[0]
        return fragment_rel if fragment_rel in node_map else None
    if marker in node_map:
        return marker
    file_part = marker.split("::", 1)[0]
    return file_part if file_part in node_map else None


# =============================================================================
# ORM entity→table mapping capture (wave 1p9qi / 1p9qg).
#
# DECLARED names only: JPA `@Entity` + `@Table(name = "…"[, schema = "…"])`
# or `@Entity(name = "…")` (Java), EF `[Table("…"[, Schema = "…"])]` or
# fluent `ToTable("…"[, "schema"])` (C#). Convention-derived names (JPA
# implicit naming / snake_casing, EF pluralization) are REFUSED and counted
# per file (`orm_entity_convention`) so the recall cost stays measurable;
# computed / constant-reference names refuse as dynamic
# (`orm_entity_dynamic`) — only string literals bind. Candidates ride
# per-file fragments (`orm_entity_candidates`, entries
# ``[source_marker, declared_table]``) and bind at finalize on the dedicated
# `maps_to` relation (see GRAPH_MAPS_TO_RELATION) with the same
# unique-match-or-drop + `external::sql::` semantics as the embedded-SQL
# bind pass above. Extends the shared annotation/attribute-argument seam
# (`_ts_java_annotation_records` / `_ts_csharp_attribute_records`).
# =============================================================================

# Capture-source marker for EF fluent `ToTable` sinks, where the entity class
# is named by the `.Entity<T>()` / `EntityTypeBuilder<T>` type argument and
# lives in another file: `entitytype::<TypeNameAsWritten>`. Resolved at
# finalize to the UNIQUE project class node of that name (kind-gated) — an
# ambiguous or missing entity type drops the candidate, never a guess. Not
# mintable as a node id (node ids are `<rel_path>::<qname>`; an indexable
# file path always carries a suffix, so no file yields the bare
# `entitytype` head — same argument as `_MYBATIS_SOURCE_PREFIX`).
_ORM_ENTITY_TYPE_PREFIX = "entitytype::"

# C# attribute tails accepted for `[Table("…")]` (attribute usage may spell
# either form; both name System.ComponentModel.DataAnnotations.Schema).
_CSHARP_TABLE_ATTRIBUTE_TAILS = frozenset({"Table", "TableAttribute"})


def _java_entity_table_mapping(
    node, source_bytes: bytes, symbol_lookup: dict[str, str]
) -> tuple[str | None, int, int]:
    """(declared_table | None, dynamic_refusals, convention_refusals) for a
    Java class declaration.

    Fires only for `@Entity` classes — the `@Entity` presence is the origin
    gate (a bare `@Table` without `@Entity` is some other framework's
    annotation). A same-file project-defined `Entity`/`Table` annotation
    TYPE refuses (impostor check, same-file scope like the 1p9qf sinks).
    Declared-name precedence: `@Table(name = …)` wins; `@Entity(name = …)`
    is the JPA-spec explicit entity name (table name defaults to it) and
    binds only when `@Table` declares no name. A present-but-non-literal
    name or schema element refuses the WHOLE mapping as dynamic (never a
    partial guess); `@Entity` with no declared name anywhere is the counted
    convention refusal.
    """
    records = _ts_java_annotation_records(node, source_bytes)
    entity = None
    table = None
    for record in records:
        tail = record["name"].rsplit(".", 1)[-1]
        if tail == "Entity" and entity is None:
            entity = record
        elif tail == "Table" and table is None:
            table = record
    if entity is None:
        return None, 0, 0
    if "Entity" in symbol_lookup or (table is not None and "Table" in symbol_lookup):
        return None, 0, 0  # project-defined annotation type → impostor, refuse
    schema: str | None = None
    name_value: str | None = None
    if table is not None:
        schema_node = table["pairs"].get("schema")
        if schema_node is not None:
            schema = _java_literal_string_expr(schema_node, source_bytes)
            if schema is None:
                return None, 1, 0  # computed schema → dynamic refusal
        name_node = table["pairs"].get("name")
        if name_node is not None:
            name_value = _java_literal_string_expr(name_node, source_bytes)
            if name_value is None:
                return None, 1, 0  # @Table(name = CONSTANT/expr) → dynamic
    if name_value is None:
        entity_name_node = entity["pairs"].get("name")
        if entity_name_node is not None:
            name_value = _java_literal_string_expr(entity_name_node, source_bytes)
            if name_value is None:
                return None, 1, 0
    if not name_value:
        return None, 0, 1  # @Entity with no declared name → convention refusal
    return (f"{schema}.{name_value}" if schema else name_value), 0, 0


def _csharp_entity_table_mapping(
    node, source_bytes: bytes, symbol_lookup: dict[str, str]
) -> tuple[str | None, int, int]:
    """(declared_table | None, dynamic_refusals, convention_refusals) for a
    C# class declaration carrying `[Table("…")]`
    (System.ComponentModel.DataAnnotations.Schema).

    The positional first argument is the table name; the optional `Schema`
    named property qualifies it. A same-file project-defined
    `Table`/`TableAttribute` type refuses (impostor). C# has no `@Entity`
    analog, so the convention counter never fires on this path — EF's
    convention-mapped entities are a census-measured gap, not a countable
    per-file fact.
    """
    records = _ts_csharp_attribute_records(node, source_bytes)
    table = None
    for record in records:
        if record["name"].rsplit(".", 1)[-1] in _CSHARP_TABLE_ATTRIBUTE_TAILS:
            table = record
            break
    if table is None:
        return None, 0, 0
    if any(tail in symbol_lookup for tail in _CSHARP_TABLE_ATTRIBUTE_TAILS):
        return None, 0, 0  # project-defined attribute type → impostor, refuse
    if not table["args"]:
        return None, 0, 0  # [Table] without a name is not a declaration
    name_value = _csharp_literal_string_expr(table["args"][0], source_bytes)
    if name_value is None:
        return None, 1, 0  # nameof(…)/constant/interpolation → dynamic
    schema_node = table["pairs"].get("Schema")
    schema: str | None = None
    if schema_node is not None:
        schema = _csharp_literal_string_expr(schema_node, source_bytes)
        if schema is None:
            return None, 1, 0
    return (f"{schema}.{name_value}" if schema else name_value), 0, 0


def _csharp_generic_single_type_argument(generic_name_node, source_bytes: bytes) -> str | None:
    """The single type argument's text of a C# `generic_name` node, or None."""
    for child in (getattr(generic_name_node, "named_children", []) or []):
        if str(getattr(child, "type", "") or "") == "type_argument_list":
            args = list(getattr(child, "named_children", []) or [])
            if len(args) == 1:
                text = _ts_node_text(args[0], source_bytes).strip()
                return text or None
            return None
    return None


def _csharp_totable_capture(
    node, source_bytes: bytes
) -> tuple[str | None, str | None, int]:
    """(entity_source_marker | None, declared_table | None, dynamic_refusals)
    for a C# `invocation_expression` at the EF fluent `ToTable("…")` sink.

    POSITIVE origin identification by construction (the origin-check
    convention's generic-name arm): the entity type must be recoverable from
    the call shape — either the receiver chain contains `.Entity<T>()`
    (`modelBuilder.Entity<User>().ToTable("users")`) or the receiver is an
    identifier the enclosing method declares as an `EntityTypeBuilder<T>`
    parameter (the `IEntityTypeConfiguration<T>.Configure` idiom). An
    impostor `ToTable` on any other receiver never fires. `ToTable("name",
    "schema")` declares a schema-qualified table; a builder-action overload
    (`ToTable(tb => …)`) declares no name and is skipped silently; any other
    non-literal argument is a counted dynamic refusal.
    """
    children = list(getattr(node, "children", []) or [])
    if not children:
        return None, None, 0
    callee = children[0]
    if str(getattr(callee, "type", "") or "") != "member_access_expression":
        return None, None, 0
    try:
        name_node = callee.child_by_field_name("name")
    except Exception:
        name_node = None
    if name_node is None:
        return None, None, 0
    method_name = _ts_node_text(name_node, source_bytes).strip().split("<", 1)[0].strip()
    if method_name != "ToTable":
        return None, None, 0
    try:
        receiver = callee.child_by_field_name("expression")
    except Exception:
        receiver = None
    entity_type: str | None = None
    cursor = receiver
    while cursor is not None and entity_type is None:
        cursor_type = str(getattr(cursor, "type", "") or "")
        if cursor_type == "invocation_expression":
            inner = next(iter(getattr(cursor, "children", []) or []), None)
            if inner is None or str(getattr(inner, "type", "") or "") != "member_access_expression":
                break
            try:
                inner_name = inner.child_by_field_name("name")
            except Exception:
                inner_name = None
            if (
                inner_name is not None
                and str(getattr(inner_name, "type", "") or "") == "generic_name"
                and _ts_node_text(inner_name, source_bytes).strip().startswith("Entity<")
            ):
                entity_type = _csharp_generic_single_type_argument(inner_name, source_bytes)
                break
            try:
                cursor = inner.child_by_field_name("expression")
            except Exception:
                break
        elif cursor_type == "member_access_expression":
            try:
                cursor = cursor.child_by_field_name("expression")
            except Exception:
                break
        elif cursor_type == "identifier":
            entity_type = _csharp_entity_builder_param_type(
                cursor, _ts_node_text(cursor, source_bytes).strip(), source_bytes
            )
            break
        else:
            break
    if not entity_type:
        return None, None, 0  # origin not established → not a sink, never fires
    marker = f"{_ORM_ENTITY_TYPE_PREFIX}{entity_type}"
    args = None
    for child in (getattr(node, "named_children", []) or []):
        if str(getattr(child, "type", "") or "") == "argument_list":
            args = child
            break
    arg_exprs: list[Any] = []
    for arg in (getattr(args, "named_children", []) or []):
        if str(getattr(arg, "type", "") or "") == "argument":
            expr = next(iter(getattr(arg, "named_children", []) or []), None)
            if expr is not None:
                arg_exprs.append(expr)
    if not arg_exprs:
        return marker, None, 0
    first = arg_exprs[0]
    name_value = _csharp_literal_string_expr(first, source_bytes)
    if name_value is None:
        if str(getattr(first, "type", "") or "") in ("lambda_expression", "anonymous_method_expression"):
            return marker, None, 0  # builder-action overload — no name declared
        return marker, None, 1  # variable/interpolated/constant name → dynamic
    schema: str | None = None
    if len(arg_exprs) >= 2:
        second = arg_exprs[1]
        second_type = str(getattr(second, "type", "") or "")
        schema = _csharp_literal_string_expr(second, source_bytes)
        if schema is None and second_type not in (
            "lambda_expression", "anonymous_method_expression"
        ):
            return marker, None, 1  # computed schema → whole mapping dynamic
    return marker, (f"{schema}.{name_value}" if schema else name_value), 0


def _csharp_entity_builder_param_type(identifier_node, identifier_text: str, source_bytes: bytes) -> str | None:
    """Entity type T when `identifier_text` names a parameter of the enclosing
    C# method declared as `EntityTypeBuilder<T>`; None otherwise."""
    if not identifier_text:
        return None
    cursor = getattr(identifier_node, "parent", None)
    depth = 0
    while cursor is not None and depth < 64:
        if str(getattr(cursor, "type", "") or "") in ("method_declaration", "local_function_statement"):
            break
        cursor = getattr(cursor, "parent", None)
        depth += 1
    if cursor is None:
        return None
    params = None
    for child in (getattr(cursor, "named_children", []) or []):
        if str(getattr(child, "type", "") or "") == "parameter_list":
            params = child
            break
    for param in (getattr(params, "named_children", []) or []):
        if str(getattr(param, "type", "") or "") != "parameter":
            continue
        try:
            p_name = param.child_by_field_name("name")
            p_type = param.child_by_field_name("type")
        except Exception:
            continue
        if p_name is None or p_type is None:
            continue
        if _ts_node_text(p_name, source_bytes).strip() != identifier_text:
            continue
        if str(getattr(p_type, "type", "") or "") != "generic_name":
            return None
        head = _ts_node_text(p_type, source_bytes).strip().split("<", 1)[0].strip()
        if head.rsplit(".", 1)[-1] != "EntityTypeBuilder":
            return None
        return _csharp_generic_single_type_argument(p_type, source_bytes)
    return None


def _resolve_orm_entity_source(
    marker: str,
    fragment_rel: str,
    node_map: dict[str, dict[str, Any]],
    simple_name_index: dict[str, list[str]],
    qualified_index: dict[str, list[str]],
) -> str | None:
    """Resolve an ORM-mapping capture source to a live node id.

    Annotation captures carry the extraction-time class node id (module id
    when the class collapsed into the file node) — same treatment as the
    embedded-SQL sources. `entitytype::<T>` markers (EF `ToTable`) resolve to
    the UNIQUE project class-kind node named T (qualified-exact first, then
    unique simple name); ambiguity or absence drops the candidate — an
    entity mapping bound to the wrong same-name twin is exactly the silent
    mis-bind the confidence taxonomy forbids.
    """
    if marker.startswith(_ORM_ENTITY_TYPE_PREFIX):
        type_name = marker[len(_ORM_ENTITY_TYPE_PREFIX):].strip()
        if not type_name:
            return None
        leaf = type_name.rsplit(".", 1)[-1]
        keys: list[tuple[dict[str, list[str]], str]] = [(qualified_index, type_name)]
        if leaf != type_name:
            keys.append((qualified_index, leaf))
        keys.append((simple_name_index, leaf))
        for index, key in keys:
            hits = [
                hit for hit in (index.get(key) or [])
                if (node_map.get(hit) or {}).get("kind") == "class"
            ]
            if len(hits) == 1:
                return hits[0]
            if hits:
                return None  # ambiguous entity type → drop, never guess
        return None
    return _resolve_sql_capture_source(
        marker, fragment_rel, node_map, simple_name_index, qualified_index
    )


def _ts_extract_callee_positional(node, source_bytes: bytes) -> str | None:
    """Fallback for grammars whose call_expression has no callee field name.

    Walks the call node's named_children, skips argument/suffix-like nodes,
    and recursively extracts the rightmost identifier from the first
    remaining child. Used by ``_ts_relation_candidates`` when the field-name
    lookup returns empty (Swift, Kotlin) — safe because the caller has
    already confirmed the node is a call (per ``profile.call_node_types``).
    """
    for child in node.named_children:
        if child.type in _TS_ARGS_NODE_TYPES:
            continue
        candidate = _ts_extract_callee_recursive(child, source_bytes)
        if candidate:
            return candidate
    return None


# ---------------------------------------------------------------------------
# SQL clause-aware statement analysis (wave 1p9qi / 1p9qd)
#
# The single shared extraction path for SQL statements. Replaces the retired
# generic substring-match + regex-candidate pipeline for SQL mode entirely:
# table references come from `object_reference` positions in specific clause
# roles, each carrying a read/write direction, and query-local names (CTEs,
# aliases, derived-table aliases, temp tables / table variables) never become
# references or definitions.
#
# CONTRACT (frozen for the wave — `1p9qe` ERROR-region body recovery and
# `1p9qf` embedded-SQL binding consume this as-is):
#
#   sql_statement_references(sql_text)  -> dict | None
#     None when the SQL grammar is unavailable; otherwise
#     {"references": [ref, ...], "definitions": [defn, ...], "error_regions": int,
#      "recovery": {"recovered_definitions": int, "unrecovered_regions": int}}
#     with script-level exclusions (temp-object names) already applied.
#
#   ref  = {"name": str,        # reference text as written ("users", "analytics.events")
#           "schema": str|None, # schema segment when written schema-qualified
#           "direction": "read"|"write",
#           "clause": one of _SQL_REF_CLAUSES,
#           "statement": statement-kind string ("select", "insert", ...),
#           "owner": str|None,  # enclosing definition's name (view lineage), None = script level
#           "extraction": None|"sql_recovery"}  # "sql_recovery" = ERROR-region provenance.
#           # BOTH recovery re-attribution forms carry the marker: region-tail
#           # re-parses AND dangling-block re-attributions (each depends on the
#           # recovery tier having identified the owning routine).
#   defn = {"name": str,        # dotted-full when schema-qualified
#           "schema": str|None,
#           "sql_kind": "table"|"view"|"procedure"|"function"|"trigger",
#           "temporary": bool,
#           "extraction": None|"sql_recovery"}  # None = trusted parse; marker = recovery tier
#
# Guarantees:
#   * Zero references from SQL keywords, column tokens, string literals, or
#     alias/CTE/temp names (AC-6) — references are structural clause
#     positions, never token scans.
#   * Scalar function invocation NAMES are excluded: an
#     `invocation > object_reference` (`NOW()`, `UPPER(x)`, `dbo.fn(a)`) is a
#     routine name, never a table reference — the invocation's ARGUMENT
#     subtree is still walked, so a table read inside an argument subquery is
#     preserved. A routine invoked in a RELATION position (a table-valued
#     function — `FROM generate_series(...)`) likewise emits no table
#     reference: a routine call is not a table (the recorded
#     routine-invocation stance; a `call` clause is future field-demand work).
#   * Read/write direction is statement-derived: FROM/JOIN sources, MERGE
#     USING, view bodies, and FK REFERENCES are reads; INSERT INTO / UPDATE /
#     DELETE FROM / MERGE INTO / ALTER / DROP / TRUNCATE targets are writes.
#   * Top-level ERROR regions (counted in `error_regions`, unchanged) route
#     through the 1p9qe DDL recovery tier: a bounded line-anchored scan over
#     comment-/string-masked region text recovers CREATE
#     {PROCEDURE|FUNCTION|TRIGGER|TABLE|VIEW} definitions (marked
#     `extraction: "sql_recovery"`) plus ALTER TABLE / CREATE INDEX ON /
#     trigger ON references. A dangling `block` following a single-routine
#     region is that routine's body — its parsed statements attribute to the
#     recovered routine; region text after a single recovered routine header
#     re-parses through this unit (one level) for the same attribution. Both
#     re-attribution forms mark their references `extraction: "sql_recovery"`.
#     Regions yielding nothing count in `recovery.unrecovered_regions` —
#     nothing is silently dropped. Recovery NEVER runs on parsed statements.
# ---------------------------------------------------------------------------

# Clause roles a reference can carry (the vocabulary 1p9qe/1p9qf build on).
_SQL_REF_CLAUSES = (
    "from", "join", "insert_into", "update", "delete_from",
    "merge_into", "merge_using", "references", "index_on",
    "alter", "drop", "truncate",
)
# Node types the reference walk never descends into: `field` is a column
# reference whose object_reference child is a table/alias QUALIFIER (`u.id`),
# `column`/`list`/`column_definitions`/`index_fields` are column-name and
# literal containers. Skipping them is what keeps aliases, column tokens, and
# string-literal contents out of the reference stream (1p9qc findings a/c/d).
_SQL_REF_SKIP_NODE_TYPES = frozenset({
    "field", "column", "list", "column_definitions", "index_fields",
})
_SQL_CREATE_KIND_BY_NODE = {
    "create_table": "table",
    "create_view": "view",
    "create_materialized_view": "view",
    "create_function": "function",
    "create_procedure": "procedure",
    "create_trigger": "trigger",
}

# ---------------------------------------------------------------------------
# SQL ERROR-region DDL recovery tier (wave 1p9qi / 1p9qe).
#
# tree-sitter-sql cannot parse every dialect's routine/DDL forms (T-SQL,
# MySQL, delimiter blocks, triggers) — those statements land in parse ERROR
# regions and would otherwise vanish from the graph. The recovery tier is the
# honest-degradation answer at statement granularity, and defines the
# degradation-convention family (marker property shape, per-file count
# logging, byte/line ceilings) that other loud-degradation tiers mirror:
#
#   * scope    — recovery runs ONLY over parse ERROR regions; parsed
#                statements are the trusted path and are never rescanned.
#   * masking  — comments (`--`, `/* */`) and string bodies (`'...'`,
#                `"..."`, `$$...$$`) are space-masked BEFORE the scan, so
#                commented-out DDL and DDL text inside string literals can
#                never mint schema objects (security commitment).
#   * anchors  — bounded, line-anchored patterns only; a candidate name that
#                fails strict identifier validation is refused, not guessed.
#   * marker   — every recovered object carries `extraction: "sql_recovery"`
#                (node property in the graph; `extraction` key in the unit).
#   * loudness — per-file counts on the module node (`sql_error_regions`,
#                `sql_recovered_definitions`, `sql_unrecovered_regions`) and
#                a verbose build-log line (`_sql_recovery_log_line`).
#   * bounds   — single pass; regions over _SQL_RECOVERY_MAX_REGION_BYTES and
#                lines over _SQL_RECOVERY_MAX_LINE_CHARS degrade to counts.
# ---------------------------------------------------------------------------
_SQL_RECOVERY_MARKER = "sql_recovery"
_SQL_RECOVERY_MAX_REGION_BYTES = 131072  # larger regions degrade to an unrecovered count
_SQL_RECOVERY_MAX_LINE_CHARS = 4096      # longer lines are skipped (minified/generated SQL)
_SQL_RECOVERY_KIND_BY_WORD = {
    "procedure": "procedure",
    "function": "function",
    "trigger": "trigger",
    "table": "table",
    "view": "view",
    "materialized view": "view",
}
_SQL_RECOVERY_ROUTINE_KINDS = frozenset({"procedure", "function", "trigger"})
# Line-anchored CREATE vocabulary (reviewable constant — extend on field
# evidence via the unrecovered counts). INDEX is matched but, mirroring the
# parsed path (`create_index` emits an `index_on` table READ, no definition
# node), recovers a reference to the indexed table — never an index
# definition, so recovered files can never claim more than parsed ones.
_SQL_RECOVERY_CREATE_RE = re.compile(
    r"^\s*CREATE\s+(?:OR\s+REPLACE\s+)?"
    r"(?P<temp>(?:GLOBAL\s+|LOCAL\s+)?(?:TEMPORARY|TEMP)\s+)?"
    r"(?P<kind>MATERIALIZED\s+VIEW|PROCEDURE|FUNCTION|TRIGGER|TABLE|VIEW|(?:UNIQUE\s+)?INDEX)\s+"
    r"(?:IF\s+NOT\s+EXISTS\s+)?"
    r"(?P<name>[^\s(;,]+)",
    re.IGNORECASE,
)
# ALTER TABLE in an ERROR region recovers as a WRITE reference (never a
# definition — ALTER modifies an existing object).
_SQL_RECOVERY_ALTER_RE = re.compile(
    r"^\s*ALTER\s+TABLE\s+(?:IF\s+EXISTS\s+)?(?P<name>[^\s(;,]+)",
    re.IGNORECASE,
)
_SQL_RECOVERY_ON_RE = re.compile(r"\bON\s+(?P<name>[^\s(;,]+)", re.IGNORECASE)
_SQL_RECOVERY_NAME_RE = re.compile(r"^[A-Za-z_][\w$]*(?:\.[A-Za-z_][\w$]*)*$")
# Named dollar-quote opening tag ($tag$ ... $tag$ — PostgreSQL). Bare $$ is
# handled separately (a letter/underscore is required between the dollars here).
_SQL_RECOVERY_DOLLAR_TAG_RE = re.compile(r"\$[A-Za-z_]\w*\$")


class _SqlRecoveredNode:
    """Synthetic stand-in for a tree-sitter node for recovery-extracted
    definitions (`register_symbol` only reads ``start_point``)."""

    __slots__ = ("start_point",)

    def __init__(self, line: int) -> None:
        self.start_point = (line, 0)


def _sql_recovery_mask_noncode(text: str) -> str:
    """Space-mask comment and string spans, preserving length and newlines.

    Runs BEFORE the recovery scan so commented-out DDL (``-- CREATE ...``,
    ``/* CREATE ... */``) and DDL text inside string literals (``'CREATE
    TABLE ghost'``, ``$$ ... $$`` bodies) can never mint schema objects
    (AC-3). Handles `--` line comments, `/* */` block comments, single-quoted
    strings with ``''`` escapes, double-quoted strings, and dollar quoting —
    both bare ``$$`` and named ``$tag$ ... $tag$`` (the close tag must match
    the open tag); unterminated spans mask to end of text. Masking double-quoted
    identifiers only costs recall (a quoted name is simply not recovered) —
    never precision. Backtick/bracket identifier quoting is NOT masked; it is
    stripped during name validation instead.
    """
    out = list(text)
    n = len(text)

    def _mask(a: int, b: int) -> None:
        for j in range(a, min(b, n)):
            if out[j] != "\n":
                out[j] = " "

    i = 0
    while i < n:
        ch = text[i]
        if ch == "-" and text.startswith("--", i):
            end = text.find("\n", i)
            end = n if end == -1 else end
            _mask(i, end)
            i = end
        elif ch == "/" and text.startswith("/*", i):
            end = text.find("*/", i + 2)
            end = n if end == -1 else end + 2
            _mask(i, end)
            i = end
        elif ch == "$":
            tag_match = _SQL_RECOVERY_DOLLAR_TAG_RE.match(text, i)
            if tag_match is not None:
                tag = tag_match.group(0)
            elif text.startswith("$$", i):
                tag = "$$"
            else:
                i += 1
                continue
            end = text.find(tag, i + len(tag))
            end = n if end == -1 else end + len(tag)
            _mask(i, end)
            i = end
        elif ch in ("'", '"'):
            quote = ch
            j = i + 1
            while j < n:
                if text[j] == quote:
                    if j + 1 < n and text[j + 1] == quote:
                        j += 2
                        continue
                    j += 1
                    break
                j += 1
            _mask(i, j)
            i = j
        else:
            i += 1
    return "".join(out)


def _sql_recovery_clean_name(raw: str) -> tuple[str | None, bool]:
    """``(validated_name, is_temp_sigil)`` for a scanned name candidate.

    Strips bracket/backtick/double-quote identifier quoting, then validates
    against a strict bare-or-dotted identifier shape. Anything that fails
    validation is refused (``None``) — recovery emits only on unambiguous
    matches. ``#tmp`` / ``@tv`` sigil names report ``is_temp_sigil=True`` so
    callers exclude them (temp objects are session-scoped, never schema
    objects).
    """
    cleaned = raw.strip().strip(";,")
    cleaned = cleaned.replace("[", "").replace("]", "").replace("`", "").replace('"', "")
    if not cleaned:
        return None, False
    if cleaned[0] in "#@":
        stripped = cleaned.lstrip("#@")
        return (stripped or None), True
    if not _SQL_RECOVERY_NAME_RE.match(cleaned):
        return None, False
    return cleaned, False


def _sql_recover_error_region(region_text: str, start_line: int) -> dict[str, Any]:
    """Bounded line-anchored DDL recovery scan over ONE parse-ERROR region.

    Single pass over comment-/string-masked text. Returns::

        {"definitions": [...],   # CREATE {TABLE|VIEW|PROCEDURE|FUNCTION|TRIGGER}
         "references": [...],    # ALTER TABLE write; CREATE INDEX / trigger ON reads
         "temp_names": set[str], # casefolded temp forms found (excluded, tracked)
         "routines": [...],      # recovered routine defs (body-attribution hook)
         "truncated": bool}      # region over the byte ceiling — nothing scanned

    Every recovered dict carries ``extraction: "sql_recovery"`` and each
    definition carries ``line`` (absolute) + ``match_line_offset`` (region-
    relative, for body segmentation).
    """
    result: dict[str, Any] = {
        "definitions": [], "references": [], "temp_names": set(),
        "routines": [], "truncated": False,
    }

    def _schema_of(name: str) -> str | None:
        return name.rsplit(".", 1)[0] if "." in name else None

    if len(region_text.encode("utf-8", "replace")) > _SQL_RECOVERY_MAX_REGION_BYTES:
        result["truncated"] = True
        return result
    masked = _sql_recovery_mask_noncode(region_text)
    for offset, line in enumerate(masked.splitlines()):
        if len(line) > _SQL_RECOVERY_MAX_LINE_CHARS:
            continue
        match = _SQL_RECOVERY_CREATE_RE.match(line)
        if match is not None:
            kind_word = " ".join(match.group("kind").split()).casefold()
            if kind_word.endswith("index"):
                on_match = _SQL_RECOVERY_ON_RE.search(line, match.end())
                if on_match is not None:
                    name, is_temp = _sql_recovery_clean_name(on_match.group("name"))
                    if name and is_temp:
                        result["temp_names"].add(name.casefold())
                    elif name:
                        result["references"].append({
                            "name": name, "schema": _schema_of(name),
                            "direction": "read", "clause": "index_on",
                            "statement": "create_index", "owner": None,
                            "extraction": _SQL_RECOVERY_MARKER,
                        })
                continue
            sql_kind = _SQL_RECOVERY_KIND_BY_WORD.get(kind_word)
            if sql_kind is None:
                continue
            name, is_temp = _sql_recovery_clean_name(match.group("name"))
            if name is None:
                continue
            if is_temp or match.group("temp"):
                result["temp_names"].add(name.casefold())
                continue
            defn = {
                "name": name, "schema": _schema_of(name),
                "sql_kind": sql_kind, "temporary": False,
                "line": start_line + offset, "match_line_offset": offset,
                "extraction": _SQL_RECOVERY_MARKER,
            }
            result["definitions"].append(defn)
            if sql_kind in _SQL_RECOVERY_ROUTINE_KINDS:
                result["routines"].append(defn)
                if sql_kind == "trigger":
                    # `CREATE TRIGGER trg ... ON <table>` — the trigger's
                    # subject table, attributed to the recovered trigger.
                    on_match = _SQL_RECOVERY_ON_RE.search(line, match.end())
                    if on_match is not None:
                        on_name, on_temp = _sql_recovery_clean_name(on_match.group("name"))
                        if on_name and not on_temp:
                            result["references"].append({
                                "name": on_name, "schema": _schema_of(on_name),
                                "direction": "read", "clause": "from",
                                "statement": "create_trigger", "owner": name,
                                "extraction": _SQL_RECOVERY_MARKER,
                            })
            continue
        match = _SQL_RECOVERY_ALTER_RE.match(line)
        if match is not None:
            name, is_temp = _sql_recovery_clean_name(match.group("name"))
            if name and is_temp:
                result["temp_names"].add(name.casefold())
            elif name:
                result["references"].append({
                    "name": name, "schema": _schema_of(name),
                    "direction": "write", "clause": "alter",
                    "statement": "alter_table", "owner": None,
                    "extraction": _SQL_RECOVERY_MARKER,
                })
    return result


# ---------------------------------------------------------------------------
# PL/pgSQL loop-body DML recovery (wave 1rs45). tree-sitter-sql has no plpgsql
# grammar, so a routine body's loop scaffolding (`FOR … LOOP` / `WHILE … LOOP`
# / `FOREACH … LOOP` / `END LOOP`) shreds into nested ERROR nodes. The DML
# statement immediately after `LOOP` in an inline-query-FOR (`FOR r IN SELECT …
# FROM src LOOP <DML>`) is the residual the 1p9qi statement-dispatch drops: the
# parser is still in SELECT/FROM state at `LOOP`, so the write target is
# absorbed into the header query's `relation` span. Approach B (mechanism spike
# 2026-07-06): mask the body, keyword-strip ONLY the loop scaffolding, and
# reparse the residue through the existing statement unit (`_sql_analyze_program`,
# `recover=False`) — reusing the already-adversarially-reviewed unit gives
# direction/CTE/temp/alias/nested-loop handling for free with ZERO new DML/CTE
# vocabulary; the whole faithfulness surface collapses to "is the strip correct?"
#
# GATED to loop-bearing bodies only: a routine whose masked body has no `LOOP`
# stays entirely on the normal body walk (non-loop partial bodies — IF/CASE/
# RETURN QUERY/EXECUTE — already recover their in-branch DML via walk_reads'
# statement dispatch, so routing them through the strip would risk regressing
# what already works). A loop-bearing body that ALSO holds non-loop DML (a
# sibling `IF … INSERT … END IF`) keeps that DML too: the strip removes only the
# loop scaffolding, so the IF/CASE statements survive into the reparsed residue
# and the unit re-dispatches them (mixed-body no-regression, verified).
_SQL_LOOP_FOR_HEADER_RE = re.compile(r"\bFOR\b\s+.+?\s+\bIN\b\s+", re.IGNORECASE | re.DOTALL)
_SQL_LOOP_WHILE_HEADER_RE = re.compile(r"\bWHILE\b\s+.+?\s+\bLOOP\b", re.IGNORECASE | re.DOTALL)
_SQL_LOOP_FOREACH_HEADER_RE = re.compile(r"\bFOREACH\b\s+.+?\s+\bLOOP\b", re.IGNORECASE | re.DOTALL)
_SQL_LOOP_END_LOOP_RE = re.compile(r"\bEND\s+LOOP\b[^\n;]*;?", re.IGNORECASE)
_SQL_LOOP_KEYWORD_RE = re.compile(r"\bLOOP\b", re.IGNORECASE)
# A bare `LOOP` header (`LOOP … END LOOP`) not preceded by an identifier char —
# a plain identifier/column containing "loop" is protected by the word boundary
# plus the preceding-char guard (`loop_events`, `a.loop`).
_SQL_LOOP_BARE_RE = re.compile(r"(?<![.\w])\bLOOP\b", re.IGNORECASE)


def _sql_body_is_loop_bearing(body_text: str) -> bool:
    """True when the routine body contains a real `LOOP` keyword (masked).

    Masking first so a `LOOP` inside a string literal or comment does not
    trip the gate — only genuine loop scaffolding routes a body through the
    strip-reparse. Identifiers/columns containing "loop" are excluded by the
    word boundary in `_SQL_LOOP_KEYWORD_RE`.
    """
    return bool(_SQL_LOOP_KEYWORD_RE.search(_sql_recovery_mask_noncode(body_text)))


def _sql_strip_loop_scaffolding(body_text: str) -> str:
    """Blank the PL/pgSQL loop scaffolding out of ``body_text``, in place.

    Keyword/token-oriented over MASKED text (never line-oriented — the spike
    proved a line strip fails multi-line and single-line loop headers), but
    edits the ORIGINAL text so a kept header query is real, not masked:

      * ``FOR <var…> IN <query> LOOP`` → keep ``<query>`` as a standalone
        statement (the header query's reads are genuine), blank ``FOR…IN`` and
        the closing ``LOOP``, inject a ``;`` terminator where ``LOOP`` was.
      * ``FOR <var> IN <lo>..<hi> LOOP`` (integer range, no SELECT) → blank
        the whole header (no table read).
      * ``WHILE … LOOP`` / ``FOREACH … LOOP`` / ``END LOOP [label];`` / a bare
        ``LOOP`` header → blank entirely.

    Blanked spans become spaces (newlines preserved) so byte offsets and line
    structure survive for a clean reparse. Cursor-FOR (`FOR r IN c(…) LOOP`)
    keeps its `c(…)` invocation, which the unit mints nothing for — no phantom.
    """
    masked = _sql_recovery_mask_noncode(body_text)
    out = list(body_text)

    def blank(a: int, b: int) -> None:
        for i in range(a, b):
            if out[i] != "\n":
                out[i] = " "

    for m in _SQL_LOOP_END_LOOP_RE.finditer(masked):
        blank(m.start(), m.end())
    for m in _SQL_LOOP_WHILE_HEADER_RE.finditer(masked):
        blank(m.start(), m.end())
    for m in _SQL_LOOP_FOREACH_HEADER_RE.finditer(masked):
        blank(m.start(), m.end())
    i = 0
    while True:
        header = _SQL_LOOP_FOR_HEADER_RE.search(masked, i)
        if header is None:
            break
        loop_kw = _SQL_LOOP_KEYWORD_RE.search(masked, header.end())
        if loop_kw is None:
            i = header.end()
            continue
        query = body_text[header.end():loop_kw.start()]
        if ".." in query and not re.search(r"\bSELECT\b", query, re.IGNORECASE):
            # Integer-range FOR — no table read; blank the whole header.
            blank(header.start(), loop_kw.end())
        else:
            blank(header.start(), header.end())   # remove "FOR … IN"
            blank(loop_kw.start(), loop_kw.end())  # remove "LOOP"
            out[loop_kw.start()] = ";"             # terminate the kept query
        i = loop_kw.end()
    text = "".join(out)
    # Any bare `LOOP` header left (a `LOOP … END LOOP` with no FOR/WHILE) →
    # equal-length blank so offsets are preserved.
    text = _SQL_LOOP_BARE_RE.sub(lambda m: " " * (m.end() - m.start()), text)
    return text


def _sql_routine_body_inner(create_node, source_bytes: bytes) -> str | None:
    """Return the inner dollar-quoted body text of a natively-parsed routine.

    The body lives in a ``function_body`` child wrapped by two ``dollar_quote``
    nodes (`$$ … $$` or `$tag$ … $tag$`). Returns the text BETWEEN them (raw
    PL/pgSQL, un-masked) so the loop-strip masker can run on it directly — the
    masker space-fills whole ``$$ … $$`` spans, so the wrapper must be removed
    first or the entire body would be masked. Returns None when the routine has
    no well-formed dollar-quoted body (e.g. a trigger's `EXECUTE FUNCTION`, or a
    SQL-language body), leaving such routines on the normal walk.
    """
    for child in _sql_node_children(create_node):
        if str(getattr(child, "type", "") or "") != "function_body":
            continue
        quotes = [
            c for c in _sql_node_children(child)
            if str(getattr(c, "type", "") or "") == "dollar_quote"
        ]
        if len(quotes) == 2:
            start = int(getattr(quotes[0], "end_byte", 0) or 0)
            end = int(getattr(quotes[1], "start_byte", 0) or 0)
            if end > start:
                return source_bytes[start:end].decode("utf-8", "replace")
    return None


def _sql_recovery_log_line(
    rel_path: str,
    error_regions: int,
    recovered: int,
    unrecovered: int,
    partial_bodies: int = 0,
    partial_bodies_recovered: int = 0,
) -> str:
    """Per-file build-log line for the SQL DDL recovery tier (loudness).

    ``partial_bodies`` counts natively-parsed routines whose BODY held a
    nested parse-ERROR (loop/control-flow) — distinct from the top-level
    ERROR-region counts above. ``partial_bodies_recovered`` (wave 1rs45)
    reports how many of those had in-loop DML recovered by the strip-reparse,
    so the loudness signal never overstates what remains genuinely partial.
    """
    return (
        f"build_index: sql recovery {rel_path} — {error_regions} parse-error "
        f"region(s): {recovered} definition(s) recovered, "
        f"{unrecovered} region(s) unrecovered, "
        f"{partial_bodies} routine body(ies) partially parsed "
        f"({partial_bodies_recovered} loop-recovered)"
    )


# ---------------------------------------------------------------------------
# Line-scan degraded extraction tier (wave 1p9q6). The direct parallel to the
# 1p9qe SQL ERROR-region recovery convention above, applied to CODE files over
# the tree-sitter AST parse cap (default 2 MB) but under the walk cap (5 MB).
# Such files previously contributed ZERO graph nodes — a silent hole where
# everything importing them dangled to `external::`. This tier recovers their
# IMPORTS and TOP-LEVEL DEFINITIONS only, via a bounded, AST-free scan; it
# emits NO calls/reads edges (a line scan cannot resolve those faithfully).
# Its definitions DO participate as cross-file resolution candidates, so an
# oversized hub's symbols both bind inbound references AND correctly force
# refusal of an otherwise-unique bind when a twin exists (faithfulness core).
# Mirrors the 1p9qe convention shape (SCANNER is new; the marker/counts/log
# layer is the convention-mirror):
#   * marker   — every line-scanned node carries `extraction: "line_scan"`
#                (the parallel to `extraction: "sql_recovery"`).
#   * loudness — per-file counts on the module node (`line_scan_defines`,
#                `line_scan_imports`, `line_scan_skipped` — parallel to
#                `sql_recovered_definitions`/`sql_error_regions`/
#                `sql_unrecovered_regions`) + a verbose build-log line
#                (`_line_scan_log_line`, parallel to `_sql_recovery_log_line`);
#                a whole-file skip past the byte ceiling sets
#                `line_scan_ceiling_skipped` and is logged, never silent.
#   * bounds   — single pass; a hard scan-byte ceiling
#                (`_LINE_SCAN_MAX_BYTES_DEFAULT`, env-overridable via
#                WAVEFOUNDRY_MAX_LINE_SCAN_BYTES) + a per-line length guard
#                (`_LINE_SCAN_MAX_LINE_CHARS`) so pathological minified lines
#                cannot blow up build time.
#   * masking  — comment/string spans are space-masked BEFORE the scan (the
#                `_sql_recovery_mask_noncode` shape, generalized to code
#                comment styles) so declaration-looking text inside strings,
#                comments, or minified lines can never mint a node (AC-3).
# ---------------------------------------------------------------------------
_LINE_SCAN_MARKER = "line_scan"
# Whole-file scan-byte ceiling; over it → today's behavior (skip), now LOUD.
# Defaults to the walk cap so every file that actually reaches this tier
# (already < walk cap) is scanned by default; the ceiling is the env-tunable
# safety valve the cost-bound tests exercise (AC-3/AC-4).
_LINE_SCAN_MAX_BYTES_DEFAULT = 5_000_000
_LINE_SCAN_MAX_LINE_CHARS = 4096  # longer lines are skipped, counted (minified guard)

# Line-leading declaration: optional (bounded) modifier keywords, then a
# definition keyword, then the name. Anchored at column 0 (a top-level proxy —
# nested/indented declarations are intentionally not recovered; Requirement 1
# is "top-level definition names").
_LINE_SCAN_DEF_RE = re.compile(
    r"^(?:(?:pub|export|default|public|private|protected|internal|static|final|"
    r"abstract|async|open|sealed|const|unsafe|extern|inline|virtual|override|"
    r"partial)\s+){0,4}"
    r"(?P<kw>def|class|function|func|fn|type|impl|struct|enum|trait|interface|"
    r"record|object|protocol|actor|namespace|module|mod)\s+"
    r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)"
)
# Keyword → node kind (mirrors the tree-sitter normalization: struct/enum/
# trait/type/… collapse to "class"; callables are "function").
_LINE_SCAN_CLASS_KEYWORDS = frozenset({
    "class", "type", "impl", "struct", "enum", "trait", "interface", "record",
    "object", "protocol", "actor", "namespace", "module", "mod",
})
# Import anchor — the keyword is CODE, so it survives comment/string masking;
# a commented-out or stringified import line is blanked by the mask and never
# matches here. `#` is only an include when the comment profile treats it as
# code (C-family), so a Python `#`-comment line is masked before this runs.
_LINE_SCAN_IMPORT_ANCHOR_RE = re.compile(
    r"^(?:from\s+[\w.]+\s+import\b|import\b|use\b|#\s*include\b)"
)
# Bare (unquoted) module specifier — Python `import os` / `from a.b import`,
# Rust `use a::b::c`. Captured from the MASKED line (bare identifiers survive).
_LINE_SCAN_BARE_SPEC_RE = re.compile(
    r"^(?:from\s+(?P<from>[\w.]+)|(?:import|use)\s+(?P<mod>[\w.:]+))"
)
# Quoted / angle-bracket specifier — JS/TS `from "x"`, Go `import "fmt"`,
# C `#include <stdio.h>`. Read from the RAW line (the string span is masked
# away in the masked line), and ONLY after the anchor confirmed on the masked
# line that this is a genuine (non-commented) import.
_LINE_SCAN_QUOTED_SPEC_RE = re.compile(r"""['"<]([^'"<>\n]+)['">]""")

# `#`-line-comment languages. For everything else (the C-family that actually
# reaches this tier), `#` starts a preprocessor directive (`#include`) that
# MUST survive masking, and `/* */` block comments apply.
_LINE_SCAN_HASH_COMMENT_LANGS = frozenset({
    "python", "ruby", "perl", "r", "elixir", "julia", "make",
    "yaml", "toml", "shell", "bash", "dockerfile",
})


def _line_scan_comment_profile(lang_key: str | None) -> tuple[tuple[str, ...], bool]:
    """``(line_comment_tokens, has_block_comment)`` for the mask, by language
    family. `#` is a comment ONLY for `#`-comment languages; for the C-family
    default it is preprocessor syntax and must not be masked."""
    if lang_key in _LINE_SCAN_HASH_COMMENT_LANGS:
        return ("#",), False
    return ("//",), True


def _line_scan_mask(text: str, lang_key: str | None, *, mask_strings: bool = True) -> str:
    """Space-mask comment (and, by default, string) spans, preserving length
    and newlines (the `_sql_recovery_mask_noncode` shape, generalized to code
    comment styles). Runs BEFORE the definition scan so declaration-looking
    text in comments/strings can never mint a node (precision commitment).

    ``mask_strings=False`` masks comments ONLY (strings survive) — used for
    import-specifier extraction, where the module path IS a string literal but
    a trailing comment must still be neutralized so a quoted token inside a
    comment can never be read as a module."""
    line_comments, has_block = _line_scan_comment_profile(lang_key)
    out = list(text)
    n = len(text)

    def _mask(a: int, b: int) -> None:
        for j in range(a, min(b, n)):
            if out[j] != "\n":
                out[j] = " "

    i = 0
    while i < n:
        ch = text[i]
        matched_lc = next((tok for tok in line_comments if text.startswith(tok, i)), None)
        if matched_lc is not None:
            end = text.find("\n", i)
            end = n if end == -1 else end
            _mask(i, end)
            i = end
        elif has_block and text.startswith("/*", i):
            end = text.find("*/", i + 2)
            end = n if end == -1 else end + 2
            _mask(i, end)
            i = end
        elif mask_strings and (text.startswith('"""', i) or text.startswith("'''", i)):
            # Triple-quoted strings (Python docstrings) — mask to the matching
            # close so declaration text in a docstring never mints.
            q3 = text[i:i + 3]
            end = text.find(q3, i + 3)
            end = n if end == -1 else end + 3
            _mask(i, end)
            i = end
        elif mask_strings and ch in ("'", '"', "`"):
            quote = ch
            j = i + 1
            while j < n:
                if text[j] == "\\":  # backslash escape (C-family / Python strings)
                    j += 2
                    continue
                if text[j] == quote:
                    j += 1
                    break
                j += 1
            _mask(i, j)
            i = j
        else:
            i += 1
    return "".join(out)


def _line_scan_extract(source_text: str, lang_key: str | None = None) -> dict[str, Any]:
    """Bounded, AST-free line scan recovering IMPORTS + TOP-LEVEL DEFINITIONS.

    Returns::

        {"imports": [module_spec, ...],            # order-preserving, deduped
         "definitions": [(name, kind, line), ...],  # top-level only, deduped
         "skipped_lines": int,                      # length-guard skips
         "ceiling_skipped": bool}                   # whole file over byte ceiling

    Never emits call/read facts. Definitions are line-anchored at column 0
    (after optional modifiers) on comment/string-masked text, so strings,
    comments, and minified lines mint nothing (AC-3). Encoding robustness: a
    UTF-8 BOM is stripped; ``splitlines`` yields the last line even without a
    final newline and tolerates mixed newline styles."""
    result: dict[str, Any] = {
        "imports": [], "definitions": [], "skipped_lines": 0, "ceiling_skipped": False,
    }
    text = source_text
    if text.startswith("\ufeff"):  # strip UTF-8 BOM (encoding robustness)
        text = text[1:]
    ceiling = int(os.environ.get("WAVEFOUNDRY_MAX_LINE_SCAN_BYTES") or _LINE_SCAN_MAX_BYTES_DEFAULT)
    if ceiling > 0 and len(text.encode("utf-8", "replace")) > ceiling:
        result["ceiling_skipped"] = True
        return result
    # Two masks (both O(n), cheap even at the walk cap): the FULL mask (comments
    # + strings) drives the definition scan, the import anchor, and bare-name
    # capture — none of which may see string/comment content. The COMMENT-ONLY
    # mask preserves string literals (so a quoted module specifier survives) but
    # still neutralizes a trailing comment (so a quoted token inside a comment
    # can never be misread as a module).
    full_masked = _line_scan_mask(text, lang_key, mask_strings=True)
    comment_masked = _line_scan_mask(text, lang_key, mask_strings=False)
    raw_lines = text.splitlines()
    masked_lines = full_masked.splitlines()
    comment_masked_lines = comment_masked.splitlines()
    seen_imports: set[str] = set()
    seen_defs: set[str] = set()
    for offset, masked_line in enumerate(masked_lines):
        raw_line = raw_lines[offset] if offset < len(raw_lines) else ""
        if len(raw_line) > _LINE_SCAN_MAX_LINE_CHARS:
            result["skipped_lines"] += 1
            continue
        def_match = _LINE_SCAN_DEF_RE.match(masked_line)
        if def_match is not None:
            name = def_match.group("name")
            kw = def_match.group("kw")
            kind = "class" if kw in _LINE_SCAN_CLASS_KEYWORDS else "function"
            if name not in seen_defs:
                seen_defs.add(name)
                result["definitions"].append((name, kind, offset + 1))
            continue
        if _LINE_SCAN_IMPORT_ANCHOR_RE.match(masked_line):
            spec: str | None = None
            cmask_line = comment_masked_lines[offset] if offset < len(comment_masked_lines) else ""
            quoted = _LINE_SCAN_QUOTED_SPEC_RE.search(cmask_line)
            bare = _LINE_SCAN_BARE_SPEC_RE.match(masked_line)
            if bare is not None and bare.group("from") is not None:
                # Python `from a.b import c` — the module is the bare `from`
                # target (never a same-line quoted token).
                spec = bare.group("from")
            elif quoted is not None:
                # JS/TS `from "x"`, Go `import "fmt"`, C `#include <x>` — the
                # module is the (string/angle) specifier.
                spec = quoted.group(1)
            elif bare is not None:
                # Python `import os`, Rust `use a::b::c` — bare dotted/`::` path.
                spec = bare.group("mod")
            if spec and spec not in seen_imports:
                seen_imports.add(spec)
                result["imports"].append(spec)
    return result


def _line_scan_log_line(
    rel_path: str,
    defines: int,
    imports: int,
    skipped: int,
    *,
    ceiling_skipped: bool = False,
) -> str:
    """Per-file build-log line for the line-scan degraded-extraction tier
    (loudness; the `_sql_recovery_log_line` parallel)."""
    if ceiling_skipped:
        return (
            f"build_index: line-scan {rel_path} — over the scan-byte ceiling; "
            f"skipped (imports + top-level definitions not recovered)"
        )
    return (
        f"build_index: line-scan {rel_path} — over the AST parse cap: "
        f"{defines} definition(s) + {imports} import(s) recovered, "
        f"{skipped} line(s) skipped (length guard)"
    )


# R7 (wave 1rrx5): clustering-asymmetry measurement threshold. Community
# detection excludes `reads` but NOT `writes`/`maps_to`, so a hot write-target
# data node (an audit/events log written by many routines, or an entity mapped
# by many classes) can bridge otherwise-unrelated modules — the exact failure
# mode the `reads` exclusion prevents. This is the incoming-edge count at or
# above which a data-layer node is surfaced for that evidence-gathering
# decision. Read-only: it changes no edge and no community.
_SQL_HOT_DATA_INDEGREE_THRESHOLD = 8


def sql_hot_data_layer_nodes(payload, *, threshold: int = _SQL_HOT_DATA_INDEGREE_THRESHOLD):
    """Read-only clustering-asymmetry diagnostic (wave 1rrx5 R7).

    Surfaces data-layer nodes (``sql_kind`` table/view) whose incoming
    ``writes``/``maps_to`` in-degree is ``>= threshold`` — the hot write-target
    tables that could bridge communities if ``writes``/``maps_to`` were ever
    admitted to clustering. Evidence-gathering only: no edge, node, or
    community is changed. Returns ``[{"id", "sql_kind", "in_degree"}, …]``
    sorted by descending in-degree then id.
    """
    nodes: dict[str, dict[str, Any]] = {}
    for n in (payload.get("nodes") or []):
        nid = n.get("id")
        if nid is not None:
            nodes[nid] = n
    counts: dict[str, int] = {}
    for e in (payload.get("edges") or []):
        if e.get("relation") in (GRAPH_WRITES_RELATION, GRAPH_MAPS_TO_RELATION):
            tgt = e.get("target")
            node = nodes.get(tgt)
            if node is not None and node.get("sql_kind") in ("table", "view"):
                counts[tgt] = counts.get(tgt, 0) + 1
    hot = [
        {"id": nid, "sql_kind": nodes[nid].get("sql_kind"), "in_degree": count}
        for nid, count in counts.items()
        if count >= threshold
    ]
    hot.sort(key=lambda h: (-h["in_degree"], h["id"]))
    return hot


def _sql_node_children(node) -> list:
    try:
        return list(getattr(node, "named_children", []) or [])
    except Exception:
        return []


def _sql_subtree_has_error(node) -> bool:
    """True when any descendant of ``node`` is a parse-ERROR node.

    Walks ALL children (not just named) so an ERROR nested under an unnamed
    wrapper is still found. Used to flag a natively-parsed routine whose BODY
    contains a tree-sitter-sql parse failure — e.g. a PL/pgSQL FOR/WHILE loop
    the grammar cannot parse. The CREATE header parses at top level, so the
    nested ERROR never reaches scan_top and `error_regions` stays 0; in-loop
    DML is dropped with no top-level signal. This flag restores loudness.
    """
    stack = list(getattr(node, "children", []) or [])
    while stack:
        current = stack.pop()
        if str(getattr(current, "type", "") or "") == "ERROR":
            return True
        stack.extend(list(getattr(current, "children", []) or []))
    return False


def _sql_temp_sigil(node, source_bytes: bytes) -> bool:
    """True when an object_reference is a temp-table / table-variable form.

    `@tv` parses as the reference text itself; `#tmp` parses with the sigil
    as a preceding ERROR token, so also check the byte immediately before
    the node (`#tmp`, `##global`).
    """
    text = _ts_node_text(node, source_bytes).strip()
    if text.startswith("#") or text.startswith("@"):
        return True
    start = int(getattr(node, "start_byte", 0) or 0)
    return start > 0 and source_bytes[start - 1:start] in (b"#", b"@")


def _sql_object_reference_parts(node, source_bytes: bytes) -> tuple[str, str | None]:
    """(full_name, schema) for an `object_reference` node."""
    name = " ".join(_ts_node_text(node, source_bytes).split())
    schema: str | None = None
    try:
        schema_node = node.child_by_field_name("schema")
    except Exception:
        schema_node = None
    if schema_node is not None:
        schema = _ts_node_text(schema_node, source_bytes).strip() or None
    return name, schema


def _sql_collect_cte_names(stmt_node, source_bytes: bytes) -> set[str]:
    """Casefolded CTE names declared anywhere in this statement subtree."""
    names: set[str] = set()
    stack = [stmt_node]
    while stack:
        current = stack.pop()
        if str(getattr(current, "type", "") or "") == "cte":
            for child in _sql_node_children(current):
                if str(getattr(child, "type", "") or "") == "identifier":
                    text = _ts_node_text(child, source_bytes).strip()
                    if text:
                        names.add(text.casefold())
                    break
        stack.extend(_sql_node_children(current))
    return names


def _sql_analyze_program(root_node, source_bytes: bytes, *, recover: bool = True) -> dict[str, Any]:
    """Analyze a parsed SQL program: definitions, clause-aware references,
    temp-object names, and ERROR regions routed through the recovery tier.

    Statement-scoped exclusions (CTE names, alias positions, temp sigils) are
    applied here; the SCRIPT-scoped temp-name exclusion is the caller's job
    (`temp_names` is returned casefolded for that filter) so that a temp
    object created in one statement never binds a reference in another.

    ``recover=False`` disables the ERROR-region recovery scan — used for the
    single-level body re-parse inside recovery itself (no recursion) and
    counts every ERROR region as unrecovered.
    """
    definitions: list[dict[str, Any]] = []
    references: list[dict[str, Any]] = []
    temp_names: set[str] = set()
    error_regions = 0
    unrecovered_regions = 0
    partial_bodies = 0
    partial_bodies_recovered = 0

    def make_ref(
        oref,
        *,
        direction: str,
        clause: str,
        statement: str,
        owner: str | None,
        cte_names: set[str],
    ) -> None:
        if oref is None:
            return
        if _sql_temp_sigil(oref, source_bytes):
            name = _ts_node_text(oref, source_bytes).strip().lstrip("#@")
            if name:
                temp_names.add(name.casefold())
            return
        name, schema = _sql_object_reference_parts(oref, source_bytes)
        if not name or name.casefold() in _SQL_RELATION_KEYWORD_STOPLIST:
            return
        if name.casefold() in cte_names:
            return
        references.append({
            "name": name,
            "schema": schema,
            "direction": direction,
            "clause": clause,
            "statement": statement,
            "owner": owner,
        })

    def walk_reads(node, clause: str, statement: str, owner: str | None, cte_names: set[str]) -> None:
        node_type = str(getattr(node, "type", "") or "")
        if node_type in _SQL_REF_SKIP_NODE_TYPES:
            return
        if node_type == "statement":
            # Wave 1p9qi in-body routine fix: a nested `statement` node must be
            # dispatched through analyze_statement — never flattened by the
            # generic read descent below. A natively-parsed PL/pgSQL routine
            # body (`$$`/`$tag$`, the TRUSTED path) wraps each of its
            # statements in a `statement` node exactly like the top level
            # (verified against the parsed AST). Without this branch the whole
            # body flowed through the generic walk, which hard-codes
            # `direction="read"` at every object_reference — so in-body
            # INSERT/UPDATE/DELETE/MERGE were emitted as READS (direction
            # inverted; the write went to the wrong bucket) and in-body CREATE
            # TABLE / CREATE TEMP TABLE became phantom reads that bypassed the
            # AC-6 temp exclusion. Routing to analyze_statement gives each
            # in-body statement its correct clause-derived direction, mints the
            # temp-name exclusion for in-body temp objects, and treats in-body
            # creates as definitions (dropped by handle_create_routine — routine
            # bodies never mint schema objects). This makes the native path
            # consistent with the recovery tier, which already re-enters
            # analyze_statement for recovered bodies. Loose reference positions
            # with no enclosing `statement` (e.g. a subquery inside an
            # unparseable `IF (...)` that lands in a nested ERROR region) still
            # fall through to the generic read descent below — genuine reads are
            # never dropped.
            analyze_statement(node, owner, cte_names)
            return
        if node_type == "relation":
            for child in _sql_node_children(node):
                ctype = str(getattr(child, "type", "") or "")
                if ctype == "object_reference":
                    make_ref(child, direction="read", clause=clause, statement=statement,
                             owner=owner, cte_names=cte_names)
                elif ctype == "subquery":
                    walk_reads(child, "from", statement, owner, cte_names)
                # alias identifiers are deliberately never collected
            return
        if node_type == "invocation":
            # Wave 1p9qi integration: a scalar function invocation's NAME parses
            # as `invocation > object_reference` (`WHERE created < NOW()` →
            # `NOW`), which is a routine name, never a table reference — the
            # generic descent minted `reads external::NOW`-style noise (4.4% of
            # unit references on the Fineract census corpus). Skip the direct
            # object_reference child (the function name) but KEEP walking the
            # argument subtree so a genuine table read inside an argument
            # subquery (`COALESCE((SELECT n FROM orgs), 'x')`) is preserved.
            # Relation-position invocations (`FROM generate_series(...)`) are
            # handled by the `relation` branch above and are untouched: they
            # emit no table reference (a routine call is not a table — the
            # recorded routine-invocation stance; a `call` clause is future
            # field-demand work).
            for child in _sql_node_children(node):
                if str(getattr(child, "type", "") or "") == "object_reference":
                    continue
                walk_reads(child, clause, statement, owner, cte_names)
            return
        if node_type == "object_reference":
            make_ref(node, direction="read", clause=clause, statement=statement,
                     owner=owner, cte_names=cte_names)
            return
        if node_type == "cte":
            for child in _sql_node_children(node):
                if str(getattr(child, "type", "") or "") == "statement":
                    analyze_statement(child, owner, cte_names)
            return
        if node_type == "function_declaration":
            # R3 (wave 1rrx5): a PL/pgSQL `DECLARE <var> <type>` parses as a
            # `function_declaration` whose DIRECT object_reference child is the
            # TYPE name (`DECLARE r record` → object_reference `record`), never
            # a table — same "a name is not a reference" family as the routine
            # name / RETURNS type / EXECUTE action skips. (A builtin type parses
            # as an `int`/keyword node, not object_reference, so it is already
            # clean.) Skip the direct type-name object_reference but still
            # descend into other children so a default-value read
            # (`DECLARE x int := (SELECT … FROM t)`, a nested `statement`
            # routed through analyze_statement) is preserved.
            #
            # R3 refinement (1rrx5 delivery review, adversarial finding 2): a
            # `%ROWTYPE` / `%TYPE` attribute makes the object_reference a
            # GENUINE table dependency — `DECLARE r some_table%ROWTYPE` anchors
            # the row type to `some_table`, and `DECLARE v some_table.col%TYPE`
            # to that table's column. The grammar parses `some_table` as a clean
            # object_reference and leaves the trailing `%ROWTYPE`/`%TYPE` as an
            # ERROR sibling of the declaration. So skip the object_reference type
            # name ONLY for a BARE type (`record`, custom domain — no % signal);
            # when a `%ROWTYPE`/`%TYPE` ERROR sibling is present, KEEP the
            # object_reference so the real table read survives (pre-R3 behavior
            # for anchored declarations, restored without the phantom).
            children = _sql_node_children(node)
            anchors_table = False
            for _c in children:
                if str(getattr(_c, "type", "") or "") == "ERROR":
                    _errtxt = _ts_node_text(_c, source_bytes).casefold()
                    if "%rowtype" in _errtxt or "%type" in _errtxt:
                        anchors_table = True
                        break
            for child in children:
                if (not anchors_table
                        and str(getattr(child, "type", "") or "") == "object_reference"):
                    continue
                walk_reads(child, clause, statement, owner, cte_names)
            return
        next_clause = clause
        if node_type == "from":
            next_clause = "from"
        elif "join" in node_type:
            next_clause = "join"
        for child in _sql_node_children(node):
            walk_reads(child, next_clause, statement, owner, cte_names)

    def handle_create_table(create_node, statement_node) -> None:
        children = _sql_node_children(create_node)
        name_node = next(
            (c for c in children if str(getattr(c, "type", "") or "") == "object_reference"),
            None,
        )
        is_temp = any(
            str(getattr(c, "type", "") or "") in ("keyword_temporary", "keyword_temp")
            for c in children
        )
        table_name: str | None = None
        if name_node is not None:
            if _sql_temp_sigil(name_node, source_bytes):
                is_temp = True
            name, schema = _sql_object_reference_parts(name_node, source_bytes)
            table_name = name or None
            if is_temp and name:
                temp_names.add(name.casefold())
            if not is_temp and name:
                definitions.append({
                    "name": name,
                    "schema": schema,
                    "sql_kind": "table",
                    "temporary": False,
                    "node": statement_node,
                })
        # FK targets: every OTHER object_reference in the create subtree
        # (column-level `REFERENCES orgs(id)` and table-level constraints).
        owner = table_name if not is_temp else None
        stack = list(children)
        while stack:
            current = stack.pop()
            if current is name_node:
                continue
            if str(getattr(current, "type", "") or "") == "object_reference":
                make_ref(current, direction="read", clause="references",
                         statement="create_table", owner=owner, cte_names=set())
                continue
            stack.extend(_sql_node_children(current))

    def handle_create_view(create_node, statement_node, cte_names: set[str]) -> None:
        view_name: str | None = None
        for child in _sql_node_children(create_node):
            ctype = str(getattr(child, "type", "") or "")
            if ctype == "object_reference" and view_name is None:
                name, schema = _sql_object_reference_parts(child, source_bytes)
                if name:
                    view_name = name
                    definitions.append({
                        "name": name,
                        "schema": schema,
                        "sql_kind": "view",
                        "temporary": False,
                        "node": statement_node,
                    })
            elif ctype in ("create_query", "statement", "select", "from"):
                walk_reads(child, "from", "create_view", view_name, cte_names)

    def handle_create_routine(create_node, statement_node, sql_kind: str, cte_names: set[str]) -> None:
        nonlocal partial_bodies, partial_bodies_recovered
        routine_name: str | None = None
        expect_return_type = False
        expect_action_name = False
        # Loudness (1p9qi delivery council): if this natively-parsed routine's
        # body subtree contains a nested parse-ERROR (a PL/pgSQL loop /
        # control-flow construct tree-sitter-sql cannot parse), some in-body
        # DML may have been dropped. The header parsed at top level so
        # scan_top / `error_regions` never sees it — flag it here so the
        # partial extraction is observable rather than silent.
        has_body_error = _sql_subtree_has_error(create_node)
        if has_body_error:
            partial_bodies += 1
        # Loop-body DML recovery (wave 1rs45), GATED to loop-bearing bodies.
        # Only a partial body whose masked text actually contains a `LOOP`
        # construct is routed through the strip-reparse below — the residual
        # the 1p9qi statement-dispatch drops is the DML absorbed after `LOOP`.
        # A non-loop partial body (IF/CASE/RETURN QUERY/EXECUTE) stays on the
        # normal body walk, which already recovers its in-branch DML via
        # walk_reads' statement dispatch; routing it through the strip would
        # risk regressing what already works.
        loop_body_inner = _sql_routine_body_inner(create_node, source_bytes) if has_body_error else None
        loop_bearing_body = bool(loop_body_inner) and _sql_body_is_loop_bearing(loop_body_inner)
        # After the routine's own definition is recorded, everything the body
        # mints via analyze_statement (in-body CREATE TABLE / CREATE VIEW, etc.)
        # is dropped: a routine body never defines schema objects at module
        # scope — the same stance the recovery tier takes for recovered bodies
        # (handle_error_region discards nested definitions from its body
        # re-parse). The body's *references* (with their clause-derived
        # direction and routine owner) and its temp-name exclusions are kept.
        #
        # R6a (wave 1rrx5): the drop is UNCONDITIONAL on routine nodes so the
        # "bodies never define at module scope" invariant is TOTAL — the floor
        # starts at the current definition count (before this routine adds
        # anything) and is bumped past the routine's own definition once its
        # name parses. If the header name does NOT parse as an object_reference
        # (an unnamed-but-parseable `CREATE FUNCTION () RETURNS integer …`,
        # where the empty name leaves routine_name None and a builtin return
        # type is a non-object_reference `int` node), the floor stays at the
        # pre-routine count and every in-body definition is still dropped
        # (previously this leaked because the drop was gated on a parsed name).
        body_def_floor = len(definitions)
        routine_ref_floor = len(references)
        for child in _sql_node_children(create_node):
            ctype = str(getattr(child, "type", "") or "")
            if ctype == "object_reference" and routine_name is None:
                name, schema = _sql_object_reference_parts(child, source_bytes)
                if name:
                    routine_name = name
                    definitions.append({
                        "name": name,
                        "schema": schema,
                        "sql_kind": sql_kind,
                        "temporary": False,
                        "node": statement_node,
                    })
                    body_def_floor = len(definitions)
            elif ctype == "object_reference" and expect_return_type:
                # 1p9qi review fix (adversarial finding 3): `RETURNS <type>`
                # parses as a second top-level object_reference — a return
                # TYPE name, never a table — same stance as the invocation-
                # name exclusion above (a name is not a reference).
                expect_return_type = False
            elif ctype == "object_reference" and expect_action_name:
                # R1 (wave 1rrx5): a trigger's `EXECUTE FUNCTION <name>` /
                # `EXECUTE PROCEDURE <name>` action name parses as a trailing
                # object_reference AFTER `keyword_execute` (and an intervening
                # `keyword_function`/`keyword_procedure`) — a routine name, not
                # a table. Skip it. The ON-table read (which appears BEFORE
                # keyword_execute) is already minted by the else branch, so it
                # is preserved. The flag latches from keyword_execute until this
                # object_reference is consumed so the intervening keyword does
                # not clear it.
                expect_action_name = False
            else:
                expect_return_type = ctype == "keyword_returns"
                if ctype == "keyword_execute":
                    expect_action_name = True
                walk_reads(child, "from", f"create_{sql_kind}", routine_name, cte_names)
        del definitions[body_def_floor:]
        # Loop-body DML recovery (wave 1rs45) — AUGMENT the walk above, do not
        # replace it. The normal body walk already runs (its statement dispatch
        # is more robust than the strip-reparse for assignment-heavy PL/pgSQL
        # bodies, where `recover=False` re-traps a DML in an ERROR — a real-corpus
        # finding), so it stays the recall floor. For a loop-bearing body we
        # ADDITIONALLY strip the loop scaffolding and reparse the residue through
        # the statement unit (`recover=False`, no recursion) to recover the DML
        # the parser absorbed after `LOOP` into the header query's `relation` span
        # — the residual the walk cannot reach. Only references the walk did NOT
        # already produce for this routine are appended (dedup on
        # direction+name), so a table the walk found is recorded exactly once and
        # never doubled; the added refs attach to the routine owner with
        # `sql_recovery` provenance. In-body definitions from the reparse are
        # ignored (routine bodies never define at module scope).
        #
        # Gated on `recover` so the strip runs ONLY at the top level, never inside
        # the strip's own `recover=False` reparse — the same one-level contract
        # `handle_error_region` uses for its body re-parse. The residue strictly
        # shrinks each level anyway, but this makes the no-recursion contract
        # explicit rather than incidental (code-review delivery lane 2026-07-06).
        if loop_bearing_body and recover:
            stripped = _sql_strip_loop_scaffolding(loop_body_inner)
            if stripped.strip():
                body_tree = _ts_parse("sql", stripped)
                if body_tree is not None:
                    reparsed = _sql_analyze_program(
                        body_tree.root_node, stripped.encode("utf-8"), recover=False
                    )
                    temp_names.update(reparsed["temp_names"])
                    already = {
                        (r["direction"], r["name"]) for r in references[routine_ref_floor:]
                    }
                    added_any = False
                    for ref in reparsed["references"]:
                        key = (ref["direction"], ref["name"])
                        if key in already:
                            continue
                        already.add(key)
                        references.append({
                            **ref,
                            "owner": routine_name if ref["owner"] is None else ref["owner"],
                            "extraction": _SQL_RECOVERY_MARKER,
                        })
                        added_any = True
                    if added_any:
                        partial_bodies_recovered += 1

    def analyze_statement(stmt_node, owner: str | None, outer_cte_names: set[str] | None = None) -> None:
        cte_names = set(outer_cte_names or ()) | _sql_collect_cte_names(stmt_node, source_bytes)
        children = _sql_node_children(stmt_node)
        child_types = [str(getattr(c, "type", "") or "") for c in children]
        is_delete = "delete" in child_types
        is_merge = "keyword_merge" in child_types
        is_truncate = "keyword_truncate" in child_types
        if is_merge:
            pending: str | None = None
            for child in children:
                ctype = str(getattr(child, "type", "") or "")
                if ctype == "keyword_into":
                    pending = "merge_into"
                elif ctype == "keyword_using":
                    pending = "merge_using"
                elif ctype == "object_reference" and pending is not None:
                    make_ref(
                        child,
                        direction="write" if pending == "merge_into" else "read",
                        clause=pending, statement="merge", owner=owner, cte_names=cte_names,
                    )
                    pending = None
                elif ctype == "subquery":
                    walk_reads(child, "from", "merge", owner, cte_names)
                elif ctype == "cte":
                    walk_reads(child, "from", "merge", owner, cte_names)
                elif ctype == "when_clause":
                    # R2 (wave 1rrx5): a MERGE `WHEN … THEN` branch holds real
                    # table reads inside subqueries — a `SET x = (SELECT v FROM
                    # lookup_tbl)` assignment and an `INSERT … VALUES ((SELECT …
                    # FROM seed_tbl))` (the VALUES subquery is `list`-wrapped,
                    # which walk_reads skips, so route the subquery NODES
                    # directly). Walk the when_clause subtree at UNBOUNDED depth
                    # and route every `subquery` node found — a subquery nested
                    # at ANY depth under the when_clause is reached (the stack
                    # descends through intervening wrapper nodes; a found
                    # subquery is handed to walk_reads, which recurses into its
                    # own nested subqueries). Bounded by the reference filter,
                    # not by depth: predicate columns and the assignment LHS
                    # parse as `field`/`column` (skipped), merge aliases are
                    # plain `identifier` siblings (walk_reads mints only at
                    # object_reference) — none mint a reference.
                    stack = _sql_node_children(child)
                    while stack:
                        node = stack.pop(0)
                        if str(getattr(node, "type", "") or "") == "subquery":
                            walk_reads(node, "from", "merge", owner, cte_names)
                        else:
                            stack.extend(_sql_node_children(node))
            return
        for child in children:
            ctype = str(getattr(child, "type", "") or "")
            if ctype == "create_table":
                handle_create_table(child, stmt_node)
            elif ctype in ("create_view", "create_materialized_view"):
                handle_create_view(child, stmt_node, cte_names)
            elif ctype in ("create_function", "create_procedure", "create_trigger"):
                handle_create_routine(child, stmt_node, _SQL_CREATE_KIND_BY_NODE[ctype], cte_names)
            elif ctype == "create_index":
                for sub in _sql_node_children(child):
                    if str(getattr(sub, "type", "") or "") == "object_reference":
                        make_ref(sub, direction="read", clause="index_on",
                                 statement="create_index", owner=owner, cte_names=cte_names)
            elif ctype.startswith("alter_"):
                for sub in _sql_node_children(child):
                    if str(getattr(sub, "type", "") or "") == "object_reference":
                        make_ref(sub, direction="write", clause="alter",
                                 statement=ctype, owner=owner, cte_names=cte_names)
                        break  # only the altered object; column REFERENCES etc. below
                # FK targets added by ALTER ... ADD CONSTRAINT ... REFERENCES:
                seen_first = False
                stack = _sql_node_children(child)
                while stack:
                    current = stack.pop(0)
                    if str(getattr(current, "type", "") or "") == "object_reference":
                        if not seen_first:
                            seen_first = True
                            continue
                        make_ref(current, direction="read", clause="references",
                                 statement=ctype, owner=owner, cte_names=cte_names)
                        continue
                    stack.extend(_sql_node_children(current))
            elif ctype.startswith("drop_"):
                for sub in _sql_node_children(child):
                    if str(getattr(sub, "type", "") or "") == "object_reference":
                        make_ref(sub, direction="write", clause="drop",
                                 statement=ctype, owner=owner, cte_names=cte_names)
            elif ctype == "insert":
                insert_children = _sql_node_children(child)
                target = next(
                    (c for c in insert_children if str(getattr(c, "type", "") or "") == "object_reference"),
                    None,
                )
                make_ref(target, direction="write", clause="insert_into",
                         statement="insert", owner=owner, cte_names=cte_names)
                for sub in insert_children:
                    if sub is target:
                        continue
                    walk_reads(sub, "from", "insert", owner, cte_names)
            elif ctype == "update":
                for sub in _sql_node_children(child):
                    stype = str(getattr(sub, "type", "") or "")
                    if stype == "relation":
                        for rel_child in _sql_node_children(sub):
                            if str(getattr(rel_child, "type", "") or "") == "object_reference":
                                make_ref(rel_child, direction="write", clause="update",
                                         statement="update", owner=owner, cte_names=cte_names)
                    elif stype == "object_reference":
                        make_ref(sub, direction="write", clause="update",
                                 statement="update", owner=owner, cte_names=cte_names)
                    else:
                        walk_reads(sub, "from", "update", owner, cte_names)
            elif ctype == "from" and is_delete:
                # DELETE FROM t: the from clause's DIRECT relation is the
                # WRITE target; anything deeper (joins, where subqueries)
                # remains read-direction.
                for sub in _sql_node_children(child):
                    stype = str(getattr(sub, "type", "") or "")
                    if stype == "object_reference":
                        make_ref(sub, direction="write", clause="delete_from",
                                 statement="delete", owner=owner, cte_names=cte_names)
                    elif stype == "relation":
                        for rel_child in _sql_node_children(sub):
                            if str(getattr(rel_child, "type", "") or "") == "object_reference":
                                make_ref(rel_child, direction="write", clause="delete_from",
                                         statement="delete", owner=owner, cte_names=cte_names)
                    else:
                        walk_reads(sub, "from", "delete", owner, cte_names)
            elif ctype == "object_reference" and is_truncate:
                make_ref(child, direction="write", clause="truncate",
                         statement="truncate", owner=owner, cte_names=cte_names)
            elif ctype in ("delete", "keyword_truncate"):
                continue
            else:
                walk_reads(child, "from", _sql_statement_kind(child_types), owner, cte_names)

    def _sql_statement_kind(child_types: list[str]) -> str:
        if "select" in child_types:
            return "select"
        return "statement"

    def handle_error_region(err_node) -> str | None:
        """Recovery (1p9qe) for one parse-ERROR region.

        Populates definitions/references/temp_names from the bounded
        line-anchored scan; when the region swallowed a single routine's
        BODY too (trigger form), re-parses the text after the recovered
        CREATE line through this unit (one level, ``recover=False``) and
        attaches the parseable fragments' references to the recovered
        routine. Nested definitions and nested ERROR counts from the
        re-parse are ignored — parsed routine bodies never mint definitions
        either, and the region is already counted once at this level.

        Returns the routine name an immediately-following dangling `block`
        should attribute to (single-routine regions only — 0 or 2+ recovered
        routines fall back to script scope rather than guessing).
        """
        nonlocal unrecovered_regions
        start_byte = int(getattr(err_node, "start_byte", 0) or 0)
        end_byte = int(getattr(err_node, "end_byte", 0) or 0)
        region_text = source_bytes[start_byte:end_byte].decode("utf-8", "replace")
        start_line = int((getattr(err_node, "start_point", None) or (0, 0))[0] or 0)
        recovered = _sql_recover_error_region(region_text, start_line)
        temp_names.update(recovered["temp_names"])
        for defn in recovered["definitions"]:
            definitions.append({
                "name": defn["name"],
                "schema": defn["schema"],
                "sql_kind": defn["sql_kind"],
                "temporary": False,
                "extraction": _SQL_RECOVERY_MARKER,
                "node": _SqlRecoveredNode(defn["line"]),
            })
        references.extend(dict(ref) for ref in recovered["references"])
        sole_routine = recovered["routines"][0] if len(recovered["routines"]) == 1 else None
        if sole_routine is not None:
            body_lines = region_text.splitlines(keepends=True)
            body_text = "".join(body_lines[sole_routine["match_line_offset"] + 1:])
            if body_text.strip():
                body_tree = _ts_parse("sql", body_text)
                if body_tree is not None:
                    nested = _sql_analyze_program(
                        body_tree.root_node, body_text.encode("utf-8"), recover=False
                    )
                    temp_names.update(nested["temp_names"])
                    for ref in nested["references"]:
                        if ref["owner"] is None:
                            references.append({
                                **ref,
                                "owner": sole_routine["name"],
                                "extraction": _SQL_RECOVERY_MARKER,
                            })
        if not recovered["definitions"] and not recovered["references"]:
            unrecovered_regions += 1
        return sole_routine["name"] if sole_routine is not None else None

    # Top-level scan (document order): analyze `statement` nodes; route
    # parse-ERROR regions through the 1p9qe recovery tier (counted loudly
    # either way). A dangling `block` immediately following an ERROR region
    # whose recovery yielded exactly ONE routine is that routine's body —
    # its statements attribute to the recovered routine instead of the
    # script level (the live-verified dangling-reference defect). A parsed
    # top-level statement closes the attribution window; comments between
    # the header and its block do not.
    pending_owner: str | None = None

    def scan_top(node, inherited_owner: str | None) -> None:
        nonlocal error_regions, unrecovered_regions, pending_owner
        for child in _sql_node_children(node):
            ctype = str(getattr(child, "type", "") or "")
            if ctype == "ERROR":
                error_regions += 1
                pending_owner = None
                if recover:
                    pending_owner = handle_error_region(child)
                else:
                    unrecovered_regions += 1
            elif ctype == "statement":
                analyze_statement(child, inherited_owner)
                if inherited_owner is None:
                    pending_owner = None
            elif ctype in ("comment", "marginalia"):
                continue
            elif ctype == "block":
                owner = pending_owner if pending_owner is not None else inherited_owner
                pending_owner = None
                ref_start = len(references)
                scan_top(child, owner)
                # 1p9qi review: a dangling-block re-attribution depends on the
                # recovery tier exactly like the region-tail re-parse — mark
                # BOTH `sql_recovery`. Any non-None owner reaching scan_top
                # traces back to handle_error_region's recovered routine
                # (parsed CREATE bodies attribute inside analyze_statement,
                # never through this scan), so the gate is just `owner`.
                if owner is not None:
                    for _ref in references[ref_start:]:
                        if _ref.get("owner") == owner and not _ref.get("extraction"):
                            _ref["extraction"] = _SQL_RECOVERY_MARKER
            else:
                scan_top(child, inherited_owner)

    scan_top(root_node, None)

    return {
        "definitions": definitions,
        "references": references,
        "temp_names": temp_names,
        "error_regions": error_regions,
        "unrecovered_regions": unrecovered_regions,
        "partial_bodies": partial_bodies,
        "partial_bodies_recovered": partial_bodies_recovered,
    }


def sql_statement_references(sql_text: str) -> dict[str, Any] | None:
    """Standalone SQL statement-analysis unit (wave 1p9qi / 1p9qd).

    THE contract for `1p9qf`'s embedded-SQL bind stage (and `1p9qe`'s
    recovered-body analysis): parse SQL text with no file-node context and
    return the clause-aware reference list — the same list the SQL file
    extraction path derives its edges from (parity-tested). Returns None
    when the SQL grammar is unavailable; see the section comment above for
    the reference/definition dict shapes and guarantees.
    """
    tree = _ts_parse("sql", sql_text)
    if tree is None:
        return None
    source_bytes = sql_text.encode("utf-8")
    analysis = _sql_analyze_program(tree.root_node, source_bytes)
    temp_names = analysis["temp_names"]
    references = [
        {**ref, "extraction": ref.get("extraction")}
        for ref in analysis["references"]
        if ref["name"].casefold() not in temp_names
    ]
    # Parsed extraction wins name collisions; recovery is strictly additive.
    parsed_names = {d["name"] for d in analysis["definitions"] if not d.get("extraction")}
    definitions = [
        {
            "name": d["name"], "schema": d["schema"], "sql_kind": d["sql_kind"],
            "temporary": d["temporary"], "extraction": d.get("extraction"),
        }
        for d in analysis["definitions"]
        if not (d.get("extraction") and d["name"] in parsed_names)
    ]
    return {
        "references": references,
        "definitions": definitions,
        "error_regions": analysis["error_regions"],
        "recovery": {
            "recovered_definitions": sum(1 for d in definitions if d["extraction"]),
            "unrecovered_regions": analysis["unrecovered_regions"],
            "partial_bodies": analysis["partial_bodies"],
            "partial_bodies_recovered": analysis["partial_bodies_recovered"],
        },
    }


def _sql_apply_file_extraction(
    root_node,
    source_bytes: bytes,
    *,
    module_id: str,
    node_map: dict[str, dict[str, Any]],
    register_symbol,
    add_edge,
) -> None:
    """SQL file extraction through the statement-analysis unit.

    Registers schema-object definitions (tables/views/routines with a
    `sql_kind` node property), then emits `reads`/`writes` edges for the
    clause-aware references. Same-file resolution mirrors the 1p7dg
    convention: an exact qualified-name match or a UNIQUE bare-name match
    binds at RECEIVER_RESOLVED; local ambiguity or no local match emits
    `external::<name>` at EXTRACTED for the cross-file machinery (which
    applies the same qualified-first / unique-bare / refuse-on-ambiguity
    rules). Temp objects are script-scoped: never registered, and references
    to their names are dropped (AC-6).
    """
    analysis = _sql_analyze_program(root_node, source_bytes)
    owner_ids: dict[str, str] = {}
    local_qname: dict[str, str] = {}
    local_bare: dict[str, list[str]] = {}
    recovered_count = 0
    # Parsed definitions register first: parsed extraction wins name
    # collisions, recovery (1p9qe) is strictly additive on top of it.
    parsed_defs = [d for d in analysis["definitions"] if not d.get("extraction")]
    recovered_defs = [d for d in analysis["definitions"] if d.get("extraction")]
    for defn in parsed_defs + recovered_defs:
        if defn.get("extraction") and defn["name"] in owner_ids:
            continue
        kind = "class" if defn["sql_kind"] in ("table", "view") else "function"
        node_id = register_symbol(defn["name"], kind, defn["node"], None)
        node_map[node_id]["sql_kind"] = defn["sql_kind"]
        if defn.get("extraction"):
            # Degradation-honesty marker: this object came from the ERROR-
            # region recovery scan, not a trusted parse.
            node_map[node_id]["extraction"] = defn["extraction"]
            recovered_count += 1
        owner_ids[defn["name"]] = node_id
        local_qname.setdefault(defn["name"], node_id)
        bare = defn["name"].rsplit(".", 1)[-1]
        bucket = local_bare.setdefault(bare, [])
        if node_id not in bucket:
            bucket.append(node_id)
    temp_names = analysis["temp_names"]
    for ref in analysis["references"]:
        name = ref["name"]
        if name.casefold() in temp_names:
            continue
        source = owner_ids.get(ref["owner"]) if ref["owner"] else None
        if source is None:
            source = module_id
        confidence = "RECEIVER_RESOLVED"
        target = local_qname.get(name)
        if target is None and "." not in name:
            bare_matches = local_bare.get(name, [])
            if len(bare_matches) == 1:
                target = bare_matches[0]
        if target is None:
            # R4 (wave 1rrx5): node-id hygiene — a bracket/backtick/quote-
            # quoted T-SQL/MySQL identifier (`[dbo].[users]`) that the grammar
            # mis-parses (ref name `dbo].[users`) must not mint a mangled
            # `external::dbo].[users`. Normalize ONLY the emitted external id
            # via the existing quote-strip table; the statement unit's
            # names-as-written output (`ref["name"]`) is untouched. Binding
            # stays unique-match-or-drop, so two differently-quoted forms
            # collapsing onto one `external::dbo.users` point at the SAME
            # external node (correct), never a wrong bind.
            target = f"external::{_sql_normalize_object_name(name) or name}"
            confidence = "EXTRACTED"
        if target == source:
            # Self-references (self-FK, a view named in its own body) carry
            # no graph value — 1p9qc's self-referential-import precedent.
            continue
        relation = GRAPH_WRITES_RELATION if ref["direction"] == "write" else GRAPH_READS_RELATION
        add_edge(source, target, relation, confidence=confidence, evidence=ref["clause"])
    if analysis["error_regions"]:
        # Loud degradation counts (1p9qe convention): total parse-ERROR
        # regions (frozen 1p9qd contract), how many definitions the recovery
        # tier extracted from them, and how many regions yielded nothing.
        node_map[module_id]["sql_error_regions"] = analysis["error_regions"]
        if recovered_count:
            node_map[module_id]["sql_recovered_definitions"] = recovered_count
        if analysis["unrecovered_regions"]:
            node_map[module_id]["sql_unrecovered_regions"] = analysis["unrecovered_regions"]
    if analysis["partial_bodies"]:
        # Loudness for the nested-in-body ERROR case (1p9qi delivery council):
        # a natively-parsed routine whose BODY holds a parse-ERROR (a PL/pgSQL
        # loop / control-flow construct tree-sitter-sql cannot parse) may drop
        # some in-body DML. Because the header parses at top level,
        # `error_regions` never counts it — so this is set OUTSIDE the
        # error_regions gate above. Kept DISTINCT from sql_unrecovered_regions
        # (top-level ERROR regions): the semantics differ.
        #
        # Wave 1rs45 recovered/unrecovered split: `sql_partial_bodies` stays the
        # total (routines with a nested body ERROR — the honest loudness signal);
        # `sql_partial_bodies_recovered` counts those the loop-strip-reparse
        # recovered in-loop DML from. The remainder (total − recovered) are
        # genuinely still partial — non-loop control-flow ERRORs, or loop bodies
        # the strip yielded nothing new for — so the signal never claims more
        # than was actually recovered.
        node_map[module_id]["sql_partial_bodies"] = analysis["partial_bodies"]
        if analysis.get("partial_bodies_recovered"):
            node_map[module_id]["sql_partial_bodies_recovered"] = analysis["partial_bodies_recovered"]


def _ts_relation_candidates(
    node,
    source_bytes: bytes,
    relation: str,
    mode: str,
    profile: _TsLanguageProfile | None = None,
) -> list[str]:
    candidates = []
    for field_name in _ts_relation_field_names(relation, mode):
        try:
            child = node.child_by_field_name(field_name)
        except Exception:
            child = None
        if child is None:
            continue
        candidate = _ts_clean_name(_ts_node_text(child, source_bytes))
        if candidate and not _ts_candidate_rejected(candidate) and candidate not in candidates:
            candidates.append(candidate)
    if candidates:
        return candidates
    # For "call" relation in code mode, field-name lookup may miss for
    # grammars whose call_expression exposes the callee positionally rather
    # than via a named field (Swift, Kotlin). Try the positional fallback
    # (wave 130ol): walk named_children, skip argument-list nodes, and
    # extract the rightmost identifier from the first non-suffix child.
    # Safe because the caller (walk_calls) has already confirmed the node
    # is a call via the explicit per-language ``profile.call_node_types``.
    if relation == "call" and mode == "code":
        positional = _ts_extract_callee_positional(node, source_bytes)
        if positional and not _ts_candidate_rejected(positional):
            profile_stop = profile.stop_terms if profile is not None else frozenset()
            if positional not in _STOP_TERMS and positional not in profile_stop:
                return [positional]
        return []
    text = _ts_node_text(node, source_bytes)
    if not text:
        return []
    # Fall back to a light parse of the AST span, keeping the grammar boundary.
    # Preserved for non-call relations (e.g. import) where the multi-token
    # fallback is still useful and the noise risk is lower.
    raw_candidates = re.findall(r"[A-Za-z_][A-Za-z0-9_.$:#/\-]*", text)
    profile_stop = profile.stop_terms if profile is not None else frozenset()
    fallback_candidates = [
        candidate for candidate in raw_candidates
        if candidate not in _STOP_TERMS
        and candidate not in profile_stop
        # Import-only: statement keywords (`import`/`use`/`as`/…) are never import
        # targets, but several (`from`, `require`, `default`) ARE valid method/
        # function names, so the filter must NOT touch call candidates.
        and not (relation == "import" and candidate in _RELATION_KEYWORD_NOISE)
        and not _ts_candidate_rejected(candidate)
    ]
    return fallback_candidates


def _ts_pick_symbol_name(candidates: list[str], mode: str, node_type: str) -> str:
    if not candidates:
        return ""
    if mode == "markup":
        for candidate in candidates:
            if candidate and candidate.casefold() not in _STOP_TERMS:
                return candidate
        return candidates[0]
    if mode == "sql":
        for candidate in candidates:
            if candidate and candidate.casefold() not in _STOP_TERMS:
                return candidate
        return candidates[0]
    if mode == "config":
        for candidate in candidates:
            if candidate and candidate.casefold() not in _STOP_TERMS:
                return candidate
        return candidates[0]
    for candidate in candidates:
        simple = candidate.rsplit(".", 1)[-1].casefold()
        if simple and simple not in _STOP_TERMS:
            return candidate
    return candidates[0]


# Wave 1p61v: a valid code symbol name is a plain identifier. `function` is a
# fully-reserved word in every C-family / TS / JS grammar, so it can never be a
# real definition name — anonymous `function (…) {}` expressions otherwise
# registered as a junk symbol literally named `function` (p60n field trace,
# Issue 2: `function (function)` entry points). Deliberately minimal: contextual
# keywords that ARE legal identifiers (`type`, `async`, `await`, `yield`, `fn`,
# `func`, …) are NOT listed, so no real symbol is ever dropped.
_TS_SYMBOL_NAME_RE = re.compile(r"^[A-Za-z_$][\w$]*$")
_TS_NEVER_SYMBOL_NAMES = frozenset({"function"})


def _ts_is_emittable_symbol_name(name: str, mode: str) -> bool:
    """False when ``name`` is a parser artifact rather than a real symbol.

    Markup / SQL / config names legitimately include dashes, dots, and slashes,
    so only code-mode names are required to be plain identifiers. Catches the
    anonymous-function `function` junk node and non-identifier route-path tokens
    (`/`, `/users`) without rejecting any legal identifier.

    NOTE: the caller gates this to TS/JS only. The plain-identifier rule would
    wrongly reject legitimate non-identifier symbol names in other languages
    (C++ `operator==`, Rust operators, Ruby `valid?`/`save!`/`<=>`), so it must
    not be applied to them.
    """
    if not name:
        return False
    if mode in ("markup", "sql", "config"):
        return True
    simple = name.rsplit(".", 1)[-1]
    if not _TS_SYMBOL_NAME_RE.match(simple):
        return False
    return simple not in _TS_NEVER_SYMBOL_NAMES


def _ts_extract_arrow_const_bindings(node, source_bytes: bytes) -> list[tuple[str, "Any"]]:
    """Extract function names from `const X = (...) => {...}` / `const X = function() {...}` shapes.

    Wave 1p2q3 (1p2tz post-ship per field validation): modern TS code
    extensively uses `export const myFunc = async (args) => { ... }` instead
    of `export function myFunc(args) { ... }`. Tree-sitter parses these as
    ``lexical_declaration → variable_declarator → arrow_function`` rather than
    ``function_declaration``, so the standard name-from-descendants extractor
    finds no identifier at the lexical_declaration level and the symbol never
    registers. This helper walks the lexical_declaration's variable_declarator
    children, returns one (name, declarator_node) per function-bound declarator.

    Returns empty list when ``node`` isn't a lexical_declaration / variable_statement
    or when no child binds a function-shaped expression.
    """
    if node is None:
        return []
    node_type = str(getattr(node, "type", "") or "")
    if node_type not in ("lexical_declaration", "variable_statement", "variable_declaration"):
        return []
    bindings: list[tuple[str, "Any"]] = []
    for child in (getattr(node, "named_children", []) or []):
        if str(getattr(child, "type", "") or "") != "variable_declarator":
            continue
        # Identify the bound name and whether the value is function-shaped.
        decl_children = list(getattr(child, "children", []) or [])
        name = ""
        is_fn_value = False
        for dc in decl_children:
            dctype = str(getattr(dc, "type", "") or "")
            if dctype == "identifier" and not name:
                name = source_bytes[dc.start_byte:dc.end_byte].decode("utf-8", errors="replace").strip()
            elif dctype in ("arrow_function", "function_expression", "function"):
                is_fn_value = True
        if name and is_fn_value:
            bindings.append((name, child))
    return bindings


def _ts_extract_import_module_specifier(import_node, source_bytes: bytes) -> str:
    """Return the raw module-specifier text from a TS/JS import statement.

    Wave 1p2q3 (1p2tz post-ship-3 per field validation): the existing
    `_ts_relation_candidates` path runs every candidate through `_ts_clean_name`
    which strips leading `./` and `../` characters (the regex starts at the
    first identifier character). That's correct for general identifier
    handling but loses the relative-import shape — both `./events` and `events`
    collapse to `"events"` at the call site of `_resolve_ts_import_via_tsconfig`,
    so the resolver can't tell that `./events` should go through the
    relative-path resolver instead of the tsconfig.paths resolver. This helper
    returns the raw specifier (quotes stripped, but `./` preserved) so the
    import handler can branch on the actual import shape.

    Returns empty string when the import has no parseable source field
    (e.g. side-effect-only imports without `from` clause).
    """
    if import_node is None:
        return ""
    # Try the `source` field first (tree-sitter TS exposes it directly on
    # import_statement). Fall back to scanning children for a `string` node.
    src_node = None
    try:
        src_node = import_node.child_by_field_name("source")
    except Exception:
        src_node = None
    if src_node is None:
        for child in (getattr(import_node, "children", []) or []):
            if str(getattr(child, "type", "") or "") == "string":
                src_node = child
                break
    if src_node is None:
        return ""
    text = source_bytes[src_node.start_byte:src_node.end_byte].decode("utf-8", errors="replace").strip()
    # Strip surrounding quotes (single or double or backtick).
    if len(text) >= 2 and text[0] in ("'", '"', "`") and text[0] == text[-1]:
        text = text[1:-1]
    return text


def _ts_extract_imported_names(import_node, source_bytes: bytes) -> list[str]:
    """Return the locally-bound names introduced by a TS/JS import statement.

    Wave 1p2q3 (1p2tf): supports the four shapes consumers care about for
    receiver-type resolution:
      - named:      `import { Foo, Bar } from '@scope/lib'` → ['Foo', 'Bar']
      - named alias: `import { Foo as F } from '@scope/lib'` → ['F']
      - default:    `import Default from '@scope/lib'` → ['Default']
      - namespace:  `import * as Util from '@scope/lib'` → ['Util']
      - type-only:  `import type { Foo } from '@scope/lib'` → ['Foo']
                    (the `type` keyword sits between `import` and `import_clause`)
    Returns an empty list when no imported names are surfaced (side-effect
    imports like `import './polyfill';`).
    """
    if import_node is None:
        return []
    names: list[str] = []
    for child in (getattr(import_node, "children", []) or []):
        if getattr(child, "type", "") != "import_clause":
            continue
        for clause_child in (getattr(child, "children", []) or []):
            ctype = getattr(clause_child, "type", "") or ""
            if ctype == "identifier":
                # Default import: import_clause contains a direct identifier.
                names.append(
                    source_bytes[clause_child.start_byte:clause_child.end_byte].decode("utf-8", errors="replace")
                )
            elif ctype == "named_imports":
                for spec in (getattr(clause_child, "children", []) or []):
                    if getattr(spec, "type", "") != "import_specifier":
                        continue
                    # When `as` alias is present, the SECOND identifier child is
                    # the local name; otherwise the single identifier IS the
                    # local name. Walk children left-to-right and grab the last
                    # identifier before any non-identifier separator.
                    spec_idents: list[str] = []
                    for sc in (getattr(spec, "children", []) or []):
                        if getattr(sc, "type", "") == "identifier":
                            spec_idents.append(
                                source_bytes[sc.start_byte:sc.end_byte].decode("utf-8", errors="replace")
                            )
                    if spec_idents:
                        names.append(spec_idents[-1])
            elif ctype == "namespace_import":
                for sc in (getattr(clause_child, "children", []) or []):
                    if getattr(sc, "type", "") == "identifier":
                        names.append(
                            source_bytes[sc.start_byte:sc.end_byte].decode("utf-8", errors="replace")
                        )
                        break
    return [n for n in names if n]


def _ts_import_aliases(node, source_bytes: bytes, mode: str) -> dict[str, str]:
    text = _ts_node_text(node, source_bytes)
    aliases: dict[str, str] = {}
    if not text:
        return aliases
    for imported, alias in re.findall(r"\b([A-Za-z_][A-Za-z0-9_.$:#/\-]*)\s+as\s+([A-Za-z_][A-Za-z0-9_]*)\b", text):
        aliases[alias] = imported
    for alias, target in re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([A-Za-z_][A-Za-z0-9_.$:#/\-]*)\b", text):
        aliases[alias] = target
    if mode in {"markup", "sql", "config"}:
        return aliases
    if "require(" in text or "import" in text or "using" in text or "use " in text:
        simple_targets = re.findall(r"[A-Za-z_][A-Za-z0-9_.$:#/\-]*", text)
        for candidate in simple_targets:
            if candidate not in aliases:
                aliases[candidate] = candidate
    return aliases


def _ts_resolve_target(candidate: str, symbol_lookup: dict[str, str], import_aliases: dict[str, str]) -> str:
    clean = _ts_clean_name(candidate)
    if not clean:
        return ""
    if clean in import_aliases:
        return f"external::{import_aliases[clean]}"
    if clean in symbol_lookup:
        return symbol_lookup[clean]
    simple = _simple_name(clean)
    if simple in symbol_lookup:
        mapped = symbol_lookup[simple]
        if mapped:
            return mapped
    if "." in clean:
        head, tail = clean.split(".", 1)
        if head in import_aliases:
            return f"external::{import_aliases[head]}.{tail}"
    return f"external::{clean}"


# ---------------------------------------------------------------------------
# Cross-file resolution helpers (wave 1p9q3 / 1p9q2)
#
# The per-edge resolution logic below is EXTRACTED MECHANICALLY from the former
# in-place rewrite loop in `finalize()` — semantics unchanged (the wrong-twin
# faithfulness contract lives here; every branch still requires a UNIQUE
# match). Extraction lets the unified merge pipeline run the exact same code
# for a full merge and for symbol-scoped incremental re-resolution.
# ---------------------------------------------------------------------------

# Merge-state sidecar format version (bump when the sidecar shape changes so an
# older sidecar degrades to a loud full re-merge instead of misparsing).
_MERGE_STATE_FORMAT = "1"

# Fragment-edge provenance keys (wave 1p9q2). A stored resolved fragment edge
# carries enough provenance to recover its raw (extraction-time) form so a
# later symbol-delta can re-run resolution — promotion AND demotion:
#   _x — original `external::<bare>` name of a rewritten target
#   _c — original confidence when exact-unique promotion changed it
#   _d — tombstone: unresolved external `reads` edge (dropped from output,
#        retained so a later unique candidate can re-promote it)
_PROV_EXT = "_x"
_PROV_CONF = "_c"
_PROV_DROP = "_d"

# Analytics flags are recomputed fresh every build from the merged maps; they
# are stripped wherever nodes enter the merge so per-file state stays pristine.
_ANALYTICS_NODE_FLAGS = ("is_entry_point", "dead_code_risk", "is_chokepoint")


def _rust_norm_join(base: str, rel: str) -> str:
    """Join a repo-relative dir with a (possibly ``../``) relative path, normalized.

    Pure string normalization on forward-slash repo-relative paths (the form
    node ids use). ``.`` segments drop; ``..`` pops the accumulated tail.
    """
    parts: list[str] = []
    for seg in (base.split("/") if base else []) + rel.replace("\\", "/").split("/"):
        if seg in ("", "."):
            continue
        if seg == "..":
            if parts:
                parts.pop()
        else:
            parts.append(seg)
    return "/".join(parts)


def _rust_child_dir(file_path: str) -> str:
    """Directory under which a module file's ``mod child;`` children live.

    Rust 2018 rule: a crate root (``lib.rs``/``main.rs``) and a ``mod.rs`` file
    resolve children in their OWN directory; any other module file ``foo.rs``
    resolves children under a sibling ``foo/`` directory.
    """
    d = file_path.rsplit("/", 1)[0] if "/" in file_path else ""
    base = file_path.rsplit("/", 1)[-1]
    if base in ("lib.rs", "main.rs", "mod.rs"):
        return d
    stem = base[:-3] if base.endswith(".rs") else base
    return f"{d}/{stem}" if d else stem


def _resolve_rust_mod_file(
    child_dir: str, name: str, override: str | None, rs_files: set[str], parent_file: str
) -> str | None:
    """Resolve a ``mod name;`` declaration to the child module's file, or None.

    ``#[path = "…"]`` override wins and is resolved relative to the directory of
    the file that CONTAINS the ``mod`` declaration (correct for crate-root /
    ``mod.rs`` hosts — the common case). Otherwise the 2018-edition pair
    ``<child_dir>/name.rs`` then ``<child_dir>/name/mod.rs`` is tried. Returns a
    file only when it exists in the indexed set — an unresolved decl yields None
    so the child falls to per-file identity (never a guessed parent).
    """
    if override:
        pdir = parent_file.rsplit("/", 1)[0] if "/" in parent_file else ""
        cand = _rust_norm_join(pdir, override)
        return cand if cand in rs_files else None
    flat = f"{child_dir}/{name}.rs" if child_dir else f"{name}.rs"
    nested = f"{child_dir}/{name}/mod.rs" if child_dir else f"{name}/mod.rs"
    if flat in rs_files:
        return flat
    if nested in rs_files:
        return nested
    return None


def _build_rust_module_index(node_map: dict[str, dict[str, Any]]) -> dict[str, dict]:
    """Model each Rust definition's crate-relative module path (wave 1p9q5).

    Returns ``{"module_by_file": {file -> module-path}, "inline_mods_by_file":
    {file -> [dotted inline-mod qnames]}}``. The module path is derived from the
    ``mod`` declaration graph rooted at crate roots (``lib.rs``/``main.rs`` =
    ``crate``); files unreachable from any crate root (common under partial
    indexing) fall to a per-file identity ``mod-file:<path>`` that only ever
    equals itself — a missing model degrades to a recall gap (``external::``),
    never a wrong same-name bind. ``mod`` decls and inline-mod qnames are read
    from the ``rust_mod_decls`` / ``rust_inline_mods`` properties the extractor
    stores on each ``.rs`` file's module node (node-borne, so incremental merges
    recover them from per-file fragments, exactly like ``declared_package``).
    """
    rs_files: set[str] = set()
    mod_decls_by_file: dict[str, list[dict]] = {}
    inline_mods_by_file: dict[str, list[str]] = {}
    for node_id, node in node_map.items():
        if node_id.startswith("external::") or "::" in node_id:
            continue
        if not node_id.endswith(".rs"):
            continue
        rs_files.add(node_id)
        decls = node.get("rust_mod_decls")
        if decls:
            mod_decls_by_file[node_id] = decls
        inline = node.get("rust_inline_mods")
        if inline:
            inline_mods_by_file[node_id] = list(inline)
    module_by_file: dict[str, str] = {}
    # BFS from crate roots along the mod-declaration graph. A plain list acts as
    # the queue (order-independent result: each file is claimed by exactly one
    # parent — Rust forbids declaring the same module file from two places).
    queue: list[str] = []
    for f in sorted(rs_files):
        if f.rsplit("/", 1)[-1] in ("lib.rs", "main.rs"):
            module_by_file[f] = "crate"
            queue.append(f)
    head = 0
    while head < len(queue):
        f = queue[head]
        head += 1
        base_mod = module_by_file[f]
        child_dir = _rust_child_dir(f)
        for decl in mod_decls_by_file.get(f, []):
            name = decl.get("name")
            if not name:
                continue
            child = _resolve_rust_mod_file(child_dir, name, decl.get("path"), rs_files, f)
            if child and child not in module_by_file:
                module_by_file[child] = f"{base_mod}::{name}"
                queue.append(child)
    for f in rs_files:
        module_by_file.setdefault(f, f"mod-file:{f}")
    return {"module_by_file": module_by_file, "inline_mods_by_file": inline_mods_by_file}


def _rust_module_key(
    node_id: str, module_by_file: dict[str, str], inline_mods_by_file: dict[str, list[str]]
) -> str:
    """The full Rust module-path key for a definition node (wave 1p9q5).

    ``<file-module-path>`` optionally suffixed with the longest inline-``mod``
    qname (segment-aligned) that encloses the definition — so two defs in the
    same inline ``mod`` share a key while a file-scope def and an inline-mod def
    in the same file do NOT. Cross-file defs never share a key (each ``.rs`` file
    is a distinct module), so the tier can only bind a same-module candidate.
    """
    file_part = node_id.split("::", 1)[0]
    base = module_by_file.get(file_part) or f"mod-file:{file_part}"
    qn = node_id.split("::", 1)[1] if "::" in node_id else ""
    best = ""
    for m in inline_mods_by_file.get(file_part, ()):
        if (qn == m or qn.startswith(m + ".")) and len(m) > len(best):
            best = m
    if best:
        return f"{base}::" + best.replace(".", "::")
    return base


def _build_candidate_indexes(
    node_map: dict[str, dict[str, Any]],
) -> tuple[dict[str, list[str]], dict[str, list[str]], dict[str, set[str]], dict[str, str], dict[str, dict]]:
    """Build (simple_name_index, qualified_index, cs_file_ns, pkg_by_file, rust_module_index) from a node map.

    Extracted verbatim from finalize (waves 130ol/1312l/1316l/1p4ef/1p4ev/
    1p66e — see the inline comments retained below). Pure function of the node
    mapping; also runs on per-file node subsets to compute the symbol-delta
    keys for scoped re-resolution (the per-(file, simple) winner logic is
    per-file, so a whole-file subset yields exactly that file's contributions).

    Wave 1p9qh (1p9qb): ``pkg_by_file`` maps a Java/Kotlin file to its
    DECLARED package, harvested from the ``declared_package`` property the
    extractor stores on the file's module node. Node-derived like
    ``cs_file_ns``, so incremental merges rebuild it from per-file fragments
    with no extra state.

    Wave 1p9q5: ``rust_module_index`` models each Rust definition's crate-
    relative module path (``_build_rust_module_index``) so the same-module
    disambiguation tier can key on Rust's language-defined scope (the module
    tree, not the directory). Node-derived from ``rust_mod_decls`` /
    ``rust_inline_mods`` on each ``.rs`` module node, so it too rebuilds from
    per-file fragments on an incremental merge.
    """
    simple_name_index: dict[str, list[str]] = {}
    qualified_index: dict[str, list[str]] = {}
    per_file_simple: dict[tuple[str, str], str] = {}
    # Wave 1p4eq (1p4ev faithfulness fix): each C# file's DECLARED namespaces,
    # harvested from its namespace nodes (`file.cs::Namespace`, kind="module").
    cs_file_ns: dict[str, set[str]] = {}
    # Wave 1p9qh (1p9qb): each Java/Kotlin file's DECLARED package.
    pkg_by_file: dict[str, str] = {}
    for node_id, node in node_map.items():
        if node_id.startswith("external::"):
            continue  # external endpoint nodes are not project candidates
        if "::" not in node_id:
            _pkg = node.get("declared_package")
            if _pkg:
                pkg_by_file[node_id] = str(_pkg)
        if "::" in node_id and node.get("kind") == "module":
            _ns_file = node_id.split("::", 1)[0]
            if _ns_file.endswith(".cs"):
                cs_file_ns.setdefault(_ns_file, set()).add(node_id.split("::", 1)[1])
        # Wave 13129 (1316l): merged Swift class/module nodes (collapsed_pair=True)
        # live at the file id and carry the class label.
        is_collapsed_pair = bool(node.get("collapsed_pair"))
        if "::" not in node_id and not is_collapsed_pair:
            continue
        if is_collapsed_pair:
            file_part = node_id
            qualified = str(node.get("label") or "")
        else:
            file_part, qualified = node_id.split("::", 1)
        label = str(node.get("label") or "")
        simple = label or qualified.rsplit(".", 1)[-1]
        if not simple:
            continue
        key = (file_part, simple)
        # Keep the shortest qualified name (the outer/real definition), with a
        # lexicographic tie-break so the choice is order-independent (1p66e).
        per_file_simple[key] = _pick_shorter_node_id(per_file_simple.get(key), node_id)
    for (file_part, simple), node_id in per_file_simple.items():
        simple_name_index.setdefault(simple, []).append(node_id)
        if "::" in node_id:
            _, qualified = node_id.split("::", 1)
            if qualified and qualified != simple:
                qualified_index.setdefault(qualified, []).append(node_id)
        else:
            # Wave 1p4ef: collapsed / basename-merged node (no "::" in id) —
            # its qualified name IS its label (== simple).
            qualified = simple
        # Index a module-path-derived dotted form so per-file extractors that
        # emit dotted external targets can resolve to project nodes.
        dotted_module = re.sub(r"\.[A-Za-z0-9]+$", "", file_part).replace("/", ".")
        dotted_module = dotted_module.lstrip(".")
        if dotted_module:
            dotted_full = f"{dotted_module}.{qualified}"
            qualified_index.setdefault(dotted_full, []).append(node_id)
            parts = dotted_full.split(".")
            for i in range(1, len(parts)):
                suffix = ".".join(parts[i:])
                if "." in suffix:
                    qualified_index.setdefault(suffix, []).append(node_id)
    # Wave 13129 (1312l): dedupe entries — suffix-indexing can re-add the same
    # node under its direct qualified key; without dedupe `len(candidates)==1`
    # fails for legit single-candidate matches. Order preserved (stable).
    for _k in list(qualified_index.keys()):
        qualified_index[_k] = list(dict.fromkeys(qualified_index[_k]))
    for _k in list(simple_name_index.keys()):
        simple_name_index[_k] = list(dict.fromkeys(simple_name_index[_k]))
    rust_module_index = _build_rust_module_index(node_map)
    return simple_name_index, qualified_index, cs_file_ns, pkg_by_file, rust_module_index


def _candidate_delta_keys(nodes: list[dict[str, Any]]) -> set[str]:
    """Lookup keys contributed to the candidate indexes by these nodes.

    The symbol-delta unit for scoped re-resolution (wave 1p9q2): any candidate-
    index key with an old or new candidate in a changed/removed file may have a
    changed candidate SET, so every edge consulting that key must re-resolve.
    Computed by running the exact index builder on the subset — zero drift
    from the real index by construction.
    """
    subset: dict[str, dict[str, Any]] = {}
    for node in nodes:
        if isinstance(node, dict):
            node_id = str(node.get("id") or "")
            if node_id:
                subset.setdefault(node_id, node)
    simple_idx, qualified_idx, _, _, _ = _build_candidate_indexes(subset)
    return set(simple_idx) | set(qualified_idx)


def _build_imports_by_file(raw_edge_keys) -> tuple[dict[str, dict[str, str]], dict[str, list[str]]]:
    """Per-source-file import maps for ambiguous-receiver disambiguation.

    Extracted verbatim from finalize (waves 1p47e/1p66e): file -> { imported
    simple name -> import FQN }; on a final-segment collision keep the
    lexicographically smallest FQN (stable, order-independent).

    Wave 1p9qh (1p9q9): an import target ending in ``.*`` (the structured Java
    wildcard-import edge, ``external::com.foo.*``) is a PACKAGE-PREFIX fact,
    not a simple-name binding — it goes into the second returned map
    (file -> sorted list of wildcard-imported package prefixes) and is kept out
    of the simple-name buckets (its final segment ``*`` is never a receiver
    head). The wildcard map feeds the wildcard-participation pass in
    ``_resolve_external_call_target``.
    """
    imports_by_file: dict[str, dict[str, str]] = {}
    wildcard_imports_by_file: dict[str, set[str]] = {}
    for (e_src, e_tgt, e_rel, _e_conf) in raw_edge_keys:
        if e_rel == "imports" and e_tgt.startswith("external::"):
            fqn = e_tgt[len("external::"):]
            if not fqn:
                continue
            if fqn.endswith(".*"):
                _pkg = fqn[:-2]
                if _pkg:
                    wildcard_imports_by_file.setdefault(e_src, set()).add(_pkg)
                continue
            _seg = fqn.rsplit(".", 1)[-1]
            _bucket = imports_by_file.setdefault(e_src, {})
            _prev = _bucket.get(_seg)
            if _prev is None or fqn < _prev:
                _bucket[_seg] = fqn
    # Sorted lists for order-independence (1p66e determinism discipline).
    return imports_by_file, {
        f: sorted(pkgs) for f, pkgs in wildcard_imports_by_file.items()
    }


def _resolve_external_call_target(
    src: str,
    bare: str,
    conf: str,
    *,
    simple_name_index: dict[str, list[str]],
    qualified_index: dict[str, list[str]],
    imports_by_file: dict[str, dict[str, str]],
    cs_file_ns: dict[str, set[str]],
    wildcard_imports_by_file: dict[str, list[str]] | None = None,
    java_pkg_by_file: dict[str, str] | None = None,
    rust_module_index: dict[str, dict] | None = None,
) -> tuple[str | None, bool]:
    """Resolve one `external::<bare>` calls-edge target to a project node.

    Extracted verbatim from finalize's cross-file rewrite loop (waves 130ol/
    1312l/1319s/1p47e/1p4eq/1p4er/1p4et/1p4ev/1p2q3/1p7dg — inline comments
    retained). Returns ``(resolved_node_id_or_None, rewrote_exact)`` where
    ``rewrote_exact`` marks the exact-unique branches eligible for confidence
    promotion. Every branch still requires a UNIQUE (len==1) match — the
    never-bind-the-wrong-twin contract is unchanged.
    """
    if not bare or bare in _TS_GLOBAL_DENYLIST:
        return None, False
    # Wave 13129 (1312l): for edges emitted by receiver-type resolution
    # (confidence=RECEIVER_RESOLVED), trust the qualified match but BLOCK the
    # simple-name fallback. Wave 131bt (1319s): CONSTRUCTION_RESOLVED is a peer.
    _receiver_resolved = conf in ("RECEIVER_RESOLVED", "CONSTRUCTION_RESOLVED")
    resolved: str | None = None
    # Wave 1p2q3 / 1p7dg: track whether `resolved` was set by an EXACT-unique
    # branch — exact simple name (AC-1), exact qualified name, Go package-
    # authoritative match, or import-edge disambiguation. Those binds are
    # promoted EXTRACTED->RECEIVER_RESOLVED. The AC-2 simple-name fallback and
    # the same-dir / C# namespace HEURISTICS are NOT exact: they bind the
    # target but KEEP EXTRACTED confidence.
    rewrote_exact = False
    candidates: list[str] = []
    if "." in bare:
        # AC-2: qualified target — require an exact qualified-name match to a
        # project node's post-`::` portion. The final segment must also pass
        # the denylist (so `external::pathlib.Path` stays external even if
        # some project file defines `Path`).
        final_seg = bare.rsplit(".", 1)[-1]
        if final_seg in _TS_GLOBAL_DENYLIST:
            return None, False
        candidates = qualified_index.get(bare, [])
        if len(candidates) == 1:
            resolved = candidates[0]
            rewrote_exact = True  # exact qualified-name match
        elif not candidates and not _receiver_resolved:
            # Fallback: try the last segment in simple_name_index (with
            # ambiguity safety + denylist already checked). Skipped for
            # RECEIVER_RESOLVED edges: the resolver already determined the
            # target class — simple-name fallback would mis-rewrite to a
            # phantom project node.
            simple_candidates = simple_name_index.get(final_seg, [])
            if len(simple_candidates) == 1:
                resolved = simple_candidates[0]
    else:
        # AC-1: bare simple name match.
        candidates = simple_name_index.get(bare, [])
        if len(candidates) == 1:
            resolved = candidates[0]
            rewrote_exact = True  # exact simple-name match (AC-1)
    # Wave 1p4eq (1p4et faithfulness fix): Go package-qualified receiver — the
    # qualifier is AUTHORITATIVE: resolve only to a candidate whose package
    # (the Go-convention directory basename) matches. Stays external when no
    # project package matches (genuinely external, or a name collision).
    if (
        resolved is None
        and not candidates
        and bare.count(".") == 2
        and (src.split("::", 1)[0] if "::" in src else src).endswith(".go")
    ):
        pkg_head, inner_key = bare.split(".", 1)
        pkg_matches = []
        for cand in qualified_index.get(inner_key, []):
            cfile = cand.split("::", 1)[0]
            cdir = cfile.rsplit("/", 1)[0] if "/" in cfile else ""
            cpkg = cdir.rsplit("/", 1)[-1] if cdir else ""
            if cpkg == pkg_head:
                pkg_matches.append(cand)
        if len(pkg_matches) == 1:
            resolved = pkg_matches[0]
            rewrote_exact = True  # Go package-authoritative match
    # Wave 1p47e (1p470): import-edge disambiguation. When the simple/qualified
    # match above was ambiguous, use the SOURCE FILE's `imports` edge for the
    # receiver's head segment to pick the candidate whose defining module
    # matches what the file imported. Requires the filter to leave exactly ONE
    # candidate — a genuinely external receiver stays external.
    if resolved is None and len(candidates) > 1:
        src_file = src.split("::", 1)[0] if "::" in src else src
        head = bare.split(".", 1)[0]

        # Wave 1p9qh (1p9qb; adversarial fix F2): Java/Kotlin package identity
        # keys on the parsed `package` DECLARATION (`declared_package` on the
        # file's module node), with the directory as fallback for
        # declaration-less files. The `pkg:`/`dir:` prefixes keep the two key
        # spaces disjoint. Shared by the wildcard own-package-shadow guard AND
        # the same-package fallback tier below — the two MUST agree, or a
        # source whose declared package lives outside its mirroring directory
        # is shadow-guarded and package-bound under different identities.
        _pkg_map = java_pkg_by_file or {}

        def _pkg_key(f: str) -> str:
            _pkg = _pkg_map.get(f)
            if _pkg:
                return f"pkg:{_pkg}"
            return "dir:" + (f.rsplit("/", 1)[0] if "/" in f else "")

        imp_fqn = imports_by_file.get(src_file, {}).get(head)
        if imp_fqn:
            accept = {imp_fqn}
            if "." in imp_fqn:
                accept.add(imp_fqn.rsplit(".", 1)[0])
            matches = []
            for cand in candidates:
                cfile = cand.split("::", 1)[0]
                cmod = re.sub(r"\.[A-Za-z0-9]+$", "", cfile).replace("/", ".").lstrip(".")
                if cmod in accept:
                    matches.append(cand)
            if len(matches) == 1:
                resolved = matches[0]
                rewrote_exact = True  # import-edge-disambiguated unique match
        # Wave 1p9qh (1p9q9): wildcard-import participation. A wildcard import
        # (`import com.foo.*;` → package prefix "com.foo") is genuine
        # visibility evidence — an ambiguous candidate whose defining module
        # matches a wildcard-imported package is preferred EXACTLY like an
        # explicit import of `<pkg>.<head>` would be, with the same
        # unique-survivor rule: two candidates matching wildcard imports →
        # stay external, never guess. Runs only after the explicit-import
        # check above left the receiver unresolved (explicit precedence).
        # Java package shadowing guard: the source file's OWN package is an
        # implicit on-demand import that SHADOWS wildcard imports in Java, so
        # an own-package twin counts as a match for refusal purposes — the
        # same-package tier below (declared-package keyed, 1p9qb) then binds
        # it Java-faithfully.
        if resolved is None:
            _wild_pkgs = (wildcard_imports_by_file or {}).get(src_file, ())
            if _wild_pkgs:
                _accept_wild: set[str] = set()
                for _pkg in _wild_pkgs:
                    _accept_wild.add(f"{_pkg}.{head}")
                    _accept_wild.add(_pkg)
                # Own-package identity = the DECLARED package (directory
                # fallback) via `_pkg_key`, matching the 1p9qb same-package
                # tier's keying exactly — never the directory alone.
                # Adversarial fix (F2): keying this guard on the directory
                # let a source whose declared package lives outside its
                # mirroring directory bind a wildcard twin that Java
                # shadowing forbids — and, on an `extends` target, mint
                # wrong inherited call binds in untouched callers.
                _src_pkg_key = _pkg_key(src_file)
                _wild_matches: list[str] = []
                _own_matches: list[str] = []
                for cand in candidates:
                    _cfile = cand.split("::", 1)[0]
                    _cmod = re.sub(r"\.[A-Za-z0-9]+$", "", _cfile).replace("/", ".").lstrip(".")
                    if _cmod in _accept_wild:
                        _wild_matches.append(cand)
                    if _pkg_key(_cfile) == _src_pkg_key:
                        _own_matches.append(cand)
                if len(_wild_matches) == 1 and all(m in _wild_matches for m in _own_matches):
                    resolved = _wild_matches[0]
                    rewrote_exact = True  # wildcard-import-disambiguated unique match
        # Wave 1p4er: same-package fallback, GATED to languages with
        # package-level visibility without an import (Java/Kotlin/Go). Runs
        # ONLY after the import path left it unresolved: resolve iff exactly
        # one candidate shares the source's package.
        #
        # Wave 1p9qh (1p9qb): Java/Kotlin key on the parsed `package`
        # DECLARATION (the language fact the indexer already extracts —
        # `declared_package` on the file's module node), with the directory
        # as fallback for declaration-less files (default package ⇒ directory
        # locality, preserving pre-1p9qb behavior for package-less fixtures).
        # The `pkg:`/`dir:` prefixes keep the two key spaces disjoint so a
        # declared package can never coincide with a directory string. Both
        # flip directions are deliberate: split-directory same-package files
        # now disambiguate; same-directory different-package files now
        # refuse. Go keeps pure directory keying — a Go package IS its
        # directory, so directory keying is its declared semantics.
        if resolved is None and src_file.endswith(".go"):
            src_dir = src_file.rsplit("/", 1)[0] if "/" in src_file else ""
            same_dir = []
            for cand in candidates:
                cfile = cand.split("::", 1)[0]
                cdir = cfile.rsplit("/", 1)[0] if "/" in cfile else ""
                if cdir == src_dir:
                    same_dir.append(cand)
            if len(same_dir) == 1:
                resolved = same_dir[0]
        elif resolved is None and src_file.endswith((".java", ".kt", ".kts")):
            src_key = _pkg_key(src_file)
            same_pkg = []
            for cand in candidates:
                cfile = cand.split("::", 1)[0]
                if _pkg_key(cfile) == src_key:
                    same_pkg.append(cand)
            if len(same_pkg) == 1:
                resolved = same_pkg[0]
        # Wave 1p4ev: C# namespace membership — keep candidates whose namespace
        # is the source's OWN namespace or a `using`-imported one, deriving a
        # node's namespace from its file's DECLARED namespaces by longest
        # prefix (nesting-proof). Resolve iff exactly one survives.
        if resolved is None and src_file.endswith(".cs"):
            def _cs_ns(nid: str) -> str:
                f = nid.split("::", 1)[0]
                qn = nid.split("::", 1)[1] if "::" in nid else ""
                best = ""
                for ns in cs_file_ns.get(f, ()):
                    if (qn == ns or qn.startswith(ns + ".")) and len(ns) > len(best):
                        best = ns
                return best
            accept_ns = {_cs_ns(src)} | set(imports_by_file.get(src_file, {}).values())
            accept_ns.discard("")
            ns_matches = [c for c in candidates if _cs_ns(c) in accept_ns]
            if len(ns_matches) == 1:
                resolved = ns_matches[0]
        # Wave 1p9q5: Rust same-module membership — Rust's visibility rule is the
        # MODULE TREE (items in the same module are visible without `use`), not
        # the directory. Key each candidate on its full module-path (crate-
        # relative file-module path + longest enclosing inline-`mod` suffix) and
        # keep those equal to the call site's module. Resolve iff exactly one
        # survives; zero/multiple → stay external (never bind a same-name twin in
        # another module, and — the sharpest wrong-bind risk — never cross-bind a
        # file-scope def with an inline-`mod` def in the same file). A file whose
        # crate root is not indexed falls to a per-file identity, so an unmodeled
        # module degrades to a recall gap, not a wrong parent guess.
        if resolved is None and src_file.endswith(".rs"):
            _rmi = rust_module_index or {}
            _mbf = _rmi.get("module_by_file") or {}
            _imf = _rmi.get("inline_mods_by_file") or {}
            _src_key = _rust_module_key(src, _mbf, _imf)
            same_mod = [c for c in candidates if _rust_module_key(c, _mbf, _imf) == _src_key]
            if len(same_mod) == 1:
                resolved = same_mod[0]
    return resolved, rewrote_exact


def _resolve_external_read_target(
    src: str,
    bare: str,
    *,
    qualified_index: dict[str, list[str]],
    node_map: dict[str, dict[str, Any]],
) -> str | None:
    """Resolve one `external::<bare>` reads-edge target, or None to DROP.

    Extracted verbatim from finalize (wave 1p4ls, delivery review B2): bind an
    imported read ONLY to a UNIQUE constant matched by the import's QUALIFIED
    name — never guessed from a bare simple name. A read that cannot resolve
    to a unique qualified project constant is DROPPED, never wrong-bound.
    """
    if not bare:
        return None
    cands = [
        c
        for c in qualified_index.get(bare, [])
        if (node_map.get(c) or {}).get("kind") == GRAPH_CONST_KIND
    ]
    if len(cands) == 1 and cands[0] != src:
        return cands[0]
    return None


# Wave 1p9qi (1p9qd): file suffixes whose sources are SQL — derived from the
# language map so the two can never drift. Used to recognize SQL-origin
# `reads` edges (table references) in cross-file resolution: constant reads
# can never originate from a SQL file (SQL mode emits no identifier reads),
# so the source suffix is a sound routing signal.
_SQL_SOURCE_SUFFIXES = frozenset(
    ext for ext, lang in _TS_EXTENSION_TO_LANGUAGE.items() if lang == "sql"
)


def _sql_table_reference_edge(raw_edge: dict[str, Any]) -> bool:
    """True when a `reads` edge is a SQL table reference (source is a SQL file)."""
    if str(raw_edge.get("relation") or "") != GRAPH_READS_RELATION:
        return False
    src = str(raw_edge.get("source") or "")
    src_file = src.split("::", 1)[0] if "::" in src else src
    dot = src_file.rfind(".")
    return dot >= 0 and src_file[dot:].lower() in _SQL_SOURCE_SUFFIXES


def _raw_fragment_edge(edge: dict[str, Any]) -> dict[str, Any]:
    """Recover the raw (extraction-time) edge from a stored fragment edge."""
    if _PROV_DROP in edge:
        return {k: v for k, v in edge.items() if k != _PROV_DROP}
    if _PROV_EXT in edge:
        raw = {k: v for k, v in edge.items() if k not in (_PROV_EXT, _PROV_CONF)}
        raw["target"] = "external::" + str(edge[_PROV_EXT])
        if _PROV_CONF in edge:
            raw["confidence"] = edge[_PROV_CONF]
        return raw
    return edge


def _output_fragment_edge(edge: dict[str, Any]) -> dict[str, Any] | None:
    """Fragment edge → payload edge (strip provenance); None for tombstones."""
    if _PROV_DROP in edge:
        return None
    if _PROV_EXT in edge:
        return {k: v for k, v in edge.items() if k not in (_PROV_EXT, _PROV_CONF)}
    return edge


def _edge_lookup_keys(raw_edge: dict[str, Any]) -> set[str]:
    """Candidate-index keys this raw edge's resolution consults.

    Mirrors the resolver's lookup surface exactly: `bare` (qualified or
    simple), the final segment (the AC-2 fallback), and the Go inner key for
    package-qualified Go receivers. Used to select scope-(b) edges — any edge
    whose keys intersect the symbol delta must re-resolve. Wave 1p9qh (1p9qa):
    `extends`/`implements` supertype edges consult the same `bare` +
    final-segment keys as calls (they resolve through the same machinery).
    The `super.` and `staticorinherited#` markers need NO dedicated lookup
    shape: phase-1 re-resolution passes them through untouched, and their
    real binding happens in the finalize OUTPUT pass, which is recomputed
    fresh from the full merged maps on every build (so supertype/definer/
    claim symbol deltas are picked up without any per-edge invalidation).
    """
    tgt = str(raw_edge.get("target") or "")
    if not tgt.startswith("external::"):
        return set()
    rel = str(raw_edge.get("relation") or "")
    bare = tgt[len("external::"):]
    if not bare:
        return set()
    # Wave 1p9qi (1p9qd): SQL table-reference edges (`writes`, and `reads`
    # emitted from SQL sources) resolve through the call machinery, so they
    # consult the same bare + final-segment keys as calls.
    if rel == GRAPH_WRITES_RELATION or _sql_table_reference_edge(raw_edge):
        keys = {bare}
        if "." in bare:
            keys.add(bare.rsplit(".", 1)[-1])
        return keys
    if rel == "reads":
        return {bare}
    if rel in _INHERITANCE_RELATIONS:
        keys = {bare}
        if "." in bare:
            keys.add(bare.rsplit(".", 1)[-1])
        return keys
    if rel != "calls":
        return set()
    keys = {bare}
    if "." in bare:
        keys.add(bare.rsplit(".", 1)[-1])
        if bare.count(".") == 2:
            src = str(raw_edge.get("source") or "")
            src_file = src.split("::", 1)[0] if "::" in src else src
            if src_file.endswith(".go"):
                keys.add(bare.split(".", 1)[1])
    return keys


_TYPED_RECEIVER_CONFS = ("RECEIVER_RESOLVED", "CONSTRUCTION_RESOLVED")


def _downgrade_unresolved_typed_calls(edge: dict[str, Any]) -> dict[str, Any]:
    """Honesty pass (wave 1p9q8): a typed-receiver METHOD-CALL `calls` edge that
    STAYS `external::` after cross-file resolution must not carry a
    receiver/construction resolution confidence.

    The Python typed-receiver resolver (annotations / constructor assignments,
    wave 1p9q4) emits `external::<Type>.<method>` WITH `RECEIVER_RESOLVED` /
    `CONSTRUCTION_RESOLVED` at extraction time and relies on the finalize
    cross-file rewrite to swap the target onto the real project node (keeping
    that confidence). When the qualified `<Type>.<method>` name never binds a
    project node — the method is absent from the resolved class, or the receiver
    type is an ambiguous cross-file same-name twin — the edge remains
    `external::`, i.e. UNRESOLVED. `RECEIVER_RESOLVED` means "bound to a
    receiver-typed PROJECT node"; an external target is not resolved, so the
    honest label is `EXTRACTED`. No provenance is recorded: the downgraded edge
    IS its own raw form, so a later symbol delta that makes the target
    resolvable re-resolves from `EXTRACTED` and re-promotes on an exact unique
    rebind.

    Scope: only a DOTTED `external::<Type>.<method>` target — the exact shape a
    typed-receiver method call produces. A BARE `external::<Type>` construction
    edge (the constructor call itself; e.g. Go composite-literal / `new(Foo)`
    tagged `CONSTRUCTION_RESOLVED` before a language's cross-file type rewrite is
    wired) is a resolved-TYPE reference, not a dangling method call, and is left
    untouched.

    This ALSO catches Java's `super.`/`staticorinherited#` markers when the
    finalize inheritance pass (`_apply_inheritance_output_passes` /
    `_arbitrate_static_or_inherited`) cannot bind them to a unique project
    supertype definer: both refusal paths re-emit a DOTTED
    `external::super.<Enclosing>.<method>` or `external::<Enclosing>.<method>`
    target while keeping the marker's original `RECEIVER_RESOLVED` confidence,
    so it lands here unchanged and is downgraded the same as an unresolved
    Python typed-receiver call. This is intended, not a gap: `RECEIVER_RESOLVED`
    on an unresolved external super/inherited target was a pre-existing Java
    over-claim (the library-superclass or ambiguous-definer case genuinely
    never resolved to a project node); this pass makes that label honest too.
    """
    if (
        edge.get("relation") == "calls"
        and edge.get("confidence") in _TYPED_RECEIVER_CONFS
    ):
        tgt = str(edge.get("target") or "")
        if tgt.startswith("external::") and "." in tgt[len("external::"):]:
            return {**edge, "confidence": "EXTRACTED"}
    return edge


def _resolve_fragment_edge(raw_edge: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    """Resolve ONE raw edge into its stored fragment form.

    Applies the exact per-edge logic of the former in-place rewrite loop:
    `calls` edges with `external::` targets rewrite-or-stay-external (with the
    wave-1p7dg exact-unique confidence promotion); `reads` edges bind to a
    unique constant or become tombstones. Provenance keys keep the raw edge
    recoverable so a later symbol-delta re-runs resolution (promotion AND
    demotion). All other edges pass through unchanged.

    Wave 1p9q8: the honesty downgrade for a typed-receiver `calls` edge that
    stays `external::` runs LATER, on the FINAL output edge set (after the
    finalize inheritance/package output passes that resolve some `external::`
    calls edges to project nodes) — see `_downgrade_unresolved_typed_calls`
    applied in `finalize()`. It cannot run here: a fragment-stage `external::`
    edge may still resolve to a project node in a later output pass.
    """
    # Degenerate-corpus guard: the former rewrite loop ran only when at least
    # one candidate index was non-empty; replicate so a docs-only corpus keeps
    # its external reads edges exactly as before.
    if not (ctx["simple_name_index"] or ctx["qualified_index"]):
        return raw_edge
    tgt = str(raw_edge.get("target") or "")
    rel = str(raw_edge.get("relation") or "")
    if not tgt.startswith("external::") or rel not in (
        "calls", "reads", GRAPH_WRITES_RELATION, *_INHERITANCE_RELATIONS
    ):
        return raw_edge
    src = str(raw_edge.get("source") or "")
    bare = tgt[len("external::"):]
    # Wave 1p9qi (1p9qd): SQL table references (writes always; reads when the
    # SOURCE is a SQL file) route through the CALL machinery below — exact
    # qualified-name match first, unique bare-name fallback, refusal on
    # ambiguity, with the 1p7dg exact-unique promotion. They must NOT hit the
    # 1p4ls constant-read branch: its unique-CONSTANT-or-DROP contract would
    # tombstone every unresolved table reference (`external::audit_log` is
    # real reference evidence, not a droppable constant read).
    sql_table_ref = rel == GRAPH_WRITES_RELATION or _sql_table_reference_edge(raw_edge)
    # Wave 1p9qh (1p9qa): `super.`/`base.` call markers are owned by the
    # finalize inheritance pass. Never resolved here — the AC-2 final-segment
    # fallback could wrong-bind the marker to an unrelated same-named symbol
    # (or to the subclass's own override, the exact method `super.` skips).
    # The static-or-inherited marker (adversarial fix F1) is likewise owned
    # by the finalize pass — it passes through phase 1 untouched.
    if rel == "calls" and (
        bare.startswith(_SUPER_CALL_PREFIX)
        or bare.startswith(_STATIC_OR_INHERITED_PREFIX)
    ):
        return raw_edge
    if rel == "reads" and not sql_table_ref:
        target = _resolve_external_read_target(
            src,
            bare,
            qualified_index=ctx["qualified_index"],
            node_map=ctx["node_map"],
        )
        if target is None:
            return {**raw_edge, _PROV_DROP: True}
        return {**raw_edge, "target": target, _PROV_EXT: bare}
    conf = str(raw_edge.get("confidence") or "")
    resolved, rewrote_exact = _resolve_external_call_target(
        src,
        bare,
        conf,
        simple_name_index=ctx["simple_name_index"],
        qualified_index=ctx["qualified_index"],
        imports_by_file=ctx["imports_by_file"],
        cs_file_ns=ctx["cs_file_ns"],
        wildcard_imports_by_file=ctx.get("wildcard_imports_by_file"),
        java_pkg_by_file=ctx.get("java_pkg_by_file"),
        rust_module_index=ctx.get("rust_module_index"),
    )
    if not resolved or resolved == src:
        return raw_edge
    # Wave 1p9qh (1p9qa): a supertype must resolve to a TYPE node — a
    # same-named function/constant twin is never a supertype. Refuse (stay
    # external) rather than bind a non-class candidate.
    if rel in _INHERITANCE_RELATIONS and (ctx["node_map"].get(resolved) or {}).get("kind") != "class":
        return raw_edge
    # Wave 1p9qi (1p9qd): a SQL table reference must resolve to a SQL schema
    # object (`sql_kind`-carrying node) — a coincidental same-name host-
    # language class/function is never the referenced table. Refuse (stay
    # external) rather than bind a non-SQL twin.
    if sql_table_ref and "sql_kind" not in (ctx["node_map"].get(resolved) or {}):
        return raw_edge
    # Wave 1p2q3 / 1p7dg: exact-unique cross-file rebinds are high-confidence
    # by construction — promote EXTRACTED->RECEIVER_RESOLVED. Heuristic binds
    # (AC-2 fallback, same-dir, C# namespace) correctly stay EXTRACTED.
    out = {**raw_edge, "target": resolved, _PROV_EXT: bare}
    if conf == "EXTRACTED" and rewrote_exact:
        out["confidence"] = "RECEIVER_RESOLVED"
        out[_PROV_CONF] = conf
    return out


def _class_member_node_id(class_node_id: str, member: str, node_map: dict[str, dict[str, Any]]) -> str | None:
    """Node id of ``<class>.<member>`` when the class defines it, else None.

    Wave 1p9qh (1p9qa). Handles both qualified class nodes
    (``f.java::Outer.Inner`` → ``f.java::Outer.Inner.m``) and collapsed
    dominant-class file nodes (``Foo.java`` → ``Foo.java::Foo.m`` — a merged
    class's members are qualified under its label, 1316l).
    """
    node = node_map.get(class_node_id) or {}
    if "::" in class_node_id:
        cand = f"{class_node_id}.{member}"
    else:
        label = str(node.get("label") or "")
        if not label:
            return None
        cand = f"{class_node_id}::{label}.{member}"
    return cand if cand in node_map else None


def _enclosing_class_node_id(source_id: str, node_map: dict[str, dict[str, Any]]) -> str | None:
    """The class node lexically enclosing a method node id, or None.

    Wave 1p9qh (1p9qa): derived from the source id's OWN qualified name
    (never a name lookup, so a same-named twin class in another file can
    never capture a `super.` call). Falls back to the collapsed dominant-
    class file node when the parent qname matches the merged label.
    """
    if "::" not in source_id:
        return None
    file_part, qname = source_id.split("::", 1)
    if "." not in qname:
        return None
    parent_q = qname.rsplit(".", 1)[0]
    cand = f"{file_part}::{parent_q}"
    if (node_map.get(cand) or {}).get("kind") == "class":
        return cand
    mod = node_map.get(file_part) or {}
    if (
        mod.get("collapsed_pair")
        and mod.get("kind") == "class"
        and str(mod.get("label") or "") == parent_q
    ):
        return file_part
    return None


def _walk_supertype_definers(
    start_classes: list[str],
    method: str,
    super_adj: dict[str, list[tuple[str, str]]],
    node_map: dict[str, dict[str, Any]],
) -> list[tuple[str, list[str]]]:
    """Bounded BFS over PROJECT-RESOLVED supertype edges collecting every
    supertype in the walk that defines ``method``.

    Wave 1p9qh (1p9qa). ``start_classes`` are the depth-1 frontier (the
    receiver's direct supertypes — themselves definer candidates); the walk
    expands over both `extends` and `implements` edges up to
    ``_INHERITANCE_WALK_MAX_DEPTH`` hops. It can never pass through an
    `external::` supertype — the adjacency only contains project-resolved
    targets by construction — and a diamond is visited once (visited set).
    Returns ``[(member_node_id, hop_chain)]`` sorted by definer class id;
    the caller binds ONLY on exactly one definer (never picks an override
    winner). ``hop_chain`` is the class-id path from the first supertype hop
    to the definer inclusive — the bind's audit provenance.
    """
    definers: dict[str, tuple[str, list[str]]] = {}
    visited: set[str] = set(start_classes)
    queue: list[tuple[str, list[str]]] = [(c, [c]) for c in start_classes]
    while queue:
        cls, chain = queue.pop(0)
        member = _class_member_node_id(cls, method, node_map)
        if member is not None:
            definers[cls] = (member, chain)
        if len(chain) >= _INHERITANCE_WALK_MAX_DEPTH:
            continue
        for sup, _rel in super_adj.get(cls, ()):
            if sup not in visited:
                visited.add(sup)
                queue.append((sup, chain + [sup]))
    return [definers[cls] for cls in sorted(definers)]


def _arbitrate_static_or_inherited(
    key: tuple[str, str, str, str],
    edge_map: dict[tuple[str, str, str, str], dict[str, Any]],
    node_map: dict[str, dict[str, Any]],
    super_adj: dict[str, list[tuple[str, str]]],
    resolve_ctx: dict[str, Any],
) -> None:
    """Arbitrate ONE static-or-inherited marker edge, JLS-6.4.1-faithfully.

    Wave 1p9qh adversarial fix (F1). The marker
    ``external::staticorinherited#<Enclosing>.<method>#<claim>`` records a
    bare call that a static-import fact would bind while the enclosing class
    also has a supertype clause. Arbitration order (JLS 6.4.1 — members in
    class scope, INCLUDING INHERITED members, shadow single-static and
    static-on-demand imports):

    1. The enclosing class defines the member itself → bind it (class scope;
       defensive — extraction's same-file precedence normally catches this).
    2. Exactly ONE supertype in the bounded project-resolved walk defines
       the member → bind inherited, with ``via_supertype`` provenance.
    3. MULTIPLE definers in the walk → refuse
       (``external::<Enclosing>.<method>``). Inherited members exist, so the
       static import stays shadowed — "falling back" to it would invert the
       JLS shadow — and picking an override winner is the guess the
       single-definer rule forbids.
    4. NO definer in the walk → the static-import claim stands: resolve
       ``<claim>`` exactly as the phase-1 cross-file pass resolves
       ``external::<claim>`` (unique project bind, else stays qualified
       external — never bare).

    The enclosing class is derived from the SOURCE id (never a name lookup,
    mirroring the `super.` marker) — an unidentifiable or mismatched
    enclosing class refuses like case 3: without an arbitrable class scope
    the static claim is never trusted blindly.

    Every marker the emitter can mint is rewritten (bind inherited / refuse
    / claim stands) — none appears in an output payload. A malformed
    lookalike (wrong separator shape) passes through untouched rather than
    being guessed at; the emitter cannot produce one and no language can
    mint the `#`-separated form from source (pinned by the invariant test).
    """
    src, tgt, _rel, conf = key
    rest = tgt[len("external::") + len(_STATIC_OR_INHERITED_PREFIX):]
    if _STATIC_OR_INHERITED_SEP not in rest:
        return  # unmintable from the emitter; never guess on a malformed marker
    left, claim = rest.rsplit(_STATIC_OR_INHERITED_SEP, 1)
    if "." not in left or not claim:
        return
    recv_simple, method = left.rsplit(".", 1)
    edge = edge_map.pop(key)

    def _emit(target: str, via: list[str] | None = None) -> None:
        new_edge = {k: v for k, v in edge.items() if k != "via_supertype"}
        new_edge["target"] = target
        new_edge["confidence"] = conf
        if via is not None:
            new_edge["via_supertype"] = list(via)
        edge_map.setdefault((src, target, "calls", conf), new_edge)

    refusal = f"external::{recv_simple}.{method}"
    enclosing = _enclosing_class_node_id(src, node_map)
    if (
        enclosing is None
        or str((node_map.get(enclosing) or {}).get("label") or "") != recv_simple
    ):
        _emit(refusal)
        return
    own = _class_member_node_id(enclosing, method, node_map)
    if own is not None:
        _emit(own)
        return
    supers = sorted({t for t, _r in super_adj.get(enclosing, ())})
    definers = (
        _walk_supertype_definers(supers, method, super_adj, node_map)
        if supers
        else []
    )
    if len(definers) == 1:
        member_id, chain = definers[0]
        _emit(member_id, via=chain)
        return
    if len(definers) > 1:
        _emit(refusal)
        return
    # Case 4: no inherited definer in the project-resolved walk — the
    # static-import claim stands, resolved exactly as phase 1 would have.
    resolved, _rewrote = _resolve_external_call_target(
        src,
        claim,
        conf,
        simple_name_index=resolve_ctx["simple_name_index"],
        qualified_index=resolve_ctx["qualified_index"],
        imports_by_file=resolve_ctx.get("imports_by_file") or {},
        cs_file_ns=resolve_ctx.get("cs_file_ns") or {},
        wildcard_imports_by_file=resolve_ctx.get("wildcard_imports_by_file"),
        java_pkg_by_file=resolve_ctx.get("java_pkg_by_file"),
        rust_module_index=resolve_ctx.get("rust_module_index"),
    )
    if resolved and resolved != src:
        _emit(resolved)
    else:
        _emit(f"external::{claim}")


def _apply_inheritance_output_passes(
    edge_map: dict[tuple[str, str, str, str], dict[str, Any]],
    node_map: dict[str, dict[str, Any]],
    simple_name_index: dict[str, list[str]],
    qualified_index: dict[str, list[str]],
    resolve_ctx: dict[str, Any] | None = None,
) -> None:
    """Wave 1p9qh (1p9qa): inheritance-aware OUTPUT passes, in place.

    Runs fresh on the assembled edge map every build — like the analytics
    node flags — so persisted per-file fragments stay pristine and
    incremental == full merge by construction (a deterministic function of
    the merged maps; the differential harness enforces it).

    Pass 1 — C# base-relation kind correction: the extraction-time
    first-base-is-`extends` positional convention is replaced by the TRUE
    kind for PROJECT-RESOLVED bases (target `declared_kind == "interface"` →
    `implements`, else `extends`). `.cs` sources only — Java relations are
    syntax-derived and never flipped — and never for interface declarers
    (interface : I, J is interface inheritance, always `extends`).

    Pass 2 — inherited-method + `super.`/`base.` call binding: a still-
    external `calls` edge `external::<Recv>.<m>` whose receiver type resolves
    to a UNIQUE project class binds to `<Supertype>.<m>` when exactly ONE
    supertype in the bounded walk defines it (multiple definers → refusal —
    never guess an override winner); the `super.` marker binds via the
    enclosing class's single project-resolved `extends` target. Every
    inherited bind carries ``via_supertype`` (the supertype hop chain) —
    council-mandated audit provenance: a wrong supertype edge amplifies into
    many wrong call binds, and the property is what makes that failure mode
    visible in calibration and adversarial review.

    Adversarial fix (F1): pass 2 also arbitrates the ``staticorinherited#``
    deferred markers (`_arbitrate_static_or_inherited` — JLS 6.4.1: inherited
    definer wins over the static-import claim; multi-definer refuses; no
    definer lets the claim stand). ``resolve_ctx`` carries the phase-1
    resolution context for the claim-stands case; when None a minimal
    context is built from the provided indexes.
    """
    if resolve_ctx is None:
        resolve_ctx = {
            "simple_name_index": simple_name_index,
            "qualified_index": qualified_index,
        }
    # --- Pass 1: C# base-relation kind correction (project targets only). ---
    for key in sorted(k for k in edge_map if k[2] in _INHERITANCE_RELATIONS):
        src, tgt, rel, conf = key
        if tgt.startswith("external::"):
            continue  # positional convention stays for unresolved bases (inert: both relations traverse identically)
        src_file = src.split("::", 1)[0]
        if not src_file.endswith(".cs"):
            continue
        if (node_map.get(src) or {}).get("declared_kind") == "interface":
            continue
        true_rel = (
            "implements"
            if (node_map.get(tgt) or {}).get("declared_kind") == "interface"
            else "extends"
        )
        if true_rel == rel:
            continue
        edge = edge_map.pop(key)
        edge_map.setdefault((src, tgt, true_rel, conf), {**edge, "relation": true_rel})

    # --- Project-resolved supertype adjacency (post-correction). ---
    super_adj: dict[str, list[tuple[str, str]]] = {}
    for src, tgt, rel, _conf in edge_map:
        if rel in _INHERITANCE_RELATIONS and not tgt.startswith("external::"):
            super_adj.setdefault(src, []).append((tgt, rel))
    # Adversarial fix (F1): the static-or-inherited markers must ALWAYS be
    # arbitrated (they may never leak into an output payload), even when no
    # project-resolved supertype edge exists anywhere — an empty adjacency
    # simply means the walk finds no definer and the static claim stands.
    _static_marker_head = "external::" + _STATIC_OR_INHERITED_PREFIX
    if not super_adj and not any(
        k[2] == "calls" and k[1].startswith(_static_marker_head) for k in edge_map
    ):
        return
    for lst in super_adj.values():
        lst.sort()

    # --- Pass 2: inherited-method + super-call binding. ---
    for key in sorted(
        k for k in edge_map if k[2] == "calls" and k[1].startswith("external::")
    ):
        src, tgt, _rel, _conf = key
        bare = tgt[len("external::"):]
        if bare.startswith(_STATIC_OR_INHERITED_PREFIX):
            _arbitrate_static_or_inherited(
                key, edge_map, node_map, super_adj, resolve_ctx
            )
            continue
        if bare.startswith(_SUPER_CALL_PREFIX):
            rest = bare[len(_SUPER_CALL_PREFIX):]
            if "." not in rest:
                continue
            recv_simple, method = rest.rsplit(".", 1)
            enclosing = _enclosing_class_node_id(src, node_map)
            if (
                enclosing is None
                or str((node_map.get(enclosing) or {}).get("label") or "") != recv_simple
            ):
                continue  # refuse on any enclosing-class mismatch
            parents = [t for t, r in super_adj.get(enclosing, ()) if r == "extends"]
            if len(parents) != 1:
                continue  # zero or ambiguous project-resolved parents → refuse
            definers = _walk_supertype_definers(parents, method, super_adj, node_map)
        else:
            if "." not in bare:
                continue
            recv, method = bare.rsplit(".", 1)
            if not recv or not method:
                continue
            cands = qualified_index.get(recv, []) if "." in recv else simple_name_index.get(recv, [])
            cands = [c for c in cands if (node_map.get(c) or {}).get("kind") == "class"]
            if len(cands) != 1:
                continue  # receiver type not uniquely a project class → refuse
            recv_cls = cands[0]
            supers = sorted({t for t, _r in super_adj.get(recv_cls, ())})
            if not supers:
                continue
            if _class_member_node_id(recv_cls, method, node_map) is not None:
                # The receiver class defines the method itself; the edge is
                # external only because phase-1 candidate lookup refused
                # (ambiguity). An inherited bind here would be a guess.
                continue
            definers = _walk_supertype_definers(supers, method, super_adj, node_map)
        if len(definers) != 1:
            continue  # zero definers, or the multi-definer refusal
        member_id, chain = definers[0]
        if member_id == src:
            continue
        edge = edge_map.pop(key)
        edge_map.setdefault(
            (src, member_id, "calls", "RECEIVER_RESOLVED"),
            {
                **edge,
                "target": member_id,
                "confidence": "RECEIVER_RESOLVED",
                "via_supertype": list(chain),
            },
        )


class GraphIndexSession:
    """Incremental graph cache for a single index layer."""

    def __init__(
        self,
        *,
        root: Path,
        index_dir: Path,
        layer: str,
        files: list[Path],
        current_file_meta: dict[str, dict[str, Any]],
        walker_version: str,
        chunker_version: str,
        verbose: bool = False,
        state: dict[str, Any] | None = None,
    ) -> None:
        if layer not in GRAPH_FILENAMES:
            raise ValueError(f"Unsupported graph layer: {layer}")
        self.root = root
        self.index_dir = index_dir
        self.layer = layer
        self.files = files
        self.current_file_meta = current_file_meta
        self.verbose = verbose
        self.walker_version = walker_version
        self.chunker_version = chunker_version
        # Wave 1p9q3 (1p9q2): `state_path` is the LEGACY monolithic JSON state
        # (discarded one-time when the store opens); the live state is the
        # per-file SQLite store at `store_path`.
        self.state_path = index_dir / GRAPH_DIRNAME / GRAPH_STATE_FILENAMES[layer]
        self.store_path = index_dir / GRAPH_DIRNAME / GRAPH_STORE_FILENAMES[layer]
        self._store: GraphStateStore | None = None
        self.graph_path = index_dir / GRAPH_DIRNAME / GRAPH_FILENAMES[layer]
        self.pending_code: dict[str, dict[str, Any]] = {}
        self.pending_doc_text: dict[str, str] = {}
        # Lazy-cached `.gitattributes` `linguist-generated=true` patterns (wave 130rj).
        # Populated on first call to record_file() so we only parse the file once
        # per session even when no generated-code classification is required.
        self._gitattrs_patterns: frozenset[str] | None = None
        # Wave 1p2q3 (1p2wd post-ship 1.3.28): optional pre-loaded state.
        # Parent loads state from disk once and shares it with worker sessions
        # to avoid 1,542× redundant JSON reads + parses that serialized on the
        # GIL under thread-mode parallel extraction. A field kernel-sample
        # histogram showed 43% of samples in mutex/condvar waits — classic
        # GIL thrashing where 4 threads serialize on Python work that doesn't
        # release the GIL (state read, JSON parse, dict construction). With
        # state passed in, the worker's __init__ skips _load_state entirely.
        if state is not None:
            self._state = state
        else:
            self._state = self._load_state()
        self._current_paths = {
            _repo_rel(path.relative_to(root)) for path in files
            if path.is_file() and not _is_minified_file(_repo_rel(path.relative_to(root)))
        }
        # Wave 1p2q3 (1p2wd post-ship 1.3.25 / Bug 9): skip `git ls-files` when
        # there are no files to filter. The parallel-extraction workers each
        # construct a fresh `GraphIndexSession` with `files=[]` per task; the
        # resulting `self._current_paths` is also empty, so `set() -= ignored`
        # was a no-op — but the subprocess.run that produced `ignored` still
        # fired on every call. On a 1,542-file workload that's 1,542 git
        # subprocess invocations per build. On macOS spawn-mode workers,
        # `subprocess.Popen.__init__`'s internal `select.poll().poll()` for
        # fork-completion can deadlock when called from inside an already-
        # spawned worker process (field session, stack samples show
        # all 4 workers stuck in this exact poll). The empty-files guard
        # makes the worker path subprocess-free while keeping the
        # parent-thread behavior identical (the parent always has `files`).
        if self._current_paths:
            ignored = _gitignored_paths(root)
            if ignored:
                self._current_paths -= ignored

    def _ensure_store(self) -> GraphStateStore:
        """Open (once) the per-file SQLite state store for this session.

        Wave 1p9q3 (1p9q2). Side effects on first open:
        - One-time legacy discard: a monolithic ``project-graph-state.json``
          is DELETED (decision: discard, not migrate — the version-mismatch
          path already forces a full re-extract on upgrade, so a one-time
          re-extract is the established upgrade cost and migration code would
          be single-use complexity). Idempotent: the file is simply gone on
          subsequent opens.
        - Whole-store version check: any schema/builder/walker/chunker/layer
          mismatch resets the store (rows + merge sidecar), preserving the
          historical ``_load_state`` invalidation semantics.
        """
        if self._store is None:
            if self.state_path.exists():
                try:
                    self.state_path.unlink()
                    print(
                        "build_index: legacy monolithic graph state discarded "
                        f"({self.state_path.name}) — the per-file state store "
                        "supersedes it; a one-time full re-extract follows",
                        file=sys.stderr,
                        flush=True,
                    )
                except OSError:
                    pass
            self._store = GraphStateStore(
                self.store_path,
                layer=self.layer,
                walker_version=self.walker_version,
                chunker_version=self.chunker_version,
            )
            self._store.ensure_current()
        return self._store

    def close_store(self) -> None:
        """Close the state-store connection.

        Hook-spawned builds are short-lived processes, but tests (and the
        in-process auto-rebuild path) construct many sessions — an explicit
        close avoids fd/WAL-handle buildup. A later store access transparently
        reopens.
        """
        if self._store is not None:
            self._store.close()
            self._store = None

    def _load_state(self) -> dict[str, Any]:
        """Load the lightweight session state view from the per-file store.

        Wave 1p9q3 (1p9q2): the returned dict keeps the historical shape
        (version keys + ``files``) but ``files`` entries carry ``source_hash``
        only — artifacts stay in the store and are read per file. Version
        mismatch resets the store inside ``_ensure_store`` so the returned
        ``files`` is empty exactly when a full re-extract must follow
        (`update_graph_index` keys its corpus expansion off that).
        """
        store = self._ensure_store()
        return {
            "schema_version": GRAPH_SCHEMA_VERSION,
            "builder_version": GRAPH_BUILDER_VERSION,
            "layer": self.layer,
            "walker_version": self.walker_version,
            "chunker_version": self.chunker_version,
            "files": {
                rel: {"source_hash": source_hash}
                for rel, source_hash in store.paths_with_hashes().items()
            },
        }

    def _source_location(self, text: str, line: int) -> str:
        if line <= 0:
            return "1:0"
        lines = text.splitlines()
        if line > len(lines):
            line = len(lines)
        col = 0
        if 1 <= line <= len(lines):
            match = re.search(r"\S", lines[line - 1])
            col = match.start() if match else 0
        return f"{line}:{col}"

    # ------------------------------------------------------------------
    # Doc scan exclusion
    # ------------------------------------------------------------------

    def _is_doc_scan_excluded(self, rel_path: str) -> bool:
        rel = _repo_rel(rel_path)
        # Framework seeds are explicitly included even though they start with '.'
        if rel.startswith(".wavefoundry/framework/seeds/"):
            return False
        for prefix in _DOC_SCAN_EXCLUDE_PREFIXES:
            if rel.startswith(prefix):
                return True
        # Exclude paths with any component starting with '.'
        for part in rel.split("/"):
            if part.startswith("."):
                return True
        return False

    # ------------------------------------------------------------------
    # File recording
    # ------------------------------------------------------------------

    def record_file(self, rel_path: str, source_text: str) -> None:
        """Record the current contents of a changed file."""
        rel = _repo_rel(rel_path)
        if _is_minified_file(rel):
            return
        kind = _kind_for_path(rel)
        source_hash = _sha256_text(source_text)
        if kind == "code":
            # Pre-classify the file for generated-code tagging (wave 130rj).
            # Cache gitattributes patterns lazily on first classification call.
            if self._gitattrs_patterns is None:
                self._gitattrs_patterns = _load_gitattributes_generated_paths(self.root)
            source_bytes = source_text.encode("utf-8", errors="replace")
            is_generated = _classify_generated(rel, source_bytes, self._gitattrs_patterns)
            artifact = self._extract_code_artifact(rel, source_text)
            if is_generated:
                # Tag every node from a generated-classified file with `generated: True`
                # so downstream consumers can filter/aggregate without re-classifying.
                artifact["generated"] = True
                for node in artifact.get("nodes", []):
                    if isinstance(node, dict):
                        node["generated"] = True
            self.pending_code[rel] = {
                "source_hash": source_hash,
                "artifact": artifact,
            }
        elif not self._is_doc_scan_excluded(rel):
            self.pending_doc_text[rel] = source_text

    # ------------------------------------------------------------------
    # Code extraction
    # ------------------------------------------------------------------

    def _extract_python_artifact(self, rel_path: str, source_text: str) -> dict[str, Any]:
        try:
            tree = ast.parse(source_text, filename=rel_path)
        except SyntaxError:
            return {
                "kind": "code",
                "path": rel_path,
                "source_hash": _sha256_text(source_text),
                "nodes": [_node(rel_path, _path_term(rel_path), "module", rel_path, "1:0", layer=self.layer)],
                "edges": [],
                "defined_symbols": [],
                "simple_names": {},
                "mentioned_symbols": [],
            }

        module_id = rel_path
        module_node = _node(module_id, _path_term(rel_path), "module", rel_path, "1:0", layer=self.layer)
        nodes: list[dict[str, Any]] = [module_node]
        edges: list[dict[str, Any]] = []
        defined_symbols: list[str] = []
        simple_names: dict[str, list[str]] = {}
        simple_name_lookup: dict[str, list[str]] = {}
        import_aliases: dict[str, str] = {}

        # Wave 131bt (1319o): Python single-dominant-class merge.
        # When a file `foo_bar.py` (or `Foo.py`) has exactly one top-level
        # `class_definition` whose name matches the basename (literal or
        # snake-to-PascalCase), merge the file node and the class node into
        # one node at the file id. Module-level functions/constants don't
        # block the merge.
        _py_basename_raw = ""
        if rel_path.endswith(".py"):
            _py_basename_raw = rel_path.rsplit("/", 1)[-1][:-3]
        _py_basename_candidates: frozenset[str] = (
            frozenset({
                _py_basename_raw,
                "".join(p[:1].upper() + p[1:] for p in _py_basename_raw.split("_") if p),
            })
            if _py_basename_raw
            else frozenset()
        )
        _py_top_level_class_count = sum(
            1 for s in tree.body if isinstance(s, ast.ClassDef)
        )

        def add_symbol(qname: str, kind: str, lineno: int, label: str | None = None, parent: str | None = None, value: str | None = None) -> str:
            # Wave 131bt (1319o): merge top-level class into module node when
            # the dominance gate passes (exactly one top-level class) and the
            # class name matches the file basename (literal or snake-to-Pascal).
            if (
                kind == "class"
                and parent is None
                and _py_top_level_class_count == 1
                and qname in _py_basename_candidates
            ):
                module_node["label"] = qname
                module_node["kind"] = "class"
                module_node["collapsed_pair"] = True
                simple_names.setdefault(qname, []).append(module_id)
                if module_id not in defined_symbols:
                    defined_symbols.append(module_id)
                return module_id
            node_id = f"{rel_path}::{qname}"
            new_node = _node(
                node_id,
                label or qname.split(".")[-1],
                kind,
                rel_path,
                self._source_location(source_text, lineno),
                layer=self.layer,
            )
            if value is not None:  # Wave 1p4ls: constant nodes carry a simple-literal value
                new_node["value"] = value
            nodes.append(new_node)
            edges.append(_edge(module_id, node_id, "defines", confidence="EXTRACTED"))
            defined_symbols.append(node_id)
            base_name = qname.split(".")[-1]
            simple_names.setdefault(base_name, []).append(node_id)
            if parent:
                simple_name_lookup.setdefault(parent, []).append(node_id)
            return node_id

        def emit_py_constant(stmt: "ast.Assign | ast.AnnAssign", parent_qname: str | None) -> None:
            # Wave 1p4ls: a module-/class-level Python constant → a graph node (kind="constant").
            # Reuses the chunk lane's detection predicates (Req-7 — one detector): UPPER_SNAKE name,
            # with typing.Final as a casing-independent override. Function-local assigns never reach
            # here (scope_kind gate); Enum members are skipped (their class body is scope_kind="enum").
            _ck = _chunker_module()
            value_node = stmt.value
            if isinstance(stmt, ast.AnnAssign):
                targets = [stmt.target]
                final_override = _ck._is_final_annotation(stmt.annotation)
            else:
                targets = list(stmt.targets)
                final_override = False
            # value only for a single simple-literal RHS; chained/unpacked targets share or drop it
            literal = _py_const_literal_value(value_node)
            names: list[str] = []
            for tgt in targets:
                if isinstance(tgt, ast.Name):
                    names.append(tgt.id)
                elif isinstance(tgt, (ast.Tuple, ast.List)):
                    names.extend(e.id for e in tgt.elts if isinstance(e, ast.Name))
            tuple_unpack = any(isinstance(t, (ast.Tuple, ast.List)) for t in targets)
            for name in names:
                if not (final_override or _ck._is_const_name(name)):
                    continue
                qname = f"{parent_qname}.{name}" if parent_qname else name
                add_symbol(qname, GRAPH_CONST_KIND, stmt.lineno,
                           value=None if tuple_unpack else literal)

        def collect_imports_and_defs(body: list[ast.stmt], parent_qname: str | None = None, scope_kind: str = "module") -> None:
            for stmt in body:
                if isinstance(stmt, ast.Import):
                    for alias in stmt.names:
                        alias_name = alias.asname or alias.name.split(".")[-1]
                        import_aliases[alias_name] = alias.name
                        target_id = f"external::{alias.name}"
                        nodes.append(
                            _node(target_id, alias.name, "module", "", "1:0", layer=self.layer)
                        )
                        edges.append(_edge(module_id, target_id, "imports", confidence="EXTRACTED"))
                elif isinstance(stmt, ast.ImportFrom):
                    mod = stmt.module or ""
                    for alias in stmt.names:
                        alias_name = alias.asname or alias.name
                        import_aliases[alias_name] = f"{mod}.{alias.name}" if mod else alias.name
                        target_label = f"{mod}.{alias.name}" if mod else alias.name
                        target_id = f"external::{target_label}"
                        nodes.append(
                            _node(target_id, target_label, "module", "", "1:0", layer=self.layer)
                        )
                        edges.append(_edge(module_id, target_id, "imports", confidence="EXTRACTED"))
                elif isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    qname = f"{parent_qname}.{stmt.name}" if parent_qname else stmt.name
                    add_symbol(qname, "function", stmt.lineno)
                    if stmt.body:
                        collect_imports_and_defs(stmt.body, qname, "function")
                elif isinstance(stmt, ast.ClassDef):
                    qname = f"{parent_qname}.{stmt.name}" if parent_qname else stmt.name
                    add_symbol(qname, "class", stmt.lineno)
                    # Wave 1p4ls: an Enum class body's members are NOT constants (kept as the class
                    # node), mirroring the chunk lane — recurse with scope_kind="enum" to skip them.
                    body_scope = "enum" if _chunker_module()._is_enum_class(stmt) else "class"
                    collect_imports_and_defs(stmt.body, qname, body_scope)
                elif scope_kind in ("module", "class") and isinstance(stmt, (ast.Assign, ast.AnnAssign)):
                    # Wave 1p4ls: module/class-level constant → graph node. Function-local assigns
                    # (scope_kind="function") and Enum members (scope_kind="enum") are excluded.
                    emit_py_constant(stmt, parent_qname)

        collect_imports_and_defs(tree.body)

        # Build a lookup for the exact target node IDs available in this file.
        symbol_lookup = {symbol_id.split("::", 1)[-1]: symbol_id for symbol_id in defined_symbols}
        for name, items in simple_names.items():
            if len(items) == 1:
                symbol_lookup.setdefault(name, items[0])

        # Wave 1p4ls: ids of THIS file's constant nodes — gates reads-edge emission so a `reads`
        # edge only ever binds a constant target (never a coincidental same-name function/class).
        const_ids = {n["id"] for n in nodes if n.get("kind") == GRAPH_CONST_KIND}

        # Wave 1p9q4: simple names of THIS file's class nodes — the same-file half
        # of the constructor-assignment gate (`x = Foo()` types `x` as `Foo` only
        # when `Foo` is a same-file class or an imported name). Collapsed
        # dominant-class file nodes carry the class name as `label`, so their
        # `label` participates too.
        local_class_names = {n["label"] for n in nodes if n.get("kind") == "class" and n.get("label")}

        # Wave 131bt (1319q) + 1p9q4: Python receiver-type resolution. Two
        # deterministic, AST-local, unique-match-or-drop signals feed a
        # receiver-type table:
        #   (1) ANNOTATION (RECEIVER_RESOLVED) — parameter/local/attribute type
        #       annotations (`def m(self, foo: Foo)`, `foo: Foo`, `self.x: Foo`,
        #       class-body `x: Foo`). Optional[T]/`T | None` and string forward
        #       refs unwrap to T; any genuine multi-type union or other generic
        #       is unresolvable (no guess).
        #   (2) CONSTRUCTION (CONSTRUCTION_RESOLVED) — direct constructor
        #       assignment (`foo = Foo()`, `self.x = Foo()`, module-level
        #       `foo = Foo()`) where `Foo` is a same-file class or imported name.
        # A receiver call `recv.method()` binds to `Type.method` only when that
        # method exists on the resolved class (same-file `symbol_lookup`, else the
        # existing unique-candidate cross-file pass). Conflicting resolved types
        # for one name demote it (no bind). No inheritance/MRO walk.
        def _py_extract_simple_type(annotation: ast.AST | None) -> str | None:
            if annotation is None:
                return None
            if isinstance(annotation, ast.Name):
                return annotation.id if annotation.id != "None" else None
            if isinstance(annotation, ast.Constant) and isinstance(annotation.value, str):
                # String / forward-ref annotation (`x: "Foo"`, `x: "Optional[Foo]"`).
                # Parse the string as an expression and recurse; a malformed or
                # unresolvable string yields None (no guess).
                text = annotation.value.strip()
                if not text:
                    return None
                try:
                    parsed = ast.parse(text, mode="eval")
                except SyntaxError:
                    return None
                return _py_extract_simple_type(parsed.body)
            if isinstance(annotation, ast.Attribute):
                # foo.bar.Foo — last segment (a dotted named type, not a union/generic).
                return annotation.attr
            if isinstance(annotation, ast.Subscript):
                # ONLY Optional[T] / Union[...] unwrap — and only to a SINGLE
                # non-None member. Every other generic (List[Foo], Dict[str, Foo],
                # Callable[...], ...) is treated as unresolvable — no guess at the
                # element type (Requirement 1 / AC-3).
                if isinstance(annotation.value, ast.Name) and annotation.value.id in ("Optional", "Union"):
                    slice_node = annotation.slice
                    if isinstance(slice_node, ast.Tuple):
                        inners = [_py_extract_simple_type(elt) for elt in slice_node.elts]
                        non_none = [t for t in inners if t and t != "None"]
                        # Optional[T] / Union[T, None] → T; a genuine Union[A, B]
                        # (multiple non-None members) is ambiguous → no bind.
                        return non_none[0] if len(non_none) == 1 else None
                    inner = _py_extract_simple_type(slice_node)
                    return inner if inner and inner != "None" else None
                return None
            if isinstance(annotation, ast.BinOp) and isinstance(annotation.op, ast.BitOr):
                # PEP 604 `A | B | None`. Unwrap ONLY when exactly one non-None
                # member survives across the whole flattened union; a multi-type
                # union is ambiguous → no bind. A member we cannot resolve to a
                # simple type also poisons the union (unresolvable → no guess).
                parts: list[str] = []
                stack: list[ast.AST] = [annotation.left, annotation.right]
                resolvable = True
                while stack:
                    node = stack.pop()
                    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
                        stack.extend([node.left, node.right])
                        continue
                    if isinstance(node, ast.Constant) and node.value is None:
                        continue  # the `None` half of an optional
                    t = _py_extract_simple_type(node)
                    if t is None:
                        resolvable = False
                        continue
                    if t != "None":
                        parts.append(t)
                if not resolvable:
                    return None
                return parts[0] if len(parts) == 1 else None
            return None

        def _py_construction_type(value: ast.AST | None) -> str | None:
            # Wave 1p9q4: the class name a `= Foo()` constructor assignment types
            # its target as, else None. Faithful gate: `Foo` must be a bare Name
            # that is a same-file class OR an imported name (dotted / attribute
            # constructors are out of scope — the doc's signal is direct
            # `ClassName(...)`). Non-constructor calls (`helper()`) whose callee is
            # neither a same-file class nor an import return None. Imported-name
            # over-permissiveness is self-bounding: `Foo.method` only survives when
            # a UNIQUE project class actually defines `method` (else it stays
            # external and is dropped), so a mis-classified factory never binds.
            if not (isinstance(value, ast.Call) and isinstance(value.func, ast.Name)):
                return None
            name = value.func.id
            if name in local_class_names or name in import_aliases:
                return name
            return None

        def _py_finalize_types(acc: dict[str, list[tuple[str, str]]]) -> dict[str, tuple[str, str]]:
            # Wave 1p9q4: collapse per-name (type, signal) evidence into a single
            # (type, confidence) binding, demoting on conflict. `signal` is "ann"
            # (annotation) or "ctor" (construction). Conflicting RESOLVED types for
            # one name → drop (no bind). When exactly one type survives, annotation
            # evidence (if any) sets RECEIVER_RESOLVED; construction-only sets
            # CONSTRUCTION_RESOLVED.
            out: dict[str, tuple[str, str]] = {}
            for name, entries in acc.items():
                distinct = {t for t, _sig in entries}
                if len(distinct) != 1:
                    continue  # conflicting evidence → unresolvable
                only_type = next(iter(distinct))
                conf = "RECEIVER_RESOLVED" if any(sig == "ann" for _t, sig in entries) else "CONSTRUCTION_RESOLVED"
                out[name] = (only_type, conf)
            return out

        def _py_is_self_attr_target(target: ast.AST) -> bool:
            return (
                isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Name)
                and target.value.id in ("self", "cls")
            )

        # Wave 1p47e (1p470): lazy-loader return-type inference. The wavefoundry
        # sibling-script loader idiom `def _load_X(): return _load_script("mod")`
        # (and direct `v = _load_script("mod")`) returns a *module* object. Without
        # tracking it, `v.Class.method()` / `v.func()` emitted no call edge at all
        # because `v` had no known type — the dominant self-host blast-radius hole
        # (`GraphQueryIndex.from_root` called from 14 sites, 0 incoming edges).
        # `loader_modules` maps a file-local wrapper-function name → module name.
        loader_modules: dict[str, str] = {}
        for _ldr_stmt in tree.body:
            if isinstance(_ldr_stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                _eff = [
                    s for s in _ldr_stmt.body
                    if not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant))
                ]
                if len(_eff) == 1 and isinstance(_eff[0], ast.Return):
                    _ret = _eff[0].value
                    if (
                        isinstance(_ret, ast.Call)
                        and isinstance(_ret.func, ast.Name)
                        and _ret.func.id == "_load_script"
                        and _ret.args
                        and isinstance(_ret.args[0], ast.Constant)
                        and isinstance(_ret.args[0].value, str)
                    ):
                        loader_modules[_ldr_stmt.name] = _ret.args[0].value

        def _py_loader_module(call_node: ast.AST) -> str | None:
            """Module name a sibling-loader call returns, else None (wave 1p470).

            Recognizes `_load_script("mod")` (direct) and `_load_wrapper()` where
            the wrapper's body is `return _load_script("mod")`.
            """
            if isinstance(call_node, ast.Call) and isinstance(call_node.func, ast.Name):
                fn = call_node.func.id
                if (
                    fn == "_load_script"
                    and call_node.args
                    and isinstance(call_node.args[0], ast.Constant)
                    and isinstance(call_node.args[0].value, str)
                ):
                    return call_node.args[0].value
                if fn in loader_modules:
                    return loader_modules[fn]
            return None

        def _py_build_local_types(node: ast.AST, scope_class: str | None) -> dict[str, tuple[str, str]]:
            """Build name → (type, confidence) mapping for a function body.

            Wave 1p9q4: two signals — annotations (params + local `AnnAssign`;
            RECEIVER_RESOLVED) and constructor assignments (local `x = Foo()`;
            CONSTRUCTION_RESOLVED). One-level scope (does not descend into nested
            functions/classes). Conflicting resolved types for one name demote it.
            """
            acc: dict[str, list[tuple[str, str]]] = {}

            def _record(name: str, t: str | None, signal: str) -> None:
                if t:
                    acc.setdefault(name, []).append((t, signal))

            # If this is a function, capture typed parameters (annotation signal).
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                args = node.args
                all_args = list(args.posonlyargs) + list(args.args) + list(args.kwonlyargs)
                if args.vararg:
                    all_args.append(args.vararg)
                if args.kwarg:
                    all_args.append(args.kwarg)
                for arg in all_args:
                    _record(arg.arg, _py_extract_simple_type(getattr(arg, "annotation", None)), "ann")
            # Scan body at this scope level (don't descend into nested
            # functions/classes — they have their own scope).
            body = getattr(node, "body", []) or []
            stack = list(body)
            while stack:
                stmt = stack.pop()
                if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    continue
                if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                    _record(stmt.target.id, _py_extract_simple_type(stmt.annotation), "ann")
                elif (
                    isinstance(stmt, ast.Assign)
                    and len(stmt.targets) == 1
                    and isinstance(stmt.targets[0], ast.Name)
                ):
                    _record(stmt.targets[0].id, _py_construction_type(stmt.value), "ctor")
                # Descend into compound statements (if/for/while/try/with).
                for field, value in ast.iter_fields(stmt):
                    if isinstance(value, list):
                        stack.extend(v for v in value if isinstance(v, ast.stmt))
                    elif isinstance(value, ast.stmt):
                        stack.append(value)
            return _py_finalize_types(acc)

        def _py_build_class_attr_types(classdef: ast.ClassDef) -> dict[str, tuple[str, str]]:
            """Wave 1p9q4: attribute name → (type, confidence) for a class.

            Aggregates receiver-type evidence for `self.<attr>` across the whole
            class body (all methods): annotated attributes (`self.x: Foo`,
            class-body `x: Foo`; RECEIVER_RESOLVED) and constructor assignments
            (`self.x = Foo()`, class-body `x = Foo()`; CONSTRUCTION_RESOLVED).
            Conflicting resolved types for one attribute demote it. Enables
            `self.x.method()` resolution to `Foo.method`.
            """
            acc: dict[str, list[tuple[str, str]]] = {}

            def _record(name: str, t: str | None, signal: str) -> None:
                if t:
                    acc.setdefault(name, []).append((t, signal))

            def _scan_method_body(method: ast.AST) -> None:
                substack = list(getattr(method, "body", []) or [])
                while substack:
                    s = substack.pop()
                    if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        continue
                    if isinstance(s, ast.AnnAssign) and _py_is_self_attr_target(s.target):
                        _record(s.target.attr, _py_extract_simple_type(s.annotation), "ann")
                    elif (
                        isinstance(s, ast.Assign)
                        and len(s.targets) == 1
                        and _py_is_self_attr_target(s.targets[0])
                    ):
                        _record(s.targets[0].attr, _py_construction_type(s.value), "ctor")
                    for _field, value in ast.iter_fields(s):
                        if isinstance(value, list):
                            substack.extend(v for v in value if isinstance(v, ast.stmt))
                        elif isinstance(value, ast.stmt):
                            substack.append(value)

            for stmt in classdef.body:
                if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                    _record(stmt.target.id, _py_extract_simple_type(stmt.annotation), "ann")
                elif (
                    isinstance(stmt, ast.Assign)
                    and len(stmt.targets) == 1
                    and isinstance(stmt.targets[0], ast.Name)
                ):
                    _record(stmt.targets[0].id, _py_construction_type(stmt.value), "ctor")
                elif isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    _scan_method_body(stmt)
            return _py_finalize_types(acc)

        def _py_build_module_types() -> dict[str, tuple[str, str]]:
            """Wave 1p9q4: module-level name → (type, confidence).

            Top-level `name: Foo` annotations and `name = Foo()` constructor
            assignments — the module-global receiver-type table. Shadow-guarded at
            resolution time: a function-local binding of the same name suppresses
            the module type (never resolve a shadowed global).
            """
            acc: dict[str, list[tuple[str, str]]] = {}

            def _record(name: str, t: str | None, signal: str) -> None:
                if t:
                    acc.setdefault(name, []).append((t, signal))

            for stmt in tree.body:
                if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                    _record(stmt.target.id, _py_extract_simple_type(stmt.annotation), "ann")
                elif (
                    isinstance(stmt, ast.Assign)
                    and len(stmt.targets) == 1
                    and isinstance(stmt.targets[0], ast.Name)
                ):
                    _record(stmt.targets[0].id, _py_construction_type(stmt.value), "ctor")
            return _py_finalize_types(acc)

        py_module_types = _py_build_module_types()

        def _py_build_module_vars(node: ast.AST) -> dict[str, str]:
            """Map local var → module name for sibling-loader assignments (1p470).

            Tracks `v = _load_script("mod")` and `v = _load_wrapper()` so
            `v.Class.method()` / `v.func()` resolve to the loaded module's
            symbols. One-level scope, mirrors `_py_build_local_types`.
            """
            mvars: dict[str, str] = {}
            body = getattr(node, "body", []) or []
            stack = list(body)
            while stack:
                stmt = stack.pop()
                if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    continue
                if (
                    isinstance(stmt, ast.Assign)
                    and len(stmt.targets) == 1
                    and isinstance(stmt.targets[0], ast.Name)
                ):
                    mod = _py_loader_module(stmt.value)
                    if mod:
                        mvars[stmt.targets[0].id] = mod
                for _field, value in ast.iter_fields(stmt):
                    if isinstance(value, list):
                        stack.extend(v for v in value if isinstance(v, ast.stmt))
                    elif isinstance(value, ast.stmt):
                        stack.append(value)
            return mvars

        class CallCollector(ast.NodeVisitor):
            def __init__(self, current_symbol: str, scope_class: str | None = None, local_types: dict[str, tuple[str, str]] | None = None, module_vars: dict[str, str] | None = None, local_names: set[str] | None = None, attr_types: dict[str, tuple[str, str]] | None = None, module_types: dict[str, tuple[str, str]] | None = None) -> None:
                self.current_symbol = current_symbol
                self.scope_class = scope_class
                # Wave 1p9q4: name/attr → (type, confidence). local_types and
                # attr_types carry per-name confidence (RECEIVER_RESOLVED for an
                # annotation, CONSTRUCTION_RESOLVED for a constructor assignment).
                self.local_types: dict[str, tuple[str, str]] = local_types or {}
                self.attr_types: dict[str, tuple[str, str]] = attr_types or {}
                self.module_types: dict[str, tuple[str, str]] = module_types or {}
                self.module_vars: dict[str, str] = module_vars or {}
                # Wave 1p4ls: names bound locally in this function — a read of one is the local, not
                # a same-name constant (shadowing guard), so it never emits a reads edge.
                self.local_names: set[str] = local_names or set()
                # Wave 131bt (1319q) + 1p9q4: tuples of (source, target,
                # explicit_confidence_or_None). None → the emit loop derives the
                # confidence from the target (same-file bound → RECEIVER_RESOLVED,
                # else EXTRACTED); a string is the resolver-determined level.
                self.calls: list[tuple[str, str, str | None]] = []
                # Wave 1p4ls: (source, constant_target) reads of a same-file constant.
                self.reads: list[tuple[str, str]] = []
                # Wave 1p7dh: (source, literal_key) config-key read candidates from
                # `.get("KEY")` getters and `cfg["KEY"]` subscripts — resolved to
                # config-key nodes in finalize (self-bounding: only a literal that
                # matches a config-key node becomes a `reads_config` edge).
                self.config_reads: list[tuple[str, str]] = []

            def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:  # noqa: N802
                return None

            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> Any:  # noqa: N802
                return None

            def visit_ClassDef(self, node: ast.ClassDef) -> Any:  # noqa: N802
                return None

            def visit_Call(self, node: ast.Call) -> Any:  # noqa: N802
                target, conf = self._resolve_call(node.func)
                if target:
                    self.calls.append((self.current_symbol, target, conf))
                # Wave 1p7dh: a string-literal first arg to a `.get("KEY")` getter
                # is a config-key read candidate (bounded later by node match).
                if (
                    isinstance(node.func, ast.Attribute)
                    and node.func.attr in _CONFIG_GETTER_ATTRS
                    and node.args
                    and isinstance(node.args[0], ast.Constant)
                    and isinstance(node.args[0].value, str)
                    and node.args[0].value
                ):
                    self.config_reads.append((self.current_symbol, node.args[0].value))
                self.generic_visit(node)

            def visit_Subscript(self, node: ast.Subscript) -> Any:  # noqa: N802
                # Wave 1p7dh: `cfg["KEY"]` literal subscript read → config-key candidate.
                if isinstance(node.ctx, ast.Load) and isinstance(node.slice, ast.Constant) \
                        and isinstance(node.slice.value, str) and node.slice.value:
                    self.config_reads.append((self.current_symbol, node.slice.value))
                self.generic_visit(node)

            def visit_Name(self, node: ast.Name) -> Any:  # noqa: N802
                # Wave 1p4ls: a bare-name READ that resolves to a same-file constant → reads edge.
                if isinstance(node.ctx, ast.Load):
                    self._maybe_read(node.id)
                return None

            def visit_Attribute(self, node: ast.Attribute) -> Any:  # noqa: N802
                # Wave 1p4ls: `Owner.CONST` / `self.CONST` reads of a class constant.
                if isinstance(node.ctx, ast.Load):
                    base = node.value
                    if isinstance(base, ast.Name):
                        if base.id in ("self", "cls") and self.scope_class:
                            self._maybe_read(f"{self.scope_class}.{node.attr}", qualified=True)
                        else:
                            self._maybe_read(f"{base.id}.{node.attr}", qualified=True)
                self.generic_visit(node)

            def _maybe_read(self, name: str, qualified: bool = False) -> None:
                # Faithful: bind ONLY to a same-file constant node, never a local shadow, never a
                # coincidental same-name function/class (symbol_lookup uniqueness + const_ids kind gate).
                if not qualified and name in self.local_names:
                    return
                target = symbol_lookup.get(name)
                if target is None and self.scope_class and not qualified:
                    target = symbol_lookup.get(f"{self.scope_class}.{name}")
                if target is not None and target in const_ids and target != self.current_symbol:
                    self.reads.append((self.current_symbol, target))
                elif target is None and not qualified and name in import_aliases:
                    # Wave 1p4ls: cross-module imported-constant candidate — emit an external::
                    # reads edge; finalize() resolves it to a UNIQUE constant (kind-checked) or
                    # drops it (most imports are functions/classes → dropped; never wrong-bound).
                    self.reads.append((self.current_symbol, f"external::{import_aliases[name]}"))

            def _resolve_call(self, func: ast.AST) -> tuple[str | None, str | None]:
                # Returns (target, explicit_confidence_or_None). None confidence
                # defers to the emit loop (same-file bound → RECEIVER_RESOLVED,
                # else EXTRACTED). A receiver-typed bind returns its own level:
                # RECEIVER_RESOLVED (annotation) or CONSTRUCTION_RESOLVED (ctor).
                if isinstance(func, ast.Name):
                    name = func.id
                    if name in import_aliases:
                        target_label = import_aliases[name]
                        return f"external::{target_label}", None
                    if name in symbol_lookup:
                        return symbol_lookup[name], None
                    if self.scope_class:
                        candidate = f"{self.scope_class}.{name}"
                        if candidate in symbol_lookup:
                            return symbol_lookup[candidate], None
                    return None, None
                if isinstance(func, ast.Attribute):
                    attr = func.attr
                    value = func.value
                    if isinstance(value, ast.Name):
                        root = value.id
                        if root in ("self", "cls") and self.scope_class:
                            candidate = f"{self.scope_class}.{attr}"
                            if candidate in symbol_lookup:
                                return symbol_lookup[candidate], None
                        # Wave 131bt (1319q) + 1p9q4: receiver-type via the local
                        # type table (annotation → RECEIVER_RESOLVED, constructor
                        # assignment → CONSTRUCTION_RESOLVED — the level travels
                        # with the type).
                        if root in self.local_types:
                            receiver_type, conf = self.local_types[root]
                            qualified = f"{receiver_type}.{attr}"
                            if qualified in symbol_lookup:
                                return symbol_lookup[qualified], conf
                            return f"external::{receiver_type}.{attr}", conf
                        # Wave 1p470: sibling-loader module var, e.g.
                        # `gq = _load_graph_query(); gq.some_module_func()`.
                        if root in self.module_vars:
                            return f"external::{self.module_vars[root]}.{attr}", "RECEIVER_RESOLVED"
                        if root in import_aliases:
                            return f"external::{import_aliases[root]}.{attr}", None
                        if root in symbol_lookup:
                            candidate = f"{root}.{attr}"
                            if candidate in symbol_lookup:
                                return symbol_lookup[candidate], None
                        # Wave 1p9q4: module-level typed global (shadow-guarded — a
                        # function-local binding of the same name wins and is
                        # handled above / left unresolved).
                        if root in self.module_types and root not in self.local_names:
                            receiver_type, conf = self.module_types[root]
                            qualified = f"{receiver_type}.{attr}"
                            if qualified in symbol_lookup:
                                return symbol_lookup[qualified], conf
                            return f"external::{receiver_type}.{attr}", conf
                    # Wave 1p470: inline sibling-loader call, e.g.
                    # `_load_graph_query().load_graph()`.
                    if isinstance(value, ast.Call):
                        mod = _py_loader_module(value)
                        if mod:
                            return f"external::{mod}.{attr}", "RECEIVER_RESOLVED"
                    if isinstance(value, ast.Attribute) and isinstance(value.value, ast.Name):
                        root = value.value.id
                        # Wave 1p9q4: self-attribute receiver typing —
                        # `self.store.put()` where `self.store` has an annotation
                        # or construction type. The confidence level travels with
                        # the attribute type.
                        if root in ("self", "cls") and value.attr in self.attr_types:
                            receiver_type, conf = self.attr_types[value.attr]
                            qualified = f"{receiver_type}.{attr}"
                            if qualified in symbol_lookup:
                                return symbol_lookup[qualified], conf
                            return f"external::{receiver_type}.{attr}", conf
                        # Wave 1p470: `gq.GraphQueryIndex.from_root()` where gq is a
                        # sibling-loader module var → graph_query.GraphQueryIndex.from_root.
                        if root in self.module_vars:
                            return f"external::{self.module_vars[root]}.{value.attr}.{attr}", "RECEIVER_RESOLVED"
                        if root in import_aliases:
                            return f"external::{import_aliases[root]}.{value.attr}.{attr}", None
                    # Wave 1p470: inline loader 3-level, e.g.
                    # `_load_graph_query().GraphQueryIndex.from_root()`.
                    if isinstance(value, ast.Attribute) and isinstance(value.value, ast.Call):
                        mod = _py_loader_module(value.value)
                        if mod:
                            return f"external::{mod}.{value.attr}.{attr}", "RECEIVER_RESOLVED"
                    return None, None
                return None, None

        def collect_calls(body: list[ast.stmt], current_symbol: str, scope_class: str | None = None, owner_node: ast.AST | None = None, attr_types: dict[str, tuple[str, str]] | None = None) -> None:
            # Wave 131bt (1319q) + 1p9q4: build the local type table for
            # receiver-type resolution when an owner function/method is provided;
            # `attr_types` (the enclosing class's `self.<attr>` type table) is
            # threaded in by the caller.
            local_types: dict[str, tuple[str, str]] = {}
            module_vars: dict[str, str] = {}
            local_names: set[str] = set()
            if owner_node is not None:
                local_types = _py_build_local_types(owner_node, scope_class)
                module_vars = _py_build_module_vars(owner_node)
                local_names = _py_local_names(owner_node)
            collector = CallCollector(current_symbol, scope_class=scope_class, local_types=local_types, module_vars=module_vars, local_names=local_names, attr_types=attr_types, module_types=py_module_types)
            for stmt in body:
                collector.visit(stmt)
                if isinstance(stmt, ast.ClassDef):
                    class_qname = f"{current_symbol.split('::', 1)[-1]}.{stmt.name}" if current_symbol else stmt.name
                    child_attr_types = _py_build_class_attr_types(stmt)
                    for child in stmt.body:
                        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            child_symbol = f"{rel_path}::{class_qname}.{child.name}"
                            collect_calls(child.body, child_symbol, scope_class=class_qname, owner_node=child, attr_types=child_attr_types)
                elif isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    func_qname = f"{current_symbol.split('::', 1)[-1]}.{stmt.name}" if current_symbol else stmt.name
                    # A nested function inside a method still sees the enclosing
                    # class's `self` — propagate the current attr_types.
                    collect_calls(stmt.body, f"{rel_path}::{func_qname}", scope_class=scope_class, owner_node=stmt, attr_types=attr_types)
            for src, target, conf in collector.calls:
                # Wave 1p7dg / 1p9q4: derive the edge confidence. An explicit level
                # from `_resolve_call` (RECEIVER_RESOLVED for an annotation-typed
                # receiver, CONSTRUCTION_RESOLVED for a constructor-assignment
                # receiver) is trusted as-is. When `_resolve_call` returned None the
                # bind is a same-file `symbol_lookup` match BY CONSTRUCTION —
                # `symbol_lookup` holds this file's per-file-unique `defined_symbols`
                # plus `simple_names` entries added only at `len==1`. Those four
                # paths (enclosing-class method via `self`/`cls`, same-file bare def,
                # enclosing-class bare call, qualified `Owner.method` on a same-file
                # symbol) are exact-by-name, so a non-`external::` target promotes
                # EXTRACTED->RECEIVER_RESOLVED. A guessed/unresolved receiver returns
                # `external::`/None and correctly stays EXTRACTED.
                #
                # NOTE (wave 1p9q8): a typed-receiver CROSS-FILE bind emits
                # `external::<Type>.<attr>` WITH its resolution confidence here and
                # relies on the finalize cross-file rewrite to swap the target onto
                # the real project node (preserving the confidence). So the honesty
                # correction — an edge that STAYS `external::` because it never
                # rewrites (method absent from the class; ambiguous same-name twin)
                # must not keep RECEIVER_RESOLVED/CONSTRUCTION_RESOLVED — cannot be
                # applied at THIS emit site (we do not yet know whether the external
                # target will resolve). It is applied in the finalize pass
                # (`_downgrade_unresolved_typed_calls`), where "did it actually bind
                # a project node" is finally known.
                if conf is not None:
                    confidence = conf
                elif target and not target.startswith("external::"):
                    confidence = "RECEIVER_RESOLVED"
                else:
                    confidence = "EXTRACTED"
                edges.append(_edge(src, target, "calls", confidence=confidence))
            # Wave 1p4ls: same-file constant reads (deduped per (reader, constant)).
            for src, target in dict.fromkeys(collector.reads):
                edges.append(_edge(src, target, GRAPH_READS_RELATION, confidence="EXTRACTED"))
            # Wave 1p7dh: buffer config-key read candidates (reader, literal) for
            # cross-file resolution against config-key nodes in finalize.
            config_read_candidates.extend(collector.config_reads)

        # Wave 1p7dh: (reader_symbol, literal_key) pairs, resolved to config-key
        # nodes in finalize (a literal that matches no config-key node is dropped).
        config_read_candidates: list[tuple[str, str]] = []

        # Attach call edges for top-level defs and classes.
        for stmt in tree.body:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                collect_calls(stmt.body, f"{rel_path}::{stmt.name}", owner_node=stmt)
            elif isinstance(stmt, ast.ClassDef):
                class_qname = stmt.name
                class_attr_types = _py_build_class_attr_types(stmt)
                for child in stmt.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        collect_calls(child.body, f"{rel_path}::{class_qname}.{child.name}", scope_class=class_qname, owner_node=child, attr_types=class_attr_types)

        # Wave 1p9q7: AST-anchored FastAPI `Depends(...)` DI signals. Produced
        # here (not by the text-based `collect_di_signals`) so idiom text in
        # strings/comments never fires; merged WITH the text collector at the
        # call site (`_extract_code_artifact`).
        di_signals: list[dict[str, Any]] = []
        try:
            di_signals = _load_di_signals_module().collect_python_di_signals(
                rel_path, tree, import_aliases, set(simple_names.keys()), source_text
            )
        except Exception:
            di_signals = []

        return {
            "kind": "code",
            "path": rel_path,
            "source_hash": _sha256_text(source_text),
            "nodes": nodes,
            "edges": edges,
            "defined_symbols": defined_symbols,
            "simple_names": simple_names,
            "mentioned_symbols": [],
            "config_read_candidates": config_read_candidates,
            "di_signals": di_signals,
        }

    def _extract_js_artifact(self, rel_path: str, source_text: str) -> dict[str, Any]:
        lines = source_text.splitlines()
        module_id = rel_path
        nodes: list[dict[str, Any]] = [
            _node(module_id, _path_term(rel_path), "module", rel_path, "1:0", layer=self.layer)
        ]
        edges: list[dict[str, Any]] = []
        defined_symbols: list[str] = []
        simple_names: dict[str, list[str]] = {}
        import_aliases: dict[str, str] = {}
        current_class: str | None = None

        def add_symbol(qname: str, kind: str, lineno: int) -> str:
            node_id = f"{rel_path}::{qname}"
            nodes.append(
                _node(
                    node_id,
                    qname.split(".")[-1],
                    kind,
                    rel_path,
                    self._source_location(source_text, lineno),
                    layer=self.layer,
                )
            )
            edges.append(_edge(module_id, node_id, "defines", confidence="EXTRACTED"))
            defined_symbols.append(node_id)
            simple_names.setdefault(qname.split(".")[-1], []).append(node_id)
            return node_id

        for lineno, raw in enumerate(lines, start=1):
            line = raw.rstrip()
            m = _JS_IMPORT_RE.match(line)
            if m:
                spec = m.group(2)
                clause = m.group(1).strip()
                if clause.startswith("{") and clause.endswith("}"):
                    for part in clause.strip("{} ").split(","):
                        item = part.strip()
                        if not item:
                            continue
                        if " as " in item:
                            imported, alias = [p.strip() for p in item.split(" as ", 1)]
                        else:
                            imported = alias = item
                        import_aliases[alias] = f"{spec}.{imported}"
                else:
                    alias = clause.split(",")[0].strip().split(" as ")[-1].strip()
                    alias = alias.lstrip("* from ").strip() if alias else alias
                    if alias:
                        import_aliases[alias] = spec
                target_id = f"external::{spec}"
                nodes.append(_node(target_id, spec, "module", "", "1:0", layer=self.layer))
                edges.append(_edge(module_id, target_id, "imports", confidence="EXTRACTED"))
                continue
            m = _JS_REQUIRE_RE.match(line)
            if m:
                alias, spec = m.group(1), m.group(2)
                import_aliases[alias] = spec
                target_id = f"external::{spec}"
                nodes.append(_node(target_id, spec, "module", "", "1:0", layer=self.layer))
                edges.append(_edge(module_id, target_id, "imports", confidence="EXTRACTED"))
                continue
            m = _JS_DEF_RE.match(line)
            if m:
                name = m.group(1)
                if line.strip().startswith("class "):
                    current_class = name
                    add_symbol(name, "class", lineno)
                else:
                    qname = f"{current_class}.{name}" if current_class and "class" in line else name
                    add_symbol(qname, "function", lineno)
                continue
            m = _JS_CONST_FN_RE.match(line)
            if m:
                name = m.group(1)
                qname = f"{current_class}.{name}" if current_class and "class" in line else name
                add_symbol(qname, "function", lineno)
                continue
            if line.startswith("}"):
                current_class = None

        symbol_lookup = {symbol_id.split("::", 1)[-1]: symbol_id for symbol_id in defined_symbols}
        for name, items in simple_names.items():
            if len(items) == 1:
                symbol_lookup.setdefault(name, items[0])

        for lineno, raw in enumerate(lines, start=1):
            line = raw.rstrip()
            for match in _JS_CALL_RE.finditer(line):
                name = match.group(1)
                if name in ("function", "class", "if", "for", "while", "switch", "catch", "return", "const", "let", "var", "new"):
                    continue
                target = None
                if name in import_aliases:
                    target = f"external::{import_aliases[name]}"
                elif name in symbol_lookup:
                    target = symbol_lookup[name]
                if target:
                    source_symbol = defined_symbols[0] if defined_symbols else module_id
                    edges.append(_edge(source_symbol, target, "calls", confidence="EXTRACTED"))

        return {
            "kind": "code",
            "path": rel_path,
            "source_hash": _sha256_text(source_text),
            "nodes": nodes,
            "edges": edges,
            "defined_symbols": defined_symbols,
            "simple_names": simple_names,
            "mentioned_symbols": [],
        }

    def _empty_code_artifact(self, rel_path: str, source_text: str) -> dict[str, Any]:
        return {
            "kind": "code",
            "path": rel_path,
            "source_hash": _sha256_text(source_text),
            "nodes": [_node(rel_path, _path_term(rel_path), "module", rel_path, "1:0", layer=self.layer)],
            "edges": [],
            "defined_symbols": [],
            "simple_names": {},
            "mentioned_symbols": [],
        }

    def _extract_line_scan_artifact(
        self, rel_path: str, source_text: str, lang_key: str | None
    ) -> dict[str, Any]:
        """Wave 1p9q6: degraded line-scan extraction for a code file over the
        AST parse cap (but under the walk cap). Recovers imports + top-level
        definitions only — every node marked ``extraction: "line_scan"`` — and
        emits NO call/read edges. The recovered definition nodes flow into
        ``defined_symbols``/``simple_names`` exactly like a parsed definition,
        so the cross-file candidate index picks them up (a hub's symbols bind
        inbound references AND correctly force twin-refusal). Mirrors the 1p9qe
        recovery convention: marker + per-file count properties + build-log
        line. Over the scan-byte ceiling → an empty module node flagged
        ``line_scan_ceiling_skipped`` (logged, never silent)."""
        module_id = rel_path
        module_node = _node(module_id, _path_term(rel_path), "module", rel_path, "1:0", layer=self.layer)
        nodes: list[dict[str, Any]] = [module_node]
        edges: list[dict[str, Any]] = []
        defined_symbols: list[str] = []
        simple_names: dict[str, list[str]] = defaultdict(list)

        scan = _line_scan_extract(source_text, lang_key)
        if scan["ceiling_skipped"]:
            module_node["line_scan_ceiling_skipped"] = True
            return {
                "kind": "code",
                "path": rel_path,
                "source_hash": _sha256_text(source_text),
                "nodes": nodes,
                "edges": edges,
                "defined_symbols": defined_symbols,
                "simple_names": {},
                "mentioned_symbols": [],
            }

        module_node["extraction"] = _LINE_SCAN_MARKER
        import_count = 0
        for spec in scan["imports"]:
            edges.append(_edge(module_id, f"external::{spec}", "imports", confidence="EXTRACTED"))
            import_count += 1
        emitted: set[str] = set()
        for name, kind, line in scan["definitions"]:
            node_id = f"{module_id}::{name}"
            if node_id in emitted:
                continue
            emitted.add(node_id)
            node = _node(
                node_id, name, kind, rel_path,
                self._source_location(source_text, line), layer=self.layer,
            )
            node["extraction"] = _LINE_SCAN_MARKER
            nodes.append(node)
            edges.append(_edge(module_id, node_id, "defines", confidence="EXTRACTED"))
            defined_symbols.append(node_id)
            simple = _simple_name(node_id)
            if simple and node_id not in simple_names[simple]:
                simple_names[simple].append(node_id)

        # Loud degradation counts (1p9qe convention parallel; AC-1b pins these
        # three by name). Always set — even at zero — so the per-file contract
        # is uniform and directly assertable.
        module_node["line_scan_defines"] = len(defined_symbols)
        module_node["line_scan_imports"] = import_count
        module_node["line_scan_skipped"] = int(scan["skipped_lines"])
        return {
            "kind": "code",
            "path": rel_path,
            "source_hash": _sha256_text(source_text),
            "nodes": nodes,
            "edges": edges,
            "defined_symbols": defined_symbols,
            "simple_names": {name: ids for name, ids in simple_names.items()},
            "mentioned_symbols": [],
        }

    def _extract_json_artifact(self, rel_path: str, source_text: str) -> dict[str, Any]:
        ts_artifact = self._extract_tree_sitter_artifact(rel_path, source_text, "json")
        if ts_artifact is not None and ts_artifact.get("defined_symbols"):
            return ts_artifact
        try:
            payload = json.loads(source_text)
        except json.JSONDecodeError:
            return self._empty_code_artifact(rel_path, source_text)
        module_id = rel_path
        nodes: list[dict[str, Any]] = [
            _node(module_id, _path_term(rel_path), "module", rel_path, "1:0", layer=self.layer)
        ]
        edges: list[dict[str, Any]] = []
        defined_symbols: list[str] = []
        if isinstance(payload, dict):
            for key in sorted(payload.keys()):
                if not isinstance(key, str) or not key:
                    continue
                node_id = f"{rel_path}::{key}"
                nodes.append(
                    _node(node_id, key, "class", rel_path, "1:0", layer=self.layer)
                )
                edges.append(_edge(module_id, node_id, "defines", confidence="EXTRACTED"))
                defined_symbols.append(node_id)
        return {
            "kind": "code",
            "path": rel_path,
            "source_hash": _sha256_text(source_text),
            "nodes": nodes,
            "edges": edges,
            "defined_symbols": defined_symbols,
            "simple_names": {},
            "mentioned_symbols": [],
        }

    def _extract_config_artifact(self, rel_path: str, source_text: str) -> dict[str, Any]:
        """Wave 1p7dh: emit config-key NODES for `.properties` / `.yml` / `.yaml`
        files, mirroring `_extract_json_artifact`'s node/edge shape (node id
        `file::dotted.key`, kind "class", a `defines` edge `module -> node`). The
        language-agnostic finalize pass then binds these to reader code sites via
        `reads_config`. Malformed input → `_empty_code_artifact` (parity with JSON).
        """
        suffix = Path(rel_path).suffix.lower()
        try:
            if suffix == ".properties":
                keys = _parse_properties_keys(source_text)
            else:
                keys = _parse_yaml_keys(source_text)
        except Exception:
            return self._empty_code_artifact(rel_path, source_text)
        module_id = rel_path
        nodes: list[dict[str, Any]] = [
            _node(module_id, _path_term(rel_path), "module", rel_path, "1:0", layer=self.layer)
        ]
        edges: list[dict[str, Any]] = []
        defined_symbols: list[str] = []
        seen: set[str] = set()
        for key in keys:
            if not key or key in seen:
                continue
            seen.add(key)
            node_id = f"{rel_path}::{key}"
            nodes.append(_node(node_id, key, "class", rel_path, "1:0", layer=self.layer))
            edges.append(_edge(module_id, node_id, "defines", confidence="EXTRACTED"))
            defined_symbols.append(node_id)
        return {
            "kind": "code",
            "path": rel_path,
            "source_hash": _sha256_text(source_text),
            "nodes": nodes,
            "edges": edges,
            "defined_symbols": defined_symbols,
            "simple_names": {},
            "mentioned_symbols": [],
        }

    def _extract_tree_sitter_artifact(self, rel_path: str, source_text: str, lang_key: str) -> dict[str, Any] | None:
        profile = _TS_LANGUAGE_PROFILES.get(lang_key)
        if profile is None:
            return None
        tree = _ts_parse(lang_key, source_text)
        if tree is None:
            return None
        mode = profile.mode
        source_bytes = source_text.encode("utf-8", errors="replace")
        source_lines = source_text.splitlines()  # Wave 1p4ls: chunker const predicates need lines
        # Wave 1p9q7: AST-anchored NestJS/Inversify DI signals (TypeScript only),
        # walked over the already-parsed tree so idiom text in strings/comments
        # never fires. Merged WITH the text collector at the call site.
        _ts_di_signals: list[dict[str, Any]] = []
        if lang_key == "typescript":
            try:
                _ts_di_signals = _load_di_signals_module().collect_ts_di_signals(
                    rel_path, tree.root_node, source_bytes
                )
            except Exception:
                _ts_di_signals = []
        const_node_ids: set[str] = set()  # Wave 1p4ls: this file's constant node ids (reads gate)
        module_id = rel_path
        node_map: dict[str, dict[str, Any]] = {
            module_id: _node(module_id, _path_term(rel_path), "module", rel_path, "1:0", layer=self.layer)
        }
        # Wave 1p9qh (1p9qb): record the DECLARED package on the file's module
        # node so the same-package disambiguation tier keys on the language
        # fact rather than directory layout (patterns mirror the
        # package-collapse mechanism in `graph_query._DIRECTORY_AGG_LANGUAGES`).
        # Node-borne so incremental merges recover it from per-file fragments.
        if lang_key in ("java", "kotlin"):
            _pkg_match = (_JAVA_PKG_DECL_RE if lang_key == "java" else _KOTLIN_PKG_DECL_RE).search(source_text)
            if _pkg_match:
                node_map[module_id]["declared_package"] = _pkg_match.group(1)
        edge_map: dict[tuple[str, str, str, str], dict[str, Any]] = {}
        defined_symbols: list[str] = []
        simple_names: dict[str, list[str]] = defaultdict(list)
        import_aliases: dict[str, str] = {}

        def add_node(node_id: str, label: str, kind: str, source_location: str) -> None:
            if node_id not in node_map:
                node_map[node_id] = _node(node_id, label, kind, rel_path, source_location, layer=self.layer)

        def add_edge(
            source: str,
            target: str,
            relation: str,
            *,
            confidence: str,
            evidence: str | None = None,
            self_edge_kind: str | None = None,
        ) -> None:
            key = (source, target, relation, confidence)
            if key in edge_map:
                return
            edge_map[key] = _edge(
                source,
                target,
                relation,
                confidence=confidence,
                evidence=evidence,
                self_edge_kind=self_edge_kind,
            )

        # Wave 1p2q3 (1p2td): per-overload signature accumulator. Maps qualified
        # node id to the set of parameter signatures observed across all
        # overload definitions sharing that node id (after the per-file merge).
        overload_signatures: dict[str, set[str]] = {}
        # Wave 1p2q3 (1p2tf): per-file imported-name → resolved-target map.
        # Populated during import-edge emission; consulted by the TS/JS
        # receiver-type resolver so aliased cross-package types bind to the
        # resolved project node.
        import_targets: dict[str, str] = {}
        # Wave 1p9qh (1p9q9): this file's Java static imports, consumed by
        # `_resolve_java_call_target` when draining buffered calls (imports are
        # walked before the drain, so both maps are complete by then).
        #   java_static_members: bare member name -> "Class.member" from
        #     `import static com.foo.Bar.baz;` (None marks the same member
        #     name statically imported from two different classes — illegal
        #     Java, refused rather than guessed).
        #   java_static_wildcards: class FQNs from `import static com.foo.Bar.*;`
        #     (deduped, order-preserving; >1 distinct FQN → unique-survivor
        #     refusal at resolution time).
        java_static_members: dict[str, str | None] = {}
        java_static_wildcards: list[str] = []

        # Wave 13129 (1316l + 13190): class/module merge — when a file
        # `Foo.<ext>` contains a top-level type declaration named `Foo`
        # (basename match), the file node and the class node merge into
        # a single node at the file id. The class id (`<file>::<basename>`)
        # is NOT registered; edges that would target it route to the file id
        # instead. Operators querying by either form get the unified node.
        #
        # Per-language merge-eligible kinds (13190/13196/1319i/1319k multi-language extension):
        _CLASS_MODULE_MERGE_KINDS_BY_LANG: dict[str, frozenset[str]] = {
            "swift":      frozenset({"class", "struct", "actor", "enum", "protocol"}),
            # Wave 1p9qh (1p9qb): the former `"annotation_type"` entry was DEAD
            # — no kind string `"annotation_type"` is ever produced.
            # `annotation_type_declaration` now classifies as kind "class"
            # (see `_ts_kind_for_definition`), so `@interface Foo` in
            # `Foo.java` merges through the "class" entry like every other
            # Java type declaration.
            "java":       frozenset({"class", "interface", "enum", "record"}),
            "kotlin":     frozenset({"class", "interface", "object", "enum_class"}),
            "csharp":     frozenset({"class", "interface", "struct", "record", "enum"}),
            # Wave 13196: JS/TS/Scala/PHP
            "javascript": frozenset({"class"}),
            "typescript": frozenset({"class", "interface", "type", "enum"}),
            "scala":      frozenset({"class", "object", "trait", "enum"}),
            "php":        frozenset({"class", "interface", "trait"}),
            # Wave 1319i/1319k: Rust/Ruby — snake_case file convention.
            # Note: indexer's _ts_kind_for_definition normalizes Rust's
            # `struct_item`/`enum_item`/`trait_item` ALL to `"class"` kind;
            # similarly Ruby's `class` registers as `"class"` and `module`
            # registers as `"module"`. Merge gate matches against the
            # normalized kind values.
            "rust":       frozenset({"class"}),
            "ruby":       frozenset({"class", "module"}),
        }
        # Multi-extension languages (JS has 4, TS has 2).
        _CLASS_MODULE_MERGE_EXTS_BY_LANG: dict[str, tuple[str, ...]] = {
            "swift":      (".swift",),
            "java":       (".java",),
            "kotlin":     (".kt",),
            "csharp":     (".cs",),
            "javascript": (".js", ".jsx", ".mjs", ".cjs"),
            "typescript": (".ts", ".tsx"),
            "scala":      (".scala",),
            "php":        (".php",),
            "rust":       (".rs",),
            "ruby":       (".rb",),
        }
        # Wave 1319i/1319k: languages with snake_case file convention need
        # snake-to-PascalCase basename conversion. `foo_bar.rs` looks for
        # `struct FooBar`. Detection tries BOTH the snake-derived name AND
        # the literal basename (some Rust crates use `Foo.rs` directly).
        _SNAKE_TO_PASCAL_LANGS = frozenset({"rust", "ruby"})

        # Wave 131bt (1319o): languages that permit multiple top-level classes
        # per file need a dominance gate — merge only fires when the file has
        # exactly one top-level class declaration matching the basename.
        # Without the gate the merge would over-trigger on utility modules
        # containing several classes. Java/C#/Kotlin/Swift/Scala/PHP enforce
        # one-top-level-class-per-file via language convention so don't need
        # the gate.
        _DOMINANCE_GATE_LANGS = frozenset({"python", "javascript", "typescript"})

        # Wave 131bt (1319o): JS/TS support kebab-case file naming
        # convention (`foo-bar.js` containing `class FooBar`). Try kebab->Pascal
        # alongside the literal basename and snake->Pascal.
        _KEBAB_TO_PASCAL_LANGS = frozenset({"javascript", "typescript"})

        def _snake_to_pascal(name: str) -> str:
            if not name:
                return ""
            parts = name.split("_")
            return "".join(p[:1].upper() + p[1:] for p in parts if p)

        def _kebab_to_pascal(name: str) -> str:
            if not name:
                return ""
            parts = name.split("-")
            return "".join(p[:1].upper() + p[1:] for p in parts if p)

        _merge_kinds = _CLASS_MODULE_MERGE_KINDS_BY_LANG.get(lang_key, frozenset())
        _merge_exts = _CLASS_MODULE_MERGE_EXTS_BY_LANG.get(lang_key, ())
        _basename_raw = ""
        for _ext in _merge_exts:
            if rel_path.endswith(_ext):
                _basename_raw = rel_path.rsplit("/", 1)[-1].rsplit(_ext, 1)[0]
                break
        # Build the set of basename candidates the merge gate matches against.
        # For exact-match languages (Swift/Java/Kotlin/C#/Scala/PHP), only the
        # literal basename matches. For snake-to-Pascal languages (Rust/Ruby),
        # the literal basename and snake-to-Pascal conversion match. For JS/TS
        # (wave 131bt 1319o), the literal basename, snake-to-Pascal, AND
        # kebab-to-Pascal all match — JS/TS codebases use all three.
        _file_basename_candidates_set: set[str] = set()
        if _basename_raw:
            _file_basename_candidates_set.add(_basename_raw)
            if lang_key in _SNAKE_TO_PASCAL_LANGS:
                _file_basename_candidates_set.add(_snake_to_pascal(_basename_raw))
            if lang_key in _KEBAB_TO_PASCAL_LANGS:
                _file_basename_candidates_set.add(_kebab_to_pascal(_basename_raw))
                _file_basename_candidates_set.add(_snake_to_pascal(_basename_raw))
        _file_basename_candidates: frozenset[str] = frozenset(_file_basename_candidates_set)

        # Wave 131bt (1319o): pre-count top-level merge-eligible class
        # declarations. Used by the dominance gate for languages permitting
        # multi-class files (Python/JS/TS). Counted via tree-sitter AST walk
        # before walk_definitions; only direct children of the root program
        # node (or export wrappers) count as top-level.
        def _count_top_level_classes() -> int:
            if lang_key not in _DOMINANCE_GATE_LANGS:
                return -1  # Sentinel: gate not applied to this language.
            if not _merge_kinds:
                return -1
            root = tree.root_node
            count = 0
            for child in (getattr(root, "named_children", []) or []):
                ctype = getattr(child, "type", "") or ""
                # Direct top-level class declarations.
                if _ts_is_definition_node(ctype, mode):
                    kind = _ts_kind_for_definition(ctype, None, mode)
                    if kind in _merge_kinds:
                        count += 1
                    continue
                # JS/TS export wrappers — peek inside.
                if lang_key in ("javascript", "typescript") and ctype in (
                    "export_statement", "export_default_declaration"
                ):
                    for inner in (getattr(child, "named_children", []) or []):
                        inner_type = getattr(inner, "type", "") or ""
                        if _ts_is_definition_node(inner_type, mode):
                            inner_kind = _ts_kind_for_definition(inner_type, None, mode)
                            if inner_kind in _merge_kinds:
                                count += 1
            return count

        _top_level_class_count = _count_top_level_classes()

        def register_symbol(qname: str, kind: str, node, parent_symbol: str | None) -> str:
            # Wave 13129 (1316l/13190/1319i/1319k): merge top-level type whose
            # name matches one of the file basename candidates into the module
            # node. Candidates are the literal basename plus (for languages
            # with snake_case file convention like Rust/Ruby) the PascalCase
            # conversion of the basename.
            # Wave 131bt (1319o): dominance gate for multi-class languages.
            # Python/JS/TS permit multiple top-level classes per file; only
            # merge when exactly one such class exists AND its name matches
            # the basename.
            _dominance_gate_passes = (
                lang_key not in _DOMINANCE_GATE_LANGS
                or _top_level_class_count == 1
            )
            # Wave 1p9qi (1p9qg): buffer JPA/EF entity classes for the
            # post-walk mapping capture (it needs symbol_lookup for the
            # same-file impostor checks). Computed BEFORE the basename-
            # collapse early return below — a file-dominant entity class
            # (User.java defining class User, the normal JPA layout) merges
            # into the module node and never reaches the annotation block
            # further down. Gated on the cheap name-only extractors so the
            # argument-record walk runs only for annotated classes.
            _orm_entity_carrier = None
            # 1p9qi review: extracted once here and reused by the annotation-
            # capture block below (previously the same node's annotations were
            # walked twice for every Java/C# class).
            _node_annotations: list[str] | None = None
            if kind == "class" and lang_key in ("java", "csharp"):
                _node_annotations = (
                    _ts_extract_java_annotations(node, source_bytes)
                    if lang_key == "java"
                    else _ts_extract_csharp_attributes(node, source_bytes)
                )
                _orm_tails = {a.rsplit(".", 1)[-1] for a in _node_annotations}
                if (lang_key == "java" and "Entity" in _orm_tails) or (
                    lang_key == "csharp" and _orm_tails & _CSHARP_TABLE_ATTRIBUTE_TAILS
                ):
                    _orm_entity_carrier = node
            if (
                _file_basename_candidates
                and kind in _merge_kinds
                and qname in _file_basename_candidates
                and _dominance_gate_passes
            ):
                # Update module node identity to take on the class.
                module_node = node_map.get(module_id)
                if module_node is not None:
                    module_node["label"] = qname
                    module_node["kind"] = kind
                    module_node["collapsed_pair"] = True
                # Register the basename under simple_names so cross-file
                # resolution can rebind `external::Foo` to this module_id.
                simple_names.setdefault(qname, []).append(module_id)
                # Track as defined for symbol_lookup population (uses the
                # qname → module_id mapping).
                if module_id not in defined_symbols:
                    defined_symbols.append(module_id)
                if _orm_entity_carrier is not None:
                    orm_entity_class_nodes.append((module_id, _orm_entity_carrier))
                return module_id
            node_id = f"{rel_path}::{qname}"
            label = qname.rsplit(".", 1)[-1]
            add_node(node_id, label, kind, self._source_location(source_text, node.start_point[0] + 1))
            # Wave 130rj — field feedback §2.3: capture annotation tails on Java and
            # attribute tails on C# so code_callhierarchy can emit
            # `caller_pattern: "advice"` when incoming is empty for an AOP-
            # annotated/attributed method. Java annotations live inside the
            # `modifiers` child; C# attributes live in sibling `attribute_list`
            # nodes (130tc).
            if lang_key == "java":
                annotations = (
                    _node_annotations
                    if _node_annotations is not None
                    else _ts_extract_java_annotations(node, source_bytes)
                )
                if annotations:
                    node_map[node_id]["annotations"] = annotations
                    # Wave 1p9qi (1p9qf): SQL-carrying annotation sinks
                    # (MyBatis @Select/@Insert/@Update/@Delete, native @Query,
                    # @NamedNativeQuery). Gated on the already-extracted names
                    # so the argument-record walk runs only at a sink.
                    if any(
                        a.rsplit(".", 1)[-1] in _JAVA_SQL_SINK_ANNOTATIONS
                        for a in annotations
                    ):
                        _ann_sqls, _ann_dyn = _java_annotation_sql_captures(node, source_bytes)
                        for _ann_sql in _ann_sqls:
                            sql_capture_candidates.append((node_id, _ann_sql))
                        _sql_dynamic[0] += _ann_dyn
            elif lang_key == "csharp":
                attributes = (
                    _node_annotations
                    if _node_annotations is not None
                    else _ts_extract_csharp_attributes(node, source_bytes)
                )
                if attributes:
                    # Surface as `annotations` for downstream parity with Java.
                    node_map[node_id]["annotations"] = attributes
            if _orm_entity_carrier is not None:  # Wave 1p9qg: non-collapsed entity class
                orm_entity_class_nodes.append((node_id, _orm_entity_carrier))
            add_edge(module_id, node_id, "defines", confidence="EXTRACTED")
            if parent_symbol and parent_symbol != module_id:
                add_edge(parent_symbol, node_id, "defines", confidence="EXTRACTED")
            defined_symbols.append(node_id)
            simple = _simple_name(node_id)
            # Wave 1p4ls (delivery review B1): dedup the simple_names append. The constant
            # intercept recurses into a const declaration's OWN name-bearing child (e.g. a
            # Kotlin `const val X` → variable_declaration, an already-registered constant node),
            # which re-registers the SAME node_id here. An unconditional append makes
            # simple_names[X] length 2, so the uniqueness gate below (len == 1) skips X and its
            # same-scope read never resolves — silently producing zero reads edges for every
            # object/companion/class `const val`. Deduping a node_id under its own simple key is
            # always correct (a node appearing twice only inflates the count, never adds info).
            if simple and node_id not in simple_names.setdefault(simple, []):
                simple_names[simple].append(node_id)
            return node_id

        def register_constant(qname: str, node, value: str | None, parent_symbol: str | None) -> str:
            # Wave 1p4ls: a tree-sitter constant node (kind="constant"). Unlike register_symbol it
            # never merges with the file node (a constant is not a file-dominant type) and carries
            # an optional simple-literal value. Registered in defined_symbols/simple_names so reads
            # edges + cross-file resolution see it exactly like a function/class.
            node_id = f"{rel_path}::{qname}"
            add_node(node_id, qname.rsplit(".", 1)[-1], GRAPH_CONST_KIND, self._source_location(source_text, node.start_point[0] + 1))
            if value is not None:
                node_map[node_id]["value"] = value
            add_edge(module_id, node_id, "defines", confidence="EXTRACTED")
            if parent_symbol and parent_symbol != module_id:
                add_edge(parent_symbol, node_id, "defines", confidence="EXTRACTED")
            if node_id not in defined_symbols:
                defined_symbols.append(node_id)
            simple = _simple_name(node_id)
            if simple and node_id not in simple_names.setdefault(simple, []):  # 1p4ls B1: dedup (see register_symbol)
                simple_names[simple].append(node_id)
            return node_id

        # Wave 1p2q3 (1p2tz post-ship-4 perf): single-pass walker. The previous
        # implementation walked the tree twice — once for definitions, once for
        # calls — duplicating tree-traversal overhead. The single-pass walker
        # registers definitions inline (so symbol_lookup can be built immediately
        # after) and buffers call sites; post-walk, a single pass over the
        # buffer resolves and emits call edges using the now-complete symbol
        # table. Reduces walker wall-time ~30-40% on real codebases by avoiding
        # the duplicate AST descent.
        buffered_calls: list[tuple[str, Any, str, list[str]]] = []  # (source_symbol, call_node, node_type, scope_signatures_snapshot)
        buffered_reads: list[tuple[str, str]] = []  # Wave 1p4ls: (reader_symbol, identifier_text)
        # Wave 1p9qh (1p9qa): Java/C# (class_node_id, supertype_name, relation)
        # facts — drained post-walk when symbol_lookup is complete, so a
        # same-file supertype binds directly.
        buffered_supertypes: list[tuple[str, str, str]] = []
        config_read_candidates: list[tuple[str, str]] = []  # Wave 1p7dh: Java (reader_symbol, config_key)
        # Wave 1p9qi (1p9qf): (source_symbol_or_mybatis_marker, sql_text) sink
        # captures, bound at finalize; single-cell list so nested defs
        # (register_symbol / walk_definitions) can bump the refusal count.
        sql_capture_candidates: list[tuple[str, str]] = []
        _sql_dynamic = [0]
        # Wave 1p9qi (1p9qg): ORM entity→table mapping capture. Entity-class
        # AST nodes buffered by register_symbol (both collapse paths), drained
        # post-walk when symbol_lookup exists (impostor checks need it);
        # candidates = (source_marker, declared_table); refusal counters ride
        # the fragment so the convention/dynamic gaps stay visible.
        orm_entity_class_nodes: list[tuple[str, Any]] = []
        orm_entity_candidates: list[tuple[str, str]] = []
        _orm_dynamic = [0]
        _orm_convention = [0]
        func_locals: dict[str, set[str]] = {}  # reader_symbol -> {param/local binding names} (member-access F4 shadow guard)
        # Wave 1p9q5: Rust module-model harvest. `rust_mod_decls` = external
        # `mod name;` decls (name + optional `#[path]` override) driving the
        # cross-file module tree; `rust_inline_mods` = dotted qnames of inline
        # `mod name { … }` scopes (matching the walker's `.`-joined qnames) so
        # finalize can key each def on its enclosing inline module. Both are
        # stored on the file's module node (node-borne, incremental-merge safe).
        rust_mod_decls: list[dict[str, str | None]] = []
        rust_inline_mods: list[str] = []

        def walk_definitions(
            node,
            scope_names: list[str],
            scope_kinds: list[str],
            scope_symbols: list[str],
            scope_signatures: list[str] | None = None,
        ) -> None:
            if scope_signatures is None:
                scope_signatures = []
            node_type = str(getattr(node, "type", "") or "")
            current_scope_kind = scope_kinds[-1] if scope_kinds else None
            # Member-access F4 shadow guard: collect this function's parameter + local binding NAMES.
            # Done BEFORE the is_definition/import branches (which `return`) because some grammars (e.g.
            # Swift `parameter`) ARE definition nodes and would otherwise skip this.
            if current_scope_kind in ("function", "method") and node_type in _TS_BINDING_NODE_TYPES and scope_symbols:
                _bn = _ts_binding_names(node)
                if _bn:
                    func_locals.setdefault(scope_symbols[-1], set()).update(_bn)
            # Wave 1p7dh: Spring `@Value("${key}")` field/param/method annotation →
            # config-read candidate. The reader is the enclosing class node id
            # (nearest class-kind scope symbol; falls back to the file/module node
            # when the class collapsed or the annotation is module-level). The
            # finalize pass binds the key to a config-key node on a unique match.
            if lang_key == "java":
                _value_keys = _java_value_annotation_keys(node, source_bytes)
                if _value_keys:
                    _reader = module_id
                    for _k, _s in zip(reversed(scope_kinds), reversed(scope_symbols)):
                        if _k == "class":
                            _reader = _s
                            break
                    for _vk in _value_keys:
                        config_read_candidates.append((_reader, _vk))
            is_import = _ts_markup_import_nodes(node, source_bytes) if mode == "markup" else _ts_is_import_node(node_type, mode)
            is_definition = bool(_ts_markup_name_candidates(node, source_bytes)) if mode == "markup" else _ts_is_definition_node(node_type, mode)
            if is_import:
                source_symbol = scope_symbols[-1] if scope_symbols else module_id
                # Wave 1p4eu (AC-5): Rust `use_declaration` — emit CLEAN dotted
                # import edges (final segment = the imported type name, so
                # `imports_by_file` is consumable) with `as` aliases registered in
                # `import_aliases`, and produce NO keyword-noise edge. The generic
                # relation-candidate fallback below emitted `external::use`/`pub`/
                # `fn`/`as` junk and lossy `::`-paths for Rust; handling the
                # use-tree explicitly and returning skips that path entirely.
                if lang_key == "rust" and node_type == "use_declaration":
                    for _imp_head, _imp_target in _rust_use_imports(node, source_bytes):
                        add_edge(source_symbol, f"external::{_imp_target}", "imports", confidence="EXTRACTED")
                        if _imp_head and _imp_head != _imp_target.rsplit(".", 1)[-1]:
                            import_aliases[_imp_head] = _imp_target
                    return
                # Wave 1p9qh (1p9q9): Java `import_declaration` — structured
                # parse (explicit / wildcard / static / static-wildcard),
                # replacing the regex fallback FOR JAVA ONLY. Fixes two
                # defects: `import com.foo.*;` no longer truncates to the
                # useless `com.foo.` candidate (it emits a package-prefix
                # `external::com.foo.*` edge that participates in import-edge
                # disambiguation), and `import static …;` no longer emits a
                # spurious `external::static` edge (the modifier is structural,
                # never a candidate). Static-import member facts are captured
                # for bare-call resolution at the buffered-call drain.
                if lang_key == "java" and node_type == "import_declaration":
                    _jfacts = _java_import_facts(node, source_bytes)
                    if _jfacts is not None:
                        _jfqn, _jstatic, _jwild = _jfacts
                        if _jwild:
                            # Package-prefix fact (plain wildcard) or static
                            # container class (static wildcard). The `.*`
                            # suffix keeps it out of `imports_by_file`'s
                            # simple-name buckets by construction.
                            add_edge(source_symbol, f"external::{_jfqn}.*", "imports", confidence="EXTRACTED")
                            if _jstatic and _jfqn not in java_static_wildcards:
                                java_static_wildcards.append(_jfqn)
                        else:
                            add_edge(
                                source_symbol,
                                _ts_resolve_target(_jfqn, {}, import_aliases),
                                "imports",
                                confidence="EXTRACTED",
                            )
                            if _jstatic and "." in _jfqn:
                                _jcls_path, _jmember = _jfqn.rsplit(".", 1)
                                _jcls = _jcls_path.rsplit(".", 1)[-1]
                                if _jcls and _jmember:
                                    _jtarget = f"{_jcls}.{_jmember}"
                                    if _jmember in java_static_members and java_static_members[_jmember] != _jtarget:
                                        java_static_members[_jmember] = None  # conflicting classes → refuse
                                    else:
                                        java_static_members[_jmember] = _jtarget
                    return
                # Wave 1p2q3 (1p2tf): extract imported names BEFORE resolving so
                # we can register each name → resolved-target binding for the
                # receiver-type resolver later.
                imported_names: list[str] = []
                # Wave 1p2q3 (1p2tz post-ship-3): raw module specifier (with `./`
                # and `@scope/` prefixes preserved) so the resolver can branch
                # on import shape — `_ts_relation_candidates` clean-names away
                # the relative-path prefix and the tsconfig.paths code can't
                # tell `./events` apart from `events`.
                raw_spec = ""
                if lang_key in ("typescript", "javascript"):
                    imported_names = _ts_extract_imported_names(node, source_bytes)
                    raw_spec = _ts_extract_import_module_specifier(node, source_bytes)
                # Wave 1p4eu: this import node's `as` aliases (`X as W` → {W: X}),
                # computed once — used both to drop the redundant bare-alias-name
                # candidate (the Kotlin `external::W` cosmetic node) and registered
                # in `import_aliases` at the end of the branch.
                _node_aliases = _ts_import_aliases(node, source_bytes, mode)
                _import_candidates = _ts_relation_candidates(node, source_bytes, "import", mode)
                _import_candidate_set = set(_import_candidates)
                for target in _import_candidates:
                    # Skip the bare alias NAME (RHS of `as`) when its real target is
                    # also a candidate: the alias is captured in `import_aliases`, so
                    # an `external::<alias>` edge would be a redundant lossy node.
                    _aliased = _node_aliases.get(target)
                    if _aliased and _aliased != target and _aliased in _import_candidate_set:
                        continue
                    resolved: str | None = None
                    if lang_key in ("typescript", "javascript"):
                        # Wave 1p2q3 (1p2tz post-ship-3): try relative-path
                        # resolution first when the raw specifier starts with
                        # `.` or `/`. Intra-package callers (libs/foo/src/a.ts
                        # importing `./b`) need project-path resolution so
                        # import_targets carries the walked-through definition
                        # file rather than `external::*`. Without this, the
                        # cross-file rewrite pass promotes the edge to the
                        # right target node but keeps it at EXTRACTED.
                        if raw_spec and (raw_spec.startswith(".") or raw_spec.startswith("/")):
                            from_file = self.root / rel_path
                            resolved = _resolve_relative_ts_import(raw_spec, from_file, self.root)
                        else:
                            # Wave 1p2q3 (1p2q9 A): honor tsconfig `paths`
                            # aliases before falling through to external::*.
                            resolved = _resolve_ts_import_via_tsconfig(raw_spec or target, rel_path, self.root)
                    if resolved is None:
                        resolved = _ts_resolve_target(target, {}, import_aliases)
                    add_edge(source_symbol, resolved, "imports", confidence="EXTRACTED")
                    # Wave 1p2q3 (1p2tf): bind each imported name to the
                    # resolved target so the receiver-type resolver can
                    # promote `external::Foo.bar` to a project node when
                    # `Foo` was imported from a tsconfig.paths-aliased lib.
                    # Wave 1p2q3 (1p2tz): when the resolved target is a barrel
                    # re-export (`src/index.ts` patterns), follow the chain so
                    # the binding points at the actual definition file.
                    if lang_key in ("typescript", "javascript") and resolved and not resolved.startswith("external::"):
                        for name in imported_names:
                            walked = _resolve_through_barrel(name, resolved, self.root)
                            import_targets[name] = walked
                    else:
                        for name in imported_names:
                            import_targets[name] = resolved
                import_aliases.update(_node_aliases)
            # Wave 1p2q3 (1p2tz post-ship per field validation): TS/JS
            # arrow-function / function-expression bound to a `const`.
            if lang_key in ("typescript", "javascript"):
                arrow_bindings = _ts_extract_arrow_const_bindings(node, source_bytes)
                if arrow_bindings:
                    for binding_name, declarator_node in arrow_bindings:
                        qname = ".".join([*scope_names, binding_name]) if scope_names else binding_name
                        parent_symbol = scope_symbols[-1] if scope_symbols else module_id
                        node_id = register_symbol(qname, "function", declarator_node, parent_symbol)
                        next_scope_names = [*scope_names, binding_name]
                        next_scope_kinds = [*scope_kinds, "function"]
                        next_scope_symbols = [*scope_symbols, node_id]
                        next_scope_signatures = [*scope_signatures, ""]
                        for child in (getattr(declarator_node, "named_children", []) or []):
                            walk_definitions(child, next_scope_names, next_scope_kinds, next_scope_symbols, next_scope_signatures)
                    return
            # Wave 1p4ls: intercept module-/type-level CONSTANT declarations → kind="constant"
            # per-name (+ simple-literal value), reusing the chunk-lane predicates. Replaces the
            # generic variable/function mislabel for these nodes. Function/method-body locals are
            # never reached (scope gate); a constant node never pushes scope (it is a leaf).
            if mode not in ("markup", "config", "sql") and current_scope_kind not in ("function", "method"):
                _const_decls = _ts_constant_decls(
                    lang_key, node, node_type, source_bytes, source_lines,
                    in_type_body=(current_scope_kind == "class"),
                )
                if _const_decls:
                    _parent_symbol = scope_symbols[-1] if scope_symbols else module_id
                    for _cname, _cvalue in _const_decls:
                        _cqname = ".".join([*scope_names, _cname]) if scope_names else _cname
                        const_node_ids.add(register_constant(_cqname, node, _cvalue, _parent_symbol))
                    # recurse into children WITHOUT pushing scope (initializer calls/reads attribute
                    # to the enclosing scope), then stop — the constant itself is a leaf symbol.
                    for child in getattr(node, "named_children", []):
                        walk_definitions(child, scope_names, scope_kinds, scope_symbols, scope_signatures)
                    return
            if is_definition:
                candidates = _ts_name_candidates(node, source_bytes, mode)
                name = _ts_pick_symbol_name(candidates, mode, node_type)
                # Wave 1p61v: never register a parser-artifact name (the reserved
                # word `function` from an anonymous function expression, or a
                # non-identifier route-path token like `/`). Gated to TS/JS — the
                # artifact is JS/TS-specific, and other languages have legitimate
                # non-identifier symbol names (C++ `operator==`, Rust operators,
                # Ruby `valid?`/`save!`/`<=>`) that this guard must NOT drop.
                _emittable = lang_key not in ("typescript", "javascript") or _ts_is_emittable_symbol_name(name, mode)
                if name and _emittable:
                    # Wave 1p4et: Go methods are top-level `func (r Type) Method()`
                    # — not nested in a class scope — so without this they register
                    # as bare `Method`; the resolver's `Type.method` symbol_lookup
                    # probe always misses and two types with a same-named method
                    # collide to one id. Prepend the receiver type → `Type.Method`.
                    if lang_key == "go" and node_type == "method_declaration" and not scope_names:
                        _recv = _go_method_node_receiver_type(node, source_bytes)
                        if _recv:
                            name = f"{_recv}.{name}"
                    kind = _ts_kind_for_definition(node_type, current_scope_kind, mode)
                    qname = ".".join([*scope_names, name]) if scope_names else name
                    parent_symbol = scope_symbols[-1] if scope_symbols else module_id
                    node_id = register_symbol(qname, kind, node, parent_symbol)
                    # Wave 1p9q5: Rust module-model harvest at the registration
                    # site (so the inline-mod qname matches the walker's exactly).
                    # A `mod name { … }` (has a `declaration_list` body) is an
                    # inline scope; a bodyless `mod name;` is an external decl
                    # mapping to a sibling/child file (its `#[path]` override read
                    # from the preceding attribute sibling).
                    if lang_key == "rust" and node_type == "mod_item":
                        if any(
                            getattr(c, "type", "") == "declaration_list"
                            for c in getattr(node, "children", []) or []
                        ):
                            rust_inline_mods.append(qname)
                        else:
                            rust_mod_decls.append(
                                {"name": name, "path": _rust_mod_path_attr(node, source_bytes)}
                            )
                    # Wave 1p9qh (1p9qa): Java/C# inheritance facts, buffered
                    # for the post-walk drain. Interface declarers additionally
                    # carry `declared_kind: "interface"` — `_ts_kind_for_definition`
                    # normalizes interfaces to kind "class", and downstream
                    # passes (the C# base-relation kind correction) need the
                    # class-vs-interface distinction cross-file. Set via the
                    # returned node id so the collapsed dominant-class merge
                    # (1316l — node_id == module_id) is covered too.
                    if lang_key == "java" and node_type in (
                        "class_declaration", "interface_declaration",
                        "enum_declaration", "record_declaration",
                    ):
                        if node_type == "interface_declaration":
                            node_map[node_id]["declared_kind"] = "interface"
                        for _sup_name, _sup_rel in _java_supertype_facts(node, source_bytes):
                            buffered_supertypes.append((node_id, _sup_name, _sup_rel))
                    elif lang_key == "csharp" and node_type in (
                        "class_declaration", "interface_declaration",
                        "struct_declaration", "record_declaration",
                    ):
                        if node_type == "interface_declaration":
                            node_map[node_id]["declared_kind"] = "interface"
                        for _sup_name, _sup_rel in _csharp_supertype_facts(node, node_type, source_bytes):
                            buffered_supertypes.append((node_id, _sup_name, _sup_rel))
                    # Wave 1p4q4: TS `enum` / `const enum` — each member is a constant NODE
                    # (`Enum.Member`), child of the enum type node (which stays a class node above).
                    # Members are how TS expresses named constants.
                    if lang_key in ("typescript", "javascript") and node_type == "enum_declaration":
                        # The walker does NOT push a scope frame for a TS namespace/module
                        # (internal_module/module aren't definition nodes), so `qname` lacks the
                        # enclosing namespace. Recover it from the AST ancestor chain and prepend it
                        # to the member qname — else two same-named enums in two namespaces collide
                        # to one member node and silently clobber each other's value (review D1).
                        _nsparts: list[str] = []
                        _anc = getattr(node, "parent", None)
                        while _anc is not None:
                            if str(getattr(_anc, "type", "") or "") in ("internal_module", "module"):
                                for _c in getattr(_anc, "children", []):
                                    if str(getattr(_c, "type", "") or "") in ("identifier", "nested_identifier"):
                                        _nsparts.append(_c.text.decode().strip())
                                        break
                            _anc = getattr(_anc, "parent", None)
                        _mem_base = (".".join(reversed(_nsparts)) + "." + qname) if _nsparts else qname
                        for _eb in getattr(node, "named_children", []):
                            if str(getattr(_eb, "type", "") or "") != "enum_body":
                                continue
                            for _mem in getattr(_eb, "named_children", []):
                                _mt = str(getattr(_mem, "type", "") or "")
                                if _mt == "property_identifier":
                                    _mn, _mv = _mem.text.decode().strip(), None
                                elif _mt == "enum_assignment":
                                    _mid = next((g for g in _mem.children
                                                 if str(getattr(g, "type", "") or "") == "property_identifier"), None)
                                    if _mid is None:
                                        continue
                                    _mn, _mv = _mid.text.decode().strip(), _ts_declarator_value(_mem, source_bytes)
                                else:
                                    continue
                                if _mn:
                                    const_node_ids.add(register_constant(f"{_mem_base}.{_mn}", _mem, _mv, node_id))
                    sig = _extract_definition_signature(node, source_bytes, lang_key)
                    if sig:
                        overload_signatures.setdefault(node_id, set()).add(sig)
                    should_push = _ts_is_scope_node(node_type, kind, mode)
                    if mode == "markup":
                        return
                    next_scope_names = [*scope_names, name] if should_push else scope_names
                    next_scope_kinds = [*scope_kinds, kind] if should_push else scope_kinds
                    next_scope_symbols = [*scope_symbols, node_id] if should_push else scope_symbols
                    next_scope_signatures = [*scope_signatures, sig or ""] if should_push else scope_signatures
                    for child in getattr(node, "named_children", []):
                        walk_definitions(child, next_scope_names, next_scope_kinds, next_scope_symbols, next_scope_signatures)
                    return
            if mode == "markup" and (is_import or is_definition):
                return
            # Wave 131bt (1319v): recover ERROR-wrapped top-level class declarations.
            if (
                not scope_names
                and mode not in ("markup", "config", "sql")
                and node_type == "ERROR"
            ):
                recovered = _ts_recover_error_class(node, source_bytes, lang_key)
                if recovered is not None:
                    rname, rkind = recovered
                    rqname = rname
                    rparent = module_id
                    rnode_id = register_symbol(rqname, rkind, node, rparent)
                    next_scope_names = [rname]
                    next_scope_kinds = [rkind]
                    next_scope_symbols = [rnode_id]
                    next_scope_signatures = [""]
                    for child in getattr(node, "named_children", []):
                        walk_definitions(child, next_scope_names, next_scope_kinds, next_scope_symbols, next_scope_signatures)
                    return
            # Wave 1p9qi (1p9qf): C# `<expr>.CommandText = "<sql>"` assignment
            # sink — assignments are not call nodes, so capture here.
            if lang_key == "csharp" and node_type == "assignment_expression":
                _ct_sql, _ct_dyn = _csharp_commandtext_sql_capture(node, source_bytes)
                if _ct_sql:
                    sql_capture_candidates.append(
                        (scope_symbols[-1] if scope_symbols else module_id, _ct_sql)
                    )
                _sql_dynamic[0] += _ct_dyn
            # Wave 1p2q3 (1p2tz post-ship-4 perf): buffer calls for post-walk
            # resolution. We can't emit edges yet because symbol_lookup is built
            # AFTER the walk completes.
            if _ts_is_call_node(node_type, mode, profile):
                source_symbol = scope_symbols[-1] if scope_symbols else module_id
                buffered_calls.append((source_symbol, node, node_type, list(scope_signatures)))
            # Wave 1p4ls: buffer identifier READS inside a function/method body for the `reads`
            # edge. Gated to function scope so class-body const-name identifiers and module noise
            # are not captured; resolved post-walk against the const node set (symbol_lookup
            # uniqueness = cross-module faithfulness; a coincidental twin stays unresolved).
            elif (current_scope_kind in ("function", "method") and node_type in _TS_READ_IDENT_TYPES
                  and scope_symbols and not _ts_is_member_property_leaf(node)):
                # The PROPERTY side of a member access (the trailing `.C`) is skipped here — the
                # member-access path branch below resolves `A.B.C` qualified instead, so a trailing
                # leaf can't wrong-bind a same-named constant when the head is an instance/local.
                try:
                    _ident = source_bytes[node.start_byte:node.end_byte].decode("utf-8", "replace")
                except Exception:
                    _ident = ""
                if _ident:
                    buffered_reads.append((scope_symbols[-1], _ident))
            elif current_scope_kind in ("function", "method") and node_type in _TS_MEMBER_ACCESS_TYPES and scope_symbols:
                # Member-access CONSTANT read: buffer the full qualified PATH (`Status.ACTIVE`,
                # `Outer.Inner.TOKEN`) so it resolves by EXACT qname match against a constant node.
                # This is what surfaces `graph_related.readers` for enum members + nested/type-level
                # constants accessed as `A.B.C` — including TS/JS, whose trailing `property_identifier`
                # the leaf-capture branch above never sees. Faithful by construction: the qualifier is
                # part of the key, so a same-leaf parameter / import / bare call can never match it.
                _mpath = _ts_member_access_path(node, source_bytes)
                if _mpath:
                    buffered_reads.append((scope_symbols[-1], _mpath))
            for child in getattr(node, "named_children", []):
                walk_definitions(child, scope_names, scope_kinds, scope_symbols, scope_signatures)

        # Wave 1p9qi (1p9qd): SQL bypasses the generic walker entirely — the
        # clause-aware statement analysis owns definitions AND references
        # (reads/writes edges with direction), retiring the substring-matched
        # import/call node selection + regex candidate fallback for SQL mode.
        # All downstream drains (buffered calls/reads/supertypes) stay empty.
        if mode == "sql":
            _sql_apply_file_extraction(
                tree.root_node,
                source_bytes,
                module_id=module_id,
                node_map=node_map,
                register_symbol=register_symbol,
                add_edge=add_edge,
            )
        else:
            walk_definitions(tree.root_node, [], [], [], [])
            # Wave 1p9q5: persist the Rust module-model facts on the file's
            # module node so `_build_rust_module_index` recovers them at finalize
            # (node-borne, so incremental merges rebuild from per-file fragments).
            if lang_key == "rust":
                if rust_mod_decls:
                    node_map[module_id]["rust_mod_decls"] = rust_mod_decls
                if rust_inline_mods:
                    node_map[module_id]["rust_inline_mods"] = rust_inline_mods
            # Wave 1p9qi (1p9qf): MyBatis mapper XML — statement-text capture
            # with the mapper namespace + statement id as the source marker
            # (resolved to the mapper interface at finalize).
            if mode == "markup" and rel_path.lower().endswith(".xml"):
                _mb_caps, _mb_dyn = _mybatis_mapper_captures(tree.root_node, source_bytes)
                for _mb_ns, _mb_id, _mb_sql in _mb_caps:
                    sql_capture_candidates.append(
                        (f"{_MYBATIS_SOURCE_PREFIX}{_mb_ns}::{_mb_id}", _mb_sql)
                    )
                _sql_dynamic[0] += _mb_dyn

        symbol_lookup: dict[str, str] = {}
        for symbol_id in defined_symbols:
            symbol_lookup[symbol_id.split("::", 1)[-1]] = symbol_id
        for name, items in simple_names.items():
            if len(items) == 1:
                symbol_lookup.setdefault(name, items[0])

        # Wave 131bt (1319s): symbol kind lookup for scope-aware construction
        # resolution. Maps a simple name to the kind of the symbol it resolves
        # to (e.g. "class", "function") so the construction helper can reject
        # PascalCase callees that resolve to non-class entities.
        symbol_lookup_kinds: dict[str, str] = {}
        for name, node_id in symbol_lookup.items():
            node_info = node_map.get(node_id) or {}
            kind_val = node_info.get("kind") or ""
            if kind_val:
                symbol_lookup_kinds[name] = str(kind_val)

        # Wave 1p9qi (1p9qg): drain the buffered entity classes now that
        # symbol_lookup exists (the same-file impostor checks consult it).
        _seen_orm_candidates: set[tuple[str, str]] = set()
        for _cls_id, _cls_node in orm_entity_class_nodes:
            if lang_key == "java":
                _orm_decl, _orm_dyn, _orm_conv = _java_entity_table_mapping(
                    _cls_node, source_bytes, symbol_lookup
                )
            else:
                _orm_decl, _orm_dyn, _orm_conv = _csharp_entity_table_mapping(
                    _cls_node, source_bytes, symbol_lookup
                )
            _orm_dynamic[0] += _orm_dyn
            _orm_convention[0] += _orm_conv
            if _orm_decl and (_cls_id, _orm_decl) not in _seen_orm_candidates:
                _seen_orm_candidates.add((_cls_id, _orm_decl))
                orm_entity_candidates.append((_cls_id, _orm_decl))

        # Wave 1p7dh: OTel TypeInstrumentation type-matcher targets, keyed by the
        # enclosing class node id — attached as the `instruments` property below.
        instruments_by_class: dict[str, set[str]] = {}

        # Wave 1p2q3 (1p2tz post-ship-4 perf): drain the buffered-call queue
        # using symbol_lookup + symbol_lookup_kinds. This replaces the prior
        # second AST walk (walk_calls) with a flat list traversal. The full
        # call-resolution logic (construction-resolved, per-language receiver-
        # type resolution, self-edge classification, EXTRACTED-with-import-
        # targets-promotion) runs per call exactly as before.
        for _src_symbol, _call_node, _call_node_type, _scope_signatures in buffered_calls:
            source_symbol = _src_symbol
            node = _call_node
            node_type = _call_node_type
            scope_signatures = _scope_signatures
            # Wave 1p7dh: capture OTel TypeInstrumentation target strings as the
            # enclosing class's `instruments` property. Scoped to the SPI
            # `typeMatcher()` method so method/parameter matchers in `transform()`
            # are excluded; the enclosing class id is the method's qname minus the
            # trailing `.typeMatcher` segment. Property only — no edge, no binding.
            if (
                lang_key == "java"
                and node_type == "method_invocation"
                and source_symbol.endswith(".typeMatcher")
            ):
                _aop = _java_aop_matcher_strings(node, source_bytes)
                if _aop is not None and _aop[0] in _AOP_TYPE_MATCHERS:
                    _cls_id = source_symbol.rsplit(".", 1)[0]
                    instruments_by_class.setdefault(_cls_id, set()).update(_aop[1])
            # Wave 1p7dh: Spring `Environment.getProperty("key")` /
            # `getRequiredProperty("key")` → config-read candidate (reader =
            # enclosing source_symbol). Captured by method name only; the finalize
            # pass's config-file + distinctiveness + unique-match gates bound it.
            if lang_key == "java" and node_type == "method_invocation":
                _cfg_key = _java_config_getter_key(node, source_bytes)
                if _cfg_key:
                    config_read_candidates.append((source_symbol, _cfg_key))
            # Wave 1p9qi (1p9qf): embedded-SQL capture at known call sinks
            # (Java JDBC prepare*/JdbcTemplate; C# SqlCommand/Dapper/EF raw).
            # Origin-checked where the receiver type is resolvable (see the
            # capture-section convention comment); sniff-gated; dynamic
            # arguments refused and counted.
            if lang_key == "java" and node_type == "method_invocation":
                _cap_sql, _cap_dyn = _java_call_sql_capture(node, source_bytes, symbol_lookup)
                if _cap_sql:
                    sql_capture_candidates.append((source_symbol, _cap_sql))
                _sql_dynamic[0] += _cap_dyn
            elif lang_key == "csharp" and node_type in (
                "invocation_expression", "object_creation_expression"
            ):
                _cap_sql, _cap_dyn = _csharp_call_sql_capture(node, node_type, source_bytes, symbol_lookup)
                if _cap_sql:
                    sql_capture_candidates.append((source_symbol, _cap_sql))
                _sql_dynamic[0] += _cap_dyn
                # Wave 1p9qi (1p9qg): EF fluent `ToTable("…")` mapping sink —
                # the entity type comes from the `.Entity<T>()` chain or the
                # `EntityTypeBuilder<T>` parameter (positive origin by
                # construction; impostor `ToTable` on any other receiver
                # never fires).
                if node_type == "invocation_expression":
                    _tt_marker, _tt_decl, _tt_dyn = _csharp_totable_capture(node, source_bytes)
                    if _tt_marker and _tt_decl and (_tt_marker, _tt_decl) not in _seen_orm_candidates:
                        _seen_orm_candidates.add((_tt_marker, _tt_decl))
                        orm_entity_candidates.append((_tt_marker, _tt_decl))
                    _orm_dynamic[0] += _tt_dyn
            # Wave 131bt (1319s): construction-call resolution runs FIRST.
            construction_target = _resolve_construction_target(
                node, node_type, source_bytes, symbol_lookup, symbol_lookup_kinds, lang_key
            )
            if construction_target is not None:
                add_edge(source_symbol, construction_target, "calls", confidence="CONSTRUCTION_RESOLVED")
                continue
            # Wave 13129 (1312l + 13194): per-language receiver-type resolution.
            java_resolved_target: str | None = None
            if lang_key == "java" and node_type == "method_invocation":
                java_resolved_target = _resolve_java_call_target(
                    node, source_bytes, symbol_lookup,
                    static_import_members=java_static_members,
                    static_wildcard_imports=java_static_wildcards,
                )
            elif lang_key == "kotlin" and node_type == "call_expression":
                java_resolved_target = _resolve_kotlin_call_target(node, source_bytes, symbol_lookup)
            elif lang_key == "csharp" and node_type == "invocation_expression":
                java_resolved_target = _resolve_csharp_call_target(node, source_bytes, symbol_lookup)
            elif lang_key == "go" and node_type == "call_expression":
                java_resolved_target = _resolve_go_call_target(node, source_bytes, symbol_lookup)
            elif lang_key == "rust" and node_type == "call_expression":
                java_resolved_target = _resolve_rust_call_target(node, source_bytes, symbol_lookup)
            elif lang_key == "scala" and node_type == "call_expression":
                java_resolved_target = _resolve_scala_call_target(node, source_bytes, symbol_lookup)
            elif lang_key == "swift" and node_type == "call_expression":
                java_resolved_target = _resolve_swift_call_target(node, source_bytes, symbol_lookup)
            elif lang_key in ("typescript", "javascript") and node_type == "call_expression":
                java_resolved_target = _resolve_ts_call_target(node, source_bytes, symbol_lookup, import_targets)
            elif lang_key == "php" and node_type in ("member_call_expression", "scoped_call_expression"):
                java_resolved_target = _resolve_php_call_target(node, source_bytes, symbol_lookup)
            if java_resolved_target is not None:
                # Wave 1p2q3 (1p2td): classify self-edges on overloadable langs.
                self_kind: str | None = None
                if (
                    lang_key in _OVERLOAD_LANGUAGES
                    and source_symbol == java_resolved_target
                ):
                    call_sig = _extract_call_signature(node, source_bytes, lang_key)
                    enclosing_sig = scope_signatures[-1] if scope_signatures else None
                    sigs_for_node = overload_signatures.get(source_symbol, set())
                    self_kind = _classify_self_edge(call_sig, enclosing_sig, sigs_for_node)
                add_edge(
                    source_symbol, java_resolved_target, "calls",
                    confidence="RECEIVER_RESOLVED", self_edge_kind=self_kind,
                )
            else:
                for target in _ts_relation_candidates(node, source_bytes, "call", mode, profile):
                    resolved = _ts_resolve_target(target, symbol_lookup, import_aliases)
                    # Wave 1p2q3 (1p2tz post-ship): direct-function-call import_targets promotion.
                    confidence_for_edge = "EXTRACTED"
                    if (
                        lang_key in ("typescript", "javascript")
                        and resolved.startswith("external::")
                        and import_targets
                    ):
                        clean_name = _ts_clean_name(target)
                        walked = import_targets.get(clean_name)
                        if walked and not walked.startswith("external::"):
                            resolved = f"{walked}::{clean_name}"
                            confidence_for_edge = "RECEIVER_RESOLVED"
                    # Wave 1p2q3 (1p2tz post-ship-5) + 1p7dg: symbol-table
                    # promotion. When `_ts_resolve_target` bound to a project node
                    # directly (intra-file binding via local symbol_lookup, or a
                    # cross-file unambiguous unique simple-name match), the target
                    # is high-confidence — exactly one definition could have
                    # matched — but the edge landed EXTRACTED, invisible to the
                    # `receiver_resolved` attribution. v23 promoted this for TS/JS
                    # only ("widening is a follow-up if field data warrants it").
                    # Wave 1p7dg: the AC-1 spike warranted it — Java (247) and
                    # Swift (761) carry the same under-tagged same-file bucket on
                    # real graphs. Widened to ALL languages: this fires only in the
                    # `else` branch (the per-language receiver resolver already
                    # returned None) on an already-bound non-`external::` target,
                    # so the bind is UNCHANGED (no new wrong-twin risk) and the
                    # uniqueness guarantee is the same `_ts_resolve_target` /
                    # symbol_lookup match used for TS/JS — a confidence relabel only.
                    elif resolved and not resolved.startswith("external::"):
                        confidence_for_edge = "RECEIVER_RESOLVED"
                    self_kind = None
                    if (
                        lang_key in _OVERLOAD_LANGUAGES
                        and source_symbol == resolved
                    ):
                        call_sig = _extract_call_signature(node, source_bytes, lang_key)
                        enclosing_sig = scope_signatures[-1] if scope_signatures else None
                        sigs_for_node = overload_signatures.get(source_symbol, set())
                        self_kind = _classify_self_edge(call_sig, enclosing_sig, sigs_for_node)
                    add_edge(
                        source_symbol, resolved, "calls",
                        confidence=confidence_for_edge, self_edge_kind=self_kind,
                    )

        # Wave 1p9qh (1p9qa): drain buffered supertype facts → `extends` /
        # `implements` edges. A same-file supertype binds directly at
        # RECEIVER_RESOLVED (declaration-derived; kind-gated so a same-named
        # same-file function can never capture it). Everything else emits the
        # qualified-as-declared `external::<Name>` target at EXTRACTED — the
        # cross-file pass binds a unique project candidate through the
        # import/wildcard/unique-candidate machinery (with the standard
        # exact-unique promotion) or refuses and stays external.
        for _sup_src, _sup_name, _sup_rel in buffered_supertypes:
            _sup_target = symbol_lookup.get(_sup_name)
            if (
                _sup_target
                and _sup_target != _sup_src
                and (node_map.get(_sup_target) or {}).get("kind") == "class"
            ):
                add_edge(_sup_src, _sup_target, _sup_rel, confidence="RECEIVER_RESOLVED")
            else:
                add_edge(_sup_src, f"external::{_sup_name}", _sup_rel, confidence="EXTRACTED")

        # Wave 1p2q3 (1p2td): surface per-overload param_signatures on the
        # merged node so consumers can inspect the full overload set directly
        # without re-parsing the source.
        for nid, sigs in overload_signatures.items():
            if nid in node_map and len(sigs) > 0:
                node_map[nid]["param_signatures"] = sorted(sigs)

        # Wave 1p7dh: attach OTel `typeMatcher()` target strings as the
        # `instruments` property on the enclosing instrumentation class node —
        # descriptive metadata ("what does this instrument"), not a binding edge.
        # When the class collapsed into the file node (`collapsed_pair`, 1316l —
        # a basename-matching dominant class), the qualified `file::Class` id is
        # absent; the surviving carrier is the file/module node, so fall back to it.
        for _cls_id, _targets in instruments_by_class.items():
            _carrier = _cls_id if _cls_id in node_map else _cls_id.split("::", 1)[0]
            if _carrier in node_map and _targets:
                node_map[_carrier]["instruments"] = sorted(_targets)

        # Wave 1p4ls: resolve buffered identifier reads → `reads` edges (reader function → constant).
        # symbol_lookup uniqueness is the cross-module faithfulness gate (an ambiguous same-name
        # constant is absent → stays unresolved, never a wrong twin); const_node_ids restricts the
        # target to constants only (never a coincidental same-name function/class).
        _seen_reads: set[tuple[str, str]] = set()
        for _reader, _ident in buffered_reads:
            if "." in _ident and _ident.split(".", 1)[0] in func_locals.get(_reader, ()):
                continue  # member-access head is a function-local/param shadow → reads the local, not the const (F4)
            _target = symbol_lookup.get(_ident)
            if _target is not None and _target in const_node_ids and _target != _reader:
                # A DOTTED ident is a member-access read (`Outer.Inner.TOKEN`); it must match the
                # constant's FULL qualified name, not a `_simple_name` PARTIAL key (`config.timeout`
                # for a const `Outer.config.timeout`) — else an instance/local `owner.leaf` access
                # wrong-binds a 1-level-nested const (member-access review F1). Bare-leaf reads (no
                # dot) keep the unique-simple-name path unchanged.
                if "." in _ident and _target.split("::", 1)[-1] != _ident:
                    continue
                _key = (_reader, _target)
            elif _target is None and _ident in import_aliases:
                # Wave 1p4ls: cross-module imported-constant candidate — finalize() resolves it to a
                # unique constant (kind-checked) or drops it. Most imports are non-constant → dropped.
                _key = (_reader, f"external::{import_aliases[_ident]}")
            else:
                continue
            if _key in _seen_reads:
                continue
            _seen_reads.add(_key)
            add_edge(_key[0], _key[1], GRAPH_READS_RELATION, confidence="EXTRACTED")

        return {
            "kind": "code",
            "path": rel_path,
            "source_hash": _sha256_text(source_text),
            "nodes": sorted(node_map.values(), key=lambda item: str(item.get("id") or "")),
            "edges": sorted(
                edge_map.values(),
                key=lambda item: (
                    str(item.get("source") or ""),
                    str(item.get("target") or ""),
                    str(item.get("relation") or ""),
                ),
            ),
            "defined_symbols": defined_symbols,
            "simple_names": {name: ids for name, ids in simple_names.items()},
            "mentioned_symbols": [],
            "config_read_candidates": config_read_candidates,  # Wave 1p7dh (Java @Value/getProperty)
            "sql_capture_candidates": sql_capture_candidates,  # Wave 1p9qi (1p9qf): embedded-SQL sink captures
            "sql_capture_dynamic": _sql_dynamic[0],  # Wave 1p9qf: dynamic-SQL refusals (visible gap)
            "orm_entity_candidates": orm_entity_candidates,  # Wave 1p9qi (1p9qg): declared entity→table mappings
            "orm_entity_dynamic": _orm_dynamic[0],  # Wave 1p9qg: non-literal name refusals
            "orm_entity_convention": _orm_convention[0],  # Wave 1p9qg: @Entity-with-no-declared-name refusals
            "di_signals": _ts_di_signals,  # Wave 1p9q7: AST-anchored NestJS/Inversify DI signals (TS only)
        }

    def _extract_code_artifact(self, rel_path: str, source_text: str) -> dict[str, Any]:
        suffix = Path(rel_path).suffix.lower()
        if suffix == ".py":
            artifact = self._extract_python_artifact(rel_path, source_text)
        elif suffix in {".json", ".jsonc"}:
            artifact = self._extract_json_artifact(rel_path, source_text)
        elif suffix in {".properties", ".yml", ".yaml"}:
            artifact = self._extract_config_artifact(rel_path, source_text)
        else:
            lang_key = _ts_language_key_for_path(rel_path)
            if lang_key:
                artifact = self._extract_tree_sitter_artifact(rel_path, source_text, lang_key)
                if artifact is None:
                    if _over_ts_parse_cap(source_text):
                        # Wave 1p9q6: the file is over the AST parse cap (but
                        # under the walk cap that would have dropped it). Rather
                        # than contribute zero graph nodes (a silent hole),
                        # degrade to a bounded line scan recovering imports +
                        # top-level definitions. This precedes the JS/TS regex
                        # fallback deliberately: that fallback has no size guard
                        # and would run unbounded over a multi-MB minified file.
                        artifact = self._extract_line_scan_artifact(rel_path, source_text, lang_key)
                    elif lang_key in {"javascript", "typescript"}:
                        artifact = self._extract_js_artifact(rel_path, source_text)
                    else:
                        artifact = self._empty_code_artifact(rel_path, source_text)
            elif suffix in {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx"}:
                artifact = self._extract_js_artifact(rel_path, source_text)
            else:
                artifact = {
                    "kind": "code",
                    "path": rel_path,
                    "source_hash": _sha256_text(source_text),
                    "nodes": [_node(rel_path, _path_term(rel_path), "module", rel_path, "1:0", layer=self.layer)],
                    "edges": [],
                    "defined_symbols": [],
                    "simple_names": {},
                    "mentioned_symbols": [],
                }
        try:
            di_mod = _load_di_signals_module()
            # Wave 1p9q7: the language extractors (Python `ast`, TS tree-sitter)
            # may have ALREADY populated AST-anchored DI signals on the artifact.
            # MERGE them with the text-based collector (Java/Kotlin/C#) rather
            # than overwriting — a Java text-signal and a Python AST-signal must
            # both survive. The text collector returns [] for Python/TS, so the
            # merge is order-independent and never double-counts.
            extractor_signals = artifact.get("di_signals") or []
            text_signals = di_mod.collect_di_signals(rel_path, source_text)
            artifact["di_signals"] = list(extractor_signals) + list(text_signals)
        except Exception:
            artifact.setdefault("di_signals", [])
        return artifact

    # ------------------------------------------------------------------
    # Doc extraction
    # ------------------------------------------------------------------

    def _extract_doc_artifact(
        self,
        rel_path: str,
        source_text: str,
        symbol_terms: dict[str, set[str]],
        matcher: tuple[dict[str, set[str]], re.Pattern[str] | None, dict[str, set[str]]] | None = None,
    ) -> dict[str, Any]:
        kind = _kind_for_path(rel_path)
        node_kind = "seed" if kind == "seed" else "doc"
        module_id = rel_path
        nodes = [
            _node(module_id, _path_term(rel_path), node_kind, rel_path, "1:0", layer=self.layer)
        ]
        edges: list[dict[str, Any]] = []
        matched_terms: set[str] = set()
        mentioned_set: set[str] = set()

        if matcher is None:
            matcher = self._compile_doc_matcher(symbol_terms)
        simple_lower, complex_pattern, complex_lower = matcher

        # Only scan inline backtick spans for simple keyword matches (skip JSON/config fences).
        inline_ctx = _extract_inline_code_contexts(source_text)
        inline_terms = _extract_doc_match_terms(inline_ctx)
        code_ctx = _extract_code_contexts(source_text)

        for lower_term, targets in simple_lower.items():
            if lower_term not in inline_terms:
                continue
            matched_terms.add(lower_term)
            filtered = _filter_doc_code_targets(lower_term, targets)
            for target in filtered:
                if target in mentioned_set:
                    continue
                mentioned_set.add(target)
                edges.append(
                    _edge(
                        module_id,
                        target,
                        "doc_references_code",
                        confidence=_doc_code_reference_confidence(lower_term, target, match_count=len(filtered)),
                        evidence=lower_term,
                    )
                )

        # Dotted/complex terms: one combined regex pass over all code context.
        if complex_pattern:
            for m in complex_pattern.finditer(code_ctx):
                key = m.group().lower()
                targets = complex_lower.get(key)
                if not targets:
                    continue
                matched_terms.add(key)
                filtered = _filter_doc_code_targets(key, targets)
                for target in filtered:
                    if target in mentioned_set:
                        continue
                    mentioned_set.add(target)
                    edges.append(
                        _edge(
                            module_id,
                            target,
                            "doc_references_code",
                            confidence=_doc_code_reference_confidence(key, target, match_count=len(filtered)),
                            evidence=key,
                        )
                    )

        # Explicit markdown links and backtick file paths to other known files.
        linked_paths: set[str] = set()
        for linked_path in _extract_doc_links(source_text, rel_path, self._current_paths):
            linked_paths.add(linked_path)
        for linked_path in _extract_doc_backtick_paths(source_text, rel_path, self._current_paths):
            linked_paths.add(linked_path)
        for linked_path in sorted(linked_paths):
            edges.append(_edge(module_id, linked_path, "doc_references_doc", confidence="EXTRACTED"))

        mentioned = sorted(mentioned_set)
        return {
            "kind": node_kind,
            "path": rel_path,
            "source_hash": _sha256_text(source_text),
            "nodes": nodes,
            "edges": edges,
            "defined_symbols": [],
            "simple_names": {},
            "mentioned_symbols": mentioned,
            "matched_terms": sorted(matched_terms),
            "source_text": source_text,
        }

    # ------------------------------------------------------------------
    # Finalization
    # ------------------------------------------------------------------

    def _is_doc_path(self, rel_path: str) -> bool:
        return _kind_for_path(rel_path) in {"doc", "seed"}

    def _build_symbol_terms(self, artifacts: dict[str, dict[str, Any]]) -> dict[str, set[str]]:
        terms: dict[str, set[str]] = {}
        for artifact in artifacts.values():
            if artifact.get("kind") != "code":
                continue
            for node in artifact.get("nodes", []):
                if not isinstance(node, dict):
                    continue
                node_id = str(node.get("id") or "")
                if not node_id:
                    continue
                label = str(node.get("label") or "")
                if label:
                    terms.setdefault(label, set()).add(node_id)
                qname = node_id.split("::", 1)[-1]
                if qname and qname != label:
                    terms.setdefault(qname, set()).add(node_id)
                simple = _simple_name(node_id)
                if simple and simple != label and simple != qname and simple not in _STOP_TERMS:
                    terms.setdefault(simple, set()).add(node_id)
                if _is_module_graph_node(node):
                    source_file = str(node.get("source_file") or node_id)
                    stem = _path_term(source_file)
                    if stem and stem not in _STOP_TERMS:
                        terms.setdefault(stem, set()).add(node_id)
        return terms

    _SIMPLE_TERM_RE = re.compile(r"^[A-Za-z0-9_]+$")

    def _compile_doc_matcher(
        self, symbol_terms: dict[str, set[str]]
    ) -> tuple[dict[str, set[str]], re.Pattern[str] | None, dict[str, set[str]]]:
        """Build fast lookup structures for doc symbol scanning.

        Returns (simple_lower, complex_pattern, complex_lower) where:
        - simple_lower: lowercase pure-identifier terms → node id sets
        - complex_pattern: compiled combined regex for dotted/special terms (or None)
        - complex_lower: lowercase complex terms → node id sets
        """
        simple_lower: dict[str, set[str]] = {}
        complex_lower: dict[str, set[str]] = {}
        for term, ids in symbol_terms.items():
            if not term or term in _DOC_MATCH_STOP_TERMS:
                continue
            if len(term) < _MIN_DOC_MATCH_TERM_LEN:
                continue
            lower = term.lower()
            if self._SIMPLE_TERM_RE.match(term):
                simple_lower.setdefault(lower, set()).update(ids)
            else:
                complex_lower.setdefault(lower, set()).update(ids)
        complex_pattern: re.Pattern[str] | None = None
        if complex_lower:
            sorted_terms = sorted(complex_lower.keys(), key=len, reverse=True)
            complex_pattern = re.compile(
                r"\b(?:" + "|".join(re.escape(t) for t in sorted_terms) + r")\b",
                re.IGNORECASE,
            )
        return simple_lower, complex_pattern, complex_lower

    def _payload_binding_ok(self, store: GraphStateStore) -> str:
        """Return the bound payload fingerprint when the on-disk payload file
        matches the store's recorded binding (size + mtime_ns + bound marker),
        else ``""``.

        Wave 1p9q3 (1p9q2) crash-consistency probe: the payload artifact and
        the SQLite store cannot commit atomically *together*, so the store
        records which payload it vouches for. Any mismatch (torn window,
        manual deletion, out-of-band rewrite) degrades to a loud full re-merge
        — never a silently inconsistent graph.
        """
        meta = store.meta_all()
        if meta.get("payload_stat_state") != "bound":
            return ""
        fingerprint = str(meta.get("payload_fingerprint") or "")
        if not fingerprint:
            return ""
        try:
            st = self.graph_path.stat()
        except OSError:
            return ""
        if str(st.st_size) != meta.get("payload_size"):
            return ""
        if str(st.st_mtime_ns) != meta.get("payload_mtime_ns"):
            return ""
        return fingerprint

    def finalize(self) -> dict[str, Any]:
        """Merge per-file artifacts into the graph payload.

        Wave 1p9q3 (1p9q2) rewrite: one unified pipeline serves both the full
        merge and the incremental delta merge over a persistent merge state
        (the ``merge_state`` blob in the per-file store):

        - **Zero-change fast path** — nothing pending, nothing removed, and the
          store vouches for the on-disk payload: return the existing payload
          without any merge work or artifact rewrite.
        - **Incremental** — per-file fragments for changed files are recomputed
          from their fresh artifacts; untouched files' stored fragments are
          reused, EXCEPT edges whose resolution consults a candidate-index key
          in the symbol delta (names whose candidate set may have changed —
          computed from the old+new nodes of changed/removed files plus the
          DI-synth node delta). Those re-resolve against the fresh indexes, so
          promotion (external → bound) and demotion (bound → external) both
          propagate into untouched files. Fragment edges carry provenance
          (`_x`/`_c`/`_d`) so their raw form is recoverable without re-reading
          any unchanged file's record — state I/O touches only changed rows.
        - **Full merge** — missing/inconsistent merge state (or a fresh/reset
          store) loads every stored record and recomputes all fragments; the
          same code path, with everything treated as changed. This is the
          differential oracle path and the loud degrade target.

        Equivalence invariant: an incremental build produces the same node
        set, edge-key set (incl. confidences), and ``input_fingerprint`` as a
        from-scratch build of the same tree (enforced by the randomized
        differential harness in the test suite).

        Persist order + crash windows (AC-5): store commit (rows + sidecar +
        binding meta with ``payload_stat_state='pending'``) → payload write →
        binding stat commit. A crash in any window leaves the binding either
        stale or pending; the next build detects the mismatch and performs a
        loud full re-merge from the (newer-or-equal) committed rows — a lost
        build is re-buildable, a torn one is detectable, and a wrong graph is
        never served silently.
        """
        import time as _time

        merge_started = _time.monotonic()
        store = self._ensure_store()
        reads_before = store.record_reads
        writes_before = store.record_writes
        blob_reads_before = store.blob_reads
        blob_writes_before = store.blob_writes
        blob_bytes_before = store.blob_bytes_written
        stats: dict[str, Any] = {
            "mode": "incremental",
            "files_changed": len(self.pending_code) + len(self.pending_doc_text),
            "files_removed": 0,
            "symbols_invalidated": 0,
            "edges_reresolved": 0,
        }

        current_paths = set(self._current_paths)
        known_paths = store.paths_with_hashes()

        # Files that existed in the prior graph state but are gone now (deleted
        # or renamed away). Edges from surviving files into these paths are
        # stale and must be pruned even when the referring file did not change.
        removed_paths = set(known_paths) - current_paths
        # Purge any doc artifacts cached from paths that are now excluded.
        excluded_docs = {
            rel
            for rel in known_paths
            if rel not in removed_paths
            and _kind_for_path(rel) in {"doc", "seed"}
            and self._is_doc_scan_excluded(rel)
        }
        drop_paths = removed_paths | excluded_docs
        stats["files_removed"] = len(removed_paths)

        # --- Zero-change fast path (Req-1): no merge work, no artifact rewrite.
        if not self.pending_code and not self.pending_doc_text and not drop_paths:
            bound_fp = self._payload_binding_ok(store)
            if (
                bound_fp
                and store.meta_all().get("merge_state_format") == _MERGE_STATE_FORMAT
            ):
                payload = _read_json(self.graph_path, None)
                if (
                    isinstance(payload, dict)
                    and str(payload.get("input_fingerprint") or "") == bound_fp
                ):
                    stats["mode"] = "zero-change"
                    stats["merge_ms"] = int((_time.monotonic() - merge_started) * 1000)
                    stats["state_reads"] = store.record_reads - reads_before
                    stats["state_writes"] = store.record_writes - writes_before
                    stats["blob_reads"] = store.blob_reads - blob_reads_before
                    stats["blob_writes"] = store.blob_writes - blob_writes_before
                    stats["blob_bytes"] = store.blob_bytes_written - blob_bytes_before
                    payload["merge_stats"] = stats
                    return payload
            # Fall through: the binding is inconsistent — re-merge loudly below
            # rather than serve a payload the store cannot vouch for.

        # --- Acquire the persistent merge state. ---
        merge_files: dict[str, dict[str, Any]] = {}
        prev_di_synth_nodes: list[dict[str, Any]] = []
        incremental = False
        merge_state = store.get_blob("merge_state")
        if (
            isinstance(merge_state, dict)
            and str(merge_state.get("format") or "") == _MERGE_STATE_FORMAT
            and not merge_state.get("locality_violation")
            and isinstance(merge_state.get("files"), dict)
            and str(merge_state.get("payload_fingerprint") or "")
            and self._payload_binding_ok(store)
            == str(merge_state.get("payload_fingerprint") or "")
        ):
            merge_files = merge_state["files"]
            prev_di = merge_state.get("di_synth_nodes")
            prev_di_synth_nodes = prev_di if isinstance(prev_di, list) else []
            incremental = True
        else:
            stats["mode"] = "full-merge"

        # Artifacts whose fragments must be (re)computed this build.
        recompute_artifacts: dict[str, dict[str, Any]] = {}
        if not incremental:
            pending_all = set(self.pending_code) | set(self.pending_doc_text)
            stored_only = 0
            for rel, record in store.iter_records():
                if rel in drop_paths:
                    continue
                artifact = record.get("artifact")
                if isinstance(artifact, dict):
                    recompute_artifacts[rel] = artifact
                    if rel not in pending_all:
                        stored_only += 1
            if stored_only:
                # Loud degrade (AC-5/Req-6): a usable store without a usable
                # merge state means an interrupted or pre-upgrade build; the
                # full re-merge below reconstructs everything from the rows.
                print(
                    f"build_index: graph merge state missing or inconsistent for "
                    f"{self.layer} layer — performing a full re-merge of "
                    f"{stored_only} stored file record(s)",
                    file=sys.stderr,
                    flush=True,
                )

        # --- Per-file delta bookkeeping (symbol-scoped invalidation inputs). ---
        changed_code_symbols: set[str] = set()
        # Symbol IDs that existed before but no longer do (renamed/removed
        # within a surviving file). Edges pointing at these are stale.
        removed_symbols: set[str] = set()
        # Old + new nodes of changed/removed files: the candidate-index keys
        # they contribute form the symbol delta for scoped re-resolution.
        # Kept PER-SIDE: _build_candidate_indexes keeps one winner per
        # (file, simple name), so a merged old+new subset drops the loser
        # node's qualified keys from the delta even though each node is a
        # winner in its own epoch's real index — a same-file depth swap
        # (top-level CONST -> Class.CONST) would then escape scope (b) for
        # `reads` edges in untouched files (adversarial faithfulness finding).
        delta_nodes_old: list[dict[str, Any]] = []
        delta_nodes_new: list[dict[str, Any]] = []

        if incremental:
            for rel in set(self.pending_code) | drop_paths:
                old_entry = merge_files.get(rel)
                if isinstance(old_entry, dict):
                    delta_nodes_old.extend(
                        n for n in old_entry.get("nodes", []) if isinstance(n, dict)
                    )

        # Remove vanished/excluded files from the merge state first.
        for rel in drop_paths:
            merge_files.pop(rel, None)

        # Track per-file row writes for the single store transaction.
        row_puts: dict[str, dict[str, Any]] = {}

        # Apply changed code artifacts immediately (same order as the former
        # pipeline: code first, docs against the refreshed symbol terms).
        for rel, payload_entry in self.pending_code.items():
            new_artifact = payload_entry["artifact"]
            if incremental:
                old_defs = set(
                    (merge_files.get(rel) or {}).get("defined_symbols") or []
                )
            else:
                old_defs = set(
                    (recompute_artifacts.get(rel) or {}).get("defined_symbols") or []
                )
            new_defs = set(new_artifact.get("defined_symbols") or [])
            changed_code_symbols.update(old_defs.symmetric_difference(new_defs))
            removed_symbols.update(old_defs - new_defs)
            recompute_artifacts[rel] = new_artifact
            if incremental:
                delta_nodes_new.extend(
                    n for n in new_artifact.get("nodes", []) if isinstance(n, dict)
                )
            row_puts[rel] = {
                "source_hash": payload_entry["source_hash"],
                "artifact": new_artifact,
            }

        def _artifacts_view() -> dict[str, dict[str, Any]]:
            # Accessor-compatible mapping over the merge inputs: stored entries
            # for untouched files, fresh artifacts for recomputed ones (both
            # carry `kind`/`nodes`/`mentioned_symbols`/... keys).
            view: dict[str, dict[str, Any]] = dict(merge_files)
            view.update(recompute_artifacts)
            return view

        # Rebuild symbol terms from the current code node set before docs.
        symbol_terms = self._build_symbol_terms(_artifacts_view())
        matcher = self._compile_doc_matcher(symbol_terms)

        # Changed docs are rescanned directly from their current text.
        for rel, source_text in self.pending_doc_text.items():
            artifact = self._extract_doc_artifact(rel, source_text, symbol_terms, matcher)
            recompute_artifacts[rel] = artifact
            row_puts[rel] = {
                "source_hash": artifact["source_hash"],
                "artifact": artifact,
            }

        # Any unchanged doc that mentioned a changed symbol is now stale.
        impacted_docs: list[str] = []
        if changed_code_symbols:
            for rel, entry in _artifacts_view().items():
                if entry.get("kind") not in {"doc", "seed"}:
                    continue
                mentioned = set(entry.get("mentioned_symbols") or [])
                if mentioned.intersection(changed_code_symbols):
                    impacted_docs.append(rel)

        for rel in impacted_docs:
            path = self.root / rel
            if not path.exists():
                merge_files.pop(rel, None)
                recompute_artifacts.pop(rel, None)
                row_puts.pop(rel, None)
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            artifact = self._extract_doc_artifact(rel, text, symbol_terms, matcher)
            recompute_artifacts[rel] = artifact
            row_puts[rel] = {
                "source_hash": artifact["source_hash"],
                "artifact": artifact,
            }

        # The updated doc scans may have consumed new symbols; if any docs were
        # refreshed, rebuild the symbol term map once more and rescan those
        # docs for stable output.
        if impacted_docs:
            symbol_terms = self._build_symbol_terms(_artifacts_view())
            matcher = self._compile_doc_matcher(symbol_terms)
            for rel in impacted_docs:
                if rel not in recompute_artifacts and rel not in merge_files:
                    continue
                path = self.root / rel
                try:
                    text = path.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                new_artifact = self._extract_doc_artifact(rel, text, symbol_terms, matcher)
                recompute_artifacts[rel] = new_artifact
                row_puts[rel] = {
                    "source_hash": new_artifact["source_hash"],
                    "artifact": new_artifact,
                }

        # Keep only current files in the merge state.
        for rel in list(merge_files.keys()):
            if rel not in current_paths:
                merge_files.pop(rel, None)

        # --- Build merge entries for every recomputed file. ---
        locality_violation = False
        for rel, artifact in recompute_artifacts.items():
            if rel not in current_paths:
                row_puts.pop(rel, None)
                continue
            entry: dict[str, Any] = {
                "kind": str(artifact.get("kind") or ""),
                "nodes": [n for n in artifact.get("nodes", []) if isinstance(n, dict)],
                # Raw edges for now; resolved into fragment form below.
                "edges": [e for e in artifact.get("edges", []) if isinstance(e, dict)],
            }
            for summary_key in (
                "defined_symbols",
                "mentioned_symbols",
                "config_read_candidates",
                "sql_capture_candidates",  # Wave 1p9qi (1p9qf): embedded-SQL captures
                "sql_capture_dynamic",  # Wave 1p9qf: refusal count rides the fragment
                "orm_entity_candidates",  # Wave 1p9qi (1p9qg): entity→table mapping captures
                "orm_entity_dynamic",  # Wave 1p9qg: dynamic-name refusal count
                "orm_entity_convention",  # Wave 1p9qg: convention-refusal count
                "di_signals",
            ):
                value = artifact.get(summary_key)
                if value:
                    entry[summary_key] = value
            for node in entry["nodes"]:
                node_id = str(node.get("id") or "")
                if node_id.startswith("external::"):
                    # Shared import-endpoint nodes: many files legitimately
                    # emit the same `external::<module>` node. Safe for the
                    # delta merge because the node map is re-unioned from all
                    # files' node lists every build (first-wins in sorted-file
                    # order, exactly like the full merge) — removing one
                    # file's copy never removes another contributor's.
                    continue
                file_part = node_id.split("::", 1)[0] if "::" in node_id else node_id
                if file_part != rel:
                    # Per-file removability invariant violated: this node could
                    # not be cleanly retracted when its file changes. Flag the
                    # merge state so every subsequent build takes the full
                    # re-merge path (correct, just not incremental) until the
                    # extractor is fixed.
                    locality_violation = True
            merge_files[rel] = entry

        # --- Assemble the merged node map (sorted-file, first-id-wins). ---
        node_map: dict[str, dict[str, Any]] = {}
        for rel in sorted(merge_files.keys()):
            for node in merge_files[rel].get("nodes", []):
                if not isinstance(node, dict):
                    continue
                node_id = str(node.get("id") or "")
                if node_id and node_id not in node_map:
                    # Copy so downstream analytics flags never contaminate the
                    # persisted per-file state (flags are recomputed fresh each
                    # build; stripping keeps incremental == from-scratch).
                    fresh = dict(node)
                    for flag in _ANALYTICS_NODE_FLAGS:
                        fresh.pop(flag, None)
                    node_map[node_id] = fresh

        # --- DI signal resolution (may synthesize type nodes). ---
        di_edge_items: list[tuple[tuple[str, str, str, str], dict[str, Any]]] = []
        di_synth_nodes: list[dict[str, Any]] = []
        try:
            di_mod = _load_di_signals_module()
            pre_di_ids = set(node_map)
            # Deterministic input order (wave 1p9q2): the DI pass's node picks
            # are candidate-list-order sensitive; feed artifacts sorted so full
            # and incremental builds agree on synthesized node ids.
            di_view = {rel: merge_files[rel] for rel in sorted(merge_files.keys())}
            for edge in di_mod.resolve_di_edges(di_view, node_map):
                if not isinstance(edge, dict):
                    continue
                key = (
                    str(edge.get("source") or ""),
                    str(edge.get("target") or ""),
                    str(edge.get("relation") or ""),
                    str(edge.get("confidence") or ""),
                )
                if not all(key):
                    continue
                di_edge_items.append((key, edge))
                for endpoint in (key[0], key[1]):
                    if endpoint and endpoint not in node_map:
                        file_part = endpoint.split("::")[0] if "::" in endpoint else endpoint
                        label = endpoint.split("::")[-1]
                        node_map[endpoint] = _node(
                            endpoint,
                            label,
                            "class" if "::" in endpoint else "module",
                            file_part,
                            "1:0",
                            layer=self.layer,
                        )
            di_synth_nodes = [
                node_map[nid] for nid in sorted(set(node_map) - pre_di_ids)
            ]
        except Exception:
            pass

        # --- Cross-file resolution context (candidate indexes; wave 130ol+). ---
        simple_name_index, qualified_index, cs_file_ns, java_pkg_by_file, rust_module_index = _build_candidate_indexes(node_map)

        # Raw edge views per file (fragment provenance makes untouched files'
        # raw edges recoverable without touching their store rows).
        raw_edges_by_file: dict[str, list[dict[str, Any]]] = {}
        for rel, entry in merge_files.items():
            if rel in recompute_artifacts:
                raw_edges_by_file[rel] = entry.get("edges", [])
            else:
                raw_edges_by_file[rel] = [
                    _raw_fragment_edge(e) for e in entry.get("edges", [])
                ]

        imports_by_file, wildcard_imports_by_file = _build_imports_by_file(
            (
                str(e.get("source") or ""),
                str(e.get("target") or ""),
                str(e.get("relation") or ""),
                str(e.get("confidence") or ""),
            )
            for edges in raw_edges_by_file.values()
            for e in edges
        )
        ctx = {
            "node_map": node_map,
            "simple_name_index": simple_name_index,
            "qualified_index": qualified_index,
            "imports_by_file": imports_by_file,
            "wildcard_imports_by_file": wildcard_imports_by_file,
            "cs_file_ns": cs_file_ns,
            "java_pkg_by_file": java_pkg_by_file,
            "rust_module_index": rust_module_index,
        }

        # --- Symbol delta (Req-2): candidate-index keys whose candidate set
        # may have changed. Any edge consulting one of these keys re-resolves.
        delta_keys: set[str] = set()
        if incremental:
            # Per-side unions (never one merged subset) — see delta_nodes_*
            # comment above for why the winner-picking collapse matters.
            if delta_nodes_old:
                delta_keys |= _candidate_delta_keys(delta_nodes_old)
            if delta_nodes_new:
                delta_keys |= _candidate_delta_keys(delta_nodes_new)
            prev_by_id = {
                str(n.get("id") or ""): n
                for n in prev_di_synth_nodes
                if isinstance(n, dict)
            }
            new_by_id = {str(n.get("id") or ""): n for n in di_synth_nodes}
            di_prev_only = [prev_by_id[i] for i in set(prev_by_id) - set(new_by_id)]
            di_new_only = [new_by_id[i] for i in set(new_by_id) - set(prev_by_id)]
            if di_prev_only:
                delta_keys |= _candidate_delta_keys(di_prev_only)
            if di_new_only:
                delta_keys |= _candidate_delta_keys(di_new_only)
        stats["symbols_invalidated"] = len(delta_keys)

        # --- Fragment resolution: full for recomputed files; symbol-scoped for
        # untouched files (scope (a) + scope (b) of Req-2). ---
        reresolved = 0
        for rel in sorted(merge_files.keys()):
            entry = merge_files[rel]
            if rel in recompute_artifacts:
                entry["edges"] = [
                    _resolve_fragment_edge(e, ctx) for e in raw_edges_by_file[rel]
                ]
                reresolved += len(entry["edges"])
                continue
            if not delta_keys:
                continue
            raw_edges = raw_edges_by_file[rel]
            new_edges: list[dict[str, Any]] | None = None
            stored_edges = entry.get("edges", [])
            for idx, raw_edge in enumerate(raw_edges):
                keys = _edge_lookup_keys(raw_edge)
                if not keys or keys.isdisjoint(delta_keys):
                    continue
                resolved = _resolve_fragment_edge(raw_edge, ctx)
                if new_edges is None:
                    new_edges = list(stored_edges)
                new_edges[idx] = resolved
                reresolved += 1
            if new_edges is not None:
                entry["edges"] = new_edges
        stats["edges_reresolved"] = reresolved
        if self.verbose and reresolved:
            print(
                f"build_index: graph cross-file resolution ran for {reresolved} "
                f"edges ({stats['mode']})",
                flush=True,
            )

        # --- Assemble the final edge map (sorted-file union of fragments,
        # first-key-wins collapse — identical key set to the former in-place
        # rewrite by construction). ---
        edge_map: dict[tuple[str, str, str, str], dict[str, Any]] = {}
        for rel in sorted(merge_files.keys()):
            for fragment_edge in merge_files[rel].get("edges", []):
                if not isinstance(fragment_edge, dict):
                    continue
                edge = _output_fragment_edge(fragment_edge)
                if edge is None:
                    continue
                key = (
                    str(edge.get("source") or ""),
                    str(edge.get("target") or ""),
                    str(edge.get("relation") or ""),
                    str(edge.get("confidence") or ""),
                )
                if not all(key):
                    continue
                edge_map.setdefault(key, edge)
        for key, edge in di_edge_items:
            edge_map.setdefault(key, edge)

        # Wave 1p9qh (1p9qa): inheritance-aware output passes — C# base-
        # relation kind correction + bounded single-definer inherited-method /
        # `super.` call binding. Applied to the assembled OUTPUT edge map on
        # every build (per-file fragments untouched, like the analytics node
        # flags), so incremental == full merge by construction.
        _apply_inheritance_output_passes(
            edge_map, node_map, simple_name_index, qualified_index,
            resolve_ctx=ctx,
        )

        # Wave 1p7dh: config-key -> reader edges. Match each captured config-read
        # literal (from `.get("KEY")` / `cfg["KEY"]`) against the config-key nodes
        # (`file.json::key`) present in the graph and emit a `reads_config` edge
        # (reader -> config-key) at LITERAL_DERIVED confidence on a UNIQUE match.
        # Self-bounding + faithful: a literal matching NO config-key node (ordinary
        # dict access — the common case) is dropped, and one matching MORE THAN ONE
        # config surface (same key in two files, or a leaf collision) is dropped
        # rather than bound to the wrong twin. Full-key match takes precedence over
        # a leaf match.
        config_key_index: dict[str, list[str]] = {}
        config_leaf_index: dict[str, list[str]] = {}
        for node_id in node_map:
            if not _is_json_config_node_id(node_id):
                continue
            if not _is_config_file_path(node_id.split("::", 1)[0]):
                continue  # only declared/pattern-matched CONFIG files, not data JSON
            key = node_id.split("::", 1)[1]
            if not key:
                continue
            config_key_index.setdefault(key, []).append(node_id)
            leaf = key.rsplit(".", 1)[-1]
            if leaf != key:
                config_leaf_index.setdefault(leaf, []).append(node_id)
        if config_key_index:
            seen_cfg: set[tuple[str, str]] = set()
            for rel in sorted(merge_files.keys()):
                for cand in merge_files[rel].get("config_read_candidates", []) or []:
                    if not (isinstance(cand, (list, tuple)) and len(cand) == 2):
                        continue
                    reader, literal = cand
                    if not isinstance(reader, str) or not isinstance(literal, str):
                        continue
                    if not _config_literal_is_distinctive(literal):
                        continue
                    match = config_key_index.get(literal) or config_leaf_index.get(literal)
                    if not match or len(match) != 1:
                        continue
                    target = match[0]
                    if reader == target or reader not in node_map:
                        continue
                    pair = (reader, target)
                    if pair in seen_cfg:
                        continue
                    seen_cfg.add(pair)
                    key_t = (reader, target, GRAPH_CONFIG_READS_RELATION, GRAPH_LITERAL_DERIVED_CONFIDENCE)
                    edge_map.setdefault(
                        key_t,
                        _edge(reader, target, GRAPH_CONFIG_READS_RELATION, confidence=GRAPH_LITERAL_DERIVED_CONFIDENCE),
                    )

        # Wave 1p9qi (1p9qf): embedded-SQL bind. Each captured sink literal
        # (per-file `sql_capture_candidates` fragments) runs through the
        # frozen 1p9qd statement-analysis unit; every clause-aware table
        # reference binds source → table at LITERAL_DERIVED on a UNIQUE match
        # against the SQL-DEFINED (`sql_kind` table/view) node set —
        # schema-qualified/exact name first, then bare/final-segment;
        # AMBIGUITY DROPS the edge (never a guess); NO match mints the
        # reserved `external::sql::<name>` target (relation-scoped invariant —
        # see `_SQL_EXTERNAL_TABLE_PREFIX`). Recomputed fresh from fragments
        # on every build, exactly like the config-read pass above, so
        # incremental == full merge by construction and these edges never
        # enter fragments or phase-1 resolution.
        sql_captures: list[tuple[str, str, str]] = []
        sql_dynamic_refused = 0
        _seen_captures: set[tuple[str, str]] = set()
        for rel in sorted(merge_files.keys()):
            entry = merge_files[rel]
            try:
                sql_dynamic_refused += int(entry.get("sql_capture_dynamic") or 0)
            except (TypeError, ValueError):
                pass
            for cand in entry.get("sql_capture_candidates", []) or []:
                if not (isinstance(cand, (list, tuple)) and len(cand) == 2):
                    continue
                cap_src, cap_sql = cand
                if not (isinstance(cap_src, str) and isinstance(cap_sql, str) and cap_src and cap_sql):
                    continue
                if (cap_src, cap_sql) in _seen_captures:
                    continue
                _seen_captures.add((cap_src, cap_sql))
                sql_captures.append((rel, cap_src, cap_sql))

        # Wave 1p9qi (1p9qg): ORM entity→table mapping candidates (declared
        # names captured per file — see the capture section). Collected here
        # so both LITERAL_DERIVED bind passes share one `sql_kind` node index.
        orm_mapping_candidates: list[tuple[str, str, str]] = []
        orm_convention_refused = 0
        orm_dynamic_refused = 0
        _seen_orm_caps: set[tuple[str, str]] = set()
        for rel in sorted(merge_files.keys()):
            entry = merge_files[rel]
            try:
                orm_convention_refused += int(entry.get("orm_entity_convention") or 0)
            except (TypeError, ValueError):
                pass
            try:
                orm_dynamic_refused += int(entry.get("orm_entity_dynamic") or 0)
            except (TypeError, ValueError):
                pass
            for cand in entry.get("orm_entity_candidates", []) or []:
                if not (isinstance(cand, (list, tuple)) and len(cand) == 2):
                    continue
                map_src, map_decl = cand
                if not (isinstance(map_src, str) and isinstance(map_decl, str) and map_src and map_decl):
                    continue
                if (map_src, map_decl) in _seen_orm_caps:
                    continue
                _seen_orm_caps.add((map_src, map_decl))
                orm_mapping_candidates.append((rel, map_src, map_decl))
        _orm_bind_active = bool(
            orm_mapping_candidates or orm_convention_refused or orm_dynamic_refused
        )

        # Shared bind-target index over the SQL-defined (`sql_kind`
        # table/view) node set — used by BOTH LITERAL_DERIVED bind passes
        # (embedded SQL above, ORM mapping below); built once.
        sql_object_index: dict[str, list[str]] = {}
        sql_leaf_index: dict[str, list[str]] = {}
        if sql_captures or sql_dynamic_refused or _orm_bind_active:
            for node_id, node in node_map.items():
                if node.get("sql_kind") not in ("table", "view"):
                    continue
                qname = node_id.split("::", 1)[1] if "::" in node_id else str(node.get("label") or "")
                qname = _sql_normalize_object_name(qname)
                if not qname:
                    continue
                sql_object_index.setdefault(qname, []).append(node_id)
                leaf = qname.rsplit(".", 1)[-1]
                if leaf != qname:
                    sql_leaf_index.setdefault(leaf, []).append(node_id)
        # Keys of the embedded-SQL edges added by the bind pass below, so the
        # counters can be reconciled after the downstream prunes (1p9qi review:
        # `bound`/`external` must equal edges REALLY in the payload, not edges
        # the pass attempted — e.g. a short-symbol-pruned source method takes
        # its embedded-SQL edges with it).
        _sql_capture_edge_keys: set[tuple[str, str, str, str]] = set()
        if sql_captures or sql_dynamic_refused:
            sql_counters = {
                "candidates": len(sql_captures),
                "bound": 0,
                "external": 0,
                "ambiguous_dropped": 0,
                # 1p9qi review (parity with the ORM pass's `entity_unresolved`):
                # captures whose source marker resolved to no project node.
                "source_unresolved": 0,
                "dynamic_refused": sql_dynamic_refused,
                # FIX 1 (1rrx5 delivery review): TRUNCATE-led candidates whose
                # parse carries trailing garbage after the target (non-SQL prose
                # at a SQL sink) — refused before bind so no confidently-wrong
                # writes edge is minted. Loud per the 1p9qi stats convention.
                "dirty_truncate_refused": 0,
                # R8 (1rrx5, post-delivery): DELETE/UPDATE/INSERT-led candidates
                # whose parse carries an INTERIOR error before the target table
                # (non-SQL prose with a mandatory-clause connective at a SQL
                # sink, e.g. `delete the row from cache`) — refused before bind,
                # generalizing the truncate defense to the same wrong class.
                "dirty_prose_refused": 0,
            }
            _seen_sql_edges: set[tuple[str, str, str]] = set()
            for rel, cap_src, cap_sql in sql_captures:
                analysis = sql_statement_references(_sql_sanitize_embedded(cap_sql))
                if analysis is None:
                    # SQL grammar unavailable — no embedded binds this build.
                    # 1p9qi review (1p9qe loudness convention): mark it in the
                    # stats + say it, so zero binds is never mistaken for
                    # "no SQL found".
                    sql_counters["grammar_unavailable"] = True
                    if self.verbose:
                        print(
                            "build_index: embedded-SQL capture skipped — SQL "
                            "grammar unavailable (no binds this build)",
                            flush=True,
                        )
                    break
                source = _resolve_sql_capture_source(
                    cap_src, rel, node_map, simple_name_index, qualified_index
                )
                if source is None:
                    sql_counters["source_unresolved"] += 1
                    continue
                # FIX 1 (1rrx5 delivery review, adversarial finding 1): refuse a
                # TRUNCATE-led candidate whose parse carries trailing garbage
                # after the target table. `jdbc.update("truncate events now")`
                # sniffs as SQL (leads with `truncate`), parses as a truncate of
                # `events` + a sibling ERROR `now`, and would otherwise mint a
                # confidently-wrong `writes` edge against a REAL table at
                # LITERAL_DERIVED. Scoped to candidates that actually produced a
                # truncate reference so the extra parse only runs for the rare
                # TRUNCATE case; clean `TRUNCATE TABLE events` / `TRUNCATE
                # events` (no ERROR) bind unchanged, and DELETE/UPDATE/INSERT/
                # ALTER/DROP are untouched (they never carry statement=truncate).
                if any(
                    str(ref.get("statement") or "") == "truncate"
                    for ref in analysis.get("references", [])
                ) and _sql_embedded_parse_has_error(_sql_sanitize_embedded(cap_sql)):
                    sql_counters["dirty_truncate_refused"] += 1
                    continue
                # R8 (1rrx5, post-delivery review): generalize the clean-parse
                # defense to the DELETE/UPDATE/INSERT arm of the SAME
                # confidently-wrong class FIX 1 hardened for TRUNCATE.
                # `jdbc.update("delete the row from cache")` sniffs as SQL (leads
                # with `delete`), parses as a DELETE of `cache` whose interior
                # `the row` is an ERROR node BEFORE the `from` target, and would
                # otherwise mint a confidently-wrong `writes cache` at
                # LITERAL_DERIVED. Refuse a delete/update/insert candidate whose
                # parse carries an INTERIOR error (before its first table
                # reference); valid trailing dialect the grammar does not model
                # (`DELETE FROM t RETURNING id`, `INSERT … ON CONFLICT …`, an
                # unmodeled `USING`/option tail) leaves the ERROR AFTER the
                # target and binds unchanged. Scoped to candidates that actually
                # produced a delete/update/insert reference so the extra parse
                # runs only for that arm; TRUNCATE keeps its own any-ERROR gate
                # above (its minimal `TRUNCATE <ident>` grammar cannot separate
                # interior from trailing). Discriminator empirically validated
                # against the live grammar before ship (change-doc R8/AC-9).
                if any(
                    str(ref.get("statement") or "") in ("delete", "update", "insert")
                    for ref in analysis.get("references", [])
                ) and _sql_embedded_has_interior_error(_sql_sanitize_embedded(cap_sql)):
                    sql_counters["dirty_prose_refused"] += 1
                    continue
                for ref in analysis.get("references", []):
                    ref_name = _sql_normalize_object_name(str(ref.get("name") or ""))
                    if not ref_name:
                        continue
                    relation = (
                        GRAPH_WRITES_RELATION
                        if str(ref.get("direction") or "") == "write"
                        else GRAPH_READS_RELATION
                    )
                    matches = sql_object_index.get(ref_name) or []
                    if not matches:
                        leaf = ref_name.rsplit(".", 1)[-1]
                        matches = list(dict.fromkeys(
                            (sql_object_index.get(leaf) or []) + (sql_leaf_index.get(leaf) or [])
                        ))
                    if not matches:
                        target = f"external::{_SQL_EXTERNAL_TABLE_PREFIX}{ref_name}"
                        bucket = "external"
                    elif len(matches) == 1:
                        target = matches[0]
                        bucket = "bound"
                    else:
                        sql_counters["ambiguous_dropped"] += 1
                        continue
                    if source == target:
                        continue
                    edge_id = (source, target, relation)
                    if edge_id in _seen_sql_edges:
                        continue
                    _seen_sql_edges.add(edge_id)
                    sql_counters[bucket] += 1
                    edge_key = (source, target, relation, GRAPH_LITERAL_DERIVED_CONFIDENCE)
                    _sql_capture_edge_keys.add(edge_key)
                    edge_map.setdefault(edge_key, _edge(
                        source, target, relation, confidence=GRAPH_LITERAL_DERIVED_CONFIDENCE,
                    ))
            stats["sql_capture"] = sql_counters
            if self.verbose:
                print(
                    "build_index: embedded-SQL capture "
                    f"candidates={sql_counters['candidates']} bound={sql_counters['bound']} "
                    f"external={sql_counters['external']} "
                    f"ambiguous_dropped={sql_counters['ambiguous_dropped']} "
                    f"source_unresolved={sql_counters['source_unresolved']} "
                    f"dirty_truncate_refused={sql_counters['dirty_truncate_refused']} "
                    f"dirty_prose_refused={sql_counters['dirty_prose_refused']} "
                    f"dynamic_refused={sql_counters['dynamic_refused']}",
                    flush=True,
                )

        # Wave 1p9qi (1p9qg): ORM entity→table mapping bind. Each declared
        # mapping (per-file `orm_entity_candidates` fragments) binds entity
        # class → table node on the dedicated `maps_to` relation at
        # LITERAL_DERIVED, with EXACTLY the embedded-SQL match semantics:
        # normalized qualified-exact name first, then unique bare/leaf match
        # against the `sql_kind` node set; AMBIGUITY DROPS the edge; NO match
        # mints the reserved `external::sql::<name>` target. `entitytype::`
        # sources (EF ToTable) resolve to the unique project class or drop.
        # Recomputed fresh from fragments every build — these edges never
        # enter fragments or phase-1 resolution (same invariant contract as
        # the pass above; pinned by tests).
        if _orm_bind_active:
            orm_counters = {
                "candidates": len(orm_mapping_candidates),
                "bound": 0,
                "external": 0,
                "ambiguous_dropped": 0,
                "entity_unresolved": 0,
                "convention_refused": orm_convention_refused,
                "dynamic_refused": orm_dynamic_refused,
            }
            _seen_orm_edges: set[tuple[str, str]] = set()
            for rel, map_src, map_decl in orm_mapping_candidates:
                source = _resolve_orm_entity_source(
                    map_src, rel, node_map, simple_name_index, qualified_index
                )
                if source is None:
                    orm_counters["entity_unresolved"] += 1
                    continue
                decl_name = _sql_normalize_object_name(map_decl)
                if not decl_name:
                    continue
                matches = sql_object_index.get(decl_name) or []
                if not matches:
                    leaf = decl_name.rsplit(".", 1)[-1]
                    matches = list(dict.fromkeys(
                        (sql_object_index.get(leaf) or []) + (sql_leaf_index.get(leaf) or [])
                    ))
                if not matches:
                    target = f"external::{_SQL_EXTERNAL_TABLE_PREFIX}{decl_name}"
                    bucket = "external"
                elif len(matches) == 1:
                    target = matches[0]
                    bucket = "bound"
                else:
                    orm_counters["ambiguous_dropped"] += 1
                    continue
                if source == target:
                    continue
                edge_id = (source, target)
                if edge_id in _seen_orm_edges:
                    continue
                _seen_orm_edges.add(edge_id)
                orm_counters[bucket] += 1
                edge_map.setdefault(
                    (source, target, GRAPH_MAPS_TO_RELATION, GRAPH_LITERAL_DERIVED_CONFIDENCE),
                    _edge(source, target, GRAPH_MAPS_TO_RELATION, confidence=GRAPH_LITERAL_DERIVED_CONFIDENCE),
                )
            stats["entity_mapping"] = orm_counters
            if self.verbose:
                print(
                    "build_index: ORM entity mapping "
                    f"candidates={orm_counters['candidates']} bound={orm_counters['bound']} "
                    f"external={orm_counters['external']} "
                    f"ambiguous_dropped={orm_counters['ambiguous_dropped']} "
                    f"entity_unresolved={orm_counters['entity_unresolved']} "
                    f"convention_refused={orm_counters['convention_refused']} "
                    f"dynamic_refused={orm_counters['dynamic_refused']}",
                    flush=True,
                )

        # Reverse invalidation: drop edges left dangling by deletions/renames in
        # surviving (unchanged) referrer files. A cached referrer fragment can
        # still carry an edge into a symbol or file that no longer exists. We
        # only prune edges whose endpoint is *known* to have been removed (a
        # removed path, or a symbol that vanished from a re-extracted file), so
        # legitimate edges to external imports or unresolved targets are
        # preserved.
        # NOTE (defense-in-depth, adversarial review): this prune repairs the
        # PAYLOAD only — the persisted per-file fragments keep whatever they
        # carried. That is correct as long as scope-(b) re-resolution catches
        # every affected fragment edge (it updates fragments); but any future
        # scope-(b) miss class would be MASKED here for exactly one build and
        # then resurface as a dangling payload edge on the next unrelated
        # edit. If a dangling edge is ever observed post-prune, suspect the
        # symbol delta, not this block.
        if removed_paths or removed_symbols:
            def _file_of(node_id: str) -> str:
                return node_id.split("::")[0] if "::" in node_id else node_id

            for key in [
                k
                for k in edge_map
                if k[0] in removed_symbols
                or k[1] in removed_symbols
                or _file_of(k[0]) in removed_paths
                or _file_of(k[1]) in removed_paths
            ]:
                edge_map.pop(key, None)

        # Prune short internal symbols: drop code symbol nodes with labels ≤
        # _SHORT_SYMBOL_MAX_LEN chars unless some other file imports or calls them.
        # EXEMPT constants (kind=GRAPH_CONST_KIND): an enum member / named const like `Status.OK`
        # or `Dir.Up` (label `OK`/`Up`) is a meaningful value-carrying symbol, not the loop-var /
        # type-param noise this prune targets — and these short names are the wave's own canonical
        # examples. The chunk lane already keeps them (`_go_const_chunk_name`); the graph matches so
        # `code_definition("OK")` resolves (1p4q4 review D2/F1).
        # Wave 1p9qi (1p9qd): SQL schema objects (`sql_kind`-carrying nodes)
        # are likewise exempt — a short table/view name (`t1`, `v1`) is a real
        # CREATE-declared object, never the loop-var/type-param noise this
        # prune targets, and pruning one silently drops its lineage edges.
        short_symbols: set[str] = {
            node_id
            for node_id, node in node_map.items()
            if "::" in node_id
            and len(str(node.get("label") or "")) <= _SHORT_SYMBOL_MAX_LEN
            and node.get("kind") != GRAPH_CONST_KIND
            and "sql_kind" not in node
        }
        if short_symbols:
            externally_used: set[str] = set()
            for src, tgt, rel, conf in edge_map:
                if tgt not in short_symbols or rel == "defines":
                    continue
                tgt_file = str((node_map.get(tgt) or {}).get("source_file") or "")
                src_file = src.split("::")[0] if "::" in src else src
                if src_file != tgt_file:
                    externally_used.add(tgt)
            pruned = short_symbols - externally_used
            for node_id in pruned:
                node_map.pop(node_id, None)
            for key in [k for k in edge_map if k[0] in pruned or k[1] in pruned]:
                edge_map.pop(key, None)

        # 1p9qi review: reconcile the embedded-SQL capture counters against the
        # POST-prune edge_map so `bound`/`external` equal edges really in the
        # payload (the reverse-invalidation and short-symbol prunes above can
        # drop a just-bound edge, e.g. when its source method node is pruned).
        if _sql_capture_edge_keys and "sql_capture" in stats:
            _sc = stats["sql_capture"]
            _survived_bound = 0
            _survived_external = 0
            for key in _sql_capture_edge_keys:
                if key in edge_map:
                    if key[1].startswith("external::"):
                        _survived_external += 1
                    else:
                        _survived_bound += 1
            _pruned_out = (_sc["bound"] - _survived_bound) + (_sc["external"] - _survived_external)
            if _pruned_out:
                _sc["bound"] = _survived_bound
                _sc["external"] = _survived_external
                _sc["pruned_post_bind"] = _pruned_out
                if self.verbose:
                    print(
                        "build_index: embedded-SQL capture reconcile — "
                        f"{_pruned_out} edge(s) pruned post-bind; "
                        f"bound={_survived_bound} external={_survived_external}",
                        flush=True,
                    )

        # Prune zero-edge doc/seed nodes — they're fully covered by semantic search
        # and provide no graph navigation value.
        _DOC_SEED_KINDS = {"doc", "seed"}
        referenced_nodes: set[str] = set()
        for src, tgt, rel, conf in edge_map:
            referenced_nodes.add(src)
            referenced_nodes.add(tgt)
        zero_edge_docs = {
            node_id
            for node_id, node in node_map.items()
            if node.get("kind") in _DOC_SEED_KINDS and node_id not in referenced_nodes
        }
        for node_id in zero_edge_docs:
            node_map.pop(node_id, None)

        # Compute graph analytics: entry points, dead code risk, chokepoints.
        # Restricted to executable source languages — excludes data/config/markup files.
        _EXECUTABLE_EXTS = frozenset({
            ".py", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx",
            ".go", ".rs", ".java", ".c", ".cpp", ".cc", ".cxx", ".h", ".hpp",
            ".cs", ".sh", ".bash", ".zsh", ".fish", ".kt", ".kts",
            ".swift", ".m", ".mm", ".rb", ".scala", ".ps1", ".psm1",
            ".sql", ".psql", ".pgsql", ".ddl", ".dml",
        })

        def _is_executable(node_id: str) -> bool:
            f = node_id.split("::")[0] if "::" in node_id else node_id
            return Path(f).suffix.lower() in _EXECUTABLE_EXTS

        # Build per-node edge sets for fast lookup.
        incoming_external: dict[str, set[str]] = {}  # tgt → set of relations from other files
        outgoing_any: set[str] = set()
        for src, tgt, rel, conf in edge_map:
            outgoing_any.add(src)
            src_file = src.split("::")[0] if "::" in src else src
            tgt_file = (node_map.get(tgt) or {}).get("source_file") or (tgt.split("::")[0] if "::" in tgt else tgt)
            if src_file != tgt_file:
                incoming_external.setdefault(tgt, set()).add(rel)

        # Entry points: executable code modules that nothing imports from another file,
        # but that have outgoing edges (so they're not isolated).
        for node_id, node in node_map.items():
            if node.get("kind") != "module" or "::" in node_id:
                continue
            if not _is_executable(node_id):
                continue
            if "imports" not in incoming_external.get(node_id, set()) and node_id in outgoing_any:
                node["is_entry_point"] = True

        # Dead code risk: executable code MODULE nodes where none of their defined
        # symbols are externally called or imported. Flagging at module level avoids
        # per-symbol noise — most internal helpers are legitimately private.
        module_has_external_use: set[str] = set()
        for src, tgt, rel, conf in edge_map:
            if rel not in {"calls", "imports"}:
                continue
            src_file = src.split("::")[0] if "::" in src else src
            tgt_file = (node_map.get(tgt) or {}).get("source_file") or (tgt.split("::")[0] if "::" in tgt else tgt)
            if src_file != tgt_file and tgt_file:
                module_has_external_use.add(tgt_file)
        for node_id, node in node_map.items():
            if node.get("kind") != "module" or "::" in node_id:
                continue
            if not _is_executable(node_id):
                continue
            if node.get("is_entry_point"):
                continue
            if node_id not in module_has_external_use and node_id in outgoing_any:
                node["dead_code_risk"] = True

        # Chokepoints: articulation points in the undirected graph, restricted to
        # executable code modules and their symbols.
        try:
            import igraph as ig
            exec_ids = [
                nid for nid in node_map
                if _is_executable(nid)
            ]
            vid = {nid: i for i, nid in enumerate(exec_ids)}
            ig_edges = [
                (vid[src], vid[tgt])
                for src, tgt, rel, conf in edge_map
                if src in vid and tgt in vid and vid[src] != vid[tgt]
            ]
            G = ig.Graph(n=len(exec_ids), edges=ig_edges, directed=False)
            for ap_idx in G.articulation_points():
                nid = exec_ids[ap_idx]
                if nid in node_map:
                    node_map[nid]["is_chokepoint"] = True
        except Exception:
            pass

        # Wave 1p9q8 honesty pass: a `calls` edge that reaches the END of the
        # finalize pipeline STILL `external::` must not carry a receiver/
        # construction resolution confidence — `RECEIVER_RESOLVED` means "bound
        # to a receiver-typed PROJECT node", and an `external::` target is
        # unresolved. The Python typed-receiver resolver (1p9q4) emits
        # `external::<Type>.<method>` WITH that confidence and relies on the
        # cross-file / inheritance rewrites to swap the target onto a project
        # node; the ones that never bind (method absent from the resolved class,
        # ambiguous cross-file same-name twin) reach here still external. Run on
        # the FINAL edge map — after every rewrite pass — so a fragment- or
        # output-stage rebind to a real project node is never clobbered. Confidence
        # is part of the edge key, so re-key and collapse any collision onto an
        # already-EXTRACTED twin.
        _downgraded_edge_map: dict[tuple[str, str, str, str], dict[str, Any]] = {}
        for _ekey, _eedge in edge_map.items():
            _new_edge = _downgrade_unresolved_typed_calls(_eedge)
            if _new_edge is _eedge:
                _downgraded_edge_map.setdefault(_ekey, _eedge)
                continue
            _new_key = (_ekey[0], _ekey[1], _ekey[2], str(_new_edge.get("confidence") or ""))
            _downgraded_edge_map.setdefault(_new_key, _new_edge)
        edge_map = _downgraded_edge_map

        from datetime import UTC, datetime

        # Wave 1p66e: input-graph fingerprint — a content hash over the sorted
        # node-set and the sorted resolved edge-set (NOT the volatile generated_at
        # timestamp). Two identical-input rebuilds produce the same fingerprint
        # once extraction + cross-file resolution are deterministic. Wave 1p9q2:
        # also the equivalence surface for incremental-vs-full merge and the
        # payload/store crash-consistency binding.
        import hashlib as _hashlib

        _fp = _hashlib.sha256()
        for _nid in sorted(node_map.keys()):
            _fp.update(_nid.encode("utf-8"))
            _fp.update(b"\0")
        _fp.update(b"\x01")  # node/edge section separator
        for _ek in sorted(edge_map.keys()):
            _fp.update("\x1f".join(_ek).encode("utf-8"))
            _fp.update(b"\0")
        input_fingerprint = _fp.hexdigest()

        graph_payload = {
            "schema_version": GRAPH_SCHEMA_VERSION,
            "builder_version": GRAPH_BUILDER_VERSION,
            "layer": self.layer,
            "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "input_fingerprint": input_fingerprint,
            "counts": {
                "files": len(merge_files),
                "nodes": len(node_map),
                "edges": len(edge_map),
                "entry_points": sum(1 for n in node_map.values() if n.get("is_entry_point")),
                "dead_code_risk": sum(1 for n in node_map.values() if n.get("dead_code_risk")),
                "chokepoints": sum(1 for n in node_map.values() if n.get("is_chokepoint")),
            },
            "nodes": sorted(node_map.values(), key=lambda item: str(item.get("id") or "")),
            "edges": sorted(edge_map.values(), key=lambda item: (
                str(item.get("source") or ""),
                str(item.get("target") or ""),
                str(item.get("relation") or ""),
            )),
        }

        # --- Persist: store commit first, then payload, then binding stat. ---
        merge_state_out: dict[str, Any] = {
            "format": _MERGE_STATE_FORMAT,
            "payload_fingerprint": input_fingerprint,
            "files": merge_files,
            "di_synth_nodes": di_synth_nodes,
        }
        if locality_violation:
            merge_state_out["locality_violation"] = True
            print(
                "build_index: graph merge encountered a node outside its own "
                "file's id space — incremental merge disabled for this layer "
                "until the next full re-merge (graph remains correct)",
                file=sys.stderr,
                flush=True,
            )
        deletes = sorted(set(known_paths) - set(merge_files))
        store.apply_build(
            puts=row_puts,
            deletes=deletes,
            blobs={"merge_state": merge_state_out},
            meta={
                "merge_state_format": _MERGE_STATE_FORMAT,
                "payload_fingerprint": input_fingerprint,
                "payload_stat_state": "pending",
            },
        )
        _write_json(self.graph_path, graph_payload)
        try:
            st = self.graph_path.stat()
            store.set_meta(
                {
                    "payload_size": str(st.st_size),
                    "payload_mtime_ns": str(st.st_mtime_ns),
                    "payload_stat_state": "bound",
                }
            )
        except OSError:
            # Binding stays "pending": the next build detects it and degrades
            # to a loud full re-merge (never a silently inconsistent graph).
            pass

        # Lightweight session state view (historical shape, hash-only entries).
        state_files_light: dict[str, dict[str, str]] = {}
        for rel in merge_files:
            put = row_puts.get(rel)
            if put is not None:
                state_files_light[rel] = {"source_hash": str(put.get("source_hash") or "")}
            else:
                state_files_light[rel] = {"source_hash": known_paths.get(rel, "")}
        self._state = {
            "schema_version": GRAPH_SCHEMA_VERSION,
            "builder_version": GRAPH_BUILDER_VERSION,
            "layer": self.layer,
            "input_fingerprint": input_fingerprint,
            "walker_version": self.walker_version,
            "chunker_version": self.chunker_version,
            "files": state_files_light,
        }

        # Attach transient per-build merge stats AFTER the payload write so
        # they are returned to the caller (build-log instrumentation, Req-9)
        # but never persisted into the artifact.
        stats["merge_ms"] = int((_time.monotonic() - merge_started) * 1000)
        stats["state_reads"] = store.record_reads - reads_before
        stats["state_writes"] = store.record_writes - writes_before
        stats["blob_reads"] = store.blob_reads - blob_reads_before
        stats["blob_writes"] = store.blob_writes - blob_writes_before
        stats["blob_bytes"] = store.blob_bytes_written - blob_bytes_before
        graph_payload["merge_stats"] = stats
        return graph_payload


# Wave 1p2q3 (1p2tz post-ship-3 perf): parallel per-file code extraction.
# Threshold-gated so small builds (tests, incremental updates) stay serial
# and don't pay the ProcessPoolExecutor spawn overhead — on macOS each worker
# spawn costs ~500ms–1s for fresh Python import + tree-sitter language load.
# Doc/seed extraction stays serial because it depends on cross-file
# `symbol_terms` built across artifacts; only code-file extraction parallelizes.
_PARALLEL_EXTRACTION_THRESHOLD = int(os.environ.get("WAVEFOUNDRY_GRAPH_PARALLEL_THRESHOLD", "100"))
# Wave 1p2q3 (1p2wd / Bug 4): parallel extraction now uses `spawn` start
# method (default) + a worker `initializer` that registers `graph_indexer`
# in each fresh worker's `sys.modules` before task unpickling. The 1.3.14
# `fork` path deadlocked on macOS after transitive C extension state
# (tree-sitter parsers, possibly objc/Foundation) initialized in the parent;
# spawn boots a clean interpreter per worker and avoids the inheritance
# hazard entirely.
#
# Worker count auto-scales by file count (set in 1.3.20). The 1.3.18→1.3.19
# default of `1` (always-serial) was conservative — small projects don't
# benefit from parallel because spawn boot (~500ms–1s × workers) exceeds
# their per-file work, but large-scale builds (1k+ files) leave 2-3× perf
# on the table. The scale tiers reflect break-even math for spawn boot vs.
# parallelizable extraction time:
#   - file_count <  200 → 2 workers (modest projects)
#   - file_count <  500 → 3 workers (medium monorepos)
#   - file_count >= 500 → min(cpu_count, 4) workers (large-monorepo-shape)
# Operators can override the auto-scaled count via
# WAVEFOUNDRY_GRAPH_PARALLEL_WORKERS (any positive int; 1 disables parallel).
# The 100-file threshold for entering the parallel path at all (set by
# WAVEFOUNDRY_GRAPH_PARALLEL_THRESHOLD) is unchanged — auto-scale only
# decides *how many* workers, never *whether* to go parallel.
_PARALLEL_EXTRACTION_WORKERS_OVERRIDE: int | None = (
    int(os.environ["WAVEFOUNDRY_GRAPH_PARALLEL_WORKERS"])
    if "WAVEFOUNDRY_GRAPH_PARALLEL_WORKERS" in os.environ
    else None
)

# Wave 1p2q3 (1p2wd post-ship 1.3.27): parallel-extraction backend selector.
# `threads` (default) uses `ThreadPoolExecutor` — no spawn cost, no IPC, no
# pipe machinery, no orphan workers, no pickle. Tree-sitter releases the GIL
# during parse, so the per-file hot path still parallelizes across cores.
# `processes` uses `ProcessPoolExecutor` with spawn start method + bounded-in-
# flight chunked batches — preserved for benchmarking and for workloads where
# the Python-side walker (GIL-bound) dominates parse time enough that the
# spawn overhead is amortizable. Default flipped to threads in 1.3.27 after
# 1.3.25/1.3.26 field validation on a 1,542-file workload showed
# spawn-mode parallel-4 ran 1.6× slower than serial (44s/45.2s vs. 27.1s) —
# worker boot cost (re-importing tree-sitter etc. per spawn) and per-task
# pickle overhead dominated the actual extraction work.
# Wave 1p8gu (review fix MP-2): the default was "processes" although the comment (and the 1.3.27
# benchmark decision) says threads — so a clean install with >=100 files took the process-spawn path
# BY DEFAULT, opening a console window per worker on Windows. Default reconciled to "threads" (also
# the faster backend per the benchmark above). When "processes" IS opted in, the pool below routes
# through subprocess_util.windowless_mp_context so workers are console-free on Windows regardless.
_PARALLEL_EXTRACTION_BACKEND = os.environ.get(
    "WAVEFOUNDRY_GRAPH_PARALLEL_BACKEND", "threads"
).strip().lower()


_PERF_CORE_COUNT_CACHE: int | None = None


def _physical_perf_core_count() -> int | None:
    """Return performance-core count on macOS (Apple Silicon), or None elsewhere.

    Apple Silicon CPUs are heterogeneous: performance (P) cores run user
    code at full speed; efficiency (E) cores run at roughly 50% throughput
    and consume far less power. `os.cpu_count()` returns the total logical
    count (P + E) and gives no way to distinguish them. Running parallel
    extraction threads on E-cores when P-cores are saturated buys little —
    the bottleneck shifts to E-core throughput and IPC overhead.

    We read `hw.perflevel0.physicalcpu` via `sysctl` to get the actual
    P-core count. Cached at module level (sysctl fork+exec is cheap but
    we only need to ask once). Returns None on Linux/Windows where the
    cores are homogeneous and `os.cpu_count()` is the right answer.
    """
    global _PERF_CORE_COUNT_CACHE
    if _PERF_CORE_COUNT_CACHE is not None:
        return _PERF_CORE_COUNT_CACHE
    if sys.platform != "darwin":
        return None
    try:
        result = subprocess_util.isolated_run(
            ["sysctl", "-n", "hw.perflevel0.physicalcpu"],
            capture_output=True, text=True, timeout=2,
        )
        if result.returncode == 0:
            count = int(result.stdout.strip())
            if count > 0:
                _PERF_CORE_COUNT_CACHE = count
                return count
    except Exception:
        pass
    return None


def _system_cpu_cap() -> int:
    """Cap on parallel worker count based on available CPU resources.

    Prefers macOS P-core count when available — Apple Silicon's E-cores
    run at ~50% throughput and scheduling parallel-extraction workers
    onto them past the P-core ceiling doesn't help. Falls back to
    `cpu_count() // 2` on Linux/Windows, which approximates the physical-
    core count on SMT-enabled CPUs (almost all modern Intel/AMD servers).

    Wave 1p2q3 (1p2wd post-ship 1.3.30): raised to full P-core count after
    Field measurement showed process-8 (matching P-core count)
    matches process-6 (P-cores − 2) within noise at the fastest end of
    the curve (15.07s vs. 15.25s, both extraction ~11.4s). With the
    process backend each worker has its own GIL so the "leave headroom
    for main thread" argument that justified `P - 2` under threads
    doesn't carry — workers run independently on dedicated cores and the
    main thread does almost nothing while extraction runs. Operators on
    machines with heavy concurrent workloads can still cap manually via
    `WAVEFOUNDRY_GRAPH_PARALLEL_WORKERS=N`.
    """
    p_cores = _physical_perf_core_count()
    if p_cores is not None and p_cores > 0:
        cap = p_cores
    else:
        total = os.cpu_count() or 1
        cap = total // 2
    return max(2, cap)


def _auto_scale_worker_count(file_count: int) -> int:
    """Choose a worker count for parallel extraction.

    Operator's `WAVEFOUNDRY_GRAPH_PARALLEL_WORKERS` env var wins
    unconditionally (use `1` to disable parallel without touching the
    threshold env var). When unset, scale by `file_count`.
    """
    if _PARALLEL_EXTRACTION_WORKERS_OVERRIDE is not None:
        return _PARALLEL_EXTRACTION_WORKERS_OVERRIDE
    cpu_cap = _system_cpu_cap()
    if file_count < 200:
        return min(2, cpu_cap)
    if file_count < 500:
        return min(3, cpu_cap)
    return cpu_cap


def _worker_init_graph_indexer(graph_indexer_path: str) -> None:
    """ProcessPoolExecutor initializer for parallel extraction workers.

    Spawn-mode workers (the default since 1.3.19 / wave 1p2q3 / 1p2wd Bug 4)
    boot a fresh Python interpreter with no inherited state from the parent.
    The function reference pickled by `pool.map` resolves to
    ``graph_indexer._extract_artifact_for_worker``; since this file is loaded
    via ``importlib.util.spec_from_file_location`` (not the standard import
    system, because the framework scripts directory is not a package), a
    spawn-mode worker has no way to find the module by name unless we
    register it ourselves.

    This initializer fires once per worker process at startup, *before* the
    first task is dispatched (per the ProcessPoolExecutor contract), and
    loads this same `.py` file under the canonical ``"graph_indexer"`` name
    so subsequent task unpickling finds the function reference.
    """
    import importlib.util as _il_util
    try:
        spec = _il_util.spec_from_file_location("graph_indexer", graph_indexer_path)
        if spec is None or spec.loader is None:
            return
        module = _il_util.module_from_spec(spec)
        sys.modules["graph_indexer"] = module
        spec.loader.exec_module(module)
    except Exception:
        # If the initializer fails the worker will still attempt the task
        # and crash with a clearer ImportError than a deadlock — the parent's
        # `except Exception: ... falling back to serial` branch handles
        # whichever surface the failure takes.
        pass
    # Wave 1p2q3 (1p2wd post-ship 1.3.24 / Bug 7): macOS spawn-mode workers
    # don't self-terminate reliably when the parent dies. `multiprocessing`'s
    # `parent_sentinel` pipe is supposed to signal EOF when the parent exits,
    # but under macOS launchd's re-parenting the pipe can stay open and the
    # worker keeps running forever, idling on `call_queue.get()`. Every
    # killed build then leaks N worker processes plus the resource_tracker.
    # Mitigation: spawn a daemon thread inside each worker that polls
    # `os.getppid()` every 2s and `os._exit(0)`s as soon as the ppid changes
    # (re-parented = orphaned). Daemon thread dies with the worker so it
    # leaves no trace on clean shutdown.
    try:
        import threading as _t
        import time as _time
        import os as _os

        def _ppid_watchdog() -> None:
            try:
                orig_ppid = _os.getppid()
            except Exception:
                return
            while True:
                _time.sleep(2.0)
                try:
                    cur_ppid = _os.getppid()
                except Exception:
                    return
                if cur_ppid != orig_ppid or cur_ppid == 1:
                    try:
                        print(
                            f"build_index: [worker pid={_os.getpid()}] parent died "
                            f"(ppid {orig_ppid} -> {cur_ppid}); exiting",
                            file=sys.stderr, flush=True,
                        )
                    except Exception:
                        pass
                    _os._exit(0)

        _t.Thread(target=_ppid_watchdog, daemon=True, name="ppid-watchdog").start()
    except Exception:
        # Watchdog is best-effort; failure to start it just means the worker
        # falls back to the (broken-on-macOS-spawn) parent_sentinel behavior.
        pass


def _extract_artifacts_for_worker_batch(batch_args: list) -> list:
    """Worker entry point for a BATCH of files.

    Wave 1p2q3 (1p2wd post-ship 1.3.24 / Bug 8): per-task IPC was ~96× the
    cost of chunked IPC (`pool.map(chunksize=96)`); single-file submission
    via the bounded-in-flight pattern in 1.3.23 produced correct results but
    ran ~57× slower than serial on a 1,542-file workload because each file
    incurred a full pickle/unpickle round trip through the multiprocessing
    call queue. This batch entry processes a list of tuples in one IPC
    cycle, amortizing the pipe overhead across the whole batch.
    """
    return [_extract_artifact_for_worker(args) for args in batch_args]


def _extract_artifact_for_worker(args: tuple) -> tuple[str, dict | None]:
    """Worker entry point for parallel code-file extraction.

    Constructs a minimal `GraphIndexSession`, runs `record_file` to extract a
    single file's artifact, and returns `(rel_path, pending_code_entry)`.
    The session is discarded after extraction — only the artifact dict
    crosses the process boundary.

    Module-level (required by `spawn` start method on macOS) and self-
    contained so each worker can be a fresh Python process.
    """
    # Wave 1p2q3 (1p2wd post-ship 1.3.28): worker args include `shared_state`
    # (pre-loaded by parent) and `shared_gitattrs_patterns` so each per-task
    # `GraphIndexSession` construction skips the disk read + JSON parse +
    # gitattrs scan that previously serialized on the GIL across all worker
    # threads. Backwards-compatible: older 7-element tuples still work (the
    # session falls back to its own disk-load path).
    if len(args) >= 9:
        rel_path, source_text, root_str, layer, gitattrs_list, walker_version, chunker_version, shared_state, shared_gitattrs_patterns = args
    else:
        rel_path, source_text, root_str, layer, gitattrs_list, walker_version, chunker_version = args
        shared_state = None
        shared_gitattrs_patterns = None
    # Workers spawned via `spawn` re-import this module fresh; use whichever
    # GraphIndexSession is in the worker's sys.modules (registered by the
    # initializer) to avoid double-loading.
    gi = sys.modules.get("graph_indexer")
    Session = getattr(gi, "GraphIndexSession", GraphIndexSession) if gi is not None else GraphIndexSession
    root = Path(root_str)
    session = Session(
        root=root,
        index_dir=root / ".wavefoundry" / "index",
        layer=layer,
        files=[],
        current_file_meta={},
        walker_version=walker_version,
        chunker_version=chunker_version,
        verbose=False,
        state=shared_state,
    )
    # Pre-set gitattrs patterns so record_file() doesn't trigger another
    # disk read + scan on the worker's first code-file classification.
    if shared_gitattrs_patterns is not None:
        session._gitattrs_patterns = shared_gitattrs_patterns
    else:
        session._gitattrs_patterns = frozenset(gitattrs_list)
    session.record_file(rel_path, source_text)
    return rel_path, session.pending_code.get(rel_path)


def update_graph_index(
    *,
    root: Path,
    index_dir: Path,
    layer: str,
    files: list[Path],
    current_file_meta: dict[str, dict[str, Any]],
    changed: set[str],
    removed: set[str],
    walker_version: str,
    chunker_version: str,
    verbose: bool = False,
) -> dict[str, Any]:
    # Wave 1p2q3 (1p2tz post-ship-3 perf): the lru caches on path resolvers
    # (`_probe_ts_alias_target_cached`, `_resolve_relative_ts_import_cached`)
    # and the per-file declared-names cache are NOT cleared per-build by
    # design. Within a build they turn repeated lookups into O(1) hits; across
    # builds the LRU eviction policy + mtime-keyed dict (for declared-names)
    # handle staleness naturally. The cost of clearing per build dominated
    # wall-time on small-build test workloads where each test made a tiny
    # build call, with negligible benefit on real workloads where rebuilds
    # are infrequent. Stale-result risk is low: deleted files don't appear
    # in the per-build file list so they're not extracted regardless of
    # cached probe results.
    session = GraphIndexSession(
        root=root,
        index_dir=index_dir,
        layer=layer,
        files=files,
        current_file_meta=current_file_meta,
        walker_version=walker_version,
        chunker_version=chunker_version,
        verbose=verbose,
    )
    changed_set = {str(rel).replace("\\", "/") for rel in changed}
    removed_set = {str(rel).replace("\\", "/") for rel in removed}
    # After builder/walker/chunker bumps GraphIndexSession starts with empty cached
    # artifacts. Incremental indexer runs only pass a small ``changed`` set (e.g. docs
    # from the post-edit hook), which would otherwise write a nearly empty graph.
    if not (session._state.get("files") or {}):
        changed_set = {
            str(file_path.relative_to(root)).replace("\\", "/")
            for file_path in files
            if file_path.is_file()
        }
        if verbose and changed_set:
            print(
                f"build_index: graph state empty for {layer} layer — "
                f"re-extracting {len(changed_set)} file(s) in corpus",
                flush=True,
            )
    if verbose:
        print(
            f"build_index: graph extraction inputs for {layer} layer — "
            f"{len(changed_set)} changed, {len(removed_set)} removed",
            flush=True,
        )
    # Wave 1p2q3 (1p2tz post-ship-3 perf): bucket files by kind so code-file
    # extraction can parallelize; doc/seed stays serial (cross-file symbol
    # dependency makes it sequential by nature).
    #
    # Wave 1p2q3 (1p2wd post-ship 1.3.31 perf): parallelize the read loop with
    # a `ThreadPoolExecutor`. `Path.read_text` releases the GIL during the
    # syscall, so multiple threads issue concurrent reads to the page cache.
    # On SSD this cuts the parent's pre-extraction stage by ~1-2s on large-
    # scale (1,500+ file) workloads. Bucketing into code / doc lists stays
    # serial (and trivially fast) because it only inspects `rel` and the
    # cached `kind`. Below the parallel-extraction file-count threshold
    # the read overhead is small enough that the serial path is fine.
    code_work_items: list[tuple[str, str]] = []  # (rel_path, source_text)
    doc_work_items: list[tuple[str, str]] = []   # (rel_path, source_text)

    def _read_one(file_path: "Path") -> tuple[str, str, str] | None:
        rel = _repo_rel(file_path.relative_to(root))
        if rel not in changed_set:
            return None
        if _is_minified_file(rel):
            return None
        try:
            text = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return None
        return (rel, text, _kind_for_path(rel))

    if len(files) >= _PARALLEL_EXTRACTION_THRESHOLD:
        # Worker count for file reads: tuned smaller than extraction since
        # this is purely I/O-bound and the page cache saturates quickly.
        # Use `min(cpu_count, 8)` capped at the file count so we don't spawn
        # more threads than there's work for.
        from concurrent.futures import ThreadPoolExecutor as _TPool
        _read_workers = max(2, min(8, len(files), os.cpu_count() or 4))
        with _TPool(max_workers=_read_workers, thread_name_prefix="wavefoundry-read") as _pool:
            for result in _pool.map(_read_one, files):
                if result is None:
                    continue
                rel, text, kind = result
                if kind == "code":
                    code_work_items.append((rel, text))
                else:
                    doc_work_items.append((rel, text))
    else:
        for file_path in files:
            result = _read_one(file_path)
            if result is None:
                continue
            rel, text, kind = result
            if kind == "code":
                code_work_items.append((rel, text))
            else:
                doc_work_items.append((rel, text))

    worker_count = _auto_scale_worker_count(len(code_work_items))
    use_parallel = (
        worker_count > 1
        and len(code_work_items) >= _PARALLEL_EXTRACTION_THRESHOLD
    )
    if use_parallel:
        # Pre-load gitattrs once in the parent; pass to workers.
        if session._gitattrs_patterns is None:
            session._gitattrs_patterns = _load_gitattributes_generated_paths(root)
        gitattrs_list = list(session._gitattrs_patterns)
        backend = _PARALLEL_EXTRACTION_BACKEND if _PARALLEL_EXTRACTION_BACKEND in ("threads", "processes") else "threads"
        if verbose:
            print(
                f"build_index: graph extraction parallel — "
                f"{worker_count} {backend}, "
                f"{len(code_work_items)} code files (threshold "
                f"{_PARALLEL_EXTRACTION_THRESHOLD})",
                flush=True,
            )

        def _pdbg(msg: str) -> None:
            if verbose:
                try:
                    import threading as _t
                    thread_names = sorted(t.name for t in _t.enumerate())
                    thread_suffix = f" [threads={len(thread_names)}: {','.join(thread_names[:6])}{'...' if len(thread_names) > 6 else ''}]"
                except Exception:
                    thread_suffix = ""
                print(f"build_index: [parallel-debug] {msg}{thread_suffix}", flush=True)

        # Wave 1p2q3 (1p2wd post-ship 1.3.28): pass parent's pre-loaded state
        # and gitattrs patterns to every worker. With threads this is a free
        # reference share; with processes it's a per-task pickle cost the
        # operator accepts when opting into the process backend. Eliminates
        # 1,542× redundant `_load_state()` JSON parses + `.gitattributes`
        # disk reads that serialized on the GIL under thread parallelism
        # (field kernel-sample histogram: 43% of samples in mutex/condvar
        # waits, classic GIL thrashing from sequential Python work).
        _shared_state = session._state
        _shared_gitattrs = session._gitattrs_patterns or frozenset()
        worker_args = [
            (rel, text, str(root), layer, gitattrs_list, walker_version, chunker_version, _shared_state, _shared_gitattrs)
            for rel, text in code_work_items
        ]

        if backend == "threads":
            # Wave 1p2q3 (1p2wd post-ship 1.3.27 / Bug 4 finale): thread backend.
            # Process-mode parallel-4 ran 1.6× SLOWER than serial on the field
            # 1,542-file workload across both batch=24 (44.0s) and batch=128
            # (45.2s) — disproving the IPC-amortization hypothesis. The
            # dominant overhead was spawn-mode worker boot (each worker re-
            # imports tree-sitter from scratch) plus per-task pickle. Threads
            # eliminate both: shared interpreter state means tree-sitter loads
            # once in the parent; result return is a direct Python reference
            # with no pickle. Tree-sitter parsers release the GIL during
            # parse, so the per-file hot path still parallelizes across cores.
            # Theoretical ceiling ~1.3-1.5× over serial; we expect to actually
            # hit something close to that since the IPC cost we'd been
            # paying with processes is now ~zero.
            from concurrent.futures import ThreadPoolExecutor
            _pdbg(f"thread backend: constructing ThreadPoolExecutor (max_workers={worker_count})")
            try:
                with ThreadPoolExecutor(
                    max_workers=worker_count,
                    thread_name_prefix="wavefoundry-extract",
                ) as pool:
                    _pdbg("pool entered; iterating pool.map")
                    _seen = 0
                    for rel_path, entry in pool.map(_extract_artifact_for_worker, worker_args):
                        _seen += 1
                        if _seen == 1:
                            _pdbg(f"first task returned: rel_path={rel_path!r}")
                        elif _seen % 250 == 0:
                            _pdbg(f"progress: {_seen}/{len(worker_args)} tasks returned")
                        if entry is not None:
                            session.pending_code[rel_path] = entry
                    _pdbg(f"pool drained: {_seen} task results consumed")
            except Exception as exc:
                if verbose:
                    print(
                        f"build_index: parallel extraction (threads) failed "
                        f"({type(exc).__name__}: {exc}); falling back to serial",
                        flush=True,
                    )
                for rel, text in code_work_items:
                    session.record_file(rel, text)
        else:
            # Process-mode backend (opt-in via WAVEFOUNDRY_GRAPH_PARALLEL_BACKEND=processes).
            # Kept for benchmarking and for any workload where the Python-side
            # walker (GIL-bound) dominates parse time enough that spawn overhead
            # amortizes. The chunked-bounded-in-flight + spawn-mode + sys.path
            # mutation + worker initializer + per-task git-subprocess gating
            # all stay in place. See full root-cause analysis in
            # `docs/waves/1p2q3 field-feedback-round-4/1p2wd-bug parallel-
            # extraction-fork-deadlock-spawn-mode-fix.md`.
            _pdbg("step 1/8: worker_args built (process backend)")
            from concurrent.futures import ProcessPoolExecutor
            chunksize = max(1, len(worker_args) // (worker_count * 4))
            start_method = os.environ.get("WAVEFOUNDRY_GRAPH_PARALLEL_START_METHOD", "spawn")
            _pdbg(f"step 4/8: getting mp context for start_method={start_method!r} (chunksize={chunksize})")
            # Wave 1p8gu (review fix MP-1): window-free mp context so spawn workers do not each flash a
            # console window on Windows (pythonw.exe). Returns None on Windows without pythonw → the
            # `mp_ctx is None` branch below falls back to serial extraction (no worker windows).
            mp_ctx = subprocess_util.windowless_mp_context(start_method)
            _pdbg(f"step 5/8: mp_ctx acquired ({type(mp_ctx).__name__ if mp_ctx is not None else 'None'})")
            graph_indexer_path = str(Path(__file__).resolve())
            graph_indexer_dir = str(Path(graph_indexer_path).parent)
            path_inserted = False
            if graph_indexer_dir not in sys.path:
                sys.path.insert(0, graph_indexer_dir)
                path_inserted = True
            _pdbg(f"step 6/8: sys.path[0]={sys.path[0]!r} (path_inserted={path_inserted})")
            try:
                if mp_ctx is None:
                    for rel, text in code_work_items:
                        session.record_file(rel, text)
                else:
                    try:
                        _pdbg(
                            f"step 7/8: constructing ProcessPoolExecutor "
                            f"(max_workers={worker_count}, initializer=_worker_init_graph_indexer)"
                        )
                        from concurrent.futures import wait as _wait, FIRST_COMPLETED
                        batch_size = max(1, min(128, len(worker_args) // (worker_count * 3)))
                        batches = [
                            worker_args[i:i + batch_size]
                            for i in range(0, len(worker_args), batch_size)
                        ]
                        _pdbg(f"batched {len(worker_args)} tasks into {len(batches)} batches of up to {batch_size}")
                        with ProcessPoolExecutor(
                            max_workers=worker_count,
                            mp_context=mp_ctx,
                            initializer=_worker_init_graph_indexer,
                            initargs=(graph_indexer_path,),
                        ) as pool:
                            _pdbg("step 8/8: pool entered; about to bounded-in-flight submit batches (workers will spawn on first submit)")
                            batch_iter = iter(batches)
                            in_flight: set = set()
                            for _ in range(worker_count):
                                try:
                                    next_batch = next(batch_iter)
                                except StopIteration:
                                    break
                                in_flight.add(pool.submit(_extract_artifacts_for_worker_batch, next_batch))
                            _pdbg(f"pre-warm: submitted {len(in_flight)} batches (one per worker); waiting for first result")
                            _seen = 0
                            while in_flight:
                                done, in_flight = _wait(in_flight, return_when=FIRST_COMPLETED)
                                for fut in done:
                                    batch_results = fut.result()
                                    for rel_path, entry in batch_results:
                                        _seen += 1
                                        if _seen == 1:
                                            _pdbg(f"first task returned: rel_path={rel_path!r} (workers confirmed spawned)")
                                        elif _seen % 250 == 0:
                                            _pdbg(f"progress: {_seen}/{len(worker_args)} tasks returned")
                                        if entry is not None:
                                            session.pending_code[rel_path] = entry
                                    try:
                                        next_batch = next(batch_iter)
                                        in_flight.add(pool.submit(_extract_artifacts_for_worker_batch, next_batch))
                                    except StopIteration:
                                        pass
                            _pdbg(f"pool drained: {_seen} task results consumed")
                    except Exception as exc:
                        if verbose:
                            print(
                                f"build_index: parallel extraction failed "
                                f"({type(exc).__name__}: {exc}); falling back to serial",
                                flush=True,
                            )
                        for rel, text in code_work_items:
                            session.record_file(rel, text)
            finally:
                if path_inserted:
                    try:
                        sys.path.remove(graph_indexer_dir)
                    except ValueError:
                        pass
    else:
        for rel, text in code_work_items:
            session.record_file(rel, text)

    # Doc/seed files always sequential (need cross-file symbol_terms).
    for rel, text in doc_work_items:
        session.record_file(rel, text)

    try:
        payload = session.finalize()
    finally:
        # Close on every path — a fault mid-finalize must not leak the store
        # connection (the SQLite transaction rolls back on close).
        session.close_store()
    if verbose:
        counts = payload.get("counts") or {}
        print(
            f"build_index: graph extraction wrote {layer} graph — "
            f"{counts.get('nodes', 0)} nodes, {counts.get('edges', 0)} edges",
            flush=True,
        )
        # 1p9qe loudness: per-file SQL DDL-recovery counts (module nodes
        # carry them, so this survives worker-process extraction).
        for _node in payload.get("nodes") or []:
            _regions = int(_node.get("sql_error_regions") or 0)
            _partial = int(_node.get("sql_partial_bodies") or 0)
            if _regions or _partial:
                print(
                    _sql_recovery_log_line(
                        str(_node.get("id") or ""),
                        _regions,
                        int(_node.get("sql_recovered_definitions") or 0),
                        int(_node.get("sql_unrecovered_regions") or 0),
                        _partial,
                        int(_node.get("sql_partial_bodies_recovered") or 0),
                    ),
                    flush=True,
                )
        # 1p9q6 loudness: per-file line-scan degraded-extraction counts
        # (module nodes carry them, so this survives worker-process
        # extraction — the 1p9qe pattern). A file past the scan-byte ceiling
        # is a LOUD skip, never silent (AC-3/AC-4).
        _line_scan_files = 0
        _line_scan_ceiling_skips = 0
        for _node in payload.get("nodes") or []:
            if _node.get("line_scan_ceiling_skipped"):
                _line_scan_ceiling_skips += 1
                print(
                    _line_scan_log_line(str(_node.get("id") or ""), 0, 0, 0, ceiling_skipped=True),
                    flush=True,
                )
            elif "line_scan_defines" in _node:
                _line_scan_files += 1
                print(
                    _line_scan_log_line(
                        str(_node.get("id") or ""),
                        int(_node.get("line_scan_defines") or 0),
                        int(_node.get("line_scan_imports") or 0),
                        int(_node.get("line_scan_skipped") or 0),
                    ),
                    flush=True,
                )
        if _line_scan_files or _line_scan_ceiling_skips:
            print(
                f"build_index: line-scan degraded extraction — {_line_scan_files} "
                f"file(s) over the AST parse cap, {_line_scan_ceiling_skips} past "
                f"scan-ceiling skip(s)",
                flush=True,
            )
        # R7 (wave 1rrx5): clustering-asymmetry measurement — surface hot
        # write-target data-layer nodes so the writes/maps_to clustering-
        # exclusion decision can be made on evidence. Read-only.
        for _hot in sql_hot_data_layer_nodes(payload):
            print(
                f"build_index: sql hot data-layer node {_hot['id']} "
                f"({_hot['sql_kind']}) — {_hot['in_degree']} incoming "
                f"writes/maps_to",
                flush=True,
            )
    # Wave 1p2q3 (1p2tf): Nx project-structure detection — diagnostic only this
    # round. Presence at repo root surfaces in the payload so consumers can
    # report a per-build hint when investigating low TS receiver-resolved rates.
    try:
        if (root / "nx.json").is_file():
            payload["nx_project_detected"] = True
    except OSError:
        pass
    return payload


def read_graph_payload(root: Path, layer: str = "project") -> dict[str, Any]:
    # Wave 1p4ww: single project graph — the framework graph layer was removed.
    if layer not in GRAPH_FILENAMES:
        raise ValueError(f"Unsupported graph layer: {layer}")
    index_dir = root / ".wavefoundry" / "index"
    graph_path = index_dir / GRAPH_DIRNAME / GRAPH_FILENAMES[layer]
    payload = _read_json(graph_path, {})
    if isinstance(payload, dict) and payload:
        payload.setdefault("layer", layer)
        payload.setdefault("schema_version", GRAPH_SCHEMA_VERSION)
        payload.setdefault("nodes", [])
        payload.setdefault("edges", [])
        payload.setdefault("counts", {"files": 0, "nodes": len(payload.get("nodes") or []), "edges": len(payload.get("edges") or [])})
        payload["present"] = True
        payload["graph_path"] = str(graph_path.relative_to(root)).replace("\\", "/")
        return payload
    return {
        "layer": layer,
        "schema_version": GRAPH_SCHEMA_VERSION,
        "present": False,
        "graph_path": str(graph_path.relative_to(root)).replace("\\", "/"),
        "nodes": [],
        "edges": [],
        "counts": {"files": 0, "nodes": 0, "edges": 0},
    }
