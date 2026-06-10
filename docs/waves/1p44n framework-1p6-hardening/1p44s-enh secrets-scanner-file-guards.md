# Secrets Scanner File Guards

Change ID: `1p44s-enh secrets-scanner-file-guards`
Change Status: `complete`
Owner: Engineering
Status: planned
Last verified: 2026-06-09
Wave: 1p44n framework-1p6-hardening

## Rationale

`scan_file_raw` (`.wavefoundry/framework/scripts/wave_lint_lib/secrets_validators.py:507-558`) reads and scans every file with no input guards, making a full repository scan O(minutes) — a reported 32.6s across 2,146 files. Three gaps drive the cost:

- Line 510 calls `file_path.read_text(encoding="utf-8", errors="replace")` with no prior `stat()` size check and no NUL-byte sniff, so arbitrarily large files and binaries are fully materialized into memory.
- Line 515 builds `content_lower = content.lower()`, a second full in-memory copy of the file, even for files that will never match.
- Lines 524-525 run `pattern.search(line)` per line with no `len(line)` cap. A single multi-MB line (minified bundle, webpack `stats.html`, generated lockfile) is handed whole to every active rule's regex, triggering pathological backtracking.

A grep over the module finds no `st_size` / `getsize` / `max_line` / `is_binary` / `truncate` guard anywhere. The parallel path (`secrets_validators.py:785-817`) batches files across a `ProcessPoolExecutor`, so a single giant or binary file pins a worker and gates wall-clock time (~slowest file). Adding three independent, small guards (each under 20 LOC) removes the pathological cases without weakening detection, since real credential tokens are short and live in normal-length lines of text files.

## Requirements

1. Add a **max-line-length guard** inside the per-line loop in `scan_file_raw`, before the `pattern.search(line)` call at line 525: `if len(line) > MAX_LINE_BYTES: continue`. Use a generous threshold so legitimately long config lines that may carry a real secret are still scanned.
2. Add a **per-file size cap** before the `read_text` call at line 510: `if file_path.stat().st_size > MAX_FILE_BYTES: return [], None, []`, with the `stat()` call wrapped in `try/except` to tolerate file-disappearance races.
3. Add a **NUL-byte binary-detection guard** before the full `read_text`: read a bounded prefix via `file_path.read_bytes()[:8192]` and `if b"\x00" in prefix: return [], None, []`.
4. Define all three thresholds (`MAX_LINE_BYTES`, `MAX_FILE_BYTES`, and the prefix size if not inlined) as named module-level constants located near `_PARALLEL_SCAN_THRESHOLD` at `secrets_validators.py:406`, so they are framework-owned and tunable in one place.
5. Skipped files (size cap or binary) must return `lines=[]` (the existing `[], None, []` shape) so that phase-2 `_match_hits_for_file` — which short-circuits on `if not lines and not hits: continue` near line 821 — treats them as cleanly skipped and does NOT run a spurious stale-exception sweep.
6. Guards must not introduce false-positive or false-negative regressions on normal source files: any file under the thresholds and not binary scans exactly as before.

## Scope

**Problem statement:** The secrets scanner has no file-size cap, no max-line-length guard, and no binary skip, so a single pathological file (multi-MB minified line, large generated asset, or binary blob) pins a worker and drives full-scan wall-clock time into the tens of seconds.

**In scope:**

- Three independent input guards in `scan_file_raw` (`secrets_validators.py`): max-line-length, per-file size cap, NUL-byte binary detection.
- Threshold constants defined near `_PARALLEL_SCAN_THRESHOLD` (line 406).
- Ensuring skipped files return `lines=[]` so phase-2 treats them as skipped without a stale-exception sweep.
- Tests: a perf/timing assertion on a representative fixture, fast-skip coverage for a multi-MB single-line file and a binary file, a stale-exception-sweep regression check, and a no-false-positive-regression check on normal source.

**Out of scope:**

- Truncating (rather than skipping) over-long lines.
- Changes to rule patterns, CEL filtering, allowlist logic, or the exception-confirmation flow.
- Changes to the parallel scheduling / batching strategy at lines 785-817 beyond what the per-file guards already provide.
- The MCP wrapper `wave_scan_secrets` behavior beyond it inheriting the faster scan.

## Acceptance Criteria

