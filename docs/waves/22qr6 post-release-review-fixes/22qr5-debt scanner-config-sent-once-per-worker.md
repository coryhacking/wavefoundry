# Send scanner configuration once per worker

Change ID: `22qr5-debt scanner-config-sent-once-per-worker`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-11-06
Wave: 22qr6 post-release-review-fixes

## Rationale

The scanner client in `wave_lint_lib/secrets_validators.py` sends the full merged rule configuration (439,931 bytes for the shipped profile) with every worker request, and each file costs two requests (`path_excluded` and `scan`). In an executed probe, 50 small files produced 102 requests averaging 445 KB each: 45.4 MB of JSON, with about 8.5 ms of encode, validate and hash work per pass on each side. For a full scan of about 10k files, that is minutes of overhead.

## Product Intent

Full scans and docs-lint on large repositories avoid redundant configuration transfer, and findings and completion results are unchanged.

## Requirements

1. The client computes a digest of the exact configuration it would send, including per-call allowlist, stopword and path arguments. It configures each worker process once per digest, and later requests carry only the digest, which the worker verifies. `rules_fingerprint` (`cache_key`) alone never identifies the configuration, because callers vary the configuration under the same key.
2. A freshly spawned worker, or one that does not hold the digest, is configured before its first digest-referencing request, without discarding a healthy worker and within the request's deadline. An in-flight worker death still reports incomplete, as today; no retry is added.
3. Findings, completion and cache behavior are identical to the current behavior.

## Scope

**In scope:** worker request protocol for configuration, the client keying and resend, and tests.

**Out of scope:** folding the path check into the scan request; setup's dry-run reuse (review finding 10, accepted cost: 3-6 s ahead of a much longer build); other worker limits.

## Acceptance Criteria

- [x] AC-1: An N-file scan sends configuration bytes a bounded number of times per worker, and the number of worker processes started is also independent of N. On the current code configuration bytes scale with 2N requests.
- [x] AC-1a: Two scans with the same `cache_key` but different allowlist `paths` produce their respective findings. Referencing by `cache_key` alone would apply the stale allowlist and fail this.
- [x] AC-2: Killing the worker between requests leads to a respawn that is configured and completes the scan with the same findings. Killing it during a request reports that file incomplete, unchanged from today.
- [x] AC-3: The existing reference and consumer scanner tests pass unchanged, giving identical findings and completion.
- [x] AC-4: The change's own suites and every test it adds pass, the documents it edits validate, and no failure elsewhere is attributable to this change.

## Tasks

- [x] Add a configure-by-key request and key references in scan/path requests.
- [x] Resend on unknown key or respawn.
- [x] Add regression tests, including request-size accounting and a respawn control.

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| protocol   | implementer | 22qoz      | same files |


## Serialization Points

- `.wavefoundry/framework/scripts/wave_lint_lib/`, `.wavefoundry/framework/scripts/tests/`

## Affected Architecture Docs

N/A: an internal parent-child protocol detail with no boundary change.

## Platform Behavior

The protocol is pipe-based and platform-neutral. Respawn behavior is unchanged on Windows, macOS, Linux and WSL2.

## AC Priority


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | important | The performance outcome. |
| AC-1a | required | Guards against stale configuration (red-team RT-6). |
| AC-2 | required  | Must not create false incomplete results. |
| AC-3 | required  | No behavior change. |
| AC-4 | required  | Change-local verification. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-11-06 | Planned from verified review finding 9; finding 10 accepted as a cost. | Verifier probe f9 (102 requests, 45.4 MB, 50 files) |
| 2026-11-06 | Implemented in `betterleaks_worker.py`. `config_digest(config, cache_key)` is sha256 of the `_encode`d config plus the key. The client computes it on the exact config it would send, including per-call allowlist, stopword and path arguments, then sends `path_excluded` and `scan` with `config_digest` instead of `config` and `cache_key`. The child configures through the existing `configure` operation, which sends the full config and is now digest-echoing. The client keeps the configured digest on the process object (`process.config_digest`) and resets it in `_start` and `_drop_process`. When the digest differs, `configure` is sent inside the same `_exchange`, under the original deadline and budget, and the echoed digest must match. The child recomputes the digest from what it received; a `config_digest` label in a configure payload is ignored. A digest-only request the child does not hold is refused with the new `_ERROR_CODES` code `configuration_not_held`. The client then clears its belief, keeps the healthy child and reports the error, with no mid-request retry. An explicit `configure` call also records the digest. Full-config requests remain accepted by the child. | Shipped profile, 50 files: HEAD sends 102 requests (101 with config, 45,376,609 wire bytes); after the change, 102 requests (1 with config, 1,383,007 bytes). Client-side encoding for the digest remains; transfer, child decoding and validation of the config, and child hashing are removed. |
| 2026-11-06 | AC tests in `tests/test_scanner_worker_config.py` (7 tests OK via `run_tests.py --file`; stable over 6 repeated runs). AC-1, `test_config_bytes_and_worker_starts_do_not_scale_with_file_count`: config requests and `_Client._start` counts are equal for 3 and 12 files (one start), and bytes differ by at most 32 (request id and budget digits). AC-1a, `test_same_cache_key_with_different_allowlists_keeps_separate_results`: the same `cache_key` with different allowlist paths, and with different value regexes, gives separate results through internal calls. AC-2: `test_worker_killed_between_requests_is_respawned_configured`, `test_worker_killed_between_files_of_one_scan_is_respawned_configured`, and `test_worker_killed_during_request_reports_that_file_incomplete` (`worker_crashed` skip, then a respawn). Protocol: `test_unheld_digest_is_refused_and_the_healthy_child_is_kept` and `test_child_computes_the_digest_and_ignores_a_client_label`. | Known-bad, each in a scratch copy outside the framework tree. The HEAD worker fails AC-1 (config requests scale with N). Keying on `cache_key` alone fails AC-1a. Tracking the digest on the client instead of the process fails the between-files respawn test. Dropping the child on `configuration_not_held` fails the keep test. A child trusting the configure label fails the label test. |
| 2026-11-06 | AC-3 and platform behaviour. The protocol is pipe-based and platform-neutral, so Windows, macOS, Linux and WSL2 behave the same, and respawn is unchanged. Executed on macOS only. | Existing suites unchanged and passing via `run_tests.py --file`: `test_betterleaks_engine` (30, including the 474-rule oracle), `test_scan_completion`, `test_secrets_validators` (171), `test_secret_scan_cache`, `test_scan_secrets`, `test_secrets_prefix_collapse`, `test_mcp_scan_completion`, `test_tree_kill_routing`, `test_lifecycle_golden`, `test_scanner_skips`: 362 tests OK with the new files. `test_server_tools_lifecycle`: 666 OK. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-11-06 | Readiness repair (red-team RT-6/RT-7): key on a client-computed digest of the exact config, reuse the existing `configure` operation, and use no mid-request retry. | `cache_key` is `rules_fingerprint`, not a content hash. | Keying by `cache_key` |
| 2026-11-06 | Configure once per key, with resend on unknown key. | The engine is already cached per child by key, so this removes only the redundant transfer. Efficacy: the measured 45 MB/50 files drops to about one configuration per worker. | Fold the path check into scan (halves the cost only); shared-memory configuration (platform-specific). |
| 2026-11-06 | Exclude finding 10. | 3-6 s measured, against longer model preparation and builds; the setup index path is fragile. | Reuse the dry-run plan for the real build. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A key mismatch uses a stale configuration | The key is a digest of the exact configuration, verified by the worker; AC-1a is the control. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
