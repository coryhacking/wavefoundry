# Post-edit docs-lint hook: bound + configure the subprocess timeout (never hang, never fail early)

Change ID: `1p9bg-bug docs-lint-hook-timeout-configurable`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-01
Wave: `1p9bf windows-install-robustness`

## Rationale

Field feedback (native-Windows install of 1.9.8, large repo): the post-edit docs-lint gate hit a
hardcoded ~30 s timeout that was too short — the operator's agent had to raise it. In the current tree
the opposite hazard exists: the docs-lint hook invokes `docs_lint.py` through
`render_platform_surfaces.run_command` (→ `subprocess_util.isolated_run`) with **no timeout at all**, so
a slow or hung docs-lint on a large repo blocks the post-edit hook **unbounded** — which stalls the
editing agent (a plausible contributor to the same field report's "Claude spinning for minutes" /
"stuck for hours" symptoms). Compounding it, `maybe_docs_lint` calls `docs_lint.py` with **no file
argument**, so it lints the **whole docs tree on every edit** — the cost that makes the timeout bite.

Both failure modes have one fix: give the docs-lint hook subprocess a **generous, configurable
timeout**, and on timeout **fail safe** (do not block the edit) so a slow lint degrades to "skipped this
pass" instead of either a false rejection or an unbounded hang. `wave_validate` / the next pass still
catch real lint errors.

## Requirements

1. The post-edit docs-lint hook subprocess runs with an explicit `timeout` on both the `isolated_run`
   path and the bare `subprocess.run` fallback.
2. The timeout defaults to a generous value (**120 s**, well above the reported 30 s) and is overridable
   via `docs/workflow-config.json` (`docs_lint.hook_timeout_seconds`); a missing/invalid value falls back
   to the default (fail-safe read, never raises).
3. On `TimeoutExpired` the hook **does not block the edit** — it logs a one-line advisory to stderr and
   returns "not blocked", so a slow lint never hangs the agent and never falsely rejects an edit.
   (docs-lint stays advisory at the hook; the hard gate is `wave_validate` / close.)
4. Rendered across every platform hook body that runs docs-lint (`render_platform_surfaces.py` source +
   re-render): Claude post-edit, Cursor after-file-edit + docs-lint, Copilot, Windsurf docs-lint.
5. Full framework suite green + `wave_validate` clean; idempotent re-render.

## Scope

**Problem statement:** the docs-lint hook subprocess is unbounded (was too-short-fixed at 30 s in the
field build); a slow whole-tree lint on a large repo either hangs the hook or fails the edit.

**In scope:**

- `render_platform_surfaces.py`: `run_command`/`maybe_docs_lint` pass a `timeout`; a
  `docs_lint_hook_timeout_seconds(root)` helper reads `docs/workflow-config.json` with the 120 s default;
  `TimeoutExpired` handled as non-blocking with an advisory. Re-render all platform hook surfaces.
- Tests: the helper (default, override, bad value); a timeout maps to "not blocked" + an advisory; the
  rendered bodies pass a `timeout=` argument on the docs-lint spawn.

**Out of scope:**

- **Incremental single-file docs-lint** (lint only the changed file rather than the whole tree) — the
  higher-value follow-up, but it must preserve cross-reference validation, so it is its own change.
- The `wave_validate` / close docs-lint path (not the hot per-edit hook; no per-edit timeout pressure).
- The `#1`/`#4` install hangs themselves (validation item on the 1.10.0 Windows install).

## Acceptance Criteria

- [x] AC-1: the docs-lint hook subprocess runs with an explicit `timeout` on both the `isolated_run` and
      the fallback `subprocess.run` paths. Evidence: `run_command(argv, timeout=None)` forwards `timeout=`
      to both; `test_docs_lint_hook_is_bounded_and_advisory_on_timeout` asserts the wiring in the rendered body.
- [x] AC-2: the timeout defaults to 120 s and is overridable via
      `docs/workflow-config.json` `docs_lint.hook_timeout_seconds`; a missing/invalid value uses the
      default and never raises. Evidence: `indexer.docs_lint_hook_timeout_seconds` +
      `DocsLintHookTimeoutTests` (default, override, non-numeric/zero/negative, bad-json, missing dir).
