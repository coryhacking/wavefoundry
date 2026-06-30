"""Wave 1p517: bespoke static-shape ONNX embedder for GPU providers (CoreML / CUDA).

Why this exists: fastembed feeds onnxruntime a DYNAMIC-shape graph, which CoreML cannot
accelerate — it falls back to CPU (the GPU sits idle). Pinning the model's input dims to a
fixed ``(64, 512)`` lets CoreML compile an FP16 MLProgram that runs on the GPU. Benchmarked
~24x over INT8/CPU at cos = 1.0 vs the CPU path (M2 Max, arctic-embed-xs).

This module loads the model's EXISTING cached ONNX (bge-small is already FP16, arctic is
FP32 — CoreML downcasts FP32 to FP16 itself, so NO conversion is needed), pins it to the
static shape, and runs a raw ``onnxruntime.InferenceSession`` with CoreML's
``ModelCacheDirectory`` so the ~compile is paid once and persisted across processes.

Pooling is **CLS** ([:, 0]) + L2-normalize — matching fastembed exactly for both shipped
models (verified cos = 1.0000; mean-pooling was 0.88–0.95 and would corrupt the index).

CPU machines never reach this module: ``make_embedder`` returns ``None`` unless a GPU
provider was selected (and the ``1p4u5`` probe passed), and the caller falls back to fastembed.
"""
from __future__ import annotations

import glob
import os
import sys
from pathlib import Path
from typing import Iterable, Iterator, Optional

STATIC_BATCH = 64
# Wave 1p66v: the reranker's static batch is decoupled from the embedder's. The embedder
# bulk-processes many chunks at index time (64 amortizes well); the cross-encoder reranker
# scores a query-time pool that maxes at the code_ask candidate ceiling (AGENT_CANDIDATE_MAX
# = 40). Benchmarked {24,32,40} × pool {24,32,40} on M2 Max CoreML — 40 wins decisively
# (single pass at ~107ms for ANY pool ≤ 40), because the moment a smaller batch is exceeded
# by the pool it pays a second forward pass (~255–295ms) that dwarfs the padding it saves;
# 40 also beats the old shared 64 (~167ms — 64 pads 40→64, more wasted rows). So size the
# reranker batch to exactly cover the ceiling in one pass. Batch is a latency/compute knob
# only — ranking output is identical across sizes (the same pairs get the same logits). The
# static-graph cache key includes the batch dim, so changing this builds its own cached graph.
RERANK_STATIC_BATCH = 40
STATIC_SEQ = 512

COREML_PROVIDER = "CoreMLExecutionProvider"
CUDA_PROVIDER = "CUDAExecutionProvider"
ROCM_PROVIDER = "ROCMExecutionProvider"      # AMD GPUs
DML_PROVIDER = "DmlExecutionProvider"        # DirectML (Windows: NVIDIA/AMD/Intel)
# GPU providers we attempt, in preference order. CoreML needs the MLProgram/cache options below;
# every other GPU EP (CUDA/ROCm/DirectML) takes the provider name with default options. The
# static-shape pin + the ``offloads_to_gpu`` probe make this self-protecting: a provider that isn't
# installed, or doesn't actually offload the graph, degrades to ``None`` (fastembed / no rerank).
GPU_PROVIDERS = (COREML_PROVIDER, CUDA_PROVIDER, ROCM_PROVIDER, DML_PROVIDER)

_HOME = Path.home() / ".wavefoundry"
_ONNX_CACHE = _HOME / "cache" / "onnx"
_COREML_CACHE = _HOME / "cache" / "coreml"

# fastembed downloads some models under a different repo dir than the public model ID
# (mirrors setup_index._MODEL_CACHE_DIR_ALIASES — keep in sync).
_MODEL_CACHE_DIR_ALIASES: dict[str, tuple[str, ...]] = {
    "BAAI/bge-small-en-v1.5": ("qdrant/bge-small-en-v1.5-onnx-q",),
    "BAAI/bge-base-en-v1.5": ("qdrant/bge-base-en-v1.5-onnx-q",),
    "Snowflake/snowflake-arctic-embed-xs": ("snowflake/snowflake-arctic-embed-xs",),
}

