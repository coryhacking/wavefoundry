# Bound every wf setup Phase-1 child with a per-step deadline and no-progress watchdog

Change ID: `1p9it-bug setup-phase1-child-deadlines`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-07-02
Wave: TBD

## Rationale

The entire `wf setup` Phase-1 child chain runs with **zero per-step deadline** and **zero heartbeat/watchdog**. Any one stalled child blocks the whole setup indefinitely; the operator's only recovery is a manual kill (or a reboot). This is the most plausible unexplained-mechanism behind the 1.9.8 native-Windows field reports of a reboot-needed post-Phase-1 hang and a ~4h stall at roughly step 2.3 (audit `wf_eab9a03d-004`; comparison `wf_33ca6bdb-757`).

Verified in the current tree (wave 1p9hn applied, line numbers re-confirmed):

- **Venv create** — `setup_index.py:210`: `subprocess_util.isolated_run([sys.executable, "-m", "venv", str(venv_dir)], check=True)`. No `timeout=`.
- **uv bootstrap** — `setup_index.py:353`: `subprocess_util.isolated_run([...pip install uv...], check=False, env=_pip_tls_env())`. No `timeout=`.
- **Dependency install** — `setup_index.py:401`: `result = subprocess_util.isolated_run(cmd, check=False, env=run_env)`. No `timeout=`. A stalled `uv`/`pip` PyPI fetch (corp MITM / flaky proxy) blocks forever.
- **Model warm (in-process)** — `setup_index.py:812-821` (`_warm_model` → `_build`): `embedding = TextEmbedding(model_name=..., local_files_only=..., providers=...)` then `next(iter(embedding.embed(["wavefoundry cache verification"])))`. This is a **bare in-process fastembed call with no deadline** — a hung TLS model fetch behind a corp MITM/flaky proxy stalls the whole process with no timeout and no abort. This is the primary hang candidate.
- **Index build (subprocess)** — `setup_index.py:1383` (`_run_indexer`): `proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, ...)`; the parent then blocks on `for line in proc.stdout:` (`setup_index.py:1398`) and `proc.wait()` (`setup_index.py:1402`) with **no no-progress watchdog** — a child that produces no output and never exits pins the parent forever.

The shared spawn helper `subprocess_util.isolated_run` (`subprocess_util.py:74-101`) fills only `stdin`/`creationflags`/UTF-8 capture defaults and **never injects a timeout** (it does, however, pass any `timeout=` the caller supplies straight through to `subprocess.run` via `**kwargs`, so the fix is at the call sites, not in the helper).

Net effect: a hung TLS model fetch or a stalled index-build child blocks setup indefinitely — no timeout, no progress deadline, no automatic abort, and no operator-actionable message. This change gives each Phase-1 stage a bounded, configurable deadline that fails loud with stage-specific guidance instead of hanging.

## Requirements

