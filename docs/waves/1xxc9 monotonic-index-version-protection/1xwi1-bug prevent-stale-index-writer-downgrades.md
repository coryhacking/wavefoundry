# Prevent stale processes from downgrading project indexes

Change ID: `1xwi1-bug prevent-stale-index-writer-downgrades`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-09-12
Wave: 1xxc9 monotonic-index-version-protection

## Rationale

A consumer upgrading graph builder 51 to 52 had to reload MCP before any graph query to avoid a stale extractor rebuilding the newly upgraded graph with its older implementation. Before this change, GraphStateStore.ensure_current treated every version mismatch as a reset request. Protect local developer projects against older MCP hosts, CLI processes and background workers overwriting newer graph, semantic, lexical or chunking output. Success is a preserved newer index with actionable restart guidance, without requiring the operator to time queries around reload.

## Requirements

1. Inventory every persisted compatibility field and its owning readers/writers: storage schema, graph store/schema/builder, docs/code chunker and walker, semantic model identity/dimensions/representation, FTS/tokenizer/digest/statistics contracts. Document which fields are ordered revisions and which are opaque compatibility identities. Do not order model names, hashes, tokenizer strings or framework build suffixes lexicographically.
2. A writer must refuse a published ordered revision newer than its supported revision. Equal revisions retain normal incremental behavior; older supported revisions retain forward upgrade/rebuild behavior. Mixed participant versions must not permit a partial downgrade. Missing or malformed metadata must take an explicit non-destructive classification path; genuinely empty stores must remain initializable.
3. Check before expensive preparation or destructive initialization and recheck under the actual publication transaction/lock before any affected data mutation. A process that prepared work before a newer generation was published must not commit that stale work afterward. Audit FTS-only rebuild/heal, graph query repair, semantic updates, setup/upgrade, background refresh and direct store mutation paths, not only the MCP index_build wrapper. Preserve existing generation/fence checks and unselected participant guarantees.
4. Opaque semantic/model and lexical identities require compatibility/selection checks against the current project configuration, not a numerical downgrade comparison. An explicitly selected supported model change through the current runtime remains possible; a stale process may not silently restore its cached model/configuration. Use the source-contract fingerprint policy below, preserving existing current-runtime model selection rules.
5. Refusal is typed and observable through MCP, CLI, index health and background status, names affected component and persisted/supported revisions, and recommends reload/restart of the affected host. It must not silently become zero hits, generic absent-index state, fallback-driven destructive repair or a retry storm. Reads may continue only when their existing compatibility contract explicitly permits them; otherwise refuse safely.
6. Define the first-release protection boundary honestly: newly shipped checks cannot change code already loaded by an older host. Standard upgrade must handle those incompatible hosts before newer publication, using the existing restart/host-discovery mechanisms where needed; no reliance on a manual first-query race. Stop no unrelated repository hosts automatically. Retain best-effort discovery limitations and exact standard resume commands.
7. Cover direct release jumps combining schema migration with graph/chunker/lexical advances, as well as same-schema upgrades. Keep forward-only receipt recovery and legacy --rebuild-storage behavior; neither an explicit rebuild nor setup may bypass downgrade protection. No bridge release or automatic destructive rollback.

## Concrete Compatibility Design

Use a small stdlib-only `index_compatibility.py` shared by storage and producers. It owns classification and typed errors, not connections or migrations. Capture a fingerprint of the installed producer source contract when the runtime loads (indexer, chunker, graph_indexer, graph_store, sqlite_vector_store, index_state_store and model_bundle); re-read the installed files at preflight/publication and refuse a changed runtime contract. This is an identity check, never framework-version ordering. It protects opaque model defaults and FTS implementation changes without duplicating their declarations into another configuration file. Cache unchanged file identities where safe; retain content verification at load/publication and test in-place replacements. Source-contract errors must request a fresh host rather than hot-reload inside an active transaction.

