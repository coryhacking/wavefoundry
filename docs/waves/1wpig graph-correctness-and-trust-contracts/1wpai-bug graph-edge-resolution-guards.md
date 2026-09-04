# Add Type and Provenance Guards to Graph Edge Resolution

Change ID: `1wpai-bug graph-edge-resolution-guards`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-09-04
Wave: 1wpig graph-correctness-and-trust-contracts

## Rationale

Graph finalization can rewrite an external call to the only project node with the same simple name even when that node is a non-callable JSON key. The live graph consequently claims `os.cpu_count()` calls a wave evidence field named `cpu_count`. Generic JSON-schema traversal also receives `reads_config` edges to a test fixture merely because generic keys such as `properties` are unique in a file whose name contains `config`. These false edges contaminate call hierarchy, impact, risk, path, dependency, and community analysis.

## Requirements

1. `calls` edge rewriting SHALL accept only code-origin function, method, or construction-compatible class targets appropriate to the source language and relation; structural JSON/YAML/data nodes SHALL never receive ordinary call edges.
   The discriminator SHALL be named rather than implied. No node record carries a language or origin field (the common shape is `{id, kind, label, layer, source_file, source_location}`, and the variants present in this repository add only value, chokepoint, entry-point, or collapsed-pair markers, while target repositories in other languages can add package, module, and statement-recovery markers, none of them a language or origin classifier either), and the reproduced phantom target's `kind` is `class`, which is the same kind config-key nodes are minted with, so a kind-based guard admits the defect it exists to remove. The rule is therefore exactly this and nothing more: a `calls` edge SHALL NOT target any node satisfying `graph_indexer._is_json_config_node_id`. The guard SHALL be placed immediately before the single return of `_resolve_external_call_target`, which has ten separate branches that assign a resolved target, so a per-branch implementation is ten edits and will miss some. No additional language or origin classifier SHALL be introduced for this purpose. The predicate covers `.json`, `.jsonc`, `.properties`, `.yml`, and `.yaml`, so the opening sentence's wider reference to data nodes is bounded by that list: `.toml` key nodes are an accepted residual, measured on builder version 45 at six present and zero incoming call edges, and `.xml` is not a key-node population at all, since the indexer treats that extension only as mapper markup. Neither is a coverage claim. Measured on builder version 45 that predicate is exactly separating, covering every structural-node call target, 115 on the planning-time graph and 123 re-derived across a rebuild of both sides, and none of the 17,143 Python and JavaScript targets, while both path-keyed classifiers the module already has invert: `_ts_language_key_for_path` returns `None` for `.py`, so deriving eligibility from it would delete every Python call edge, and `_CODE_EXTENSIONS` contains `.json`, so deriving eligibility from it would admit every phantom.
