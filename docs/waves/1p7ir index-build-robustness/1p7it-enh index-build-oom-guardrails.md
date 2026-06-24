# Index-build OOM guardrails: auto-scaled buffer, sequential-degrade, loud failure

Change ID: `1p7it-enh index-build-oom-guardrails`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-23
Wave: `1p7ir index-build-robustness`

## Rationale

On a CPU-only, ~15 GiB WSL2 host, the 1.8.0 index build OOM-killed the code embedding pass (~14 GiB RSS at file ~300/811) and the failure was invisible: the child `indexer.py --content all` died with SIGKILL while the wrapper looked success-ish, and the dashboard auto-index re-triggered the same `--content all` (`dashboard_server.py:254`) toward a re-kill loop.

Per-layer streaming already exists (`_StreamingLayerWriter`; `_resolve_embed_buffer_chunks`, floored at `EMBED_BATCH_SIZE`), so the lever is present — but the shipped `embed_buffer_chunks` default is too aggressive for CPU/low-RAM, and `--content all` keeps docs+code+secrets+graph pipelines resident concurrently. The operator’s working mitigation: `embed_buffer_chunks` 256→48 **and** sequential `--content docs` then `--content code` → peak RSS ~8.8 GiB.

## Requirements

1. **~~Auto-scale the embed buffer~~ — removed by measurement.** The on-machine benchmark (Progress Log 2026-06-23) showed `embed_buffer_chunks` has no effect on peak RSS on either provider, so deriving it from the memory limit cannot prevent the OOM. The buffer remains an explicit throughput knob (`indexing.embed_buffer_chunks`), but the memory lever is sequential-degrade (req 2) plus the CPU-footprint reduction in `1p7iv`.
2. **(Primary fix) Sequential-degrade on a constrained profile.** Detect CPU-only (the `wave_gpu_doctor` selection path) + a low-memory probe, and run the layers as **sequential passes** instead of concurrent `--content all` — including the dashboard auto-index trigger. A non-constrained host keeps current behavior.
3. **Fail loudly on child SIGKILL.** When the child indexer dies with SIGKILL (signal 9), the wrapper/upgrade must surface a clear "out-of-memory during code embedding" error with remediation (lower buffer / sequential / raise WSL `.wslconfig` memory) instead of returning success-ish.
4. **Break the auto-index re-kill loop.** After an OOM-killed build, the dashboard auto-index must not immediately re-trigger the same failing `--content all` (back off / require explicit rebuild).

## Scope

**Problem statement:** The build’s peak memory + concurrency OOM-kill the code pass on constrained hosts, and the kill is swallowed (looks like success) + retried in a loop.

**In scope:**

- `_resolve_embed_buffer_chunks` (memory-aware default) in `indexer.py`.
- The constrained-profile detection + sequential-pass degrade (build orchestration + `dashboard_server.py` auto-index).
- SIGKILL detection + loud remediation in the wrapper/upgrade path.
- Tests for buffer auto-scaling, the constrained-profile decision, and the SIGKILL surfacing.

**Out of scope:**

- The health-honesty fix (`1p7is`) — the other half of making the failure visible.
- Root-cause memory bounding so RSS doesn’t scale with corpus (`1p7iv`); this change mitigates via buffer + sequencing, `1p7iv` profiles the working set.

## Acceptance Criteria

