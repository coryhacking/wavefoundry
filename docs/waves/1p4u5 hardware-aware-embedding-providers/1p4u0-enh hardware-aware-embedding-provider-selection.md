# Hardware-Aware Embedding Provider Selection

Change ID: `1p4u0-enh hardware-aware-embedding-provider-selection`
Change Status: `implemented`
Owner: implementer
Status: implemented
Last verified: 2026-06-11
Wave: `1p4u5 hardware-aware-embedding-providers`

## Rationale

A Wavefoundry install on an NVIDIA GPU machine completed with CPU-only embedding execution even though GPU acceleration was available in local hardware. The observed runtime provider list was `AzureExecutionProvider` and `CPUExecutionProvider`, with no `CUDAExecutionProvider`. Current code already prefers CUDA when ONNX Runtime exposes it in `indexer.py` `_onnx_providers()`, but setup installs the standard `fastembed` dependency and does not evaluate whether the local machine should install a GPU-capable ONNX/FastEmbed stack. On Apple Silicon, ONNX Runtime may expose `CoreMLExecutionProvider`, but current Wavefoundry code intentionally excludes it because availability alone does not prove that the FastEmbed ONNX models run faster or correctly on CoreML.

The failure mode is therefore easy to miss: setup succeeds, indexing works, but large embedding jobs silently run on CPU. For repositories with tens of thousands of chunks, this can turn an avoidable GPU-capable setup issue into materially slower first-index and re-index times.

## Requirements

1. During `setup_wavefoundry.py` / `setup_index.py`, detect whether the local machine appears GPU-capable for embedding acceleration before dependency installation is finalized.
2. Select the best supported embedding runtime for local hardware, preferring CUDA on NVIDIA systems only when the installed Python packages and ONNX Runtime provider probe confirm `CUDAExecutionProvider` is usable.
3. Evaluate Apple Silicon separately through `CoreMLExecutionProvider` compatibility and performance probes; enable CoreML only when the active embedding model produces valid embeddings and beats the CPU path by a meaningful threshold.
4. Evaluate other GPU-capable ONNX Runtime providers as named platform providers, not as a generic GPU bucket: CUDA/NVIDIA first, Apple CoreML second when its probe passes, then explicitly supported secondary providers such as DirectML, OpenVINO, MIGraphX, or ROCm only when they are available and verified.
5. Preserve the current CPU-only path as the safe fallback on machines without supported GPU acceleration, unsupported operating systems, missing drivers/toolkit requirements, failed provider probes, invalid embeddings, or slower provider measurements.
6. Surface the selected embedding execution provider in setup/index logs, including clear reasons when GPU acceleration was detected in hardware but not enabled in the Python environment.
7. Keep setup local-only and deterministic: do not require telemetry, hosted capability checks, or non-Python system mutation.
8. Add tests around provider detection, package selection, fallback behavior, and operator-facing diagnostics without requiring CI to have a physical GPU.

## Scope

**Problem statement:** Wavefoundry's runtime indexer already asks ONNX Runtime for available providers and prefers CUDA if present, but setup does not install or verify a GPU-capable embedding runtime on GPU hardware. On Apple Silicon, `CoreMLExecutionProvider` can be present in ONNX Runtime, but current code excludes it and has no measured way to decide whether it should be used for Wavefoundry's embedding models. Users can unknowingly end up with CPU embeddings even when local hardware could run faster.

**In scope:**

- Add a setup-time provider evaluation path in `.wavefoundry/framework/scripts/setup_index.py`.
- Evaluate NVIDIA/CUDA capability using local probes such as `nvidia-smi`, package/provider imports, and ONNX Runtime provider availability.
- Evaluate Apple Silicon/CoreML capability using ONNX Runtime provider availability plus a small model-specific correctness and performance probe against `CoreMLExecutionProvider`.
- Evaluate secondary ONNX Runtime provider families by explicit provider name only; do not introduce a generic "GPU" provider label or fallback.
- Decide whether dependency installation should use CPU defaults or a GPU-capable dependency set, such as `fastembed-gpu` and/or `onnxruntime-gpu`, subject to compatibility verification.
- Add an explicit post-install provider verification step that confirms which ONNX providers are available to FastEmbed.
- Record provider decisions in metadata or logs sufficiently to diagnose why CPU, CUDA, or CoreML was selected.
- Emit concise setup/index logs showing the selected provider and fallback reason.
- Add an override or escape hatch if needed for operators who want to force CPU or opt into GPU probing explicitly.
- Update user-facing setup/install docs and architecture docs that describe dependency setup and indexing.

**Out of scope:**