# Some models' fastembed-resident ONNX is CoreML-HOSTILE: it's a heavily-optimized graph with
# ``com.microsoft`` contrib fused ops (Attention / SkipLayerNormalization / FastGelu) that the
# CoreML EP cannot run, so it shatters into dozens of CPU partitions (bge-small: 42/92 nodes, 38
# partitions → CPU-bound). A clean transformers.js export (decomposed standard ops) runs as a
# single CoreML partition on the GPU. Maps model → (hf_repo, onnx_file, tokenizer_file). The
# clean export's vectors are cos = 1.0 vs fastembed (same weights, CLS pooling).
CLEAN_ONNX_SOURCES: dict[str, tuple[str, str, str]] = {
    "BAAI/bge-small-en-v1.5": ("Xenova/bge-small-en-v1.5", "onnx/model_fp16.onnx", "tokenizer.json"),
    # 1p52p: the cross-encoder reranker (GPU FP16 / CPU INT8 — see _resolve_reranker_cpu_files). The active reranker is
    # ``ms-marco-MiniLM-L-6-v2`` (6-layer, 22M) via its Xenova FP16 export — chosen over the SOTA-but-
    # heavy ``bge-reranker-base`` (278M) after a head-to-head: ms-marco-L6 won known-answer recall
    # (mean rank 1.07 vs 1.67), runs ~4-5x faster (~380ms vs ~1650ms/query), uses ~8x less memory
    # (0.77 GB vs 6.3 GB RSS), and — unlike bge — the CoreML ``ModelCacheDirectory`` actually
    # accelerates restarts (3.1s warm vs 17s cold; bge stayed ~26s because CoreML re-specializes its
    # 2 GB MLProgram every session regardless of cache). bge's entry is kept resolvable for back-compat.
    "cross-encoder/ms-marco-MiniLM-L-6-v2": ("Xenova/ms-marco-MiniLM-L-6-v2", "onnx/model_fp16.onnx", "tokenizer.json"),
    "BAAI/bge-reranker-base": ("Xenova/bge-reranker-base", "onnx/model_fp16.onnx", "tokenizer.json"),
}
_CLEAN_ONNX_CACHE = _HOME / "cache" / "onnx-src"


def _fastembed_cache_dir() -> Path:
    return Path(os.getenv("FASTEMBED_CACHE_PATH") or str(_HOME / "cache" / "fastembed"))


def _model_repo_dir(model_name: str) -> Optional[Path]:
    base = _fastembed_cache_dir()
    for nm in (model_name, *_MODEL_CACHE_DIR_ALIASES.get(model_name, ())):
        d = base / f"models--{nm.replace('/', '--')}"
        if d.is_dir():
            return d
    return None


def _hf_download_cached_first(repo: str, filename: str, cache_dir: str) -> str:
    """Resolve a Hub file from the local cache first, downloading only if it isn't cached.

    Wave 1p5cx: a plain ``hf_hub_download`` makes an online metadata round-trip (revision/etag
    check) on EVERY call even when the file is cached — which emits the per-process
    ``unauthenticated requests to the HF Hub`` warning and adds latency to every reindex (the
    launcher prewarms these models on each spawn). ``local_files_only=True`` returns the cached
    path with no network; only if the file isn't cached do we fall back to an online download
    (then it's cached for next time). This is the standard HF idiom — no global offline state."""
    from huggingface_hub import hf_hub_download
    try:
        return hf_hub_download(repo, filename, cache_dir=cache_dir, local_files_only=True)
    except Exception:
        pass
    # Wave 1p939: this is a non-setup launcher (MCP wave_index_build, dashboard watcher, background
    # refresh) — apply the same CA ladder wf setup uses before the online attempt, once per process,
    # then fall back through the same reactive candidate ladder _warm_model uses on a cert-verify
    # failure (delivery-phase council finding: the proactive step alone isn't full ladder parity).
    import setup_index
    setup_index.ensure_ca_bundle_applied()
    return setup_index.retry_with_ca_bundle_ladder(
        lambda: hf_hub_download(repo, filename, cache_dir=cache_dir), repo,
    )