1. **Venv create + dependency install deadlines.** Pass a `timeout=` to the `isolated_run` spawns at `setup_index.py:210` (venv create), `setup_index.py:353` (uv bootstrap), and `setup_index.py:401` (dependency install). On `subprocess.TimeoutExpired`, fail loud with a stage-named, actionable message (network/proxy/TLS reachability to PyPI) rather than propagating a bare traceback or hanging.
2. **In-process model-warm deadline.** Give `_warm_model` / `_build` (`setup_index.py:812-821`) a bounded wall-clock deadline. Since `embedding.embed(...)` is an in-process call with no native timeout, run it under a watchdog (e.g. a daemon worker thread joined with a deadline, or an equivalent wall-clock enforcement) and abort with an actionable message (network/proxy/TLS reachability for the model download) when the deadline elapses.
3. **Index-build no-progress watchdog.** Add a no-progress watchdog to the `for line in proc.stdout:` stream in `_run_indexer` (`setup_index.py:1383`/`:1398`): if no output line arrives within a configured stall window, terminate the child (`terminate()` then `kill()` on escalation) and fail loud with a stage-named message (disk/CPU/memory for the index build). Preserve the existing line-by-line streaming and the existing exit-code handling (lock-conflict detection at `:1404`, SIGKILL/OOM handling at `:1424+`) on the success/normal-exit path.
4. **Configurable deadlines with sensible defaults.** Make each stage deadline (venv, deps, model-warm, index-build stall window) configurable via `docs/workflow-config.json` under a dedicated setup block, loaded with a helper analogous to `_workflow_project_include_prefixes` (`setup_index.py:1511`). Ship conservative defaults sized for slow-but-legit environments; missing/malformed config falls back to defaults (never raises).
5. **Actionable failure semantics.** Every timeout/abort message must name the stage that timed out and what to check for that specific stage. Timeout is a distinct, loud failure — not a silent hang and not an indistinguishable generic error.
6. **Preserve success behavior.** A normal, within-deadline setup run must behave exactly as today (same output, same exit code, same background-build spawn behavior). No new dependency; stdlib threading/subprocess only.

## Scope

**Problem statement:** `wf setup` Phase-1 spawns four child stages (venv create, dependency install, in-process model warm, index build) with no per-step deadline and no heartbeat/watchdog. Any stalled child — most plausibly a hung TLS model fetch or a stalled index-build child on native Windows behind a corp proxy — blocks setup indefinitely with no timeout, no progress deadline, and no automatic abort, leaving a manual kill as the only recourse.

**In scope:**

- Per-step `timeout=` on the venv-create (`:210`), uv-bootstrap (`:353`), and dep-install (`:401`) `isolated_run` spawns, with loud actionable timeout handling.
- A bounded wall-clock deadline (watchdog thread or equivalent) around the in-process model warm at `_warm_model`/`_build` (`:812-821`), with loud actionable abort.
- A no-progress stdout watchdog in `_run_indexer` (`:1383`/`:1398`) that detects a stalled index-build child and terminates + kills it, with loud actionable failure.
- A `docs/workflow-config.json` setup-deadlines block (with defaults) plus a loader in `setup_index.py`.
- Unit tests for each deadline path (timeout triggers abort + correct message; within-deadline path unchanged; config override respected; missing config → defaults).
- Documenting the new workflow-config keys in the workflow-config reference doc.

**Out of scope:**

