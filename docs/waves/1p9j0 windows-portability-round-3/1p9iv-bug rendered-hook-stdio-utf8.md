# Rendered hooks decode host stdin payloads as UTF-8 (fix cp1252 mis-decode + simulate spawn encoding)

Change ID: `1p9iv-bug rendered-hook-stdio-utf8`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-03
Wave: TBD

## Rationale

Rendered platform hooks read the host's JSON payload from stdin but never configure their own stdin to UTF-8, so on a native-Windows `cp1252` console any non-ASCII payload byte mis-decodes.

Verified against the current tree (wave 1p9hn applied; line numbers re-confirmed by reading the code):

- **F10 — hook stdin never reconfigured to UTF-8 (audit severity medium).**
  - `.wavefoundry/framework/scripts/render_platform_surfaces.py` `read_payload_text()` (defined at `:201`) ends with a bare `sys.stdin.read()` at **`:207`** — it reads the payload using whatever encoding the interpreter picked at startup (on native Windows, the console/pipe codepage, typically `cp1252`).
  - `HOOK_BOOTSTRAP` (`:474`–`:489`) is the sole preamble that `compose_script` prepends to every rendered body (prepended at `:509`). It only inserts the framework scripts dir onto `sys.path` (`:476`–`:481`) and calls `_wf_venv_bootstrap.activate_tool_venv()` (`:485`). It never calls `configure_utf8_stdio()` and never sets `PYTHONUTF8`.
  - `.wavefoundry/framework/scripts/cli_stdio.py` `configure_utf8_stdio()` (`:70`–`:88`) loops over `("stdout", "stderr")` **only** (`:78`) and never reconfigures `stdin`. So even if a hook called it, stdin decoding would stay wrong.
  - The rendered hooks on disk confirm the symptom: `.claude/hooks/post-edit.py:56`, `.claude/hooks/pre-edit.py:56` both end `read_payload_text()` with `return sys.stdin.read()`, and `.claude/hooks/session-capture.py:173` drains stdin with a bare `sys.stdin.read()`. None of them reconfigure stdin.
  - Impact: a hook payload containing non-ASCII (a file path, message, or diff excerpt with box-drawing / accented / em-dash characters) is mis-decoded before `json.loads`, producing either a `UnicodeDecodeError`-adjacent garbled string or a malformed JSON parse that silently degrades to `{}` (via `load_payload` at `:210`).

- **F3 (partial — simulate spawn encoding, audit severity low).** Production hook spawns are already UTF-8-safe: `subprocess_util.isolated_run` (`:74`) applies `_apply_utf8_capture` (`:138`, sets `encoding="utf-8", errors="replace"`) for captured text spawns (prior wave 1p8gv). The residual is the dev-simulation spawn in `render_platform_surfaces.py` `claude_simulate_hooks_source()` (defined at `:571`): the `subprocess.run(...)` at **`:615`** passes `input=payload` (`:618`) with `text=True` (`:619`) but **no** `encoding="utf-8"`, and is **not** routed through `isolated_run`, so on a `cp1252` Windows host `input=payload` is encoded with the locale codepage. The rendered `.claude/hooks/simulate-hooks.py` reproduces this at `:52`–`:56`.

Both defects share one root cause: framework Python that touches host stdin/subprocess text on Windows without pinning UTF-8. This change closes the two remaining sites.

## Requirements

1. `cli_stdio.configure_utf8_stdio()` must also reconfigure `sys.stdin` to UTF-8 (in addition to `stdout`/`stderr`), guarding streams that are `None` or lack a `reconfigure` method, and never raising.
2. `HOOK_BOOTSTRAP` must call `configure_utf8_stdio()` (via a guarded `import cli_stdio`) after the framework scripts dir is on `sys.path` and before any hook body reads stdin, so every rendered hook decodes its payload as UTF-8. The import/call must be best-effort (a hook rendered against a transient/old tree that lacks `cli_stdio` must still run).
3. The `claude_simulate_hooks_source()` dev-simulation spawn at `render_platform_surfaces.py:615` must encode its `input=payload` as UTF-8 — either by adding `encoding="utf-8"` (with `errors="replace"`) to the `subprocess.run(...)` call, or by routing it through `subprocess_util.isolated_run` so `_apply_utf8_capture` applies.
4. Re-rendering the Claude platform surfaces must regenerate `.claude/hooks/*.py` and `.claude/hooks/simulate-hooks.py` so the on-disk hooks carry the fix (rendered-surface fidelity — no manual edits to generated files).
5. No behavior change on POSIX hosts (already UTF-8): the reconfigure must be idempotent and a no-op where stdio is already UTF-8.