def _resolve_clean_onnx(model_name: str) -> Optional[tuple[str, str]]:
    """For a CoreML-hostile model, return (clean_onnx_path, tokenizer_path) from a clean export,
    downloading + caching it under ``~/.wavefoundry/cache/onnx-src`` (cached-first; no network when
    already present). None when the model has no clean source, or it isn't cached and the machine is
    offline.
    """
    src = CLEAN_ONNX_SOURCES.get(model_name)
    if src is None:
        return None
    repo, onnx_file, tok_file = src
    try:
        onnx_path = _hf_download_cached_first(repo, onnx_file, str(_CLEAN_ONNX_CACHE))
        tok_path = _hf_download_cached_first(repo, tok_file, str(_CLEAN_ONNX_CACHE))
    except Exception as exc:
        # Wave 1p939 (delivery-phase fix): log before degrading so a persisting CA-trust failure
        # is operator-visible instead of silently looking like a GPU/accel failure (the diagnostic
        # _hf_download_cached_first raises would otherwise be discarded here with no trace).
        print(f"[wavefoundry] clean ONNX fetch for {model_name!r} failed ({exc}); falling back to "
              "the resident model path.", file=sys.stderr, flush=True)
        return None
    return os.path.realpath(onnx_path), tok_path


def _ensure_fastembed_model_cached(model_name: str) -> None:
    """Cold-cache safety: download the model's fastembed-resident ONNX if it isn't cached yet.

    Without this, a model whose resident graph we use directly (e.g. arctic — no
    ``CLEAN_ONNX_SOURCES`` entry, so no self-downloading ``hf_hub_download`` path) silently
    fails the static-shape build whenever a launcher spawns the indexer WITHOUT first running
    ``setup_index.prewarm_models`` — most notably the dashboard's file-watcher, which spawns
    ``indexer.py --content all`` directly. The accel build then returns ``None`` and the whole
    docs layer falls back to fastembed on CPU. Fetching the resident model here (idempotent;
    a no-op once cached, honors HF offline) makes the GPU path robust for every launcher, not
    just the ones that prewarm. Uses fastembed itself so the weights are byte-identical to the
    CPU fallback path (no risk of a different export changing the vectors)."""
    try:
        from fastembed import TextEmbedding
        cache_dir = str(_fastembed_cache_dir())
        # Wave 1p5cx: cached-first so an already-warm model makes no Hub round-trip (no
        # unauthenticated-request warning); download only on a genuine cache miss.
        try:
            TextEmbedding(model_name=model_name, cache_dir=cache_dir, local_files_only=True)
        except Exception:
            # Wave 1p939: apply the same CA ladder wf setup uses before the online attempt, then
            # fall back through the reactive candidate ladder on a persisting cert-verify failure
            # (delivery-phase fix: this was the one named call site still missing ladder parity).
            import setup_index
            setup_index.ensure_ca_bundle_applied()
            try:
                setup_index.retry_with_ca_bundle_ladder(
                    lambda: TextEmbedding(model_name=model_name, cache_dir=cache_dir), model_name,
                )
            except Exception as exc:
                # Log before this function's own best-effort swallow degrades to the CPU path —
                # see _resolve_clean_onnx.
                print(f"[wavefoundry] resident model fetch for {model_name!r} failed ({exc}); "
                      "falling back to the CPU embedder path.", file=sys.stderr, flush=True)
                raise
    except Exception:
        pass


def _resolve_model_files(model_name: str) -> Optional[tuple[str, str]]:
    """Return (onnx_path, tokenizer_json_path) for the embedder.

    Prefers a CoreML-friendly clean export (``CLEAN_ONNX_SOURCES``) when one is registered;
    otherwise uses the model's fastembed-resident ONNX (arctic's resident graph is already clean),
    downloading it on a cold cache so the GPU path doesn't degrade to CPU when prewarm was skipped.
    """
    clean = _resolve_clean_onnx(model_name)
    if clean is not None:
        return clean
    repo = _model_repo_dir(model_name)
    if repo is None:
        # Cold cache + a launcher that skipped prewarm: fetch the resident model, then retry.
        _ensure_fastembed_model_cached(model_name)
        repo = _model_repo_dir(model_name)
    if repo is None:
        return None
    onnx_files = glob.glob(str(repo / "snapshots" / "*" / "**" / "*.onnx"), recursive=True)
    tok_files = glob.glob(str(repo / "snapshots" / "*" / "tokenizer.json"))
    if not onnx_files or not tok_files:
        return None
    return os.path.realpath(onnx_files[0]), tok_files[0]