2. An incompatible sole name match SHALL leave the original external/unresolved target intact.
3. `reads_config` attribution SHALL retain the existing target-side gate as sufficient provenance, and SHALL add precision levers that remove the false family without narrowing the true one. The existing gate is `graph_indexer._is_config_file_path`, plus `graph_indexer._config_literal_is_distinctive`, plus the unique-match requirement in the finalize bind. That gate produces every true edge in this repository today and SHALL NOT be rendered insufficient by this change.
   The precision levers are target-side and recall-safe by construction. A JSON Schema document, identified by a `*.schema.json` basename, is not a config instance and SHALL NOT be a config target. A `$schema` key SHALL NOT be used as that signal. Real project config instances routinely declare a schema: the reproduced false-set fixture `specs/negatives/tsconfig.json` carries a schemastore `$schema`, which is exactly what a genuine `tsconfig.json` looks like, and this change ships to every target repository where that signal would silently drop true edges. JSON Schema meta-vocabulary keys SHALL NOT bind, whether they appear as a bare literal or as the last segment of a dotted leaf path. The measured live list is `properties`, `definitions`, `description`, and `additionalProperties`; `required` and `items` cannot bind today because they already fail the length bar, and are named only so a future relaxation does not reintroduce them. A path under a test-fixture root SHALL NOT be a config target, and the change SHALL define that predicate as a named helper rather than an ad-hoc string test, because `graph_indexer` has no existing fixture-root constant and this lever ships to every target repository. Measured on builder version 45, the fixture-root lever alone removes all 64 false bindings, the schema-basename lever removes 62, and the meta-vocabulary lever removes 62 as specified above, missing only the two `compilerOptions` bindings, which are not meta-vocabulary at all. The last-segment half of that rule is load-bearing rather than decorative: `additionalProperties` occurs in the live false set only as the last segment of `properties.connections.additionalProperties` and never as a bare literal, so dropping it would make one of the four named keys unreachable on any live corpus, leaving its mandated fixture synthetic-only rather than grounded. Together the three remove 64 of 64 and retain 102 of 102. Because the live corpus cannot separate their contributions, each lever SHALL carry its own synthetic fixture, including an off-corpus control proving that a genuine project config file which declares a schema still binds.
   Loader provenance is ADDITIVE and SHALL NOT be a precondition for any edge the existing gate already binds. Spring `@Value`, `Environment.getProperty`, and `Environment.getRequiredProperty`, and Python receivers assigned from `json.load`, `yaml.safe_load`, or `tomllib.load`, MAY bind where the target-side gate cannot reach. Requiring loader provenance instead would delete the live true population: those reads are generic `.get` calls on receivers that cross one to three frames from loaders whose bodies call `json.loads` on a string rather than the modeled `json.load`, and 42 of them are read by test functions with no loader anywhere in the chain.
4. Structural JSON/YAML keys SHALL remain available for relations that legitimately target them.
5. A bounded same-root-cause census SHALL be two-sided. It SHALL report, before and after the repair, both the false-binding count and the retained-true-edge count against a named live positive set, and SHALL fail on any drop in that positive set the change document does not explain. The declared live positive set is every `reads_config` edge targeting `docs/workflow-config.json` or `docs/repo-profile.json`, measured at 102 of 166 total edges on builder version 45; the declared false set is every such edge targeting a schema document or a test fixture, measured at 64. A false-positive count alone SHALL NOT satisfy this requirement, because deleting the whole relation would score as a total success. The census SHALL also count, before and after, the `calls` edges targeting structural nodes that Requirement 1 removes, measured at 115 at planning time; both populations SHALL be re-derived from their predicates at implementation time rather than trusted as planning-time literals.
6. The repair SHALL bump `GRAPH_BUILDER_VERSION`, force unchanged-corpus re-extraction for existing indexes, and document the graph rebuild boundary. The constant to bump is the one declared in `graph_indexer.py`. `graph_cluster.py` declares a same-named module-level constant that is read only as an `or` fallback; editing that one satisfies no part of this requirement and a constant lookup returns both.

7. Execution of this change is ordered by the wave's mandatory sequence: no edit in this change may precede successful evaluator runs A and B as specified in `1wpaj` Requirement 9, and the wave was deliberately kept whole so those graph edits are gated by the hardened evaluator in the same wave. This precondition is restated here because an implementer handed only this document would otherwise see none.

## Scope

**Problem statement:** Cross-file simple-name and literal resolution converts unrelated repository data into executable or configuration dependencies.

**In scope:** Candidate indexes, call-target compatibility, config provenance, schema/test-fixture controls, graph fixtures, and full/incremental equivalence.

**Out of scope:** Removing JSON/YAML from the graph, dynamic-call inference, general type inference, and changing graph-query traversal costs.

## Acceptance Criteria