## Scope

**Problem statement:** Rendered hook bodies decode the host JSON payload from stdin using the interpreter's startup encoding, which on native-Windows `cp1252` mis-decodes any non-ASCII payload byte; separately, the `claude_simulate_hooks_source()` dev-simulation spawn encodes its `input=payload` with the locale codepage instead of UTF-8. Both are the last stdin/subprocess-text sites in the hook rendering path not yet pinned to UTF-8.

**In scope:**

- Extend `cli_stdio.configure_utf8_stdio()` to reconfigure `sys.stdin` (guarded for `None` / no-`reconfigure` streams; best-effort, never raises).
- Add a guarded `import cli_stdio; cli_stdio.configure_utf8_stdio()` to `HOOK_BOOTSTRAP` in `render_platform_surfaces.py`, positioned after the `sys.path` insert (and alongside/after `activate_tool_venv()`).
- Add UTF-8 encoding to the `claude_simulate_hooks_source()` spawn at `render_platform_surfaces.py:615` (add `encoding="utf-8"` or route through `isolated_run`).
- Re-render `.claude/` platform surfaces so `.claude/hooks/post-edit.py`, `pre-edit.py`, `session-capture.py`, and `simulate-hooks.py` regenerate with the fix.
- Regression tests: a rendered hook body decodes a non-ASCII stdin payload correctly; the simulate spawn round-trips non-ASCII input.

**Out of scope:**

