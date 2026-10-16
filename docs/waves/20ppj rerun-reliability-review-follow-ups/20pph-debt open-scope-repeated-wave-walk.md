# Single-OPEN guard re-walks the waves tree once per open wave

Change ID: `20pph-debt open-scope-repeated-wave-walk`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-10-15
Wave: `20ppj rerun-reliability-review-follow-ups`

## Rationale

`_find_other_active_wave` in `wf_server/server_impl.py` calls `record_paths.open_container_scope` for the target wave and again for every open wave it compares against. In parent scope (`OPEN_CONTAINER_SCOPE='parent'`) with the nested record layout, each call re-runs `load_record_roots` and `discover_wave_dirs`, a bounded `MAX_DEPTH` walk of the waves tree. Every `wf_implement_wave`, `wf_reopen_wave` and `wf_prepare_wave` therefore repeats the walk once per open wave. The guard already has the wave list in hand from `list_waves_cached`.

## Requirements

1. The waves tree is discovered at most once per `_find_other_active_wave` call. Either the discovered directories are passed into a scope resolver that accepts them, or the resolver exposes a variant that takes the pre-discovered list.
2. The guard's answer is unchanged for flat layouts, nested layouts, repository scope and parent scope.
3. Windows, macOS, Linux and WSL2: path comparison keeps the existing `resolve()`-based equality; no platform-specific change.

## Scope

**Problem statement:** redundant tree walks inside the single-OPEN guard.

**In scope:**

- `_find_other_active_wave` in `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `open_container_scope` in `.wavefoundry/framework/scripts/record_paths.py`, only to accept a pre-discovered list
- A regression counting discovery calls

**Out of scope:**

- Changing scope semantics or the single-OPEN policy

## Acceptance Criteria

- [x] AC-1: With a nested layout, parent scope and several open waves across parents, a counter on `discover_wave_dirs` (or an equivalent oracle) shows one discovery per `_find_other_active_wave` call.
- [x] AC-2: The existing single-OPEN guard tests pass unchanged for flat and nested layouts in both scopes.
- [x] AC-3: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Add the AC-1 oracle as a failing test.
- [x] Thread the discovered directories through the scope lookup.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Fix and test | Implementer | Readiness | Single write owner |
| Delivery review | QA | Fix and test | Read-only |

## Serialization Points

- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/record_paths.py`
- `.wavefoundry/framework/scripts/tests/`

## Affected Architecture Docs

N/A. Internal call shape inside the guard; the single-OPEN policy and its description are unchanged.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | important | The redundancy |
| AC-2 | required | Semantics must not move |
| AC-3 | required | Delivery gate |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-15 | Planned from the code review of `43621e07` | Review finding 7 |

| 2026-10-15 | Readback: pass one discovered wave-directory list into optional scope lookup; preserve canonical parent/repository guard answers. AC-1/2; server_impl, record_paths and discovery-count regression. Before: N extra discoveries; after: one per uncached/cached guard call. | Admitted plan and current-source MCP reads |

| 2026-10-15 | Focused controls passed: root follow-ups, rerun, retained docs-gate retry, scope and container-status controls: 44 tests / 0 skips. In-memory mutants restored the unbound import, repeated discovery and missing extraction guard; each targeted test detected its defect. Final combined qualification remains pending. | test_rerun_followups; test_upgrade_rerun_reliability; ResumeAfterGateTests; OpenContainerScopeTests; ContainerStatusContractTests |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-15 | Pass the discovered list into the scope resolver | Smallest change that removes the repeat; keeps one resolver | (a) Memoize discovery inside `record_paths` per call: hidden cache with invalidation questions. (b) Cache scope per wave in `McpRepoCache`: wider blast radius for a bounded walk. |

## Risks

| Risk | Mitigation |
| --- | --- |
| A resolver signature change breaks another caller | Add a keyword-only optional parameter; existing callers are unaffected |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
