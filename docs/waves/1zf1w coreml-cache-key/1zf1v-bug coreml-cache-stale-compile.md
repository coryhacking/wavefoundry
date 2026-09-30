# Stale CoreML Compiled-Model Cache Silently Disables Reranker Acceleration

Change ID: `1zf1v-bug coreml-cache-stale-compile`
Change Status: `complete`
Owner: Engineering
Status: planned
Last verified: 2026-09-30
Wave: 1zf1w coreml-cache-key

## Rationale

Field report on a 1.28.0+pti1 upgrade (Apple M2 Max, macOS 27.2, onnxruntime 1.27.0): the isolated CoreML reranker probe failed with `output_features has no value for logits`, so the reranker quietly fell back to CPU. Verified on this machine:

- `accel_embedder.StaticShapeReranker` and `StaticShapeEmbedder` pass ONNX Runtime a CoreML `ModelCacheDirectory` of `~/.wavefoundry/cache/coreml/<model>/MLProgram_ALL`. ONNX Runtime names the entry inside it from a hash of the ONNX file's path only (each entry's `model.txt` holds that path). Neither the ONNX Runtime version nor the model file's content is part of the key. The code comment there claims "any change uses a fresh cache dir", which is not true for either.
- Every reranker entry (for the 40, 32, 24 and 64 batch graphs, all dated Jun 17) holds two partitions, `0_dynamic_mlprogram` and `1_dynamic_mlprogram`. The reporter showed that the old compile split the graph with partition 0 returning an intermediate LayerNorm output, while onnxruntime 1.27 compiles the whole graph as one partition that must return `logits`. Loading the stale partition 0 produces exactly the reported error. With a fresh cache directory the probe passes on CoreML (40 finite scores, first score -8.07 against -8.37 on CPU INT8, `offloads_to_gpu=True`).
- The embedder entries are single-partition and still pass today, but they carry the same exposure.
- The reranker cache is 764 MB, three quarters of it compiles for batch sizes the code no longer uses (`RERANK_STATIC_BATCH` is 40; `STATIC_BATCH` is 32).

Goal: an ONNX Runtime or model change can never load a stale CoreML compile, and superseded compiles do not accumulate. Consumer: every macOS installation using CoreML acceleration. Success: with the stale cache above left in place, the reranker probe passes and runs on CoreML, and the superseded entries are removed.

## Requirements

1. **Version- and content-keyed cache.** Both `StaticShapeEmbedder` and `StaticShapeReranker`, on the CoreML path, use a cache directory `<model>/MLProgram_ALL/ort-<onnxruntime version>-<digest>`, where `<digest>` is a short SHA-256 over the provider options (`MLProgram`, `ALL`) and the static ONNX file the session loads (hashed in chunks after the static graph is built). One helper builds the path for both classes (the isolated probe child constructs the same classes, so it uses the same key). The digest is computed once per process per file (memoized on path, size and modification time).
2. **Superseded compiles are removed.** When the helper creates the key directory (detected by the creating `mkdir` itself, not by a prior existence check, so two concurrent starts do not both prune), it removes every other entry under that model's `MLProgram_ALL` directory: the old ORT-named entries and any other key. It never follows a symlink (a symlinked entry is unlinked, not traversed), never touches anything outside that directory, and a removal failure never prevents the session from being created. Pruning does not run when the key directory already exists. Pruning is refused (the cache directory is still returned) unless the resolved model directory sits directly under the resolved CoreML cache root and neither the model directory nor `MLProgram_ALL` is a symlink; a model name that is empty, `.` or `..` is refused the same way.
3. **Scope of the key.** CUDA, ROCm, DirectML and the CPU paths are unchanged (they pass no cache directory).
4. **Platforms.** CoreML runs only on macOS; the helper is plain Python and is exercised by hardware-free tests on every platform. Behaviour on Windows, Linux and WSL2 is unchanged because those never take the CoreML branch.
5. **Transition.** The first CoreML session after the upgrade compiles fresh (a one-time cold compile, measured at about 17 s for the reranker in wave `1p52p`) and removes the stale entries. A process running an older build keeps its own cache layout; mixing builds against one home cache at the same time is not supported, and the worst case is a recompile or a probe failure that falls back to CPU. An older build that recompiles into `MLProgram_ALL` directly leaves an entry the new key does not prune until the next key change, and two tool environments with different ONNX Runtime versions sharing one home cache prune each other's key on every alternation. The CHANGELOG entry goes under `### Fixed` in the open `## [1.28.0]` section.

