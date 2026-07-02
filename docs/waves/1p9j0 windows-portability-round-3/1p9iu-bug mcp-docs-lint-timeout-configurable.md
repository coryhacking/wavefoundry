# Configurable server-side docs-lint timeout for full-scan lifecycle tools

Change ID: `1p9iu-bug mcp-docs-lint-timeout-configurable`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-07-02
Wave: TBD

## Rationale

`run_validate()` in `.wavefoundry/framework/scripts/server_impl.py:3056` spawns
`docs_lint.py` via `_mcp_subprocess_run(...)` with a **hardcoded** `timeout=30`
(the literal is at `server_impl.py:3074`) and runs a **full** corpus scan — the
call passes no `--changed` flag, so every doc in the tree is linted. The inline
comment at `server_impl.py:3064-3069` justifies 30s as "generous (lint typically
completes <100ms on this repo's corpus)". That is true for Wavefoundry's own
corpus and false for large field repos: the 1.9.8 native-Windows big-repo field
report flagged the docs-lint 30s timeout as too short and asked for it to be made
configurable.

A configurable knob already exists — but it is wired only to the post-edit hook,
not to the server. `indexer.py:221` defines `docs_lint_hook_timeout_seconds(root)`,
which reads `docs/workflow-config.json` → `docs_lint.hook_timeout_seconds`
(default `DOCS_LINT_HOOK_TIMEOUT_DEFAULT = 120.0` at `indexer.py:218`, fail-safe
on any error/missing/non-positive value). Its only consumer is the post-edit
hook body in `render_platform_surfaces.py:340`, which additionally runs
**incrementally** (`--changed`, `render_platform_surfaces.py:350`) and, on
timeout, prints an advisory pointing the operator at
`docs_lint.hook_timeout_seconds` (`render_platform_surfaces.py:352-357`).
`server_impl.py` never imports or calls that helper — `run_validate` keeps its own
hardcoded 30s and no `--changed`, so the two paths have diverged: the light
incremental hook path is tunable, and the heavy full-scan server path is not.

The blast radius is the wave lifecycle. `run_validate` is caught only in two
places — `_run_post_write_lint` (`server_impl.py:3004`, `except Exception` at
`server_impl.py:3030`) and the `wave_audit_response` validation sub-check
(`server_impl.py:6139`, `except Exception`). Every **other** direct caller lets
`subprocess.TimeoutExpired` propagate:

- `wave_validate_response` — call at `server_impl.py:6320`
- `wave_install_audit_response` — CHECK 1 call at `server_impl.py:6389`
- `wave_prepare_response` — call at `server_impl.py:8930`
- `wave_review_response` — call at `server_impl.py:9155`
- `wave_close_response` — call at `server_impl.py:9613`

So on a large repo whose full docs-lint scan exceeds 30s, `wave_validate`,
`wave_prepare`, `wave_review`, `wave_close`, and `wave_install_audit` fail
outright with a raw `TimeoutExpired` rather than either honoring an operator-set
timeout or reporting an actionable diagnostic. These are exactly the tools that
gate readiness and close, so the defect blocks the wave workflow on the repos
where it is most likely to trigger. (Wavefoundry's own `docs/workflow-config.json`
has no `docs_lint` section today, so all defaults apply as-shipped.)

## Requirements

1. Add a shared, config-reading helper that returns the timeout (seconds) for the
   **server-side full-scan** docs-lint subprocess, reading `docs/workflow-config.json`
   → `docs_lint.full_scan_timeout_seconds`, with a generous default constant that
   at minimum matches the hook default floor (120s). The helper must be fail-safe:
   any error / missing key / non-positive value falls back to the default and never
   raises — mirroring the contract of `indexer.docs_lint_hook_timeout_seconds`.
2. `run_validate()` must use that helper's value in place of the hardcoded
   `timeout=30` at `server_impl.py:3074`. The full-scan behavior (no `--changed`)
   is unchanged.
3. On `subprocess.TimeoutExpired`, `run_validate()` must return a structured,
   caller-legible result (rather than propagating a raw exception) whose `errors`
   include a clear message naming the config key to raise
   (`docs_lint.full_scan_timeout_seconds`) and the elapsed timeout. Because every
   propagating caller already renders `errors` through `docs_lint_error`
   diagnostics, this flows an actionable message through all five lifecycle tools
   with no per-caller change.
4. Preserve the existing `_run_post_write_lint` `try/except` handling
   (`server_impl.py:3030`) as-is — it remains the broader defense-in-depth safety
   net for write-tool responses; the new in-`run_validate` timeout catch is
   additive, not a replacement.
5. Update the now-stale justification comment at `server_impl.py:3064-3069` so it
   describes the configurable timeout and the config key, not a fixed 30s.

## Scope

