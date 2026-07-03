# Set HF Hub socket timeouts in the model-warm environment so most stalled fetches raise in-thread

Change ID: `1p9p9-enh model-warm-hf-hub-socket-timeouts`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-07-03
Wave: TBD

## Rationale

Wave `1p9j0` (DF-1) bounded the in-process model warm with a wall-clock daemon-thread deadline (`_run_in_process_with_deadline`, `setup_index.py`), and hardened its abort so a timeout no longer quarantines a live cache. But that deadline is a *backstop*: when it fires, the underlying fastembed/Hugging Face download thread is **abandoned** (it cannot be interrupted from outside), and the process must exit rather than resume. That is correct as a last resort, but every abandoned-thread abort is a degraded outcome — the operator sees a timeout and must rerun.

Most real stalls are socket-level: a fetch that connects but then hangs mid-transfer behind a corp MITM / flaky proxy, or a dead ETag/metadata request. Hugging Face Hub honors two environment knobs for exactly these — `HF_HUB_DOWNLOAD_TIMEOUT` (per-chunk download read timeout) and `HF_HUB_ETAG_TIMEOUT` (metadata/HEAD request timeout). When set, a stalled socket raises a timeout **on the worker thread itself**, inside the wall-clock deadline, so the warm fails *in-thread* with the cache left quiescent — no abandoned thread, no wall-clock abort, and the existing corruption/retry machinery (which DF-1 deliberately skips only on the *deadline* path) can operate on a stopped download.

The framework does not set these today (`grep` confirms no `HF_HUB_DOWNLOAD_TIMEOUT`/`HF_HUB_ETAG_TIMEOUT` anywhere), so `_warm_model_inner` (`setup_index.py:899`) inherits HF's library defaults (~10s each). Setting them explicitly (a) makes the behavior deterministic and tunable rather than dependent on the installed `huggingface_hub` version's defaults, and (b) guarantees they are not left unbounded or bumped high by an inherited environment. This is an honest, bounded improvement — it does **not** replace the DF-1 deadline: a true drip-feed connection (each chunk arriving just under the read timeout) or a non-Hub code path can still stall, and the wall-clock deadline remains the backstop for those. The goal is to convert the common socket-stall case from "abandoned-thread wall-clock abort" into "clean in-thread failure with actionable guidance."

**MECHANISM CORRECTION (readiness re-review, 2026-07-03) — an `os.environ` set is a no-op here; use a scoped constant monkeypatch.** `huggingface_hub` reads these env vars **once at import** into module constants (`huggingface_hub.constants.HF_HUB_DOWNLOAD_TIMEOUT` / `HF_HUB_ETAG_TIMEOUT`); the download reads those *constants* at call time, and never re-reads `os.environ` after import. Verified empirically: setting the env var **before** import makes the constant honor it; mutating `os.environ` **after** import leaves the constant unchanged (a monkeypatch of the constant is what takes effect). The model warm imports fastembed→huggingface_hub before the scoped context runs (and the CA path imports it earlier still), so a set-then-restore of `os.environ` around the warm would satisfy naive ACs while having **zero effect**. The codebase already documents this exact hazard for the sibling CA case (`setup_index.py:772-782`, which works around a cached global `httpx.Client` via `close_session()`). Therefore the mechanism below is a **scoped save/set/restore of the `huggingface_hub.constants.*` module attributes** (import-order-independent, effective), reading an operator-set env var only as the *source of the value*. This correction supersedes the original `os.environ`-mutation wording in the Requirements/Scope/ACs.

## Requirements

