# Harden setup dependencies and code index defaults

Change ID: `1p9gq-change socks-proxy-dependency`
Change Status: `implemented`
Owner: implementer
Status: implemented
Last verified: 2026-07-02
Wave: 1p9gr socks-proxy-dependency

## Rationale

Field reports exposed two first-setup gaps. First, a corporate environment required a SOCKS proxy for Wavefoundry setup/model-download traffic. Wavefoundry already handles corporate CA bundles, but the tool-venv dependency set does not explicitly install httpx's SOCKS extra. Since `huggingface_hub` uses httpx and httpx requires its SOCKS optional dependency (`socksio`) for `socks5://` proxy URLs, setup should install that support by default. Second, initial setup did not build the code index even though repository guidance says `wf setup` builds the framework + project semantic indexes; the older "semantic code embeddings are optional" wording is no longer true for the expected setup experience.

## Requirements

1. The Python package metadata must include the dependency needed for httpx SOCKS proxy support.
2. `wf setup` / `setup_index.ensure_deps()` must plan the same dependency for the isolated tool venv when SOCKS support is absent.
3. Verification must prove the dependency is checked by its SOCKS support module, not merely by plain `httpx`, because plain `httpx` may already be present through transitive dependencies.
4. Default `wf setup` / `wf update-indexes` must build the code index in the foreground without requiring the operator to discover and pass `--include-code`.
5. Setup guidance must stop describing semantic code embeddings as optional and must distinguish the default foreground docs+code build from explicit per-layer background options.
6. Setup accelerator prewarm must honor the setup-selected provider decision; if the setup probe selects CPU, later static-shape prewarm/indexing must not silently re-enable CoreML from raw ONNX availability.

## Scope

**Problem statement:** Corporate environments that use SOCKS proxies can fail model/download traffic unless the tool venv has httpx SOCKS support installed. Fresh setup also leaves code search unavailable when the operator runs the documented default `wf setup` command.

**In scope:**

- Add the SOCKS-support requirement to the package dependency manifest.
- Add the same requirement to the setup dependency planner.
- Add or update focused tests for the setup dependency manifest.
- Make default setup build the docs and code semantic indexes in the same foreground pass.
- Add an explicit `--background-docs` option so docs and code both have foreground/background escape hatches.
- Fix accelerator provider fallback so setup-selected CPU remains authoritative for prewarm/index subprocesses.
- Update setup/index guidance that still describes code embeddings as optional.

**Out of scope:**

- New proxy configuration UI or environment-variable handling.
- Changing CA-bundle, TLS verification, or retry behavior.
- Pinning or replacing `httpx` itself beyond requesting its SOCKS extra.
- Running both semantic layers detached in one setup command; the current status marker is single-owner, so detached work remains one layer at a time.

## Acceptance Criteria

- [x] AC-1: `pyproject.toml` includes `httpx[socks]` in the project dependencies.
- [x] AC-2: `.wavefoundry/framework/scripts/setup_index.py` includes a setup dependency entry that installs `httpx[socks]` when the SOCKS support module is missing.
- [x] AC-3: A focused unit test asserts the setup manifest maps `httpx[socks]` to the SOCKS support module (`socksio`), avoiding a false-positive check against plain `httpx`.
- [x] AC-4: Framework tests relevant to setup dependency planning pass.
- [x] AC-5: Default `setup_index.main(["--root", ...])` builds docs and code synchronously in the foreground.
- [x] AC-6: `--background-code` and `--background-docs` provide explicit one-layer-detached setup options.
- [x] AC-7: Agent/operator guidance no longer says semantic code embeddings are optional; it describes default foreground docs+code indexing and explicit background options.
- [x] AC-8: When setup selects `CPUExecutionProvider`, accelerator prewarm does not re-enable CoreML from raw ONNX Runtime availability.

## Tasks

- [x] Add `httpx[socks]` to `pyproject.toml`.
- [x] Add `httpx[socks]` to `setup_index.REQUIRED_IMPORTS` with the correct import probe.
- [x] Add/update focused tests for the dependency manifest.
- [x] Change default setup/update-index behavior to build code in the foreground with docs.
- [x] Add a docs-background option symmetric with the code-background option.
- [x] Fix setup accelerator prewarm so it honors the setup-selected CPU provider.
- [x] Update guidance that says semantic code embeddings are optional.
- [x] Run targeted tests and, if practical, the framework test runner.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| dependency-manifest | implementer | — | Update package metadata and setup planner. |
| setup-index-default | implementer | dependency-manifest | Make default setup build docs and code in the foreground. |
| provider-prewarm | implementer | setup-index-default | Prevent setup-selected CPU from being overridden by accelerator GPU availability fallback. |
| guidance | implementer | setup-index-default | Align setup docs and prompts with the new default. |
| verification | implementer | dependency-manifest, setup-index-default, provider-prewarm, guidance | Test the manifest/default setup contracts and run setup tests. |


