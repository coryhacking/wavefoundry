# Bound `wf_audit` Index Readiness on Windows

Change ID: `1t59o-bug wf-audit-bounded-index-health`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-07-21
Wave: `1t59p wf-audit-bounded-index-health`

## Rationale

`wf_audit` is commonly the first MCP call in a session. Its index-health leg currently calls `WaveIndex.docs_health()`, which synchronously opens LanceDB tables and hashes every indexed file. Neither operation has a deadline. On native Windows, cold native loading and Defender-mediated full-corpus reads can make that first response appear hung.

The current runner already isolates native fd-1 writes before MCP transport starts, so stdout corruption is protected in a restarted current server. This change addresses the remaining true-latency path: an audit must not perform the native table open or full freshness hash synchronously.

## Requirements

1. **Fast audit index snapshot:** `wf_audit` obtains index readiness only from bounded metadata/file-state reads: completed build epoch, expected index-table directories, and configured code-layer presence. It must not call `WaveIndex.docs_health()`, `_ensure_loaded()`, LanceDB import/connect/open-table, or `_layer_current_hashes()`.
2. **Honest freshness contract:** the audit index payload explicitly says that full freshness was not scanned (for example `freshness_checked: false` / `freshness: unknown`). `wf_audit` must not claim an index is current merely from the metadata snapshot; its top-level readiness semantics and diagnostics must make that distinction explicit.
3. **Keep deep verification available:** explicit `index_health` retains its complete full-hash freshness behavior. No index rebuild, model/embedder/reranker load, or new background task is introduced by `wf_audit`.
4. **Windows-safe latency proof:** tests demonstrate that the audit path succeeds against a ready metadata fixture while spying/patching the native load and full-hash helpers to fail if called. A regression test also proves stale/unknown snapshot state is surfaced honestly rather than reported as current/ready.
5. **Contract documentation:** update the MCP tool-surface and any operator-facing `wf_audit` guidance to distinguish its fast readiness snapshot from explicit full `index_health` freshness verification.

## Scope

**Problem statement:** `wf_audit` combines a bounded docs-lint subprocess with an unbounded native-load/full-hash index-health leg, so native Windows users can perceive a first-call hang with no incremental response.

**In scope:**

- `wf_audit_response`, `WaveIndex` health/readiness helpers, and focused tests
- MCP tool-surface and operator guidance for the revised audit/index-health distinction
- Native-Windows test seams where they exercise the no-native-load/no-full-hash contract

**Out of scope:**

- Process-wide stdout isolation; the current `server.py` startup runner already owns that protection
- Changing the full-corpus docs-lint timeout or reducing docs-lint scope
- Reworking LanceDB, SQLite, embeddings, reranking, index-build, or `index_health` full verification
- Adding telemetry, background work, or a new audit tool

## Acceptance Criteria

- [x] AC-1: `wf_audit` completes its index leg without invoking native LanceDB loading or a repository-wide hash walk.
- [x] AC-2: its payload distinguishes metadata readiness from unverified freshness and cannot label an unknown/stale snapshot as current.
- [x] AC-3: `index_health` retains its full freshness scan and existing ready/stale behavior.
- [x] AC-4: focused tests cover a ready fast snapshot, stale/unknown truthfulness, and no-native-load/no-full-hash tripwires; Windows-safe branches are exercised where practical.
- [x] AC-5: tool-surface/operator docs describe the fast `wf_audit` snapshot versus explicit `index_health`; full suite and docs validation pass (6,093 tests across 59 files, OK, 2026-07-21; docs-lint ok).

## Tasks

- [x] Trace the minimum metadata required for readiness and define the audit payload/`ready` semantics before changing the handler. (Bounded primitives confirmed: `_store_has_completed_build`, `export_meta_snapshot`, Lance `is_dir`, config prefixes; `ready` gate switched to `metadata_ready`.)
- [x] Implement the metadata-only audit health helper; route `wf_audit` through it without altering `index_health`. (`_audit_index_snapshot` + `_audit_meta_snapshot`; `index_health_response` untouched.)
- [x] Add no-native-load/no-hash and truthfulness regression tests. (`WfAuditBoundedIndexSnapshotTests`, 7 tests: real-WaveIndex tripwires, source pin, ready/truthful/code-layer/chunker cases, `index_health` contrast; the source pin immediately caught a comment naming the forbidden seam, proving it non-vacuous.)
- [x] Update MCP/operator documentation; run docs validation and the full suite. (Spec `wf_audit` entry + tool-chooser two-surface rows; project-context-memory audit paragraph; search-architecture "Index Readiness: Two Surfaces" section. Suite 6,093 OK; docs-lint ok.)

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| contract + helper | implementer | — | Shared `server_impl.py` seam; define semantics first. |
| regression tests | qa-reviewer | contract + helper | Native-load and hash tripwires. |
| docs + integration | docs-contract-reviewer | contract + helper | Surface contract, docs gate, full suite. |

