# Orphaned Graph and Sidecar Rows Survive Every Incremental Build

Change ID: `1u8nz-bug index-removal-missed-when-path-leaves-scope-before-disk`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-08-01
Wave: `1u8o2 downstream-field-report-fixes`

## Rationale

Filed from the Solaris downstream field report (2026-08-01): deleted, ignored files kept their
chunks in the Lance tables and their nodes in the graph, and the codebase map advertised two
phantom areas; a docs update removed zero, a full graph rebuild re-extracted 559 files with an
identical node count and zero removals, and only the map regenerator healed.

**The reporter's root-cause hypothesis is REFUTED by two independent executed reproductions
(prepare cycle, 2026-08-01).** The hypothesis was that scope-excluded paths are never visited so
their removal is never evaluated. On the current tree that is false: removal detection is
registry-minus-enumeration over the UN-filtered registry (`_detect_changes`,
`indexer.py:990`, called at `:4002`), a Lance-side eligibility reaper runs on every incremental
(`_reap_stranded_lance_rows`, `indexer.py:2284`, invoked at `:4181` idle-path and `:4784`
build-path), and eviction is cross-layer ("evicted regardless of which content type's run
discovers the deletion", `:4109-4111`). Executed probes drove all four orderings (field ordering
ignore+delete then update; long ordering with an intermediate build; scoped docs-only then
code-only updates; ignored-but-present) through the REAL `build_index` in scratch fixtures: every
store healed, every time. Scope-departure retirement of still-on-disk ignored paths is ALREADY
shipped behavior, including the layer-hash drop that forces re-embed on un-ignore
(`_cleanup_layer_state_for_reaped`, `indexer.py:2383`).

