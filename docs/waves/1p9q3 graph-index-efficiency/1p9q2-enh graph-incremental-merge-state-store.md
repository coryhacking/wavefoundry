# Graph index: incremental merge with symbol-scoped cross-file invalidation, and a per-file state store

Change ID: `1p9q2-enh graph-incremental-merge-state-store`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-07-03
Wave: TBD

## Rationale

The graph build is incremental at **extraction** but full-cost at **merge**. `GraphIndexSession` (`graph_indexer.py:5484`) re-extracts only changed/removed files against a per-file artifact cache, but `finalize()` then **re-merges every cached artifact from every file into a fresh node/edge map on every build** (`graph_indexer.py:7404-7541`), re-runs the cross-file resolution rewrite over the whole graph, and rewrites all artifacts in full. The per-file cache that enables incremental extraction — `project-graph-state.json` — is itself a single monolithic JSON document (22.6 MB on the self-hosted repo, **twice the size of the graph it supports**) that is fully parsed and fully rewritten per build.

The post-edit hook triggers this on every reindex (`_build_graph_artifacts` runs unconditionally, `indexer.py:2756-2828`), so a one-file edit pays: parse 22.6 MB state + re-merge 453 artifacts + full cross-file rewrite + rewrite everything. On the self-hosted repo this is tolerable; at 5k files / 100k+ nodes the same design is O(repo) work and hundreds of MB of I/O per edit. `1p9py` (compression) shrinks the bytes ~20× but not the work — this change fixes the work:

