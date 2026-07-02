# Windows dashboard cmdline parse: spaced --root paths defeat reconciliation

Change ID: `1p9hl-bug windows-dashboard-cmdline-parse`
Change Status: `implemented`
Owner: implementer
Status: implemented
Last verified: 2026-07-02
Wave: 1p9hn windows-portability-round-2

## Rationale

`dashboard_lib.dashboard_cmdline_pids` (`:322`) extracts the `--root` value from a running process's command line using `rest.split()` followed by `cand = toks[i+1]`. On Windows, `_windows_process_cmdlines` reads `Win32_Process.CommandLine`, and Python's `subprocess.list2cmdline` quotes arguments containing spaces (e.g. `--root "C:\Users\First Last\repo"`). `rest.split()` yields `cand = '"C:\\Users\\First'` — a quote-prefixed, space-truncated token whose `Path(...).resolve()` never equals the target.

When the token does not match, the loop returns an empty list. `_dashboard_pid_is_live` and `_dashboard_already_serving` treat the running dashboard as absent, and `wave_dashboard_start` re-spawns a duplicate that climbs to the next port — reintroducing the field symptom that wave 1p8pf closed.

Space-free paths are unaffected (`list2cmdline` only quotes values containing spaces), so this only triggers on Windows repo paths with spaces (common: `C:\Users\First Last\…`, `C:\Program Files\…`).

## Requirements

1. `dashboard_cmdline_pids` must correctly extract the `--root` value when the command-line argument is quoted (e.g. `"C:\Users\First Last\repo"`) on Windows.
2. The fix must handle both the `--root VALUE` (space-separated) and `--root=VALUE` (equals-separated) forms.
3. The path comparison after extraction must remain `Path(cand).resolve() == Path(target).resolve()` (normalization is already correct).
4. A regression test must drive the matching loop with a quoted, spaced `--root` value and assert the correct PID is returned.

## Scope

**Problem statement:** On Windows with repo paths containing spaces, `dashboard_cmdline_pids` cannot parse the quoted `--root` value from the process command line, returning an empty list and causing `wave_dashboard_start` to re-spawn duplicate servers that climb ports.

**In scope:**

- `dashboard_lib.py:322`: replace `rest.split()` with `shlex.split(rest, posix=False)` or equivalent dequote + reassemble logic
- Regression test with a quoted, spaced `--root` value

**Out of scope:**

- The POSIX `_posix_process_cmdlines` path (unaffected)
- Dashboard server spawn, port selection, or reconciliation logic beyond the PID-matching step

## Acceptance Criteria

- [x] AC-1: `dashboard_cmdline_pids` correctly matches a running dashboard with `--root "C:\Users\First Last\repo"` in its command line — quote-aware `_ROOT_ARG_RE`; test asserts PID 2001
- [x] AC-2: The `--root=VALUE` form is also handled correctly — including the quoted `--root="..."` form; test asserts PID 2002
- [x] AC-3: Space-free paths continue to match as before (non-regression) — existing `test_cmdline_scan_parses_and_matches_root` (`--root <val>` + `--root=<val>` bare forms) still green
- [x] AC-4: A regression test with a quoted, spaced `--root` value asserts the correct PID is returned — `test_cmdline_scan_matches_quoted_spaced_root`

## Tasks

- [x] Replace `rest.split()` at `dashboard_lib.py` with a quote-aware regex (`_ROOT_ARG_RE`). **Decision: regex, not `shlex.split(posix=False)`** — shlex(posix=False) tokenizes `--root="/a b/c"` as `['--root="/a', 'b/c"']` (a mid-token quote is not grouped), so it fails AC-2. The regex handles both `--root <val>` and `--root=<val>`, quoted or bare, with backslashes literal.
- [x] Add regression test driving the matching loop with a quoted spaced `--root` command line (both `--root "..."` and `--root="..."` forms)

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| fix-parse | implementer | — | shlex.split fix at dashboard_lib.py:322 |
| add-test | implementer | fix-parse | Regression test with quoted spaced path |

## Serialization Points

- None.

## Affected Architecture Docs

N/A — confined to `dashboard_lib.py` command-line parsing. No boundary or flow change.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Core fix for the spaced-path case |
| AC-2 | required | --root=VALUE form must also work |
| AC-3 | required | Non-regression for space-free paths |
| AC-4 | required | Regression test closes the gap |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-07-02 | Change doc created from 10-dimension Windows audit | audit workflow wf_51bd40fe-082 |
| 2026-07-02 | Implemented: quote-aware `_ROOT_ARG_RE` replaces `rest.split()` in `dashboard_lib.dashboard_cmdline_pids` (server_impl delegates to it); regression test for both quoted `--root "..."` and `--root="..."` forms | `DashboardProcessControlTests` cmdline tests 3/3 green |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-07-02 | Planned `shlex.split(posix=False)` | stdlib, preserves Windows quoting rules | Manual quote stripping |
| 2026-07-02 | **Changed to a quote-aware regex** (`_ROOT_ARG_RE`) during implementation | Empirically `shlex.split("--root=\"/a b/c\"", posix=False)` yields `['--root="/a', 'b/c"']` — a mid-token quote is NOT grouped, so the `--root=VALUE` quoted form (AC-2) would fail. The regex matches both `--root <val>` and `--root=<val>`, quoted or bare, backslashes literal. | `shlex.split(posix=False)` (fails AC-2); manual scan (more code) |

## Risks

| Risk | Mitigation |
| --- | --- |
| `shlex.split` raises on malformed command lines | Wrap in try/except and fall back to existing split behavior; malformed cmdline returns no match (same as today) |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