- Supporting non-ONNX GPU runtimes or alternate embedding model families.
- Installing system-level NVIDIA drivers, CUDA toolkit packages, or OS package manager dependencies.
- Treating Apple CoreML as equivalent to CUDA or enabling it just because `CoreMLExecutionProvider` appears in ONNX Runtime.
- Benchmarking every model/provider combination during normal setup; the probe should be limited to the active Wavefoundry embedding model(s) and bounded so setup remains acceptable.
- Changing retrieval ranking, chunking behavior, graph indexing, or embedding model selection.

## Acceptance Criteria

- [x] AC-1: On a CPU-only machine or mocked CPU-only environment, setup installs/uses the CPU dependency path and logs that `CPUExecutionProvider` is selected without error.
- [x] AC-2: On a mocked NVIDIA/CUDA-capable environment where GPU packages expose `CUDAExecutionProvider`, setup selects the GPU-capable dependency/provider path and logs `CUDAExecutionProvider` as active.
- [x] AC-3: On a mocked NVIDIA/CUDA-capable environment where GPU package install or provider verification fails, setup falls back to CPU and logs the concrete fallback reason plus the manual remediation hint.
- [x] AC-4: On a mocked Apple Silicon/CoreML-capable environment where CoreML produces valid embeddings and passes the performance threshold, setup selects `CoreMLExecutionProvider` and logs it as active.
- [x] AC-5: On a mocked Apple Silicon/CoreML-capable environment where CoreML is unavailable, invalid, or slower than CPU, setup falls back to CPU and logs the concrete fallback reason.
- [x] AC-6: Named secondary providers such as DirectML/OpenVINO/MIGraphX/ROCm are considered only by explicit provider name after CUDA and CoreML; no generic GPU bucket appears in setup diagnostics or provider policy.
- [x] AC-7: Runtime provider selection remains centralized and consistent with `indexer.py` `_onnx_providers()`, so setup's reported provider and indexer's actual provider cannot diverge silently.
- [x] AC-8: Tests cover dependency selection and provider-probe branches without requiring a real GPU or Apple Neural Engine in the test environment.
- [x] AC-9: Setup/install documentation explains how Wavefoundry chooses CPU vs CUDA vs CoreML embedding execution, how to verify the active provider, and how to remediate a GPU-capable machine that is still using CPU.
- [x] AC-10: Existing framework tests pass via `python3 .wavefoundry/framework/scripts/run_tests.py`.

## Tasks

- [x] Inspect current FastEmbed and ONNX Runtime packaging constraints for CPU vs CUDA vs CoreML provider support.
- [x] Define a bounded provider probe for the active embedding model that verifies shape/numeric sanity and compares CPU vs candidate provider runtime.
- [x] Add a small provider-capability abstraction in setup/indexer code so setup can reuse or mirror runtime provider logic without duplicating fragile behavior.
- [x] Extend dependency installation planning to select CPU or GPU package requirements based on capability and operator override.
- [x] Add post-install verification that imports ONNX Runtime/FastEmbed and records available providers.
- [x] Add setup log lines for selected provider, unavailable GPU/CoreML reasons, performance-probe results, and remediation guidance.
- [x] Add unit tests with mocked `nvidia-smi`, Apple Silicon/CoreML probes, package import/provider responses, install failures, and fallback behavior.
- [x] Update architecture and setup docs to describe hardware-aware provider selection.
- [x] Run the full framework suite.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| Discovery | implementer | - | Confirm current package names, platform constraints, FastEmbed provider behavior, and CoreML viability. |
| Setup provider planning | implementer | Discovery | Owns setup-time detection, package choice, overrides, and diagnostics. |
| Runtime consistency | implementer | Discovery | Keeps setup reporting aligned with `indexer.py` provider selection. |
| Tests | qa-reviewer | Setup provider planning, Runtime consistency | Use mocks; do not require GPU hardware in CI. |
| Docs | docs-contract-reviewer | Setup provider planning | Update install/setup and architecture docs after behavior is final. |

## Serialization Points

- `.wavefoundry/framework/scripts/setup_index.py` and `.wavefoundry/framework/scripts/indexer.py` are shared framework scripts and require the repository code stage gate before implementation.
- Dependency-list changes affect install and upgrade behavior; coordinate with packaging/release notes before building a distribution.
- If seed prompts or generated setup docs need edits, open the appropriate framework edit gate and update canonical seeds before rendering downstream surfaces.

## Affected Architecture Docs