1. The model warm must run with the effective Hugging Face Hub download/etag timeouts set to bounded, conservative values **via a scoped monkeypatch of `huggingface_hub.constants.HF_HUB_DOWNLOAD_TIMEOUT` and `HF_HUB_ETAG_TIMEOUT`** (NOT an `os.environ` set — see the Mechanism Correction; the env is read once at import so a later env mutation is a no-op), so a stalled socket raises a timeout on the worker thread inside the wall-clock deadline rather than only being caught by the abandoning wall-clock abort. An operator-set `HF_HUB_*_TIMEOUT` env var is honored as the *source of the value* to apply.
2. The two timeouts must be **configurable** via `docs/workflow-config.json` (under the existing `setup` block or an adjacent key), with conservative code defaults sized for slow-but-legit environments (e.g. a value comfortably below `setup.model_warm_timeout_seconds` so the socket timeout can fire *before* the wall-clock deadline). Missing/malformed/non-positive config falls back to the default and never raises (mirroring `_setup_deadlines`).
3. The constant monkeypatch must be applied **scoped** to the warm (save/set/restore, mirroring `_offline_env`'s set-then-restore shape at `setup_index.py:567` but operating on `huggingface_hub.constants.*` module attributes rather than `os.environ`), so the override does not leak into unrelated later process behavior; an operator-set env value must be respected as the source value (do not override an explicit operator choice with a lower default).
4. Setting the timeouts must not change a healthy within-timeout warm: a normal cached or fast download behaves exactly as today (same output, same success path, same provider decision).
5. The change must be honest about scope in code comments and docs: the socket timeouts reduce the *frequency* of wall-clock aborts for the common socket-stall case but do **not** replace the DF-1 deadline, which remains the backstop for drip-feed and non-Hub stalls.

## Scope

**Problem statement:** The model warm inherits Hugging Face Hub's default socket timeouts implicitly; the framework never sets `HF_HUB_DOWNLOAD_TIMEOUT`/`HF_HUB_ETAG_TIMEOUT`, so a common socket-level stall is caught only by the DF-1 wall-clock deadline, which abandons the download thread and forces a rerun instead of failing cleanly in-thread.

**In scope:**

- Scoped save/set/restore of `huggingface_hub.constants.HF_HUB_DOWNLOAD_TIMEOUT`/`HF_HUB_ETAG_TIMEOUT` around the model warm (`_warm_model_inner` / the `_warm_model` deadline-bounded attempt), via a context manager mirroring `_offline_env`'s shape but patching the module constants (NOT `os.environ`).
- A `docs/workflow-config.json` config surface for the two values (adjacent to the `setup` deadline keys), with conservative code defaults and a fail-safe loader; respect an operator-set inherited value.
- Tests: the warm env carries the two vars at the configured/default values; an operator-set inherited value is preserved; the healthy within-timeout warm is unchanged; the env is restored after the warm (no leak); config override honored and malformed → default.

**Out of scope:**

- The DF-1 wall-clock deadline, `_run_in_process_with_deadline`, and the abandoned-thread semantics — unchanged; this complements them.
- Moving the warm into a subprocess (the DF-1 primer's larger alternative) — explicitly not attempted here.
- Any change to the CA-bundle / TLS trust-ladder, provider selection, or the corruption/quarantine/retry logic.
- Setting HF timeouts for non-warm code paths (indexer runtime embedding, reranker prewarm) — a separate concern if it arises; this change targets the setup model warm where the field stalls were observed.
- Retry/backoff on a socket timeout — a socket timeout is a clean in-thread failure that flows into the existing error path; no new retry policy.

## Acceptance Criteria

- [ ] AC-1 (**effectiveness** — supersedes the original env-presence AC, which was vacuous): during the model warm, `huggingface_hub.constants.HF_HUB_DOWNLOAD_TIMEOUT` and `HF_HUB_ETAG_TIMEOUT` **read back** the configured (or default) values — i.e. the value the HF download actually consumes at call time reflects the override. A unit test asserts the module *constants* equal the expected values inside the warm body (NOT merely that `os.environ` carries them — an `os.environ`-only assertion passes even when the override has no effect, the exact vacuous-green trap this correction removes).
- [ ] AC-2: The two timeouts are read from `docs/workflow-config.json` with conservative code defaults; a config override is honored and a missing/malformed/non-positive value falls back to the default without raising. Verified by a loader unit test (configured / absent / malformed).
- [ ] AC-3: The constant monkeypatch is applied scoped: after the warm returns (success or failure), `huggingface_hub.constants.HF_HUB_DOWNLOAD_TIMEOUT`/`HF_HUB_ETAG_TIMEOUT` are restored to their pre-warm values, and an operator-set env value is honored as the source value (not overridden by a lower default). Verified by a unit test asserting pre/post constant state and operator-value preservation.
- [ ] AC-4: A healthy within-timeout warm is behaviorally unchanged — same success path and provider decision; verified by the existing warm/setup tests staying green plus an assertion that the timeout env does not alter the success path.
- [ ] AC-5: The default socket timeouts are sized below `setup.model_warm_timeout_seconds`'s default so the socket timeout can fire before the wall-clock deadline; a test (or documented default relationship) confirms `default(socket) < default(model_warm_deadline)`.
- [ ] AC-6: `python3 .wavefoundry/framework/scripts/run_tests.py` passes; `wave_validate` is clean; the new workflow-config keys are documented (notes-only, no pre-seeded numerics, matching the `setup`/`docs_lint` block convention).

## Tasks

- [ ] Add a `_hf_hub_timeout_scope()` scoped context manager in `setup_index.py` (mirror `_offline_env`'s save/set/restore shape, `:567`): import `huggingface_hub.constants`, save the two current constant values, set them from config/defaults (or the operator env value as source) on enter, restore on exit. Guard the import (best-effort; a missing/renamed constant must not break the warm).
- [ ] Add a config loader for the two values (extend `_setup_deadlines` or an adjacent helper), with conservative defaults below `MODEL_WARM_TIMEOUT_DEFAULT`; fail-safe to defaults.
- [ ] Wrap the model warm (`_warm_model_inner` body / the `_warm_model` deadline attempt) in `_hf_hub_timeout_scope()` so the fetch runs under the patched constants.
- [ ] Document the new keys in `docs/workflow-config.json` (notes-only) and add an honest inline comment that these complement, not replace, the DF-1 wall-clock deadline, and that the mechanism patches the module constants (not `os.environ`) because HF reads the env only at import.
- [ ] Add unit tests: constant-reflects-configured-value-during-warm (effectiveness), scoped-restore + operator-value-preservation, config override/default/malformed, healthy-warm-unchanged, default-ordering (`socket < model_warm_deadline`).
- [ ] Run `python3 .wavefoundry/framework/scripts/run_tests.py` and `wave_validate`; clean any `__pycache__`.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| ws1-hf-timeout-env | implementer | — | `_hf_hub_timeout_env()` CM + config loader + wrap the warm; single-file edit in `setup_index.py`. |
| ws2-config-and-tests | implementer | ws1-hf-timeout-env | Workflow-config notes + tests (env presence, scoped restore, config, healthy-warm, ordering); run suite + `wave_validate`. |


## Serialization Points

- All production edits land in `setup_index.py` (the CM, the loader, the warm wrap); single owner. `docs/workflow-config.json` notes + tests land after the key names are settled.

## Affected Architecture Docs

N/A — the change adds a scoped environment context around the existing model warm and a config surface; it introduces no new module boundary or control-flow between components (the warm still runs in-process under the DF-1 deadline). The `docs/architecture/*` setup-flow description is unaffected. The new workflow-config keys are documented inline in `docs/workflow-config.json`, a schema/reference update, not an architecture-boundary change.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | Setting the two timeouts around the warm is the core behavior; without it the warm keeps inheriting implicit HF defaults. |
| AC-2 | important | Configurability lets slow-but-legit environments raise the socket timeouts; the defaults ship the value without it. |
| AC-3 | required | Scoped restore + not clobbering an operator override is the correctness guard (mirrors `_offline_env`); a leaked/clobbered env is a real defect. |
| AC-4 | required | A healthy warm must be provably unchanged — this is a hardening, not a behavior change to the success path. |
| AC-5 | important | The socket timeout must be able to fire *before* the wall-clock deadline or it adds no value over DF-1; the default ordering encodes that. |
| AC-6 | required | Suite + docs-lint + documented keys are the standing merge gate. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-03 | Scoped from the first `1p9j0` delivery council's rotating-seat (performance) DF-1 complement. Verified the framework sets NEITHER `HF_HUB_DOWNLOAD_TIMEOUT` nor `HF_HUB_ETAG_TIMEOUT` anywhere (grep clean), so `_warm_model_inner` (`setup_index.py:899`) inherits HF library defaults (~10s). Scoped-env precedent: `_offline_env` (`setup_index.py:567`, set-then-restore of `HF_HUB_OFFLINE`). DF-1 deadline: `_run_in_process_with_deadline` + `_warm_model` (abandons the thread on timeout). | `setup_index.py:567,899`; grep for `HF_HUB_DOWNLOAD_TIMEOUT`/`HF_HUB_ETAG_TIMEOUT` (no hits); `1p9it` DF-1 deadline machinery. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-03 | Set the HF socket timeouts explicitly (scoped) rather than relying on HF library defaults. | Deterministic + tunable + guaranteed-bounded regardless of the installed `huggingface_hub` version or an inherited env; makes the common socket-stall case fail in-thread inside the DF-1 deadline. | Rely on HF defaults — rejected: implicit, version-dependent, and can be overridden high by an inherited environment. |
| 2026-07-03 | Frame this as a complement to, not a replacement for, the DF-1 wall-clock deadline. | Honest scope: socket timeouts do not catch drip-feed connections (each chunk under the read timeout) or non-Hub stalls; the deadline remains the backstop. | Present it as a full fix for setup hangs — rejected: overclaims; the deadline is still required. |
| 2026-07-03 | Default the socket timeouts below `setup.model_warm_timeout_seconds` and make both configurable. | The socket timeout must be able to fire before the wall-clock deadline to add value; slow-but-legit environments must be able to raise it. | Hardcode a single value — rejected: no field escape hatch, and a fixed value could exceed a lowered wall-clock deadline. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A too-tight socket timeout false-trips on a legitimately slow-but-progressing download. | Conservative defaults sized for slow links; both values configurable via workflow-config; a genuine slow download that keeps making progress resets the per-chunk read timeout (it is a no-progress read timeout, not a total cap). |
| The scoped env leaks or clobbers an operator-set value. | Set-then-restore CM mirroring `_offline_env`; AC-3 pins pre/post state and operator-value preservation. |
| Overstating the benefit — operators expect no more setup hangs. | Requirement 5 + Decision Log + inline comments state explicitly that this complements the DF-1 deadline; drip-feed and non-Hub stalls still rely on the wall-clock backstop. |
| The two env vars are ignored by a future `huggingface_hub` that renames them. | They are the documented HF Hub knobs today; if HF renames them, the DF-1 deadline still backstops, and a follow-up updates the names — no silent failure mode (a healthy warm is unaffected either way). |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
