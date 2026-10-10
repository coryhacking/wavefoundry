# Preserve complete graph communities across publication resets

Change ID: `207t3-bug graph-community-reset-publication`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-10-08
Wave: `207t4 graph-community-publication`

## Rationale

The canonical Waveforge qualification exposed incomplete community membership after the Rust graph builder version changed. GraphPublication.apply deletes the graph tables on reset, but graph_cluster.prepare_cluster_publication diffs against the still-readable previous generation. Unchanged communities and members are omitted, then deleted at publication. update_graph_clusters accepts the incomplete reconstruction when the topology fingerprint matches, preventing subsequent setup from repairing it. Deliver a bounded publication repair and automatic recovery of this incomplete state, preserving atomicity and normal incremental writes. This necessary qualification fix is separate from C1–C5; no assertions or gate budgets are waived.

Executed scratch proof uses actual GraphPublication and GraphCommunityPublication: three unchanged members survive reset=false and disappear reset=true while analysis still claims three. A subsequent unchanged-fingerprint call supplies no repair publication. The current repository has 137 advertised communities and 70,518 advertised members, but only 19 community rows and 832 membership rows. These observations are diagnosis, not a requirement tied to this checkout's changing data.

## Requirements

1. Prepare communities and memberships against the database state that will exist when the graph publication applies. A reset must publish the complete newly computed replacement, including unchanged communities and members, inside the existing single transaction. Preserve the previous visible generation until commit and rollback behavior on failure.
2. Reuse persisted clusters for an unchanged fingerprint only when their stored community and membership representation is complete under the existing cluster contract. Incomplete or contradictory published rows must cause recomputation and a repair publication. Do not synthesize members from counts or accept an incomplete partition as current.
3. Preserve normal no-reset incremental behavior: unchanged memberships are not rewritten; a valid unchanged generation avoids clustering and betweenness recomputation. Preserve stable community IDs where supported, layer isolation, graph compatibility checks, and source rechecks.
4. Test through actual publication orchestration and stored-response consumers, including reset, unchanged-fingerprint corruption recovery, valid reuse, transaction failure and representative production/evidence communities. The change's own tests must be independent of the running checkout's graph contents.
5. Document the reset baseline and reuse completeness invariant. Repair the local derived graph using canonical setup after implementation, verify the original evidence-partition queries, and run the full framework suite as a qualification gate.

## Scope

In scope: reset-aware community preparation, persisted-membership completeness for fingerprint reuse, their direct publication callers and verification consumers. The observed repository database is derived state, never checked-in source.

Out of scope: Rust extraction changes, role-link migration, readiness phase isolation, new clustering algorithms, evidence-partition ranking semantics, relaxing fixture assertions or timing budgets, close/commit/push, private security requests and journal relocation.

## Acceptance Criteria

- [x] AC-1: A real graph version-reset publication preserves every expected computed community/member row, including rows unchanged from the preceding generation; analysis and reconstructed rows agree after commit.
- [x] AC-2: Same-fingerprint reuse rejects an incomplete published representation and restores the correct members through recomputation/publication; missing community and member rows have non-vacuous controls.
- [x] AC-3: Valid unchanged reuse still skips expensive analysis and produces no unnecessary membership rewrite; normal changed membership retains bounded incremental writes.
- [x] AC-4: The actual transaction preserves the old visible generation until commit and restores it after a failure; layer/compatibility/source checks continue working.
- [x] AC-5: Controlled production/evidence fixtures return their correct independent rankings and limits after reset and recovery, without requiring the running checkout's contents.

## Tasks

- [x] Capture the reset-baseline and incomplete-reuse failures with actual publication fixtures.
- [x] Propagate reset state to cluster preparation and validate persisted completeness before reuse.
- [x] Exercise transaction, incremental/reuse and response controls; detect representative known-bad mutations.
- [x] Update publication documentation and obtain independent code, QA, architecture, docs-contract and performance review.
- [x] Refresh the local derived graph through canonical setup and record the original consumer qualification; run the canonical suite last before technical close checks.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Publication and clustering | Implementer | Readiness | Serialize graph_indexer with completed Rust source |
| Verification and documentation | QA / technical writer | Implementation | Real SQLite and public consumer oracles |
| Independent review | Required reviewers | Frozen implementation | No self-approval |

## Serialization Points

- `.wavefoundry/framework/scripts/indexer.py`
- `.wavefoundry/framework/scripts/graph_indexer.py`
- `.wavefoundry/framework/scripts/graph_cluster.py`
- `.wavefoundry/framework/scripts/tests/test_graph_cluster.py`
- `.wavefoundry/framework/scripts/tests/test_graph_transactional_state.py`
- `.wavefoundry/framework/scripts/tests/test_indexer.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools_retrieval.py`
- `docs/architecture/data-and-control-flow.md`
- `docs/architecture/testing-architecture.md`

## Affected Architecture Docs

Data-and-control-flow: one transaction uses the replacement baseline on reset; fingerprint reuse requires complete persisted membership. Testing-architecture: controlled reset/recovery and production/evidence response oracles.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Fix loss at reset |
| AC-2 | required | Repair already incomplete derived stores |
| AC-3 | required | Preserve the normal fast path |
| AC-4 | required | Preserve publication atomicity |
| AC-5 | required | Verify observable consumer behavior |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-08 | Planned separately after actual reset/no-reset and fingerprint-reuse probes. No source edits before Prepare. | /tmp/wf-204mp-cluster-reset-probe.py and .log; current GraphPublication.apply and cluster preparation/reuse code |