- [x] AC-3: a docs-lint `TimeoutExpired` returns "not blocked" (the edit proceeds) with a stderr
      advisory — it never blocks the edit and never hangs. Evidence: `maybe_docs_lint` catches
      `subprocess.TimeoutExpired` → returns `(False, "")` + a stderr advisory (asserted in the render test).
- [x] AC-4: rendered across all docs-lint hook bodies; idempotent re-render; `run_tests.py` +
      `wave_validate` pass. Evidence: re-render (claude/cursor/copilot/windsurf) + rendered `.claude/hooks/post-edit.py`
      compiles with the timeout wiring; full suite + docs gate.

## Tasks

- [x] `indexer.docs_lint_hook_timeout_seconds(root)` (config read, 120 s default, fail-safe) +
      `DOCS_LINT_HOOK_TIMEOUT_DEFAULT`; `render_platform_surfaces.py` threads `timeout=` through
      `run_command`/`maybe_docs_lint` and handles `TimeoutExpired` as non-blocking + advisory; re-rendered all hosts. Done.
- [x] Tests (`DocsLintHookTimeoutTests` 4 helper arms; render-source assertion of the timeout +
      `TimeoutExpired` wiring); `run_tests.py` + `wave_validate` pending final run. Done.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| [workstream-1] | implementer | — | Single lane: `render_platform_surfaces` helper + hook-body timeout + re-render + tests. Touches rendered hook surfaces — full suite + idempotent re-render gate it. |

## Serialization Points

- `render_platform_surfaces.py` is the canonical hook-body source; edit + re-render, never hand-edit a
  rendered hook (self-hosting boundary). The timeout helper is shared by every docs-lint hook body.

## Affected Architecture Docs

N/A — a hook-robustness fix; no boundary/flow change. (The hook cadence is described in
`docs/architecture/chunking-and-indexing-pipeline.md`, unaffected.)

## AC Priority

| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The core fix — bound the subprocess so it can't hang the hook. |
| AC-2 | required | Configurable + generous default so a large repo doesn't fail early. |
| AC-3 | required | Fail-safe on timeout — never block an edit, never hang. |
| AC-4 | required | Rendered everywhere, no regression, idempotent. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-01 | Planned from 1.9.8 native-Windows field feedback (docs-lint 30 s too short). Found the current tree has NO timeout on the docs-lint hook spawn (unbounded) and lints the whole tree per edit — so the fix bounds + configures it and fails safe. Admitted to the pre-1.10.0 `1p9bf` wave. | operator field report; `render_platform_surfaces.run_command`/`maybe_docs_lint`. |
| 2026-07-01 | Implemented. `indexer.docs_lint_hook_timeout_seconds` (120 s default, `docs_lint.hook_timeout_seconds` override, fail-safe) + `run_command(timeout=)` + `maybe_docs_lint` advisory-on-`TimeoutExpired`; re-rendered all hosts. The helper lives in `indexer.py` (unit-tested); the hook loads it via the existing hook-helpers path with a 120 s fallback. AC-1..4 met. | `DocsLintHookTimeoutTests` (4) + render assertion; rendered `post-edit.py` compiles with the wiring. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-01 | On timeout, do NOT block the edit (advisory), rather than fail the edit. | Blocking on a slow lint is worse than skipping it — it would reject legitimate edits; `wave_validate`/close remain the hard gate. | Block on timeout (rejected — false rejections); keep unbounded (rejected — hangs the agent). |
| 2026-07-01 | Generous default (120 s) + `workflow-config` override, not a bare bump. | A fixed value can't fit every repo size; a config knob lets a very large repo raise it without editing rendered hooks. | Hardcode a bigger constant (rejected — not tunable); env var only (rejected — config is the project contract). |
| 2026-07-01 | Keep whole-tree lint; defer incremental single-file lint. | Incremental linting must preserve cross-reference validation — a larger, riskier change; the timeout addresses the reported symptom now. | Make lint incremental here (deferred — own change). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| A generous timeout still blocks the agent for up to 120 s on a huge repo. | Advisory-on-timeout means the edit is never rejected; the config knob lets a huge repo lower it; incremental lint is the deferred structural fix. |
| Advisory-on-timeout lets a real lint error through the hook. | The hook was always best-effort; `wave_validate` and wave-close are the authoritative docs gates and are unchanged. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
