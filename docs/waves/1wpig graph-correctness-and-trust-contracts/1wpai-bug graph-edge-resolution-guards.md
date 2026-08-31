# Add Type and Provenance Guards to Graph Edge Resolution

Change ID: `1wpai-bug graph-edge-resolution-guards`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-08-30
Wave: 1wpig graph-correctness-and-trust-contracts

## Rationale

Graph finalization can rewrite an external call to the only project node with the same simple name even when that node is a non-callable JSON key. The live graph consequently claims `os.cpu_count()` calls a wave evidence field named `cpu_count`. Generic JSON-schema traversal also receives `reads_config` edges to a test fixture merely because generic keys such as `properties` are unique in a file whose name contains `config`. These false edges contaminate call hierarchy, impact, risk, path, dependency, and community analysis.

## Requirements

1. `calls` edge rewriting SHALL accept only code-origin function, method, or construction-compatible class targets appropriate to the source language and relation; structural JSON/YAML/data nodes SHALL never receive ordinary call edges.
2. An incompatible sole name match SHALL leave the original external/unresolved target intact.
3. `reads_config` attribution SHALL require explicit framework annotation/API provenance or a receiver traced to a modeled config-loading operation; a filename, receiver name, or generic `.get`/subscript literal alone SHALL not be sufficient.
   Positive controls are concrete: Spring `@Value`, `Environment.getProperty`, and `Environment.getRequiredProperty` are explicit framework/API provenance; Python receivers assigned from modeled `json.load`, `yaml.safe_load`, `tomllib.load`, or an explicitly recognized project config-loader return are loader-traced provenance. Generic dictionary `.get`, literal subscript, schema traversal, and a variable merely named `cfg`/`config` are negative controls unless one of those provenance paths is present.
4. Structural JSON/YAML keys SHALL remain available for relations that legitimately target them.
5. A bounded same-root-cause census SHALL quantify false call and config bindings before and after the repair.
6. The repair SHALL bump `GRAPH_BUILDER_VERSION`, force unchanged-corpus re-extraction for existing indexes, and document the graph rebuild boundary.

## Scope

**Problem statement:** Cross-file simple-name and literal resolution converts unrelated repository data into executable or configuration dependencies.

**In scope:** Candidate indexes, call-target compatibility, config provenance, schema/test-fixture controls, graph fixtures, and full/incremental equivalence.

**Out of scope:** Removing JSON/YAML from the graph, dynamic-call inference, general type inference, and changing graph-query traversal costs.

## Acceptance Criteria

- [ ] AC-1: `os.cpu_count()` plus a unique JSON `cpu_count` key retains an external call target and produces no project call edge.
- [ ] AC-2: Equivalent collisions with documentation, YAML/config keys, and non-callable project symbols do not hijack calls.
- [ ] AC-3: Generic schema processing produces no `reads_config` edge to config-named schemas or test fixtures without receiver provenance.
- [ ] AC-4: Positive callable and constructor resolution retain their supported edges/confidence; Spring `@Value`/`Environment.getProperty`/`getRequiredProperty` and loader-traced Python config receivers retain `reads_config`, while otherwise identical generic `.get`, subscript, schema, and receiver-name-only controls do not bind.
- [ ] AC-5: Full and incremental graph builds are equivalent for the new fixtures, and the live same-root-cause census records before/after false-positive counts.
- [ ] AC-6: Graph architecture documentation defines relation-compatible resolution and config provenance; focused and full tests pass.
- [ ] AC-7: A pre-fix persisted graph is invalidated by the builder-version bump, re-extracts an otherwise unchanged corpus, and passes the post-rebuild live census.

## Tasks

- [ ] Partition candidate indexes by relation-compatible node kind and language.
- [ ] Guard external-call rewriting against incompatible targets.
- [ ] Strengthen config-read provenance and generic schema vocabulary handling.
- [ ] Add positive, negative, ambiguous-name, schema, fixture, explicit Spring API/annotation, Python loader-trace, generic dictionary/subscript, and incremental tests.
- [ ] Run the bounded live-edge census and update graph architecture documentation.
- [ ] Bump the graph builder version and add stale-artifact/unchanged-corpus re-extraction coverage.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Call resolution | implementer | — | Kind/language compatibility |
| Config attribution | implementer | — | Provenance and schema controls |
| Fidelity verification | qa-reviewer | Both | Mixed-artifact census and fixtures |

## Serialization Points

- `.wavefoundry/framework/scripts/graph_indexer.py`
- `.wavefoundry/framework/scripts/tests/test_graph_indexer.py`, `.wavefoundry/framework/scripts/tests/test_graph_incremental_merge.py`, `docs/architecture/graph-index-system.md`

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
| 2026-08-30 | Planned from the graph audit lane. | Public `code_callgraph(update_graph_index)` reproduction and source-corroborated `reads_config` fixture edge. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-08-30 | Restrict resolution per relation using compatible target kinds and provenance. | Repairs false attribution while preserving structural data nodes for valid relations. | **Keep universal simple-name matching:** reproduces phantom edges. **Exclude all JSON/YAML nodes:** removes useful structural/config graph coverage. **Drop all extracted edges:** sacrifices supported fallback coverage far beyond the defect. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Stricter guards create false negatives. | Pair every negative collision fixture with positive callable/config controls and census relation counts. |
| Provenance support varies by language. | Preserve unresolved/external edges honestly when proof is unavailable. |
| Cached graphs retain pre-fix edges. | Bump the builder version and prove unchanged-corpus re-extraction. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
