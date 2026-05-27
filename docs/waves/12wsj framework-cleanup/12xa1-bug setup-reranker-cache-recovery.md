# Setup Model Cache Recovery

Change ID: `12xa1-bug setup-reranker-cache-recovery`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-26
Wave: `12wsj framework-cleanup`

## Rationale

`setup_wavefoundry.py` is the canonical bootstrap entrypoint for Wavefoundry MCP readiness, but today it hard-fails when model prewarm encounters a broken FastEmbed cache or a transient download failure. In the observed failure, the reranker snapshot symlinked `onnx/model.onnx` to a zero-byte `.incomplete` blob, so every subsequent setup run and MCP-triggered project index rebuild stayed stuck until the cache was manually repaired.

That behavior is more fragile than the rest of the system contract. The immediate failure was in the reranker path, but the same broken-cache mechanics can affect embedding models too. Setup should treat all prewarmed model caches as repairable assets with one consistent recovery path rather than assuming only the happy path or forcing manual cache surgery.

## Requirements

1. `setup_wavefoundry.py` / `setup_index.py` must detect and recover from broken FastEmbed cache states for every model it prewarms: docs embedding model, code embedding model when enabled, and reranker model. Broken states include missing or unreadable ONNX assets, broken symlinks, and zero-byte or `.incomplete` blob targets.
2. Model prewarm must retry once after quarantining only the corrupted cache entry for the affected model; it must not require the operator to manually delete cache directories.
3. Reranker prewarm remains a hard prerequisite for successful setup, and embedding-model prewarm remains a hard prerequisite for the corresponding index content being built. When a required model still cannot be downloaded because the network is unavailable or the download host cannot be reached, setup must fail with a specific, actionable diagnostic that distinguishes cache corruption from network unavailability and leaves no stale in-progress index process behind.
4. MCP-triggered project index rebuilds that route through `setup_index.py` must respect the same model-cache recovery logic so the server does not spin indefinitely on the same corrupted cache state.
5. Agent-facing setup/install guidance must instruct the agent to request operator permission to rerun the canonical setup path when required model download fails because network access is unavailable; agents should not switch to out-of-band manual model downloads.
6. Automated tests must cover embedding and reranker branches in setup, including corruption-repair paths and offline/network-unavailable paths.

## Scope

**Problem statement:** The setup/bootstrap path is not resilient to partial model downloads. A broken FastEmbed cache entry for any required prewarmed model can block `setup_wavefoundry.py`, keep MCP index health stale, and require manual cache cleanup.

**In scope:**

- `setup_index.py` model prewarm paths and any helper extraction needed to make recovery deterministic
- Targeted cache-integrity checks for embedding and reranker model artifacts used by setup
- Clear operator diagnostics for corruption vs network/download failure, keyed to the affected model
- MCP rebuild parity for the same setup path
- Agent-facing setup/install guidance for permissioned retry after model-download failure
- Unit tests in `test_setup_index.py` and any focused server-tool coverage needed for the repaired contract

**Out of scope:**

- Changing model-selection policy or which models setup is required to prewarm
- Replacing FastEmbed, ONNXRuntime, or Hugging Face as the model provider stack
- Broad redesign of search ranking behavior or runtime retrieval policy
- Unrelated index-health drift in the current `12wsj` wave

## Acceptance Criteria

- [x] AC-1: Targeted regression coverage demonstrates that a deliberately corrupted cache entry for a required prewarmed model is detected and quarantined without manual cache deletion.
- [x] AC-2: When a required model cannot be downloaded because the host is offline or DNS/network resolution fails, setup returns a specific diagnostic that names the model download failure as the cause, exits cleanly, and leaves no ambiguous stale-state failure behind.
- [x] AC-3: Targeted server/build-status regression coverage demonstrates that MCP project index rebuilds route through `setup_index.py` for project `content='all'` and report a terminal failure state instead of remaining stuck when setup exits on model-prewarm error.
- [x] AC-4: Agent-facing setup/install guidance tells the agent to request operator permission to rerun the canonical setup path when required model download fails because network access is unavailable.
- [x] AC-5: `test_setup_index.py` includes explicit coverage for embedding-model prewarm success/failure, reranker prewarm success/failure, corruption recovery, and download/network failure handling.
- [x] AC-6: Existing fallback behavior remains intact for runtime search, but setup and setup-routed MCP rebuilds still require healthy caches for the models needed by the requested build before they report success.

