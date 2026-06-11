#!/usr/bin/env python3
"""Embedding execution-provider selection shared by setup and indexing."""
from __future__ import annotations

from dataclasses import dataclass
import os
import platform
import shutil
import subprocess
from typing import Callable, Iterable

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
        result = subprocess.run(
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


def _cpu_decision(available: tuple[str, ...], reason: str, remediation: str | None = None) -> ProviderDecision:
    return ProviderDecision(
        selected_provider=CPU_PROVIDER,
        providers=(CPU_PROVIDER,),
        available_providers=available,
        reason=reason,
        remediation=remediation,
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
        return _cpu_decision(available, "operator forced CPU provider")

    setup_selected = os.environ.get(SETUP_SELECTED_ENV)
    if setup_selected and not requested and setup_selected in available_set:
        if setup_selected == CPU_PROVIDER:
            return _cpu_decision(available, "CPU provider selected by setup probe")
        return ProviderDecision(
            selected_provider=setup_selected,
            providers=_dedupe_providers((setup_selected, CPU_PROVIDER)),
            available_providers=available,
            reason=f"{setup_selected} selected by setup provider probe",
        )

    candidates = (requested,) if requested else PROVIDER_PRIORITY
    probe_failures: list[str] = []
    for provider in candidates:
        if not provider:
            continue
        if provider not in available_set:
            probe_failures.append(f"{provider} unavailable")
            continue
        if provider == CPU_PROVIDER:
            return _cpu_decision(available, "operator forced CPU provider")
        if provider == CUDA_PROVIDER:
            return ProviderDecision(
                selected_provider=provider,
                providers=_dedupe_providers((provider, CPU_PROVIDER)),
                available_providers=available,
                reason=f"{provider} available in ONNX Runtime",
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


def format_provider_decision(decision: ProviderDecision) -> str:
    parts = [
        f"Embedding provider: selected={decision.selected_provider}",
        f"providers={list(decision.providers)}",
        f"available={list(decision.available_providers)}",
        f"reason={decision.reason}",
    ]
    if decision.remediation:
        parts.append(f"remediation={decision.remediation}")
    return "; ".join(parts)