**Problem statement:** The server-side full-corpus docs-lint invocation
(`run_validate`) uses a hardcoded 30s timeout with no `--changed`, and five wave
lifecycle tools (`wave_validate`, `wave_prepare`, `wave_review`, `wave_close`,
`wave_install_audit`) propagate its `TimeoutExpired` as a hard failure. On large
repos whose full scan exceeds 30s, those tools break, and — unlike the post-edit
hook — the timeout is not operator-configurable.

**In scope:**

- A shared helper reading `docs_lint.full_scan_timeout_seconds` from
  workflow-config, with a generous fail-safe default (co-located with the existing
  `docs_lint_hook_timeout_seconds` conventions), consumed by `run_validate`.
- Replacing the hardcoded `timeout=30` in `run_validate` with the configured value.
- A legible timeout diagnostic naming the config key, surfaced through the existing
  `errors`/`docs_lint_error` path so all five lifecycle callers report it clearly.
- Refreshing the stale comment at `server_impl.py:3064-3069`.
- Unit tests for the helper (config read / default / fail-safe) and for
  `run_validate` (configured timeout is applied; the timeout path yields a legible
  result naming the key).

**Out of scope:**

- Switching `wave_prepare` / `wave_close` (or any lifecycle tool) to `--changed`.
  They intentionally run a full corpus scan; only the timeout is being made
  configurable.
- Changing the post-edit hook path (`render_platform_surfaces.py` / the
  `docs_lint_hook_timeout_seconds` knob). That path already works.
- Pre-seeding `docs_lint.full_scan_timeout_seconds` into the framework
  workflow-config skeleton (defaults live in code; keep the skeleton minimal).
- Any change to `docs_lint.py`'s own scan logic or performance
  (docs-lint speedups are tracked separately).

## Acceptance Criteria

- [ ] AC-1: A helper resolves the server-side full-scan docs-lint timeout from
  `docs/workflow-config.json` → `docs_lint.full_scan_timeout_seconds`, returning a
  configured positive value when present and the default (>= 120s) otherwise; any
  malformed/missing/non-positive value returns the default without raising. Covered
  by a unit test with configured, absent, and malformed inputs.
- [ ] AC-2: `run_validate()` passes the helper's value as the `_mcp_subprocess_run`
  `timeout`; the hardcoded `timeout=30` at `server_impl.py:3074` is gone. Verified
  by a unit test that sets the config value and asserts the timeout forwarded to the
  subprocess runner.
- [ ] AC-3: `run_validate()` still runs a full scan (no `--changed`); a unit test
  asserts the spawned argv does not include `--changed`.
- [ ] AC-4: On `subprocess.TimeoutExpired`, `run_validate()` returns
  `passed: False` with an `errors` entry that names
  `docs_lint.full_scan_timeout_seconds` and the elapsed timeout, instead of raising.
  A unit test forces a timeout and asserts the returned structure and message.
- [ ] AC-5: `_run_post_write_lint`'s existing `try/except` at `server_impl.py:3030`
  is retained unchanged (confirmed by reading the diff).
- [ ] AC-6: The justification comment at `server_impl.py:3064-3069` describes the
  configurable timeout and the config key rather than a fixed 30s.
- [ ] AC-7: `python3 .wavefoundry/framework/scripts/run_tests.py` passes.

## Tasks

- [ ] Read `server_impl.py:3056-3085` (`run_validate`), `server_impl.py:3004-3036`
  (`_run_post_write_lint`), and `indexer.py:216-234`
  (`DOCS_LINT_HOOK_TIMEOUT_DEFAULT` / `docs_lint_hook_timeout_seconds`) to anchor
  the change on current line numbers.
- [ ] Add a full-scan default constant and a `_read_workflow_config`-based helper
  (`server_impl.py` already has `_read_workflow_config` at `server_impl.py:1991`)
  that reads `docs_lint.full_scan_timeout_seconds`, fail-safe to the default.
- [ ] Wire the helper into `run_validate()`; replace the literal `timeout=30` at
  `server_impl.py:3074` with the resolved value.
- [ ] Wrap the `_mcp_subprocess_run` call in `run_validate` to catch
  `subprocess.TimeoutExpired` and return a structured `passed: False` result whose
  `errors` name `docs_lint.full_scan_timeout_seconds` and the elapsed timeout.
- [ ] Update the stale comment at `server_impl.py:3064-3069`.
- [ ] Add unit tests in
  `.wavefoundry/framework/scripts/tests/test_server_tools.py` covering the helper
  (configured / default / malformed), the forwarded timeout, the full-scan argv
  (no `--changed`), and the timeout-path legible result.