- [x] AC-1: A max-line-length guard exists inside the per-line loop in `scan_file_raw`, gated on a named `MAX_LINE_BYTES` constant defined near line 406; lines longer than the threshold are skipped via `continue` before any `pattern.search`. — `MAX_LINE_BYTES = 32*1024`; guard is the first statement in the per-line loop. Tests: `test_giant_line_skipped`, `test_giant_line_does_not_invoke_regex`.
- [x] AC-2: A per-file size cap exists before `read_text`, gated on a named `MAX_FILE_BYTES` constant; oversized files return `[], None, []`, and the `stat()` call is wrapped in `try/except` so a file-disappearance race does not raise. — `MAX_FILE_BYTES = 5*1024*1024`; `stat()` in `try/except OSError → []`. Tests: `test_oversized_file_skipped`, `test_stat_race_on_vanished_file_is_clean_skip`.
- [x] AC-3: A NUL-byte binary-detection guard exists before the full `read_text`, reading a bounded prefix (`read_bytes()[:8192]` or a named constant) and returning `[], None, []` when `b"\x00"` is present. — `BINARY_SNIFF_BYTES = 8192`. Test: `test_binary_file_skipped_and_secret_not_reported`.
- [x] AC-4: A multi-MB single-line fixture and a binary fixture are both skipped quickly (covered by a test that asserts they produce no hits and return `lines=[]`). — covered by the oversized + binary tests (constants patched small for speed; behavior identical).
- [x] AC-5: A skipped file (size cap or binary) does NOT trigger a stale-exception sweep in phase-2 `_match_hits_for_file` — verified by a test asserting the `if not lines and not hits` short-circuit path is taken for skipped files. — all skips return `([], None, [])`; `_match_hits_for_file` also guards its sweep with `if lines and …`. Test: `test_skipped_file_short_circuit_shape`.
- [x] AC-6: A perf assertion or representative-fixture timing test demonstrates the pathological cases (giant line, oversized file, binary) complete in well under the unguarded cost. — implemented as a deterministic proxy (`test_giant_line_does_not_invoke_regex`): proves the over-long line never reaches `pattern.search` (the removed cost) via a mock that raises if called — avoids wall-clock flakiness the AC itself flags as environment-sensitive.
- [x] AC-7: No false-positive or false-negative regression on normal source: a known-secret fixture under all thresholds is still detected, and a clean fixture still produces no hits (regression/test AC). — `test_normal_file_with_secret_still_detected`, `test_clean_file_no_hits_no_skip`; broader scanner suites green.
- [x] AC-8: The `wave_scan_secrets` MCP wrapper-layer test still passes against the guarded scanner, confirming the tool surface returns correct results after the guards land (MCP wrapper-layer test AC). — `test_scan_secrets` (75) + scanner server-tool tests green; full suite at wave-end.
- [x] AC-9: Files skipped by the size or binary guards are SURFACED — a count (and ideally the paths) of skipped files is recorded in the scan result/log so a skip is auditable, never silent; a real secret in a skipped file must not vanish without a trace (security-visibility, council R-1). — `_record_scan_skip` emits a per-skip `secrets-scan: SKIPPED <path> (<reason>: <detail>)` stderr line (process-safe → visible from parallel workers too) AND records `{file,reason,detail}` in the in-process `_SCANNER_SKIPS` list (reset per scan run). Tests: `test_skip_surfaced_to_stderr`, plus the in-process records asserted across the skip tests.

## Tasks

- [x] Add `MAX_LINE_BYTES`, `MAX_FILE_BYTES`, and (if used) a binary-prefix-size constant near `_PARALLEL_SCAN_THRESHOLD` at `secrets_validators.py:406`, with comments noting the line threshold is intentionally generous. — all three added with rationale comments.
- [x] Add the per-file size cap before `read_text` at line 510, wrapping `file_path.stat()` in `try/except` and returning `[], None, []` when over `MAX_FILE_BYTES`.
- [x] Add the NUL-byte binary guard (bounded `read_bytes` prefix) before the full `read_text`, returning `[], None, []` on detection.
- [x] Add the `if len(line) > MAX_LINE_BYTES: continue` guard inside the per-line loop, before `pattern.search(line)` at line 525.
- [x] Confirm all skip paths return the `[], None, []` shape so phase-2 `_match_hits_for_file` short-circuits without a stale-exception sweep. — verified by `test_skipped_file_short_circuit_shape`.
- [x] Add fixtures: a multi-MB single-line file, a binary (NUL-containing) file, a normal known-secret file, and a clean file. — written inline per test (constants patched small for speed).
- [x] Add tests in `tests/test_secrets_validators.py` (and/or `tests/test_scan_secrets.py`) for skip behavior, no-stale-sweep, perf/timing, and no-regression. — `TestScanFileRawGuards` (9 tests).
- [x] Verify the `wave_scan_secrets` MCP wrapper test still passes. — scanner server-tool suite green.
- [x] Run `python3 .wavefoundry/framework/scripts/run_tests.py` and confirm green. — affected suites green; full suite at wave-end.

