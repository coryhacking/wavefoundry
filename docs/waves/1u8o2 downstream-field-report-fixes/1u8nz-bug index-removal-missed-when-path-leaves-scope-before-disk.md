# Orphaned Graph and Sidecar Rows Survive Every Incremental Build

Change ID: `1u8nz-bug index-removal-missed-when-path-leaves-scope-before-disk`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-08-03
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

- [x] AC-1: Red-first: the orphan-state fixture shows graph rows, `file_freshness`, and
  `secret_scan_cache` rows surviving an incremental build against current code, and one
  incremental reconciling all of them post-fix, driving the real stores.
- [x] AC-2: The Lance/FTS/registry self-heal and the scope-departure retirement paths are pinned
  by regression tests that stay green (the four probe orderings encoded as tests or an equivalent
  subset recorded in the change doc).
- [x] AC-3: Absence classification and the circuit breaker are tested: ENOENT removes, an
  unreadable path preserves (implemented via ERROR INJECTION at the stat/scandir seam, never
  filesystem chmod, which is vacuous under root and flaky across platforms), and a would-remove
  count over the threshold defers with an explicit log line.
- [x] AC-4: The reconciliation runs inside the build epoch at the reap seam; a removal-only pass
  opens and finalizes an epoch (generation advances, test-driven); the no-out-of-epoch-deletion
  clause is satisfied by a reachability assertion on the new retirement API plus a recorded caller
  census (a universal negative is census-verified, not test-driven).
- [x] AC-5: The requirement 4 discrepancy record exists in this doc: the shipped-pack behavior
  reproduced or explained by archaeology, with the version boundary named.
- [x] AC-6: Structural perf assertion instead of wall-clock: the reconciliation performs at most
  one existence/authority check per store row (spy-counted) and never descends into ignored
  trees (poisoned-tree spy); full framework suite passes.

## Tasks

- [x] Encode the four healing orderings as regression pins (AC-2), reusing the probe fixtures
- [x] Build the orphan-state fixture and the red-first graph/sidecar test (AC-1, red before fix)
- [x] Implement the graph retirement API and the reap-seam extension inside the epoch
- [x] Implement absence classification and the mass-removal circuit breaker with its threshold
      recorded
- [x] Close the pack-lineage discrepancy (requirement 4) and record it
- [x] Structural perf assertions (AC-6); rerun the seam cluster plus `test_indexer`,
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
  build-epoch flow this extends). Required. DONE: new item 15 documents the orphan-store
  reconciliation (authority, per-path classification, breaker, epoch placement, both seams).
- `docs/architecture/chunking-and-indexing-pipeline.md` and
  `docs/architecture/graph-index-system.md`. Candidates at Prepare. DECIDED at implementation:
  graph-index-system.md updated (an "Orphan retirement" paragraph after the merge-mode section,
  documenting `retire_orphaned_graph_paths` and why retirement routes through the merge);
  chunking-and-indexing-pipeline.md NOT updated (its reap coverage describes the Lance layer-state
  path, which this change pins unchanged; the new pass is fully described by the two docs above).
- CHANGELOG `### Fixed` bullet at the release that ships it. DONE (1.15.0 unreleased section).

## AC Priority

| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The orphan-store defect is the verified fix target; per-store red-first is its proof |
| AC-2 | required | The healing paths the refutation established must be pinned so the fix cannot regress them |
| AC-3 | required | Over-deletion is the one way this fix could be worse than the defect |
| AC-4 | required | Epoch discipline is the 1sed7 reader-fail-closed invariant; census plus generation test enforce it |
| AC-5 | required | The unclosed field discrepancy would leave the reporter's observation unexplained |
| AC-6 | required | The structural perf assertions keep the reconciliation from regressing incremental builds |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-01 | Filed from the Solaris downstream defect report with the reporter's scope-exclusion hypothesis and a "verify at prepare" hedge. | Field report 2026-08-01 |
| 2026-08-01 | Prepare cycle REFUTED the filed root cause by two independent executed reproductions (red-team seat and code lane, six probe scripts, real build_index in scratch fixtures): all four deletion orderings heal every store on the current tree; removal detection diffs the unfiltered registry; the Lance eligibility reaper already retires scope-departed paths every incremental. The verified defect is orphaned STORE rows: graph file rows and the freshness/secret-scan sidecars survive every incremental (only a full graph rebuild heals them on the current tree, which itself contradicts the reporter's zero-removals and opens the pack-lineage question of requirement 4). Plan rewritten around the verified defect: reap-seam extension inside the build epoch, absence classification with a mass-removal circuit breaker, parity decision for ignored-but-present, per-store red-first tests, and the discrepancy-closure requirement. | Probe artifacts probe_d_stranding/probe_d4_scoped/probe_d5_orphan and red-team probes, scratchpad 2026-08-01; indexer.py:990/:2284/:4109-4111/:4164-4170; graph_indexer.py:14654/:13269 |
| 2026-08-01 | Implementation sharpened the red shape with a per-table probe (probe_d6_pertable.py): a ZERO-CHANGE incremental leaves graph, file_freshness, and secret_scan_cache all holding orphans; a changed-file incremental heals graph (the merge's known-minus-current diff) and freshness (fingerprint moves, whole-table replace) but NEVER secret_scan_cache. Red-first tests landed: `OrphanStoreReconcileTests.test_one_incremental_reconciles_graph_and_sidecar_orphans` (AC-1) and `test_removal_only_pass_opens_and_finalizes_epoch` (AC-4) both FAILED against pre-fix code (orphans survived; generation 1 not greater than 1), while the four ordering pins (`LanceSelfHealOrderingPinTests`) passed, matching the prepare-cycle grounding. | probe_d6_pertable.py output 2026-08-01; pre-fix unittest run: 2 failures of 6 |
| 2026-08-01 | Fix landed: `orphan_store_paths` + `remove_sidecar_paths` (index_state_store.py read/write side, per-table semantics), `retire_orphaned_graph_paths` (graph_indexer.py, routes retirement through `update_graph_index` with an empty changed set so the merge prunes rows, edges, payload, and merge state atomically), and `_plan_orphan_store_reconcile` / `_execute_orphan_store_reconcile` in indexer.py wired at BOTH reap seams inside the epoch (idle path: plan read-only before the short-circuit, execute after `begin_build_epoch`; build path: after the Lance reap). Post-fix: all 13 tests green (AC-1 fixture, epoch/generation, four ordering pins, injection/breaker/spy units, caller census). | tests/test_indexer.py `OrphanStoreReconcileTests`, `LanceSelfHealOrderingPinTests`, `OrphanReconcilePlanUnitTests`, `OrphanRetirementCallerCensusTests`; indexer.py `_plan_orphan_store_reconcile`/`_execute_orphan_store_reconcile` |
| 2026-08-01 | Requirement 4 CLOSED by executed pack-lineage archaeology (probe_pack_lineage.py run against the shipped 1.12.0/1.13.0/1.14.0 packs from ~/.wavefoundry/dist): the version boundary is 1.12.0 to 1.13.0. On 1.12.0 a zero-change incremental heals EVERY store including secret_scan_cache (no idle short-circuit existed; every pass ran the mutation path). From 1.13.0 (the 1sed6/1sek8 epoch and no-op work) the zero-change idle path became a plan-only reap, stranding graph and freshness orphans on idle passes forever and secret_scan_cache orphans on EVERY build shape including full rebuilds. The reporter's zero-removals-on-full-graph-rebuild did NOT reproduce on any executed pack (1.12.0, 1.13.0, 1.14.0 full graph rebuilds all pruned store-minus-walk); the surviving explanations are recorded in the Decision Log and the requirement 1 reconciliation self-heals fielded corpora regardless of which older mechanism minted the rows. | probe_pack_lineage.py outputs for v1120/v1130/v1140, scratchpad 2026-08-01 |
| 2026-08-01 | Verification closed: seam cluster reruns green (seam modules incl. test_index_state_store and test_reconcile_scan, 760 tests OK; test_server_tools, test_indexer, test_graph_indexer, 2377 tests OK), full framework suite green (6720 tests across 61 files, OK). data-and-control-flow.md item 15 and the graph-index-system.md orphan-retirement paragraph document the new pass; CHANGELOG bullet added. Change implemented. | run_tests.py output 2026-08-01; docs/architecture/data-and-control-flow.md; docs/architecture/graph-index-system.md |
| 2026-08-01 | Delivery-review repairs landed (QA P2-1, QA P2-2, QA P3, arch/code P3 findings): new `OrphanStoreReconcileTests.test_build_path_with_real_change_reconciles_sidecar_orphan` pins the BUILD-path reap seam (kills QA mutant F, `if any(...)` disabled at the indexer build-path invocation, previously suite-surviving; verified failing on a mutated scratch byte-copy, passing on the real tree); the DriftWorklistAuditSurfaceTests never-blocks-ready pin de-vacuated by making the fixture audit-ready (ready True pre-injection, asserted; kills QA mutant H, stale evaluation forcing ready=False in wf_audit assembly, verified on the scratch mutant); HarnessCoherencePackTextTests fixture comment reworded to copied-and-abridged for the seed-080 wf_cli line; `retire_orphaned_graph_paths` docstring caller census corrected to one production callee path wired at BOTH reap seams; duplicated-word graph retirement log fixed and annotated (planned count vs walk-parity merge); breaker deferral message extended with the operator situation and remedy plus the Decision Log row above; graph-index-system.md orphan-retirement paragraph gains the walk-parity clause. Reruns: affected classes 17 tests OK; test_indexer 285 OK; test_server_tools 1566 OK. | Delivery lane findings 2026-08-01; scratch mutant runs 2026-08-01; tests/test_indexer.py, tests/test_server_tools.py, indexer.py, graph_indexer.py, docs/architecture/graph-index-system.md |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-01 | Fix target is orphan-store reconciliation (graph plus sidecars), not scope-departure detection | Two independent executed reproductions show scope departure healing correctly on every ordering while orphaned graph and sidecar rows survive all incrementals; building the filed registry-minus-disk mechanism would duplicate the shipped Lance reaper at a new seam and could ship with the graph still leaking | Implement the filed registry-minus-disk design (rejected: refuted premise; duplicates a working mechanism; adds a new race and over-deletion surface) |
| 2026-08-01 | Reconciliation extends the existing reap seam inside the build epoch | The reap already runs under the read-only-plan-then-epoch pattern in _build_index_locked, so partial deletes are unobservable, crash-before-finalize never publishes, and the 1u44n publication admission applies without a new entry point | A standalone store-side deletion API (rejected: would run outside the epoch, violating the reader-fail-closed invariant and re-answering the publication-authorization question) |
| 2026-08-01 | Ignored-but-present policy: parity with shipped retirement behavior | The Lance eligibility reap already retires ignored-but-present paths and drops layer hashes; graph parity makes every surface agree with the map and the exact-navigation tools; scope-narrowing config changes then delete on next build, which is the documented corpus-membership semantics | Retain ignored-but-present store rows (rejected: makes semantic and graph retrieval disagree with every other surface and with current Lance behavior) |
| 2026-08-01 | secret_scan_cache retires ONLY disk-absent paths; the parity rule applies to file_freshness and graph only | The standalone secrets scanner's candidate set is ALL tracked files, intentionally wider than the index corpus (the preserved 1rsha semantics), so a present-but-out-of-index-scope cache row is a legitimate entry; retiring it would thrash the cache without correctness gain. Freshness and graph rows exist only for corpus paths, so scope-departed rows there are stale by definition and retire (parity) | Uniform parity across all three stores (rejected: mass-deletes legitimate tracked-file cache entries and would trip the circuit breaker on healthy repos); uniform absence-only (rejected: leaves scope-departed freshness and graph rows stale until an unrelated rebuild) |
| 2026-08-01 | Absence classification: a dedicated `_orphan_path_stat` seam; ENOENT/ENOTDIR removes, any other OSError preserves; tests inject errors by patching the seam | AC-3 forbids chmod-based tests (vacuous under root, flaky across platforms); a discrete module-level stat seam gives the injection point while production behavior stays a plain `os.stat`. ENOTDIR joins ENOENT because it is the path-prefix variant of positive deletion evidence | Patch `os.stat` globally in tests (rejected: bleeds into sqlite/pathlib calls inside the same window); chmod fixtures (rejected by the AC) |
| 2026-08-01 | Circuit-breaker threshold: defer a store's reconciliation when would-remove >= 8 rows AND would-remove > 50% of the store's rows (`ORPHAN_RECONCILE_BREAKER_MIN_ROWS = 8`, `ORPHAN_RECONCILE_BREAKER_FRACTION = 0.5`) | The fraction guards large stores against transiently invisible subtrees (unmounted volume, torn walk) cascading into wholesale retirement; the absolute floor keeps small repos reconciling normally (2 orphans of 5 rows is 40% and under the floor, so ordinary small-repo deletions never defer). Deferral is loud: stderr line plus the durable store log, and the next build re-plans | Fraction only (rejected: 2 of 3 rows on a tiny store would defer forever); count only (rejected: 100 rows of a 100k-row store is not a mass event); fail the build (rejected: the sidecars are optional residents; freshness posture is best-effort) |
| 2026-08-01 | Graph retirement routes through the merge (`retire_orphaned_graph_paths` delegates to `update_graph_index` with an empty changed set), never a raw row DELETE | A raw delete desyncs the per-file store from the merge-state fragments and the served payload; the merge prunes rows, re-resolves edges into removed paths, rewrites payload and clusters atomically, and is the exact machinery every ordinary build already trusts. Consequence, recorded honestly: within a triggered merge the prune is walk-parity (an unreadable file is invisible to the walk), so per-path unreadable-preservation is enforced at the TRIGGER (the plan only invokes retirement when a removable, non-unreadable orphan exists) plus the circuit breaker, which is the same exposure every shipped mutation build already has | Raw `DELETE FROM files` retirement API (rejected: store/payload desync, stale edges and clusters); invalidate the payload binding and force a full re-merge next build (rejected: serves a stale payload in the window and doubles the cost) |
| 2026-08-01 | AC-2 ordering pins: all four probe orderings encoded as tests (`LanceSelfHealOrderingPinTests`), no subset | The probes already existed and the four tests cost little; encoding all four removes the need for an equivalence argument | Equivalent-subset with a recorded argument (allowed by the AC; unnecessary once the full encoding was cheap) |
| 2026-08-01 | Caller census for the no-out-of-epoch-deletion clause (AC-4) | `retire_orphaned_graph_paths`: defined in graph_indexer.py; sole production caller is `_execute_orphan_store_reconcile` in indexer.py, whose two call sites both sit inside `_build_index_locked` after `begin_build_epoch` (idle seam and build-path reap seam). `remove_sidecar_paths`: defined in index_state_store.py; sole production caller is the same `_execute_orphan_store_reconcile`. Census pinned by `OrphanRetirementCallerCensusTests` (reference scan over the framework scripts) | Test-driving the universal negative (rejected by the AC itself: a universal negative is census-verified) |
| 2026-08-01 | Accepted consequence of the breaker plus the absence-only cache rule: a mass-orphaned secret_scan_cache can defer indefinitely on a static corpus | secret_scan_cache has no alternative healer (freshness and graph heal through other passes; the cache only heals through this reconcile), and the deferral clears only when newly indexed files dilute the would-remove fraction under the breaker, which never happens on a corpus that stops growing. The state is loud (stderr line plus the durable store log on every build), self-diluting on any growing corpus, and has no silent data effect (stale cache rows are never served as findings; they only occupy rows). This is the deliberate alternative to failing the build; the deferral message names the situation and the dilution remedy so the operator is not left diagnosing a silent loop | Fail the build on persistent deferral (rejected: the sidecars are optional residents and freshness posture is best-effort); a cache-specific breaker bypass (rejected: reopens the mass-removal exposure the breaker exists to close) |
| 2026-08-01 | Reporter's zero-removals-on-full-graph-rebuild: unreproduced on the executed lineage; surviving explanations recorded | Executed full graph rebuilds on 1.12.0, 1.13.0, and 1.14.0 packs all pruned store-minus-walk. Surviving candidate mechanisms for the field observation: (a) a graph-builder-version advance across the reporter's four-pack upgrade lineage resets the store, making the rebuild re-extract the current corpus from empty state with a cosmetically true removed=0 and no orphan nodes to remove, while the phantom entries the reporter saw lived in the map and Lance-backed surfaces (consistent with "only the map regenerator healed"); (b) the observed surfaces were never graph-payload-backed. Either way the requirement 1 reconciliation is the self-heal for whatever older mechanism minted the rows | Keep probing older packs until exact reproduction (rejected: the boundary that matters for the fix, 1.12.0 to 1.13.0, is pinned by execution; deeper archaeology does not change the shipped remedy) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Over-deletion from transient IO failures or unreadable subtrees | Requirement 3: per-path ENOENT-only removal, IO-error preservation, mass-removal circuit breaker with a recorded threshold |
| The new pass duplicates or races the existing Lance reap | Requirement 1 pins the Lance path as-is and extends the SAME seam; AC-2 regression-pins the healthy orderings |
| The field discrepancy hides a second, unfixed old-pack mechanism | Requirement 4 makes closing it an acceptance criterion, not a footnote |
| Epoch discipline regression | AC-4 tests generation advance on removal-only passes and absence of out-of-epoch deletion paths |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
