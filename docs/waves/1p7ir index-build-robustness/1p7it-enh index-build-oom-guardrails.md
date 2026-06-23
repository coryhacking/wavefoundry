# Index-build OOM guardrails: auto-scaled buffer, sequential-degrade, loud failure

Change ID: `1p7it-enh index-build-oom-guardrails`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-06-23
Wave: `1p7ir index-build-robustness`

## Rationale

On a CPU-only, ~15 GiB WSL2 host, the 1.8.0 index build OOM-killed the code embedding pass (~14 GiB RSS at file ~300/811) and the failure was invisible: the child `indexer.py --content all` died with SIGKILL while the wrapper looked success-ish, and the dashboard auto-index re-triggered the same `--content all` (`dashboard_server.py:254`) toward a re-kill loop.

Per-layer streaming already exists (`_StreamingLayerWriter`; `_resolve_embed_buffer_chunks`, floored at `EMBED_BATCH_SIZE`), so the lever is present — but the shipped `embed_buffer_chunks` default is too aggressive for CPU/low-RAM, and `--content all` keeps docs+code+secrets+graph pipelines resident concurrently. The operator’s working mitigation: `embed_buffer_chunks` 256→48 **and** sequential `--content docs` then `--content code` → peak RSS ~8.8 GiB.

## Requirements

1. **Auto-scale the embed buffer to the real memory limit.** Pick a safe `embed_buffer_chunks` default from the **cgroup/WSL memory limit** (not host RAM — WSL caps are lower), floored at `EMBED_BATCH_SIZE`. An explicit `indexing.embed_buffer_chunks` override still wins. Lower the shipped default for the unconstrained case too if measurement warrants.
2. **Sequential-degrade on a constrained profile.** Detect CPU-only (the `wave_gpu_doctor` selection path) + a low-memory probe, and run the layers as **sequential passes** instead of concurrent `--content all` — including the dashboard auto-index trigger. A non-constrained host keeps current behavior.
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

- [ ] AC-1: the default `embed_buffer_chunks` is derived from the cgroup/WSL memory limit (floored at `EMBED_BATCH_SIZE`); an explicit config override still wins; verified by tests with a stubbed memory limit.
- [ ] AC-2: on a CPU-only + low-memory profile the build runs sequential passes (one embedding pipeline resident at a time), including the dashboard auto-index; a non-constrained profile is unchanged.
- [ ] AC-3: a child SIGKILL surfaces a clear out-of-memory error with remediation; the wrapper/upgrade no longer reports success after an OOM kill.
- [ ] AC-4: after an OOM-killed build the dashboard auto-index does not immediately re-trigger the same `--content all` (no re-kill loop).
- [ ] AC-5: measured on a constrained host (or a memory-capped repro) — peak RSS stays bounded well under the cap and the code pass completes; recorded as the value gate.
- [ ] AC-6: framework tests cover buffer auto-scaling, the constrained-profile decision, and SIGKILL surfacing, bytecode-free; `wave_validate` clean.

## Tasks

- [ ] Make `_resolve_embed_buffer_chunks` memory-aware (cgroup/WSL probe → safe default).
- [ ] Add constrained-profile detection (CPU-only + memory probe) + sequential-pass degrade in the build orchestration and `dashboard_server.py` auto-index.
- [ ] Detect child SIGKILL → loud OOM remediation in the wrapper/upgrade; add auto-index back-off.
- [ ] Tests (buffer scaling, profile decision, SIGKILL surfacing) bytecode-free + the constrained-host peak-RSS measurement.

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
| AC-1 | required  | Memory-aware default is the primary mitigation. |
| AC-2 | required  | Sequential-degrade prevents the concurrent-pipeline OOM. |
| AC-3 | required  | Loud failure is half of making the OOM visible (with `1p7is`). |
| AC-4 | important | Stops the re-kill loop. |
| AC-5 | required  | Real-host value gate — ship only on a bounded-RSS measurement. |
| AC-6 | required  | Test-locked behavior, bytecode-free. |


## Progress Log


| Date       | Update | Evidence |
| ---------- | ------ | -------- |
| 2026-06-23 | Drafted from the 1.8.0 field report. Streaming writer exists; the gap is the default buffer + `--content all` concurrency + swallowed SIGKILL + auto-index re-kill loop. | memory `project_field_feedback_1p8_oom_tls`; `indexer.py` `_resolve_embed_buffer_chunks`/`_StreamingLayerWriter`; `dashboard_server.py:254` |


## Decision Log


| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-06-23 | Mitigate (buffer + sequential + loud) here; root-cause memory bounding is `1p7iv` | The mitigation is small and ships a 1.8.1 fast; the deeper working-set profiling is larger and value-gates separately. | One big memory change — rejected: delays the urgent mitigation. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Over-aggressive sequential-degrade slows builds on capable hosts | Gate strictly on CPU-only + low-memory; capable/GPU hosts keep concurrent behavior. |
| Misreading the WSL/cgroup limit (host RAM vs VM cap) | Probe the cgroup/WSL limit explicitly, floor at `EMBED_BATCH_SIZE`, and test with a stubbed limit. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