| 2026-10-08 | Coordinator independently reran the actual reset/no-reset publication probe: reset loses all three unchanged members; unchanged-fingerprint follow-up supplies no repair. Targeted current source confirms the orchestration owner is indexer._build_graph_artifacts. | python3 -B /tmp/wf-204mp-cluster-reset-probe.py, exit 0 asserts diagnosed failure; live code_read GraphPublication.apply, prepare_cluster_publication, update_graph_clusters and _build_graph_artifacts |

| 2026-10-08 | Full independent readiness complete: actual standard primer, four isolated fixed seats, rotating performance/docs, alternative weighing, red-team closing and fresh anonymized chair; five required lane approvals plus council typed at current receipt0cce. wf_prepare_wave(mode=ready) succeeds, no activation or source edits; all nine scope fingerprints unchanged. Implementation ACs/tasks remain pending. | readiness-evidence.json; wave Review Checkpoints; events.jsonl; full wf_validate_docs and Prepare lint/garden clean |

| 2026-10-08 | Readback: implement complete replacement on every scheduled global reset, including valid same-fingerprint reuse, and structurally validate persisted catalogs/members before reuse. Before: walker reset can erase 2 communities/9 members while reused clusters return no publication; after: reuse may skip analysis but supplies complete reset rows. Preserve old generation for supported IDs, historical member stamps, normal delta/no-op, sole transaction/source/schema guards and global reset. AC1–5 map to declared graph/indexer, test and architecture paths; no semantic partition-certification, C5/private/journal scope or close/commit/push. Root activated207t4 and opened gate; root owns quiet canonical/setup and C1 inventory. | Current readiness-evidence.json and receipt0cce; mandatory pre-implementation memory briefing; both current indexer callers and projection/fixed-category source read live |

| 2026-10-08 | Implementation frozen: both indexer callers propagate scheduled global reset; reset preparation uses empty write baseline while retaining old generation for supported IDs. Valid reset reuse still publishes all rows without expensive analysis; analysis_recomputed preserves truthful existing result metadata. SQL reuse validates structural catalogs/attributes/counts/seeds, exact eligible identities/pairs and fixed categories; no partition-certification claim or format/version bump. Pending Rust edits preserved. | implementation-evidence.json; indexer.py, graph_cluster.py; GraphCommunityPublication only adds analysis_recomputed default |
| 2026-10-08 | AC1–5 verified through actual build/orphan orchestration, SQLite reset/recovery and WAL reader/SQL rollback/source/schema/layer controls, valid historical/empty no-op, bounded one-member delta, and two production/two larger evidence artifacts with independent literal limits1/2 identities/order/counts/hubs. All ACs and first three tasks marked complete; architecture docs updated, remaining combined review and canonical tasks deliberately unchecked. | 94 transaction/cluster tests in 2.270s; 3 controlled public-response tests in 0.864s; whole indexer owner398 in 182.223s. Total495 passed, zero skips; /tmp/wf-207t4-indexer-owner.log; AC map in implementation-evidence.json |
| 2026-10-08 | Negative controls detect nine transaction source defects (reset baseline/participant, both caller inputs, completeness bypass, false recomputation metadata and isolated fixed/identity/catalog guards) plus two public-consumer defects at genuine assertions. Equal-count ghost and fixed swaps use nonseed members to isolate their guard. Pre-fix proof belongs to actual readiness probes; helper fixtures did not run before the core landed. Source/test helpers finished. | /tmp/wf207t4-mutants-gsrf_h1u/*.log; /tmp/wf-207t4-consumer-mutants.py and reset/reuse logs; implementation-evidence.json |
| 2026-10-08 | Root retains canonical setup/live consumer qualification, quiet full-suite receipt, maintained C1 test inventory and fresh independent delivery review. No close-ready claim, self-approval, gate closure, pause, close, commit or push. Scoped git diff --check passes. | /tmp/wf-207t4-frozen.json contains all nine frozen SHA256 paths; readiness evidence remains unchanged historical proof |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-08 | Select reset-aware replacement preparation plus completeness-gated reuse. | Repairs the causal publication defect and recovers existing incomplete state while retaining the incremental contract. | Always rewriting all cluster rows avoids the reset hole but violates bounded incremental writes. A version bump alone masks this repository's state without fixing the next reset or stable-fingerprint corruption. Weakening response assertions leaves silently incomplete graph results. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Completeness checks accidentally reject valid fixed communities or duplicate legitimate memberships. | Derive the invariant from existing stored community semantics and exercise representative fixtures before choosing implementation details. |
| Reset preparation uses a separate mutation that exposes an empty generation. | Prepare outside the lock and apply all replacement rows only inside the existing transaction. |
| Recovery or validation imposes corpus-sized work on every normal query. | Keep checks on the build/reuse path, retain valid no-op publication and measure the affected fast path. |

## Session Handoff

Planning only. Public 204mp is OPEN; ready this wave without activation and serialize implementation after pausing that wave's admitted repair work. No closure/commit/push approval is implied. See docs/agents/session-handoff.md.
