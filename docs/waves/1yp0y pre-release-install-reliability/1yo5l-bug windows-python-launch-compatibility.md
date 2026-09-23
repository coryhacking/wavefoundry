# Windows Python Prerequisite Discovery and Remediation

Change ID: `1yo5l-bug windows-python-launch-compatibility`
Change Status: `implementing`
Owner: Engineering
Status: active
Last verified: 2026-09-22
Wave: 1yp0y pre-release-install-reliability

## Rationale

The primary objective is proper, visible diagnosis whenever python3 cannot run correctly. Success means the operator understands the failed stage, the observed evidence and the next appropriate action, even when no local repair is possible. Remediation is secondary; implementing a new launcher or automatic repair is not required to achieve this objective.

Before the next release, detect and explain native-Windows environments where python.exe works but the required python3 command does not, then guide or perform an explicitly supported repair. MCP launches must continue to use python3. The operator corrected the initial fallback proposal: this is discovery, diagnosis and remediation of the prerequisite, not an alternate launch contract. A user reported friction during a 1.25.0+pqn7 fresh install dated 2026-09-21. Their report does not include the Phase 1 command log, so why the concern was not surfaced remains unproven. Current setup checks python3 only after dependency provisioning, while wf.cmd itself cannot reach Python diagnostics if that command is absent.

## Requirements

1. Preserve the canonical python3 requirement for MCP, generated hooks and CLI launchers, along with readiness rejection of unsupported launch commands. Discover other installed Python entry points only to diagnose and repair that prerequisite; python.exe or py must never silently become the steady-state MCP command.
2. Probe python3 before entering the setup reconciliation/mutation scope, dependency provisioning, model downloads or framework surface writes. The strict setup check must not accept the legacy WAVEFOUNDRY_SKIP_PYTHON_HEAL bypass as prerequisite success; non-strict compatibility callers may retain its existing skip behavior. If absent or unusable on Windows, discover available python.exe and, where useful, the Python launcher; execute bounded version/identity probes to distinguish a supported installed interpreter from an absent runtime, old version, Store-placeholder alias, failed probe or timeout. Mere executable presence is not proof of readiness.
3. Make diagnosis the primary deliverable. Report the attempted command and failed stage (command resolution, interpreter execution/version, or subsequent MCP bootstrap), the resolved path and interpreter identity when available, and the observed exit/error or timeout. Distinguish confirmed observations from suspected PATH, alias, permission/policy or host-environment causes; where evidence is insufficient, say the cause is undetermined and give the next diagnostic step rather than guessing or recommending reinstall by default. Ensure the failure is visible even when wf.cmd cannot start Python. Ship a bounded read-only .wavefoundry/framework/scripts/diagnose_python.ps1 entry invoked with powershell -NoProfile -File, without execution-policy bypass. Reference it from wf.cmd launch-failure guidance and first-install/new-workstation instructions; if policy blocks the script, provide manual discovery and IT handoff guidance. Keep it independent of Python, MCP, install-log completion and setup mutation. Cover the pre-Python entry/instruction path and Python-level setup checks; a diagnostic bootstrap may inspect an alternate interpreter but must not continue ordinary setup or MCP serving under an unapproved alternate command. State which command failed, which usable installation was discovered, the likely cause supported by evidence, and concrete platform-appropriate repair steps.
4. Guidance must offer a verified way to make python3 resolvable to the intended compatible interpreter, preserving existing installations and avoiding needless reinstall advice when Python is already suitable. Account for PATH, execution aliases and stale host environments; do not prescribe a shell-only alias or cmd shim as sufficient for a raw-spawn MCP host. Selected remediation is guidance-only, with no environment writes or new launcher implementation. Diagnose first, then direct the operator to an existing approved python3 executable/alias and permitted user PATH repair, or IT when policy blocks that route. Any repair mechanism must document its exact write scope, authorization, conflict handling, reversibility and host compatibility before implementation; do not silently reintroduce the previously rejected automatic environment-healing behavior.
5. After repair, verify python3 through the actual MCP launch shape, including server.py --dry-run and host restart/reconnect guidance. A successful python.exe probe, interactive-shell alias or current-process execution does not establish that a fresh host can launch python3. Keep setup unready until the canonical prerequisite succeeds.
6. Preserve shared tool-venv activation, interpreter compatibility checks, stderr-only MCP diagnostics, subprocess isolation, user-owned config fields, root anchoring and operator-owned permissions. Update canonical install/runtime guidance and local carriers with a per-sentence propagation table. Minimum and recommended versions remain distinct; do not claim every Windows installer supplies python3.
7. Support enterprise users without local administrator rights. Do not require elevation, Microsoft Store access, Developer Mode or changes to machine-wide PATH as the default remedy. Prefer an existing approved installation: discover an existing python3 executable/alias and a permitted user-level PATH repair first. Where only python.exe exists and no approved python3 entry is available, explain the command-name gap and provide the IT handoff. A user-local executable launcher remains a possible future repair, not a supported or required implementation in this wave. If policy prevents local repair, stop with a copy-ready IT handoff naming the discovered interpreter, failed probe, required python3 command and minimum version, host visibility/restart requirements and verification steps. Do not bypass enterprise restrictions or report the prerequisite satisfied while waiting for IT.
8. Apply diagnosis equally to a fresh install and an already-seeded repository newly checked out on another machine. Committed launch configuration and completed install-log rows are not proof of local runtime readiness. Provide a pre-MCP diagnostic path reachable without a working python3 or attached MCP; retain committed surfaces and existing index data while diagnosing the new machine. Do not prescribe reseeding or rebuilding solely because the local interpreter cannot launch.

