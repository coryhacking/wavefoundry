# GPU / embedding-provider diagnostic — `setup-wavefoundry --check-gpu` CLI + `wave_gpu_doctor` MCP tool

Change ID: `1p6et-enh gpu-provider-diagnostic-command`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-18
Wave: `1p6d5 windows-python-exec-hardening-and-wsl2-support`

## Rationale

There is no first-class way to ask "what embedding/GPU capabilities does this machine actually have, and what would Wavefoundry select?" — the answer today is hand-assembled from `provider_policy` internals. With WSL2 now a blessed target and GPU being the murkiest part of cross-platform support (CUDA auto-detect, the CUDA 12/13 ABI gap, AMD/Intel falling to CPU, DirectML being native-Windows-only), the operator needs a runnable diagnostic to inspect a host and guide future GPU work — and downstream WSL2/Windows users need it to self-diagnose.

This adds a single shared report over `provider_policy` exposed two ways (operator-chosen): a **CLI** (`wave-gpu-doctor` / `setup-wavefoundry --check`) for humans on a shell, and a **`wave_gpu_doctor` MCP tool** for agents/dashboard. Pure introspection — no model load, no index build, no side effects.

## Requirements

1. **Shared report.** Add `provider_policy.diagnostic_report() -> dict` returning a structured capability snapshot: platform (system/machine), onnxruntime version (or None), `WAVEFOUNDRY_EMBED_PROVIDER` request, `nvidia_gpu_present`, `apple_silicon_present`, `available_onnx_providers`, the `select_embedding_providers()` decision (selected provider + ordered providers + reason + remediation), and the `detect_cuda12_abi_gap()` result. No model load / index build / mutation.
2. **CLI.** `setup_wavefoundry.py --check` prints the report human-readably and exits 0 **without running the 3 setup steps** (short-circuit at the top of `main`). Add a `.wavefoundry/bin/wave-gpu-doctor` launcher (POSIX bash, venv-aware, mirroring the other launchers) that runs `setup_wavefoundry.py --check`. It is also reachable via the existing `setup-wavefoundry --check` launcher (args pass through).
3. **MCP tool.** Add a read-only `wave_gpu_doctor` tool (`@mcp.tool(annotations=_READONLY_TOOL)`) returning `diagnostic_report()` in the standard envelope (via a module-level `wave_gpu_doctor_response`). New tool ⇒ a one-time **server reconnect** is required for it to register (FastMCP limitation) — call out in the change/handoff.
4. **Discoverability weaving (seed-first).** Add `wave_gpu_doctor` to the canonical framework seed tool surface FIRST (so other projects pick it up on upgrade), then the project-local surfaces: `AGENTS.md` tool list, `docs/specs/mcp-tool-surface.md`, and a `wave-gpu-doctor` line in the `docs/reports/wsl2-smoke-checklist.md` GPU step. Requires `seed_edit_allowed` for the seed edit (open/close around it).
4. **Native-Windows note.** The `wave-gpu-doctor` bin launcher is POSIX bash only (no `.cmd` twin) — consistent with all 9 existing launchers; native-Windows `.cmd` launcher coverage is the deferred Area-1 work. On WSL2 it runs the Linux path (the point).
5. **No regression; docs-lint clean.** Full framework suite green; the diagnostic is pure-introspection so no behavior change to setup/index/provider selection.

## Scope

**Problem statement:** No first-class, runnable GPU/embedding-provider capability diagnostic; the info is locked in `provider_policy` internals.

**In scope:** `provider_policy.diagnostic_report()`; `setup_wavefoundry.py --check`; the `wave-gpu-doctor` bin launcher + render; the `wave_gpu_doctor` MCP tool + response fn; seed + `AGENTS.md` + `mcp-tool-surface.md` + smoke-checklist weaving; tests.

**Out of scope:**

- Changing any provider-selection / setup behavior (introspection only).
- A `.cmd` Windows twin of the `wave-gpu-doctor` launcher (Area-1).
- New GPU detection (AMD/Intel/DirectML auto-detect) — separate follow-up; this only *reports* current capability.
- Running a model probe (the report uses `select_embedding_providers()` no-probe view; it states that CUDA/CPU are exact and probe-required providers show their availability via `available_onnx_providers`).

## Acceptance Criteria

