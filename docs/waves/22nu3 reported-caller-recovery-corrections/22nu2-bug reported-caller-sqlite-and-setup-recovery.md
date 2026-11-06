# Finish the reported SQLite and setup recovery fixes

Change ID: `22nu2-bug reported-caller-sqlite-and-setup-recovery`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-11-05
Wave: 22nu3 reported-caller-recovery-corrections

## Rationale

The audit after commit 614ac8a2 found that the private-copy SQLite fix reached another test class, while Waveforge's reported DryRunIdleMaintenanceTests._snapshot still opens original databases with mode=ro. Executing that exact method against five temporary WAL/SHM states creates or changes original sidecars in every case. Source tracing and a controlled failure-message probe also show that model preparation omits the selected root from its recovery message. The bounded MCP recovery census found bare setup commands in the no-compatible-index, missing-process-information and failed-upgrade-dependencies paths. No runtime database corruption or native Windows execution is claimed.

## Product Intent

Downstream maintainers should be able to drop the reported SQLite patch and receive usable setup recovery commands for the repository they selected. AC-1 tests the exact reported snapshot caller; AC-2 and AC-3 test root continuity through actual setup and MCP callers. This maintains Horizon 1's dependable existing foundation without changing the adopted vision, adding acceptance gates or starting setup automatically.

## Requirements

1. Make DryRunIdleMaintenanceTests._snapshot inspect isolated copies of each SQLite database and its existing WAL/SHM files. Preserve all committed rows, schema comparisons and non-SQLite artifact comparisons. Leave the original directory's entries and bytes unchanged. This applies only to quiescent test fixtures; runtime SQLite read policy is unchanged.
2. Carry the selected setup root through main, prewarm_models, _prewarm_required_model and _model_failure_message to the existing model-bundle recovery guidance. Both ordinary and prewarm-only setup must retain an explicit --root even when the working directory differs. Keep direct helper calls usable and preserve timeout, quarantine, provider and offline semantics.
3. Use setup_readiness.repository_launcher_argv and format_command in the identified MCP setup recovery paths: WaveIndex._ensure_loaded's setup advice, _process_info_status and its three callers (server info, index health and build status), and upgrade dependency failure. Preserve the pending-install continuation, diagnostic codes, failure classification and operator-direction requirement. Windows commands use the selected checkout's wf.cmd; POSIX commands use its wf launcher.
4. Prove integration at the reported consumers. A helper-only test does not satisfy an AC. Run pre-fix failing controls and post-fix controls with direct assertions on directory bytes, committed WAL rows and independently expected target paths. Do not download models, run setup, change machine configuration or claim native Windows qualification.

## Scope

In scope: the named test helper, setup failure-message root plumbing, identified MCP diagnostics, focused tests and concise current documentation. Out of scope: live database policy, provider selection, new runtime snapshots, automatic setup, lifecycle authority, downstream edits, global command-text conversion, package/release work, commits or closure.

## Acceptance Criteria

- [x] AC-1: The actual DryRunIdleMaintenanceTests._snapshot handles absent sidecars, SHM only, empty WAL and populated WAL with/without SHM; it sees committed WAL rows, handles multiple SQLite files and preserves every original entry and byte. Non-SQLite comparisons remain effective. The unchanged caller fails these controls.
- [x] AC-2: Ordinary and prewarm-only setup failure controls started outside an explicitly selected repository produce model recovery guidance for that target, retaining model-bundle selectors and bounded failure behavior. Losing root propagation makes the consumer controls fail.
- [x] AC-3: The identified server/index/upgrade callers return correctly quoted repository-local setup commands for controlled POSIX and Windows cases, retain diagnostic and pending-install semantics, and perform no setup. Bare or wrong-root remedies fail direct assertions.

## Tasks

- [x] Establish failing consumer regressions for all three defects.
- [x] Apply the narrow caller repairs and update affected contracts and fixtures.
- [x] Verify consumer controls and discriminating bad variants; complete required independent delivery review and framework qualification.

