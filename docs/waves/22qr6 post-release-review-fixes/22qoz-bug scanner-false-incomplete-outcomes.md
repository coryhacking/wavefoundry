# Scanner false or unexplained incomplete outcomes

Change ID: `22qoz-bug scanner-false-incomplete-outcomes`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-11-06
Wave: 22qr6 post-release-review-fixes

## Rationale

Wave 22qky made incomplete scans of eligible files block close and fail docs-lint. A post-release code review, independently verified on HEAD `1ef5e0c9`, found three ways that this outcome is wrong or unexplained:

1. **Decoded-size expansion (executed).** `wave_lint_lib/secrets_validators.py` decodes content with `errors="replace"` before handing it to the worker. Each invalid byte becomes U+FFFD (3 UTF-8 bytes, 6 on the `ensure_ascii` wire). A 2,097,119-byte dense Latin-1 file decoded to 6,222,599 UTF-8 bytes and was recorded as `upstream scan incomplete: worker_input_too_large` on every scan. The file is under the 5 MiB read guard, so its reason misleads, and rescanning can never clear it.
2. **Idle alarm (executed with a patched 2 s timeout).** `wave_lint_lib/betterleaks_worker.py` `_serve` arms a 115 s SIGALRM with the default handler before blocking in `readline`. An idle reusable worker kills itself (return code -14). The client normally respawns it, but a request that races the alarm is recorded as `worker_crashed`, which is a false incomplete scan.
3. **No remedy for deterministic skips (executed).** A 6.29 MB file is correctly incomplete under 22q2w AC-1: resource limits and unreadable input are failures, not intentional exclusions. However, the `[scan-incomplete]` message and the CLI/MCP payload do not say that rescanning cannot help, or that an explicit `[allowlist] paths` entry is the supported way to exclude the file. Adding such an entry was verified to make the scan complete.

## Product Intent

Operators whose repositories hold large or non-UTF-8 text files, and anyone whose MCP server stays idle between scans, see a scan recorded as incomplete only when the scan actually failed. That outcome names the true cause and a remedy that works. The 22q2w completion policy is unchanged: resource-limit and unreadable failures still block close.

## Requirements

1. Before sending, and after path exclusion, the parent checks the CRLF-normalised decoded content against each fixed engine input limit, using exactly the engine's predicates and constants, preferably through one shared engine helper: `len(content.encode('utf-8')) > MAX_CONTENT_BYTES`, and the newline count `content.count('\n') > betterleaks_engine.MAX_LINES`. The newline count is not `splitlines()` and not a line count. A file over either limit is not sent and is recorded with a deterministic reason naming that limit (decoded size or line count), not `worker_input_too_large` or `detection_or_filter_work_incomplete`.
2. The reusable worker never terminates while idle waiting for a request. The request deadline still bounds the processing of each request.
3. The fixed-limit reasons, `file too large` and the new decoded-size and line-count reasons, carry remedy text derived from one `scanner_skips` projection and used by every `[scan-incomplete]` producer (docs-lint, CLI and MCP completion payload). The remedy says that rescanning alone will not clear it. It names the supported fixes: convert or split the file, or, after confirming the file holds no secrets, add an explicit project `[allowlist] paths` exclusion anchored to that one path (`^` + escaped path + `$`). Other reasons keep their current text. Limits that can only be detected during matching (engine match caps and filter errors) are not classified here, because `_scan_upstream_raw` collapses them into one detail (`detection_or_filter_work_incomplete`).

## Scope

**Problem statement:** false or unexplained incomplete-scan outcomes block close.

**In scope:** parent-side decoded-size check, idle-timer disarm in the worker loop, remedy text for deterministic incomplete reasons, tests and docs touched by those strings.

**Out of scope:** changing which reasons count as intentional exclusions; raising the worker or request caps; scanner rule content; classifying limits detected only during matching (this would need a ledger detail schema change; follow-up).

## Acceptance Criteria

- [x] AC-1: A roughly 2 MiB file of mostly invalid UTF-8 bytes with no NUL in the sniff window is reported with the decoded-size reason and remedy, and never with `worker_input_too_large`. A control file whose decoded size is just under the cap still scans completely. On the current code the oversize fixture produces `worker_input_too_large`.
- [x] AC-1b: A file under 5 MiB with `MAX_LINES + 1` newline characters is recorded with the line-count reason and remedy, not `detection_or_filter_work_incomplete`, and becomes complete once an anchored `[allowlist] paths` entry is added. Two controls must scan completely: `MAX_LINES` newlines followed by an unterminated final line (`MAX_LINES + 1` lines), and a file whose separators are form feeds rather than newlines. A residual `detection_or_filter_work_incomplete` outcome receives no fixed-limit remedy. On the current code the over-limit file produces `detection_or_filter_work_incomplete` with "retry".
- [x] AC-2: With the worker timeout patched short, a worker left idle past the timeout serves the next request on the same process ID, and the timeout still ends a request that runs past it. On the current code the idle worker exits with SIGALRM.
- [x] AC-3: An oversize file's incomplete outcome carries the remedy text in docs-lint, CLI and MCP output, stays incomplete across rescans and becomes complete once an `[allowlist] paths` entry is added. A non-size incomplete reason (for example a worker timeout) does not receive the size remedy.
- [x] AC-4: The change's own suites and every test it adds pass, the documents it edits validate, and no failure elsewhere is attributable to this change.