- [x] AC-1: `provider_policy.diagnostic_report()` returns the structured snapshot (platform, onnxruntime_version, requested_provider_env, nvidia/apple detection, available_onnx_providers, selected_provider + providers + reason + remediation, cuda12_abi_gap), pure-introspection. Tested (`test_diagnostic_report_shape_and_reflects_probes` — mocked probes drive the output; no embedder constructed). Smoke-verified live via `--check` on this host.
- [x] AC-2: `setup_wavefoundry.py --check-gpu` prints the report (via `format_diagnostic_report`) and returns 0 without running setup. Tested (`test_check_flag_prints_diagnostic_and_skips_setup` — asserts rc 0, diagnostic printed, and none of the 3 setup steps ran). Verified live (exit 0).
- [x] AC-3: `wave_gpu_doctor` MCP tool (`@mcp.tool(_READONLY_TOOL)`, `_ensure_no_extra_args`-guarded) returns `diagnostic_report()` via `wave_gpu_doctor_response` in the standard envelope. Tested (`GpuDoctorToolTests` — status ok + all report keys + usage). **Needs a one-time server reconnect to register (FastMCP).**
- [x] AC-4: **No dedicated GPU-doctor bin launcher** (operator-directed reversal — it was redundant). The diagnostic is reached via the **`--check-gpu`** flag on the existing `setup-wavefoundry` launcher + the `wave_gpu_doctor` MCP tool. Regression-guarded by `GpuDoctorLauncherTests` (asserts no `wave-gpu-doctor`/`wave-doctor` launcher is rendered; `setup-wavefoundry` still is).
- [x] AC-5: woven into discoverability — `AGENTS.md` tool list + `docs/specs/mcp-tool-surface.md` table + the WSL2 smoke-checklist GPU step. **Correction:** there is NO seed tool-catalog to update — the framework source of truth for the tool is `server_impl.py` (ships downstream via the package); seeds 050/100 only name docs-gate tools in prose, not a catalog. So "seed-first" = the tool in `server_impl`; the rest are this repo's project surfaces.
- [x] AC-6: No regression — full framework suite green (**3332**, +4); docs-lint clean; the server-reconnect requirement is documented (this AC + the change Rationale + handoff).

## Tasks

- [x] `provider_policy.diagnostic_report()` + `format_diagnostic_report()` (used `os`/`platform`; annotated `-> dict`, no `Any` needed).
- [x] `setup_wavefoundry.py`: `--check` short-circuit in `main` → `_load_provider_policy` (sys.path + plain import; fixed an importlib-name crash) → print report → return 0.
- [x] `render_platform_surfaces.render_bin_launchers`: added `wave-gpu-doctor` (→ `setup_wavefoundry.py --check`). (Render integration test asserts specific launchers, not an exhaustive set — unaffected.)
- [x] `server_impl`: `wave_gpu_doctor_response(root)` + `@mcp.tool` `wave_gpu_doctor` (local `import provider_policy`).
- [x] Weave: `AGENTS.md`, `docs/specs/mcp-tool-surface.md`, `docs/reports/wsl2-smoke-checklist.md`. (No seed tool-catalog exists — see AC-5; `seed_edit_allowed` opened then closed unused.)
- [x] Tests: `GpuDoctorCheckTests` (report shape + `--check` short-circuit), `GpuDoctorToolTests` (envelope), `WaveDoctorLauncherTests` (render). Full suite 3332 + docs-lint green.

## Affected Architecture Docs

`N/A` for boundaries/flow — new read-only diagnostic surface. Updates `docs/specs/mcp-tool-surface.md` (tool reference) and `AGENTS.md` (tool list); seed tool surface updated as source of truth.