## Agent Execution Graph

One implementation owner integrates the related test and diagnostic changes. Independent reviewers inspect the actual callers and before/after evidence. No new workflow or additional evaluation loop is introduced.

## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/tests/test_indexer.py`
- `.wavefoundry/framework/scripts/setup_index.py`
- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/wf_server/index_handlers.py`
- `.wavefoundry/framework/scripts/wf_server/upgrade_handlers.py`
- `.wavefoundry/framework/scripts/tests/test_setup_index.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`
- `.wavefoundry/framework/scripts/tests/test_process_info_callers.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools_retrieval.py`
- `.wavefoundry/framework/scripts/tests/test_startup_install.py`
- `.wavefoundry/framework/scripts/tests/test_upgrade_failure_surfacing.py`
- `docs/architecture/testing-architecture.md`
- `docs/specs/mcp-tool-surface.md`

CHANGELOG.md receives one concise correction. Reviewers read; the coordinator owns source edits. Framework seeds, generated hooks, model_bundle.py, runtime storage and prior closed waves are protected. Focused supporting tests may change only where these named callers require them; identify any extra path before editing it.

## Affected Architecture Docs

Clarify the test-only snapshot coverage in testing-architecture.md and root-aware recovery in mcp-tool-surface.md. No architecture ownership or runtime storage policy changes.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Repairs the exact downstream helper rather than a neighboring implementation. |
| AC-2 | required | Keeps the recovery command bound to the selected target. |
| AC-3 | required | Removes the identified unsafe command ambiguity without changing failure semantics. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-05 | Repair the named callers using isolated test copies and the existing launcher owner. | The original snapshot caller fails five sidecar controls; root omission and bare commands are directly observable. Consumer assertions discriminate missing integration. | A broader runtime read-policy change risks ignoring live WAL data; documentation-only repair leaves the behavior unchanged. |

## Risks

Private copies are valid only for quiescent test fixtures. Root plumbing can break test doubles or lose pending-install messaging; targeted consumer tests cover both. Windows coverage is controlled simulation, not native execution. The prior green suite missed the caller linkage, so helper success and checkbox completion are insufficient evidence.

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-05 | Implemented and independently reviewed. All three ACs and tasks complete; final frozen-tree canonical suite passes 12,374 tests/217 files/12 skips in 544.962s. Code, QA, architecture, docs-contract and delivery Council approve; model-oracle repair is terminal. No scope expansion or operator signoff. | Matching green receipt 5df7c7f3; delivery-evidence.json and typed events. Earlier all-worker-pass run was guard-refused after coordinator evidence-JSON edits; clean rerun used no acceptance shortcut. |
| 2026-11-05 | Corrected a new test oracle that assumed POSIX commands. Controlled Windows formatting exposed two assertion failures; the repaired consumer now covers both platforms and setup modes, with all 12 bad variants still detected. Prior qualification was intentionally interrupted and drained before this test-only edit. | Typed model-oracle-platform-format, cycle 1; independent code/QA verification and fresh qualification pending. |
| 2026-11-05 | Exact consumer baseline failed 14 assertions across five tests; repaired consumers and adjacent controls pass. Twelve in-memory bad variants are caught by assertions without errors/skips, including the original SQLite reader and each root edge. Two scheduling expectations were updated for the added root keyword and independently rerun. | delivery-evidence.json; full canonical qualification and independent delivery review pending. |
| 2026-11-05 | Readback: repair the exact snapshot caller and selected-root setup/MCP messages. AC-1–3 use original consumers and independent byte/path expectations. Implementer owns the named source/tests; preserve runtime SQLite and provider policy. Add failing tests before narrow repairs. | Current readiness receipt 0f7d72c7308d38425eae; all required lanes and Council approved; Implement wave activated. |
| 2026-11-05 | Planned from the read-only audit and exact-method temporary fixtures. No source edits made. | Source at 614ac8a2; five original-directory side effects; failure message defaults to working directory; bounded MCP caller census. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
