# Rescope the post-write docs-lint to the incremental `--changed` scan, reserving full-corpus scans for the lifecycle gates

Change ID: `1p9p8-enh post-write-lint-incremental-changed`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-07-04
Wave: TBD

## Rationale

Every write-side wave MCP tool attaches a post-write docs-lint result to its response via `_run_post_write_lint` (`.wavefoundry/framework/scripts/server_impl.py:3019`), which calls `run_validate(root)` (`:3071`). `run_validate` runs a **full-corpus** docs-lint scan (`docs_lint.py` with **no** `--changed`, `:3095-3099`) bounded by `docs_lint_full_scan_timeout_seconds` (default `DOCS_LINT_FULL_SCAN_TIMEOUT_DEFAULT`, 300s, `:2005`). Consequences:

- **The post-write path pays full-corpus cost on every write tool.** A write tool that touched one or two docs re-lints the entire corpus just to attach a lint summary — the response cannot return until the whole-tree scan completes.
- **A stalled lint blocks the response for up to 300s.** Because `_run_post_write_lint` shares `run_validate`'s bound, a genuinely hung `docs_lint.py` holds every write-side tool response for the full 300s window (10× the pre-`1p9iu` 30s worst case; the tradeoff was explicitly accepted-but-flagged in `1p9iu`'s risk table and raised again by the first `1p9j0` delivery council's rotating seat as the "rescope to `--changed`" alternative).