## Serialization Points

- The `server_impl.py` audit/index-health seam is serial: contract + helper lands before tests and documentation reconcile the final payload.

## Affected Architecture Docs

`docs/specs/mcp-tool-surface.md` and `docs/architecture/search-architecture.md`: `wf_audit` changes from a full index-freshness check to a fast metadata readiness snapshot, while `index_health` remains the explicit full verification surface.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Removes the reported unbounded audit path. |
| AC-2 | required | Prevents a fast path from silently overstating index health. |
| AC-3 | required | Preserves the existing deep verification contract. |
| AC-4 | required | Prevents regression to hidden native/full-scan work. |
| AC-5 | required | Public tool-contract and standard verification gate. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-07-21 | Created from native-Windows `wf_audit` hang investigation. Confirmed `wf_audit` calls `docs_health()`, which calls `_ensure_loaded()` (LanceDB import/connect/open) and `_layer_health()` (full indexed-file hash walk); docs-lint remains separately bounded. | `server_impl.py:9213`, `:738`, `:891`, `:660`, `:3430`. |
| 2026-07-21 | Implemented: `_audit_index_snapshot` + `_audit_meta_snapshot` (bounded control-plane reads: epoch, Lance dir presence, store meta incl. recorded-path code-prefix check preserving the 1p7is contract, chunker comparison); `wf_audit` routed through it with `ready` gating on `metadata_ready` and an `index_freshness_unverified` advisory on healthy responses; `index_health` untouched. 7 new tests incl. real-WaveIndex tripwires and a source pin; the pin caught its first violations on the first run (an explanatory comment naming the forbidden seam and the stale response-fn docstring), proving it non-vacuous. Live post-reload `wf_audit` served the snapshot (`metadata_ready: true`, `freshness: unknown`) instantly. | `WfAuditBoundedIndexSnapshotTests` (7); live wf_audit envelope 2026-07-21; suite 6,093 OK. |
| 2026-07-21 | Operator P1 (cycle 1, `audit-snapshot-full-meta-scan`): the first snapshot implementation read the store through the per-file exporter, materializing every per-file bookkeeping row (O(indexed files)) and contradicting the bounded objective. Repaired: `_audit_build_summary` now calls `read_build_summary` (layer scalars plus one COUNT); readiness derives from NO per-file metadata (chunker versions from layer scalars; `code_sources_in_scope` from configuration alone, the fail-closed 1p7is reading); the source pin extends over the helper region forbidding the exporter and per-file references, and it caught my own docstring naming the bookkeeping table before the reword (second live catch for this wave's pin). | `ev-audit-snapshot-full-meta-scan-2`; index_state_store.py:2481 vs :2533; strengthened `test_audit_source_has_no_native_or_hash_references`. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- |
| 2026-07-21 | Make `wf_audit` metadata-only for index readiness; retain full freshness in `index_health`. | The default first-session audit must be bounded and must not cold-load native storage or hash a whole repository. | Preserve current full scan with only a timeout; spawn full health in a subprocess. |
| 2026-07-21 | Surface unverified freshness explicitly rather than infer `current` from metadata. | Avoid trading a hang for a false-ready result. | Keep the old `semantic_ready` meaning without a freshness qualifier. |
| 2026-07-21 | Do not modify global stdout isolation. | Current `server.py` already duplicates protocol stdout and redirects native fd 1 before transport starts; only a full host restart applies runner updates. | Add another per-call redirect (unsafe with concurrent operations and redundant). |

## Risks

| Risk | Mitigation |
| --- | --- |
| Fast snapshot is mistaken for a freshness proof. | Separate fields/diagnostics and docs; stale/unknown regression test. |
| Audit and `index_health` semantics drift. | Keep full checker untouched and add focused contrast tests. |
| Narrow helper accidentally triggers LanceDB through an indirect import. | Tripwire patches native load and full-hash helpers during audit tests. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