## Scope

**Operator scope adjustment (2026-09-22):** external native Windows qualification is deferred until after the next release, per the operator’s final-review request. AC-3 and the native-execution portion of AC-6 are intentionally unmet in this wave. For AC-1/2/4/7, closure evaluates delivered source behavior, portable regression tests and source review; none is a claim of executed Windows behavior. The guidance, canonical python3 requirement, no-mutation boundary and truthful diagnostics remain mandatory now. See post-release-windows-validation.md for the retained test protocol and ownership.

In scope: early prerequisite discovery, pre-Python failure visibility, actionable diagnosis and a reviewed remediation path, post-repair verification, tests and a retained protocol for operator-deferred native-Windows qualification after the next release.

Intended source owners: diagnose_python.ps1 (new read-only Windows diagnostic), venv_bootstrap.py, setup_wavefoundry.py, setup_readiness.py and the wf.cmd producer in render_platform_surfaces.py where needed for diagnostics; associated tests. Renderer/MCP/hook launch output is a protected contract, not a fallback migration target. Intended guidance: seeds 011, 050 and 160, framework and repository READMEs, AGENTS.md, native-windows-support.md, project-overview.md, install/upgrade prompts and platform-mapping.md. Derive the final edit set from the prerequisite/diagnostic call path and classify other launch sites as intentionally unchanged.

Out of scope: alternate steady-state MCP commands, per-machine absolute paths in shared configs, project-venv workarounds, Python version-policy changes, dependency upgrades, automatic rebuilds, new MCP tools, general Python package management and release publication. Environment mutations and new launcher implementations are out of scope; guidance-only remediation preserves the existing no-environment-healing policy.

## Acceptance Criteria