- [ ] Run `python3 .wavefoundry/framework/scripts/run_tests.py` and fix failures.
- [ ] Run `wave_validate` on this repo (docs gate) before handoff.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ------------------------------ | ----------- | ------------ | ------------------------------------------------------------------------------------------------------------ |
| ws1-helper-and-run-validate | implementer | —            | Add the full-scan timeout constant + config helper in `server_impl.py`; wire into `run_validate`; catch `TimeoutExpired` → legible result; refresh the stale comment. Single-file edit in `server_impl.py`. |
| ws2-tests | implementer | ws1-helper-and-run-validate | Add unit tests in `test_server_tools.py` (helper config/default/fail-safe; forwarded timeout; no `--changed`; timeout-path message). Runs the framework suite. |


## Serialization Points

- `.wavefoundry/framework/scripts/server_impl.py` — all production edits land in
  this one file (`run_validate`, the new helper/constant, the comment). Single
  owner; no concurrent edits.
- `.wavefoundry/framework/scripts/tests/test_server_tools.py` — test additions;
  land after ws1 so assertions match the final signatures.

## Affected Architecture Docs

N/A — the change is confined to a single module's subprocess timeout
configuration. It adds no cross-module boundary, changes no data/control flow, and
does not alter the docs-gate verification architecture (docs-lint remains the hard
gate at prepare/close; only its timeout becomes configurable). No architecture doc
describes the hardcoded 30s value.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority   | Rationale |
| ---- | ---------- | --------- |
| AC-1 | required   | The configurable helper is the core of the fix — without it the timeout stays hardcoded. |
| AC-2 | required   | Wiring the helper into `run_validate` is the behavior change the field report asked for. |
| AC-3 | required   | Guards the explicit out-of-scope boundary: full scan must be preserved (no `--changed`). |
| AC-4 | important  | Turns a raw `TimeoutExpired` into an actionable diagnostic; the fix works without it but is far less legible. |
| AC-5 | required   | Preserving the existing safety net is a stated constraint; regressing it would widen scope. |
| AC-6 | low        | Comment hygiene; the stale text misleads future readers but has no runtime effect. |
| AC-7 | required   | The framework suite must stay green. |


## Progress Log


| Date       | Update | Evidence |
| ---------- | ------ | -------- |
| 2026-07-02 | Scoped from the 1.9.8 Windows big-repo install audit (F2, medium): `run_validate` full-scan timeout is hardcoded 30s and not configurable, breaking five lifecycle tools on large repos while the equivalent hook knob exists. Verified all cited sites against the post-1p9hn tree and corrected line numbers. | Windows audit `wf_eab9a03d-004`; comparison `wf_33ca6bdb-757`; primary site `server_impl.py:3074` (`timeout=30` in `run_validate`); existing knob `indexer.py:221` / default `indexer.py:218`; propagating callers `server_impl.py:6320,6389,8930,9155,9613`. |


## Decision Log


| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-07-02 | Introduce a distinct `docs_lint.full_scan_timeout_seconds` key rather than reuse `docs_lint.hook_timeout_seconds`. | The full-corpus server scan and the incremental (`--changed`) post-edit hook have different cost profiles; a separate knob lets operators tune the heavy path without loosening the hook, while co-locating both under the `docs_lint` namespace. | (a) Reuse `hook_timeout_seconds` for both — simpler single knob, but couples two different cost profiles; (b) raise only the hardcoded default with no config key — leaves the "make it configurable" field ask unmet. |
| 2026-07-02 | On timeout, have `run_validate` return `passed: False` with a legible `errors` message instead of propagating `TimeoutExpired`. | Every propagating caller already renders `errors` via `docs_lint_error`, so one internal catch yields an actionable diagnostic across all five tools with zero per-caller edits. | Add try/except at each of the five call sites — five edits, more surface, higher regression risk. |
| 2026-07-02 | Do not pre-seed the new key into the framework workflow-config skeleton. | Framework owns generic defaults in code; the skeleton stays minimal (no duplicate-of-code-default blocks). | Emit the key with its default into every project's workflow-config — noisy and redundant. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Returning `passed: False` on timeout (instead of the previous raw exception) changes `_run_post_write_lint`'s result from `clean: None` to `clean: False` on the rare timeout. | Acceptable and more actionable — the message names the config key. `_run_post_write_lint`'s `except` is retained as a broader net; a unit test pins the timeout-path result shape. |
| A misconfigured very-large `full_scan_timeout_seconds` could let a genuinely hung lint block a tool longer than before. | The value is operator-set and only raised deliberately; the default stays generous-but-bounded (>=120s), and non-positive/malformed values fail safe to the default. |
| Line numbers shift again before implementation. | Requirements and tasks cite constructs (`run_validate`, the `timeout=` literal, `_run_post_write_lint`, the five caller functions) alongside current line numbers; implementer re-reads before editing. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