**The verified current-tree defect is the opposite direction: orphaned STORE rows.** When store
rows exist without registry rows (files and their `build_file_meta` entries gone, Lance or graph
or sidecar rows remaining, the plausible real field state after out-of-band cleanup or an older
pack's bug):

- Lance, chunk_registry, and FTS self-heal on the next incremental via the idle reap
  (`indexer.py:4164-4170`). Verified by probe.
- **Graph file rows survive every incremental build** (`graph/project-graph-state.sqlite::files`
  keeps the orphans): incremental graph removal is driven solely by the meta-diff `removed` set
  passed into `update_graph_index` (`graph_indexer.py:14654`, files_removed at `:13269`), and a
  path already absent from `file_meta` is invisible to it forever. Verified by probe.
- `file_freshness` and `secret_scan_cache` rows survive longer still. Verified by probe.
- On the CURRENT tree a full graph rebuild (`content='graph', mode='rebuild'`) DOES remove the
  orphans (probe observed "delta: files=3 removed=2"), which CONTRADICTS the reporter's
  zero-removals-on-rebuild. The suspected mechanism (red-team, unconfirmed): older packs'
  graph rebuild merged over retained session state, re-extracting only on EMPTY state
  (`graph_indexer.py:14685-14690` shape). Closing that discrepancy against the shipped Solaris
  pack lineage is requirement 4.

## Requirements

1. **Store-minus-authority reconciliation on incremental builds, for the stores that lack it.**
   Each incremental build reconciles the graph file/node/edge rows, `file_freshness`, and
   `secret_scan_cache` against the current authority (the registry/walk state the Lance reap
   already uses), removing rows for paths the authority no longer knows. The Lance/FTS/registry
   path already behaves correctly and is pinned, not rebuilt.
2. **The reconciliation runs inside the build epoch, at the existing reap seam.** It extends the
   idle/build reap inside `_build_index_locked` (read-only plan, then epoch), so partial deletions
   are unobservable and a crash before finalize never publishes. A removal-only pass is NOT a
   no-op: it opens and finalizes an epoch. Routing through the normal build path keeps the 1u44n
   publication-authorization admission applying during upgrade windows; no new store-side deletion
   entry point outside an epoch.
3. **Absence and eligibility semantics are decided here, not deferred.** (a) Any disk-absence
   check classifies per path: ENOENT removes; EACCES/EIO/unreadable preserves (conservative on IO
   errors). (b) A mass-removal circuit breaker defers reconciliation when the would-remove count
   exceeds a recorded fraction of the store, so a transiently unreadable subtree cannot cascade
   into wholesale retirement (the shipped eligibility reap has this hazard today via walk-derived
   comprehensions, `indexer.py:3940-3969`; do not import it into the new pass). (c)
   Ignored-but-present policy: PARITY with shipped behavior, recorded as the decision; retirement
   is current Lance behavior and the graph aligns to it, with the note that scope-narrowing config
   changes then delete on the next build, which is correct.
4. **The field discrepancy is closed, not shrugged off.** Reproduce the reporter's
   zero-removals-on-full-graph-rebuild against the shipped Solaris pack lineage (or establish the
   mechanism by code archaeology of the pack versions exercised) and record why the current tree
   differs. If an older-pack bug stranded the rows, the requirement 1 reconciliation is precisely
   the self-heal for fielded corpora and requirement 5 tests it as such.
5. **Red-first per store, driving the real stores.** Construct the orphan state (store rows
   present, registry rows absent, files gone) on a small fixture and assert pre-fix that graph and
   sidecar rows survive an incremental build (probe-proven red today) and post-fix that one
   incremental reconciles them. A stubbed registry proves nothing; tests drive `IndexStateStore`,
   the Lance tables, and the graph store end to end, per the existing `test_indexer.py` fixture
   pattern.

## Scope

**Problem statement:** store rows orphaned from the registry (out-of-band deletions, older-pack
residue) are never reconciled on incremental builds for the graph and sidecar stores, surfacing as
phantom entries in generated docs and permanently stale graph state.

**In scope:**

- The reap seam in `indexer.py` (`_build_index_locked` idle/build reap) extended to graph,
  `file_freshness`, and `secret_scan_cache`
- Graph-side path-keyed retirement plumbing (`graph_indexer.py`; per-file state exists, a
  retirement API for the reconciliation does not)
- The absence-classification and circuit-breaker semantics of requirement 3
- The pack-lineage discrepancy investigation of requirement 4
- Regression tests per requirement 5, including a pin that the Lance self-heal path stays green

**Out of scope:**

- The scope-departure detection path (verified working; pinned, not modified)
- The map regenerator (verified correct)
- Ignore-rule semantics

## Acceptance Criteria

- [ ] AC-1: Red-first: the orphan-state fixture shows graph rows, `file_freshness`, and
  `secret_scan_cache` rows surviving an incremental build against current code, and one
  incremental reconciling all of them post-fix, driving the real stores.
- [ ] AC-2: The Lance/FTS/registry self-heal and the scope-departure retirement paths are pinned
  by regression tests that stay green (the four probe orderings encoded as tests or an equivalent
  subset recorded in the change doc).
- [ ] AC-3: Absence classification and the circuit breaker are tested: ENOENT removes, an
  unreadable path preserves (implemented via ERROR INJECTION at the stat/scandir seam, never
  filesystem chmod, which is vacuous under root and flaky across platforms), and a would-remove
  count over the threshold defers with an explicit log line.
- [ ] AC-4: The reconciliation runs inside the build epoch at the reap seam; a removal-only pass
  opens and finalizes an epoch (generation advances, test-driven); the no-out-of-epoch-deletion
  clause is satisfied by a reachability assertion on the new retirement API plus a recorded caller
  census (a universal negative is census-verified, not test-driven).
- [ ] AC-5: The requirement 4 discrepancy record exists in this doc: the shipped-pack behavior
  reproduced or explained by archaeology, with the version boundary named.
- [ ] AC-6: Structural perf assertion instead of wall-clock: the reconciliation performs at most
  one existence/authority check per store row (spy-counted) and never descends into ignored
  trees (poisoned-tree spy); full framework suite passes.

## Tasks

- [ ] Encode the four healing orderings as regression pins (AC-2), reusing the probe fixtures
- [ ] Build the orphan-state fixture and the red-first graph/sidecar test (AC-1, red before fix)
- [ ] Implement the graph retirement API and the reap-seam extension inside the epoch
- [ ] Implement absence classification and the mass-removal circuit breaker with its threshold
      recorded
- [ ] Close the pack-lineage discrepancy (requirement 4) and record it
- [ ] Structural perf assertions (AC-6); rerun the seam cluster plus `test_indexer`,
      `test_graph_indexer`, `test_doc_drift`; full suite

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| fix        | implementer | —          | Serialize with 1u8o0 (both edit `index_state_store.py`) |


## Serialization Points

- `indexer.py`, `index_state_store.py`, `graph_indexer.py`: shared with 1u8o0
  (`index_state_store.py` drift taxonomy) and with the 1u5vl/1u44n regression clusters; land the
  two index-store-touching changes in sequence, not interleaved.

## Affected Architecture Docs

- `docs/architecture/data-and-control-flow.md` (items 11-13 describe the change-detection and
  build-epoch flow this extends). Required.
- `docs/architecture/chunking-and-indexing-pipeline.md` and
  `docs/architecture/graph-index-system.md`. Candidates at Prepare.
- CHANGELOG `### Fixed` bullet at the release that ships it.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | TBD      |           |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-01 | Filed from the Solaris downstream defect report with the reporter's scope-exclusion hypothesis and a "verify at prepare" hedge. | Field report 2026-08-01 |
| 2026-08-01 | Prepare cycle REFUTED the filed root cause by two independent executed reproductions (red-team seat and code lane, six probe scripts, real build_index in scratch fixtures): all four deletion orderings heal every store on the current tree; removal detection diffs the unfiltered registry; the Lance eligibility reaper already retires scope-departed paths every incremental. The verified defect is orphaned STORE rows: graph file rows and the freshness/secret-scan sidecars survive every incremental (only a full graph rebuild heals them on the current tree, which itself contradicts the reporter's zero-removals and opens the pack-lineage question of requirement 4). Plan rewritten around the verified defect: reap-seam extension inside the build epoch, absence classification with a mass-removal circuit breaker, parity decision for ignored-but-present, per-store red-first tests, and the discrepancy-closure requirement. | Probe artifacts probe_d_stranding/probe_d4_scoped/probe_d5_orphan and red-team probes, scratchpad 2026-08-01; indexer.py:990/:2284/:4109-4111/:4164-4170; graph_indexer.py:14654/:13269 |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-01 | Fix target is orphan-store reconciliation (graph plus sidecars), not scope-departure detection | Two independent executed reproductions show scope departure healing correctly on every ordering while orphaned graph and sidecar rows survive all incrementals; building the filed registry-minus-disk mechanism would duplicate the shipped Lance reaper at a new seam and could ship with the graph still leaking | Implement the filed registry-minus-disk design (rejected: refuted premise; duplicates a working mechanism; adds a new race and over-deletion surface) |
| 2026-08-01 | Reconciliation extends the existing reap seam inside the build epoch | The reap already runs under the read-only-plan-then-epoch pattern in _build_index_locked, so partial deletes are unobservable, crash-before-finalize never publishes, and the 1u44n publication admission applies without a new entry point | A standalone store-side deletion API (rejected: would run outside the epoch, violating the reader-fail-closed invariant and re-answering the publication-authorization question) |
| 2026-08-01 | Ignored-but-present policy: parity with shipped retirement behavior | The Lance eligibility reap already retires ignored-but-present paths and drops layer hashes; graph parity makes every surface agree with the map and the exact-navigation tools; scope-narrowing config changes then delete on next build, which is the documented corpus-membership semantics | Retain ignored-but-present store rows (rejected: makes semantic and graph retrieval disagree with every other surface and with current Lance behavior) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Over-deletion from transient IO failures or unreadable subtrees | Requirement 3: per-path ENOENT-only removal, IO-error preservation, mass-removal circuit breaker with a recorded threshold |
| The new pass duplicates or races the existing Lance reap | Requirement 1 pins the Lance path as-is and extends the SAME seam; AC-2 regression-pins the healthy orderings |
| The field discrepancy hides a second, unfixed old-pack mechanism | Requirement 4 makes closing it an acceptance criterion, not a footnote |
| Epoch discipline regression | AC-4 tests generation advance on removal-only passes and absence of out-of-epoch deletion paths |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
