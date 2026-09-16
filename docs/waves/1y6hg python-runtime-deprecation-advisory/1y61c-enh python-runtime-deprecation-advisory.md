# Warn once for deprecated Python runtimes

Change ID: `1y61c-enh python-runtime-deprecation-advisory`
Change Status: `complete`
Owner: Engineering
Status: active
Last verified: 2026-09-16
Wave: 1y6hg python-runtime-deprecation-advisory

## Rationale

Recommend Python 3.13 or newer while allowing existing Python 3.11 and 3.12 installations to continue running. Developers and agents should receive one actionable advisory at the command or server boundary, without repeated messages from implementation modules. The operator explicitly places CLI warning ownership in the wf command, not submodules. Preserve the earlier MCP startup and structured health visibility requirements: MCP starts directly through server.py, bypassing wf. This is a planned enhancement, separate from the open test-portability fix.

## Requirements

1. Python 3.11 and 3.12 are deprecated but allowed. Recommend Python 3.13 or newer; retain the existing minimum of 3.11 and existing dependency/runtime compatibility checks. A recommendation does not certify every future Python version. Set no removal date or new hard minimum in this change.
2. The wf command owns the human-readable CLI warning in wf_cli.main. Emit once to stderr per top-level invocation on a deprecated runtime, including setup, setup --check and help. Do not print from dispatched submodules, imports, venv_bootstrap, index builders, or setup assessors. Ordinary child-module execution must not repeat it. Repeated independent wf invocations each warn; no persistent suppression file or global warning filter.
3. Actual direct MCP serving startup (not --dry-run verification or help) owns a separate once-per-process stderr warning in server.py's executable entry. Importing the runner, hot reloading implementation, handling tools, and background polling must not re-emit it. Never print advisory text to JSON-RPC stdout. Compose with existing startup diagnostics without duplicating the deprecation message when other setup problems are present. The existing setup child server.py --dry-run must not print it; standalone dry-run is likewise silent for this notice. No need to route MCP through wf or modify every launcher.
4. Determine the runtime from the executing interpreter's version, not an arbitrary python on PATH or package metadata. Include its version and useful interpreter provenance. Bootstrap currently changes sys.path in-process, not the executing interpreter; do not infer a runtime version from executable metadata or PATH. Retain defensive tests for altered executable metadata. Preserve existing refusal for incompatible tool environments.
5. Shared version policy/formatting lives in bootstrap-safe runtime_advisory.py as small side-effect-free functions; shared modules return data only. Extend existing setup-readiness/index-health advisory data with a stable code, severity, actual version, recommended minimum, and guidance. Deprecation alone must not change ready to action_required/indeterminate, set startup_blocked, trigger automatic setup/rebuild, or affect command exit status. If another issue is present, preserve its existing status, actions and exit code.
6. Warning example: "Python 3.11 is deprecated for Wavefoundry. Python 3.13 or newer is recommended. Execution will continue." Guidance must distinguish installing/selecting newer Python from provisioning the tool environment. Document the verified ordinary setup procedure under the selected newer interpreter; do not promise that rerunning wf under the old interpreter upgrades Python, make the advisory delete shared environments automatically, or add a new interpreter-management command.
7. Update operator-facing support guidance together: 3.13+ recommended, 3.11/3.12 deprecated but accepted, below3.11 unsupported. Explain that the notice is advisory, repeat frequency, how agents find it when MCP stderr is hidden, and the tested environment-transition procedure. Do not introduce an unagreed support-removal schedule or silently replace the release test policy.

## Scope

In scope: entry-point warning ownership, pure shared policy/data, existing health/readiness advisory integration, focused regression tests and operator documentation.
Out of scope: raising the enforced Python floor; auto-installing Python; new advisory-triggered deletion/recreation of shared environments; changing MCP registration; printing warnings from child modules; changing command results or exit semantics; a new release test matrix; full interpreter/environment migration tooling; implementation in the current planning request.

## Acceptance Criteria

- [x] AC-1: Under simulated3.11/3.12, each top-level wf invocation emits exactly one deprecation warning on stderr, including dispatched multi-phase setup and read-only check; stdout payloads and exit codes retain their existing behavior. Representative3.13+ invocations emit no deprecation warning.
- [x] AC-2: Direct MCP startup emits the warning once on a deprecated runtime without contaminating JSON-RPC stdout; repeated imports, implementation reloads, tool calls and monitor checks do not emit another warning. Supported newer runtime startup emits none.
- [x] AC-3: Structured setup/index-health advisory reports the actual runtime and recommended minimum; deprecation-only ready state remains ready with no setup/rebuild action, while independent dependency, ownership or runtime failures retain their own recovery and exit behavior.
- [x] AC-4: Tests distinguish the executing runtime from PATH alternatives and bootstrap metadata, retain existing below-minimum/incompatible-runtime refusals, and prove child modules do not print deprecation warnings.
- [x] AC-5: Updated documentation states the deprecated-but-allowed policy and a tested environment-selection/setup procedure without claiming setup installs Python, concealing ordinary setup's existing replacement of incompatible shared environments, or announcing a removal release.