## Tasks

- [x] Extract model-prewarm recovery helpers that can classify failures per model: healthy cache, corrupted cache, and download/network failure.
- [x] Add cache-integrity detection for embedding and reranker snapshots, including broken snapshot symlinks and zero-byte/incomplete ONNX blobs.
- [x] Implement one-shot quarantine-and-retry behavior for the corrupted cache entry of the affected model.
- [x] Encode the setup contract for download failure as explicit fail-fast with a high-signal model-specific error and no wedged build state.
- [x] Route MCP-triggered rebuilds through the same repaired setup logic and verify process/build-status behavior.
- [x] Update the relevant setup/install prompt surfaces so agents are instructed to request operator permission to rerun canonical setup when model download fails for network reasons.
- [x] Add regression tests for embedding and reranker model branches in `test_setup_index.py` and any server-tool integration checks needed for stuck-build prevention.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| Failure classification + contract | implementer | — | Decide which model-cache failures are recoverable and when setup must fail with a precise diagnostic |
| Cache repair path | implementer | Failure classification + contract | Add corruption detection, quarantine, and retry for embedding and reranker caches |
| Agent guidance | implementer | Failure classification + contract | Update setup/install prompts so hosts request permission for canonical setup retry on network-blocked downloads |
| Test coverage | implementer | Cache repair path | Extend `test_setup_index.py`; add focused MCP/server coverage only if needed |


## Serialization Points

- `.wavefoundry/framework/scripts/setup_index.py` is the write-owning entrypoint for the reliability fix and should stay single-owner until the model-failure contract is settled.
- `test_setup_index.py` should be updated after the setup contract is finalized so tests lock the intended behavior rather than the pre-fix failure mode.

## Affected Architecture Docs