The incremental machinery already exists and is proven on the hot path: the post-edit hook runs `docs_lint.py --changed` (`render_platform_surfaces.py:350`), which self-detects the git working-tree changed set (`wave_lint_lib/cli.py:62` flag; `_run_incremental_checks` at `:168`, reusing secrets' `_get_changed_files`), runs only the per-file validators on changed `docs/` markdown, and safely no-ops (`([], [])`) on an empty or non-git changed set. A changed *config* file falls back to the full lint inside the CLI. The hook bounds it with `docs_lint_hook_timeout_seconds` (default 120s, `indexer.py:221` post-1roqn).

The write tools' own mutations land in the git working tree (unstaged), so `--changed` picks up exactly what the tool just wrote. Rescoping `_run_post_write_lint` to `--changed` with the shorter hook bound makes the post-write signal near-instant and cheap, while the **authoritative full-corpus gate stays** where correctness requires it — the five lifecycle tools (`wave_validate`, `wave_prepare`, `wave_review`, `wave_close`, `wave_install_audit`) keep calling `run_validate` (full scan) unchanged.

## Requirements

1. `_run_post_write_lint` must run an **incremental** (`--changed`) docs-lint scan, not the full-corpus `run_validate`, so a write tool's post-write lint reflects only the changed docs and returns quickly.
2. The incremental post-write scan must be bounded by the **hook** timeout knob (`docs_lint.hook_timeout_seconds`, default 120s via `indexer.docs_lint_hook_timeout_seconds`), not the full-scan knob — the whole point is a lighter, faster bound for the interactive path.
3. The full-corpus `run_validate` callers must be **unchanged** — they continue to run the full scan; only the post-write attachment path is rescoped. Besides `_run_post_write_lint`, there are **six** `run_validate` callers (readiness re-review census, confirmed at `server_impl.py:6266,6447,6516,9057,9282,9740` (refreshed 2026-07-04 post-1p9q3; exhaustive recount: 8 `run_validate(` hits = 1 def + 7 callers)): the five lifecycle gates (`wave_validate`, `wave_prepare`, `wave_review`, `wave_close`, `wave_install_audit`) **plus `wave_audit`** (the combined-readout tool, `:6266` — omitted from the original plan's census). All six stay full-corpus.
4. The post-write result shape returned by `_run_post_write_lint` (`{clean, error_count, warning_count, first_errors}`) must be unchanged so no envelope consumer breaks; the incremental scan's timeout/failure path must degrade to the same `clean: None`/legible-error contract the current defensive `except` provides.
5. Empty or non-git changed sets must be treated as a clean no-op (mirroring `_run_incremental_checks`'s `([], [])` contract), so a write tool that touched no `docs/` markdown (or a non-git checkout) reports clean rather than erroring — the full gates remain the backstop that catches anything the incremental path skips.
6. A changed config file must still fall back to the full lint (the CLI already does this inside `--changed`); the post-write path must not defeat that fallback.

## Scope

**Problem statement:** The post-write docs-lint attached to every write-side tool response runs a full-corpus scan bounded at 300s, so it is heavier and slower than the interactive path needs and can block a tool response for up to 5 minutes on a stalled lint — even though the incremental `--changed` machinery (already used by the post-edit hook) would scan only what the tool just wrote.

**In scope:**

- Add a `run_validate_changed(root)` helper (or an equivalent `changed=`/incremental parameter on the validate path) in `server_impl.py` that invokes `docs_lint.py --changed` with the `docs_lint_hook_timeout_seconds` bound and returns the same `{passed, errors, warnings, output}` shape as `run_validate`, with the same structured timeout-return contract.
- Rewire `_run_post_write_lint` (`:3019`) to call the incremental helper instead of `run_validate`.
- Leave the five lifecycle callers of `run_validate` untouched (full scan).
- Tests: post-write lint runs `--changed` (argv assertion, no full-corpus scan), uses the hook timeout, reports clean on an empty changed set, surfaces a changed-doc error, and preserves the `{clean, error_count, warning_count, first_errors}` shape + the timeout/exception degradation.

**Out of scope:**

- Any change to `run_validate` itself or to the five lifecycle gates' full-scan behavior — full-corpus remains authoritative there.
- Changes to `docs_lint.py` / `wave_lint_lib/cli.py` `--changed` logic (it already exists and is proven by the hook).
- Changing the `docs_lint.hook_timeout_seconds` / `docs_lint.full_scan_timeout_seconds` config keys or defaults.
- The post-edit hook path (`render_platform_surfaces.py`) — it already uses `--changed`; no change.
- A third timeout knob dedicated to the post-write path — reuse the existing hook knob.

## Acceptance Criteria

- [ ] AC-1: `_run_post_write_lint` invokes `docs_lint.py` with `--changed` (not a full-corpus scan); a unit test asserts the spawned argv includes `--changed` and that the post-write path does not run the full scan.
- [ ] AC-2: The post-write incremental scan is bounded by `docs_lint_hook_timeout_seconds` (default 120s), verified by a unit test that sets the hook config value and asserts the forwarded subprocess `timeout`.
- [ ] AC-3: **All** full-corpus `run_validate` callers (the five lifecycle gates `wave_validate`/`wave_prepare`/`wave_review`/`wave_close`/`wave_install_audit` **plus `wave_audit`**) still run the full scan (no `--changed`); the post-write path is the **only** `--changed` caller. A unit test asserts every one of the six full-scan call sites still routes through `run_validate` (not "at least one" — a partial rescope leak into some gates must fail), and that `_run_post_write_lint` is the sole `--changed` caller.
- [ ] AC-4: `_run_post_write_lint` returns the unchanged `{clean, error_count, warning_count, first_errors}` shape for: a clean changed set, a changed set with a docs error, an empty/non-git changed set (reports clean), and a timeout (degrades to the legible/`clean` contract, not a raised exception). Covered by unit tests.
- [ ] AC-5: A changed **config** file still triggers the CLI's internal full-lint fallback (not silently skipped) — verified by a test or by confirming the `--changed` CLI contract is unmodified and exercised.
- [ ] AC-6: `python3 .wavefoundry/framework/scripts/run_tests.py` passes; `wave_validate` is clean.

## Tasks

- [ ] Add `run_validate_changed(root)` in `server_impl.py` next to `run_validate` (`:3071`): spawn `docs_lint.py --changed`, bound by `docs_lint_hook_timeout_seconds`, same `{passed, errors, warnings, output}` shape + structured timeout return naming `docs_lint.hook_timeout_seconds`.
- [ ] Rewire `_run_post_write_lint` (`:3019`) to call `run_validate_changed`; keep the defensive `except` and the `{clean, ...}` shape.
- [ ] Confirm (and pin with a test) the five lifecycle callers still call `run_validate` (full scan) — no accidental rescope of the gates.
- [ ] Add unit tests in `tests/test_server_tools.py`: `--changed` argv on the post-write path, hook-timeout binding, clean-on-empty-changed-set, error-on-changed-doc, timeout degradation, and a lifecycle-path full-scan regression assertion.
- [ ] Run `python3 .wavefoundry/framework/scripts/run_tests.py` and `wave_validate`; clean any `__pycache__`.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| ws1-incremental-helper | implementer | — | Add `run_validate_changed`; rewire `_run_post_write_lint`. Single-file edit in `server_impl.py`. |
| ws2-tests | implementer | ws1-incremental-helper | Post-write `--changed` + hook-timeout + shape/degradation tests; lifecycle full-scan regression guard. |


## Serialization Points

- All production edits land in `server_impl.py` (`run_validate_changed`, `_run_post_write_lint`); single owner. Tests in `test_server_tools.py` land after ws1 so assertions match the final helper signature.

## Affected Architecture Docs

N/A — the change swaps one internal subprocess invocation (full-corpus → `--changed`) on the post-write attachment path and adds a sibling helper. The docs-gate architecture is unchanged: full-corpus docs-lint remains the authoritative gate at prepare/close/validate/review/install; only the advisory post-write attachment becomes incremental. No boundary, data/control-flow, or verification-strategy change. The `docs/specs/mcp-tool-surface.md` post-write-lint description may get a one-line note that the attached lint is incremental (`--changed`) while the lifecycle gates are full-corpus — captured as a task if the spec currently characterizes it.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | Running `--changed` on the post-write path is the core behavior change. |
| AC-2 | required | The lighter hook bound is the latency win the change exists for. |
| AC-3 | required | The full-corpus gates must not be weakened — this is the correctness guard on the rescope. |
| AC-4 | required | Envelope-shape + degradation invariance is what keeps every write-tool consumer working. |
| AC-5 | important | Preserves the config-change full-lint fallback so a cross-file config edit is not silently under-checked post-write; the lifecycle gates backstop it regardless. |
| AC-6 | required | Suite + docs-lint green is the standing merge gate. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-03 | Scoped from the first `1p9j0` delivery council's rotating-seat (performance) alternative and `1p9iu`'s accepted-but-flagged 30s→300s post-write latency risk. Verified: `_run_post_write_lint` (`server_impl.py:3033` post-1p9q3) → `run_validate` (`:3085`) full scan, no `--changed` (~:3098-3112), 300s bound (`docs_lint_full_scan_timeout_seconds`, `:2005` — still exact). Incremental machinery present and proven: `docs_lint.py --changed` via the post-edit hook (`render_platform_surfaces.py:350`), flag + `_run_incremental_checks` in `wave_lint_lib/cli.py:62,171` (safe `([], [])` no-op; config-change → full-lint fallback), hook bound `docs_lint_hook_timeout_seconds` (default 120s, `indexer.py:221` post-1roqn). | `server_impl.py:2005,3033,3085,~3098-3112` (refreshed 2026-07-04); `wave_lint_lib/cli.py:62,171`; `render_platform_surfaces.py:350`; `indexer.py:221`. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-03 | Rescope the post-write path to `--changed` + hook bound; keep the five lifecycle gates on the full scan. | Each path gets the scope it needs: interactive post-write attachment is near-instant on what the tool just wrote, while correctness-critical readiness/close gates stay full-corpus. Uses shipped, hook-proven machinery. | (i) Lower the full-scan default for everyone — rejected: weakens the lifecycle gates. (ii) Add a third post-write-only timeout knob on the full scan — rejected: knob proliferation and still pays full-corpus cost. (iii) Do nothing — rejected: the 300s post-write worst case and per-tool full-corpus cost are the recorded pain. |
| 2026-07-03 | Reuse `docs_lint.hook_timeout_seconds` rather than a new key. | The post-write incremental scan has the same cost profile as the post-edit hook's incremental scan; one knob governs both incremental paths coherently. | A dedicated `docs_lint.post_write_timeout_seconds` — rejected: unnecessary surface for an identical cost profile. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A write tool mutates a doc that a corpus-wide (cross-file) validator would flag, which `--changed` skips, so the post-write attachment misses it. | `--changed` runs per-file validators on the changed docs and falls back to full lint on a changed config file; the five lifecycle gates (prepare/close/validate/review/install) still run the full corpus, so nothing ships without a full-corpus pass. The post-write attachment is advisory, not a gate. |
| The write tool's mutations are not yet visible to `git` (e.g. written outside the working tree). | Write tools mutate files in place in the working tree; `_get_changed_files` sees unstaged changes. If a checkout is non-git or the set is empty, the safe `([], [])` no-op reports clean — acceptable for an advisory signal with full-corpus backstops. |
| Envelope consumers depend on the post-write lint reflecting the whole corpus. | The `{clean, error_count, warning_count, first_errors}` shape is unchanged (AC-4); consumers already treat it as advisory and decoupled from tool status; the semantic narrowing (changed-scope vs full) is the intended improvement and is documented. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
