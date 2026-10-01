# Caches of the Retired arctic-embed-xs Model Are Never Removed

Change ID: `1zico-bug retire-arctic-xs-caches`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-09-30
Wave: 1zilw validation-correctness-fixes

## Rationale

`Snowflake/snowflake-arctic-embed-xs` was the docs embedding model from v1.6.0 through v1.15.4 and was retired by model set 2 in v1.16.0 (commit `a8995441`). It populated four caches: `~/.wavefoundry/cache/fastembed/models--snowflake--snowflake-arctic-embed-xs`, `cache/onnx-src/models--Snowflake--snowflake-arctic-embed-xs`, `cache/onnx/Snowflake__snowflake-arctic-embed-xs` and `cache/coreml/Snowflake__snowflake-arctic-embed-xs` (190 MB of CoreML compiles alone on this Mac; all four exist here). The upgrade's retired-model cleanup (`upgrade_wavefoundry._RETIRED_MODEL_ALLOWLIST`, used by `_run_retired_model_cleanup`) lists only the BAAI models, so these are never removed. Flagged in wave `1zf1w` and by a field report.

## Requirements

1. **Allowlist the four xs caches.** Add `models--snowflake--snowflake-arctic-embed-xs` (fastembed), `models--Snowflake--snowflake-arctic-embed-xs` (clean-onnx), and `Snowflake__snowflake-arctic-embed-xs` (static-onnx and coreml) to `_RETIRED_MODEL_ALLOWLIST`. The existing gates still decide whether cleanup runs (eligible version, verified active model authority that refuses if any listed name is active, matching index epoch) and how a component is removed (flat name, no link ancestry, contained removal).
2. **Custom roots keep their ownership rule.** A custom-scope cache (fastembed and clean-onnx kinds) still requires the v1 model-bundle marker. xs was a model set 1 component (docs fastembed and clean-onnx), so a marked custom xs copy is owned and removed; an unmarked one is reported `unowned` and kept.
3. **Supersedes the 1v0qz scope clause.** Wave `1v0r0` (`1v0qz` Requirement 7) left the xs cache out of the operator-requested retired-supplier cleanup and limited the cleanup's retired identifiers to BAAI; that was a scope boundary for the supplier request. The operator has now asked for the xs leftover to be removed. `tests/test_model_bundle.py` `test_retired_model_residue_census_is_closed` is amended to allow exactly the xs allowlist identifiers in `upgrade_wavefoundry.py` and nothing else; the census otherwise stays closed.
4. **Platforms.** Windows, macOS, Linux and WSL2 behave the same; removal reuses the existing link-safe removal.
5. **Transition.** Removed by the next eligible upgrade's cleanup. The model cache is shared per user, so a sibling repository still on 1.6 to 1.15 re-downloads xs if it needs it (the same tradeoff `1v0r0` accepted for BAAI); the CHANGELOG line says so. CHANGELOG under `### Fixed` in `## [Unreleased]`.

## Scope

**Problem statement:** four caches of a model retired in v1.16.0 are never cleaned up.

**In scope:**

- `upgrade_wavefoundry._RETIRED_MODEL_ALLOWLIST`; tests that iterate or enumerate it (`test_default_target_enumeration_is_the_exact_allowlist`); the retired-model residue census; CHANGELOG.

**Out of scope:**

- Changing the custom-scope ownership marker.

## Acceptance Criteria

- [x] AC-1: the allowlist names the four xs components under their cache kinds, and the retired-model cleanup removes them from default caches when its existing gates pass, reporting them like the BAAI components.
- [x] AC-2: the active-authority guard still refuses cleanup if any listed name is an active model directory; a custom-scope xs copy with the v1 marker is removed and one without it is reported `unowned`.
- [x] AC-3: the change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Allowlist entries.
- [x] Tests (including the exact-allowlist enumeration and the residue census).
- [x] CHANGELOG.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Allowlist | implementer | readiness | |
| Review | code-reviewer, qa-reviewer | implementation | |

## Serialization Points

- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`, `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py`, `.wavefoundry/framework/scripts/tests/test_model_bundle.py`

## Affected Architecture Docs

N/A: data entries in an existing cleanup.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The leftover caches |
| AC-2 | required | Existing safety gates hold |
| AC-3 | required | Standard verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-30 | Delivery review: red-team and the four lanes (code, qa, release, security) approved, every mutation killed by the suite. Advisory taken: the code and test comments cited wave 1zicq instead of 1zilw (corrected). Not taken: a boundary test pinning the 2 s pid-reuse tolerance (pre-existing gap from 1zc7n, out of scope; follow-up); the shared custom-marker fixture uses symlinks, which can error on Windows without symlink privilege (pre-existing exposure shared with `test_custom_marker_requires_exact_legacy_inventory`). Full suite: 10200 tests OK | Full suite; delivery review |
| 2026-09-30 | Implemented. Four xs entries in `_RETIRED_MODEL_ALLOWLIST` (fastembed, clean-onnx, static-onnx, coreml). Tests: the exact-allowlist enumeration now pins 17 default and 7 custom-scope ids (xs adds two custom); the residue census allows exactly the three distinct xs constants and still requires every production hit to be an allowlisted constant; new `test_arctic_xs_components_follow_the_existing_ownership_and_veto_rules` (default removal, marked custom removed, unmarked custom unowned and kept, active-authority veto for each kind). `test_upgrade_wavefoundry.py` and `test_model_bundle.py` 592 OK | Focused run |
| 2026-09-30 | Readiness round 1: code-reviewer and qa-reviewer blocked because `test_retired_model_residue_census_is_closed` forbids xs in the cleanup source (a recorded `1v0qz` decision); red-team noted marked custom xs copies are owned. Repaired: census amendment and supersession recorded, custom ownership restated, enumeration test and shared-cache tradeoff added | Prepare council and lane review |
| 2026-09-30 | Planned, verified: xs was `DOCS_MODEL` from v1.6.0 to v1.15.4 (read at every tag) and retired by `a8995441` (v1.16.0); the four cache directory names exist on this machine; `_RETIRED_MODEL_ALLOWLIST` lists only BAAI components; cleanup gates and link-safe removal are unchanged | git history; cache listing; code reads |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-30 | Keep the custom-scope ownership rule unchanged | The v1 marker already proves ownership of set-1 components, which include xs | Default scope only; extend the marker check |
| 2026-09-30 | Supersede `1v0qz` Requirement 7's xs exclusion and BAAI-only cleanup census | It bounded the supplier-compliance request; the operator now asks for xs removal | Leave xs caches in place |

## Risks

| Risk | Mitigation |
| --- | --- |
| An operator re-adopted xs manually | The active-authority guard refuses cleanup while xs is an active model directory |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