# Wave 1p52p (CPU fallback): a small cross-encoder reranker also runs usefully on the CPU EP — but
# the FP16 export fails to init at ORT_ENABLE_ALL (a SimplifiedLayerNormFusion cast bug) and is slow,
# while the INT8 export runs at full optimization and is ~2x faster than FP32 with no ranking loss
# (ms-marco-L6: all known answers still rank #1). So the CPU path uses the INT8 export of the same repo.
RERANKER_CPU_ONNX_FILE = "onnx/model_int8.onnx"


def _resolve_reranker_cpu_files(model_name: str) -> Optional[tuple[str, str]]:
    """Return (int8_onnx_path, tokenizer_path) for the CPU reranker fallback, from the same clean repo
    as the GPU FP16 export. Downloads + caches under ``onnx-src`` (HF-offline-safe). None when the
    model has no clean source or the INT8 export isn't reachable."""
    src = CLEAN_ONNX_SOURCES.get(model_name)
    if src is None:
        return None
    repo, _fp16_file, tok_file = src
    try:
        onnx_path = _hf_download_cached_first(repo, RERANKER_CPU_ONNX_FILE, str(_CLEAN_ONNX_CACHE))
        tok_path = _hf_download_cached_first(repo, tok_file, str(_CLEAN_ONNX_CACHE))
    except Exception as exc:
        # Wave 1p939 (delivery-phase fix): log before degrading — see _resolve_clean_onnx.
        print(f"[wavefoundry] reranker CPU ONNX fetch for {model_name!r} failed ({exc}); falling "
              "back to the resident model path.", file=sys.stderr, flush=True)
        return None
    return os.path.realpath(onnx_path), tok_path


def _safe(model_name: str) -> str:
    return model_name.replace("/", "__")


def build_static_onnx(
    src_onnx: str,
    out_path: str,
    batch: int = STATIC_BATCH,
    seq: int = STATIC_SEQ,
    output_is_logit: bool = False,
) -> str:
    """Pin the model's symbolic batch/seq input+output dims to a fixed (batch, seq).

    Sets the dims directly on the protobuf rather than via
    ``onnx.tools.update_model_dims.update_inputs_outputs_dims`` — the latter runs a strict
    ``check_model`` that rejects some fastembed-optimized graphs (e.g. bge-small's
    ``LayerNormalization`` declared at opset 11). ORT re-infers the internal shapes from the
    fixed inputs. Requires ``onnx``.

    ``output_is_logit`` (1p52p, cross-encoder reranker): the output is a relevance logit
    ``[batch, 1]``, so pin only dim0=batch — pinning dim1 would clobber the singleton score dim.
    The bi-encoder embedder output is ``[batch, seq, hidden]`` and pins dim0+dim1 (the default).
    """
    import onnx

    def _pin(value_infos, *, pin_second: bool) -> None:
        for vi in value_infos:
            dims = vi.type.tensor_type.shape.dim
            if len(dims) >= 1:
                dims[0].dim_value = batch
                dims[0].ClearField("dim_param")
            if pin_second and len(dims) >= 2:
                dims[1].dim_value = seq
                dims[1].ClearField("dim_param")
            # any 3rd dim (hidden size) is left untouched

    model = onnx.load(src_onnx)
    _pin(model.graph.input, pin_second=True)             # input_ids / attention_mask / token_type_ids → [batch, seq]
    _pin([model.graph.output[0]], pin_second=not output_is_logit)  # [batch,seq,hidden] | logit [batch,1]
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    # Atomic publish: a concurrent reader (another indexer subprocess, or the server lazily building the
    # reranker while setup_index prewarms the same model) must never mmap a half-written graph → ORT
    # abort/segfault. Write to a private temp path, then os.replace (atomic on the same filesystem).
    # Last writer wins and both builds are byte-identical, so the race is benign once torn reads can't happen.
    tmp_path = f"{out_path}.tmp.{os.getpid()}"
    onnx.save(model, tmp_path)
    os.replace(tmp_path, out_path)
    return out_path