## Tasks

- [x] Review current entry/activation paths and choose the smallest pure policy/data seam; confirm advisory-field compatibility before edits.
- [x] Implement wf-owned and direct-MCP-entry-owned warning emission, keeping submodules silent.
- [x] Integrate structured advisory data without readiness, action or exit-code regressions.
- [x] Add focused CLI/MCP/bootstrap-advisory controls, including repeated dispatch and mixed failure cases.
- [x] Verify and document setup under a selected newer interpreter using isolated environments; reconcile relevant install/upgrade/support guidance.
- [x] Run scoped tests and independent code/QA/architecture/docs review, recording actual interpreter/platform limits.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Runtime policy and entry points | implementer | readiness | One writer owns shared advice and deduplication |
| Documentation and environment procedure | coordinator | confirmed entry behavior | Keep to existing setup path |
| Review | independent code/QA, architecture and docs-contract reviewers | frozen implementation | Verify streams, counts, runtime identity and nonblocking behavior |

## Serialization Points

- `.wavefoundry/framework/scripts/runtime_advisory.py`
- `.wavefoundry/framework/scripts/tests/test_runtime_advisory.py`
- `.wavefoundry/framework/scripts/tests/test_venv_bootstrap.py`
- `.wavefoundry/framework/scripts/wf_cli.py`
- `.wavefoundry/framework/scripts/server.py`
- `.wavefoundry/framework/scripts/setup_readiness.py`
- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_wf_cli.py`
- `.wavefoundry/framework/scripts/tests/test_setup_readiness.py`
- `.wavefoundry/framework/scripts/tests/test_setup_readiness_integration.py`
- `.wavefoundry/framework/scripts/tests/test_cli_stdio.py`
- `.wavefoundry/framework/README.md`
- `.wavefoundry/framework/seeds/011-install-wavefoundry-phase-1.prompt.md`
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`
- `docs/prompts/install-wavefoundry.prompt.md`
- `docs/prompts/upgrade-wavefoundry.prompt.md`
- `docs/references/native-windows-support.md`
- `docs/references/project-overview.md`
- `docs/contributing/build-and-verification.md`
- `docs/specs/mcp-tool-surface.md`
- `docs/architecture/data-and-control-flow.md`

Existing venv_bootstrap is a read-only dependency for policy placement and interpreter-identity review, not a warning emitter. The pure helper is declared below; it never prints, imports models, probes PATH, or mutates environment state. Coordinator owns seed/local guidance reconciliation; reviewers are read-only. Framework/seed gates apply during implementation, not this docs-only plan.

## Affected Architecture Docs

Update docs/architecture/data-and-control-flow.md for entry-owned notices versus shared advisory data; docs/specs/mcp-tool-surface.md for observable health advisory semantics. No storage, indexing or publication architecture change.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Operator requested one warning at wf, with no subordinate duplicates |
| AC-2 | required | MCP bypasses wf and must preserve transport correctness |
| AC-3 | required | Warning must not cause false setup or health failures |
| AC-4 | required | Correct runtime identity and retained safety refusals prevent misleading advice |
| AC-5 | required | Users need actionable migration guidance while execution remains permitted |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-16 | Planned only. Current wf_cli.main dispatches setup without upfront activation; other commands activate in-process. server.py executable entry performs startup assessment before activation and prints existing non-ready assessment to stderr. | MCP reads of wf_cli.main and server.py executable startup / _assess_startup |

### Implementation readback — 2026-09-16

Readback / Thought: after successful Prepare and activation, add pure runtime advisory data, wire exactly one stderr notice in wf and actual MCP serving entry, then verify nested dry-run silence and unchanged readiness. Runtime implementer owns helper/entry/assessment/tests; coordinator owns canonical/local docs. No minimum-floor bump, new environment mutation or submodule printing. Ordered work: pure policy and entry wiring; structured health; focused tests/mutations; doc reconciliation and independent rechecks; full suite and docs gate. Memory briefing reviewed thin-runner ownership/reload advisories; no new MCP tool or schema parameter is introduced.

Observe: actual existing _bootstrap_venv recreated a disposable Python3.11 venv under3.13, and PATHpython3 then agreed (session38061). No package/model downloads or shared-operator environment changes. This proves local bootstrap transition only, not native Windows/Linux/full model installation. Gapfill: coordinator uses bounded shell reads for documentation-only reconciliation after MCP code-seam grounding.