- [x] AC-1: `os.cpu_count()` plus a unique JSON `cpu_count` key retains an external call target and produces no project call edge.
- [x] AC-2: Equivalent collisions with documentation, YAML/config keys, and non-callable project symbols do not hijack calls.
- [x] AC-3: Generic schema processing produces no `reads_config` edge to schema documents, schema meta-vocabulary keys, or test fixtures; the removal is achieved by the target-side levers rather than by making loader provenance necessary, each lever carries its own synthetic fixture, an off-corpus control proves that a project config file declaring a schema still binds, and the fixture-root predicate is a named helper rather than an ad-hoc string test.
- [x] AC-4: Positive callable and constructor resolution retain their supported edges and confidence. The live positive set, defined by the AC-5 predicate and re-derived at implementation time rather than pinned to the 102 edges measured at planning, is a required positive control alongside the synthetic Spring and loader fixtures; every edge in the re-derived set is retained, and any drop is explained in the record. Schema documents, schema meta-vocabulary keys, and test-fixture paths do not bind. A run that satisfies only the synthetic controls does not satisfy this criterion.
- [x] AC-5: Full and incremental graph builds are equivalent for the new fixtures, and the live same-root-cause census reports before and after counts for BOTH the declared false set and the declared live positive set, with any unexplained drop in the positive set failing the criterion. The census also reports the before and after count of `calls` edges targeting structural nodes, measured at 115 at planning time, because that deletion is the wave's largest correction and is otherwise uncounted.
- [x] AC-6: Graph architecture documentation defines relation-compatible resolution and config provenance; this change's own suites and every test it adds pass, the documents this change authors or edits validate, and no failure elsewhere is attributable to this change.
- [x] AC-7: A pre-fix persisted graph is invalidated by the builder-version bump, re-extracts an otherwise unchanged corpus, and passes the post-rebuild live census.

## Tasks

- [~] Confirm before the first edit in this change that evaluator runs A and B have completed successfully, per Requirement 7 and `1wpaj` Requirement 9; no edit here may precede them. **Status: intentionally not met, by operator direction on 2026-09-02.** Execution was reordered so graph edits land first, and the receipt chain was separately re-scoped to an after-only measurement, so runs A and B do not exist to confirm. Both decisions and the evidence they give up are recorded in the Progress Log.
- [x] Exclude structural-node targets from `calls` rewriting using the named predicate, without introducing a kind or language partition.
- [x] Guard external-call rewriting against incompatible targets.
- [x] Add the three target-side precision levers (schema documents, schema meta-vocabulary keys, test-fixture paths) and keep loader provenance additive.
- [x] Add positive, negative, ambiguous-name, schema, fixture, explicit Spring API/annotation, Python loader-trace, generic dictionary/subscript, and incremental tests, including the live 102-edge positive control.
- [x] Run the two-sided live-edge census, reporting the false set and the positive set on both sides of the repair, and update graph architecture documentation.
- [x] Bump the graph builder version and add stale-artifact/unchanged-corpus re-extraction coverage, updating the test that pins that constant, the lint-bound builder-version claim in `docs/RELIABILITY.md`, and BOTH sites in `docs/architecture/graph-index-system.md` that mirror the graph builder version (one of which is already stale at a much older value and which the bump makes worse), all in the same change, since the docs-constants check binds that literal at error severity and the bump fails full validation without it.
- [x] Define the test-fixture-root predicate as a named helper rather than an ad-hoc string test, and cover it with its own fixture.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Call resolution | implementer | `1wpaj` runs A and B | Structural-node exclusion by the named predicate |
| Config attribution | implementer | `1wpaj` runs A and B | Target-side precision levers |
| Fidelity verification | qa-reviewer | Both | Mixed-artifact census and fixtures |

## Serialization Points

- `.wavefoundry/framework/scripts/graph_indexer.py`
- `.wavefoundry/framework/scripts/tests/test_graph_indexer.py`, `.wavefoundry/framework/scripts/tests/test_graph_incremental_merge.py`, `docs/architecture/graph-index-system.md`, `docs/RELIABILITY.md`

## Affected Architecture Docs

