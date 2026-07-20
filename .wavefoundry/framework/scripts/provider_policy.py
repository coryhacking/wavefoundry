#!/usr/bin/env python3
"""Embedding execution-provider selection shared by setup and indexing."""
from __future__ import annotations

from dataclasses import dataclass
import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Callable, Iterable

import subprocess_util  # shared subprocess isolation (wave 1p8gu)

CPU_PROVIDER = "CPUExecutionProvider"
CUDA_PROVIDER = "CUDAExecutionProvider"
COREML_PROVIDER = "CoreMLExecutionProvider"

SECONDARY_PROVIDERS: tuple[str, ...] = (
    "DmlExecutionProvider",
    "OpenVINOExecutionProvider",
    "MIGraphXExecutionProvider",
    "ROCMExecutionProvider",
)

PROVIDER_PRIORITY: tuple[str, ...] = (
    CUDA_PROVIDER,
    COREML_PROVIDER,
    *SECONDARY_PROVIDERS,
)

PROVIDER_REQUESTS: dict[str, str] = {
    "cpu": CPU_PROVIDER,
    "cuda": CUDA_PROVIDER,
    "nvidia": CUDA_PROVIDER,
    "coreml": COREML_PROVIDER,
    "dml": "DmlExecutionProvider",
    "directml": "DmlExecutionProvider",
    "openvino": "OpenVINOExecutionProvider",
    "migraphx": "MIGraphXExecutionProvider",
    "rocm": "ROCMExecutionProvider",
}

SETUP_SELECTED_ENV = "WAVEFOUNDRY_EMBED_PROVIDER_SELECTED"
REQUESTED_PROVIDER_ENV = "WAVEFOUNDRY_EMBED_PROVIDER"


@dataclass(frozen=True)
class ProviderProbeResult:
    provider: str
    ok: bool
    reason: str
    candidate_seconds: float | None = None
    cpu_seconds: float | None = None


@dataclass(frozen=True)
class ProviderDecision:
    selected_provider: str
    providers: tuple[str, ...]
    available_providers: tuple[str, ...]
    reason: str
    remediation: str | None = None
    # Wave 1p9lj: where this decision came from — "setup-cache" (honoring the decision setup
    # recorded in WAVEFOUNDRY_EMBED_PROVIDER_SELECTED), "fresh-probe" (availability/probe run in
    # this process), or "operator-request" (WAVEFOUNDRY_EMBED_PROVIDER forced it). Setup and
    # wf_gpu_doctor share the same probe chain; process-scoped cache state is the one intentional
    # difference between them, so every decision names its source explicitly.
    provenance: str = "fresh-probe"


ProviderProbe = Callable[[str], ProviderProbeResult]


def available_onnx_providers() -> tuple[str, ...]:
    try:
        import onnxruntime as ort
        providers = ort.get_available_providers()
    except Exception:
        return (CPU_PROVIDER,)
    return tuple(str(provider) for provider in providers) or (CPU_PROVIDER,)


