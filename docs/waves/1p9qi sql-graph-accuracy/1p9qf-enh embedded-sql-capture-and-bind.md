# Embedded SQL: capture SQL string literals at known Java/C# sinks and bind code to table nodes

Change ID: `1p9qf-enh embedded-sql-capture-and-bind`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-07-03
Wave: TBD

## Rationale

Nothing today detects SQL inside host-language code: grep-confirmed zero hits for `@Query`, `prepareStatement`, `JdbcTemplate`, MyBatis, Dapper, or EF anywhere in `graph_indexer.py`/`graph_di_signals.py` (guru investigation, 2026-07-03). Yet the machinery to do it faithfully is precedented three times over:

- the `reads_config` literal pipeline — shape-gated capture → distinctiveness gate → **unique-match-or-drop** → `LITERAL_DERIVED` confidence (`graph_indexer.py:7543-7591`, `_config_literal_is_distinctive` `:424`);
- the AOP matcher-string capture — walk string arguments of a fixed call-shape vocabulary (`_java_aop_matcher_strings`, `graph_indexer.py:4945`);
- SQL table nodes already exist and cross-file resolve (live-verified), and enterprise repos typically carry their DDL in-repo as Flyway/Liquibase migration `.sql` files — which this indexer already indexes.

The capability this unlocks is the one enterprises actually ask of a code graph: **code ↔ database impact** — "which services touch table X", "what breaks when this table is refactored". Design mirrors `reads_config` exactly: a per-language **capture stage** collects SQL-candidate literals only at known sinks, and a finalize **bind stage** extracts referenced tables (via `1p9qd`'s statement unit) and binds method → table at `LITERAL_DERIVED` confidence on unique match. Dynamic/concatenated SQL stays unbound; missing schema binds to `external::<table>` honestly.

A standing field lesson gates this change: **literal-derived edges must census target locality on a real repo before shipping** — synthetic fixtures hide false positives, and a literal family whose targets are mostly out-of-project binds nothing useful (the OTel `instruments` precedent). The census is an explicit AC, not a footnote.

## Requirements

1. **Java capture sinks.** SQL-candidate literals are collected only from: MyBatis annotations (`@Select`/`@Insert`/`@Update`/`@Delete`), Spring/JPA `@Query(..., nativeQuery=true)` and `@NamedNativeQuery` values, JDBC `prepareStatement(...)`/`prepareCall(...)` string arguments, and `JdbcTemplate`/`NamedParameterJdbcTemplate` query-method string arguments. Sink identification is alias-aware and import-origin-checked where checkable (same discipline as `1p9q7`): a user-defined `prepareStatement` on a non-JDBC type must not fire when the receiver type is resolvable to a non-JDBC class.
2. **C# capture sinks.** `new SqlCommand("...")` (and `CommandText = "..."` assignment), Dapper extension calls (`Query`/`Query<T>`/`Execute`/`ExecuteScalar`/`QueryFirst*` with a string first-arg), EF `FromSqlRaw`/`ExecuteSqlRaw`(+`Async`). Same origin-checking discipline where the receiver/namespace is resolvable.
3. **MyBatis XML mappers.** Mapper XML files (`<mapper namespace=...>` with `<select>/<insert>/<update>/<delete>` elements — XML mode already parses markup) contribute statement text with the owning mapper interface/namespace as the source symbol.
4. **SQL sniff gate.** A captured literal enters the pipeline only if it sniffs as SQL: leading keyword in {SELECT, INSERT, UPDATE, DELETE, WITH, MERGE, CALL, EXEC} after whitespace/parens, case-insensitive. Non-SQL strings at the sinks (rare) drop silently; SQL-looking strings NOT at a sink are never captured (no repo-wide literal trawling).
5. **Bind stage.** At finalize, each captured statement runs through `1p9qd`'s statement-analysis unit; each referenced table binds source-method → table node with a `reads`-family edge (read/write kind per the `1p9qd` representation) at `LITERAL_DERIVED` confidence, only when the table name (schema-qualified first, then bare) matches exactly **one** SQL-defined node; ambiguity drops the edge; no SQL-defined match emits `external::sql::<table>` (a namespaced external so host-language symbols named like tables can never collide).
6. **Dynamic SQL refusal.** Only single-literal arguments and adjacent compile-time string concatenation of literals bind; anything involving variables, formatting, or builders is refused (counted in the build log as unbound-dynamic, so the gap is visible).
7. **JPQL exclusion.** Non-native `@Query` (JPQL) is out of scope — it references entities, not tables; entity→table mapping is `1p9qg`'s job. The capture explicitly checks `nativeQuery=true` for `@Query`.
8. **Locality census (gating).** Before the bind stage ships enabled, run capture+bind on at least one real enterprise-shaped repo (or the most realistic available corpus) and record: sink hit counts, sniff pass rate, bind rate vs external rate, and a hand-verified precision sample (≥30 bound edges, ≥95% correct). If in-project bind rate is negligible (schema not in repo), the feature still ships (external edges are honest) but the census result is recorded and the default-on decision revisited.
9. **Version bump + adversarial review.** `GRAPH_BUILDER_VERSION` bumped; adversarial faithfulness review at wave review (this is a new literal-derived binding surface — the exact class the standing rule exists for).

## Scope

**Problem statement:** SQL embedded in Java/C# data-access code is invisible to the graph, so code↔database impact questions are unanswerable even when the repo contains both the queries and the DDL they target.

**In scope:**

- Java/C# sink capture (AST-anchored, origin-checked), MyBatis XML mappers, the SQL sniff gate.
- Finalize bind via the `1p9qd` unit with unique-match-or-drop, `LITERAL_DERIVED`, namespaced externals, dynamic refusal with visible counts.
- Locality census on a real corpus with precision sample; exact-set fixtures; version bump.

**Out of scope:**

- JPQL/HQL and entity-based queries (`1p9qg` owns entity→table mapping; JPQL binding would layer on it later).
- Python/Go/TS SQL sinks (the sink table is extensible; start where the operator's enterprise need is — Java/C#).
- SQL string reconstruction across variables/builders (StringBuilder chains, criteria APIs) — refused by design.
- Stored-procedure argument tracing (`CALL proc(?)` binds to the procedure node if `1p9qe` recovered it; tracing arguments does not).

## Acceptance Criteria

- [ ] AC-1: Java — each sink form (MyBatis annotations, native `@Query`, `prepareStatement`, `JdbcTemplate` methods) captures its literal and binds method → table for a fixture repo containing matching migration DDL; JPQL `@Query` without `nativeQuery=true` captures nothing. Exact-set unit tests per sink.
- [ ] AC-2: C# — each sink form (`SqlCommand`/`CommandText`, Dapper, EF raw) captures and binds analogously. Exact-set unit tests per sink.
- [ ] AC-3: MyBatis XML mapper statements bind with the mapper namespace/interface as source. Unit-tested.
- [ ] AC-4: Faithfulness negatives — same-named non-JDBC/non-Dapper impostor methods don't fire; SQL-looking strings outside sinks are never captured; dynamic/concatenated-with-variable SQL refuses and is counted; ambiguous table names (two `users` tables) drop the edge; unmatched tables emit namespaced `external::sql::` targets only. Adversarial unit tests each. 
- [ ] AC-5: All bound edges carry `LITERAL_DERIVED` confidence and are down-weighted in impact/path exactly as existing literal edges are (consumer parity test).
- [ ] AC-6: Locality census recorded in the Progress Log per Requirement 8, including the hand-verified ≥95% precision sample; the default-on decision is explicit in the Decision Log after the census.
- [ ] AC-7: `GRAPH_BUILDER_VERSION` bumped; adversarial review lane run and findings dispositioned; `python3 .wavefoundry/framework/scripts/run_tests.py` passes; `wave_validate` clean; no `__pycache__` under `scripts/`.

## Tasks

- [ ] Java sink capture in the Java extraction path (annotations via the captured-annotations machinery + argument capture; call-shape sinks via AST with origin checks).
- [ ] C# sink capture in the C# extraction path (same discipline).
- [ ] MyBatis XML mapper statement capture in markup mode.
- [ ] Sniff gate + capture buffering (mirroring `config_read_candidates` plumbing).
- [ ] Finalize bind stage: `1p9qd` unit → unique-match-or-drop → `LITERAL_DERIVED` edges → namespaced externals → dynamic-refusal counters + logging.
- [ ] Exact-set + adversarial fixtures per AC-1..AC-5.
- [ ] Locality census on a real corpus; precision sample; Decision Log entry for default-on.
- [ ] Bump `GRAPH_BUILDER_VERSION`; run `run_tests.py` + `wave_validate`; clean `__pycache__`.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| ws1-java-capture | implementer | — | Java sinks (annotation args + call shapes, origin-checked) + sniff gate + buffering. |
| ws2-csharp-capture | implementer | — | C# sinks (parallel; different extractor). |
| ws3-mybatis-xml | implementer | — | Mapper XML statement capture (parallel; markup mode). |
| ws4-bind-stage | implementer | ws1-java-capture | Finalize bind via the `1p9qd` unit; unique-match; externals; counters. |
| ws5-tests-census | implementer | ws2-csharp-capture, ws3-mybatis-xml, ws4-bind-stage | Exact-set/adversarial fixtures; real-corpus locality census + precision sample. |
| ws6-adversarial-review | reviewer | ws5-tests-census | Faithfulness red-team: sink impostors, sniff bypasses, wrong-table binds, census honesty. |


## Serialization Points

- Hard dependency on `1p9qd`'s statement-analysis unit (freeze its signature first) and soft dependency on `1p9qc` (clean SQL candidate space) and `1p9qe` (procedure nodes as CALL targets).
- The annotation-argument capture mechanism (ws1) should be built once and shared with `1p9qg` (`@Table` arguments) — coordinate the seam.
- Single wave-level `GRAPH_BUILDER_VERSION` bump.

## Affected Architecture Docs

`docs/specs/mcp-tool-surface.md` capability notes gain the embedded-SQL surface (sinks, confidence, refusal semantics). The census outcome and the default-on decision are decision-record material. Cross-boundary note: this creates the first code→data-layer edge family — worth a short architecture note wherever the graph model is described.

## AC Priority

(Populated at Prepare wave.)


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | Java sinks are the primary enterprise surface. |
| AC-2 | required | C# sinks are the operator-directed second surface. |
| AC-3 | important | MyBatis XML is widespread in the Java enterprise but is one idiom among the required set. |
| AC-4 | required | The faithfulness negatives are what keep a literal-derived surface from polluting the graph. |
| AC-5 | required | Confidence parity keeps downstream weighting sound. |
| AC-6 | required | The standing field lesson: literal-edge families ship only with a real-corpus locality census. |
| AC-7 | required | Standing version/adversarial/merge gates. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-03 | Scoped from the Java/SQL accuracy investigation. Confirmed: zero existing SQL-in-literal detection (case-insensitive grep of both modules); `reads_config` pipeline is the design template (`graph_indexer.py:7543-7591,:424`); AOP string-arg capture precedent (`:4945`); SQL table nodes cross-file resolve (live-verified); annotations captured but arguments not. Field lesson applied: locality census required before literal-edge families ship. | Guru investigation 2026-07-03. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-03 | Two-stage capture/bind mirroring `reads_config`, sink-gated, unique-match-or-drop, `LITERAL_DERIVED` (approach A). | Reuses the proven faithful-literal-binding discipline end to end; sink gating keeps capture O(known idioms) instead of O(all strings); the `1p9qd` unit provides table extraction without a second SQL parser; namespaced externals prevent cross-domain symbol collisions. | (B) Repo-wide SQL-sniffing of all string literals — weakness: false-positive surface scales with every string in the repo; sink knowledge is what makes precision achievable. (C) Regex-only capture (no AST) — weakness: the exact string/comment failure mode `1p9q7` rejects; both extractors already hold trees. (D) Defer until a SQL-lineage product need is proven — weakness: the operator has named the enterprise need now; the census requirement bounds the downside. |
| 2026-07-03 | Native-SQL only; JPQL excluded pending `1p9qg`. | JPQL names entities, not tables; binding it to tables requires the entity→table mapping layer — doing both in one change entangles two evidence classes. | Include JPQL via naive entity-name≈table-name matching — rejected: that is a guess, precisely what the confidence taxonomy forbids. |
| 2026-07-03 | `external::sql::` namespace for unmatched tables. | A bare `external::users` could collide with a host-language symbol candidate set; namespacing keeps the SQL domain's externals disjoint by construction. | Bare externals — rejected: cross-domain candidate pollution is a silent-wrong-bind vector the adversarial review would flag anyway. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Sink impostors (user types with `Query`/`Execute` methods) over-fire. | Origin checks where the receiver/namespace resolves; sniff gate as second filter; refusal when origin is ambiguous; adversarial impostor tests (AC-4); `LITERAL_DERIVED` down-weighting bounds damage. |
| Schema not in repo → mostly `external::sql::` edges, low perceived value. | Explicitly anticipated: census (AC-6) measures it, externals are still honest "this code runs SQL against table X" facts, and the default-on decision is made on the census evidence, not hope. |
| Table-name ambiguity across schemas/environments (dev vs prod DDL both in repo). | Schema-qualified match first; bare-name binds only on repo-wide uniqueness; ambiguity drops. The migration fixture in `1p9qd` AC-7 doubles as the multi-DDL testbed. |
| Capture stage slows Java/C# extraction. | Sinks are checked only at annotation/call nodes already visited; sniff is O(prefix); measured in the calibration pass. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
