# Keep questions available with an incomplete index

Change ID: `213yb-enh incomplete-index-question-answering`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-19
Wave: 215sy incomplete-index-question-answering

## Rationale

Three live Code Ask smoke questions returned `index_not_ready` during a background refresh. After the build lock was released, the epoch remained interrupted and a retry was still refused. The operator wants to query data already available in the SQLite vector database and receive a notice that the index needs updating, without snapshots or extra copies.

The current loader requires a complete epoch before opening vector layers (`wf_server/server_impl.Index._ensure_loaded`, around line 1777). `index_state_store.begin_build_epoch` marks the existing store building, in its own transaction, before the build's first mutation. Publication itself is one `BEGIN IMMEDIATE` transaction (vectors, text, FTS, graph, bookkeeping) and `finalize_build_epoch` is a later separate transaction, so a building or interrupted store holds either the previous generation's rows intact or, after a crash between the publication commit and finalize, the complete new rows; half-written rows never exist. Stale (complete but out-of-date) data is already served today with a freshness annotation; this change is about `building` and interrupted epochs.

## Product Intent

Agents and operators can continue asking codebase questions during stale, running or interrupted indexing, using the existing SQLite index and cited available matches. Each degraded response makes clear that coverage may be incomplete and the index needs updating. Availability does not establish current source coverage or qualify an unfinished build. AC-1 and AC-2 together establish this intent.

## Requirements

1. Permit `code_ask`, `code_search` and `docs_search` to query compatible, readable data already present in the SQLite index when the build epoch is `building` (whether or not a build holds the lock) and freshness is unproven. `uninitialized` or absent state, schema mismatch and runtime-stale remain errors. Stale, building or interrupted status alone must not block useful matches. Use existing vectors when their model, dimension and row compatibility are established; preserve the existing lexical fallback where applicable. Never bypass storage or model compatibility checks merely because results are advisory.
2. Every such response, including zero matches, carries additive structured coverage information and a visible warning: the index needs updating, results may be incomplete or out of date, and current source must be verified before relying on them. Report the actual search mode and known build state. No matches in partial coverage is not proof of absence from the repository.
3. Keep text, coordinates, vector identities and coverage observations consistent within a read. Because the epoch state token does not change between the publication commit and finalize, a degraded read takes its dense, lexical and bookkeeping rows from one read-only connection inside one read transaction (one snapshot), or detects a commit during the read with `PRAGMA data_version` on that connection and retries or fails rather than combining generations. Reuse existing SQLite transaction facilities and validated serving paths; do not combine mismatched rows or reuse invalid cached handles through publication changes. A read transaction is not a copied or persistently retained index. Do not claim results represent the last completed build unless established.
4. Queries remain read-only. Do not mark epochs complete, repair storage, trigger rebuilds, weaken publication or lifecycle gates, or modify recovery state. Missing, unreadable, corrupt or incompatible storage remains an explicit error, never a successful empty search. A partial first build may answer when it has compatible readable rows; no usable rows remains unavailable.
5. No snapshots, copied databases, retained generations, alternate indexes or extra evidence files. Preserve healthy retrieval ranking, filters and citations. Index health, strict evaluation and publication continue to report actual readiness; successful partial Q&A does not make the index ready.
6. Document the degraded read contract in the MCP spec and indexing architecture, and test the registered tools rather than only internal helpers.

## Scope

**Problem statement:** Read-only Q&A is unnecessarily coupled to whole-build completion.

**In scope:** Shared search and Code Ask gates, safe reads of available SQLite vector/text rows, honest coverage diagnostics, focused regressions and contract documentation.

**Out of scope:** Repairing the observed interrupted build, graph tool redesign, filesystem-wide fallback scans, new storage layouts, model changes, automatic rebuilds, lifecycle gate changes and timing thresholds.

**Platform behaviour:** the same on Windows, macOS, Linux and WSL2. Reads use the existing SQLite read transactions and contained file access; on Windows a concurrent writer's file locks are handled by SQLite's WAL reader semantics exactly as on the other platforms, and no new file is opened or copied.

## Acceptance Criteria

- [x] AC-1: Registered Code Ask and search return expected cited matches from compatible available rows while indexing is stale, building or interrupted, including a partial first build. After completion they use the existing healthy path.
- [x] AC-2: Every degraded response reports incomplete/outdated coverage, the need to update and its actual search mode. Empty results do not imply complete repository coverage. Healthy responses do not gain a false warning.
- [x] AC-3: Publication-transition controls show no mismatched vector/text/citation rows or invalid cache reuse. Missing, unreadable, corrupt and incompatible storage stay distinguishable from partial success, and queries perform no index writes, recovery or file copies.
- [x] AC-4: The change's own tests pass, existing healthy retrieval filters and citations remain covered, and edited documentation describes observed behavior. No unrelated failure is attributable to this change.

## Tasks

- [x] Trace shared epoch gates, vector/text compatibility, caches and existing fallback invariants; choose the smallest common read-only path.
- [x] Implement reads of available compatible data and coverage warnings without changing writer authority.
- [x] Verify registered-path state, error and publication-transition cases plus healthy compatibility.
- [x] Update MCP spec, indexing architecture and changelog; consolidate verification and review outcomes in wave.md.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Implementation | implementer | Readiness | Source, tests and documentation writes. |
| Review | code, QA, architecture reviewers | Implementation | Read-only judgment of availability, honesty and consistency. |

## Serialization Points

- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/wf_server/index_handlers.py`
- `.wavefoundry/framework/scripts/index_state_store.py`
- `.wavefoundry/framework/scripts/sqlite_vector_store.py`
- `.wavefoundry/framework/scripts/tests/`
- `docs/specs/mcp-tool-surface.md`
- `docs/architecture/chunking-and-indexing-pipeline.md`

The root changelog is an intended documentation edit. Build publication, upgrade recovery, lifecycle authority, provisioning and generated host surfaces are protected from behavioral changes. Review lanes are read-only; source writes begin only after readiness.

## Affected Architecture Docs

Update `docs/architecture/chunking-and-indexing-pipeline.md` for advisory partial retrieval versus completed publication, and `docs/specs/mcp-tool-surface.md` for coverage diagnostics.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Preserve Q&A availability. |
| AC-2 | required | Make partial coverage unmistakable. |
| AC-3 | required | Preserve consistency and storage safety. |
| AC-4 | required | Verify this contract without healthy-path regressions. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-19 | Planned from live smoke refusals and current source; operator confirmed existing SQLite data only, no snapshots or extra copies. No code or index repair performed. | Registered Code Ask, index build status, loader, epoch and FTS source inspection. |
| 2026-10-19 | Readiness red-team primer, blocker: dense and FTS reads use separate connections and the epoch state token is unchanged between publication commit and finalize, so once `building` is served a query straddling the commit could combine old dense hits with new text undetected. Repaired before any approval: requirement 3 requires one read snapshot (or a `data_version` check) for degraded reads; requirement 1 names the served state set; rationale corrected (publication is one transaction, so no half-written rows; stale data is already served; path is `wf_server/server_impl.py`). | Red-team primer report; receipt `review-policy-dad41ad748ff094888d3` superseded. |
| 2026-10-19 | Implemented: a `building` epoch is served by `code_ask`, `code_search` and `docs_search` from one read-only connection in one read transaction (`sqlite_vector_store.read_snapshot`; `_open`, `open_read_only` and read-only `IndexStateStore` join it; the context variable lives in `sqlite_runtime` because the server loads a second copy of the store modules). Inside it the state token also carries `build_layer_state` rows, so loaded index, FTS verdict, language and freshness caches turn over at the publication commit. Partial layers must prove recorded model identity; no usable rows refuses (docs live walk); heal scheduling suppressed; `index_coverage` plus `index_coverage_incomplete` on every partial response. Docs updated; CHANGELOG left to coordinator. Gapfill: some source reading by shell for speed after MCP loading. | New `tests/test_partial_index_question_answering.py` (13, real interrupted producer, FastMCP `call_tool`); updated contract tests in `test_sqlite_serving.py`, `test_server_tools_lifecycle.py`. Focused 31 files, 4043 tests OK. Scratch mutants M1, M1b, M2-M7 all killed. `wf_validate_docs` passed. |
| 2026-10-19 | Delivery repair RT-DEL-1 (test only, no product change): added `test_publication_between_two_dense_reads_is_not_combined`. A real producer thread commits its publication after the first `dense_rows` read (docs) of one degraded `code_ask` and before its later code dense read; the later read and the citations must not contain the new file, and the next call must. | Scratch mutants: removing the snapshot join from `sqlite_vector_store._open` now fails the new test (later code dense read saw `src/fresh.ts`); removing it from `index_state_store.open_read_only` still fails both straddle tests. `--file` run of the new file, `test_sqlite_serving.py` and `test_server_tools_lifecycle.py`: 703 tests OK. |
| 2026-10-19 | Delivery review: code-reviewer, architecture-reviewer, docs-contract-reviewer and qa-reviewer approved; red-team and security seats passed. RT-DEL-1 (red-team: AC-3 evidence covered only the lexical side) repaired test-only with `test_publication_between_two_dense_reads_is_not_combined` and reverified by qa-reviewer; council-delivery recorded. CHANGELOG bullet added by the coordinator. Review outcomes are carried by the ledger projection in wave.md. | Typed ledger `events.jsonl`. |
| 2026-10-19 | Full-suite repair SUITE-DEL-1: the first full run failed only `test_mcp_tool_registry.HandlerDigestTests` because the pinned handler digests for `code_ask`, `code_search` and `docs_search` were not refreshed after their intended edits. Only those three hashes were replaced in `tests/fixtures/register-surface-handler-digests.json`, and the description records wave 215sy, as waves 1ypxw and 1z8tz did. | Full-suite log `scratchpad/suite-three-waves.txt`. |
| 2026-10-19 | Additional read-only review found no implementation blocker. Canonical partial-index file: 14 tests OK; independent dense-join negative control detected mixed-generation reads. Close dry-runs prove the current 11,975-test receipt; specialist and council approvals are current, operator signoff remains missing. Corrected obsolete blanket search-refusal wording in the build guide and search architecture, plus this stale planned-only handoff; documentation-only corrections, no source change or suite repetition. | Additional focused review, live Code Ask success after restart, and canonical review/close dry-run responses. |
| 2026-10-19 | The status line in the closing section was restored to its readiness text so the review-policy receipt matches the reviewed digest; current status lives in this log: implemented, delivery-reviewed, framework test receipt proven, operator approved closure on 2026-10-19. | Coordinator. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-19 | Query compatible available SQLite data with explicit incomplete coverage. | Meets the operator's availability and no-copy requirements without claiming readiness. | Blanket refusal blocks useful questions. Retained database copies add unwanted storage mechanisms. Unconditionally ignoring every check permits incompatible data and misleading results. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Build-wide guards currently protect several consistency assumptions. | Separate freshness from row/connection compatibility; exercise publication transitions before delivery. |
| Partial zero matches look conclusive. | Include coverage warning on every degraded response. |
| Available vectors cannot establish source freshness. | Retain citations, warn about outdated data and verify current source independently. |

## Session Handoff

Planned only. Readiness and implementation are pending. No review approval or completed-build claim is inferred.
