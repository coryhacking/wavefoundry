# CUDA-13 GPU provider silently falls back to CPU (onnxruntime-gpu CUDA-12 ABI)

Change ID: `1p5py-bug cuda13-gpu-provider-fallback-surfacing`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-15
Wave: `1p5px post-release-field-hardening`

> **REVISED 2026-06-15 (field report 091yn/091yp — pivot):** the auto-shim approach was **abandoned**. On the reporter's RTX 5070 Ti / CUDA 13.3 box, a `.so.12 → .so.13` soname symlink **cannot work** — CUDA 13's cuBLAS exports different ELF version symbols (VERNEED) than CUDA 12, so the loader rejects the mismatched library (091yp). This confirms the prepare-council's exact ABI concern. The shim (`ensure_cuda12_abi_shim`, `accel_embedder._handle_cuda12_gap`, `_onnxruntime_lib_dir`) was **removed**. The change is now **warning-only**: a filesystem-based gap probe surfaces an accurate, loud, one-time warning whose remediation is "build onnxruntime-gpu from source against CUDA 13, or await a CUDA-13 wheel" — *not* a symlink. The probe is **proactive/filesystem-based** so it fires even when the CUDA libs aren't on the linker path and ORT doesn't list CUDAExecutionProvider at all (091yn — the silent-on-fresh-Arch case). Actually using the GPU is an operator action (build from source), outside framework code.

## Rationale

Field report against **1.6.0+p5lj** (Arch/CachyOS, RTX 5070 Ti / Blackwell, CUDA 13.3 driver, Python 3.14, framework-installed `onnxruntime-gpu==1.26.0` + `fastembed-gpu==0.8.0`): every index build **silently falls back to CPU** (5–10× slower on large repos). The build reports success; the only signal is a buried ONNX Runtime stderr line:

```
[E] Failed to load libonnxruntime_providers_cuda.so: libcublasLt.so.12: cannot open shared object file
[W] Failed to create CUDAExecutionProvider. Require cuDNN 9.* and CUDA 12.*
```

**Root cause:** all PyPI `onnxruntime-gpu` ≤1.26.0 are built against the **CUDA 12 ABI** and hard-link `libcublasLt.so.12` / `libcublas.so.12`. Arch and derivatives (CachyOS, Manjaro, EndeavourOS) ship only **CUDA 13.3** (`libcublasLt.so.13`); there is no CUDA-12 toolkit in their repos, and RTX 40xx/50xx effectively require CUDA 12.8+/13. So the CUDA provider cannot load, ORT silently drops to CPU, and the operator never finds out.

Two problems compound: (1) the failure is **silent** — `provider_policy.select_embedding_providers` can pick CUDA from availability alone (no probe; `provider_policy.py:121` `_provider_requires_probe` returns False for CUDA), and `accel_embedder`'s `offloads_to_gpu()` fallback drops to CPU **without surfacing why**; (2) there is **no automated remediation** — the user's only fix is root-level system symlinks (`libcublasLt.so.13 → .so.12`) that break on toolkit updates.

Operator direction (2026-06-15): **automate the fix in code if possible**; if it can't be applied automatically, the failure and its remediation **must be surfaced to the install/upgrade agent** so it can be addressed locally — never a silent CPU fallback.

## Requirements

