# ORM mapping: bind JPA and EF entity classes to SQL table nodes via declared table-name annotations

Change ID: `1p9qg-enh orm-entity-table-mapping`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-07-03
Wave: TBD

## Rationale

ORM entities are the other half of code↔database visibility: `1p9qf` covers explicit SQL, but most enterprise data access flows through JPA/Hibernate (Java) and EF Core (C#) entities, where the table name lives in a declaration — Java `@Entity` + `@Table(name = "users")`, C# `[Table("users")]` (System.ComponentModel.DataAnnotations.Schema) or `ToTable("users")` fluent configuration. The Java extractor already captures annotation **names** as a node property (`_ts_extract_java_annotations`, `graph_indexer.py:5105`, attached at `:6625-6628`) but not their **arguments**, so the mapping fact is seen and discarded.

Binding entity class → table node (declared-name, unique-match, `LITERAL_DERIVED`) makes impact flow across the object-relational seam: refactoring a table shows the entities riding it and — through existing `calls` edges into repository/service layers — the code above them. It also lays the ground for future JPQL binding (deliberately excluded from `1p9qf`): once entities map to tables, entity-referencing queries can bind transitively without guessing.

Scope discipline: declared names only. Convention-derived names (JPA's default snake-casing of class names, EF pluralization conventions) are refused in this change — deriving them means reimplementing each ORM's naming strategy, wrong versions of which produce exactly the silent mis-binds the confidence taxonomy forbids. Convention support, if ever, arrives as its own measured change.

## Requirements

1. **Annotation-argument capture.** The Java annotation machinery gains argument capture for a fixed vocabulary (`@Table(name=...)`, `@Entity(name=...)`, plus `@NamedNativeQuery` already relevant to `1p9qf`) — built as the shared seam `1p9qf` ws1 also uses. C# attribute arguments (`[Table("...")]`) capture analogously in the C# extractor; EF `ToTable("...")` call-shape capture follows the `1p9qf` sink pattern with origin checks.
2. **Mapping edge.** An entity class with a declared table name binds class → table node (`maps_to`-family edge, or `reads` with a mapping property — same representation decision process as `1p9qd`'s write edges, decided by consumer sweep) at `LITERAL_DERIVED` confidence, unique-match-or-drop against SQL-defined tables (schema-qualified first via `@Table(schema=...)` when present); no match → `external::sql::<table>` (the `1p9qf` namespace).
3. **Refusals.** `@Entity` with no `@Table` and no explicit name binds nothing (convention refusal, logged as a counted unbound-convention case so the gap is visible); dynamic/computed names refuse; two tables matching one declared name refuse.
4. **Impact semantics.** The mapping edge participates in impact traversal (table → entities → their callers) at literal-edge weighting; path search treats it as structural.
5. **Version bump + census + adversarial review.** `GRAPH_BUILDER_VERSION` bumped; the mapping shares `1p9qf`'s real-corpus locality census (entity counts, declared-name rate vs convention rate, bind rate, ≥95% precision hand-sample); adversarial review lane at wave review.

## Scope

**Problem statement:** Entity classes' declared table mappings are parsed but discarded (names captured, arguments dropped), leaving the object-relational seam invisible even when both the entity and the DDL are in-repo.

**In scope:**

- Annotation/attribute argument capture (shared seam with `1p9qf`); EF `ToTable` sink.
- The mapping edge with unique-match/refusal semantics, namespaced externals, impact weighting.
- Convention-refusal counters; census participation; fixtures; version bump.

**Out of scope:**

- Convention-derived table names (JPA implicit naming, EF pluralization) — explicit standing refusal in this change; revisit only with a measured, per-ORM strategy proposal.
- JPQL/HQL query binding (future layer on top of this mapping).
- Column-level mapping (`@Column`) — table-level is the impact tier.
- Other ORMs (Hibernate XML mappings, Doctrine, ActiveRecord) — extensible vocabulary, added on field evidence.

## Acceptance Criteria

- [ ] AC-1: Java — `@Entity @Table(name="users")` (and schema-qualified form) binds the class to the unique matching table node with the chosen mapping representation at `LITERAL_DERIVED`; `@Entity` alone binds nothing and increments the convention counter. Exact-set unit tests.
- [ ] AC-2: C# — `[Table("users")]` and `ToTable("users")` (origin-checked) bind analogously; impostor `ToTable` on a non-EF type refuses. Unit tests.
- [ ] AC-3: Refusals — ambiguous table match drops; computed/constant-reference names refuse (only string literals bind); unmatched names emit `external::sql::` targets. Adversarial unit tests.
- [ ] AC-4: Impact — `code_impact` on a table reaches its mapped entities and their existing callers at down-weighted confidence (fixture graph test).
- [ ] AC-5: Census — the `1p9qf` corpus census includes entity mapping metrics (declared vs convention rate, bind rate, precision sample) recorded in the Progress Log; the annotation-argument seam is shared with `1p9qf`, verified by both changes' tests passing on one build.
- [ ] AC-6: `GRAPH_BUILDER_VERSION` bumped; adversarial review lane run and findings dispositioned; `python3 .wavefoundry/framework/scripts/run_tests.py` passes; `wave_validate` clean; no `__pycache__` under `scripts/`.

## Tasks

- [ ] Build/extend the annotation-argument capture seam (Java) and attribute-argument capture (C#); EF `ToTable` sink with origin check.
- [ ] Mapping-edge emission with unique-match/refusal semantics + namespaced externals + convention counters; representation decided by the shared consumer sweep.
- [ ] Impact/path weighting for the mapping edge.
- [ ] Fixtures/tests per AC-1..AC-4; census metrics with `1p9qf`.
- [ ] Bump `GRAPH_BUILDER_VERSION`; run `run_tests.py` + `wave_validate`; clean `__pycache__`.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| ws1-argument-capture | implementer | — | Annotation/attribute argument seam (shared with `1p9qf`); EF sink. |
| ws2-mapping-edges | implementer | ws1-argument-capture | Edge emission, refusals, externals, counters, weighting. |
| ws3-tests-census | implementer | ws2-mapping-edges | Fixtures; census metrics alongside `1p9qf`. |
| ws4-adversarial-review | reviewer | ws3-tests-census | Faithfulness red-team: convention temptation, impostor sinks, wrong-table binds. |


## Serialization Points

- The annotation-argument seam is shared with `1p9qf` ws1 — build once, in whichever change lands first; the other consumes it.
- The mapping-edge representation follows the same consumer-sweep decision as `1p9qd`'s write edges — one sweep, both decisions.
- Shares the census corpus and pass with `1p9qf` (one census, two metric sections).
- Single wave-level `GRAPH_BUILDER_VERSION` bump.

## Affected Architecture Docs

`docs/specs/mcp-tool-surface.md` capability notes: the entity→table mapping surface and its refusal stance (declared names only — the convention refusal is a standing decision worth recording where the graph model is described, so it isn't re-litigated per wave).

## AC Priority

(Populated at Prepare wave.)


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | JPA declared-name mapping is the primary surface. |
| AC-2 | required | C# parity per the wave's operator-directed scope. |
| AC-3 | required | The refusal set is what separates this from a naming-convention guesser. |
| AC-4 | required | The mapping edge exists to make impact flow; untested weighting would corrupt results. |
| AC-5 | required | Standing literal-edge census rule; the shared seam must be proven shared. |
| AC-6 | required | Standing version/adversarial/merge gates. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-03 | Scoped from the Java/SQL accuracy investigation. Confirmed: annotation names captured but arguments discarded (`graph_indexer.py:5105,6625-6628`); no ORM idiom coverage anywhere (grep-confirmed); SQL table nodes resolvable (live-verified); design mirrors `reads_config`/`1p9qf` discipline with declared-names-only stance. | Guru investigation 2026-07-03. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-03 | Declared table names only; conventions refused and counted (approach A). | Convention derivation means reimplementing each ORM's (version-dependent) naming strategy; a wrong strategy silently mis-binds — the exact failure the confidence taxonomy exists to prevent. Counting refusals makes the recall cost measurable, so a future convention change is evidence-based. | (B) Implement JPA/EF default naming strategies — weakness: version- and configuration-dependent (physical naming strategies are pluggable); silent wrongness at scale. (C) Fuzzy name matching (class `User` ≈ table `users`) — weakness: a guess with a similarity threshold; rejected outright. |
| 2026-07-03 | Separate change from `1p9qf` despite the shared seam. | Different evidence classes (declaration facts vs query-text analysis) with different failure modes and different census metrics; the shared argument-capture seam is a build-once coordination point, not a reason to entangle review scopes. | Fold into `1p9qf` — rejected: would make the wave's largest change larger and blur two distinct faithfulness arguments. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Declared-name-only scope yields low coverage on convention-heavy codebases. | The convention counter + census quantify exactly how much is left on the table (literally); the decision to chase it becomes evidence-based rather than speculative. |
| Attribute/annotation argument parsing variance (constants as arguments, `@Table(name = TABLE_NAME)`). | Only string literals bind; constant references refuse (AC-3) — a future change could resolve same-file `static final` constants (the graph already models them) but that is explicitly deferred. |
| Shared seam drift between this and `1p9qf` (two changes touching one new mechanism). | Serialization point: build once in the first-landing change; the second change's tests run against the shared implementation; wave integration verifies both green on one build. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