class StaticShapeEmbedder:
    """fastembed-compatible embedder backed by a static-shape ONNX on a GPU provider.

    ``embed(texts)`` yields one L2-normalized CLS vector per text (matching fastembed's
    ``TextEmbedding.embed``), batching internally to the fixed ``STATIC_BATCH``.
    """

    def __init__(self, model_name: str, providers: Iterable[str]) -> None:
        import numpy as np  # noqa: F401  (import-time availability check)
        import onnxruntime as ort
        from tokenizers import Tokenizer

        files = _resolve_model_files(model_name)
        if files is None:
            raise FileNotFoundError(f"No cached ONNX/tokenizer for {model_name!r}")
        src_onnx, tok_path = files

        gpu = next((p for p in providers if p in GPU_PROVIDERS), None)
        if gpu is None:
            raise ValueError("StaticShapeEmbedder requires a GPU provider")

        # COREML_CACHE_KEY: model + provider + format + compute-units in the path, so any
        # change uses a fresh cache dir (ORT does no automatic staleness check).
        compute_units = "ALL"
        model_format = "MLProgram"
        static_path = _ONNX_CACHE / _safe(model_name) / f"static_{STATIC_BATCH}x{STATIC_SEQ}.onnx"
        if not static_path.exists():
            build_static_onnx(src_onnx, str(static_path))

        so = ort.SessionOptions()
        so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        provs: list = []
        if gpu == COREML_PROVIDER:
            coreml_cache = _COREML_CACHE / _safe(model_name) / f"{model_format}_{compute_units}"
            os.makedirs(coreml_cache, exist_ok=True)
            provs.append((COREML_PROVIDER, {
                "ModelFormat": model_format,
                "MLComputeUnits": compute_units,
                "ModelCacheDirectory": str(coreml_cache),
            }))
        else:  # CUDA / ROCm / DirectML — static shapes help; no compiled-model cache option
            provs.append(gpu)
        provs.append("CPUExecutionProvider")

        self.model_name = model_name
        self.provider = gpu
        self.session = ort.InferenceSession(str(static_path), sess_options=so, providers=provs)
        self.input_names = [i.name for i in self.session.get_inputs()]
        self.tokenizer = Tokenizer.from_file(tok_path)
        self.tokenizer.enable_truncation(max_length=STATIC_SEQ)
        self.tokenizer.enable_padding(length=STATIC_SEQ)

    def embed(self, texts: Iterable[str], batch_size: Optional[int] = None, **_: object) -> Iterator["np.ndarray"]:  # type: ignore[name-defined]
        import numpy as np

        items = [t if isinstance(t, str) else str(t) for t in texts]
        for start in range(0, len(items), STATIC_BATCH):
            chunk = items[start:start + STATIC_BATCH]
            real = len(chunk)
            # Pad the batch dim to the fixed STATIC_BATCH (empty strings; sliced off below).
            padded = chunk + [""] * (STATIC_BATCH - real) if real < STATIC_BATCH else chunk
            enc = self.tokenizer.encode_batch(padded)
            feats = {
                "input_ids": np.array([e.ids for e in enc], dtype=np.int64),
                "attention_mask": np.array([e.attention_mask for e in enc], dtype=np.int64),
                "token_type_ids": np.array([e.type_ids for e in enc], dtype=np.int64),
            }
            feed = {n: feats[n] for n in self.input_names}
            hidden = self.session.run(None, feed)[0]            # [STATIC_BATCH, STATIC_SEQ, H]
            cls = hidden[:, 0, :].astype(np.float32)            # CLS pooling (matches fastembed)
            cls /= np.clip(np.linalg.norm(cls, axis=1, keepdims=True), 1e-9, None)
            for r in range(real):
                yield cls[r]

    def offloads_to_gpu(self, threshold: float = 1.5) -> bool:
        """Return True if a full batch actually runs on the GPU (not CPU fallback).

        Not every model's graph is GPU-friendly: a fastembed-*optimized* graph (e.g. bge-small's
        fused ``LayerNormalization``) shatters into many CoreML/CPU partitions and runs CPU-bound,
        which is no faster than fastembed. We measure the CPU-time/wall-time ratio of a warm batch —
        a GPU-offloaded run leaves the CPU near-idle (ratio « 1); a CPU-bound run pegs cores (ratio » 1).
        The first call also pays the one-time CoreML compile (warmup).
        """
        import time

        probe = ["warmup probe sentence for hardware offload measurement"] * STATIC_BATCH
        list(self.embed(probe))  # warmup / compile
        wall0, cpu0 = time.time(), time.process_time()
        for _ in range(2):
            list(self.embed(probe))
        wall, cpu = time.time() - wall0, time.process_time() - cpu0
        return wall > 0 and (cpu / wall) < threshold