1. **Detect the ABI-mismatch fallback, don't swallow it.** When an NVIDIA GPU is present (`provider_policy.nvidia_gpu_present()`) but the CUDA provider fails to load or doesn't actually offload (the `libcublasLt.so.12`-missing case), the resulting CPU `ProviderDecision` must carry a specific `reason` + `remediation` naming the CUDA-12-vs-13 ABI mismatch — not a generic "CPU selected."
2. **Attempt an automated, root-free fix (best effort).** When `libcublasLt.so.12` is absent but `libcublasLt.so.13` (and `libcublas.so.13`) are present on the system, create the `.so.12 → .so.13` symlinks in a **venv-local** lib directory (no root; no system paths) and make ORT load them (venv-local `LD_LIBRARY_PATH` / loader-path injection before session creation), then re-probe. If the shim makes CUDA offload, proceed on GPU. The shim must be idempotent and never touch system directories.
3. **Surface a first-class warning when automation can't apply.** If the GPU is present but CUDA still can't load after the shim attempt (or no `.so.13` was found), the **install (`setup_*`) and upgrade index-build paths must print a prominent operator/agent-facing warning** — not a buried ORT `[E]` line — stating: GPU detected, CUDA provider failed to load due to the CUDA-12-ABI pin, the build is running on CPU, and the exact local remediation (the package-manager install + the `.so.12→.so.13` symlink note, or pointing at the framework's auto-shim if partial). The message must be machine-greppable so an agent running the install/upgrade can act.
4. **No regression on working GPU paths** (Apple CoreML, healthy CUDA-12 Linux) or CPU-only hosts: the detection/shim only engages when NVIDIA-present + CUDA-load-failed; CoreML and already-working CUDA are untouched.

## Scope

**In scope:**

- `provider_policy.py`: capture the CUDA-load-failure cause into the CPU `ProviderDecision.reason`/`remediation`; a detector for "NVIDIA present + CUDA `.so.12` missing + `.so.13` present"; the venv-local symlink shim helper (idempotent, root-free) + re-probe.
- `accel_embedder.py`: invoke the shim before giving up on the GPU provider; stop swallowing the load failure silently.
- `setup_index.py` / `setup_wavefoundry.py` and the upgrade Phase-4 index build: surface `ProviderDecision.remediation` as a prominent, greppable warning when GPU was expected but fell back.
- Tests: ABI-mismatch detection, shim symlink creation in a temp venv lib (mocked filesystem — no real CUDA), decision-carries-remediation, no-engage on CoreML/CPU/healthy-CUDA.

**Out of scope:**

- Shipping or pinning a CUDA-13 `onnxruntime-gpu` wheel (reporter's option 2) — gated on ONNX Runtime publishing one; revisit when available.
- Windows CUDA, ROCm/AMD, and non-NVIDIA accelerators.
- Changing the static-shape / FP16 embedding pipeline.

## Acceptance Criteria

- [x] AC-1 (revised per 091yn/091yp): a **filesystem-based** gap probe (`detect_cuda12_abi_gap`) surfaces an accurate, loud, one-time warning (`[wavefoundry][GPU] WARNING: …`) whose remediation is build-from-source / await-a-CUDA-13-wheel — **never the broken symlink**. It fires from `make_embedder` both when CUDA is selected but doesn't offload AND **proactively when ORT doesn't list CUDA at all** (091yn), so a fresh CUDA-13 host is no longer silent. Unit-tested (`ProviderPolicyCuda12GapTests` + `AccelCuda12WarnTests`, incl. remediation-doesn't-suggest-symlink + warn-once + shim-helper-gone). The auto-shim was **removed** (091yp); actually engaging the GPU is now an operator build-from-source step, outside framework code. **Light downstream confirm (091yn):** verify the warning actually prints on the reporter's box — no GPU-engagement claim to validate anymore.
- [x] AC-2: No behavior change on Apple CoreML, healthy CUDA-12 Linux, or CPU-only hosts — `detect_cuda12_abi_gap` returns None off-Linux/off-NVIDIA (cheap `nvidia-smi` which-check), so no warning fires; `test_no_gap_is_silent` + the no-gap detection tests confirm. Full suite **3138 OK**; docs-lint clean.

## Tasks

- [x] Detector `detect_cuda12_abi_gap` (provider_policy.py): NVIDIA + Linux + `.so.12` missing / `.so.13` present, via `ldconfig -p` + known toolkit dirs; injectable for tests.
- [x] Venv-local symlink shim `ensure_cuda12_abi_shim` (idempotent, root-free, never writes system dirs) + `accel_embedder._handle_cuda12_gap` placing it in the onnxruntime lib dir (`$ORIGIN`-RPATH) + re-probe once in `make_embedder`.
- [x] Thread the cause into the surfaced message — `gap.remediation` carries the CUDA-12-ABI cause; emitted via the accel warning (the actual silent-fallback path; `ProviderDecision.remediation` is the separate fastembed-probe path, already covers the "CUDA not listed" case).
- [x] Greppable warning `[wavefoundry][GPU] WARNING:` from `make_embedder`, which runs during `setup_*` and the upgrade Phase-4 index build (once-guarded, so no spam).
- [x] Tests (detection on/off + partial gap, idempotent shim, warn-once + shim-applies) — 9, hardware-free.
- [~] Downstream validation on the reporter's Arch/RTX 5070 Ti box (deferred — no CUDA on self-host).

## Agent Execution Graph


| Workstream     | Owner       | Depends On    | Notes |
| -------------- | ----------- | ------------- | ----- |
| provider-shim  | Engineering | —             | detection + shim + decision reason in provider_policy/accel_embedder |
| surfacing      | Engineering | provider-shim | warning in setup_* + upgrade index build; tests |


## Serialization Points

- `provider_policy.py` is shared with the existing hardware-aware policy (wave 1p4u5) — sequence the shim detection before the surfacing change.

## Affected Architecture Docs

`N/A` — install/runtime robustness within the embedding-provider selection path; no boundary/contract change. (Operator-facing remediation text is in install/upgrade output, not an architecture doc.)

## AC Priority

(Populated at Prepare wave.)

| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The silent CPU fallback is the user-facing defect; automate-or-surface is the operator's explicit requirement. |
| AC-2 | required | Must not regress the working CoreML / CUDA-12 / CPU paths. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-15 | Scoped from a 1.6.0+p5lj field report (Arch/CachyOS, RTX 5070 Ti, CUDA 13.3). Root cause: PyPI onnxruntime-gpu ≤1.26.0 is CUDA-12-ABI; Arch ships only CUDA 13 → silent CPU fallback. Hooks identified: `provider_policy.py` (ProviderDecision.reason/remediation, nvidia_gpu_present), `accel_embedder.py` (offloads_to_gpu fallback). Needs the reporter's hardware to validate the GPU path. | `provider_policy.py`, `accel_embedder.py` |
| 2026-06-15 | **Implemented (framework side) + unit-tested.** `provider_policy`: `detect_cuda12_abi_gap` + `ensure_cuda12_abi_shim` (venv-local, root-free, idempotent) + remediation builder. `accel_embedder`: `_handle_cuda12_gap` (shim into onnxruntime lib dir + re-probe; one-time greppable warning) wired into `make_embedder` (re-probe once, then warn if GPU still idle; warn on the exception path too). 9 hardware-free tests. The auto-shim's actual GPU re-engagement is **deferred to the reporter's Arch/RTX box** (no CUDA on self-host) — the guaranteed warning is shipped and tested. **Full suite 3138 OK**; docs-lint clean. | `provider_policy.py`, `accel_embedder.py`, `test_accel_embedder.py` |
| 2026-06-15 | **PIVOT (field report 091yn/091yp).** Reporter validated on RTX 5070 Ti / CUDA 13.3: the soname symlink shim **cannot work** (CUDA 13 cuBLAS has different ELF VERNEED symbols). **Removed** `ensure_cuda12_abi_shim`, `accel_embedder._handle_cuda12_gap`, `_onnxruntime_lib_dir`. Replaced with `_warn_cuda12_gap_if_present` (detect + warn only). **Corrected the remediation** (no symlink → build-from-source / await CUDA-13 wheel). **091yn:** the warn is now called proactively in `make_embedder`'s `if not gpu` branch too, so it fires when ORT doesn't list CUDA on a fresh host. Tests updated (shim tests removed; warn-once + remediation-no-symlink + shim-gone tests added). **Full suite 3138 OK**; docs-lint clean. | `provider_policy.py`, `accel_embedder.py`, `test_accel_embedder.py` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-15 | Automate the venv-local `.so.12→.so.13` shim when possible; otherwise surface a loud, greppable install/upgrade warning | Operator direction: never a silent CPU fallback; prefer automated root-free fix, guarantee the surfaced fallback. | (a) require manual root symlinks (rejected — silent + breaks on toolkit updates); (b) ship a CUDA-13 wheel (deferred — external dependency on ORT); (c) warning-only, no auto-shim (kept as the guaranteed fallback, not the only path) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Venv-local symlink shim points at an incompatible `.so.13` and crashes the session | Re-probe (`offloads_to_gpu`) after the shim; on failure, fall back to CPU + the surfaced warning rather than hard-crash |
| Cannot validate the GPU path on the self-host (Apple M2 Max, no CUDA) | Unit-test detection/shim/decision on non-CUDA hosts; gate the GPU-engages claim on downstream validation on the reporter's Arch/RTX box |
| Shim touches system dirs / needs root | Hard requirement: venv-local only, idempotent, never write system paths |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