- `docs/architecture/graph-index-system.md`

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Eliminates the reproduced phantom call. |
| AC-2 | required | Closes the same root-cause family. |
| AC-3 | required | Prevents false configuration ownership. |
| AC-4 | required | Precision repair must not erase supported true edges. |
| AC-5 | required | Live and incremental evidence establish graph fidelity. |
| AC-6 | important | Resolution behavior is an architecture contract. |
| AC-7 | required | Existing repositories must receive corrected persisted edges. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-02 | DELIVERED, and the two-sided census re-derived across a rebuild of BOTH sides per AC-5's re-derivation clause rather than trusting the planning literals. Pre-fix (all three guards reverted, real graph build on a scratch copy): 123 structural-node `calls` targets; 166 `reads_config` = 102 declared-positive + 64 false. Post-fix (live graph, builder version 46): 0 structural targets, 0 false, 134 declared-positive. The positive set GREW rather than merely surviving: removing the fixture copy from the config-target index left 13 previously ambiguous literals with a single candidate, so they bind for the first time. AC-5's fail-on-drop condition is satisfied, and the repair is recorded as NOT purely subtractive, which a census counting only false removals and true retentions cannot see. Each of the three exclusions now carries its own deletion check after review found the schema-lever fixture was suppressed by a different lever and its mutant survived. | Live artifact at builder 46; pre-fix side rebuilt by an independent delivery lane; 546 focused tests green. |
| 2026-08-30 | Planned from the graph audit lane. | Public `code_callgraph(update_graph_index)` reproduction and source-corroborated `reads_config` fixture edge. |
| 2026-09-02 | OPERATOR DIRECTION: the mandated execution order is reordered. Graph production edits land FIRST, evidenced by fixtures and the two-sided live census; the evaluator scaffold and the A/B/C receipt chain follow. This supersedes Requirement 7 here and `1wpaj` Requirement 9's rule that no graph production edit may precede successful runs A and B. Consequence recorded rather than glossed: a pre-change baseline on the current production identity can no longer be captured in place, so the before-side receipt must later be reconstructed from a clean worktree at the predecessor commit, or the chain re-scoped to an after-only measurement. The graph fixes remain fully evidenced independently of the receipt chain. | Operator instruction in session. |
| 2026-09-02 | Repaired after the prepare-council returned BLOCKED on this document. Requirement 1 now names `_is_json_config_node_id` as the discriminator because the phantom target's `kind` is `class`, which Requirement 1 previously admitted. Requirement 3 was inverted: the existing target-side gate stays sufficient and three recall-safe levers remove the false family, with loader provenance additive rather than necessary. Requirement 5 and AC-4/AC-5 became two-sided against a named live positive set. AC-6 was narrowed off repository-wide state. | Council seats measured 166 live `reads_config` edges (102 true, 64 false) and traced every true edge to generic `.get` on receivers one to three frames from loaders calling `json.loads` on a string, with 42 read by test functions carrying no loader at all. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-08-30 | Restrict resolution per relation using compatible target kinds and provenance. | Repairs false attribution while preserving structural data nodes for valid relations. | **Keep universal simple-name matching:** reproduces phantom edges. **Exclude all JSON/YAML nodes:** removes useful structural/config graph coverage. **Drop all extracted edges:** sacrifices supported fallback coverage far beyond the defect. |
| 2026-09-02 | Repair config attribution on the target side and keep loader provenance additive. | The measured true population is produced entirely by the existing target-side gate, so making source-side provenance necessary would delete 102 of 166 edges while the synthetic controls stayed green. | **Require loader provenance as planned:** deletes the live true population and scores it as a precision win under a one-sided census. **Demote rather than delete, labelling weak edges:** rejected on code grounds, because an unrecognized confidence class is bucketed into the low tier by `_CONFIDENCE_RANK` and `_edge_confidence_weight` and the report ranking counts edges without weighting confidence, so the label would be absorbed rather than honored. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Stricter guards create false negatives. | Pair every negative collision fixture with positive callable/config controls, and gate acceptance on the two-sided census retaining the declared live positive set rather than on a false-positive count. |
| Provenance support varies by language. | Preserve unresolved/external edges honestly when proof is unavailable. |
| Cached graphs retain pre-fix edges. | Bump the builder version and prove unchanged-corpus re-extraction. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