def _available_gpu_providers() -> list[str]:
    """GPU providers actually available in this onnxruntime, honoring an explicit CPU request.

    The accel path is gated by AVAILABILITY (not the fastembed-based 1p4u5 provider probe): that
    probe loads the model with ``local_files_only`` and transiently fails on a fresh/cleared model
    cache (model not downloaded yet) → CPU fallback. The static-shape path doesn't use fastembed and
    has its own ``offloads_to_gpu`` gate, so it must not be disabled by that probe.
    """
    if os.environ.get("WAVEFOUNDRY_EMBED_PROVIDER", "auto").strip().lower() == "cpu":
        return []
    try:
        import onnxruntime as ort
        available = set(ort.get_available_providers())
    except Exception:
        return []
    return [p for p in GPU_PROVIDERS if p in available]


# Wave 1p5py (revised 1p5qp per field report 091yp/091yn): CUDA 12-vs-13 ABI gap.
# On Arch/CachyOS-style hosts onnxruntime-gpu is built for the CUDA 12 ABI but the
# system has only CUDA 13, so the CUDA provider can't load and the GPU sits idle.
# We do NOT attempt a symlink shim — CUDA 13's cuBLAS exports different ELF version
# symbols (VERNEED) than CUDA 12, so a .so.13→.so.12 symlink is rejected by the
# loader (091yp). Instead we detect the gap on the FILESYSTEM (not via the linker
# path) and surface a loud, accurate one-time warning so the install/upgrade agent
# never sees a silent CPU fallback — even when ORT doesn't list CUDA at all (091yn).
_cuda12_gap_warned = False


def _warn_cuda12_gap_once(remediation: str) -> None:
    global _cuda12_gap_warned
    if _cuda12_gap_warned:
        return
    _cuda12_gap_warned = True
    print(f"[wavefoundry][GPU] WARNING: {remediation}", file=sys.stderr, flush=True)


def _warn_cuda12_gap_if_present() -> None:
    """Filesystem-probe for the CUDA 12-ABI gap and surface a one-time warning. Never raises.

    Detection is filesystem-based (`provider_policy.detect_cuda12_abi_gap`), so it fires even
    when the CUDA libs aren't on the linker path and ORT doesn't list CUDAExecutionProvider at
    all (091yn — the silent-on-fresh-Arch case). No shim is attempted (091yp).
    """
    try:
        import provider_policy as pp
        gap = pp.detect_cuda12_abi_gap()
    except Exception:
        return
    if gap is not None:
        _warn_cuda12_gap_once(gap.remediation)


def make_embedder(model_name: str, providers: Iterable[str]):
    """Return a ``StaticShapeEmbedder`` when a GPU runs this model's graph faster than CPU;
    otherwise ``None`` so the caller falls back to fastembed.

    The GPU provider is taken from ``providers`` (the 1p4u5 selection) if present, else from what's
    actually AVAILABLE — so a transient fastembed-probe failure (e.g. fresh cache) doesn't disable
    acceleration. Never raises — any failure (no GPU, missing ``onnx``/model, fragmented graph)
    degrades to ``None`` (fastembed CPU path). When an NVIDIA GPU is present but CUDA can't load
    (the CUDA 12-vs-13 ABI gap), surfaces a loud warning instead of a silent CPU fallback (wave
    1p5py/1p5qp) — including when CUDA isn't selected at all (091yn).
    """
    provider_list = list(providers)
    gpu = [p for p in provider_list if p in GPU_PROVIDERS]
    if not gpu:
        gpu = _available_gpu_providers()
    if not gpu:
        # 091yn: on a fresh CUDA-13 host ORT may not even list CUDA, so we'd never
        # reach the CUDA-selected path below — probe + warn proactively here.
        _warn_cuda12_gap_if_present()
        return None
    try:
        import onnx  # noqa: F401  (static-shape pin dependency)
        import onnxruntime  # noqa: F401
        import tokenizers  # noqa: F401
    except ImportError:
        return None
    try:
        embedder = StaticShapeEmbedder(model_name, gpu + ["CPUExecutionProvider"])
        # Only use it if the model's graph actually runs on the GPU; otherwise a
        # fragmented CoreML graph is no faster than fastembed → fall back.
        if embedder.offloads_to_gpu():
            return embedder
        if CUDA_PROVIDER in gpu:
            _warn_cuda12_gap_if_present()  # CUDA selected but didn't offload — surface the gap
        return None
    except Exception:
        if CUDA_PROVIDER in gpu:
            _warn_cuda12_gap_if_present()
        return None


