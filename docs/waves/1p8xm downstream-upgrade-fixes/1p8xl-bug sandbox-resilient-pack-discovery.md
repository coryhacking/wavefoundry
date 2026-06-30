# Sandbox-resilient pack discovery — a permission-denied search location must not abort the upgrade

Change ID: `1p8xl-bug sandbox-resilient-pack-discovery`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-29
Wave: `1p8xm downstream-upgrade-fixes`

## Rationale

The upgrade pack-discovery preflight scans candidate locations for `wavefoundry-*.zip` packs — repo root, `~/`, `~/.wavefoundry/`, `~/.wavefoundry/dist/`, and `~/Downloads/`. On macOS, `~/Downloads` is protected by TCC: the directory exists (so `Path.is_dir()` passes) but `iterdir()` raises `PermissionError` (EPERM) when the host app lacks Files-and-Folders/Full-Disk access. That exception propagates out of `_find_latest_release_zip` (`upgrade_wavefoundry.py:244-265`) and its sibling `_print_all_release_zips` (`:300-318`), **aborting the entire `wave_upgrade`** — confirmed in the field (teton, running the upgrade through the MCP tool, crashed deterministically on the `~/Downloads` scan).

A single inaccessible search location should never stop the upgrade: the scanner should **log that it couldn't look there, skip it, and continue** with the best pack from the accessible locations — and the skipped locations should be **surfaced to the operator** (in the `wave_upgrade` summary) so they can acknowledge and, if a newer pack lives there, grant access and re-run.

## Requirements

1. **Per-location resilience.** In `_find_latest_release_zip` and `_print_all_release_zips`, wrap each candidate-directory scan (`is_dir()` + `iterdir()`) in `try/except OSError` (covers `PermissionError`/EPERM and other sandbox/IO failures). On failure: `_log` a clear, single-line warning naming the location and the implication ("couldn't scan `<dir>` for packs — permission denied / sandboxed; skipping. If a newer pack is there, grant the host access and re-run."), record the location, and `continue` to the next directory. The scan returns the best pack from the accessible locations.
2. **Surface skipped locations.** Collect the skipped locations and surface them so the operator can acknowledge: thread them into the `wave_upgrade` summary as a `skipped_scan_locations` field (alongside the other `summary.*` fields), and mention them in the human-readable operator summary. The agent presents them; the operator proceeds after acknowledgment (or grants access and re-runs).
3. **No behavior change when all locations are accessible.** When every search dir reads cleanly, discovery is identical to today (no extra warnings, empty `skipped_scan_locations`).
4. **Don't widen the catch.** Only directory-scan IO errors are swallowed-and-logged; a genuine programming error elsewhere is not masked. The per-entry `stat()` already tolerates `OSError`; this adds the per-directory guard.

## Scope

**Problem statement:** a TCC/sandbox `PermissionError` on one pack-search location (`~/Downloads`) aborts the whole upgrade instead of being skipped-and-logged.

**In scope:**

- `upgrade_wavefoundry.py`: per-directory `try/except OSError` + `_log` + collect skipped locations in `_find_latest_release_zip` / `_print_all_release_zips`; expose the skipped set to callers.
- `server_impl.py` (+ the upgrade summary builder): add `skipped_scan_locations` to the `wave_upgrade` summary and the human prose.
- `test_upgrade_wavefoundry.py`: coverage for the skip-and-continue + the surfaced field.

**Out of scope:**

- The TCC permission itself (operator grants it; not something the framework can change).
- Changing the set of search locations or their priority order.
- `build_pack`'s own `dist/` scan (operator-owned dir; not the reported failure).

## Acceptance Criteria

- [x] AC-1: when a search directory's `iterdir()` raises `PermissionError`, discovery does NOT raise — it logs a warning, skips that directory, and still returns the best pack found in the accessible locations. (`_scan_dir_entries`; `test_find_latest_release_zip_resilient_to_unreadable_location`)
- [x] AC-2: the skipped location(s) are collected (`_PACK_SCAN_SKIPPED`) and surfaced in the `wave_upgrade` summary as `skipped_scan_locations` (and in the human prose). (`test_summary_surfaces_skipped_scan_locations`; `_print_operator_summary` callout)
- [x] AC-3: when all locations are accessible, behavior is unchanged — no warning, `skipped_scan_locations` empty, same selected pack. (`test_scan_dir_entries_lists_readable_dir`, `test_summary_skipped_empty_when_all_readable`)
- [x] AC-4: `_print_all_release_zips` (the `--list-zips` path) is equally resilient — a sandboxed location is skipped, not fatal. (`test_print_all_release_zips_resilient_to_unreadable_location`)
- [x] AC-5: the full framework suite + docs-lint stay green. (suite 3702 ok; docs-lint ok)
- [~] AC-6 (field validation): the reporting operator confirms `wave_upgrade` completes on a macOS host where `~/Downloads` is TCC-sandboxed, surfacing the skipped location instead of crashing. *macOS-TCC not reproducible in CI — awaits operator validation of the build; the mechanism is unit-locked via a patched `iterdir` raising `PermissionError`.*