## Scope

**Problem statement:** the CoreML compiled-model cache is keyed only by the ONNX file path, so an ONNX Runtime upgrade that repartitions the graph loads a stale compile and silently disables acceleration; superseded compiles accumulate.

**In scope:**

- `accel_embedder.py`: a cache-directory helper used by both static classes; tests; CHANGELOG.

**Out of scope:**

- Rebuilding the static ONNX file when its builder changes (it is rebuilt only when missing; a separate issue).
- A retry-with-fresh-cache fallback in the probe (the keyed path makes it unnecessary).
- The retired-model cleanup in `upgrade_wavefoundry.py`, which removes whole `coreml/<model>` folders for retired models and is unaffected.

## Acceptance Criteria

- [x] AC-1: the CoreML cache directory passed to ONNX Runtime by both classes is `<model>/MLProgram_ALL/ort-<version>-<digest>`; it changes when the ONNX Runtime version changes and when the static ONNX file's content changes, and stays the same otherwise.
- [x] AC-2: creating a new key removes the legacy ORT-named entries and other keys under that model's `MLProgram_ALL`, keeps the current key, does not prune when the key already exists, unlinks a symlinked entry without touching its target, leaves other models' caches alone, refuses to prune for a `..` model name or a symlinked `MLProgram_ALL`, and a removal error still yields the cache directory.
- [x] AC-3: CUDA, ROCm, DirectML and CPU sessions are constructed exactly as before (no cache directory, no digest).
- [x] AC-4: on this machine, with the stale reranker cache in place, the isolated reranker probe passes on CoreML after the change and the stale entries are gone.
- [x] AC-5: the change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Add the cache-directory helper and use it in both classes.
- [x] Hardware-free tests for AC-1 to AC-3.
- [x] Run the real reranker probe on this machine against the stale cache (AC-4).
- [x] CHANGELOG `### Fixed` entry under 1.28.0.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Cache key and pruning | implementer | readiness | One helper, two call sites |
| Review | code-reviewer, qa-reviewer | implementation | |

## Serialization Points

- `.wavefoundry/framework/scripts/accel_embedder.py`, `.wavefoundry/framework/scripts/tests/test_accel_embedder.py`

## Affected Architecture Docs