| Participant | Persisted field / policy | Enforcement |
| --- | --- | --- |
| Storage | meta.store_schema_version; ordered decimal | Before resident initialization/migration and before publication |
| Graph | graph:store_schema_version, schema_version, builder_version, walker_version, chunker_version; ordered decimal | GraphStateStore reset decision and GraphPublication apply |
| Semantic chunks | layer metadata chunker_versions (legacy chunker_version), walker_version; ordered decimal | Before epoch/preparation and main transaction |
| Semantic model | model_versions and loaded model_bundle selection; opaque | Current installed source contract plus existing model rebuild/precision compatibility rules |
| Vectors | Dimension/float representation owned by sqlite_vector_store schema | Storage compatibility and installed contract; no numeric model ordering |
| Lexical | FTS DDL/tokenizer, payload digest algorithm; opaque, currently storage-schema-coupled | Shared contract gate before delta/heal/rebuild; preserve existing integrity validation |
| Lexical statistics | meta.lexical_statistics.version; ordered decimal | Guard before replacement/deletion; same transaction as publication |

Pass expected supported values from producer owners into the classifier, or derive literal declarations without importing producer modules into storage. Strict nonnegative decimal comparisons, no floats/bools; explicit known legacy absence remains supported, unknown populated missing identity refuses. A database/participant proven empty may initialize. Do not independently bump all format versions simply to add a guard.

Guard IndexStateStore initialization before DDL, begin_build_epoch before the durable building update, the indexer's main BEGIN IMMEDIATE transaction before prepared.apply, graph publication, direct semantic/FTS delta and rebuild transactions, and final epoch/statistics publication. Retain existing attempt CAS and source/config change checks. Every guard inside a deferred transaction must acquire an equivalent stable write snapshot before mutation; the implementation must not claim an unlocked preflight closes a race. Named direct low-level helpers either require the guarded owner or check themselves. Do not install per-row SQL callbacks as a substitute for a complete writer census.

For the first protected release, incoming upgrade code must pause/refuse before index publication whenever the installed pre-extraction runtime lacks the guard capability. Reuse the standard --confirm-hosts-stopped CLI flow and existing repository-associated host discovery; preserve the pre-extraction capability decision in the upgrade checkpoint so extraction/retry cannot falsely claim an old host became protected. Newly installed CLI confirmation plus no positively identified live old hosts permits continuation. This can be an actionable upgrade-checkpoint refusal rather than a storage-format migration receipt when schema is already current; never invent a storage conversion to force a restart. Recheck immediately before index children. Existing storage conversion handoffs continue to own actual format changes. Fresh installs with no former runtime are exempt. Discovery is best effort; explicit confirmation carries the obligation to stop undiscovered hosts.

## Scope

In scope: shared index compatibility classification and write fences; all graph, docs/code semantic, lexical and chunker/walker producers; stale-runtime diagnostics; upgrade/reload coordination; focused multi-process regression tests; canonical upgrade guidance and relevant architecture contracts.

Out of scope: retrieval ranking changes, new embedding models, storage backend changes, memory-store/secret-scan format redesign, support for intentionally writing older formats, remote coordination, or fixing unrelated call-graph extraction defects. Inventory adjacent writers only to ensure they cannot mutate protected participants through an unguarded path.

## Acceptance Criteria