- [x] AC-1: With supported python.exe present and python3 absent, Windows install entry points visibly identify the missing required command and usable existing interpreter, then stop before provisioning or surface mutation; no fallback is reported as setup success.
- [x] AC-2: Diagnostics distinguish absent, too-old, placeholder, failed and timed-out probes and provide a remedy appropriate to the observed condition; bounded tests observe the real preflight and pre-Python entry boundaries. Each failure report identifies the failed stage and available probe evidence, separates confirmed facts from hypotheses, and gives an actionable next diagnostic or repair step. Unknown causes remain explicit, and a later MCP bootstrap failure is not misreported as a missing python3 command.
- [~] AC-3: Following the documented or explicitly supported repair on native Windows makes a fresh host's python3 launch succeed, including MCP initialization and a representative hook in a repository path with spaces. Evidence identifies the interpreter before/after and any restart required. *2026-09-22 operator directed external native Windows testing after the next release. Native execution and repair remain unverified; guidance implemented now. Follow post-release-windows-validation.md; no native pass claimed.*
- [x] AC-4: Generated MCP configurations continue to require python3; working Windows and POSIX installs retain their launch shape, shared bootstrap, root anchoring and user-owned fields across rendering/upgrade. Any implemented repair obeys its reviewed scope and refuses conflicting/unsafe cases without partial unreported changes.
- [x] AC-5: Changed diagnostics and guidance have an explicit propagation table and consistently describe discovery, remediation and canonical python3 verification rather than alternate-command fallback.
- [x] AC-7: An already-seeded checkout with correct committed MCP configuration but missing or unusable local python3 receives actionable diagnosis before MCP is available; tests prove completed install state does not suppress the check and diagnosis does not reseed, rebuild or rewrite committed configuration.
- [~] AC-6: Enterprise remediation guidance supports a standard user without assuming Store access, Developer Mode or elevation. Native Windows evidence demonstrates the selected permitted user-level remedy; a policy-blocked case produces an actionable IT handoff and remains unready without unauthorized environment changes. Any promoted user-local launcher has direct-process and fresh-host evidence; an unverified candidate is not presented as supported. *2026-09-22 operator directed external native Windows testing after the next release. Native execution and repair remain unverified; guidance implemented now. Follow post-release-windows-validation.md; no native pass claimed.*

## Tasks

- [x] Trace prerequisite checks and pre-Python entry failures; retain the existing no-environment-healing policy with guidance-only remediation. Evidence: readiness-review.md and ensure_python_resolves/_run_setup baseline probes.
- [x] Cover a newly checked-out seeded repository and document its pre-MCP diagnostic entry point without reinstall/rebuild side effects.
- [x] Implement early discovery and visible diagnosis while preserving canonical launch commands and readiness requirements.
- [~] Deliver and verify the selected remediation path and post-repair host check; design meaningful negative controls during implementation. Deferred by operator on 2026-09-22 to external testing after the next release; see post-release-windows-validation.md. Implementation and portable negative controls are complete, native verification is unperformed.
- [~] Qualify the standard-user remediation path and policy-blocked IT handoff; use the IT handoff when approved executable/alias discovery is insufficient; record the choice not to ship a new launcher. Deferred by operator on 2026-09-22 to external testing after the next release; see post-release-windows-validation.md. Implementation and portable negative controls are complete, native verification is unperformed.
- [x] Reconcile canonical and local guidance, including restart behavior, through the propagation table.
- [x] Obtain fresh code, QA, architecture, security and docs-contract review; run required framework/docs gates. Native remediation evidence is separately deferred under AC-3/AC-6.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Prerequisite diagnosis and remediation | implementer | readiness | Single writer across prerequisite owners |
| Documentation reconciliation | implementer | selected remediation path | Same writer prevents renderer/guidance races |
| Independent verification | reviewer lanes | implementation | Read-only source review; coordinator records evidence |

## Serialization Points

- `.wavefoundry/framework/scripts/venv_bootstrap.py`
- `.wavefoundry/framework/scripts/setup_wavefoundry.py`
- `.wavefoundry/framework/scripts/setup_readiness.py`
- `.wavefoundry/framework/scripts/render_platform_surfaces.py`
- `.wavefoundry/framework/scripts/tests/`
- `.wavefoundry/framework/seeds/`
- `docs/prompts/`
- `docs/references/native-windows-support.md`

## Affected Architecture Docs