class StaticShapeReranker:
    """Cross-encoder reranker on a static-shape ONNX (1p52p). Dual precision by provider:

    - **GPU** (CoreML/CUDA/ROCm/DirectML): the **FP16** export → ~107 ms/query (M2 Max CoreML, wave
      1p66v: a single ``RERANK_STATIC_BATCH``=40 pass covering the full candidate ceiling; was ~167 ms
      at the old shared 64-batch, which padded the 40-pool to 64).
    - **CPU** (no GPU available): the **INT8** export on ``CPUExecutionProvider`` (``ORT_ENABLE_ALL``),
      ~6x slower than the GPU path (was ~960 ms at batch 64) with no ranking loss. The FP16 export is
      NOT used on the CPU EP (it fails to init at ``ORT_ENABLE_ALL`` — a SimplifiedLayerNormFusion cast bug).

    ``rerank(query, passages)`` returns one **raw relevance logit per passage** (the server applies a
    sigmoid). The cross-encoder graph (ms-marco-MiniLM = BERT; bge-reranker = XLM-RoBERTa) takes
    ``[input_ids, attention_mask]`` (± ``token_type_ids``); the feed is filtered to the actual inputs.

    A GPU provider in ``providers`` selects the FP16/GPU path; otherwise the INT8/CPU path. Callers use
    ``make_reranker`` rather than constructing directly.
    """

    def __init__(self, model_name: str, providers: Iterable[str]) -> None:
        import numpy as np  # noqa: F401  (import-time availability check)
        import onnxruntime as ort
        from tokenizers import Tokenizer

        gpu = next((p for p in providers if p in GPU_PROVIDERS), None)
        so = ort.SessionOptions()
        so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

        if gpu is not None:
            # GPU FP16 path.
            files = _resolve_model_files(model_name)
            if files is None:
                raise FileNotFoundError(f"No cached FP16 ONNX/tokenizer for reranker {model_name!r}")
            src_onnx, tok_path = files
            static_path = _ONNX_CACHE / _safe(model_name) / f"rerank_static_{RERANK_STATIC_BATCH}x{STATIC_SEQ}.onnx"
            if not static_path.exists():
                build_static_onnx(src_onnx, str(static_path), output_is_logit=True, batch=RERANK_STATIC_BATCH)
            provs: list = []
            if gpu == COREML_PROVIDER:
                coreml_cache = _COREML_CACHE / _safe(model_name) / "MLProgram_ALL"
                os.makedirs(coreml_cache, exist_ok=True)
                provs.append((COREML_PROVIDER, {
                    "ModelFormat": "MLProgram",
                    "MLComputeUnits": "ALL",
                    "ModelCacheDirectory": str(coreml_cache),
                }))
            else:  # CUDA / ROCm / DirectML
                provs.append(gpu)
            provs.append("CPUExecutionProvider")
            self.provider = gpu
        else:
            # CPU INT8 path.
            files = _resolve_reranker_cpu_files(model_name)
            if files is None:
                raise FileNotFoundError(f"No cached INT8 ONNX/tokenizer for reranker {model_name!r}")
            src_onnx, tok_path = files
            static_path = _ONNX_CACHE / _safe(model_name) / f"rerank_cpu_int8_static_{RERANK_STATIC_BATCH}x{STATIC_SEQ}.onnx"
            if not static_path.exists():
                build_static_onnx(src_onnx, str(static_path), output_is_logit=True, batch=RERANK_STATIC_BATCH)
            provs = ["CPUExecutionProvider"]
            self.provider = "CPUExecutionProvider"

        self.model_name = model_name
        self.session = ort.InferenceSession(str(static_path), sess_options=so, providers=provs)
        self.input_names = [i.name for i in self.session.get_inputs()]
        self.output_name = self.session.get_outputs()[0].name
        self.tokenizer = Tokenizer.from_file(tok_path)
        self.tokenizer.enable_truncation(max_length=STATIC_SEQ)
        self.tokenizer.enable_padding(length=STATIC_SEQ)

    def rerank(self, query: str, passages: Iterable[str], **_: object) -> list:
        """Yield one raw logit per passage (cross-encoder relevance), batching to STATIC_BATCH."""
        import numpy as np

        docs = [p if isinstance(p, str) else str(p) for p in passages]
        scores: list = []
        for start in range(0, len(docs), RERANK_STATIC_BATCH):
            chunk = docs[start:start + RERANK_STATIC_BATCH]
            real = len(chunk)
            pairs = [(query, d) for d in chunk]
            if real < RERANK_STATIC_BATCH:                # pad the batch dim; sliced off below
                pairs = pairs + [(query, "")] * (RERANK_STATIC_BATCH - real)
            enc = self.tokenizer.encode_batch(pairs)
            feats = {
                "input_ids": np.array([e.ids for e in enc], dtype=np.int64),
                "attention_mask": np.array([e.attention_mask for e in enc], dtype=np.int64),
                "token_type_ids": np.array([e.type_ids for e in enc], dtype=np.int64),
            }
            feed = {n: feats[n] for n in self.input_names}   # roberta reranker omits token_type_ids
            out = np.asarray(self.session.run([self.output_name], feed)[0]).reshape(RERANK_STATIC_BATCH, -1)
            for r in range(real):
                scores.append(float(out[r, 0]))
        return scores

    def offloads_to_gpu(self, threshold: float = 1.5) -> bool:
        """True if a full rerank batch actually runs on the GPU (CPU near-idle). Mirrors the
        embedder probe; the first call pays the one-time CoreML compile (warmup)."""
        import time

        probe = ["warmup probe passage for reranker hardware offload measurement"] * RERANK_STATIC_BATCH
        self.rerank("warmup query", probe)  # warmup / compile
        wall0, cpu0 = time.time(), time.process_time()
        for _ in range(2):
            self.rerank("warmup query", probe)
        wall, cpu = time.time() - wall0, time.process_time() - cpu0
        return wall > 0 and (cpu / wall) < threshold


