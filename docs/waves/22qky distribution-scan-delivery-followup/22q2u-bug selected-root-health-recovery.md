# Keep health recovery on the selected repository

Change ID: `22q2u-bug selected-root-health-recovery`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-11-06
Wave: 22qky distribution-scan-delivery-followup

## Rationale

Waveforge found that `index_health_response` still recommends `wf setup --root .` after the recovery-command repairs. This can select the server's working directory and, on Windows, collide with the Firewall command. A bounded execution of the current response with a selected `/tmp/selected target` and a storage-runtime failure returned that literal and no recovery argv. A rootless `_process_info_status` execution also wrapped the human instruction to select a repository inside an executable-looking `Run` command. Source inspection found bare setup advice in `sqlite_runtime`, `sqlite_vector_store`, `setup_reconciliation` and `process_info`; their individual error branches have not yet all been executed.

## Product Intent

Operators and agents should receive a usable remedy for the repository they selected, without treating an ordinary Git pull or merge as authority or a requirement to run setup. This supports the adopted vision's dependable operation across hosts; it changes recovery presentation, not the product destination or setup ownership. AC-1 through AC-3 jointly establish the outcome.

## Requirements

1. Every setup remedy produced by `index_health_response` uses the existing `setup_commands.setup_recovery` owner with `index.root`, exposing the absolute repository launcher, argument vector and named display-shell dialect. Non-setup remedies retain their restart, incremental index update, rebuild or owned-recovery distinction.
2. The affected storage and process exception producers must not introduce conflicting bare `wf setup` or current-directory commands into these responses. Where a producer knows the selected repository, it can use the existing command helper; where it lacks that context, it describes the failure and setup action in prose and lets the owning boundary attach a command. It must not guess a repository from cwd, a database filename or the framework source location.
3. A missing root yields an instruction to select a repository, empty recovery argv and no shell; callers do not wrap that instruction in command quoting or prefix it as something executable. A pending startup dependency installation retains its existing progress continuation instead of recommending a second setup.
4. Preserve the current readiness policy. Git operations that change files require a read-only readiness/freshness check; they do not automatically run setup. Ordinary application edits remain incremental-index work. Relevant configuration (including framework VERSION), dependency or setup-environment changes retain their existing assessment/remedies. Framework-source-only stamp differences at unchanged VERSION remain a limitation, with live checks still running. Do not add repository-name special cases, Git hooks, automatic setup, or automatic rebuilds. Root-aware bare `wf setup` remains supported by the launcher.
5. Use the shared, distribution-renamable launcher owner. Preserve error codes, preservation warnings, pending-upgrade ownership and no-publication behavior of health checks. Clarify these limits in the existing documentation touched by this repair.

## Scope

**In scope:** `wf_server/index_handlers.py`, the process-information response in `wf_server/server_impl.py`, `setup_commands.py` only if needed for a shared presentation distinction, `sqlite_runtime.py`, `sqlite_vector_store.py`, `setup_reconciliation.py`, `process_info.py`; focused tests for those response boundaries and readiness controls. Coordinator-owned updates to `.wavefoundry/framework/README.md`, `docs/specs/mcp-tool-surface.md`, `docs/contributing/build-and-verification.md`, `docs/architecture/data-and-control-flow.md` and the CHANGELOG describe the behavior.

**Out of scope:** changing readiness inputs, index eligibility, precision/provider selection, storage recovery authority, launcher root discovery, upstream release pins, automatic commands, historical records, unrelated dirty README/version/overview/catalog files and framework seeds.

## Acceptance Criteria

- [x] AC-1: A selected root different from cwd reaches storage-runtime, missing/degraded/absent index setup remedies with the correct repository launcher, argv and display-shell metadata. POSIX and Windows command-shape controls include spaces and metacharacters. Injecting the old root-dot remedy fails the checks; stale-source and stale-runtime controls still recommend index refresh or host restart respectively.
- [x] AC-2: A rootless process failure produces readable selection guidance with no executable argv; a known-root process failure and affected storage exception paths contain no contradictory bare/current-directory command. Pending startup installation still points to progress. Tests reach the response/exception owners rather than checking only helper text.
- [x] AC-3: Isolated readiness controls distinguish ordinary application changes and same-VERSION framework-source differences from relevant VERSION/configuration/environment changes. Read-only checking performs no setup/rebuild/publication, and existing root-aware bare-launcher behavior remains intact.
- [x] AC-4: This change's added and affected focused tests pass, its edited documentation validates, and no failure elsewhere is attributable to this change. Documentation makes the check-versus-setup distinction and selected-root recovery fields explicit.

## Tasks

- [x] Route remaining health setup branches through the shared recovery owner and normalize affected lower-level/rootless advice.
- [x] Add public-response and readiness regression controls, including a known-bad old-remedy control; run affected tests.
- [x] Record results and coordinate the shared specification, architecture and release-note updates.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Recovery behavior and tests | recovery implementer | recorded readiness | Owns named Python paths and focused tests only |
| Shared documentation | coordinator | behavior settled | Serializes shared spec/architecture/CHANGELOG edits across changes |
| Independent verification | review lanes | implementation | Read-only review with actual response controls |

## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/wf_server/index_handlers.py`
- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/setup_commands.py`
- `.wavefoundry/framework/scripts/setup_readiness.py`
- `.wavefoundry/framework/scripts/sqlite_runtime.py`
- `.wavefoundry/framework/scripts/sqlite_vector_store.py`
- `.wavefoundry/framework/scripts/setup_reconciliation.py`
- `.wavefoundry/framework/scripts/process_info.py`
- `.wavefoundry/framework/scripts/tests/test_process_info_callers.py`
- `.wavefoundry/framework/scripts/tests/test_setup_readiness.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools_retrieval.py`
- `.wavefoundry/framework/scripts/tests/test_sqlite_serving.py`
- `.wavefoundry/framework/scripts/tests/test_setup_reconciliation.py`
- `.wavefoundry/framework/README.md`
- `docs/specs/mcp-tool-surface.md`
- `docs/contributing/build-and-verification.md`
- `docs/architecture/data-and-control-flow.md`

Coordinator owns CHANGELOG edits. Source edits require framework-edit authority; no seed edits are planned.

## Affected Architecture Docs

`docs/architecture/data-and-control-flow.md`: clarify selected-root response ownership and unchanged readiness/refresh distinction. `docs/specs/mcp-tool-surface.md`: document structured health recovery. Shared files are coordinator-owned.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Reproduces the field defect and proves the intended remedy |
| AC-2 | required | Prevents contradictory or non-executable advice at adjacent boundaries |
| AC-3 | required | Protects the operator's explicit check-versus-setup constraint |
| AC-4 | required | Keeps the delivered behavior and its contract aligned |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-06 | Planning only. Executed the current `index_health_response` with an injected storage-runtime failure and selected root; observed `wf setup --root .` and no argv. Executed `_process_info_status(None)` with unavailable psutil; observed `Run` wrapping selection prose. | In-process faithful response-boundary probes using `server_tools_support.load_server`, `MagicMock` and `patch`; no setup, model, live index or framework source writes. Lower-level branch coverage remains unverified until implementation tests. |
| 2026-11-06 | Existing isolated setup-readiness suite passed: 54 tests in 6.716 seconds. This validates its existing fixtures, not new recovery behavior. | `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p test_setup_readiness.py` |
| 2026-11-06 | Readback: use the selected root for health/setup recovery and retain portable argv/shell metadata; rootless errors remain human guidance. A runtime failure for a selected target currently returns cwd-relative setup; it will return that target’s launcher. Preserve current readiness inputs and incremental/restart/owned-recovery paths; no automatic setup, source-only policy change or launcher discovery change. AC-1 to AC-3 cover response, exception and readiness controls. | Implementer owns the named recovery Python files and focused tests; shared README/spec/architecture/CHANGELOG edits remain coordinator-owned. |
| 2026-11-06 | Implemented selected-root health recovery with argv/shell metadata, rootless process guidance, rootless storage prose and known-root setup reconciliation commands. Preserved readiness policy and non-setup recovery. Focused canonical runner passed 173 tests across five files with zero skips in 10.534 seconds; its old-remedy injected control was rejected. | `test_process_info_callers.SelectedRootHealthRecoveryTests`; `test_setup_readiness.SetupReadinessTests.test_application_edits_do_not_request_setup_or_rewrite_stamp`; `run_tests.py --file test_process_info.py --file test_process_info_callers.py --file test_setup_readiness.py --file test_setup_reconciliation.py --file test_sqlite_serving.py`. Initial direct unittest runs exposed system-interpreter missing psutil and concurrent-source identity changes; canonical tool-venv run passed without test weakening. |
| 2026-11-06 | Verified bare launcher binding without repair: from `/private/tmp`, PATH selected this checkout’s launcher and `wf setup --check --json` returned existing `setup_inputs_changed` with this checkout’s absolute launcher/root argv. It did not select cwd or execute setup. | Read-only child invocation returned exit 1/action_required; native Windows command shape is exercised by fixtures, not a native Windows host. |
| 2026-11-06 | The broader retrieval test worker passed 1,062 tests with zero skips in 77.470 seconds. The focused run correctly refused a green aggregate because sibling implementation changed upgrade and docs-handler sources while it ran. No repair to these tests was made; the coordinator’s final frozen full suite remains required. | `run_tests.py --file test_server_tools_retrieval.py`; guard identified `upgrade_wavefoundry.py` and `wf_server/docs_handlers.py`. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-06 | Reuse `setup_recovery` at context-owning response boundaries; lower-level errors without a root stay prose-only. | Directly fixes the executed root-dot and rootless presentation failures without a new root-discovery mechanism. The actual caller receives argv plus shell metadata; no automatic action is implied. Measure success through response regression tests and later field use, not claims about every possible caller. | Replacing strings individually leaves inconsistent commands and metadata. Globally forcing setup after Git changes creates unnecessary work and violates the operator's requirement. |
| 2026-11-06 | Preserve current readiness input policy, including source-only same-VERSION limitation. | Current `assess_setup` compares configuration/environment before source hashes; source-only drift deliberately does not request setup. The repair must not expand that contract. | Treating any framework diff as setup-required would undo wave 212yk and is unnecessary for this recovery presentation defect. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Low-level storage code lacks a repository root | Do not infer it; attach commands only at a root-owning boundary |
| Windows display command mistaken for Git Bash syntax | Preserve structured argv and explicit shell dialect |
| Repair overwrites upgrade continuation with setup | Test owned recovery and pending-startup exceptions; preserve existing error codes |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
