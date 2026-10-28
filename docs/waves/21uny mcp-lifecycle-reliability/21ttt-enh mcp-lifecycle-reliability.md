# MCP Lifecycle Reliability

Change ID: `21ttt-enh mcp-lifecycle-reliability`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-27
Wave: 21uny mcp-lifecycle-reliability

## Rationale

An operator expected MCP reload to replace Python processes. Inspection and an actual Codex daemon restart showed the old servers exited when their host connections ended; reload intentionally retains the process. An isolated stdio probe exited normally after EOF, before and after two reloads. No production process leak is established. Source inspection of `server.build_server.inference_lifespan` shows no shutdown finalizer; `ImplHandler.close` handles resource cleanup during reload, while its monitor-stop methods discard references without checking join completion. These are verified source observations; adverse active-work consequences remain unverified until regression probes execute.

## Product Intent

Operators and coding agents can distinguish reload from process restart, identify the serving process, and receive explicit cleanup outcomes when a connection ends or reload cannot stop an old worker. AC-1 through AC-4 together demonstrate this outcome. Wavefoundry owns handler resources; the host owns session lifetime and Tensorwell remains an independent shared service.

## Requirements

1. Reload and server-info expose additive process identity (PID, parent PID, project root, uptime) and reload semantics. Reload explicitly reports process unchanged and preserves existing version/restart diagnostics. Uptime measures server lifetime, not time since implementation reload.
2. Normal serving teardown, exception, or cancellation through the lifespan closes the current handler even after reload. Cleanup is idempotent, bounded for monitor joins, attempts remaining resources after a cleanup failure, and reports failures on stderr without corrupting stdio or masking the original serving exception.
3. Monitor shutdown signals stop and checks bounded join completion. A surviving worker remains identifiable and produces an explicit incomplete-cleanup warning; reload must not create another handler while its previous monitor still runs. Later cleanup/reload can retry once it stops. Preserve healthy reload behavior.
4. Tests exercise actual stdio startup, repeated reload, EOF, and disconnect during finite active work, plus direct failure/cancellation and monitor-timeout cases. No live user session, shared Tensorwell service, model download, or external network is needed. Fixtures terminate and reap only their own children on failure.
5. Document the ownership boundary and recovery: reload updates implementation in place; process restart requires the host; an idle connection is not proof of abandonment.
6. Before destructive reload cleanup, prevent new monitor callbacks from entering and wait a bounded time for active callbacks to finish. If preparation times out or raises, release the pause without stopping either monitor or disposing handler resources; identify the blocked resource and distinguish this refusal from failure after destructive cleanup begins. Use the same synchronization boundary for callback entry and preparation to prevent a check/start race. Healthy reload proceeds only while callbacks remain paused; process shutdown retains best-effort cleanup.

## Scope

**In scope:** runner lifespan and reload, handler cleanup and process diagnostics, focused tests, MCP specification and architecture documentation.

**Out of scope:** killing other sessions, idle timeouts, process registries or new daemons, replacing stdio, changing Tensorwell lifetime or host config, immediate interruption of arbitrary blocking native work, or graceful SIGKILL handling.

## Platform Behavior

Expected Windows behavior follows the same in-process reload and handler-cleanup contract: process identity uses Python OS APIs, uptime uses a monotonic clock, and monitor shutdown uses threading events and bounded joins. These changes introduce no Unix signal or process-group dependency. This is source-grounded intent, not native platform qualification. All execution evidence for this wave was collected on macOS; native Windows, Linux and WSL execution remain unverified. Windows qualification should exercise actual stdio initialization, repeated reload with immediate tool calls, idle and finite-work EOF, monitor timeout/refusal/retry, and owned-child cleanup. The Codex daemon restart command used in this session is macOS host recovery evidence, not a verified Windows procedure.

## Reload Failure Behavior