## Tasks

- [x] Add the per-directory `try/except OSError` + `_log` + skipped-location collection to `_find_latest_release_zip` and `_print_all_release_zips` (via the shared `_scan_dir_entries` helper + `_record_skipped_scan_location`) (under `framework_edit_allowed`).
- [x] Expose the skipped set and thread it into the `wave_upgrade` `summary.skipped_scan_locations` + human prose. **Note:** `server_impl` needed NO edit — the summary dict is JSON-dumped to the sentinel and `wave_upgrade_response` parses the whole dict into `data.summary`, so the new field flows through automatically.
- [x] Add `test_upgrade_wavefoundry.py` cases for AC-1..4. (6 in `SandboxResilientPackDiscoveryTests`)
- [x] Run the framework suite + docs-lint; confirm green. (suite 3702 ok; docs-lint ok)
- [~] Hand the build to the operator for AC-6 validation. *Pending a build/release.*

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| per-dir resilience + skipped collection | implementer | — | `framework_edit_allowed`; `upgrade_wavefoundry.py` |
| summary surfacing (`skipped_scan_locations`) | implementer | resilience | `server_impl.py` summary builder |
| tests + suite/docs-lint | qa-reviewer | both | AC-1..5 |

## Serialization Points

- The discovery helper returns the skipped set that the summary builder consumes — land the helper change before/with the summary plumbing.

## Affected Architecture Docs

`N/A` — IO-resilience + one new summary field in the existing upgrade flow; no boundary/flow/verification-architecture change.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The core fix — a sandboxed location can't abort the upgrade. |
| AC-2 | required | Operator must see the skipped location to acknowledge. |
| AC-3 | required | No regression when all locations are readable. |
| AC-4 | required | The `--list-zips` path is equally resilient. |
| AC-5 | required | Suite + docs-lint green. |
| AC-6 | important | Real-world macOS-TCC confirmation; post-build. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-29 | Drafted from a teton field report: `wave_upgrade` crashed deterministically on the `~/Downloads` scan (macOS TCC `PermissionError` from `iterdir()`). Root cause: no per-directory guard in the two pack scanners. | `upgrade_wavefoundry.py:244-265,300-318`; `_log` at `:147`. |
| 2026-06-29 | Implemented. Added `_scan_dir_entries` (guarded `is_dir()`+`iterdir()` → `None` on `OSError`, logs + records the skip) + `_record_skipped_scan_location` + module-level `_PACK_SCAN_SKIPPED`; both scanners use it (the finder clears the accumulator at start). Added `skipped_scan_locations` to `_build_upgrade_summary` + a callout in `_print_operator_summary`. server_impl unchanged (sentinel passthrough). AC-1..5 met; AC-6 `[~]`. | `upgrade_wavefoundry.py` diff; 6 `SandboxResilientPackDiscoveryTests`; suite 3702 ok; docs-lint ok. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-29 | Skip-and-log per location + surface skipped locations in the summary (not a hard pause). | The discovery helper can't sanely block for input; surfacing the skip in the summary lets the agent present it and the operator acknowledge. | Drop `~/Downloads` from the search set (rejected — it's a common pack-drop location); hard-fail with a friendlier message (rejected — still aborts the upgrade). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Swallowing too broad an exception masks a real bug. | Catch only `OSError` around the directory scan; the rest of the function is unguarded; per-entry `stat` guard is unchanged. |
| Operator misses the skip and assumes all locations were checked. | Surface `skipped_scan_locations` in the summary + human prose (AC-2) so the agent presents it for acknowledgment. |
| macOS-TCC can't be reproduced in CI. | Unit-test the mechanism with a patched `iterdir` raising `PermissionError`; gate the real-world AC-6 on operator validation. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