def nvidia_gpu_present() -> bool:
    nvidia_smi = shutil.which("nvidia-smi")
    if not nvidia_smi:
        return False
    try:
        result = subprocess_util.isolated_run(
            [nvidia_smi, "-L"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0 and bool(result.stdout.strip())


def apple_silicon_present() -> bool:
    return platform.system() == "Darwin" and platform.machine().lower() in {"arm64", "aarch64"}


def _dedupe_providers(providers: Iterable[str]) -> tuple[str, ...]:
    out: list[str] = []
    for provider in providers:
        if provider and provider not in out:
            out.append(provider)
    return tuple(out)


def _requested_provider(raw: str | None = None) -> str | None:
    token = (raw if raw is not None else os.environ.get(REQUESTED_PROVIDER_ENV, "auto")).strip().lower()
    if not token or token == "auto":
        return None
    return PROVIDER_REQUESTS.get(token)


def _cpu_decision(
    available: tuple[str, ...],
    reason: str,
    remediation: str | None = None,
    provenance: str = "fresh-probe",
) -> ProviderDecision:
    return ProviderDecision(
        selected_provider=CPU_PROVIDER,
        providers=(CPU_PROVIDER,),
        available_providers=available,
        reason=reason,
        remediation=remediation,
        provenance=provenance,
    )


def _provider_requires_probe(provider: str) -> bool:
    return provider != CUDA_PROVIDER


def select_embedding_providers(
    *,
    available_providers: Iterable[str] | None = None,
    provider_probe: ProviderProbe | None = None,
    requested_provider: str | None = None,
) -> ProviderDecision:
    """Return the ordered ONNX providers Wavefoundry should pass to FastEmbed.

    CUDA can be selected from provider availability alone because ONNX Runtime's
    CUDAExecutionProvider already proves the installed Python environment can
    see a CUDA-capable provider. CoreML and other platform providers need a
    model-specific probe because availability does not prove the active
    FastEmbed ONNX model is correct or faster on that backend.
    """
    available = _dedupe_providers(available_providers or available_onnx_providers())
    available_set = set(available)
    requested = _requested_provider(requested_provider)
    if requested == CPU_PROVIDER:
        return _cpu_decision(available, "operator forced CPU provider", provenance="operator-request")

    setup_selected = os.environ.get(SETUP_SELECTED_ENV)
    if setup_selected and not requested and setup_selected in available_set:
        if setup_selected == CPU_PROVIDER:
            return _cpu_decision(
                available, "CPU provider selected by setup probe", provenance="setup-cache"
            )
        return ProviderDecision(
            selected_provider=setup_selected,
            providers=_dedupe_providers((setup_selected, CPU_PROVIDER)),
            available_providers=available,
            reason=f"{setup_selected} selected by setup provider probe",
            provenance="setup-cache",
        )

    candidates = (requested,) if requested else PROVIDER_PRIORITY
    # A selection driven by WAVEFOUNDRY_EMBED_PROVIDER is operator-requested even when a probe
    # validates it; the bottom CPU fallback stays "fresh-probe" because there the probe failure,
    # not the operator, drove the outcome.
    success_provenance = "operator-request" if requested else "fresh-probe"
    probe_failures: list[str] = []
    for provider in candidates:
        if not provider:
            continue
        if provider not in available_set:
            probe_failures.append(f"{provider} unavailable")
            continue
        if provider == CPU_PROVIDER:
            return _cpu_decision(available, "operator forced CPU provider", provenance="operator-request")
        if provider == CUDA_PROVIDER:
            return ProviderDecision(
                selected_provider=provider,
                providers=_dedupe_providers((provider, CPU_PROVIDER)),
                available_providers=available,
                reason=f"{provider} available in ONNX Runtime",
                provenance=success_provenance,
            )
        if provider_probe is None and _provider_requires_probe(provider):
            probe_failures.append(f"{provider} requires a bounded model probe")
            continue
        if provider_probe is not None:
            probe = provider_probe(provider)
            if not probe.ok:
                probe_failures.append(f"{provider} probe failed: {probe.reason}")
                continue
            reason = probe.reason or f"{provider} passed provider probe"
        else:
            reason = f"{provider} available in ONNX Runtime"
        return ProviderDecision(
            selected_provider=provider,
            providers=_dedupe_providers((provider, CPU_PROVIDER)),
            available_providers=available,
            reason=reason,
            provenance=success_provenance,
        )

    remediation = None
    if nvidia_gpu_present() and CUDA_PROVIDER not in available_set:
        remediation = (
            "NVIDIA GPU detected, but CUDAExecutionProvider is not available. "
            "Install a CUDA-capable FastEmbed/ONNX Runtime stack such as fastembed-gpu "
            "for faster embedding, then rerun setup."
        )
    reason = "no verified GPU execution provider; using CPU"
    if probe_failures:
        reason = f"{reason} ({'; '.join(probe_failures)})"
    return _cpu_decision(available, reason, remediation)


# --- CUDA 12-vs-13 ABI gap (wave 1p5py) -----------------------------------
# PyPI onnxruntime-gpu (<=1.26) is built against the CUDA 12 ABI and hard-links
# libcublasLt.so.12 / libcublas.so.12. Arch/CachyOS/Manjaro ship only CUDA 13
# (libcublasLt.so.13), so ORT's CUDAExecutionProvider is *listed* (compiled in)
# but fails to dlopen at session creation → silent CPU fallback. We detect the
# gap (NVIDIA present + .so.12 absent + .so.13 present) and surface a loud,
# accurate remediation rather than falling back silently. NOTE (1p5qp/091yp): a
# soname symlink (.so.13 → .so.12) does NOT work — CUDA 13's cuBLAS exports
# different ELF VERNEED version symbols, so the loader rejects it. The shim was
# removed; this is detection + warning only (build-from-source is the real fix).
_CUDA12_REQUIRED_STEMS: tuple[str, ...] = ("libcublasLt.so", "libcublas.so")
_CUDA_LIB_SEARCH_DIRS: tuple[str, ...] = (
    "/opt/cuda/lib64",
    "/opt/cuda/targets/x86_64-linux/lib",
    "/usr/local/cuda/lib64",
    "/usr/local/cuda/targets/x86_64-linux/lib",
    "/usr/lib64",
    "/usr/lib",
    "/usr/lib/x86_64-linux-gnu",
)


@dataclass(frozen=True)
class Cuda12AbiGap:
    """A detected CUDA 12-ABI gap: ORT needs `.so.12` libs the system only has as `.so.13`."""
    missing: tuple[str, ...]              # e.g. ("libcublasLt.so.12", "libcublas.so.12")
    so13_by_target: dict[str, str]        # {"libcublasLt.so.12": "/opt/cuda/lib64/libcublasLt.so.13"}
    remediation: str


def _ldconfig_lib_paths() -> dict[str, str]:
    """Best-effort {basename: path} from `ldconfig -p`. Empty on any failure."""
    ldconfig = shutil.which("ldconfig") or "/sbin/ldconfig"
    try:
        result = subprocess_util.isolated_run(
            [ldconfig, "-p"], capture_output=True, text=True, timeout=3, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {}
    out: dict[str, str] = {}
    for line in result.stdout.splitlines():
        # "\tlibcublasLt.so.12 (libc6,x86-64) => /usr/lib/libcublasLt.so.12"
        if "=>" not in line:
            continue
        left, _, path = line.partition("=>")
        name = left.strip().split(" ", 1)[0]
        path = path.strip()
        if name and path and name not in out:
            out[name] = path
    return out


def _find_versioned_lib(name: str, ldcache: dict[str, str]) -> str | None:
    """Resolve a versioned lib basename (e.g. libcublasLt.so.12) to a path, or None."""
    if name in ldcache:
        return ldcache[name]
    for d in _CUDA_LIB_SEARCH_DIRS:
        candidate = Path(d) / name
        if candidate.exists():
            return str(candidate)
    return None


def detect_cuda12_abi_gap(
    *,
    is_linux: bool | None = None,
    has_nvidia: bool | None = None,
    find_lib: Callable[[str], str | None] | None = None,
) -> Cuda12AbiGap | None:
    """Detect the CUDA 12-vs-13 ABI gap. Returns a Cuda12AbiGap, or None when not applicable.

    Linux + NVIDIA only. The gap exists when a required `.so.12` cublas lib is absent
    but its `.so.13` counterpart is present. Params are injectable for testing.
    """
    if is_linux is None:
        is_linux = platform.system() == "Linux"
    if not is_linux:
        return None
    if has_nvidia is None:
        has_nvidia = nvidia_gpu_present()
    if not has_nvidia:
        return None
    if find_lib is None:
        ldcache = _ldconfig_lib_paths()
        find_lib = lambda name: _find_versioned_lib(name, ldcache)

    missing: list[str] = []
    so13_by_target: dict[str, str] = {}
    for stem in _CUDA12_REQUIRED_STEMS:
        if find_lib(f"{stem}.12") is not None:
            continue  # .so.12 present — no gap for this lib
        so13 = find_lib(f"{stem}.13")
        if so13:
            target = f"{stem}.12"
            missing.append(target)
            so13_by_target[target] = so13
    if not missing:
        return None
    found = ", ".join(sorted(so13_by_target.values()))
    remediation = (
        "NVIDIA GPU detected but the CUDA execution provider cannot load: onnxruntime-gpu (PyPI) is "
        f"built against the CUDA 12 ABI ({', '.join(missing)}) and this system has only the CUDA 13 "
        f"runtime ({found}). A soname symlink (.so.13 → .so.12) does NOT fix this — CUDA 13's cuBLAS "
        "exports different ELF version symbols (VERNEED), so the dynamic loader rejects the mismatched "
        "library. Embedding/indexing is running on CPU (5–10× slower on large repos). To use the GPU: "
        "build onnxruntime-gpu from source against CUDA 13, or install a CUDA-13-built wheel once one is "
        "published. Set WAVEFOUNDRY_EMBED_PROVIDER=cpu to silence this and run on CPU intentionally."
    )
    return Cuda12AbiGap(tuple(missing), so13_by_target, remediation)


# Wave 1p5py / 1p5qp: the venv-local `.so.12 → .so.13` symlink shim was REMOVED.
# Field validation (091yp, RTX 5070 Ti / CUDA 13.3) confirmed CUDA 13's cuBLAS
# exports different ELF version symbols (VERNEED) than CUDA 12, so a soname
# symlink is rejected by the loader — it cannot work and risks loading a
# mismatched library. The detection (`detect_cuda12_abi_gap`) remains and now
# drives a loud, accurate operator warning only (build-from-source / await a
# CUDA-13 wheel). See `accel_embedder._warn_cuda12_gap_if_present`.


def format_provider_decision(decision: ProviderDecision) -> str:
    parts = [
        f"Embedding provider: selected={decision.selected_provider}",
        f"providers={list(decision.providers)}",
        f"available={list(decision.available_providers)}",
        f"reason={decision.reason}",
        f"decision-source={decision.provenance}",
    ]
    if decision.remediation:
        parts.append(f"remediation={decision.remediation}")
    return "; ".join(parts)


# Wave 1p6et: REMOTE / inert ORT execution providers that Wavefoundry never selects (local-only).
# AzureExecutionProvider proxies inference to a cloud Azure ML endpoint; it ships compiled into the
# stock onnxruntime wheel so it appears in get_available_providers() even with no Azure config.
# Excluded from the diagnostic's `available_onnx_providers` DISPLAY so it isn't mistaken for a usable
# local backend. Selection already ignores it (not in PROVIDER_PRIORITY / PROVIDER_REQUESTS).
_REMOTE_INERT_PROVIDERS = frozenset({"AzureExecutionProvider"})


def diagnostic_report(provider_probe: "ProviderProbe | None" = None) -> dict:
    """Wave 1p6et: structured embedding-provider / GPU capability snapshot for the `setup-wavefoundry --check-gpu`
    CLI and the `wf_gpu_doctor` MCP tool.

    When ``provider_probe`` is supplied (the CLI + MCP pass setup's ``_probe_embedding_provider``),
    the selection runs the SAME bounded model probe setup uses — so probe-required providers
    (CoreML / ROCm / OpenVINO / DML) are confirmed and ``selected_provider`` matches what setup/runtime
    actually pick (e.g. CoreML on Apple Silicon). This LOADS a model (~seconds; needs the model cached,
    else it degrades gracefully to CPU). Without a probe it is the fast no-probe view (CUDA/CPU exact;
    probe-required providers visible only via ``available_onnx_providers``). Pre-setup safe: onnxruntime
    absent → ``onnxruntime_version`` None and the provider set degrades to CPU.
    """
    ort_version = None
    try:
        import onnxruntime as _ort
        ort_version = getattr(_ort, "__version__", None)
    except Exception:  # noqa: BLE001 — ORT may be absent (pre-setup); report None, don't raise
        ort_version = None
    decision = select_embedding_providers(provider_probe=provider_probe)
    gap = detect_cuda12_abi_gap()
    available = [p for p in available_onnx_providers() if p not in _REMOTE_INERT_PROVIDERS]
    return {
        "platform": {"system": platform.system(), "machine": platform.machine()},
        "onnxruntime_version": ort_version,
        "requested_provider_env": os.environ.get(REQUESTED_PROVIDER_ENV, ""),
        "nvidia_gpu_present": nvidia_gpu_present(),
        "apple_silicon_present": apple_silicon_present(),
        "available_onnx_providers": available,
        "selected_provider": decision.selected_provider,
        "providers": list(decision.providers),
        "selection_reason": decision.reason,
        "selection_remediation": decision.remediation,
        "decision_provenance": decision.provenance,
        "cuda12_abi_gap": str(gap) if gap else None,
    }


def format_diagnostic_report(report: dict) -> str:
    """Human-readable rendering of :func:`diagnostic_report` for the `setup-wavefoundry --check-gpu` CLI."""
    plat = report.get("platform", {})
    lines = [
        "Wavefoundry embedding-provider / GPU diagnostic",
        f"  platform                  : {plat.get('system')} {plat.get('machine')}",
        f"  onnxruntime               : {report.get('onnxruntime_version') or 'NOT INSTALLED'}",
        f"  WAVEFOUNDRY_EMBED_PROVIDER : {report.get('requested_provider_env') or '(auto)'}",
        f"  nvidia GPU                : {report.get('nvidia_gpu_present')}",
        f"  apple silicon             : {report.get('apple_silicon_present')}",
        f"  ORT providers             : {', '.join(report.get('available_onnx_providers') or [])}",
        f"  would select              : {report.get('selected_provider')}",
        f"    reason                  : {report.get('selection_reason')}",
        f"    decision source         : {report.get('decision_provenance') or 'fresh-probe'}",
    ]
    if report.get("selection_remediation"):
        lines.append(f"    remediation             : {report['selection_remediation']}")
    gap = report.get("cuda12_abi_gap")
    lines.append(f"  CUDA 12/13 ABI gap        : {('DETECTED -> ' + gap) if gap else 'no'}")
    return "\n".join(lines)
