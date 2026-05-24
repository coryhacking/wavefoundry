# Project Index Health Check Falsely Flags Framework Paths As Stale

Change ID: `12shs-bug project-index-health-flags-framework-paths-stale`
Change Status: `planned`
Owner: wave-coordinator
Status: planned
Last verified: 2026-05-21
Wave: TBD

## Rationale

After a full project-layer index rebuild, `wave_audit` and the index health check consistently report 86 `.wavefoundry/framework/` paths as stale with `removed_paths_count: 86`. These files are intentionally excluded from the project index scope — they belong to the framework layer, which indexes them correctly and reports `stale_paths_count: 0`.

The health check should not flag framework-excluded paths as stale. Because it does, `semantic_ready` stays `false` and `readiness_overview` stays `needs_update` permanently, even when both layers have been fully rebuilt and are functionally current. This makes the audit readiness signal unreliable and causes unnecessary `wave_index_build` recovery suggestions on every `wave_audit` call.

## Requirements

1. The project-layer health check must not report paths that are excluded from the project index scope as stale or removed.
2. After a successful full project-layer rebuild, `wave_audit` must not surface a `index_not_ready` diagnostic for paths that are correctly handled by the framework layer.
3. The fix must not change which files each layer indexes — the project/framework layer boundary must remain intact.
4. `semantic_ready` must reflect `true` when both layers have been rebuilt and contain no genuinely stale content.

## Scope

**Problem statement:** The project index health check compares indexed paths against the filesystem and flags `.wavefoundry/framework/` files as "removed" because the project indexer skips them. A full rebuild does not resolve this because the health check counts framework-scoped exclusions as staleness rather than correctly-excluded paths.

**In scope:**

- Fix the project-layer health check / stale-path detection logic so excluded-scope paths are not reported as stale
- Ensure `wave_audit` and `wave_index_health` correctly derive `semantic_ready` and `readiness_overview` when both layers are current

**Out of scope:**

- Changing which files belong to the project vs. framework index layer
- Changing the framework layer's own health check behavior (it is already correct)

## Acceptance Criteria

- AC-1: After a full project-layer rebuild, `wave_audit` reports `stale_paths_count: 0` for the project layer (no `.wavefoundry/framework/` paths appear as stale).
- AC-2: `semantic_ready` is `true` after both layers are rebuilt with no genuinely stale content.
- AC-3: The `index_not_ready` diagnostic is not surfaced when the only "stale" paths are framework-excluded files.
- AC-4: The framework layer continues to index `.wavefoundry/framework/` files correctly and is unaffected by this fix.

## Tasks

- [ ] Investigate where stale-path detection occurs in the project-layer health check (likely `setup_index.py` or `indexer.py`)
- [ ] Determine whether excluded-scope paths are written into the hash manifest or compared against it during health check
- [ ] Fix the health check so framework-scoped paths are treated as out-of-scope rather than removed
- [ ] Update or add a test asserting that excluded-scope paths do not appear in stale path counts
- [ ] Verify `wave_audit` reports clean after rebuild with the fix applied

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| root-cause | implementer | — | Trace stale-path detection in indexer/setup_index |
| fix | implementer | root-cause | Correct health check exclusion logic |
| test | qa-reviewer | fix | Add/update test coverage |

## Serialization Points

- Root-cause investigation must complete before the fix, since the exact location of the exclusion logic is unknown.

## Affected Architecture Docs

N/A — confined to the indexer health check; no boundary, flow, or verification architecture is affected.

## AC Priority

(Populated at Prepare wave.)

| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | Core correctness: stale count must be 0 after a clean rebuild |
| AC-2 | required | `semantic_ready` false permanently undermines audit signal |
| AC-3 | required | Spurious recovery suggestions erode operator trust in audit output |
| AC-4 | required | Must not regress framework-layer indexing |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-21 | Observed during pre-implementation index rebuild for wave 12sg7: 86 `.wavefoundry/framework/` paths reported stale after full rebuild; framework layer clean. | `wave_audit` output in session |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-05-21 | Track as bug, not maintenance | Health check gives incorrect signal; this is broken behavior, not routine upkeep | Track as tech debt |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Fix accidentally narrows stale detection and masks real staleness | Keep the fix scoped to paths that match the framework-exclusion pattern; do not suppress stale detection broadly |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.