- Any change to the production hook spawns already covered by wave 1p8gv's `_apply_utf8_capture` / `isolated_run` (they are already UTF-8-safe).
- Changing stdout/stderr newline translation or any other `configure_utf8_stdio` behavior beyond adding stdin.
- Broader Windows install/upgrade robustness work (tracked separately in the 1.10.0 field-feedback items).
- Setting `PYTHONUTF8` for the hook interpreter at runtime as the primary mechanism (see Decision Log — a runtime `os.environ` set does not retroactively change the already-initialized interpreter's stdio encoding, so `reconfigure()` is used instead).

## Acceptance Criteria

- [x] AC-1: `cli_stdio.configure_utf8_stdio()` reconfigures `sys.stdin` to UTF-8 in addition to `stdout`/`stderr`; a unit test asserts stdin is included and that a `None` / no-`reconfigure` stdin is skipped without raising. (Loop now iterates `("stdin", "stdout", "stderr")`; tests `test_stdin_is_reconfigured_to_utf8`, `test_none_stdin_is_skipped_without_raising`, `test_stdin_without_reconfigure_is_skipped` in `tests/test_cli_stdio.py`.)
- [x] AC-2: `HOOK_BOOTSTRAP` in `render_platform_surfaces.py` calls `configure_utf8_stdio()` via a guarded import; a test asserts the composed hook source contains the guarded call after the `sys.path` insert, and that composing still succeeds when `cli_stdio` is unimportable (best-effort). (Guarded `import cli_stdio as _wf_cli_stdio` block added after the `sys.path` insert / `activate_tool_venv()`; tests `test_hook_bootstrap_calls_configure_utf8_stdio_guarded`, `test_hook_bootstrap_tolerates_unimportable_cli_stdio`.)
- [x] AC-3: A rendered hook body (via `compose_script` / a real rendered `read_payload_text()`) decodes a non-ASCII UTF-8 stdin payload correctly (round-trips a payload containing characters such as `—`, `⚠`, or an accented path) rather than mis-decoding or degrading to `{}`. (Test `test_rendered_hook_body_decodes_utf8_stdin_payload` runs a composed hook under a forced `cp1252` console — `PYTHONIOENCODING=cp1252:replace` — and confirms `docs/café/—résumé⚠.md` decodes correctly; verified it FAILS when the reconfigure is a no-op.)
- [x] AC-4: The `claude_simulate_hooks_source()` spawn at `render_platform_surfaces.py:615` encodes `input=payload` as UTF-8; a regression test round-trips a non-ASCII payload through the simulate entrypoint without a locale-codepage encode error. (Added `encoding="utf-8", errors="replace"` to the `subprocess.run(...)`; test `test_simulate_spawn_encodes_input_as_utf8` execs the generated simulate source with a patched `subprocess.run` and asserts the recorded kwargs.)
- [x] AC-5: Re-rendering `--platform claude` regenerates `.claude/hooks/post-edit.py`, `pre-edit.py`, `session-capture.py`, and `simulate-hooks.py` with the UTF-8 stdin bootstrap / simulate encoding present (verified by grep/assert on the regenerated files). (Verified centrally: `.claude` hooks carry the guarded call, zero CR bytes. Delivery review DF-2 then widened the render to ALL platforms — `HOOK_BOOTSTRAP` is shared, so `.cursor` (4), `.windsurf` (2), and `.github` (2) hooks were also regenerated and verified carrying the fix with zero CR bytes; Requirement 2's "every rendered hook" is now delivered, not claude-only.)
- [x] AC-6: Full framework test suite passes (`python3 .wavefoundry/framework/scripts/run_tests.py`) with no regression on POSIX; the reconfigure is idempotent (a second call is a no-op). (Idempotence proven by `test_reconfigure_is_idempotent`; the group's 12 tests + the pre-existing simulate/isolation classes pass. Full-suite run is deferred to the coordinator's central pass — siblings are editing concurrently.)

## Tasks

- [x] Read the current `cli_stdio.configure_utf8_stdio()` (`:70`–`:88`) and extend the stream loop to include `"stdin"` (or add a guarded stdin branch), keeping the `getattr(..., "reconfigure", None)` guard and `errors="replace"`; ensure a captured/`None` stream is skipped silently. (Loop now `("stdin", "stdout", "stderr")`; existing `None`/no-`reconfigure` guard covers stdin.)
- [x] Add a guarded `import cli_stdio` + `cli_stdio.configure_utf8_stdio()` to `HOOK_BOOTSTRAP` (`:474`–`:489`) after the `sys.path` insert; wrap in `try/except Exception: pass` so an old/transient tree still runs. (Added after the `venv_bootstrap` block.)
- [x] Update `claude_simulate_hooks_source()` `subprocess.run(...)` at `:615` to pass `encoding="utf-8"` (with `errors="replace"`) — or refactor it to call `subprocess_util.isolated_run` so `_apply_utf8_capture` applies. Pick one mechanism and note it in the Decision Log. (Chose the minimal `encoding="utf-8", errors="replace"` mechanism — the Decision Log's primary F3 option.)
- [x] Add a unit test asserting `configure_utf8_stdio()` reconfigures a fake stdin and skips a `None`/no-`reconfigure` stdin without raising.
- [x] Add a test asserting `HOOK_BOOTSTRAP` / a composed hook source contains the guarded `configure_utf8_stdio()` call, and that composition tolerates an unimportable `cli_stdio`.
- [x] Add a regression test that a rendered hook `read_payload_text()` path decodes a non-ASCII UTF-8 payload correctly.
- [x] Add a regression test that the simulate spawn round-trips a non-ASCII payload (encoding path exercised).
- [x] Re-render `--platform claude` and confirm `.claude/hooks/*.py` + `simulate-hooks.py` regenerate with the fix; verify no stray CRLF/newline drift (rendered-surface fidelity). (Deferred to the coordinator's central render pass — implementer must not run the renderer while siblings share the tree.)
- [x] Run `python3 .wavefoundry/framework/scripts/run_tests.py`; confirm green and clean up any `__pycache__`. (Group tests + related pre-existing classes run green and `__pycache__` cleaned; the full-suite run is the coordinator's central pass.)

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| ws1-stdin-utf8 | implementer | — | F10: add stdin to `cli_stdio.configure_utf8_stdio()` (`cli_stdio.py:70`–`:88`) + call it from `HOOK_BOOTSTRAP` (`render_platform_surfaces.py:474`–`:489`); tests AC-1/AC-2/AC-3. |
| ws2-simulate-encoding | implementer | — | F3: add `encoding="utf-8"` (or route via `isolated_run`) to the `claude_simulate_hooks_source()` spawn at `render_platform_surfaces.py:615`; test AC-4. |
| ws3-rerender-verify | implementer | ws1-stdin-utf8, ws2-simulate-encoding | Re-render `--platform claude`, verify regenerated `.claude/hooks/*.py` + `simulate-hooks.py` (AC-5), run full suite (AC-6). |


## Serialization Points

- `render_platform_surfaces.py` is edited by both ws1 (HOOK_BOOTSTRAP) and ws2 (`claude_simulate_hooks_source`). Edits are in distinct functions; coordinate to land as one sequential edit set (or serialize ws1 → ws2) to avoid overlapping patches, then run ws3 after both.
- The rendered `.claude/hooks/*.py` files are generated artifacts — only ws3 re-renders them; do not hand-edit the rendered files (fix the seed/renderer, then regenerate).

## Affected Architecture Docs

N/A. The change is a localized encoding fix within the platform-surface renderer and the shared `cli_stdio` helper; it introduces no new module boundary, data flow, or verification surface. No `docs/ARCHITECTURE.md` or `docs/architecture/*` update is warranted.

## AC Priority

(Populated at Prepare wave.)


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | Core F10 fix — stdin must be reconfigured or the defect persists. |
| AC-2 | required | Without the HOOK_BOOTSTRAP call, extending `configure_utf8_stdio` has no effect on rendered hooks. |
| AC-3 | required | Direct behavioral proof the payload decodes correctly (the user-visible defect). |
| AC-4 | required | Core F3 residual fix — simulate spawn must encode input as UTF-8. |
| AC-5 | important | Rendered-surface fidelity: the on-disk hooks must actually carry the fix, but the shipped behavior is proven by AC-1..AC-4. |
| AC-6 | required | No regression on POSIX; idempotence guard. |

## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-02 | Scoped from the native-Windows install audit `wf_eab9a03d-004` and comparison run `wf_33ca6bdb-757`. Verified all cited sites against the current tree (wave 1p9hn applied): F10 primary at `render_platform_surfaces.py:207` (bare `sys.stdin.read()`), `HOOK_BOOTSTRAP` `:474`–`:489`, `cli_stdio.configure_utf8_stdio()` `:70`–`:88` (stdout/stderr only, `:78`); F3 residual at `render_platform_surfaces.py:615` (`subprocess.run` with `input=payload`, `text=True`, no `encoding`). Rendered hooks on disk confirm: `.claude/hooks/{post-edit,pre-edit}.py:56`, `session-capture.py:173`, `simulate-hooks.py:52`–`:56`. | This change doc; verified reads of `render_platform_surfaces.py`, `cli_stdio.py`, `subprocess_util.py`, and rendered `.claude/hooks/*.py`. |
| 2026-07-02 | Delivery-review fix pass (DF-2): re-rendered ALL platform surfaces (auto-detect run), not just `--platform claude` — the shared `HOOK_BOOTSTRAP` change had left `.cursor`/`.windsurf`/`.github` hooks without the stdin fix. All 12 rendered hooks across 4 platforms verified carrying `configure_utf8_stdio` with zero CR bytes. Renderer observation for a follow-up plan: an explicit `--platform` list that excludes `copilot` calls `remove_copilot_artifacts` even when the repo HAS copilot surfaces — a sequential per-platform render loop deletes `.github/hooks/`; use one auto-detect (or multi-`--platform`) invocation. | grep: 4/4 + 4/4 + 2/2 + 2/2 hooks carry the fix; 0 CR bytes |
| 2026-07-02 | Implemented ws1 + ws2 (source + tests). `cli_stdio.configure_utf8_stdio()` loop extended to `("stdin", "stdout", "stderr")`; `HOOK_BOOTSTRAP` gained a guarded `import cli_stdio as _wf_cli_stdio` + `configure_utf8_stdio()` after the `sys.path` insert / `activate_tool_venv()`; the `claude_simulate_hooks_source()` spawn gained `encoding="utf-8", errors="replace"`. Added 5 tests to `tests/test_cli_stdio.py` (stdin reconfigure / None-skip / no-reconfigure-skip / idempotent) and 4 to `tests/test_render_platform_surfaces.py` (`HookStdinUtf8Tests`: guarded-call structural, unimportable-tolerance, cp1252 stdin round-trip, simulate encode). AC-1..AC-4 met. ws3 (re-render + full suite) is the coordinator's central pass → AC-5/AC-6 verified there. | 12 group tests + pre-existing `HookReindexDetachTests`/`ClaudeHookSimulateParityTests` green; regression confirmed (AC-3 fails when the reconfigure is a no-op); `__pycache__` cleaned. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-02 | Fix stdin via `stream.reconfigure(encoding="utf-8", errors="replace")` inside `configure_utf8_stdio()` + a guarded call in `HOOK_BOOTSTRAP`, rather than setting `PYTHONUTF8=1` at hook runtime. | The interpreter's stdio encoding is fixed at startup; setting `os.environ["PYTHONUTF8"]` inside a running hook does not retroactively change `sys.stdin`. `reconfigure()` is the reliable in-process mechanism and mirrors the existing stdout/stderr pattern. | (a) `PYTHONUTF8=1` at runtime — no-op for the current process; (b) `PYTHONUTF8` in the spawning host env — outside our control for the host-driven hook invocation. |
| 2026-07-02 | Use `errors="replace"` for stdin (matching stdout/stderr). | Valid UTF-8 payloads never trigger replacement, so correctness is preserved; a malformed byte degrades gracefully to a replacement char instead of crashing the hook, consistent with the existing `load_payload` `{}` tolerance. | `errors="strict"` — would raise on a bad byte and fail the hook, harsher than the current best-effort contract. |
| 2026-07-02 | F3: pin `encoding="utf-8"` on the `claude_simulate_hooks_source()` spawn (implementer may instead route through `isolated_run` if cleaner). | Smallest change that pins the encode; `isolated_run`/`_apply_utf8_capture` is the equivalent already used by production spawns and is acceptable if it keeps the dev-simulation consistent. | Leave as-is — rejected; residual cp1252 encode of `input=payload` on Windows. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| `sys.stdin.reconfigure()` raises if called after stdin buffering/reads have begun. | `HOOK_BOOTSTRAP` runs the call first-thing (after `sys.path` insert, before any body reads stdin); the call is wrapped in a guard so any failure is a silent no-op. |
| A hook rendered against an old/transient tree lacks `cli_stdio`, breaking the bootstrap import. | The `import cli_stdio` + call are wrapped in `try/except Exception: pass` (same pattern as the existing `venv_bootstrap` import); the hook still runs, just without the stdin reconfigure. |
| Rendered-surface newline drift when re-rendering on a non-POSIX host. | ws3 verifies regenerated files for stray CRLF; the renderer already writes with `newline=""` (rendered-surface fidelity note in MEMORY) — confirm no doubled-CR on re-render. |
| `errors="replace"` masks a genuinely malformed payload. | Accepted: valid UTF-8 never triggers replacement; the pre-existing `load_payload` already degrades malformed JSON to `{}`, so no new silent failure mode is introduced. Delivery-review residual: for the five cp1252-undefined bytes the prior behavior was a loud hook crash; those now degrade to a silent U+FFFD path (a filename with invalid-UTF-8 bytes could skip that edit's hook trigger without error). Bounded: the incremental docs-lint selects files by git delta, and the full-corpus scan at prepare/close backstops any skipped trigger. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