- [~] AC-1: **Removed by measurement — `embed_buffer_chunks` is not auto-scaled.** The on-machine benchmark (Progress Log 2026-06-23) showed buffer size has no effect on peak RSS on either provider (GPU ~1.7 GiB, CPU ~13–15 GiB, flat/non-monotonic across 64–2048) and is corpus-independent; the field operator's `256→48` was floored to 256 and a no-op. Auto-scaling the buffer cannot prevent the OOM, so it is dropped in favor of AC-2 (sequential-degrade) and `1p7iv` (CPU-footprint reduction).
- [~] AC-2: **Superseded by `1p7iv` for the in-scope hosts — deferred.** The profiling (1p7iv) showed the build's peak is a *single* forward batch's activations, and `1p7iv`'s batch-32 default bounds each embedding pass to ~3.5 GiB — so even concurrent docs+code (separate processes) peaks ~7 GiB, comfortably under the ~15 GiB field host. Sequential-degrade would only help sub-~8 GiB hosts (not in the reported scope); it's narrow defense-in-depth now, deferred unless such a host is reported (would re-open as its own change). The constrained-profile cgroup/WSL detection ships with it when needed.
- [x] AC-3: a child SIGKILL (signal 9) surfaces an **OOM-specific** error with remediation (lower `code/docs_embed_batch_size`, sequential `--content`, raise WSL2 `.wslconfig` memory) in `setup_index._run_indexer`; the build raises (never reports success). Background-build OOMs are now also visible via `1p7is` health + the cleanup BEHIND check.
- [x] AC-4: **re-scoped (operator) — the dashboard is a read-only viewer; the index-trigger was removed entirely.** The `auto_index`/`auto_index_delay_seconds` settings and the whole `IndexBuilder` class were **deleted** from the dashboard; it never triggers builds. Index updates are owned by the MCP/hook background path (post-edit hook → `indexer.py`, the MCP server's `_start_background_index_refresh`, `wave_index_build`). The dashboard's build-status display reads the **shared** state (`collect_health` → `wave_index_build_status_response` — the hook/MCP builds). The re-kill loop is now structurally impossible (no dashboard build to loop), so the OOM back-off band-aid was reverted. ~27 obsolete dashboard tests removed; suite 3409 OK.
- [x] AC-5: value gate met by the `1p7iv` measurement — batch-32 bounds the embedding pass to ~3.5 GiB (field host ~14 → ~3.5 GiB), well under the cap, code pass completing; recorded in the `1p7iv` Progress Log.
- [x] AC-6: tests cover the viewer-only default (`test_auto_index_defaults_disabled`, incl. the opt-in) and the `setup_index` OOM-kill message path; bytecode-free; `wave_validate` clean. (Buffer-autoscale + constrained-profile tests dropped with AC-1/AC-2.)
- [x] AC-7: the unset `embed_buffer_chunks` default is **1024** (best build throughput in the benchmark — fastest + lowest of 64/128/256/1024/2048; peak RSS is buffer-invariant so this is purely a throughput choice), decoupled from `SORT_WINDOW_SIZE`; pinned by `test_resolve_embed_buffer_chunks_override_and_floor`.

## Tasks

- [~] Make `_resolve_embed_buffer_chunks` memory-aware — **dropped (measurement: buffer has no RSS effect; see AC-1)**. CPU-footprint reduction moves to `1p7iv`.
- [~] Add constrained-profile detection + sequential-pass degrade — **deferred with AC-2** (superseded by `1p7iv`'s batch-32 default for in-scope hosts).
- [x] Detect child SIGKILL → OOM-specific remediation in `setup_index._run_indexer` (AC-3); add dashboard auto-index OOM back-off (AC-4).
- [x] Tests (dashboard OOM back-off + signal-kill raise) bytecode-free; the constrained-host peak-RSS measurement is the `1p7iv` batch sweep.

## Agent Execution Graph


| Workstream         | Owner       | Depends On | Notes                                              |
| ------------------ | ----------- | ---------- | -------------------------------------------------- |
| buffer-autoscale   | implementer | —          | memory-aware `_resolve_embed_buffer_chunks`        |
| sequential-degrade | implementer | —          | CPU-only + mem probe; build + dashboard auto-index |
| loud-failure       | implementer | —          | SIGKILL surfacing + auto-index back-off            |
| value-gate         | reviewer    | all above  | constrained-host peak-RSS measurement              |


## Serialization Points

- Pairs with `1p7is` (health honesty) — both needed for the OOM to be visible end-to-end.
- Coordinates with `1p7iv` on the memory model (this change is the mitigation; `1p7iv` is the root-cause bound) — avoid double-counting the same fix.

## Affected Architecture Docs

- **Update if present:** the indexing/build architecture doc — the memory-aware default + constrained-profile sequential degrade + the failure-surfacing contract. Confirm scope at Prepare.

## AC Priority

(Populated at Prepare wave — proposed below.)


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | Was the primary mitigation; **dropped to `[~]` by measurement** — `embed_buffer_chunks` has no RSS effect on either provider (see the AC-1 inline note). |
| AC-2 | required  | Sequential-degrade — **deferred to `[~]`**: `1p7iv`'s batch-32 default already bounds each pass to ~3.5 GiB, so it's narrow defense-in-depth for sub-8 GiB hosts (out of reported scope). |
| AC-3 | required  | Loud failure is half of making the OOM visible (with `1p7is`). |
| AC-4 | important | Stops the re-kill loop. |
| AC-5 | required  | Real-host value gate — ship only on a bounded-RSS measurement. |
| AC-6 | required  | Test-locked behavior, bytecode-free. |
| AC-7 | important | A free build-throughput win from the benchmark (not an OOM fix); test-pinned. |


## Progress Log


| Date       | Update | Evidence |
| ---------- | ------ | -------- |
| 2026-06-23 | Drafted from the 1.8.0 field report. Streaming writer exists; the gap is the default buffer + `--content all` concurrency + swallowed SIGKILL + auto-index re-kill loop. | memory `project_field_feedback_1p8_oom_tls`; `indexer.py` `_resolve_embed_buffer_chunks`/`_StreamingLayerWriter`; `dashboard_server.py:254` |
| 2026-06-23 | **On-machine benchmark (M2 Max) — REFRAMES the change: `embed_buffer_chunks` is a dead memory lever; the OOM is the CPU embedding provider's FIXED working set.** Swept buffer 64/128/256/1024/2048: peak RSS is flat and non-monotonic on BOTH providers — GPU/CoreML ~1.6–1.9 GiB (1024 fastest), CPU ~13–15 GiB — with no relationship to buffer (pure run-to-run noise). CPU RSS is also **corpus-independent** (13,395-chunk run and 4,209-chunk run both ~13–15 GiB), so it is the fastembed/onnxruntime CPU arena+thread footprint, not chunks-in-flight. CPU is ~7–8× the GPU path — THIS is the field OOM (~14 GiB). The config knob is floored at `EMBED_BATCH_SIZE`=256, so the field operator's `256→48` was floored back to 256 AND a no-op anyway; their real fix was the sequential passes. → drop the buffer-autoscale AC; sequential-degrade (AC-2) is the fix; root-cause CPU-footprint reduction (thread/arena) moves to `1p7iv`. | `experiments/buffer_bench.py`; `/usr/bin/time -l` peak-RSS sweeps (GPU full-corpus + CPU isolated small-corpus + corpus-size control) |
| 2026-06-23 | **Implemented loud-failure + defer sequential-degrade.** AC-3: `setup_index._run_indexer` emits an OOM-specific SIGKILL message + remediation (lower `code/docs_embed_batch_size`, sequential `--content`, raise WSL2 memory) and raises. AC-4: dashboard `IndexBuilder` sets an OOM back-off on exit -9 — suppresses rearm + auto-retrigger (loud log), cleared by a clean build or explicit `signal_startup`. AC-2 (sequential-degrade) **deferred to `[~]`**: `1p7iv`'s batch-32 default bounds each pass to ~3.5 GiB so concurrent docs+code (~7 GiB) fits the in-scope ~15 GiB hosts — sequential-degrade is now narrow defense-in-depth for sub-8 GiB hosts. Suite 3432 OK. | `setup_index.py` `_run_indexer`; `dashboard_server.py` `IndexBuilder`; `test_dashboard_server.py` `test_oom_kill_sets_backoff_and_suppresses_auto_rebuild` |


## Decision Log


| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-06-23 | Mitigate (buffer + sequential + loud) here; root-cause memory bounding is `1p7iv` | The mitigation is small and ships a 1.8.1 fast; the deeper working-set profiling is larger and value-gates separately. | One big memory change — rejected: delays the urgent mitigation. |
| 2026-06-23 | **Drop buffer-autoscale (AC-1 → `[~]`); make sequential-degrade THE fix; move CPU-footprint reduction to `1p7iv`** | The on-machine benchmark proved `embed_buffer_chunks` does not affect peak RSS on either provider (flat/non-monotonic across 64–2048) and the CPU ~13–15 GiB footprint is fixed + corpus-independent — so auto-scaling the buffer cannot prevent the OOM. The only thing that bounds peak on a constrained host is running one ~13–15 GiB embedding pass at a time (sequential-degrade), exactly the field operator's working mitigation. | Keep buffer-autoscale — rejected: measured no-op, would ship false reassurance. |
| 2026-06-23 | **Re-scope AC-4 (operator): dashboard viewer-only; remove the index-trigger entirely; revert the OOM back-off.** Index updates belong to ONE background path (post-edit hook / MCP server `_start_background_index_refresh` / `wave_index_build`), not the dashboard. Removed the `auto_index` settings + the whole `IndexBuilder` class; the dashboard's build-status display now reads the shared hook/MCP state (`collect_health` → `wave_index_build_status_response`). The re-kill loop is structurally impossible (no dashboard build), so the back-off band-aid was reverted. ~27 obsolete tests removed; suite 3409 OK. | Default-off-but-keep-IndexBuilder — rejected (operator: remove it; the triggers are hook/MCP-owned). Keep the back-off — rejected: it guarded a trigger that no longer exists. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Over-aggressive sequential-degrade slows builds on capable hosts | Gate strictly on CPU-only + low-memory; capable/GPU hosts keep concurrent behavior. |
| Misreading the WSL/cgroup limit (host RAM vs VM cap) | Probe the cgroup/WSL limit explicitly, floor at `EMBED_BATCH_SIZE`, and test with a stubbed limit. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