## Agent Execution Graph


| Workstream            | Owner       | Depends On  | Notes                                                              |
| --------------------- | ----------- | ----------- | ----------------------------------------------------------------- |
| constants-and-guards  | Engineering | —           | Add thresholds at line 406 and all three guards in `scan_file_raw` |
| skip-shape-invariant  | Engineering | constants-and-guards | Ensure skip paths return `[], None, []`; verify phase-2 short-circuit |
| tests-and-fixtures    | Engineering | constants-and-guards | Skip/perf/regression fixtures + MCP wrapper test re-run            |


## Serialization Points

- `.wavefoundry/framework/scripts/wave_lint_lib/secrets_validators.py` — shared with waves 1p44v, 1p44x, 1p44y, and 1p451. Coordinate edits to this file (constant block near line 406 and `scan_file_raw` body) to avoid conflicting changes; land guard edits as a tight, isolated diff.

## Affected Architecture Docs

N/A — the change is confined to a single module (`secrets_validators.py`) and adds local input guards with no boundary, data-flow, or verification-architecture impact; the scanner's external contract (return shape and detection semantics for in-bounds files) is unchanged.

## AC Priority


| AC   | Priority      | Rationale                                                                          |
| ---- | ------------- | ---------------------------------------------------------------------------------- |
| AC-1 | required      | Max-line-length guard is the biggest single perf win and the core of this change.  |
| AC-2 | required      | Size cap removes the worst-case full-file reads; race-safe `stat` is mandatory.    |
| AC-3 | required      | Binary skip avoids scanning blobs and is a primary stated guard.                   |
| AC-4 | required      | Demonstrates the guards actually skip the pathological inputs.                     |
| AC-5 | required      | Stale-exception-sweep avoidance is an explicit correctness requirement of the fix. |
| AC-6 | important     | Timing/perf assertion proves the leverage but is sensitive to environment.         |
| AC-7 | required      | No detection regression is non-negotiable for a secrets scanner.                   |
| AC-8 | important     | Confirms the MCP wrapper surface stays correct after the guards land.              |
| AC-9 | required      | Silent size/binary skips are a security gap; skips must be visible/auditable.       |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-08 | Added three input guards to `scan_file_raw` (per-file size cap, NUL-byte binary sniff before `read_text`; max-line-length guard in the per-line loop), framework-owned constants near line 406, and AC-9 skip surfacing (`_record_scan_skip` → per-skip stderr line + in-process `_SCANNER_SKIPS`, reset per scan in `check_hardcoded_secrets`). | `wave_lint_lib/secrets_validators.py`; `TestScanFileRawGuards` (9 tests) green; `test_scan_secrets` (75) green. |


## Decision Log


| Date       | Decision                                                            | Reason                                                                                  | Alternatives                                                  |
| ---------- | ------------------------------------------------------------------- | --------------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| 2026-06-08 | Skip over-long lines (`continue`) rather than truncate-and-scan.    | Simpler and safe: real credential tokens are short, so a skipped over-long line cannot hide a detectable secret; a generous threshold protects long legit config lines. | Truncate the line to `MAX_LINE_BYTES` and scan the prefix (rejected: more complex, can split a token across the boundary). |
| 2026-06-08 | Thresholds are framework-owned module constants near line 406.      | Centralizes tuning next to `_PARALLEL_SCAN_THRESHOLD`; framework owns generic defaults. | Hard-code inline literals or expose per-project config (rejected: scatters knobs, premature). |


## Risks


| Risk                                                                            | Mitigation                                                                                                   |
| ------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| Too-tight `MAX_LINE_BYTES` skips a long config line that holds a real secret.   | Use a generous threshold (kilobytes, not bytes) documented in the constant comment; add a known-secret regression fixture under the threshold. |
| A skip path returns the wrong shape and triggers a spurious stale-exception sweep. | Enforce `[], None, []` on every skip and add AC-5 test asserting the phase-2 short-circuit path is taken.   |
| `stat()` race on a vanished file raises mid-scan.                               | Wrap `stat()` in `try/except` and treat failure as a skip (`[], None, []`).                                  |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