1. **Incremental merge:** keep the merged node/edge maps across builds and apply per-file deltas (remove the old file's fragment, insert the new one), rather than re-merging from scratch.
2. **Symbol-scoped cross-file invalidation:** the subtle correctness core. Cross-file resolution binds an edge only when the candidate set for a name is unique (the v24/v25 mechanism in the `GRAPH_BUILDER_VERSION` changelog, `graph_indexer.py:35`). A changed file can flip uniqueness **elsewhere**: adding a second `Foo` must demote a previously-bound `calls → Foo` edge in an *untouched* file back to `external::Foo`; deleting one must promote. Invalidation must therefore be keyed by **symbol name** (the names a changed file defines/exports, before and after), re-running resolution only for edges referencing affected names — not merely by file.
3. **Per-file state store:** replace the monolithic state document with a store supporting per-file reads/writes (a directory of per-file compressed artifact blobs with a small manifest, or an equivalent SQLite table — decided by a measurement-informed spike, see Decision Log), so a one-file build reads and writes O(changed) state, not O(repo).

The faithfulness stakes are high: the "never bind the wrong twin" property is guarded by an adversarial test pattern (`test_graph_indexer.py` — e.g. `test_ambiguous_simple_name_stays_external:807`, `test_ambiguous_cross_file_simple_name_not_promoted:2201`, `test_cross_file_resolution_still_faithful:5683`). The non-negotiable invariant for this change: **an incremental build must produce a graph logically identical to a from-scratch build of the same tree.** Per the standing security-control-faithfulness rule, this change requires an adversarial review lane before close — green unit tests have missed silent narrowing in resolution changes before.

## Requirements

1. **Delta merge.** `finalize()` (or its successor) maintains persistent merged node/edge maps and applies per-file deltas for changed/removed files. A build with zero changed files performs no merge work and no artifact rewrite (today it re-merges everything and rewrites all files regardless). **Persistence model (council clarification, prepare review 2026-07-03):** builds run in hook-spawned, short-lived processes, so "persistent" means *on disk*, not in a process — the merged maps ARE the payload artifact: an incremental build loads the current payload, applies the delta, and atomically rewrites it (via `1p9py`'s writer). The symbol-scoped re-resolution additionally needs a name → candidate-ids lookup; maintain it incrementally alongside the merged maps (persisted with the payload or state store, or rebuilt from the loaded payload at build start if measured cheap — spike decides) rather than recomputed repo-wide, or the invalidation step silently reintroduces O(repo) work.
2. **Symbol-scoped invalidation.** For each changed/removed file, compute the symbol-name delta (names defined/exported before vs after, including class/function/constant simple and qualified names, plus import-graph effects used by import-edge disambiguation). Re-run cross-file resolution exactly for: (a) all edges originating in changed files, and (b) all edges in *any* file whose target name's candidate set may have changed — i.e., edges referencing a name in the delta (bound or `external::`). Promotion (external → bound) and demotion (bound → external) both work.
3. **Equivalence invariant.** For any edit sequence, the incrementally-maintained graph equals a full rebuild of the same tree: same node set, same edge set (including confidence levels), same `input_fingerprint` (`graph_indexer.py:8172-8182`). This is the primary acceptance surface, enforced by a randomized/differential test harness, not only hand-picked cases.
4. **Per-file state store.** The state layer exposes per-file get/put/delete plus iteration, with per-file (not whole-store) write granularity. Store-level metadata (builder/chunker/walker versions, epoch) preserves the existing whole-store invalidation semantics (`_load_state`, `graph_indexer.py:5552-5569`): version mismatch still invalidates everything and forces full re-extraction. Backend selected by spike measurement (per-file gzip blobs + manifest vs stdlib SQLite); selection criteria: per-build I/O at 1-file change on a 5k-file synthetic corpus, crash-consistency story, Windows behavior (no new native deps — stdlib only either way).
5. **Full-rebuild path retained.** `full=True` / version-mismatch / missing-state builds do a from-scratch extract+merge exactly as today, and that path also (re)seeds the persistent merged maps and state store. The differential harness uses it as the oracle.
6. **Crash consistency.** An interrupted incremental build never leaves a torn store or a merged map inconsistent with the state manifest — writes are atomic per file with a last-writer manifest (or SQLite transaction); a detected inconsistency degrades to full rebuild (loudly, via the existing stderr build log), never to a silently wrong graph.
7. **Downstream analysis passes.** Clusters (and betweenness, if `1p9q1` lands) still recompute from the merged maps per build. Re-analysis cost on unchanged-graph builds is skipped via the fingerprint (if the merged fingerprint is unchanged, analysis artifacts are not recomputed or rewritten).
8. **Version bump + migration.** `GRAPH_BUILDER_VERSION` bumped; a legacy monolithic state file is either migrated in one pass or discarded in favor of a one-time full re-extract (spike decides — migration is preferred if cheap, discard is acceptable given version-mismatch already forces re-extract today; the upgrade path must be explicit either way).
9. **Instrumentation.** The existing build log line (`indexer.py:2815-2819`) gains merge-phase timing and delta sizes (files changed, symbols invalidated, edges re-resolved), so field reports can distinguish extraction cost from merge cost.

## Scope

**Problem statement:** Every build re-merges all cached per-file artifacts, re-runs cross-file resolution repo-wide, fully parses and rewrites a monolithic 22.6 MB state document, and rewrites all graph artifacts — O(repo) work per one-file edit, hook-triggered on every edit.

**In scope:**

- Persistent merged maps + per-file delta merge in the finalize path.
- Symbol-scoped cross-file invalidation (promotion and demotion), including import-disambiguation effects.
- Per-file state store (spike → blobs-vs-SQLite decision → implementation), with version/epoch semantics preserved and crash consistency.
- Fingerprint-gated skip of unchanged analysis/artifact rewrites.
- Differential test harness (incremental vs full-rebuild oracle over randomized edit sequences on fixture corpora) plus targeted twin-flip cases; adversarial review lane at wave review.
- Migration/discard path for legacy state; version bump; instrumentation.
- Before/after measurement: 1-file-edit build wall time and bytes written on the self-hosted repo and a large synthetic corpus.

**Out of scope:**

- Changing extraction, per-language resolvers, or resolution *semantics* — identical output graphs is the invariant; only *when* resolution re-runs changes.
- Artifact serialization format (owned by `1p9py`; this change writes through whatever that lands).
- Query-side behavior (`1p9pz` owns caching; the payload artifact remains the query contract).
- Incremental clustering/betweenness algorithms (analysis passes remain recompute-on-change; only the unchanged-skip is added).
- Any new non-stdlib dependency (explicitly: no kuzu/duckdb/rustworkx; SQLite candidate is stdlib `sqlite3`).

## Acceptance Criteria

- [ ] AC-1: A one-file edit build performs merge work proportional to the delta: state I/O touches only changed files plus the manifest (verified by instrumentation/counters in test), and a zero-change build rewrites no artifacts. Unit/integration-tested; measured 1-file-edit wall time and bytes written on the self-hosted repo recorded in the Progress Log with the pre-change baseline.
- [ ] AC-2: Differential equivalence — over randomized edit sequences (add/modify/delete files that define/reference shared names) on fixture corpora, the incremental graph equals the full-rebuild oracle after every step: node set, edge set with confidences, and `input_fingerprint` all identical. Harness lands in the suite with a fixed seed set; any divergence is a test failure printing the offending sequence.
- [ ] AC-3: Twin-flip faithfulness — targeted tests: (a) adding a second `Foo` in file B demotes a previously-bound edge → `external::Foo` in untouched file A; (b) deleting one of two `Foo`s promotes A's `external::Foo` edge to bound; (c) same via import-disambiguation change; (d) rename flows (old name released, new name bound) — each asserted equal to the full-rebuild oracle, in the spirit of the existing ambiguity suite.
- [ ] AC-4: Version/epoch semantics — a builder/chunker/walker version mismatch still invalidates the whole store and full-re-extracts; the legacy monolithic state file is migrated or discarded per the decided path, exactly once, idempotently. Unit-tested.
- [ ] AC-5: Crash consistency — a build interrupted between per-file writes (fault-injection test) leaves the store detectably consistent-or-degraded: the next build either resumes correctly or performs a loud full rebuild; it never serves a merged graph inconsistent with the oracle. Unit-tested.
- [ ] AC-6: Unchanged-graph builds skip analysis recompute and artifact rewrites (fingerprint-gated); a changed-graph build still refreshes clusters (and betweenness if present). Unit-tested.
- [ ] AC-7: State-store spike recorded — the blobs-vs-SQLite measurement (1-file-change I/O on a 5k-file synthetic corpus, crash story, Windows notes) and the selection rationale are in the Decision/Progress Log before the backend implementation lands.
- [ ] AC-8: Instrumentation — the build log reports merge timing and delta sizes (files, symbols invalidated, edges re-resolved). Verified by test on the log line shape.
- [ ] AC-9: Adversarial review lane run at wave review for the resolution-invalidation logic (security-control-faithfulness rule: differential green is necessary, not sufficient); findings addressed or explicitly dispositioned before close.
- [ ] AC-10: `python3 .wavefoundry/framework/scripts/run_tests.py` passes; `wave_validate` clean; no `__pycache__` under `scripts/`.

## Tasks

- [ ] Spike: per-file gzip blobs + manifest vs stdlib SQLite for the state store; measure on a 5k-file synthetic corpus; record decision (AC-7).
- [ ] Implement the state-store abstraction (get/put/delete/iterate, store-level version metadata, atomic per-file writes / transactions, migration-or-discard of legacy state).
- [ ] Restructure finalize: persistent merged node/edge maps, per-file fragment removal/insertion, zero-change fast path.
- [ ] Implement symbol-delta computation (defined/exported names before/after per changed file + import-graph effects) and symbol-scoped re-resolution (promotion + demotion), reusing the existing unique-candidate resolution functions unchanged.
- [ ] Fingerprint-gated skip for analysis passes and artifact rewrites.
- [ ] Differential harness (randomized edit sequences vs full-rebuild oracle, fixed seeds) + targeted twin-flip/import-flip/rename tests + fault-injection crash tests.
- [ ] Instrumentation in the build log; version bump with changelog entry.
- [ ] Measure before/after (self-hosted repo + synthetic large corpus); record in Progress Log.
- [ ] Run `run_tests.py` + `wave_validate`; clean `__pycache__`; flag the adversarial review lane in wave review.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| ws1-spike-state-store | implementer | — | Backend spike + measurement + decision record; then the store abstraction with atomicity/versioning/migration. |
| ws2-delta-merge | implementer | ws1-spike-state-store | Persistent merged maps; per-file fragment delta; zero-change fast path; fingerprint-gated skips. |
| ws3-symbol-invalidation | implementer | ws2-delta-merge | Symbol-delta computation + scoped re-resolution (promote/demote); the correctness core — smallest possible diff over existing resolution functions. |
| ws4-differential-harness | implementer | ws2-delta-merge, ws3-symbol-invalidation | Randomized differential harness + twin-flip/rename/crash fault-injection tests + instrumentation checks. |
| ws5-adversarial-review | reviewer | ws3-symbol-invalidation, ws4-differential-harness | Faithfulness red-team on invalidation completeness (what edit shapes could the symbol delta miss?); runs in wave review. |


## Serialization Points

- Sequenced **after** `1p9py` (this change writes state through the compressed I/O helpers; doing it in the other order rewrites this change's store code).
- ws1's store interface gates ws2; ws3 is deliberately isolated so the resolution-scoping diff is reviewable on its own.
- `finalize()` is the hub file region shared with `1p9q1`'s analysis placement — coordinate the analysis-pass seam (fingerprint-gated skip) between the two changes at integration.
- One coordinated `GRAPH_BUILDER_VERSION` bump at wave integration with `1p9py`/`1p9q1`.

## Affected Architecture Docs

Audit `docs/specs/mcp-tool-surface.md` (index build/status descriptions) and any architecture/reference doc describing the graph build pipeline or the state file's role; document the per-file state store and the incremental-merge invariant (incremental ≡ full rebuild). If a data-and-control-flow doc covers indexing, the merge path description changes. The build-pipeline contract change warrants a decision record for the store-backend selection (spike outcome).

## AC Priority

(Populated at Prepare wave.)


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | O(delta) builds are the point of the change. |
| AC-2 | required | The equivalence invariant is the correctness contract; without the differential oracle the change is unverifiable. |
| AC-3 | required | Twin promotion/demotion is exactly where incremental resolution silently goes wrong; these are the adversarial cases. |
| AC-4 | required | Version invalidation and one-time migration protect every target repo at upgrade. |
| AC-5 | required | A torn store yielding a silently wrong graph is the worst failure mode; loud degradation is mandatory. |
| AC-6 | important | Skip-on-unchanged is a real win but a missed skip only costs time, not correctness. |
| AC-7 | required | The backend decision must be evidence-based and recorded; it shapes crash-consistency and Windows behavior. |
| AC-8 | important | Field diagnosability; no correctness impact. |
| AC-9 | required | Standing rule for detection/binding-faithfulness changes; differential tests alone have missed narrowing before. |
| AC-10 | required | Suite + docs-lint green is the standing merge gate for framework code. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-03 | Scoped from the graph-index efficiency evaluation. Confirmed: per-file extraction cache with full re-merge in `finalize()` (`graph_indexer.py:7404-7541`); monolithic state 22.6 MB vs 11.7 MB payload on the self-hosted repo; hook-triggered on every reindex (`indexer.py:2756-2828`); whole-store version invalidation (`graph_indexer.py:5552-5569`); cross-file unique-candidate resolution per v24/v25 changelog (`graph_indexer.py:35`); reverse-invalidation precedent for dangling edges exists (`graph_indexer.py:7593` region). Faithfulness oracle: the ambiguity test pattern in `test_graph_indexer.py` (:807, :2201, :5683 et al.). | `graph_indexer.py:35,5484,5552-5569,7404-7541,7593`; `indexer.py:2756-2828`; measurements 2026-07-03. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-03 | Incremental merge with symbol-scoped invalidation over persistent merged maps (approach A). | Converts per-edit cost from O(repo) to O(delta) while keeping resolution *semantics* untouched (only re-run scope changes); the differential-oracle harness plus the existing full-rebuild path make equivalence checkable; symbol-name keying is the minimal invalidation unit that is still provably sufficient for unique-candidate resolution (uniqueness of a binding depends only on the candidate set for that name). | (B) File-scoped invalidation (re-resolve only changed files' edges) — weakness: **incorrect** — misses demotion/promotion of edges in untouched files when a twin appears/disappears; exactly the wrong-twin failure the test suite guards. (C) Full re-merge but only when the extraction delta is non-empty, plus skip rewrites on unchanged fingerprint — weakness: honest and simple but still O(repo) merge on every real edit; acceptable fallback if the spike reveals blocking complexity, not the goal. |
| 2026-07-03 | State-store backend decided by spike (per-file gzip blobs + manifest vs stdlib SQLite), not up front. | Both are stdlib-only and satisfy per-file granularity; they differ in crash-consistency ergonomics (SQLite transactions vs atomic-rename + manifest) and small-file I/O behavior (Windows filesystems penalize many small files) — measurable, not arguable. Deciding on evidence honors the calibrate-don't-guess rule; the store sits behind an abstraction either way. | Pick SQLite now — likely winner on crash story but thousands-of-blobs vs one-db I/O on Windows deserves the measurement; pick blobs now — simplest but weakest crash story. Embedded graph DBs (kuzu) — rejected outright: unmaintained-vendor risk (company ceased operations 2025), native-dep Windows risk, and the query side stays in-memory regardless (evaluation finding). |
| 2026-07-03 | Analysis passes stay recompute-on-change (fingerprint-gated skip only). | Incremental Leiden/betweenness maintenance is research-grade complexity; the passes are seconds-scale at current sizes and gated off entirely when the graph is unchanged — the dominant hook-fire case. | Incremental community maintenance — rejected as speculative complexity with no measured need (simplest-solution-first). |
| 2026-07-03 | Sequence after `1p9py` in the same wave. | The store writes through the compressed I/O helpers; landing format first avoids rewriting this change's persistence twice. Tier-1 changes also de-risk independently if this change slips. | Land together unordered — rejected: avoidable churn on the shared writer seam. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Symbol-scoped invalidation misses an edit shape (re-export/barrel chains, qualified-vs-simple name aliasing, package-authoritative Go resolution) → stale wrong-twin edge in an untouched file. | The symbol delta includes qualified names and import-graph effects; the randomized differential harness (AC-2) explores composed edit sequences beyond hand-written cases; targeted twin/import/rename tests (AC-3); mandatory adversarial review lane (AC-9) hunts the miss classes explicitly. Fallback: any detected inconsistency degrades loudly to full rebuild. |
| Persistent merged maps drift from state-store truth after a crash. | AC-5 fault-injection; manifest/transaction consistency check on load; degrade-to-full-rebuild is always available and loud. |
| Many-small-files store behaves badly on Windows (open-handle cost, AV scanning). | The spike measures on a 5k-file corpus with Windows notes; SQLite is the standing alternative; store is behind an abstraction so the backend is swappable. |
| Complexity lands but wins are marginal on small repos. | Zero-change fast path and O(delta) merge cost nothing extra on small repos; the differential harness keeps the added complexity honest; the C fallback (skip-rewrites-only) is recorded if the spike kills the approach. |
| Interaction with the in-query synchronous rebuild path (`graph_query.py:122-275`) during a version-bump upgrade. | Existing inflight-lock coordination unchanged; version mismatch takes the full-rebuild path which reseeds store + maps atomically before the payload is republished. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