- Changing `subprocess_util.isolated_run`/`isolated_popen` internals (they already pass `timeout=` through; no helper change required beyond confirming passthrough).
- Deadlines for stages outside `wf setup` Phase-1 (upgrade pipeline, dashboard watcher, background/detached index builds, MCP-triggered builds).
- Retry/backoff logic, resumable setup, or partial-progress checkpointing.
- The separate CA-bundle / TLS trust-ladder behavior (`_warm_model`'s CA retry loop) — untouched except that its overall in-process attempt is now deadline-bounded.
- Any change to embedding precision, provider selection, OOM/SIGKILL handling, or lock-conflict semantics.

## Acceptance Criteria

- [ ] AC-1: The venv-create (`:210`), uv-bootstrap (`:353`), and dep-install (`:401`) spawns each pass a `timeout=`; a simulated `subprocess.TimeoutExpired` from those spawns produces a loud, stage-named failure message referencing network/proxy/TLS reachability, verified by unit test.
- [ ] AC-2: The in-process model warm (`_warm_model`/`_build`, `:812-821`) is bounded by a wall-clock deadline; a simulated over-deadline `embed(...)` triggers an abort with a stage-named message referencing model-download network/proxy/TLS, verified by unit test (no reliance on a real network fetch).
- [ ] AC-3: `_run_indexer` (`:1383`/`:1398`) terminates and kills a child that emits no output within the configured stall window and fails loud with a stage-named message referencing disk/CPU/memory, verified by unit test with a stub/no-output child; the child is confirmed reaped (no orphan).
- [ ] AC-4: Each stage deadline is read from `docs/workflow-config.json` (setup block) with a documented default; an override in a fixture config is honored and a missing/malformed config falls back to defaults without raising, verified by unit test.
- [ ] AC-5: A within-deadline (normal) setup run is behaviorally unchanged — same streamed output, same exit code, same background-build spawn — verified by the existing setup tests staying green plus a within-deadline regression assertion.
- [ ] AC-6: `python3 .wavefoundry/framework/scripts/run_tests.py` passes; `wave_validate` (docs-lint) is clean after the workflow-config reference-doc update.

## Tasks

- [ ] Add a workflow-config loader for setup deadlines (helper next to `_workflow_project_include_prefixes` at `:1511`), with default constants for venv, deps, model-warm, and index-build stall window; malformed/missing config → defaults.
- [ ] Pass `timeout=` to `isolated_run` at `:210`, `:353`, and `:401`; wrap each in `try/except subprocess.TimeoutExpired` and raise/exit with a stage-named, actionable (network/proxy/TLS) message.
- [ ] Wrap `_warm_model`/`_build` (`:812-821`) in a wall-clock deadline (daemon worker thread joined with timeout, or equivalent); on deadline, abort with a stage-named model-download-reachability message. Ensure the existing CA-retry loop still runs inside the bounded attempt.
- [ ] Add a no-progress watchdog around the `for line in proc.stdout:` loop in `_run_indexer` (`:1398`): reset the deadline on each line; on stall, `proc.terminate()` then escalate to `proc.kill()`, drain/join, and fail loud with a disk/CPU/memory message. Preserve the existing exit-code/lock-conflict/OOM handling for normal exits.
- [ ] Add unit tests: each timeout path (venv/deps/model/index) fires and emits the correct stage message; within-deadline path unchanged; config override honored; missing config → defaults; stalled index child is reaped.
- [ ] Document the new `docs/workflow-config.json` setup-deadline keys (defaults + meaning) in the workflow-config reference doc.
- [ ] Run `python3 .wavefoundry/framework/scripts/run_tests.py` and `wave_validate`; fix any failures.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ----------------------------------- | ----------- | ------------ | ------------------------------------------------------------------------------------------------- |
| ws1-config-loader | implementer | —            | Setup-deadline loader + default constants in `setup_index.py` (helper mirrors `:1511`); no other stage may hardcode a deadline. |
| ws2-spawn-timeouts | implementer | ws1-config-loader | `timeout=` + `TimeoutExpired` handling at `:210`, `:353`, `:401`. |
| ws3-model-warm-deadline | implementer | ws1-config-loader | Wall-clock watchdog around `_warm_model`/`_build` (`:812-821`). |
| ws4-index-build-watchdog | implementer | ws1-config-loader | No-progress stdout watchdog + terminate/kill in `_run_indexer` (`:1383`/`:1398`). |
| ws5-tests-and-docs | implementer | ws2-spawn-timeouts, ws3-model-warm-deadline, ws4-index-build-watchdog | Unit tests for every path + workflow-config reference-doc keys; run suite + `wave_validate`. |


## Serialization Points

- `.wavefoundry/framework/scripts/setup_index.py` is edited by ws1–ws4 — a single shared file. Land ws1 (config loader + default constants) first; ws2/ws3/ws4 then edit disjoint functions (`_bootstrap_venv`/`_bootstrap_uv`/`_install_deps`, `_warm_model`, `_run_indexer`) and must not each introduce their own hardcoded deadline constant.
- `docs/workflow-config.json` schema keys and the workflow-config reference doc: ws1 defines the keys, ws5 documents them — coordinate the key names before ws5 writes the doc.
- ws5's tests depend on the abort/message contracts finalized in ws2/ws3/ws4; those message strings are the test oracle and must be settled before test authoring.

## Affected Architecture Docs

N/A for the architecture hub and child docs. The change is confined to `setup_index.py`'s Phase-1 orchestration: it adds bounded deadlines, a no-progress watchdog, and a config surface, but introduces no new module boundary and no new control-flow between components. The only doc update is the new `docs/workflow-config.json` setup-deadline keys in the workflow-config reference (captured as an in-scope task), which is a schema/reference update, not an architecture-boundary or data-flow change.

## AC Priority

(Populated at Prepare wave.)


| AC | Priority | Rationale |
| ---- | --------- | ---------------------------------------------------------------------------------------------------------- |
| AC-1 | required | Dep-install/venv hangs are a direct Phase-1 stall path; bounding them is core to the fix. |
| AC-2 | required | In-process model warm is the primary unbounded-hang candidate behind the field defect (TLS model fetch). |
| AC-3 | required | Stalled index-build child matches the ~4h stall-at-step-2.3 report; the no-progress watchdog is core. |
| AC-4 | important | Configurability lets slow-but-legit environments raise deadlines instead of hitting a false timeout; defaults ship the safety net without it. |
| AC-5 | required | Preserving success behavior is a hard non-regression gate — a bad deadline that trips on healthy runs is worse than the hang. |
| AC-6 | required | Suite + docs-lint green is the standing merge gate for framework code. |


## Progress Log


| Date | Update | Evidence |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| 2026-07-02 | Scoped from the native-Windows install audit; verified all five cited sites in the 1p9hn-applied tree and corrected line numbers. | Audit `wf_eab9a03d-004`; comparison `wf_33ca6bdb-757`; `setup_index.py:210,353,401,812-821,1383,1398,1402`; `subprocess_util.py:74-101` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---------- | -------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------- |
| 2026-07-02 | Fix at the call sites, not in `subprocess_util.isolated_run`. | `isolated_run` already passes `timeout=` through `**kwargs`; adding a helper default would silently affect every unrelated spawn across the framework. | Inject a default `timeout=` in `isolated_run` (rejected: over-broad blast radius). |
| 2026-07-02 | Bound the in-process model warm with a watchdog thread / wall-clock deadline. | `fastembed`'s `TextEmbedding`/`embed` is a synchronous in-process call with no native timeout parameter, so a subprocess-style `timeout=` is not available. | Move the warm into a subprocess purely to get a `timeout=` (rejected: larger change, out of scope). |
| 2026-07-02 | Use a no-progress (idle-output) watchdog for the index build, not a fixed total cap. | Legit large-repo builds can run long but keep emitting progress lines; a fixed total cap would false-trip while an idle-stall watchdog targets the actual hang. | Fixed total wall-clock cap on the index build (rejected: false timeouts on big repos). |
| 2026-07-02 | Deadlines configurable via `docs/workflow-config.json` with defaults. | Slow-but-legit environments (corp proxy, low-RAM WSL2) must be able to raise limits without editing framework code. | Hardcode deadlines (rejected: no field escape hatch). |


## Risks


| Risk | Mitigation |
| --------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| A too-tight default deadline false-trips on slow-but-legit environments (corp proxy, low-RAM WSL2). | Ship conservative defaults; make every deadline configurable via workflow-config; AC-5 regression-asserts the healthy within-deadline path is unchanged. |
| Index-build watchdog kill leaves an orphan/zombie child on Windows. | Terminate then escalate to kill, drain the stream, and join; AC-3 explicitly asserts the child is reaped (no orphan). |
| Watchdog thread for the in-process model warm cannot truly interrupt a blocked native fastembed call. | Use a daemon worker thread joined with a deadline so the abort path returns control and fails loud even if the underlying native call is still parked; document that the process may need to be exited on the abort path rather than resumed. |
| New workflow-config keys drift from the reference doc. | ws1 defines the keys and ws5 documents them in the same wave; `wave_validate`/docs-lint gates the doc; key names are settled at a serialization point before ws5 writes. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