## Serialization Points

- `pyproject.toml` and `setup_index.REQUIRED_IMPORTS` must stay in sync for fresh package installs and isolated tool-venv setup.
- Default setup should complete both docs and code semantic indexes before returning; background flags are explicit operator tradeoffs.

## Affected Architecture Docs

Update `docs/architecture/chunking-and-indexing-pipeline.md` and `docs/architecture/data-and-control-flow.md` if setup default behavior changes. No new architecture decision is needed; this aligns docs with the intended setup contract.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority                                             | Rationale |
| ---- | ---------------------------------------------------- | --------- |
| AC-1 | required | Package installs must include SOCKS support. |
| AC-2 | required | The isolated setup path is the main operator install path. |
| AC-3 | required | Plain `httpx` presence is insufficient evidence that SOCKS proxy URLs work. |
| AC-4 | required | The dependency-planning behavior must be verified. |
| AC-5 | required | Fresh setup must complete the code index by default. |
| AC-6 | required | Explicit background behavior must remain available without becoming the default. |
| AC-7 | required | Operator and agent guidance must not contradict setup behavior. |
| AC-8 | required | A setup probe that rejects CoreML must not be bypassed by a later accelerator prewarm path. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-02 | Planned scoped dependency update. | Field report; setup dependency manifests identified. |
| 2026-07-02 | Implemented SOCKS dependency manifest updates and focused setup tests. | `pyproject.toml`; `setup_index.REQUIRED_IMPORTS`; `test_setup_index.py` |
| 2026-07-02 | Expanded scope per operator report: initial setup must not leave code index absent or document it as optional. | Operator field report; `AGENTS.md`, setup docs, and `setup_index.py` default behavior. |
| 2026-07-02 | Implemented default foreground docs+code indexing, explicit docs/code background options, and aligned setup guidance. | `setup_index.py`; `test_setup_index.py`; `AGENTS.md`; install/upgrade seeds; architecture/contributing docs. |
| 2026-07-02 | Reproduced and fixed setup accelerator prewarm crash path: setup selected CPU, but accelerator fallback re-enabled CoreML and crashed in ONNX/CoreML native code. | Crash reports from Python PIDs 3755/9761; provider probe subprocess completed after fix. |
| 2026-07-02 | Delivery review found and fixed foreground leakage in `--background-docs`: the foreground parent prewarmed docs+code models before the code-only build. | Layer-aware `_indexer_models` / `prewarm_models`; `SetupLayerSchedulingTests`; full framework suite. |
| 2026-07-02 | Verified framework suite. | `python3 .wavefoundry/framework/scripts/run_tests.py` — 4,088 tests OK. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-02 | Select `httpx[socks]` and probe `socksio`. | `huggingface_hub` uses httpx, and httpx's SOCKS support is enabled by its `socks` extra; probing `socksio` ensures an existing plain-httpx install does not hide missing SOCKS support. | Add `PySocks` directly (fits requests, not httpx); add plain `httpx` (does not install SOCKS support); document proxy setup only (leaves setup broken in the reported environment). |
| 2026-07-02 | Make default setup build docs and code in the foreground. | The operator clarified that code should be treated like docs: if no foreground/background option is specified, both layers should complete before setup returns. This avoids a false-completion trap where setup reports success while code search is still unavailable. | Keep code optional (rejected by field report); default to background code (rejected by operator clarification and false-completion risk). |
| 2026-07-02 | Keep background setup one layer at a time. | The background build marker/status path is single-owner today; allowing both docs and code to detach in one command would make status/log ownership ambiguous. | Allow both `--background-docs` and `--background-code` together (rejected until status tracking supports multiple detached owners). |
| 2026-07-02 | Make setup-selected CPU authoritative for accelerator fallback. | The setup probe can reject CoreML, but `accel_embedder` separately queried raw ONNX availability and could re-enable CoreML during prewarm/indexing, causing a native SIGSEGV that Python cannot catch. | Treat it as a test-only issue (rejected after production probe reproduced the crash); force CPU globally (rejected because explicit operator GPU requests should still work). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Existing venv already has plain `httpx`, so a naive import probe would skip installing the extra. | Probe `socksio`, the module supplied by httpx's SOCKS extra. |
| Adding an unpinned dependency could shift resolver output. | Keep the requirement minimal and rely on existing package-age guard / setup dependency flow. |
| A detached semantic build could be mistaken for a completed index layer. | Make foreground docs+code the default and reserve detached work for explicit `--background-code` / `--background-docs` calls, with guidance to check `wave_index_build_status` / `wave_index_health`. |
| CoreML can crash in native code after the setup probe selected CPU. | Preserve explicit GPU overrides, but make `WAVEFOUNDRY_EMBED_PROVIDER_SELECTED=CPUExecutionProvider` suppress accelerator raw-GPU fallback in setup-spawned prewarm/index subprocesses. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