The baseline implementation uses best-effort cleanup without rollback when reload is refused. The operator-authorized extension below changes preparation refusal to preserve handler resources and resume monitor scheduling; the following partial-cleanup limitation remains applicable after destructive cleanup starts. A monitor that stopped remains stopped on the retained handler; telemetry, cache and index resources may also have been released. A successful later reload recreates the handler and its configured monitors; retry alone cannot guarantee recovery while the original worker remains stuck. Persistent failure requires host-owned restart. The refusal therefore preserves ownership of surviving workers, not uninterrupted service from the old handler.

This deliberately tightens earlier behavior: cleanup errors previously allowed reload to continue with a warning; they now prevent module reload and handler replacement. Reversible monitor quiescence before destructive cleanup is now admitted as Requirement 6 and AC-6/7; implementation evidence is recorded in Progress Log. A blocked callback itself is not cancelled or duplicated.

## Acceptance Criteria

- [x] AC-1: Public server-info and successful reload identify the same process and project; uptime does not reset across reload, and reload explicitly reports process unchanged with existing restart-required information preserved. Missing identity or ambiguous reload fails the oracle.
- [x] AC-2: Lifespan teardown closes the currently installed handler after reload, including exception/cancellation paths; cleanup failures are observable without masking the original error or preventing remaining cleanup. Tests fail if the finalizer is absent or closes only the startup handler.
- [x] AC-3: A deliberately nonterminating monitor produces bounded, named incomplete-cleanup reporting and prevents replacement handler creation; its reference remains available for retry. Healthy monitors stop and repeated reloads do not accumulate workers. Ignoring a join timeout fails the oracle.
- [x] AC-4: Subprocess tests complete real MCP initialization and reload requests, prove same PID across reload, and observe bounded exit on idle EOF and EOF during finite active work; failure cleanup reaps owned children. An intentionally retained input or nonexiting test server fails the exit oracle. Tests never stop a shared Tensorwell service.
- [x] AC-5: Updated MCP and architecture docs distinguish reload, cleanup outcomes, host-owned session lifetime, and shared-service lifetime; the change's own tests and edited documents validate, with no unrelated failure attributed to this change.

- [x] AC-6: With either monitor callback held active, registered reload refuses within a bounded preparation deadline, retains the same handler and both worker identities, leaves stop events unset and cache/index/telemetry intact, and resumes ordinary monitor callbacks after release without requiring another reload. An implementation that calls close before successful preparation fails this oracle.
- [x] AC-7: Successful preparation prevents new callbacks from entering through the cleanup boundary, including a callback-entry race; successful retry then reloads with healthy registered tools and no additional workers. Shutdown still stops paused workers, and failure after destructive cleanup starts is explicitly distinguished from preparation refusal. The change's own tests pass and edited docs validate.

## Tasks

- [x] Implement additive process diagnostics and explicit reload semantics.
- [x] Implement current-handler lifespan cleanup and monitor failure reporting/retry safety.
- [x] Add focused lifecycle and actual stdio subprocess tests with known-bad evidence.
- [x] Update MCP/architecture contracts and run focused and canonical verification.
- [x] Complete independent delivery review and record evidence.

- [x] Implement reversible monitor preparation and separate reload failure phases.
- [x] Verify timeout rollback, callback-entry ordering, successful retry and shutdown with actual monitor threads and registered tools.
- [x] Update contracts/platform limits and complete refreshed qualification and independent review.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Lifecycle implementation and tests | implementer | readiness | Coordinator owns tightly coupled source edits |
| Independent review | code-reviewer, qa-reviewer, architecture-reviewer | frozen packet | Fresh independent contexts; council per policy |

## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/server.py`
- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`
- `.wavefoundry/framework/scripts/tests/test_mcp_lifecycle.py`
- `.wavefoundry/framework/scripts/tests/test_index_source_guard.py`
- `.wavefoundry/framework/scripts/tests/test_setup_readiness_integration.py`
- `.wavefoundry/framework/scripts/tests/test_server_context_efficiency.py`
- `docs/specs/mcp-tool-surface.md`
- `docs/architecture/data-and-control-flow.md`

Serialize source writes; freeze review fingerprints. No seed, platform, dependency or unrelated vision edits.

## Affected Architecture Docs

`docs/architecture/data-and-control-flow.md`: serving teardown, reload identity, incomplete monitor shutdown and host/shared-service ownership. `docs/specs/mcp-tool-surface.md`: additive response and failure semantics.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Removes ambiguity that triggered investigation |
| AC-2 | required | Explicit owned-resource teardown |
| AC-3 | required | Prevents silent worker accumulation |
| AC-4 | required | Verifies actual transport/process behavior |
| AC-5 | required | Accurate operator expectations |
| AC-6 | required | Preparation refusal preserves the current handler |
| AC-7 | required | Quiescence and recovery are race-safe and distinguish failure phases |

## Progress Log

2026-10-27: Two-phase extension complete. Final canonical suite passed 12,281 tests / 214 files / 12 skips / 555.492s, exit 0; receipt result ok, inputs hash 7762ecb578e583a256853250e82c015c1ed937b0d6be3194b28b455c6de313bf. All seven ACs and all tasks complete. Fresh code/architecture/QA/docs and full council delivery approvals recorded; no new findings. Readiness wording refresh e9ef2647a41b046ea5c5 changed only a stale implementation-status sentence, with each original lane comparing the normalized delta and explicitly reusing its prior readiness evidence. No source changed after qualification. Wave remains open for operator signoff/closure; no commit or live runtime activation performed.

2026-10-27: Independent code-review probe derived a staggered two-callback invariant: hold both actual callbacks on distinct events, invoke registered reload on a separate execution thread, release only the index callback and require reload to remain unfinished with resources intact; release the CE callback within the preparation budget, then require successful replacement, both old workers stopped and immediate registered server-info with the same PID. Probe passed. This independently exercises the all-active-callback drain requirement; scratch implementation is disposable, recipe retained here. Chair independently passed three new lifecycle methods (4.723s) and actual stdio class (7.846s); targeted false-success preparation injection failed both registered callback cases as expected. Other reviewers confirmed their remits with their own controls. Repeated maintained tests are correlated corroboration, not independent discoveries. Reality used a whole-file mutant rather than targeted-first; disclosed, no rerun. Native Windows/Linux/WSL execution, arbitrary foreground/native quiescence and post-cleanup rollback remain outside the claim.

2026-10-27: AC6/7 and implementation/tests tasks complete. Final focused lifecycle file: 11 tests / 14.238s, zero skips; adjacent SourceGuardTests/SharedAssessmentTests/PathFreeMonitorRowTests: 22 / 2.379s, zero skips. Registered-tool tests hold either actual callback, prove refusal preserves identities/events/cache/telemetry, release it and prove subsequent ordinary callback progress, then retry reload and call registered server-info. A controlled interval boundary proves callbacks ready before pause cannot enter after preparation; close stops both paused workers. Preparation exception rolls back admission. Isolated source mutants bypassing prepare, omitting rollback, omitting entry gate, and omitting CE active bookkeeping each fail the named lifecycle oracle with assertion failures, no unittest errors. Mutant recipes: replace prepare call with complete success; suppress failure-finally pause reset; suppress both paused checks; remove CE active-set insertion. Routine logs and quiesce-mutants.json remain in work area. Full docs validation clean. Canonical suite and refreshed independent delivery review pending.

Readback: AC6/7 add reversible preparation before existing destructive cleanup. Before, a blocked callback can leave its healthy peer stopped and handler resources disposed. After, a preparation refusal keeps the same workers/resources and releases the pause; actual stuck work is neither cancelled nor duplicated. Source changes are runner/handler; lifecycle tests exercise registered tools and real callbacks; three existing constructor-bypass fixtures gain synchronization state. Docs distinguish failure phases and platform limits. The one-second deadline bounds preparation waiting, not the pre-existing projection barrier. Full current readiness council and all four lanes passed on receipt 28fd8c11b4c159422f33; source edits begin only after successful Prepare/Implement.

2026-10-27: Operator requested implementing the proposed reversible preparation. Existing change extended before code edits; readiness and delivery review must be refreshed. Baseline executed through perform_mcp_reload with an actual blocked monitor and an actual stoppable peer: reload refused while peer stopped and index/cache/telemetry were released. Proposed fix is not yet executed. Original AC-1 through AC-5 evidence remains historical; new AC-6/7 and three tasks are pending.

2026-10-27: Implementation and delivery review complete. Final canonical qualification after the test repair passed 12,278 tests across 214 files, 12 skips, in 547.348s (exit 0); receipt result ok, inputs hash c77de6d0f24d9facabadbf943e3986041fc0997c860a5617a4d8e70a22c47ee1. Routine log: `.wavefoundry/work/21uny/canonical-final-tests.log`. Fresh code/QA reviewers independently passed all eight lifecycle tests and caught old-name mutants on the first reload. QA independently cleared the required finding in cycle 1; code, QA, architecture, docs-contract and council-delivery approvals are current. All ACs and tasks complete. Wave remains open; no operator signoff, closure or commit inferred.

2026-10-27: Durable reproduction recipe for the council's unique composed recovery probe: create an actual handler with staleness polling at 0.01s, block its `assess_setup` callback on a threading Event, then call `perform_mcp_reload`. Require named index-monitor cleanup refusal and unchanged handler/module/thread/stop-event ownership. Release the callback and join, perform an actual second reload, then call registered `wf_server_info` through FastMCP and verify the same PID/root and a live replacement monitor. The independent probe passed. Maintained companion coverage is in `HandlerCleanupTests`, `RunnerCleanupTests` and `McpStdioLifecycleTests`; the scratch script is disposable. This establishes controlled timeout/refusal/recovery, not arbitrary native interruption or host-session expiry.

2026-10-27: Repair cycle 1 (typed start recorded before edits) changed only `test_mcp_lifecycle.py`: fixture tools now use valid wf_ prefixes; every reload requires nonzero registration and an immediate public server-info identity/uptime check before worker-count comparison. Focused file: 8 passed / 10.064s. Restoring original invalid prefixes in an isolated test-file copy fails on the FIRST reload (0 not greater than 0), proving the repaired oracle catches the original issue. Product source, contracts and AC meaning unchanged. Fresh focused code/QA review and final canonical requalification follow.

2026-10-27: Host-access canonical run passed 12,278 tests/214 files/12 skips in 553.125s; full docs validation passed. Delivery finding `21uny-qa-lifecycle-fixture-prefix` reopens AC-3/4 and test task: invalid test helper prefixes degrade the first reload, but the after-third-reload info assertion lets the maintained test pass. QA independently corrected scratch names and composed timeout/refusal/release/reload succeeded; production regression not established. All initial review findings are being collected before one focused test-only repair.

2026-10-27: Canonical first run executed 12,278 tests across 214 files / 536.390s, 12 skips. Seven failed files: registry handler-digest guard caught an unnecessary server-info docstring change (removed; public contract remains in spec), and six files failed sandbox permissions for ps, local sockets, or tool-environment/cache test writes. Preserved first-run log in work/canonical-tests.log and runner refused receipt 42e8a26ea3eb41ddb36087de613dbc4b. No unrelated code changed; retry uses host access.

2026-10-27: AC-2 complete: actual FastMCP lifespan closes the latest handler after reload for normal exit, error and cancellation; cleanup failure preserves body error and writes stderr only. Final focused lifecycle run: 8 tests / 10.168s; package census: 31 tests / 23.182s. Integration repaired stale inference-provider mocking after reload; each subcase now patches the freshly imported module and asserts intercepted startup. No product scope change. Mutation controls in isolated copies detected all four defects: absent finalizer and startup-handler-only finalizer fail `RunnerCleanupTests.test_lifespan_closes_current_after_real_reload_for_normal_error_and_cancellation`; ignored timeout fails `HandlerCleanupTests.test_real_monitor_timeout_retains_reference_reports_and_retries`; removed refusal fails `RunnerCleanupTests.test_reload_refuses_incomplete_or_raised_cleanup_before_module_or_handler_replacement`. All mutated copies exited with assertion failure; no repository-source mutation.

2026-10-27: New lifecycle file: 8 tests passed in 9.857s. AC-1 actual JSON-RPC identity/uptime across three reloads; AC-3 actual monitor survivor/reference/retry and refusal-before-reconstruction; AC-4 idle and entered finite-work EOF plus retained-input/nonexiting-child exit-oracle controls. Test-owned subprocesses reaped; explicit local provider and offline/no-install environment. Maintained proof: `test_mcp_lifecycle.McpStdioLifecycleTests`, `HandlerCleanupTests`, `RunnerCleanupTests`. Final mutation checks and delivery review pending.

2026-10-27: Source implementation complete; existing reload-focused tests: 47 passed in 23.905s; ImplHandlerCloseTests: 2 passed in 1.426s. Process identity preserved through module dictionary; cleanup refuses module reload/build on failure. New AC-specific transport and failure probes remain in progress. Evidence: `.wavefoundry/work/21uny/reload-focused.log` (disposable routine log), maintained existing test classes.

Readback: AC-1 through AC-5 add explicit same-process identity and uptime, close the current handler on lifespan exit, retain and report monitors that exceed bounded joins, and refuse replacement until cleanup succeeds. Before: EOF never calls close and timeout loses worker identity. After: current-handler cleanup runs and incomplete reload returns retry guidance. Source: server.py/server_impl.py; tests: test_mcp_lifecycle.py and existing server tests as needed; docs: MCP spec and data/control flow. Host/session and Tensorwell lifetimes remain outside scope.

Thought: implement runner/handler jointly while a separate implementer authors the isolated regression tests against the admitted ACs; source and test ownership do not overlap.

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-27 | Planning: host restart removed old MCP PIDs; isolated EOF probes exited in 0.074s and 0.126s without forced termination. Baseline only, not universal shutdown proof. | Session diagnostic; `server.perform_mcp_reload`, `server.build_server`, `ImplHandler.close` reads |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-27 | Add diagnostics and bounded cleanup using existing ownership | Addresses observed confusion and source cleanup gaps without claiming a demonstrated leak. Diagnostics advise; finalization and reload refusal control cleanup. Idle host connections remain outside server control. Measure using public identity and shutdown regression oracles. | Diagnostics alone leaves cleanup gaps; idle termination disrupts legitimate sessions; new supervision adds unnecessary complexity. |

2026-10-27: Selected reversible callback quiescence over (a) restarting stopped monitors, which races surviving threads and cannot restore disposed resources, and (b) mandatory host restart, which removes healthy in-process reload. A shared condition guards callback entry, a pause request and active callback identities; preparation waits at most one second for active work, rolls back the pause on failure, and leaves it held on success until cleanup stops workers. This controls resource preservation, rather than merely advising retry. It cannot interrupt stuck native work or undo a failure after cleanup starts. Existing stop/join logic remains the shutdown path. Success is measured by resource/thread identity, resumed callback progress after refusal, and healthy registered tools after successful retry; a false-idle race must fail tests.

## Risks

| Risk | Mitigation |
| --- | --- |
| Obsolete handler captured at startup | Resolve current handler at teardown; test reload-before-exit |
| Slow native work delays EOF | Bound finite-work fixture; exclude arbitrary uninterruptible work |
| Warnings corrupt JSON-RPC | stderr-only shutdown reporting and actual protocol tests |
| Timeout creates duplicate monitors | Preserve references and refuse replacement until stopped |
| Tests interfere with user processes | Isolated framework, local/no-network provider, owned-child-only reap |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