- [x] AC-1: A source-grounded matrix names each compatibility field, comparison policy, reader/writer and enforcement seam; covers all four requested areas and walker/storage prerequisites without inventing numerical order for opaque identities.
- [x] AC-2: For each ordered field, newer persisted data causes typed refusal through its reachable producer; equal and older supported controls succeed. Missing/malformed, mixed-version and empty-store fixtures receive their specified outcomes. Refused attempts leave participant rows, compatibility metadata and published generation unchanged, with only explicitly allowed diagnostic bookkeeping.
- [x] AC-3: Deterministic two-process barriers demonstrate that an old worker starting or preparing before a newer publication cannot overwrite it afterward. Guard-removal mutation fails the regression. Exercise both preparation and final publication checks without timing sleeps as the oracle.
- [x] AC-4: Public MCP/CLI and background/query-triggered repair tests show actionable newer-index diagnostics, no silent zero-result/absent-layer interpretation, no destructive auto-heal and no repeated rebuild loop. Compatible reads and ordinary updates remain supported under the documented policy.
- [x] AC-5: Semantic model/configuration and FTS contract identity fixtures reject stale cached selections while allowing an explicitly authorized supported change through the current runtime; vectors, FTS and chunks remain consistent on refusal or cancellation.
- [x] AC-6: Upgrade rehearsals cover same-schema builder advancement and direct legacy/schema-7 to current storage plus graph advancement, including an already-loaded pre-protection host. The old host is fenced by the supported handoff before publication or the upgrade refuses with retained recovery data. No intermediate release, receipt editing or unrelated host termination is required.
- [x] AC-7: Changed upgrade/health guidance explains automatic protection, first-hop old-host limits and safe recovery. Targeted tests cover native-handle/lock/error behavior using portable fixtures; native execution results and untested platforms are explicitly distinguished. The change's tests pass and authored documents validate.

## Tasks

- [x] Complete compatibility and direct-writer census; reproduce the graph downgrade in an isolated fixture and classify semantic/lexical paths as observed or potential.
- [x] Select comparison/opaque-identity policy and first-hop old-host protocol; record concrete enforcement points before readiness.
- [x] Implement shared checks and wire all affected preparation/publication/repair paths.
- [x] Add typed diagnostics and bounded background behavior; retain supported read behavior.
- [x] Implement and rehearse same-schema and combined migration upgrade handoffs.
- [x] Run boundary, concurrent-process and omission-mutation tests; record source/state preservation evidence.
- [x] Update canonical guidance, rendered local prompt, architecture and concise end-user changelog; run required delivery lanes before closure.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Compatibility census and protocol | architecture-reviewer / implementer | — | Resolve field policies before readiness |
| Writer fences and diagnostics | implementer | Compatibility census and protocol | One owner for shared transaction seam |
| Upgrade and regression verification | qa-reviewer / implementer | Writer fences and diagnostics | Independent review of applied changes |

## Serialization Points

Shared compatibility/publication changes serialize before caller integration. Review existing targeted publication refusal contracts from wave 1xq4f before extending them.

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/index_compatibility.py`
- `.wavefoundry/framework/scripts/model_bundle.py`
- `.wavefoundry/framework/scripts/indexer.py`
- `.wavefoundry/framework/scripts/index_state_store.py`
- `.wavefoundry/framework/scripts/scan_secrets.py`
- `.wavefoundry/framework/scripts/graph_indexer.py`
- `.wavefoundry/framework/scripts/graph_store.py`
- `.wavefoundry/framework/scripts/graph_snapshot.py`
- `.wavefoundry/framework/scripts/graph_query.py`
- `.wavefoundry/framework/scripts/sqlite_vector_store.py`
- `.wavefoundry/framework/scripts/sqlite_runtime.py`
- `.wavefoundry/framework/scripts/chunker.py`
- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/setup_index.py`
- `.wavefoundry/framework/scripts/sqlite_storage_migration.py`
- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/upgrade_extensions.py`
- `.wavefoundry/framework/scripts/upgrade_lib.py`
- `.wavefoundry/framework/scripts/tests/`
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`
- `.wavefoundry/framework/README.md`
- `docs/prompts/upgrade-wavefoundry.prompt.md`
- `docs/specs/mcp-tool-surface.md`
- `docs/architecture/`
- `docs/RELIABILITY.md`

These are review boundaries, not a mandate to edit every file. Upgrade guidance changes belong in seed 160 first, then reconcile the local prompt; protect unrelated seeds, rendered markers and active wave 1xtnr. Implementer owns code/seed writes only after readiness; reviewers inspect and return evidence, not concurrent source edits.

## Affected Architecture Docs

