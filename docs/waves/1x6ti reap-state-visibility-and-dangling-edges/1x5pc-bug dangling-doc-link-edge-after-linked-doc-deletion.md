# A Doc-Link Edge Into a Deleted Doc Resurfaces on the Next Unrelated Build

Change ID: `1x5pc-bug dangling-doc-link-edge-after-linked-doc-deletion`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-09-05
Wave: 1x6ti reap-state-visibility-and-dangling-edges

## Rationale

Found by the red-team seat during the delivery review of wave `1x54z`
(RED-RV2-1) and reproduced byte for byte on the pre-wave tree, so it is not
that wave's defect. When a doc that another doc links to is deleted, the
first build after the deletion prunes the target's node and the
`doc_references_doc` edge from the served payload. On the next build that
does not touch the linking doc (an unrelated code edit), the edge comes back
into `project-graph.json` with no target node and no store row for the
target, and it persists across further unrelated builds until a full
rebuild.

The mechanism is visible in `GraphIndexSession.finalize`. The reverse
invalidation block prunes `edge_map` only for endpoints in this merge's
`removed_paths` and `removed_symbols`; the persisted per-file fragments keep
whatever edges they carried, and the payload is reassembled from every
fragment on every merge. A removed symbol triggers re-resolution of the
fragments that referenced it; a removed doc path does not, and the block's
own note predicts the consequence ("masked here for exactly one build and
then resurface as a dangling payload edge on the next unrelated edit"). A
second variant of the same class was found in the same review (ARCH-RV3-1):
since wave `1x54z` the merge keeps the stored fragment of a doc under a
directory the walk could not read and skips it in the impacted-docs rescan,
so when a symbol that doc mentions is renamed during the outage the fragment
keeps its `doc_references_code` edge to the removed symbol id; the prune
masks it for one build and the next merge re-emits it with no target node.
Both variants are fragment edges whose endpoint is gone from the tree at
payload assembly, and both violate the `finalize` docstring's invariant that
an incremental merge serves the same edge-key set as a from-scratch build,
which resolves links and mentions against the current tree and emits neither
edge. `GraphQueryIndex` builds its adjacency from edges regardless of node
presence, so a dangling edge surfaces a neighbour id with no node in one-hop
and traversal results.

## Requirements

1. At payload assembly in `GraphIndexSession.finalize`, immediately after
   the short-symbol prune and BEFORE the embedded-SQL capture reconcile and
   the zero-edge doc prune (so the capture counters and the doc prune both
   see the filtered map), any edge whose source or target id is neither a
   node, nor an endpoint under the `external::` namespace (unresolved by design: external
   supertypes on `implements` and `extends`, unresolved calls and imports,
   the relation-scoped `external::sql::` names), nor a current path of the
   build (the widened local `current_paths` the prune already uses, which
   carries the walk-shadowed known paths), nor, under a directory the walk
   reported unreadable this build, an endpoint whose edge the last published
   payload served (delivery review CODE-DEL-1 and CODE-RV1-2: a file the
   graph never nodes inside a shadowed subtree has no store row to widen
   from, so the last published payload, read once per merge only during an
   outage, decides; the subtree is served as of the last readable build)
   SHALL be dropped. Current-path endpoints without a node are
   legitimate evidence the graph carries today and must survive: a doc link
   to a file the graph never nodes (a `.gitignore`, a `Makefile`, an unscanned
   config file), a link to a doc under the scan-exclusion prefixes, and a
   memory-record file target into `docs/waves/` (the readiness census found
   six such edges on this repository's graph). Running before the zero-edge
   doc prune is what lets a doc whose only edge was dangling be pruned
   exactly as a from-scratch build prunes it.
2. The number of edges dropped SHALL be reported in the merge stats as
   `edges_dropped_dangling` and on the verbose merge line, which is the
   `merge_suffix` f-string in `_build_graph_artifacts` (`indexer.py`), not
   the graph module; the field is appended after the `sidecar:` segment so
   the existing merge-line regex pin in `test_graph_incremental_merge.py`
   (which requires `state io:` directly after `edges_reresolved`) keeps
   matching, and the pin moves with the line if the layout changes.
3. `GRAPH_BUILDER_VERSION` SHALL be bumped so persisted payloads built before
   this change are rebuilt and their dangling edges cleared; the pinned
   version in `test_graph_indexer.py` moves with it (the
   `test_server_tools_retrieval.py` fixture literal was checked and is a
   MagicMock stub never compared to the constant, so it stays), the shipped
   graph-quality post report is regenerated because it records the builder
   version and a fresh run must reproduce it, and the change discloses
   that the first graph query after the upgrade runs a synchronous in-process
   full graph re-extract (`_ensure_graph_builder_current`) and that
   `graph_indexer.py` is a production-identity module for the retrieval
   evaluator.
4. Tests SHALL pin: the deleted-linked-doc sequence (link, delete the target,
   build, unrelated edit, build) serves no edge into the deleted path and is
   equivalent to a from-scratch build under `assert_equivalent` (node set,
   edge-key set with confidences, and `input_fingerprint`), including a doc
   whose only link was the deleted target; the shadowed-doc rename sequence
   (rename during a walk outage, recovery, unrelated edit) serves no edge to
   the removed symbol id and is equivalent the same way (the merge
   harness's `_RepoDriver` is extended to omit the shadowed subtree from
   `files` and `current_file_meta` and to pass `unreadable_dirs`, mirroring
   what the indexer's walk hands the session); edges to `external::`
   endpoints (the fixture carries an unresolved call and an external
   supertype) and to node-less current-path endpoints survive the filter,
   pinned as absolute presence assertions on BOTH the incremental and the
   from-scratch payloads, because the differential is blind to an exemption
   the oracle applies too; and deleting the filter, moving it after the
   zero-edge doc prune, and removing the current-path exemption each fail a
   named test, recorded as mutations before review.
5. Before the change ships, a full rebuild of this repository SHALL be
   measured with the filter in place and the count and classes of dropped
   edges recorded in the Progress Log; any class beyond the two known
   variants is investigated, not accepted silently.

## Scope

**Problem statement:** the merge's payload prune removes an edge into a
removed endpoint once, but the linking fragment re-emits it on the next
unrelated build, so the served graph carries edges to nodes that do not
exist.

**In scope:**

- The assembly-time endpoint filter in `finalize`, its stat, and the builder
  version bump.
- Differential tests against a full rebuild for both variants, the
  `external::` survival pin, and the mutation.
- The measurement on this repository's own graph.

**Out of scope:**

- The eligibility reap, the breaker policy and the walk-shadow preservation
  itself (wave `1x54z`); this change repairs what the merge serves from a
  preserved fragment, not whether it is preserved.
- Re-resolving stored fragments for removed doc paths: the fragment stays as
  extracted until its doc is next re-scanned, which is the accepted posture,
  and the served payload is what this change makes correct.
- Minting nodes for current paths the graph never nodes (config files,
  scan-excluded docs): they stay node-less, exempt endpoints.

## Acceptance Criteria

- [x] AC-1: After deleting a linked doc and running two incremental builds (the second after an unrelated edit), the payload carries no edge into the deleted path.
- [x] AC-2: The payload after that sequence, including a doc whose only link was the deleted target, is equivalent to a full rebuild's under `assert_equivalent` (node set, edge-key set with confidences, `input_fingerprint`).
- [x] AC-3: After a symbol a shadowed doc mentions is renamed during a walk-shadow outage, then recovery and an unrelated edit, the payload carries no edge to the removed symbol id and is equivalent to a full rebuild's under `assert_equivalent`.
- [x] AC-4: Edges to `external::` endpoints (an external supertype on `implements` or `extends`, an unresolved call) and to node-less current-path endpoints (a link to a `.gitignore`, a link to a scan-excluded doc, a memory target into `docs/waves/`) survive the filter, pinned by absolute presence assertions on both the incremental and the from-scratch payloads; during a walk outage an edge into a node-less file under the unreadable directory survives when the last published payload served it, and an edge that payload dropped stays absent (delivery review CODE-DEL-1, CODE-RV1-2).
- [x] AC-5: `edges_dropped_dangling` is reported in the merge stats; `GRAPH_BUILDER_VERSION` is bumped with the pinned test, the shipped graph-quality post report and the `docs/RELIABILITY.md` claim moved with it (the retrieval fixture literal is a stub and stays).
- [x] AC-6: Deleting the filter, moving it after the zero-edge doc prune, and removing the current-path exemption each fail a named test, recorded as mutations before review.
- [x] AC-7: A full rebuild of this repository with the filter records the number and classes of dropped edges in the Progress Log, with every class beyond the two known variants explained, and the six current-path edges the readiness census found today are shown to survive.
- [x] AC-8: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Red first: a failing `assert_equivalent` differential for the deleted-linked-doc sequence (with a doc whose only link was the deleted target) against a full rebuild.
- [x] Implement the endpoint filter in `finalize` immediately after the short-symbol prune (before the embedded-SQL capture reconcile), with the `external::` and current-path exemptions (the widened local `current_paths`) and the stat; append `edges_dropped_dangling` to the `merge_suffix` line in `_build_graph_artifacts` after the `sidecar:` segment; bump `GRAPH_BUILDER_VERSION`; move the pinned version in `test_graph_indexer.py` and check whether the `test_server_tools_retrieval.py` fixture literal is compared to the constant (it may be a stub value); update the `docs/RELIABILITY.md` builder-version claim.
- [x] Add the shadowed-doc rename differential (driver extended with `unreadable_dirs` and a hidden subtree) and the survival pins as absolute presence assertions on both payloads (`external::` and node-less current-path endpoints).
- [x] Measure a full rebuild of this repository; record the dropped-edge count and classes and the survival of the six census edges.
- [x] Record the mutations (filter removed; filter moved after the zero-edge doc prune; current-path exemption removed).
- [x] Docs: `graph-index-system.md` (incremental-merge bullet; the finalize output-pass order sentence, which today claims the reverse-invalidation prune drops dangling edges before the payload is written; the orphan-retirement clause "a later merge can re-emit the stored fragment's stale edge" retired; the stale constant block refreshed); the `finalize` docstring and the NOTE above the reverse-invalidation prune; `docs/RELIABILITY.md`; CHANGELOG entry under Unreleased plus the Upgrading note's count of builder moves, stating the real post-bump number or avoiding the numeral form.

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes                                              |
| ---------- | ----------- | ---------- | -------------------------------------------------- |
| filter     | implementer | —          | `finalize` only; exemption for `external::`.       |
| pin        | implementer | filter     | Two differentials against `full=True`; survival.   |
| measure    | implementer | filter     | This repository's graph, before and after.         |


## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/graph_indexer.py`
- `.wavefoundry/framework/scripts/indexer.py`
- `.wavefoundry/framework/scripts/tests/test_graph_incremental_merge.py`
- `.wavefoundry/framework/scripts/tests/test_graph_indexer.py`
- `.wavefoundry/framework/scripts/tests/test_indexer.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools_retrieval.py`
- `docs/architecture/graph-index-system.md`
- `docs/RELIABILITY.md`
- `docs/reports/graph-quality-post.json`

## Affected Architecture Docs

`docs/architecture/graph-index-system.md`: the incremental-merge paragraph
gains the assembly-time invariant (every served edge's endpoints are a node,
an `external::` id, a current path, or, under a walk-reported unreadable
directory, an endpoint whose edge the last published payload served), the finalize output-pass order
sentence names the filter as the pass before the zero-edge doc prune and
stops claiming the reverse-invalidation prune alone drops dangling edges,
the orphan-retirement paragraph's "a later merge can re-emit the stored
fragment's stale edge" clause is retired, and the stale constant block is
refreshed. `docs/RELIABILITY.md`: the graph builder version claim moves with
the bump. No boundary or flow change.

## AC Priority


| AC   | Priority  | Rationale                                                     |
| ---- | --------- | ------------------------------------------------------------- |
| AC-1 | required  | The defect itself.                                            |
| AC-2 | required  | The merge's own documented invariant.                         |
| AC-3 | required  | The second variant of the same class (ARCH-RV3-1).            |
| AC-4 | required  | The exemption is what keeps the filter from removing real evidence. |
| AC-5 | important | Visibility of the filter's work and the rebuild of stale payloads. |
| AC-6 | required  | A guard that survives its own deletion is not landed.         |
| AC-7 | required  | The filter's blast radius on a real graph is measured, not assumed. |
| AC-8 | required  | Standard delivery gate.                                       |


## Progress Log


| Date       | Update                                                                                                 | Evidence                                         |
| ---------- | ------------------------------------------------------------------------------------------------------ | ------------------------------------------------ |
| 2026-09-05 | Delivery review cycle 2 reverification: the code, QA, architecture and docs-contract lanes each verified the cycle-2 repairs independently (the outage no longer resurrects dropped edges on the lanes' own probes; consecutive outages are non-increasing; a missing or corrupt last payload degrades to drop with no raise; eleven prose sites state the four-way predicate). Notes recorded without repair: CODE-RV2-1 (a doc scanned before its link target exists never gains the edge until re-scanned, pre-existing and outside scope, parked as plan `1x8e1`); QA-RV2-1 (the all-endpoints rule has no reachable discriminating input); DOCS-RV2-1 (the verbose log line's shorthand); the relation component of the last-served key is unpinned because no real fragment can disagree with the payload on a doc-link relation. | Lane reports in the session scratchpad (`rv2_code_1x6ti`, `rv2_qa_1x6ti`, `rv2_arch_1x6ti`); full suite 8,462 OK on the cycle-2 tree. |
| 2026-09-05 | Delivery review cycle 2. CODE-RV1-2 and QA-RV1-1 (code and QA reverification lanes, independently): the cycle-1 exemption kept, during an outage, edges the last readable build had already dropped (a linker fragment re-emitting a link into a doc deleted under the directory that later became unreadable, with the pruned only-link doc node resurrected); repaired by narrowing the exemption to edges the last published payload served (`_edge_servable` reads the payload at `self.graph_path` once per merge, only when `unreadable_dirs` is non-empty, keyed by source, target and relation), pinned by `test_outage_does_not_resurrect_an_edge_the_last_readable_build_dropped`. CODE-RV1-1 and QA-RV1-2: the exemption's locality and its directory boundary were unpinned at the call site; `test_unrelated_outage_drops_stale_edges_and_respects_the_directory_boundary` (an unrelated `vault` outage with stale targets in `docs/` and the sibling `vault2/`) pins both. DOCS-RV1-2 and ARCH-RV1-1: every prose statement of the predicate (the `finalize` docstring, the comment and verbose line, the builder-version comment and its copy, the graph-index-system.md invariant bullet and pass-order clause, the CHANGELOG entry, the Wave Summary, Requirement 1, AC-4 and Affected Architecture Docs here) now states the four-way predicate. QA-RV1-4 recorded as a pre-existing fast-path risk (row above). Mutations (scratch, `mut_r2/`): last-served condition removed, exempt-everything-when-unreadable, boundary-less prefix; each killed by the named tests. | `DanglingEndpointFilterTests` 7 OK; mutant trees under `mut_r2/` in the session scratchpad, killing tests named in this row. |
| 2026-09-05 | Delivery review cycle 1. CODE-DEL-1 (code lane, real, wave-introduced): a doc link into a file the graph never nodes inside a walk-shadowed subtree has no store row to widen from, so the filter dropped it during the outage and the zero-change recovery served the outage payload without it, against the `1x54z` posture; repaired by exempting an endpoint whose file lies under `self.unreadable_dirs` in `_endpoint_servable`, pinned by `test_link_into_a_node_less_file_under_an_unreadable_directory_survives_the_outage`. DOCS-DEL-1 and CODE-DEL-3: the implement task was unchecked (the earlier mark call had failed on its argument shape), now marked. DOCS-DEL-2: Requirement 3 and AC-5 now say one pin moved and the retrieval fixture is a stub. ARCH-DEL-1: the Risks row names both production-identity modules and the gate's trigger. Self-found at the receipt run, before the lanes reported: the full suite failed twice on the delivered tree. `ShippedReportPairTests.test_the_shipped_post_report_still_matches_a_fresh_run` because `docs/reports/graph-quality-post.json` records the graph builder version: regenerated with `graph_quality_eval.py --label post` (totals, relations, corpus digest and evaluator identity reproduce byte for byte; only the builder version, production identity, repository identity and timestamps moved), added to the review targets. `ChunkCoordinateContractTests.test_repository_prose_coordinate_census_reports_zero_wrong` because the Decision Log tables of both change docs had 800-character padded header rows and rows over the remaining budget, which the chunker line-wraps into a header-only part with a row's coordinates: the header rows were narrowed (content untouched) and the chunker defect parked as plan `1x81x`. | Repaired tree: `DanglingEndpointFilterTests` 5 OK; `test_graph_quality_eval` 90 OK; the census test and the full suite re-run at the receipt. |
| 2026-09-05 | Measured (Requirement 5, AC-7): a from-scratch graph build of this repository with the filter in place, into a scratch index directory against the real root (`measure_1x5pc/run_full_graph.py`), 2,024 files, 23,872 nodes, 70,372 edges, `dangling: dropped=0` on the merge line, as expected for a from-scratch build whose fragments are all fresh (the defect is a stale fragment's re-emission, which only an incremental merge can produce). Node-less endpoint census of the measured payload against the served one: 10,618 `external::` call targets and 412 `external::` import targets (unresolved by design, exempt), and exactly the six non-external node-less edges the readiness census found, all with targets on disk, all surviving: four `doc_references_doc` (`AGENTS.md` to a scan-excluded doc under `docs/contributing/`; `CHANGELOG.md` to `.aiignore`, `.gitattributes`, `.gitignore`) and two `memory_targets` (into `docs/waves/` and to `.aiignore`). No class beyond the two known variants appeared; nothing to investigate. The served index had already been rebuilt at builder 50 by the post-edit refresh and carries the same six edges. | Measurement log `measure_1x5pc/run.log` and the census output in the session scratchpad; served payload `.wavefoundry/index/graph/project-graph.json` at builder `50`. |
| 2026-09-05 | Implemented. Red first: `DanglingEndpointFilterTests` (test_graph_incremental_merge.py) failed three of four on the unrepaired tree (the deleted-doc differential, the shadowed-rename differential, the stats count) and the survival pin passed, as expected. The filter sits in `finalize` immediately after the short-symbol prune with `_endpoint_servable` (node map, `external::`, the widened local `current_paths`) and `stats["edges_dropped_dangling"]`; the merge line in `_build_graph_artifacts` (indexer.py) gains `dangling: dropped=N` after the sidecar segment and the regex pin moved with it; `GRAPH_BUILDER_VERSION` 49 to 50 with the pin in test_graph_indexer.py, the `docs/RELIABILITY.md` claim and the graph-index-system.md constant block; the `test_server_tools_retrieval.py` fixture literal (`"45"`) is a stub the test never compares to the constant and was left alone. The `_RepoDriver` harness gained `unreadable_dirs` (shadowed subtree omitted from `files` and `current_file_meta`, directories passed through). | `DanglingEndpointFilterTests` 4 tests OK; `BuildLogInstrumentationTests` OK; test_graph_incremental_merge.py 44 OK; test_graph_indexer.py 547 OK. |
| 2026-09-05 | Mutations before review (scratch copies under the session scratchpad, `mut_1x5pc/run.py`): A filter removed (the pop loop replaced by `pass`) killed by `test_deleted_linked_doc_serves_no_edge_into_the_deleted_path` and `test_shadowed_doc_rename_serves_no_edge_to_the_removed_symbol`; B filter moved after the zero-edge doc prune killed by the same two (node sets diverge: the only-link doc survives as a zero-edge node the oracle prunes); C current-path exemption removed killed by `test_external_and_node_less_current_path_endpoints_survive` (the `.gitignore`, scan-excluded doc and memory-target edges vanish from the incremental payload). | Mutation table: A killed (2 tests), B killed (2 tests), C killed (1 test); all three named tests pass on the unmutated tree. |
| 2026-09-04 | Filed from the `1x54z` delivery review (RED-RV2-1, probe R1b on the cycle-2 tree and on the pre-wave control). | Wave `1x54z` events ledger, finding RED-RV2-1.    |
| 2026-09-04 | Widened to the removed-symbol variant left by a doc the merge could not rescan during an outage (ARCH-RV3-1, probe2_nodes on the cycle-3 tree). | Wave `1x54z` events ledger, finding ARCH-RV3-1. |
| 2026-09-05 | Prepare lane repairs on admission (code CODE-PREP-3; architecture ARCH-PREP-2; QA QA-PREP-2, QA-PREP-5): the filter slot pinned to immediately after the short-symbol prune so the embedded-SQL capture counters see the filtered map; the exemption reads the widened local `current_paths`; the verbose merge line named as `merge_suffix` in `indexer.py` with the field appended after `sidecar:` so the existing regex pin holds, and `indexer.py` added to the review targets; the survival pins made absolute presence assertions on both payloads and a third mutant (current-path exemption removed) added, because the differential is blind to an exemption the oracle applies too; the driver extension for the shadowed sequence named; the retrieval fixture literal flagged as possibly a stub. Both lanes reproduced the deleted-linked-doc sequence through the real merge with a from-scratch oracle (nodes, edge keys and fingerprint diverge; the only-link doc survives as a zero-edge node) and the QA lane reproduced the shadowed rename through a driver subclass. | Lane reports in the session scratchpad (`prep_code/probe_baseline.py`, `prep_qa/probe_deleted_doc.py`, `probe_shadow_rename.py`, `probe_memory_target.py`, `probe_external.py`). |
| 2026-09-04 | Prepare council repairs on admission (red-team RED-PREP-1, 2, 6; docs-contract DOCS-PREP-1, 2, 3, 4): the exemption widened from `external::` alone to `external::` plus current-path endpoints, because a census of this repository's served graph found six legitimate node-less edges (four `doc_references_doc` to files the graph never nodes or to scan-excluded docs, two `memory_targets` into `docs/waves/`); the filter placed before the zero-edge doc prune, because a post-prune filter left a doc whose only link was deleted as a zero-edge node the oracle prunes; AC-2 and AC-3 pinned by `assert_equivalent` rather than edge keys; AC-3 wording aligned with the exemption; the two builder-version pins, the `docs/RELIABILITY.md` claim, the pass-order sentence, the `finalize` NOTE and the Upgrading note added to the tasks and targets; the synchronous first-query rebuild and the production-identity perturbation disclosed. | Council seat reports in the session scratchpad (`prep_redteam/census.py`, `probe_a_dangling.py`, `probe_a2_nodes.py`). |
| 2026-09-04 | Plan feature: mechanism grounded in `finalize` (the reverse-invalidation block prunes only this merge's removed endpoints and its note predicts the resurfacing; the short-symbol prune and the zero-edge doc prune run after it; the honesty pass over `edge_map` is the last rewrite before the analytics) and in `GraphQueryIndex.__init__` (adjacency from edges regardless of node presence). Divergent pre-plan recorded in the Decision Log. | `code_keyword` and `code_read` over `graph_indexer.py` and `graph_query.py`. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-04 | The exemption is membership in the node map, the `external::` namespace, or the build's current-path set; the filter runs before the zero-edge doc prune (readiness council, RED-PREP-1 and RED-PREP-2). | The defect is an endpoint gone from the tree, not an endpoint the graph never nodes; a current file the graph links to without a node is evidence the served graph carries today, and a from-scratch build carries it too, so a node-map-only filter would remove it from both sides and the differential could not see the loss. Placing the filter after the zero-edge doc prune leaves a doc whose only edge was dangling alive as a zero-edge node the oracle prunes, so node sets and fingerprints diverge while edge keys match. | **Node-map-only exemption with `external::`:** drops six real edges on this repository today and unbounded classes on target repositories (any README link to a `Makefile` or `.env.example`). **Mint path nodes for node-less current paths:** changes the node set for every consumer for a class the graph deliberately does not node. |
| 2026-09-04 | Filter dangling endpoints at payload assembly, `external::` excepted, with a stat and a builder-version bump (divergent pre-plan, selected). | One mechanism restores the incremental-equals-full invariant for both known variants and any future fragment re-emission class; the served payload is what consumers read. Its weakness, that it also drops any other node-less internal endpoint class that exists today, is bounded by the measurement requirement on this repository's graph before it ships. | **Re-resolve the fragments that link into a removed doc path (add removed doc paths to the impacted-docs rescan):** cannot cover the shadowed-doc variant, since the doc cannot be read during the outage and nothing triggers a rescan after recovery, and it re-reads docs from disk for every removed path. **Both mechanisms:** two implementations of one invariant, the first adding cost without payload benefit once the filter exists. |


## Risks


| Risk                                                                                          | Mitigation                                                                                                   |
| --------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| The filter drops an edge class the graph queries rely on that has no node today.             | Requirement 5 measures a full rebuild of this repository and records every dropped class before shipping; `external::` is exempt by construction. |
| A delete-only build whose removed paths have no graph-state row (a node-less file the graph never stored) takes the zero-change fast path and serves the prior payload, stale link included, until the next build with real work (delivery review QA-RV1-4, pre-existing fast-path behaviour). | Self-healing at the next real merge; treating such a removal as real work is a fast-path design change outside this wave, promoted by a field report of a stale link persisting across builds. |
| The builder-version bump forces a graph rebuild on every consumer's next build, and the first graph query after the upgrade runs it synchronously in-process (`_ensure_graph_builder_current`), serving uncached until then. | The bump is the standing convention for a served-edge-set change; the rebuild is embedding-free and clears the stale edges; the CHANGELOG Upgrading note discloses the synchronous first-query rebuild. |
| `graph_indexer.py` and `indexer.py` are production-identity modules for the retrieval evaluator (`PRODUCTION_RETRIEVAL_MODULES`) and `graph_builder` is a production version constant, so a same-generation comparison across this change reads as a production change. | Expected and disclosed; the standing gate's trigger is a change to ranking, question classification, chunking relevance, hybrid candidate selection or result demotion, none of which this change makes, so no receipt is owed by this wave; the measured from-scratch build of this repository dropped zero edges. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