`N/A` — the change is confined to bootstrap/setup reliability inside the existing indexing toolchain and does not introduce a new architecture boundary or runtime flow.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | Manual cache repair is the primary defect being fixed |
| AC-2 | required  | Operators need a precise, actionable failure mode when a required model cannot be fetched |
| AC-3 | required  | MCP rebuilds must stop wedging on the same model-cache failure |
| AC-4 | important | Recovery is incomplete if agents are not told to request permission for the canonical retry path |
| AC-5 | required  | Current tests miss most of the model-prewarm failure surface |
| AC-6 | important | The fix must preserve existing degraded-search fallback behavior |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-26 | Reviewed `setup_wavefoundry.py`, `setup_index.py`, and MCP/server fallback behavior. Confirmed setup hard-fails in reranker prewarm before index build, while runtime search already degrades gracefully without a reranker. | `.wavefoundry/framework/scripts/setup_index.py:279-302`, `.wavefoundry/framework/scripts/setup_index.py:473-508`, `.wavefoundry/framework/scripts/server_impl.py:740-763` |
| 2026-05-26 | Operator clarified that reranker availability should remain a hard prerequisite for setup success; the reliability fix should preserve that policy while making failures self-healing or explicit. | User direction during plan review |
| 2026-05-26 | Confirmed test gap: setup tests cover embedding prewarm only and do not exercise `_warm_reranker` or broader model-cache failure recovery. | `.wavefoundry/framework/scripts/tests/test_setup_index.py:242-276` |
| 2026-05-26 | Observed live failure mode: reranker snapshot `onnx/model.onnx` symlink targeted a zero-byte `.incomplete` blob, causing setup and MCP rebuilds to fail repeatedly until manual cache intervention. | Local reproduction during `setup_wavefoundry.py --root .` and MCP `wave_index_build` checks |
| 2026-05-26 | Operator broadened the desired repair contract from reranker-only to all setup-prewarmed models. | User direction during plan review |
| 2026-05-26 | Implemented model-cache recovery helpers in `setup_index.py`, including corruption detection, quarantine-and-retry, and clean fail-fast diagnostics. Extended setup tests to cover reranker prewarm and model-cache failure behavior. | `.wavefoundry/framework/scripts/setup_index.py`, `.wavefoundry/framework/scripts/tests/test_setup_index.py` |
| 2026-05-26 | Verified targeted setup tests pass and live offline setup now exits with a concise reranker-network diagnostic instead of a traceback. | `/opt/homebrew/bin/python3 .wavefoundry/framework/scripts/tests/test_setup_index.py`, `python3 .wavefoundry/framework/scripts/setup_wavefoundry.py --root .` |
| 2026-05-26 | Operator requested that the same change also cover agent guidance: on model-download failure, ask for permission to rerun canonical setup with network access instead of doing an out-of-band manual download. | User direction during implementation review |
| 2026-05-26 | Updated operator- and agent-facing setup/upgrade guidance to keep recovery on the canonical setup path and require permission before rerunning setup with network access. | `docs/prompts/install-wavefoundry.prompt.md`, `docs/prompts/upgrade-wavefoundry.prompt.md`, `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`, `AGENTS.md` |
| 2026-05-26 | Fixed embedding-cache repair parity so setup recognizes FastEmbed's alias cache directories for BAAI embedding presets, not only the literal model IDs. Added targeted setup and MCP build-status regression coverage for the remaining failure contract. | `.wavefoundry/framework/scripts/setup_index.py`, `.wavefoundry/framework/scripts/tests/test_setup_index.py`, `.wavefoundry/framework/scripts/tests/test_server_tools.py` |
| 2026-05-26 | Verified the remaining repair contract with targeted proofs instead of repeated live reruns: setup-index regression coverage passes, and MCP `content='all'` rebuilds were manually verified to route through `setup_index.py` and settle to a terminal failed status when setup exits on model-prewarm error. | `python3 .wavefoundry/framework/scripts/tests/test_setup_index.py`; manual verification snippet against `.wavefoundry/framework/scripts/server_impl.py` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-05-26 | Treat this as a bug in the setup/bootstrap contract, not a one-off local env issue. | The canonical setup path is expected to repair or clearly diagnose cache bootstrap failures without manual cache surgery. | Document manual cache deletion only; rejected because it preserves a fragile operator workflow. |
| 2026-05-26 | Broaden repair behavior to all setup-prewarmed models while keeping the existing change ID for continuity. | The observed defect surfaced in the reranker path, but the same cache-corruption mechanics can affect embeddings and should not require a second follow-on bug. Renaming the admitted change ID after review would create unnecessary churn. | Keep repair reranker-only; rejected because it would preserve identical failure modes for embedding caches. |
| 2026-05-26 | Keep network-recovery guidance on the canonical setup path rather than permitting ad hoc direct model downloads. | Operators should approve rerunning the supported bootstrap flow, not a side-channel fetch that bypasses setup semantics. | Teach agents to manually download models; rejected because it splits the recovery path and weakens the setup contract. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Setup becomes too permissive and silently downgrades search quality without clear operator notice | Keep required model prewarm as a hard prerequisite; only improve corruption recovery and failure diagnostics |
| Cache repair logic accidentally deletes healthy shared model assets | Quarantine only the corrupted cache subtree or blob target for the affected model, and cover it with regression tests |
| Fix addresses CLI setup but not MCP-triggered rebuilds | Reuse the same helper/contract in the setup path used by MCP project rebuild routing and validate through MCP health/build-status checks |
| Broadening from reranker to all models expands the blast radius of cache repair logic | Centralize model-cache checks in one helper and add per-model regression fixtures rather than duplicating ad hoc repair code |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