N/A: a cache-path change inside one module; no boundary, flow or verification change.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The defect: stale compiles load after a runtime change |
| AC-2 | required | Operator asked for superseded compiles to be removed; safety of deletion |
| AC-3 | required | No change to other providers |
| AC-4 | required | Real-hardware proof on the reporting machine |
| AC-5 | required | Standard verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-30 | Delivery review (independent, Opus): code-reviewer, qa-reviewer, red-team and security-reviewer APPROVE, no build-changing defect. Adversarial pruning checks held (escaping names, symlinked cache root, symlink, file, dangling and junction entries, a symlink swapped in between scandir and rmtree with `rmtree.avoids_symlink_attacks` true). 20 mutants: 15 killed, 4 equivalent by design, 1 real test gap. Taken: `test_only_the_creating_mkdir_prunes` (the exists-then-makedirs mutant now fails); Transition wording for the orphaned old-build entry and mixed ONNX Runtime versions; a note on the real-cache test that it must run under the tool venv; CHANGELOG mentions the provider options. Kept as is: the real-cache test (isolation cannot reach the probe child and would cost a cold compile per run). Follow-up, out of scope: the unreferenced `Snowflake__snowflake-arctic-embed-xs` CoreML cache (190 MB) is on no retired-model allowlist | 9 cache tests OK; full suite 10172 OK before this row |
| 2026-09-30 | Implemented. `accel_embedder`: `_coreml_cache_dir` (key `MLProgram_ALL/ort-<version>-<digest>`, digest over `MLProgram|ALL|` and the static graph, chunked and memoized on path, size and mtime; the creating `mkdir` decides who prunes), `_prune_superseded_coreml_entries` (name guard for empty, `.`, `..` and separators; refuses a symlinked model or variant directory or one not directly under the resolved cache root; unlinks symlinks and files, `rmtree` for real directories, per-entry errors ignored); both static classes use it and `_COREML_FORMAT`/`_COREML_UNITS`; the misleading cache comment is gone. Tests (`CoreMLCacheKeyTests`): key composition and change on version and content; pruning set with a legacy entry, an older key, a stray file, a symlink to an outside directory and a neighbouring model; no prune on an existing key; `..` name; symlinked variant; rmtree error; both classes pass the keyed directory; CUDA passes none. Mutants: no version, no content, prune always, no containment (both checks), no symlink checks (both), follow symlink entries, unguarded rmtree, reranker old path; all caught. Disabling only one of the two overlapping containment or symlink checks survives by design (the other still refuses). Real hardware (AC-4): the new code migrated the stale reranker cache (four two-partition entries, 764 MB) to one `ort-1.27.0-922c07622340a560` key (206 MB) during the module run, via the existing real-CoreML test `test_reranker_fp16_matches_fp32_when_available`; the isolated reranker and embedder probes then passed on CoreML (they assert offload and finite scores) and the embedder's old entry was pruned. Gapfill: shell reads, the targets were known from the investigation | 84 accel tests OK |
| 2026-09-30 | Readiness review (independent, fresh context): code-reviewer, qa-reviewer, red-team and security-reviewer APPROVE, no blocking defect. Adopted: detect a newly created key by the creating `mkdir` (not exists-then-makedirs) so concurrent starts do not both prune; containment guard (`_safe` only replaces `/`, so a `..` or `.` name would escape; resolved model directory must sit directly under the resolved cache root, no symlinked model or `MLProgram_ALL` directory); provider options in the digest; chunked, memoized hashing; correct the misleading cache comment. Not adopted: macOS version in the key (forces a recompile on every point release; partitioning is ONNX Runtime's). Confirmed: CoreML-only cache path in both classes, probe child builds the same classes, fixed batch constants, no other writer of the CoreML cache | Readiness report |
| 2026-09-30 | Planned from a field report, verified on this machine: every reranker cache entry has `0_` and `1_dynamic_mlprogram` (Jun 17); embedder entries have one partition; `model.txt` holds only the ONNX path; `accel_embedder` builds `<model>/MLProgram_ALL` with no version or content; onnxruntime 1.27.0 in the tool venv; `STATIC_BATCH` 32 and `RERANK_STATIC_BATCH` 40 are fixed constants; the probe child builds the same classes | Cache listing; code reads |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-30 | Key by ONNX Runtime version plus a content digest of the static ONNX file | Covers both ways a compile goes stale (runtime repartitioning, a rebuilt graph) with no extra configuration | Wipe the cache on version change only; retry once with a fresh cache after a probe failure |
| 2026-09-30 | Prune siblings only when a new key is created | Reclaims superseded compiles once, costs nothing on later starts | Prune on every start; leave cleanup to the operator |

## Risks

| Risk | Mitigation |
| --- | --- |
| Pruning removes a compile another process is using | Only entries other than the current key are removed; a concurrent older build is unsupported and degrades to a recompile or CPU fallback |
| Hashing a 45 MB graph slows session start | Once per process per file, memoized |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