## Tasks

- [x] Add the parent-side decoded-size check and reason.
- [x] Disarm the worker's idle timer and arm it only around request processing.
- [x] Add remedy text for deterministic incomplete reasons and update affected docs.
- [x] Add regression tests with known-bad controls.

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| scanner    | implementer | —          |       |


## Serialization Points

- `.wavefoundry/framework/scripts/wave_lint_lib/`, `.wavefoundry/framework/scripts/scanner_skips.py`, `.wavefoundry/framework/scripts/run_secrets_scan.py`, `.wavefoundry/framework/scripts/tests/`

## Affected Architecture Docs

`docs/architecture/data-and-control-flow.md` only if the scanner outcome paragraph names reasons. Otherwise N/A: there is no boundary or ownership change.

## Platform Behavior

SIGALRM is POSIX-only (macOS, Linux, WSL2). The Windows worker has no SIGALRM path, so the idle fix has no effect there, and parent-side request deadlines behave as before. The decoded-size check and remedy text are platform-neutral.

## AC Priority


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | A permanent false failure blocks close. |
| AC-1b | required | Same false-remedy defect through the line limit (chair finding). |
| AC-2 | required | A false `worker_crashed` blocks close. |
| AC-3 | required | Without a remedy, operators cannot recover. |
| AC-4 | required | Change-local verification. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-11-06 | Coordinator follow-through for Requirement 3: the `wf_scan_secrets` `scan_incomplete` diagnostic (`wf_server/docs_handlers.py`) and the close `secret_scan_incomplete` message (`wf_server/server_impl.py`) now take their closing guidance from `scanner_skips.incomplete_guidance`; non-fixed-limit text is unchanged. | `test_scanner_input_limits` AC-3 test asserts the MCP diagnostic carries the remedy (13 OK); close message covered by full suite |
| 2026-11-06 | Planned from verified post-release code review findings 1, 2 and 3. | Verifier probes f12/f1b/f2/f3 (session scratchpad) |
| 2026-11-06 | Requirement 1: added `betterleaks_engine.exceeded_input_limit`, one predicate used by both the engine's `scan` and the parent. It uses the engine's `MAX_CONTENT_BYTES` and `MAX_LINES` and copies neither. The checks are encoded byte length > `MAX_CONTENT_BYTES`, then `content.count("\n")` > `MAX_LINES`, never `splitlines()`. The parent runs it in the upstream branch of `scan_file_raw` after `_upstream_path_excluded` and after CRLF normalisation. The two reasons are `decoded content too large` (detail `<n> bytes > <cap> decoded cap`) and `too many lines` (detail `<n> newlines > <cap> cap`). The encode uses the engine's existing `surrogateescape` form: any string that strict `encode('utf-8')` accepts encodes identically, and the parent's replacement-decoded text has no surrogates. The engine and worker `MAX_CONTENT_BYTES` are both 5 MiB. Under the full 474-rule ruleset, the just-under-cap control (5,242,878 decoded bytes) scanned completely in 0.74 s; line and mixed Latin-1 variants took 0.42 s and 1.06 s, all far inside the 115 s budget. | `test_scanner_input_limits` (13 tests OK via `run_tests.py --file`), including `test_decoded_size_just_under_cap_scans_completely_with_full_ruleset` and `test_shared_predicate_matches_engine_refusal_exactly`. Probe on HEAD code: the oversize fixture gives `worker_input_too_large`; the `MAX_LINES + 1` fixture gives `detection_or_filter_work_incomplete` with "retry". Mutant `limit = None` (no parent check): 4 failures and 1 error. Mutant using `splitlines()`: both newline controls and 2 predicate subtests fail. |
| 2026-11-06 | Requirement 2 (`_serve`): the loop disarms the timer (`setitimer(ITIMER_REAL, 0)`, guarded by `hasattr`) before `readline`. After a line arrives, it arms `MAX_TIMEOUT_SECONDS` for decoding, then the request budget, which stays armed through the response write. | The tests copy the worker with the timeout patched to 0.5 s. `test_idle_worker_serves_next_request_on_same_process` keeps the same process after 1.5 s idle. `test_request_alarm_still_ends_an_overlong_request_at_the_worker` sees the worker exit with -SIGALRM; the parent never kills it. `test_closing_input_ends_an_idle_worker` shows an idle worker exits 0 on EOF. Probe on HEAD code: the idle worker returned -14 after 1.5 s. Mutant restoring the idle alarm fails the idle and EOF tests. Mutant removing the request alarm makes the request test fail (no exit within 10 s). |
| 2026-11-06 | Requirement 3: added one `scanner_skips` projection: `fixed_limit_remedy(row)`, backed by `allowlist_entry(rel)` and `incomplete_guidance(rows, retry)`. `scanner_completion` rows with a fixed-limit reason (`file too large`, `decoded content too large`, `too many lines`) gain `remedy`, which names the TOML-valid anchored entry `'^' + re.escape(rel) + '$'`; that reaches the CLI and MCP payloads. The two `[scan-incomplete]` summaries use the same projection: `secrets_validators` (the old "retry" line) and `scanner_completion_failures`. They stay path-free, so the existing `test_parallel_path_skips_oversized_file_in_worker` passes unchanged. Without a fixed-limit row the summaries keep their current "retry" text. Updated `docs/specs/mcp-tool-surface.md`, `docs/contributing/build-and-verification.md` and `CHANGELOG.md`. `data-and-control-flow.md` names no reasons, so it is N/A. Out of the serialization scope and left unchanged: the generic `scan_incomplete` diagnostic text in `wf_server/docs_handlers.py` and the close messages in `server_impl.py`. | `test_remedy_reaches_docs_lint_cli_and_mcp_and_allowlist_clears_it` covers record-only docs-lint, the in-process CLI and a real `wf_scan_secrets_response` subprocess. It also shows the outcome stays incomplete over two rescans and the remedy's own entry clears it. `test_read_guard_size_gets_remedy_but_worker_timeout_does_not`, `test_residual_engine_incompleteness_keeps_retry_text_without_remedy` and `RemedyProjectionTests` (tomllib round trip; Go-regex compile matches only that path) also pass. Mutant where the projection returns no remedy: 2 failures and 5 errors. |
| 2026-11-06 | Platform behaviour. macOS, Linux and WSL2: the idle worker is unbounded and the request alarm still applies. Windows has no `setitimer`, so `_disarm` and `_alarm` do nothing and parent-side deadlines are unchanged. The size and line check and the remedy text are platform-neutral, and the remedy entry is a POSIX repo-relative path. Executed on macOS only; Windows, Linux and WSL2 were not run. | AC-4 suites, all through `run_tests.py --file`: `test_betterleaks_engine`, `test_scan_completion`, `test_secrets_validators`, `test_mcp_scan_completion`, `test_secret_scan_cache`, `test_scan_secrets`, `test_secrets_prefix_collapse`, `test_scanner_skips`, `test_tree_kill_routing`, `test_lifecycle_golden` and both new files: 362 tests OK. `test_server_tools_lifecycle`: 666 tests OK. No `__pycache__` under `.wavefoundry/framework/`. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-11-06 | Readiness repair 2 (chair finding `22qr6-chair-22qoz-line-cap-remedy`, operator-chosen bounded repair): one parent-side check of both fixed engine input limits, decoded bytes and `MAX_LINES`, each with its own reason and the shared remedy. Efficacy: the chair's 210,000-line, 1.26 MB fixture gets an accurate reason and a working remedy. | Line count is checkable before send like decoded size. | Defer the line limit to a follow-up |
| 2026-11-06 | Readiness repair (red-team RT-1): engine-cap remedies are scoped out; the remedy comes from one projection. Red-team alternative `surrogateescape` decoding (which would scan such files fully) is rejected: it changes line hashes for lines with invalid bytes and churns existing exceptions. The decoded-oversize file remains a real resource-limit failure under the 22q2w policy. | Red-team primer | Scan with `surrogateescape` |
| 2026-11-06 | Detect decoded oversize in the parent and report it accurately. | This is the smallest change; it keeps the 22q2w policy and worker protocol unchanged. Efficacy: the motivating 2 MiB Latin-1 fixture would get an accurate reason and remedy rather than a misleading one; it still blocks close until excluded, which is the intended policy. | Raise the worker content cap to 3x and use `ensure_ascii=False` on the wire. That scans more files, but it changes protocol limits and request sizing, a larger review surface. |
| 2026-11-06 | Disarm the alarm while idle. | Fixes the root cause rather than retrying. | Retry once on `worker_crashed` in the client; that masks real crashes. |
| 2026-11-06 | Remedy text only for finding 1. | Verified that 22q2w intended oversize to be incomplete. | Reclassify oversize as intentional exclusion; that would contradict 22q2w AC-1. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The decoded-size estimate differs from the worker's measured size | Compute it exactly as `len(content.encode('utf-8'))` on the same CRLF-normalised string that is sent, against `betterleaks_worker.MAX_CONTENT_BYTES` imported rather than copied. |
| Disarming the idle alarm leaves an abandoned worker alive | The worker exits when `readline` returns EOF (parent exit closes its stdin); a test closes stdin on an idle worker and observes the exit. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
