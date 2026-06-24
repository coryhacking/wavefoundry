# Session Handoff

Owner: Engineering
Status: in_progress
Last verified: 2026-06-23

## `1p7ir index-build-robustness` (OPEN, implementing) — ALL 4 CHANGES IMPLEMENTED. UNCOMMITTED.
Driven by the 1.8.0 CPU-only-WSL2 OOM + corporate-TLS field report. Full suite **3437 OK** bytecode-free; docs-lint clean.

- **`1p7iv`** (memory fix — the headline): on-machine profiling found the OOM driver is the **forward-pass activation tensors** (onnxruntime CPU arena), corpus- and thread-independent; GPU keeps them in GPU memory off-RSS (the ~7–8× gap). Fix: **per-model forward batch** (`_resolve_embed_batch_size`, config-overridable `indexing.{code,docs}_embed_batch_size`), default **32** (down from 256) → code 5.36→1.55, docs 9.47→2.49 GiB (~3.5–3.8×), field ~14→~3.5 GiB, equal-or-faster, vectors batch-invariant. `indexer.py`.
- **`1p7is`** (health honesty): `wave_index_health` now reports `incomplete` + `code` in `missing_layers` + `semantic_ready=false` + a `code_layer_missing` diagnostic when code sources are in scope but `code.lance` is absent (the silent-OOM mask). `server_impl.py`; 3 tests.
- **`1p7it`** (OOM guardrails): buffer default 2048→**1024** (throughput; AC-7); AC-1 buffer-autoscale **dropped** (measured no-op); AC-3 **OOM-specific SIGKILL message** (`setup_index._run_indexer`); AC-4 **dashboard OOM back-off** (no re-kill loop); AC-2 sequential-degrade **deferred `[~]`** (1p7iv obviates it for in-scope hosts). 2 tests.
- **`1p7iu`** (TLS): `_warm_model` retries the model download against the **OS trust store** on `CERTIFICATE_VERIFY_FAILED` (honors `SSL_CERT_FILE`/`REQUESTS_CA_BUNDLE`; verification stays ON); remediation error otherwise. `setup_index.py`; 5 tests. AC-5 (real proxy host) `[~]` deferred.

## Deferred `[~]` (recorded, non-blocking): 1p7it AC-2 sequential-degrade (sub-8GiB hosts only); 1p7iu AC-5 real-proxy gate.
## Next: review-wave + operator-gated close. NOT committed (per "commit when done" rhythm). Bench scratch in `experiments/buffer_bench.py` (kept).
## Earlier this session: 1p7de closed + committed (Land 1p7de 5d55a88); 1p7ir planned-commit c4741d4.

## Current Session

**Active wave:** *(none)*