Update current-state.md and data-and-control-flow.md for prerequisite/diagnostic flow, testing-architecture.md for native remediation qualification, and platform-mapping.md only where recovery guidance needs correction. Preserve the identical python3 command contract. If a bounded repair is selected, explicitly reconcile the prior no-environment-healing decision for that named scope.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Reported Windows failure |
| AC-2 | required | Primary objective: accurate, actionable diagnosis even when repair is unavailable |
| AC-3 | required | Canonical launch and repair boundaries |
| AC-4 | required | Preserve launch contracts and repair safety |
| AC-5 | required | Installers must act on the correct contract |
| AC-6 | required | Enterprise users may lack local admin rights and installation permissions |
| AC-7 | required | Runtime prerequisites are machine-local even when the repository is already seeded |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-22 | Defer native Windows qualification until after the next release | Operator explicitly requested final review now and external testers after release; do not represent skipped or simulated tests as native proof | Holding closure/release for a currently unavailable Windows host is no longer required |
| 2026-09-22 | Select guidance-only remediation; no environment repair implementation | Latest operator priority is diagnosis; existing policy already forbids automatic healing | A new native launcher adds maintenance and enterprise-policy qualification without improving diagnosis |
| 2026-09-22 | Prioritize proper diagnosis over repair mechanisms | Explicit operator priority: explain inability to run python3 correctly, including when repair cannot be performed | A generic install warning or speculative cause is insufficient; new launcher implementation remains optional |
| 2026-09-22 | Preserve mandatory python3; diagnose and repair its availability | Explicit operator correction: discovery and remediation, not fallback | Alternate-command MCP fallback rejected; warning without discovery cannot distinguish missing runtime from a command/alias problem |
| 2026-09-22 | Select early diagnosis with a verified remediation path | Removes hidden prerequisite friction without changing launch semantics | Automatic global PATH/shim changes have prior portability and ownership risks; guidance-only versus bounded explicit repair remains a readiness decision |
| 2026-09-22 | Require standard-user remediation and a policy-respecting IT handoff | Operator identified enterprise clients without local administrator rights | Admin/Store/Developer Mode prerequisites rejected as defaults; user-local executable launcher remains a candidate requiring qualification, not an automatic repair commitment |

## Risks

| Risk | Mitigation |
| --- | --- |
| wf.cmd fails before Python diagnostics run | Test and document the pre-Python entry path |
| Interactive alias works but MCP raw spawn fails | Verify python3 from the actual fresh-host launch shape |
| Repair overwrites existing aliases or changes interpreter unexpectedly | Explicit repair scope/conflict handling if selected; report interpreter identity |
| Simulated tests hide Windows process/alias behavior | External native-Windows testing after the next release per operator direction; retain unverified status until results exist |
| Enterprise application control blocks user-local executables or PATH changes | Respect policy, preserve unready state and provide a precise IT handoff; do not evade controls |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-22 | Readback: diagnose failed python3 accurately before setup mutation and without MCP on seeded new workstations; retain canonical launches and guidance-only remediation. Before: timeout looks like old Python; after: timed-out probe and next step, no setup writes. Owners: venv_bootstrap, setup_wavefoundry, diagnose_python.ps1, launcher producer/tests. | Current readiness approvals |
| 2026-09-22 | Thought: parallelize isolated validator implementation and authored guidance while coordinator owns Windows diagnostics; integrate before tests and delivery review | Disjoint file ownership |
| 2026-09-22 | Included already-seeded fresh checkouts with unavailable local python3 and no attached MCP | Operator steering; Requirement 8 and AC-7 |
| 2026-09-22 | Made diagnosis the primary objective and strengthened diagnostic evidence and uncertainty requirements | Operator clarification; Rationale, Requirement 3 and AC-2 |
| 2026-09-22 | Added non-admin enterprise remediation, conditional launcher qualification and policy-blocked IT handoff | Operator approved final plan adjustment; Requirement 7 and AC-6 |
| 2026-09-22 | Operator corrected scope: preserve python3, discover/diagnose missing availability and guide or perform reviewed remediation | Current conversation; replaces the initial fallback proposal |
| 2026-09-22 | Planned from operator field report and current-source investigation for next release | venv_bootstrap.ensure_python_resolves; setup_wavefoundry step 2b; setup_readiness._valid_surface_entry; render_bin_launchers |
| 2026-09-22 | Implemented strict pre-mutation diagnosis and pre-Python script; focused checks pass. Strict-skip mutant killed by test_strict_check_cannot_be_skipped; timeout-loss mutant killed by new byte-output regression. Native qualification remains open. | implementation-evidence.md; guidance-propagation.md |

## Session Handoff

Implementation underway following typed readiness approval and successful Prepare. Coordinator owns prerequisite diagnostics; isolated validator and guidance changes are integrated. Native Windows qualification is unproven and operator-deferred to external testing after the next release. Final review and close-readiness validation are authorized; no commit requested.