def _reranker_disabled() -> bool:
    """True when reranking is explicitly turned off — ``WAVEFOUNDRY_DISABLE_RERANKER`` (set by the
    test suite, and an operator opt-out). Distinct from ``WAVEFOUNDRY_EMBED_PROVIDER=cpu``, which now
    means "run the reranker on the CPU (INT8)", not "no reranker"."""
    return os.environ.get("WAVEFOUNDRY_DISABLE_RERANKER", "").strip().lower() in ("1", "true", "yes", "on")


def make_reranker(model_name: str, providers: Iterable[str]):
    """Return a ``StaticShapeReranker`` for this hardware, or ``None`` if reranking is disabled/unbuildable.

    GPU available → FP16 on the GPU (kept only if it actually offloads; a fragmented graph falls through
    to CPU). No GPU → INT8 on the CPU EP (~960 ms/query, no ranking loss). ``WAVEFOUNDRY_DISABLE_RERANKER``
    forces ``None`` (tests / opt-out). Never raises — any build failure degrades to ``None`` (the caller
    then skips reranking → vector order).
    """
    if _reranker_disabled():
        return None
    # NOTE: do NOT eagerly ``import onnx`` here — ``make_reranker`` runs in the long-lived MCP SERVER
    # process, which already has ``onnxruntime`` loaded; the protobuf-heavy ``onnx`` package is only
    # needed to BUILD the static graph (at prewarm, in a build subprocess). Warm cache → onnxruntime only.
    try:
        import onnxruntime  # noqa: F401
        import tokenizers  # noqa: F401
    except ImportError:
        return None
    provider_list = list(providers)
    gpu = [p for p in provider_list if p in GPU_PROVIDERS] or _available_gpu_providers()
    if gpu:
        try:
            reranker = StaticShapeReranker(model_name, gpu + ["CPUExecutionProvider"])
            if reranker.offloads_to_gpu():
                return reranker
            # GPU graph didn't actually offload (fragmented) → fall through to the CPU INT8 path.
        except Exception:
            pass
    try:
        return StaticShapeReranker(model_name, ["CPUExecutionProvider"])  # CPU INT8
    except Exception:
        return None