## AC Priority


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The shared report is the core; both surfaces depend on it. |
| AC-2 | required | The CLI surface (operator-chosen). |
| AC-3 | required | The MCP surface (operator-chosen). |
| AC-4 | important | Ergonomic `wave-gpu-doctor` launcher; `setup-wavefoundry --check` also works. |
| AC-5 | important | Discoverability (seed-first) — agents/operators must find the new tool. |
| AC-6 | required | No regression; docs-lint clean. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-18 | Operator-directed ("enable the GPU diagnostic hook … guide future development"); chose CLI + MCP. Built on the hand-assembled `provider_policy` diagnostic surfaced this session. | `provider_policy.py` (nvidia/apple detection, select_embedding_providers, detect_cuda12_abi_gap) |
| 2026-06-18 | Implemented all 6 ACs. Shared `diagnostic_report()`/`format_diagnostic_report()`; `--check` CLI (smoke-verified live, exit 0, no setup); `wave-gpu-doctor` launcher; `wave_gpu_doctor` MCP tool (needs reconnect). Fixed an importlib-name crash in the loader (→ sys.path + plain import). No seed tool-catalog exists → server_impl is the framework source; wove AGENTS.md + mcp-tool-surface.md + smoke checklist. | +4 tests; full suite **3332 green**; docs-lint clean |
| 2026-06-18 | Post-delivery refinement (operator-directed): exclude REMOTE/inert ORT EPs (`AzureExecutionProvider` — a cloud Azure ML proxy that ships in the ORT wheel) from the diagnostic's `available_onnx_providers` DISPLAY (`_REMOTE_INERT_PROVIDERS`); selection already ignored it. Verified live via `--check` (Azure gone; CoreML/CPU remain) + `wave_gpu_doctor` via MCP after reconnect. | `provider_policy.diagnostic_report`; +1 test (`test_diagnostic_report_filters_remote_azure_provider`); suite green except the known env-flake `test_get_reranker_does_not_cache_none_on_failure` (accel_embedder/CoreML-box, isolation-reproducible, causally unrelated — `diagnostic_report` not referenced in accel_embedder) |
| 2026-06-18 | Operator-directed rename: bin launcher `wave-doctor` → **`wave-gpu-doctor`** (matches the `wave_gpu_doctor` MCP tool; the name was too generic). Renamed across renderer + docstrings + tests + docs; re-rendered (`.wavefoundry/bin/wave-gpu-doctor` created, old `wave-doctor` removed — never shipped); verified it runs. | `render_platform_surfaces.py`, `provider_policy.py`, `server_impl.py`, `setup_wavefoundry.py`, tests, `mcp-tool-surface.md`, `wsl2-smoke-checklist.md`; full suite **3333 green**; docs-lint clean |
| 2026-06-18 | Operator-directed surface reversal: **removed the dedicated bin launcher entirely** (redundant) and renamed the CLI flag `--check` → **`--check-gpu`**. The diagnostic is now reached via `setup-wavefoundry --check-gpu` + the `wave_gpu_doctor` MCP tool. Removed the renderer block + on-disk file; `GpuDoctorLauncherTests` now guards against re-adding a launcher. | `render_platform_surfaces.py`, `setup_wavefoundry.py`, `server_impl.py`, `provider_policy.py`, tests, `mcp-tool-surface.md`, `wsl2-smoke-checklist.md`; suite + docs-lint re-verified |
| 2026-06-18 | Accuracy fix (operator-directed): the diagnostic now runs setup's bounded probe so `would select` matches runtime. Verified live: `setup-wavefoundry --check-gpu` reports `CoreMLExecutionProvider` on this M2 Max (was CPU). `diagnostic_report` gained `provider_probe`; CLI + MCP pass `_probe_embedding_provider` (MCP guards stdout→stderr). Tests reworked: routing (`--check-gpu` short-circuits setup), probe-selection (CoreML confirmed), + an `SETUP_SELECTED_ENV` cross-file env-leak guard. | `provider_policy.diagnostic_report`, `setup_wavefoundry._run_gpu_check`, `server_impl.wave_gpu_doctor_response`; full suite **3334 green**; docs-lint clean |
| 2026-06-18 | Reworded the CoreML probe reason (operator-directed clarity): the micro-benchmark timing is now explicitly labelled "a tiny correctness micro-benchmark, NOT representative throughput — the accelerated FP16/static-shape path runs at index time" (kept "not a speedup gate"). Considered + rejected making the probe embed a real script: it uses the plain-fastembed (dynamic) path, not the FP16/static accel path where the ~8.75× win lives, so a heavier probe wouldn't be representative and would only slow setup. Surfaces in `--check-gpu` / `wave_gpu_doctor` / setup output. | `setup_index._probe_embedding_provider`; test asserts the `micro-benchmark` label; full suite **3334 green** |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-18 | Surface both a CLI and an MCP tool over one `diagnostic_report()`. | Operator-chosen; humans run the CLI on a WSL2/Windows shell, agents/dashboard call the tool. | CLI-only (lean) / MCP-only (no shell access for downstream users) — operator picked both. |
| 2026-06-18 | `--check` short-circuits `setup_wavefoundry.main`; `wave-gpu-doctor` launcher delegates to it. | One implementation, reachable both as a dedicated launcher and via the existing `setup-wavefoundry` launcher. | A standalone `wave_doctor.py` script (more surface; unnecessary). |
| 2026-06-18 | Report uses the no-probe `select_embedding_providers()` view + `available_onnx_providers`. | Pure introspection, fast, no model load; CUDA/CPU exact, probe-required providers visible via availability. | Run a full provider probe (heavy; needs models) — out of scope for a quick diagnostic. |
| 2026-06-18 | Removed the dedicated bin launcher; use the `--check-gpu` flag on `setup-wavefoundry` instead. | Operator-directed — a separate launcher was redundant with the flag, and fewer surfaces means no `.cmd` Area-1 twin to maintain. | Keep `wave-gpu-doctor` as a dedicated launcher (rejected by operator). |
| 2026-06-18 | RESOLVED (operator chose accuracy): `diagnostic_report(provider_probe=...)` now runs setup's bounded probe; the CLI + MCP pass `setup_index._probe_embedding_provider`, so `would select` matches runtime — verified live: `CoreMLExecutionProvider` on this M2 Max (was CPU). Loads a model (cached → fast; the `SETUP_SELECTED_ENV` cache short-circuits it when setup already ran); MCP redirects stdout→stderr for stdio safety; the no-arg `diagnostic_report()` stays no-probe for cheap/test use. | The no-probe view under-reported the probe-required providers (CoreML/ROCm/OpenVINO/DML) as CPU. | (a) probe-always [CHOSEN]; (b) probe opt-in; (c) annotate-only (rejected — operator wanted the true answer). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| New MCP tool not visible until server reconnect (FastMCP). | Documented in the change + handoff; the CLI works immediately without reconnect. |
| `diagnostic_report` accidentally triggers a model load / side effect. | Uses only the lightweight provider_policy probes (nvidia-smi, ORT availability, ldconfig); test asserts no model/index call. |
| Seed edit drifts from project docs. | Seed-first then render/sync project surfaces; docs-lint; grep audit (AC-5). |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
