# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-06-29

wave-id: `1p8xm downstream-upgrade-fixes`
Title: Downstream Upgrade Fixes

## Objective

Two downstream-upgrade fixes surfaced by a teton 1.9.7 upgrade. `1p8xk`: strip the four wavefoundry-internal `1p8t4` ADR references that the stage-gate guard shipped into seeds (downstream repos lack the file → dangling reference). `1p8xl`: a TCC-sandboxed pack-search location (`~/Downloads`) must not abort the upgrade — skip-and-log it and surface the skipped locations in the `wave_upgrade` summary for operator acknowledgment.

## Changes

Change ID: `1p8xk-bug strip-internal-adr-refs-from-seeds`
Change Status: `implemented`

Change ID: `1p8xl-bug sandbox-resilient-pack-discovery`
Change Status: `implemented`

Completed At: 2026-06-29

## Wave Summary

Wave `1p8xm` (Downstream Upgrade Fixes) delivered two changes: Strip wavefoundry-internal ADR references from shipped seeds and Sandbox-resilient pack discovery — a permission-denied search location must not abort the upgrade. Notable adjustments during implementation: Sandbox-resilient pack discovery — a permission-denied search location must not abort the upgrade: Implemented. Added `_scan_dir_entries` (guarded `is_dir()`+`iterdir()` → `None` on `OSError`, logs + records the skip) + `_record_skipped_scan_location` + module-level `_PACK_SCAN_SKIPPED`; both scanners use it (the finder clears the accumulator at start). Added `skipped_scan_locations` to `_build_upgrade_summary` + a callout in `_print_operator_summary`. server_impl unchanged (sentinel passthrough). AC-1..5 met; AC-6 `[~]`.

**Changes delivered:**

- **Strip wavefoundry-internal ADR references from shipped seeds** (`1p8xk-bug strip-internal-adr-refs-from-seeds`) — 4 ACs completed. Key decisions: Strip the ADR pointers; keep the rationale inline.
- **Sandbox-resilient pack discovery — a permission-denied search location must not abort the upgrade** (`1p8xl-bug sandbox-resilient-pack-discovery`) — 5 ACs completed. Key decisions: Skip-and-log per location + surface skipped locations in the summary (not a hard pause).
## Journal Watchpoints

- `1p8xk` guard: `seed_edit_allowed` for the seed edits (050/160/009); strip ONLY the `1p8t4` pointers, leave the generic `docs/architecture/decisions/` (dir/template/README) references and all surrounding guidance intact.
- `1p8xl` guard: `framework_edit_allowed` for `upgrade_wavefoundry.py` + `server_impl.py`; catch only `OSError` around the directory scan (don't mask other errors); preserve the existing per-entry `stat()` guard.
- Watchpoint: `1p8xl` AC-6 (real macOS-TCC `~/Downloads` sandbox) is repro-gated — unit-test the mechanism via a patched `iterdir` raising `PermissionError`; operator validates the build (`[~]`).

## Review Evidence

- wave-council-readiness: approved 2026-06-29 — two cited downstream-upgrade fixes; `1p8xk` is four targeted seed-prose removals (no behavior change), `1p8xl` is a per-directory `OSError` guard in the two pack scanners + a `skipped_scan_locations` summary field. ACs unit-assertable except `1p8xl` AC-6 (macOS-TCC, `[~]`). Risks bounded (over-strip / over-broad-catch both mitigated). No dependencies.
- wave-council-delivery: approved 2026-06-29 — PASS, no blocking findings (both changes). **`1p8xk`**: `grep -r 1p8t4 seeds/` empty (all five occurrences removed); generic `decisions/` refs intact; stage-gate guidance unchanged in behavior; suite 3702 green. **`1p8xl`**: 6 tests prove skip-and-record (not fatal), pack still returned from accessible locations, `--list-zips` equally resilient, `skipped_scan_locations` surfaced (empty when all readable); the `except OSError` is scoped only to the directory scan (no masking; per-entry `stat` guard unchanged); surfacing rides the existing sentinel passthrough (no `server_impl` change); AC-6 `[~]` macOS-TCC-repro-gated. docs-lint ok.
- operator-signoff: pending operator confirmation at closure

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-06-29: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: stripping the ADR link from `1p8xk` could leave the carve-out rationale unmotivated for a future maintainer — bounded because each seed location states the WHY inline and the provenance belongs in the internal ADR/change doc (kept); for `1p8xl`, a too-broad `except` could mask a real bug — bounded by catching only `OSError` around the directory scan; strongest-alternative: ship the ADR downstream (rejected — it's a wavefoundry-internal record) / drop `~/Downloads` from the search set (rejected — common pack-drop location). Carried constraints: strip ONLY the `1p8t4` pointers (keep generic `decisions/` refs); catch ONLY `OSError` around the dir scan.)

## Dependencies

- No external wave dependencies.
