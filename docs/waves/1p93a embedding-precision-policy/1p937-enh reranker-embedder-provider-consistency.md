# One machine classification drives embedder + reranker precision

Change ID: `1p937-enh reranker-embedder-provider-consistency`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-30
Wave: `1p93a embedding-precision-policy`

## Rationale

ADR `1p92d` requires that **one per-machine classification drives the whole pipeline** — a GPU machine runs FP16 end-to-end (embed + rerank), a CPU-bound machine runs INT8 end-to-end — so the embedder and reranker precision never split. The reranker already implements FP16-GPU / INT8-CPU, but its provider classification is resolved **independently** of the embedder's: `make_reranker` (`accel_embedder.py:555`) discovers providers via `_available_gpu_providers()` internally, while the embedder uses `provider_policy.select_embedding_providers()` (through `indexer._onnx_providers()`). The server's call site passes an empty list — `accel_embedder.make_reranker(RERANKER_MODEL, [])` (`server_impl.py:979`) — forcing that internal rediscovery. Both ultimately read ORT availability, but via separate paths, so the classification is duplicated rather than shared. This change makes a single resolved provider decision drive both, guaranteeing the embed and rerank precision agree on every machine.

## Requirements

1. **Resolve the provider list once** (the embedder's decision via `provider_policy.select_embedding_providers()` / `_onnx_providers()`) and pass it to **both** `make_embedder` and `make_reranker`, rather than letting `make_reranker` rediscover via `_available_gpu_providers()`.
2. **`server_impl` passes the resolved list.** Replace `make_reranker(RERANKER_MODEL, [])` (`server_impl.py:979`) with the resolved provider list, so the reranker's GPU-vs-CPU (FP16-vs-INT8) selection keys off the same classification as the embedder.
3. **`make_reranker` honors a supplied list.** When a non-empty provider list is passed, use it (it may still fall back to `_available_gpu_providers()` only when given an empty list, for back-compat / standalone callers).
4. **No ranking-output change.** This is a provider/precision-selection consistency change; the reranker's scores/order for a given precision are unchanged (INT8 reranker is "no ranking loss" per `1p52p`).

## Scope

**Problem statement:** the reranker classifies its provider/precision independently of the embedder, so a machine could in principle run a split pipeline (e.g. embedder on CPU-INT8 while the reranker independently picks something else).

**In scope:**

- `accel_embedder.py`: `make_reranker` honors a supplied provider list; document the shared-classification contract.
- `server_impl.py`: pass the resolved provider list to `make_reranker` at `:979`.
- `setup_index.py`: confirm `_prewarm_gpu_accel` already passes a consistent `providers` list to both `make_embedder` and `make_reranker` (it does — `:1026-1064`); align if needed.
- `tests/test_accel_embedder.py`: assert embedder + reranker resolve to the same precision class under a mocked provider decision.

**Out of scope:**

- The INT8-CPU **embedder** path (`1p935`) — this change only unifies the *classification*; `1p935` builds the embedder side.
- Reranker batch sizing (`RERANK_STATIC_BATCH = 40`, already tuned in `1p66v`).

## Acceptance Criteria

- [x] AC-1: under a mocked CPU-only provider decision (no available GPU), both the embedder and the reranker resolve to INT8/CPU; under a mocked GPU decision, both resolve to FP16/GPU — driven by the same shared resolution. Evidence: `test_embedder_and_reranker_share_classification_cpu` / `..._gpu` (`test_accel_embedder.py`).
- [x] AC-2 (**corrected during AC-4 hardware validation**): `make_reranker` resolves its provider **identically to `make_embedder`** — `[list∩GPU] or _available_gpu_providers()` — so the two never split; `server_impl._get_reranker` passes `_onnx_providers()`. **The original implementation (honor a non-empty CPU-only list literally) was WRONG and caused the very split it was meant to prevent** — see Decision Log. Evidence: `accel_embedder.make_reranker` (shared `or _available_gpu_providers()` fallback); `server_impl._get_reranker` passes `_onnx_providers()`; `test_make_reranker_cpu_list_with_available_gpu_uses_gpu`, `..._honors_explicit_gpu_list`, `..._cpu_only_when_no_gpu_available`; hardware-confirmed: reranker builds on `CoreMLExecutionProvider` on the M2 Max (was CPU-INT8 before the fix).
- [x] AC-3: the reranker's output ranking for a fixed precision is unchanged (regression guard). Evidence: 1p937 changes only provider **selection**, not `rerank()`; existing `test_rerank_returns_one_logit_per_passage` / `..._batches_across_static_batch_boundary` cover the rerank output shape/order unchanged.
- [x] AC-4: full framework suite + docs-lint green. Evidence: 3,755 tests OK; docs-lint clean.

## Tasks

- [x] Make `make_reranker` resolve providers identically to `make_embedder` (`[list∩GPU] or _available_gpu_providers()`) so the two can't split (`framework_edit_allowed`). Done: `accel_embedder.make_reranker`. **(Corrected: the first cut removed the `or _available_gpu_providers()` fallback for non-empty lists — that broke consistency; restored.)**
- [x] Pass the resolved provider list from `server_impl._get_reranker`. Done: `server_impl.py` passes `_indexer_constant("_onnx_providers")()` (harmless with the restored fallback — a CPU-only list still recovers the available GPU).
- [x] Add a mocked-provider test asserting embedder + reranker share the classification; ranking-unchanged guard. Done: `test_accel_embedder.py` (CPU-list-with-GPU→GPU, explicit-GPU→GPU, no-GPU→CPU, share-classification cpu/gpu).
- [x] Run suite + docs-lint. Done: 3,756 tests OK; docs-lint clean.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| make_reranker honors supplied providers | implementer | — | `accel_embedder.py:555` |
| server passes resolved list | implementer | make_reranker | `server_impl.py:979` |
| consistency tests | qa-reviewer | both | mocked-provider classification parity |

## Serialization Points

- The resolved provider list is the single source — it must be computed once (`_onnx_providers()` / `provider_policy`) and threaded to both `make_embedder` and `make_reranker`. Lands with `1p935`'s dispatch changes so a half-applied state never ships a split pipeline.

## Affected Architecture Docs

`docs/architecture/embedding-model.md` — note the single per-machine classification driving both embedder and reranker. ADR `1p92d` records the decision.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| ---- | ---------------------------------------------------- | --------- |
| AC-1 | required | The whole point — one classification, no split pipeline. |
| AC-2 | required | The mechanism (shared provider list). |
| AC-3 | important | Guard against an accidental ranking change. |
| AC-4 | required | No regressions. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-30 | Drafted from ADR `1p92d` + the reranker/embedder provider-resolution map. | `1p92d-adr`; `accel_embedder.py:555`, `server_impl.py:979`. |
| 2026-06-30 | Implemented (first cut): `make_reranker` honors a supplied non-empty provider list (empty → rediscover); `server_impl._get_reranker` threads `_onnx_providers()`. | `accel_embedder.py`, `server_impl.py` diffs; tests; 3,755 tests OK |
| 2026-06-30 | **Corrected after AC-4 hardware validation caught a regression THIS change introduced:** restored `make_reranker`'s `[list∩GPU] or _available_gpu_providers()` fallback (mirror `make_embedder`). | On the M2 Max, `select_embedding_providers()`/`_onnx_providers()` returns `["CPUExecutionProvider"]` even with CoreML available (conservative embedding-throughput probe). `make_embedder` overrides that with the available GPU; the first-cut `make_reranker` honored the CPU-only list literally → embedder GPU-FP16 but reranker CPU-INT8 — the exact split 1p937 exists to prevent, plus a perf regression (CPU reranker ~4s/query vs GPU ~350ms). Restoring the shared fallback makes both resolve identically. Confirmed on hardware: reranker now builds on `CoreMLExecutionProvider`. | `accel_embedder.py`, `test_accel_embedder.py`; 3,756 tests OK |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-30 | Both `make_embedder` and `make_reranker` resolve GPU as `[list∩GPU] or _available_gpu_providers()` — the shared availability fallback IS the single classification. The server threads `_onnx_providers()` for intent, but the fallback is what guarantees consistency. | `_onnx_providers()` (the conservative embedding probe) can say CPU on a GPU box; `make_embedder` ignores that and uses the available GPU, so `make_reranker` must too. The only CPU-forcing path is `WAVEFOUNDRY_EMBED_PROVIDER=cpu` (→ `_available_gpu_providers()`=[]), which sends BOTH to CPU-INT8 together. | (Rejected, was the first cut) Honor a non-empty CPU-only list literally in `make_reranker` — caused embedder-vs-reranker split on machines where the embedding probe under-selects (found on real M2 Max via AC-4). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| A standalone caller relied on `make_reranker`'s internal rediscovery. | Preserve empty-list rediscovery; only the supplied-list path changes behavior. |
| Provider decision computed differently at index vs query time. | Both read `provider_policy` / `_onnx_providers()`; AC-1 asserts parity under one decision. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