- `docs/architecture/current-state.md` - setup topology should mention hardware-aware provider evaluation and provider diagnostics.
- `docs/architecture/chunking-and-indexing-pipeline.md` - embedding runtime/provider selection should be documented if it becomes part of the indexing contract.
- `docs/contributing/build-and-verification.md` or install/upgrade docs - operator verification and remediation steps should be updated.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | CPU fallback must remain reliable for all existing users. |
| AC-2 | required | The core enhancement is enabling verified GPU execution when supported. |
| AC-3 | required | GPU detection must not turn install into a brittle failure path. |
| AC-4 | important | Apple Silicon is common local developer hardware and should be evaluated when ONNX Runtime exposes CoreML. |
| AC-5 | required | CoreML availability must not create slower or incorrect default behavior. |
| AC-6 | important | Non-NVIDIA providers should be explicit and verifiable, not a misleading generic GPU tier. |
| AC-7 | required | Setup logs must match runtime behavior. |
| AC-8 | required | CI cannot depend on physical GPU hardware. |
| AC-9 | important | Operators need actionable guidance when hardware and provider state differ. |
| AC-10 | required | Framework script changes require full-suite verification. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-11 | Plan drafted from field feedback on NVIDIA GPU install using CPU-only embedding runtime. | Current code evidence: `setup_index.py` installs `fastembed`; `indexer.py` selects CUDA only when ONNX Runtime reports `CUDAExecutionProvider`. |
| 2026-06-11 | Added Apple Silicon/CoreML as an evaluated provider path, with correctness/performance gates before enablement. | Local Mac evidence: Apple M2 Max exposes `CoreMLExecutionProvider`, but current Wavefoundry code intentionally excludes it. |
| 2026-06-11 | Operator confirmed provider priority should be CUDA/NVIDIA, CoreML when verified, then explicit secondary provider families, then CPU. | Implemented as named ONNX provider candidates; no generic GPU bucket. |
| 2026-06-11 | Implemented shared provider policy, setup dependency planning, bounded provider probe, setup diagnostics, runtime provider reuse, docs, and mocked tests. | Added `provider_policy.py`; updated `setup_index.py`, `indexer.py`, `test_setup_index.py`, `test_indexer.py`, `docs/architecture/current-state.md`, `docs/architecture/chunking-and-indexing-pipeline.md`, and `docs/contributing/build-and-verification.md`. Verification: focused setup tests OK; provider-selection tests OK; `wave_validate` OK; full framework suite 3137 tests OK. |
| 2026-06-11 | Ran setup on the local macOS Apple Silicon machine. | `setup_index.py --root .` selected `CoreMLExecutionProvider` with providers `['CoreMLExecutionProvider', 'CPUExecutionProvider']`; available providers were `['CoreMLExecutionProvider', 'AzureExecutionProvider', 'CPUExecutionProvider']`; bounded probe measured CoreML `0.085s` vs CPU `0.096s`. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-11 | Prefer setup-time hardware-aware provider evaluation with verified fallback. | It fixes the install-time dependency gap while preserving runtime provider probing and safe CPU behavior. | Alternative 1: document manual `onnxruntime-gpu` installation only; weak because users still silently get CPU by default. Alternative 2: always install GPU dependencies; weak because it risks breaking CPU-only or unsupported systems and increases install complexity. Alternative 3: benchmark CPU vs GPU on every setup; weak because it can make setup slower and requires more moving parts than provider verification. |
| 2026-06-11 | Evaluate CoreML separately from CUDA and enable only after a bounded model-specific correctness/performance probe. | `CoreMLExecutionProvider` can exist on Apple Silicon, but availability is not enough to prove Wavefoundry's FastEmbed ONNX models benefit from it. | Alternative 1: keep CoreML out of scope; weak because Apple Silicon is common and ONNX Runtime exposes a plausible provider. Alternative 2: always use CoreML when available; weak because prior code excluded it for model-compatibility/performance reasons and it could regress users. |
| 2026-06-11 | Treat non-NVIDIA GPU support as named ONNX Runtime provider families, not a generic GPU tier. | DirectML, OpenVINO, MIGraphX, and ROCm have different platform/package constraints and should only activate after explicit availability and model probing. | A generic GPU fallback would be easier to describe but would hide incompatible provider semantics and make diagnostics less actionable. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| GPU package availability differs by OS, Python version, CUDA version, or package age guard. | Treat GPU as an opt-in-by-capability path with explicit fallback diagnostics; preserve CPU as default when verification fails. |
| `fastembed-gpu` and `onnxruntime-gpu` packaging constraints may conflict with the existing supply-chain age guard. | Discovery must confirm package compatibility before implementation; add tests for failed install planning. |
| Setup and runtime provider logic could drift. | Centralize or share provider probing where practical, and add tests that compare setup-reported and runtime-selected providers. |
| GPU detection could be noisy on machines with drivers installed but unusable CUDA runtime. | Verify provider availability through ONNX Runtime after installation, not hardware probe alone. |
| CoreML could be available but slower or numerically unsuitable for the active embedding model. | Require a bounded correctness and performance probe before selecting CoreML; otherwise keep CPU. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