Update docs/architecture/graph-index-system.md, layering-rules.md and data-and-control-flow.md for version authority, refusal and the publication boundary; docs/specs/mcp-tool-surface.md and docs/RELIABILITY.md for operator-visible recovery. No separate ADR required unless readiness selects a new architectural boundary rather than extending existing publication ownership.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Complete ownership coverage |
| AC-2 | required | No downgrade guarantee |
| AC-3 | required | Prevent check/write races |
| AC-4 | required | Safe observable recovery |
| AC-5 | required | Non-numeric compatibility correctness |
| AC-6 | required | Real first-release upgrade protection |
| AC-7 | required | Usable cross-platform delivery |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-12 | Closure authorized by the current operator request. The earlier Session Handoff below records the implementation checkpoint; this update and the wave record supersede its pending-review/authorization state without changing the reviewed plan. | wave.md; docs/agents/session-handoff.md |
| 2026-09-12 | Delivery review complete: all seven required specialist lanes and targeted council approve, no actionable findings. Current caller census received fresh readiness approval and re-Prepare passed. | delivery-review.json; typed events.jsonl approvals |
| 2026-09-12 | Implementation verification complete: 8,976 tests across 90 files pass, 12 skips; current receipt hash independently recomputed. All ACs met. Required delivery lanes remain pending before closure. | implementation-evidence.json |
| 2026-09-12 | Full-suite concurrency exposed manual state-store loaders publishing partially initialized modules. Indexer and scanner now share Python's synchronized import; a barrier regression covers both loaders. | implementation-evidence.json |
| 2026-09-12 | Shared fences, public diagnostics and first-hop handoff implemented. Advisory gaps repaired for vectorless chunk provenance, graph read compatibility and FTS maintenance. Focused tests, process barriers and omission mutants recorded; full-suite verification pending. The final task remains unchecked solely for the required delivery lanes before closure; its documentation work is complete. | implementation-evidence.json |
| 2026-09-12 | Caller census explicitly includes graph_query automatic repair and upgrade_lib checkpoint retention; both implement admitted requirements without a new behavioral boundary. | Direct reader/upgrade checkpoint seams |
| 2026-09-12 | Readback: reject older writers before preparation and in publication; preserve newer rows and show restart guidance. Shared guards then caller integration, first-hop upgrade handoff, focused tests and full suite. No format bump or ranking change. Thought: implement the shared guard and upgrade checkpoint as separate ownership lanes. | Current readiness approval; readiness-review.json |
| 2026-09-12 | Planned by operator request following consumer builder-52 upgrade report. No implementation performed. | GraphStateStore.ensure_current and _VERSION_KEYS; existing seed-derived upgrade prompt documents stale-server downgrade risk. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-12 | Select shared preflight plus transaction-bound compatibility fencing, with entrypoint diagnostics and upgrade handoff. | Protects both newly started and already-preparing stale writers. | Reload-only guidance depends on operator timing and other hosts; entrypoint-only comparisons miss direct writers and the preparation/publication race. |
| 2026-09-12 | Keep first-hop old-host handling explicit. | Older loaded code cannot execute checks introduced by this release. | Claiming future guards retroactively protect old hosts would overstate safety. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Pre-protection host ignores new checks | Existing restart/host handoff, deterministic old-runtime rehearsal, no universal discovery claim |
| Guard runs after initialization or outside transaction | Trace first mutation and final publication for every writer; adversarial interleaving |
| Opaque model identity mistaken for ordered version | Explicit compatibility matrix and current configuration authority |
| Partial build replaces unselected newer participant | Mixed-version fixtures and existing 1xq4f transaction contracts |
| Overbroad refusal prevents legitimate forward rebuild | Equal/older/empty positive controls and explicit model-change test |

## Session Handoff

Readiness approved and implementation complete. Shared writer guards, upgrade handoff and public diagnostics passed the full suite (8,976 tests; 12 skips), with a current verified receipt. All ACs are met; required delivery review remains pending before closure. Wave 1xtnr is paused, retaining its delivery evidence and uncommitted work. No closure, commit or package is authorized for this effort.