Implementation progress: pure runtime helper, CLI/MCP emission and additive readiness data are present. Focused helper/entry tests pass on actual Python3.11 and3.13; readiness/integration47 tests pass on3.13. Canonical README, install/upgrade seeds and local guidance now document the transition. Full delivery review and final suite remain pending.

Message wording refinement: use “This advisory does not block execution; existing runtime checks still apply” for the illustrative warning, so unrelated failures are not described as successful execution. The example is illustrative; runtime requirements and scope remain as readied.

Delivery evidence so far: runtime6, readiness/integration47, CLI51 and bootstrap33 tests pass under actual Python3.11 and3.13 (one existing bootstrap skip on3.11). Six mutations rejected on each runtime: missing policy, newer-runtime warning, duplicate CLI warning, MCP dry-run warning, missing structured field, and advice changing readiness. MCP tests execute real executable entry/main/stdio with heavyweight construction stubbed, plus import/façade reload and repeated assessment silence; full implementation reload silence is supported by entry ownership and existing reload coverage. Source/docs frozen for independent review; full suite running.

Current handoff (supersedes the historical planning-request scope qualifier and Session Handoff below): operator subsequently authorized Prepare, review and implementation; these stages are complete with independent delivery approvals. Final full-suite verification remains running. No closure or commit authorized. The readied requirement/scope text is retained as its historical policy receipt input; no actual delivery requirement was narrowed.

Validation update: full docs gate passed with no errors/warnings. First full9104-test suite failed only dashboard process/socket tests under the sandbox; unchanged dashboard207tests pass in the host-access rerun. Remaining full-suite completion pending. Framework/seed gates closed;21-file review fingerprint still matches.

Final validation: both full runs executed9104tests/95files with21skips. Sandbox run failed only dashboard process/socket tests; host-access rerun passed dashboard207tests but hit unchanged TechDocs timing assertion184ms versus150ms. Independent TechDocs86tests passed in8.926s with correctCLTGit PATH; an initial isolated retry used systemGit and hit the pre-existing Xcode license block. No test threshold/code changed. Full docs gate passed, independent reviews approved, all AC/tasks complete. No fresh whole-suite green receipt is claimed; obtain one before closure. Logs: /private/tmp/wf-1y6hg-full-tests.log, /private/tmp/wf-1y6hg-full-tests-host.log, /private/tmp/wf-1y6hg-techdocs-recheck-fixed-path.log.

Closure update: full suite now green,9104tests/95files,12skips,655.088s, two workers with host process/socket access. Fresh receipt replaces prior stale evidence. Same tests and thresholds; no framework changes after review. Operator authorized closure.

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-16 | Emit notices at wf and the separate direct MCP entry only | One owner per user-visible invocation; preserves operator's prohibition on submodule warnings | Warn in every module/bootstrap: repeated noise and import side effects. CLI-only notice: invisible to directly launched MCP hosts. Raise minimum immediately: blocks existing users contrary to request |
| 2026-09-16 | Keep shared advisory classification pure and nonblocking | Agent visibility without turning deprecation into setup work | Add a readiness failure: creates unnecessary repair loops. Persist warning suppression: extra local state for a simple per-invocation notice |

## Risks

| Risk | Mitigation |
| --- | --- |
| MCP logs are hidden by some hosts | Existing health/check response carries structured advisory |
| Runtime version inferred incorrectly from environment metadata | Use executing version and capture accurate provenance at boundary |
| Duplicate notice through existing startup formatting | Count exact deprecation occurrences in combined failure tests |
| Python upgrade instructions break a shared tool environment | Test isolated environment transition and preserve existing mismatch safeguards; no auto-removal |

## Readiness refinements

Source-grounded primer: setup_wavefoundry._run_mcp_server_dry_run inherits stderr, so MCP dry-run must not emit a second warning. setup_index._bootstrap_venv already replaces a mismatched environment; this wave does not change that behavior. Document stopping all consumers of the shared environment before a deliberate ordinary setup under newer Python, or using a separately selected WAVEFOUNDRY_TOOL_VENV for isolation. Select Python3.13+ as the PATH python3 used both by setup and the restarted MCP host: setup verification explicitly launches PATH python3, so merely invoking a version-specific executable is insufficient. Propagate an isolated WAVEFOUNDRY_TOOL_VENV to the host when chosen. Test the transition on disposable environments only. Structured advisory lives outside reasons/actions/status; format_text remains a readiness summary and does not reprint it.

## Session Handoff

Admitted to wave1y6hg; awaiting readiness and implementation. Test-only wave1y4j8 is paused. Operator authorized Prepare, review and implementation, not closure, commit or release.
