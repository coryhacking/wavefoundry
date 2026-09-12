# Unified Index Compatibility and Recovery

Change ID: `1xoye-bug unified-index-compatibility-and-recovery`
Change Status: `review`
Owner: Engineering
Status: active
Last verified: 2026-09-11
Wave: 1xq4f dashboard-lifecycle-integrity

## Rationale

The operator requested that all four findings from the uncommitted-change compatibility review join wave `1xq4f`. This change protects agents and operators using the unified index on macOS, Windows and Linux: graph citations must describe one generation, failed indexing must release its database handles, graph failures must identify the correct recovery action, and Windows tests must not assume symlink privileges.

The review demonstrated three runtime defects and one test-only portability defect. It did not demonstrate a Windows cutover failure or unsafe cleanup. Preserve unified SQLite, its existing ownership controls and forward upgrade recovery. Repair these bounded mechanisms rather than reopen the storage architecture. Evidence is retained in the wave's `compatibility-review.json`; the review covered the uncommitted tree after `1xny6`, and does not certify native Windows/Linux/Intel macOS package execution.

## Requirements

1. `graph_indexer.read_published_graph_snapshot` must bind graph metadata, nodes, edges and source hashes to one explicit SQLite read transaction, released on every outcome. Its exact-definition consumer must never certify an old node using a new source receipt.
2. Every `IndexStateStore` owned by `indexer._build_index_locked`, including its idle path, must close on success, ordinary failure and cancellation. Closure spans preparation, reconciliation and publication, preserves rollback and the original error, and must not depend on destruction of a retained exception traceback.
3. Graph snapshots and their public consumers must preserve typed runtime/storage/migration failure causes and actionable recovery. An unavailable native runtime, refused WAL filesystem or pending migration must not be represented as a genuinely unbuilt graph. Missing content and transient in-flight publication remain distinct states; do not restore stale JSON as a fallback.
4. The new migration inventory test must run ordinary file/directory cases even when native symlink creation is unavailable. Only unsupported symlink cases may skip, with an explicit reason; retain deterministic reparse/ownership protection coverage.

## Scope

**In scope:** the four findings, their focused regression and known-bad controls, and documentation of the corrected contracts.

- `ARCH-COMPAT-2`: missing read transaction in `read_published_graph_snapshot`; a real second-connection commit returned an old node and new source hash. A `BEGIN` control returned consistent old data.
- `ARCH-COMPAT-1`: missing unconditional shared-store cleanup; cancellation and reconciliation errors left a real APSW connection queryable while the exception traceback was retained. Rollback worked. Windows replacement interference is a possible consequence, not a native observation.
- `COMPAT-1`: graph reader exception handling erased `storage_runtime_unavailable` and `storage_recovery_required`; dashboard output reported absence and the path tool recommended graph creation for a valid existing graph.
- `compat-qa-1`: new migration inventory symlink cases error under injected Windows privilege denial before reaching the inventory. Tests are not deployed; this adds to an existing suite portability gap.

**Out of scope:** replacing SQLite or command-line dashboard identity; changing migration ownership or destructive cleanup policy; changing pinned dependencies; broad test-suite cleanup; retroactively editing closed-wave reviews; claiming native platform qualification from mocks or local tests. The existing dashboard change remains separately admitted.

## Acceptance Criteria

- [x] AC-1: A deterministic two-connection test commits a newer graph and source manifest between reads and proves the helper returns one consistent generation. The exact-definition consumer is also exercised so old declarations cannot be certified by new source receipts. Removing the read transaction makes the named regression fail; transaction/connection cleanup is asserted on failure.
- [x] AC-2: Public build tests retain exception tracebacks after cancellation during graph publication and an ordinary reconciliation failure and prove each owned APSW connection is already closed, the build lock is released and no partial participant writes are committed. Include the idle-path failure case. Removing unconditional cleanup makes the named test fail; normal standalone process termination is not substituted for this proof.
- [x] AC-3: A valid published graph used through public MCP and dashboard consumers preserves runtime/storage/migration failure codes and useful recovery under bounded injected faults. It does not recommend rebuilding as a remedy for an unavailable binding or unsupported filesystem. Missing graph and in-flight publication controls retain their legitimate behavior. Restoring the broad exception-to-absence translation makes the named assertions fail.
- [x] AC-4: With symlink creation raising a Windows-style capability error, the inventory test still executes its ordinary file/directory assertions and reports only the unsupported symlink cases as explicit skips. With symlinks available, the real symlink cases execute. Existing simulated reparse/ownership assertions remain effective. Restoring unconditional symlink creation makes the capability-denial regression fail.

## Tasks

- [x] Pin the direct published graph helper's complete read to one transaction and add helper/consumer interleaving coverage.
- [x] Apply unconditional cleanup over the full lifetime of full/changed and idle build stores, including reconciliation errors and cancellation; test retained tracebacks.
- [x] Carry typed failure details through `GraphSnapshot`, graph tools and dashboard consumers; preserve absence and in-flight semantics with positive and negative controls.
- [x] Make only the new inventory fixture's symlink-dependent cases capability-aware, retaining ordinary and simulated reparse coverage.
- [x] Record one named falsifying control per AC and run the change's affected suites; document any intentional platform skips separately from passing coverage.
- [x] Update the affected architecture/recovery documentation and the end-user changelog description when implementation lands.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| C1 snapshot and build lifetime | implementer | — | Graph producer/helper and indexer; AC-1/AC-2. |
| C2 graph diagnostics | implementer | — | Snapshot and public response consumers; AC-3. |
| C3 portable fixture | implementer | — | Migration tests only; AC-4. |
| C4 documentation and review | implementer / reviewers | C1, C2, C3 | Reconcile contracts and focused proof. |

## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/graph_indexer.py`, `.wavefoundry/framework/scripts/indexer.py`, `.wavefoundry/framework/scripts/graph_snapshot.py`, `.wavefoundry/framework/scripts/graph_query.py`
- `.wavefoundry/framework/scripts/server_impl.py`, `.wavefoundry/framework/scripts/dashboard_lib.py`, `.wavefoundry/framework/scripts/dashboard_server.py`
- `.wavefoundry/framework/scripts/tests/test_indexer.py`, `.wavefoundry/framework/scripts/tests/test_graph_snapshot_readers.py`, `.wavefoundry/framework/scripts/tests/test_server_tools_retrieval.py`, `.wavefoundry/framework/scripts/tests/test_dashboard_server.py`, `.wavefoundry/framework/scripts/tests/test_sqlite_storage_migration.py`
- `docs/architecture/data-and-control-flow.md`, `docs/architecture/graph-index-system.md`, `docs/architecture/testing-architecture.md`

Read-only contract references: `index_state_store.open_read_only`, `sqlite_runtime` typed exceptions and `sqlite_storage_migration` recovery codes. Declare any necessary expansion during re-Prepare rather than treating the entire storage layer as write scope.

The dashboard change also owns `server_impl.py`, `dashboard_lib.py`, `dashboard_server.py` and dashboard tests. Use one owner at a time for those files; C2 must serialize with dashboard L1/L2. C4 shares `data-and-control-flow.md` with dashboard L3. The sibling plan's original disjoint-file concurrency statement applies only within that change, not across the expanded wave. The changelog is a separate root-level documentation target, not a declared path token.

## Affected Architecture Docs

- `docs/architecture/graph-index-system.md`: explicit read-snapshot and diagnostic contracts.
- `docs/architecture/data-and-control-flow.md`: connection ownership across failure/cancellation and actionable reader recovery.
- `docs/architecture/testing-architecture.md`: concurrency controls, retained-traceback checks and capability-aware Windows test coverage.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Mixed generations undermine source-bound citations on every platform. |
| AC-2 | required | Failed work must release its owned database resources deterministically. |
| AC-3 | required | Operators need the real failure cause to recover without futile rebuilds. |
| AC-4 | required | The admitted Windows fixture must reach the behavior it is meant to test. |

## Validation and Release Gates

Re-Prepare the expanded wave before code edits. Required review coverage includes code, QA, architecture and security, with performance review for changed indexing/reader paths and release review of the qualification boundary. Run affected tests and full framework validation at the normal delivery gate; local green tests alone do not qualify other hosts.

Retain the existing native package qualification gate from `1xny6`: actual packaged setup/upgrade, graph and semantic reads, incremental publication and fresh-process reopen on the supported target matrix. Native Windows additionally needs real retained-handle cutover/retry and capability-limited account checks. Linux, Windows and Intel macOS execution remains outstanding; neither injected Windows errors nor a wheel inventory marks it complete. No new platform support or intermediate bridge release is introduced here.

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-11 | Operator admitted all four compatibility findings for repair; implementation remains pending. | `compatibility-review.json`: architecture, reality, QA, security and release reports; original review verified no Python source drift during review. |
| 2026-09-11 | Readback: pin graph helper reads to one transaction; close owned full/idle build stores on every exit; preserve typed errors through public readers; skip only unsupported symlink fixture cases. Thought: C1 storage owner precedes T1; coordinator owns C2/C3, with server/dashboard edits after L1/L2 ownership releases. | Current readiness receipt and typed lane approvals; implementation now authorized. |
| 2026-09-11 | AC-4 complete: migration suite passed (108 tests, one existing skip); injected Windows denial executes three ordinary shapes plus removable control and skips only two link cases. Unguarded fixture mutant fails the denial regression. | `implementation-evidence.json`: symlink_fixture. |
| 2026-09-11 | AC-3 complete: typed causes and recovery survive snapshot/query/public MCP/dashboard adapters; cache and post-fault recovery controls pass. Snapshot 50, query 92, retrieval 1,034 (nine skips), focused 5; four old-behavior mutants fail. | `implementation-evidence.json`: graph_diagnostics. |
| 2026-09-11 | Storage/targeted implementation complete: final eight contract tests and exact-definition consumer pass; six named production mutants fail. A schema-refusal defect found in the broader run is repaired and passes focused verification; canonical full validation is pending. | `implementation-evidence.json`: storage_and_targeted, frozen source hashes. |

| 2026-09-11 | Canonical validation found one graph-state consumer regression: codebase-map safe generation returned success for corrupt storage. AC-3 reopened for compatible failure-state handling; all other modules passed. | `implementation-evidence.json`: canonical_validation; 8,897 tests, one failure. |

| 2026-09-11 | AC-3 repair verified: preserve the established NOT_READY snapshot contract while retaining typed diagnostics. Existing map and receipt survive read failure; genmap 69, snapshot 51 and query 92 pass. Five mutation controls fail. | `implementation-evidence.json`: graph_diagnostics; final full-suite rerun underway. |

| 2026-09-11 | Implementation complete and ready for delivery review: canonical suite green, 8,898 tests across 86 files, 12 skips; receipt recomputed against the final source. Docs gate and whitespace check pass. | `implementation-evidence.json`: canonical_validation. |

| 2026-09-11 | Delivery finding ARCH-DELIVERY-001 repaired: architecture prose now describes shared SQLite ownership and distinguishes physical row retention from epoch-governed availability. Fresh architecture replay and council passed; no runtime changes. Gapfill: shell used for two bounded prose replacements and report aggregation, with code claims independently verified through MCP-first reviewers and executed probes. | `delivery-review.json`: architecture-reverification and council; typed cycle 1 complete. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-11 | Select focused repairs within unified SQLite and keep native qualification separate. | Each demonstrated defect has a bounded mechanism and falsifying test; preserves the accepted consolidation benefits. | Rejected: restoring a second JSON/storage backend, which duplicates authority and hides runtime failures. Rejected: shipping unchanged with documentation alone, which does not repair demonstrated mixed reads or resource/diagnostic defects. |
| 2026-09-11 | Track the four findings as one separate bug change in `1xq4f`. | The shared storage and test work is materially different from dashboard process identity, but belongs in the operator-selected wave. | Expanding the dashboard ACs would blur ownership and verification of independent mechanisms. |

## Risks

| Risk | Mitigation |
| --- | --- |
| A long-lived read transaction pins WAL and delays maintenance. | Keep the transaction within one helper call; close on every exit and test bounded lifetime. |
| New cleanup masks the original exception or closes a borrowed connection. | Close only owned stores in `finally`; preserve the original failure and explicit ownership contract. |
| More explicit diagnostic states change response consumers. | Inspect paired producers/consumers and test missing, in-flight and runtime-failure cases separately. |
| Platform skips hide relevant coverage. | Skip only unsupported real-symlink cases; keep ordinary and simulated reparse cases active and report native gaps. |

## Session Handoff

See `docs/agents/session-handoff.md`. Addition changes the admission/review boundary; prior dashboard-only readiness is historical and the expanded wave needs re-Prepare.

## Plan Review

2026-09-11: Requirements, AC and Scope were checked against the brief and current code. `read_published_graph_snapshot` opens one connection but has no `BEGIN`; `_read_pinned` already provides the local read-transaction pattern. Full/changed and idle build stores have separate lifetimes, so both require explicit cleanup coverage. `GraphSnapshot` currently lacks failure fields and its reader catches all exceptions; carry causes through paired consumers without treating missing or in-flight content as runtime failure. Dashboard C2 overlap remains serialized. Native qualification is release follow-through, not a claim made by local fault injection. No operator decision remains; the requested repairs preserve the approved storage and process-identity architecture.
