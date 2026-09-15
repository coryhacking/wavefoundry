# Host-neutral wave orchestration

Change ID: `1y0zw-enh host-neutral-wave-orchestration`
Change Status: `completed`
Owner: Engineering
Status: planned
Last verified: 2026-09-14
Wave: 1y3hb host-neutral-wave-orchestration

## Rationale

Teams may choose Codex for one wave, Claude Code for another, or implement in one agent system and review in another. They need the same clear delegation, verification and handoff rules each time. The goal is effective coordinator-led work without binding the framework to a vendor, model, sidebar layout or native team feature.

Brief: extend the existing wave workflow for operators and coding agents. Keep one coordinator responsible for delivery, assign bounded work when useful, and preserve independent review. Reuse the existing change document, wave record and evidence; do not build a system for simultaneously orchestrating multiple hosts. The 1xxcb/1xtnr closure pilot supplies an example of scoped verification and model selection, not proof of implementation speed or cost savings.

## Requirements

1. **Portable roles.** Define coordinator, worker and reviewer responsibilities using role names. No provider, product, model or reasoning level is mandatory, and the repository does not select one agent system for every wave. The same policy applies to Codex, Claude Code, Antigravity, Copilot and other hosts through the shared project instructions.
2. **Useful delegation.** The coordinator decomposes admitted scope into independent work with explicit dependencies and file ownership, delegates only when tools and capacity support it, and continues independent coordination work while workers run. Give each worker the relevant ACs, allowed/forbidden paths, interface constraints, MCP-first retrieval instructions, verification expectations and a bounded deliverable. Keep shared-file edits serialized. Reuse a worker for follow-up within its assignment when its context remains useful; rebrief or replace it when stale. Do not create agents merely to fill slots or copy the whole conversation by default.
3. **Best model per task across the lifecycle.** From Prepare and planning review through implementation, verification, delivery review and Close, choose the best available model and reasoning effort for each specific task, using capable models efficiently. Respect operator choices. Judge fit from task ambiguity, reasoning depth, domain expertise, failure consequences, context needs and observed results; do not equate role with a fixed model tier. Use the most capable available model when its judgment is needed, and a lighter model only when it can meet the same quality bar for the bounded task. Consider total effort including retries, rework and coordinator integration, not just per-call cost; escalate or reassign when evidence warrants it. Do not invent a model switch, thread, messaging feature or quota. If delegation is unavailable or inappropriate, execute implementation tasks sequentially and state that fact. Required independent review still needs an independent context; relabeling the implementer does not satisfy it.
4. **Coordinator acceptance.** Workers return changed paths, AC coverage, commands and observed results, remaining risks and blockers. The coordinator verifies the actual changes, resolves integration issues, and keeps the existing Agent Execution Graph and Progress Log current. Worker completion is not wave completion. Preserve existing stage gates, review independence, single-writer rules, and operator authority over closure, commits and releases.
5. **Optional review handoff.** An operator may implement with one system and review with another. Record a concise handoff in the existing wave/change documents: reviewed revision or tree fingerprint, scope and ACs, changed paths, commands/results, unresolved findings and next action. The receiving reviewer checks the current tree and evidence independently; a different vendor alone does not establish independence. No automatic discovery, cross-host messaging, host/session registry or concurrent multi-host scheduler is required.
6. **One policy, normal delivery.** Seed 180 owns the orchestration policy, including task-fit model allocation throughout Prepare-to-Close; bootstrap, upgrade and review guidance point to it and carry only phase-specific obligations. Reconcile the existing project prompts through the supported install/upgrade procedure, preserving customized content. Existing host entry files and skills remain thin pointers; do not copy a separate orchestration policy into every vendor configuration. Record available elapsed-time/usage and rework observations in existing evidence when evaluating the approach, with unavailable measurements stated; do not promise savings from the closure-only pilot.

## Scope

**In scope:** canonical seed guidance, its existing project-local implementation/review/concurrency prompts, a compact review-handoff contract, and focused propagation/behavioral checks. Clarify the existing workflow rather than add a new command.

**Intended edits:** seed 050 and its AGENTS/coordinator output for the same inherited-MCP compatibility clause; seed 180 for the policy; seed 100 for bootstrap propagation; seed 160 for existing customized-surface upgrade reconciliation; the existing prepare, implementation, upgrade, review, pause, close and concurrency project prompts where they consume that policy; `docs/contributing/agent-team-workflow.md` and `docs/agents/platform-mapping.md` for concise cross-host pointers. Update the existing missing-only prepare/implementation/review/close lifecycle templates so new installations receive the same contract. Inspect the existing renderer and carrier tests to use their supported paths; any runtime/schema change discovered to be necessary requires a scope review before implementation.

**Out of scope:** cross-host orchestration infrastructure; a provider/model registry; new MCP tools, plugins or agent-control adapters; mandatory sidebar threads, worktrees or extra Markdown files; automatic model purchasing/configuration; weakening evidence or approval gates; benchmarking claims not measured by this work.

### Propagation and compatibility checks

| Source | Destination / verification |
| --- | --- |
| Seed 050 and its AGENTS/coordinator output | Qualify the same inherited-MCP assumption; preserve thin entry guidance and existing agent editing reconciliation. |
| Seed 180 | Canonical orchestration policy; replace universal child-MCP inheritance claims with observed-capability routing while retaining MCP-first when attached. |
| Seed 100 + missing-only prepare/implementation/review/close templates | Fresh project prompts receive the contract; renderer preserves an existing customized prompt. |
| Seed 160 | Agent editing pass merges required clauses into customized prepare/implementation/review/pause/close/concurrency surfaces; rerender alone is not claimed to perform that merge. |
| Existing project prompts and team/platform guidance | Phase-specific pointers to canonical policy, checked after reconciliation. |
| Existing host entry/skill renderers | Codex, Claude Code, Antigravity and Copilot entry-path checks; no native-host execution claim. |

## Acceptance Criteria

- [x] AC-1: Across Prepare, implementation, review and Close, the canonical policy and reconciled project prompts choose model/effort by task fit and total verified effort, and describe the same coordinator/worker/reviewer responsibilities without requiring a named host, model, reasoning level or UI feature.
- [x] AC-2: A bounded delegation walkthrough produces explicit ACs, dependencies, owned/forbidden paths and verification results in the existing change document; overlapping writes are serialized and the coordinator checks the combined result before accepting it.
- [x] AC-3: Walkthroughs for ambiguous readiness, bounded implementation, difficult review and routine closure choose an executable model/effort allocation. Cases with available delegation, unavailable delegation and unavailable model selection each choose an executable path; sequential fallback does not claim independent review or fabricate unavailable host capabilities.
- [x] AC-4: A review handoff from one agent system to another is understandable from the existing wave documents and current tree alone; it identifies scope, fingerprint, evidence, unresolved findings and next action without a host registry or shared chat transcript. Same-system fresh-context review also remains valid under existing policy.
- [x] AC-5: Fresh-install and customized-upgrade checks show the policy reaches the existing Prepare-through-Close surfaces, preserves project-authored content and keeps host-specific wrappers as pointers. Checks cover entry paths for Codex, Claude Code, Antigravity and Copilot without claiming native execution on hosts not actually exercised.

## Tasks

- [x] Confirm the canonical owner and existing install/upgrade carriers; remove duplicate policy text in the touched scope.
- [x] Extend seed 180 with portable delegation, model-choice principles, worker reports and coordinator acceptance.
- [x] Reconcile bootstrap/upgrade instructions, missing-only lifecycle templates and existing project prompts; preserve customized content.
- [x] Clarify sequential fallback and optional independent review handoff without changing review gates.
- [x] Run the AC walkthroughs and focused propagation checks; record observed evidence and capability limits in the wave's existing report.
- [x] Run required documentation validation and applicable framework checks; complete readiness and delivery review through the existing lifecycle.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Canonical policy and propagation | implementer / technical-writer | Prepare wave | One writer for seeds and shared prompt surfaces |
| Capability and handoff walkthroughs | qa-reviewer | Draft policy | Read-only independent checks; no fabricated hosts |
| Contract and duplication review | docs-contract-reviewer | Policy and propagation evidence | Check independence, vendor neutrality and preservation |

## Serialization Points

One implementer owns seed and template edits; one technical writer owns project prompt reconciliation, serialized after canonical edits. Reviewers are read-only. Coordinator alone updates lifecycle state. Host configs, shared manifests and rendered entry files are protected and may only change through their existing generators if required by the approved scope.

- `.wavefoundry/framework/seeds/050-agent-entry-surface-bootstrap.prompt.md`
- `AGENTS.md`
- `docs/agents/wave-coordinator.md`
- `.wavefoundry/framework/seeds/180-implement-feature.prompt.md`
- `.wavefoundry/framework/seeds/100-project-prompt-surface-bootstrap.prompt.md`
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`
- `.wavefoundry/framework/install/lifecycle-prompts/`
- `.wavefoundry/framework/scripts/tests/test_render_agent_surfaces.py`
- `.wavefoundry/framework/scripts/tests/test_render_platform_surfaces.py`
- `docs/prompts/prepare-wave.prompt.md`
- `docs/prompts/close-wave.prompt.md`
- `docs/prompts/implement-feature.prompt.md`
- `docs/prompts/upgrade-wavefoundry.prompt.md`
- `docs/prompts/implement-wave.prompt.md`
- `docs/prompts/review-wave.prompt.md`
- `docs/prompts/pause-wave.prompt.md`
- `docs/prompts/agent-routing-concurrency.prompt.md`
- `docs/contributing/agent-team-workflow.md`
- `docs/agents/platform-mapping.md`

## Affected Architecture Docs

`N/A` for runtime architecture: no persistence, transport or execution engine changes. The operating contract changes in the existing agent-team workflow and platform-mapping documentation named above. No ADR is needed for guidance alone.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The operator chooses the system per wave |
| AC-2 | required | Useful delegation needs bounded ownership and integration |
| AC-3 | required | Host differences must not make the workflow fictitious |
| AC-4 | required | Review can move to another system without losing context or independence |
| AC-5 | required | Guidance must reach new and existing projects without divergent vendor copies |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-14 | Extend the existing host-neutral workflow with capability-aware delegation and optional review handoff. | Fits choosing a different agent system for each wave and reuses existing authority/evidence. | Vendor-specific playbooks drift and encode transient models; a cross-host scheduler solves a different problem and adds unnecessary infrastructure. |
| 2026-09-14 | Keep model names and reasoning levels outside the mandatory policy. | Operator preference and host capabilities vary; model choice is an execution decision. | Making the Astra/Luna pilot the default excludes other systems and mistakes a closure check for a measured implementation benchmark. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Sequential fallback becomes self-approval | Explicitly retain fresh independent review requirements |
| Guidance is copied into many host files and drifts | One canonical policy; phase-specific pointers and normal reconciliation |
| Parallelism increases conflicts or cost | Bounded ownership, dependency checks, actual capacity and measured observations |
| A customized project prompt misses the new guidance | Exercise the supported upgrade reconciliation and preserve user content |

## Progress Log

**2026-09-15 bounded amendment:** Operator requested two concrete refinements within Requirements 2–3 (useful delegation and total effort): consider briefing/waiting/integration overhead before delegation, and require an early task-sized useful output with prompt diagnosis/rebrief/model change/reclaim on stalled progress. No scope, AC, ownership, runtime or review-policy boundary changes; existing phase pointers already reach the canonical section. Coordinator writes the two files directly; independent reviewers verify the amendment. Six new obligations extend the existing named carrier test and its deletion controls; prior completion/receipt/fingerprint below are historical until refreshed. No extra workflow, timer service, artifact or approval gate.

**Amendment verification:** 8 focused tests passed, zero skips; the existing semantic mutation loop now detects 46 controls including six added delegation obligations. Fresh code reviewer independently deleted each new clause at the seed read boundary: six intended assertion failures, no errors/skips. Fresh QA instrumented the six new mutation cases and verified small-coupled-work/local ownership plus stalled-worker recovery without self-review or overlapping writes. Fresh docs-contract reviewer tested four reversed policies (delegate when slots exist, wait for final output, wait indefinitely, sequential self-review): all detected. Successful progress continues; legitimate long computation is assessed contextually, not cancelled by a fixed deadline. All three amendment delivery approvals recorded; no source blockers or policy-boundary changes. Refreshed full suite passed: 9,013 tests, 91 files, 12 skips, 643.524 seconds; receipt independently matches current framework tree. Documentation validation passed. Edit gates closed. Amendment complete, no closure or commit authorized. Seed SHA256 `f50b4725232fd9adfea727819835444c289aa40c075975c9b504a2e33941dccd`; test SHA256 `5e2b1d8bc560784ad8e5832db29966a7d7878ee56e47ffa07f472f413b4a8770`; both unchanged during independent review. This supersedes earlier fingerprints for those two files only; other reviewed files unchanged. Text/fixture checks do not establish agent adherence, elapsed-time savings or native-host execution.


| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-14 | Deviation: guidance lane returned no edits; coordinator took over that serialized write assignment to unblock the test writer. Canonical policy and phase pointers now written; scoped inheritance claims replaced. | Seed180 Host-neutral orchestration; seeds050/100/160; existing templates/project prompts. |
| 2026-09-14 | Readback: choose model/effort by task from Prepare through Close; replace assumed worker tools with observed capability. Bounded guidance writer and separate test writer; coordinator integrates, fresh reviewers judge. No runtime/schema/host registry. | AC1–5; user implementation instruction; successful Prepare and activation. |
| 2026-09-14 | Thought: canonical policy and phase pointers first; focused carrier/walkthrough tests next; then integration, full validation and independent delivery lanes. Gapfill: exact prose reads and mechanical doc edits use shell; code scaffold investigated via MCP outline/read. | Guidance owner envelope_verification; test owner readiness_qa; no overlapping owned files. |
| 2026-09-14 | Brief confirmed: use the same instructions whichever agent system runs a wave; optionally implement in one and review in another. Cross-host orchestration explicitly excluded. Diverge/critique/select recorded above. Planning only; not admitted or readied. | Operator clarification; seed100 bootstrap rules, seed180 implementation contract, existing agent-routing-concurrency and agent-team-workflow docs. |


Operator clarification (2026-09-14): optimize model fit and total effort for every lifecycle task, Prepare through Close; no fixed cheap-worker or premium-coordinator split. Apply the same canonical policy through concise phase pointers.

## Session Handoff

Implementation and delivery review complete in wave 1y3hb; all five ACs and six tasks verified. Typed code/QA/docs-contract approvals recorded; memory proposal returned zero candidates. Full suite 9,013 tests passed (21 skips), docs-lint passed, receipt matches current framework tree, 21 reviewed source files unchanged. Edit gates closed. No runtime/schema or version change. Wave remains implementing until operator authorizes closure; no commit or package requested.

**Implementation evidence and review handoff (2026-09-14):**

Scope: AC1–5, host-neutral task-fit allocation across Prepare-to-Close; no runtime/schema/host scheduler. Reviewed working-tree fingerprint (SHA-256 of sorted path-to-SHA-256 JSON): `e071c54d14b18f944b15d490c2bb657573844b9039cfb54160887d9a7265bfc8`. Individual content hashes are reconstructible from this exact path set; receiving reviewers snapshot and compare these paths before/after review.

Changed paths:

- `.wavefoundry/framework/install/lifecycle-prompts/close-wave.prompt.md`
- `.wavefoundry/framework/install/lifecycle-prompts/implement-wave.prompt.md`
- `.wavefoundry/framework/install/lifecycle-prompts/prepare-wave.prompt.md`
- `.wavefoundry/framework/install/lifecycle-prompts/review-wave.prompt.md`
- `.wavefoundry/framework/scripts/tests/test_render_agent_surfaces.py`
- `.wavefoundry/framework/seeds/050-agent-entry-surface-bootstrap.prompt.md`
- `.wavefoundry/framework/seeds/100-project-prompt-surface-bootstrap.prompt.md`
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`
- `.wavefoundry/framework/seeds/180-implement-feature.prompt.md`
- `AGENTS.md`
- `docs/agents/platform-mapping.md`
- `docs/agents/wave-coordinator.md`
- `docs/contributing/agent-team-workflow.md`
- `docs/prompts/agent-routing-concurrency.prompt.md`
- `docs/prompts/close-wave.prompt.md`
- `docs/prompts/implement-feature.prompt.md`
- `docs/prompts/implement-wave.prompt.md`
- `docs/prompts/pause-wave.prompt.md`
- `docs/prompts/prepare-wave.prompt.md`
- `docs/prompts/review-wave.prompt.md`
- `docs/prompts/upgrade-wavefoundry.prompt.md`

**Bounded worker assignment and coordinator acceptance:** `readiness_qa` owned only `.wavefoundry/framework/scripts/tests/test_render_agent_surfaces.py`; forbidden all guidance, runtime, wave and lifecycle files. AC2/3/5, dependency: canonical draft/pointer wording; interface: public `render_agent_surfaces` / existing platform entry renderer and existing BriefingLoopCarrierTests. Brief required MCP-first outline/read, five focused tests, negative controls, honest simulated-merge/native-host limits, exact commands/results. Root took sole guidance ownership after the first writing lane returned no edits; no write overlap. Root reread the entire test diff and all changed guidance, checked phase reachability and stale-inheritance replacements, and ran the normal surface renderer.

**Observed verification:** test worker ran `python3 -B -m unittest test_render_agent_surfaces.HostNeutralOrchestrationCarrierTests test_render_agent_surfaces.BriefingLoopCarrierTests -v` from the scripts/tests directory: 8 passed, zero skips, 0.169 seconds; 40 deletion/reversal controls. Before guidance, fresh Prepare pointer tests failed for the missing owner, not an infrastructure error. `wf_sync_surfaces(mode="run")` passed with no changes but inherited Git-license warning; normal `wf render-surfaces` passed with Homebrew Python and CommandLineTools Git on PATH. `git diff --check` passed. Full suite subsequently passed outside the sandbox: 9,013 tests, 91 files, 21 skips, 603.447 seconds. First sandbox attempt failed dashboard access and was interrupted, not counted as passing.

**Next action / unresolved items:** independent code, QA and docs-contract delivery approvals are recorded; full suite and docs gate passed. Implementation is complete; await operator decision on closure. No approval of closure or commit. No native Claude/Antigravity/Copilot execution, automatic authored-prose migration, cost saving or model-adherence claim. Model/usage cost data unavailable; focused test elapsed time above is measured, not a lifecycle speed benchmark.

**Independent delivery review:**

- Code reviewer: 8 focused tests passed, zero skips; six independent effective mutants caught (model fallback, MCP inheritance, review pending, upgrade conflict, review pointer, fresh Close capability). A template probe initially intercepted no reads and was discarded; corrected `Path.open` boundary probe failed for the intended assertion. All 21 reviewed path hashes stable.
- QA reviewer: five new carrier tests passed, four independent public-render missing-pointer mutants caught (Prepare/Implement/Review/Close). Walkthroughs: ambiguous readiness uses sufficient reasoning capability; deterministic bounded implementation may use lighter capability only at the same quality bar; difficult review uses a fresh context with adequate depth; routine Close uses adequate capability and escalates unresolved judgments, never self-authorizing closure. No delegation -> disclosed sequential implementation; no model selector -> current model; parent MCP without worker MCP -> documented fallback/Gapfill; no independent context -> required review pending. These are guidance walkthroughs, not native-host benchmarks.
- Docs-contract reviewer: independently authored the documented merge against 11 pre-change destination fixtures with customized prose and managed sentinels. First pass changed 11, second zero; reverse-edit comparison preserved every other byte. Missing pointer/deleted customization controls detected; duplicate placement and conflicting cheapest-worker instruction caused stop without overwrite. Fixture evidence is authored reconciliation, not automatic upgrader behavior.
- QA and docs-contract independently recomputed the handoff fingerprint above, verified the current 21-file tree and accepted artifact-only review plus the actual bounded test assignment. Both initially noted incomplete progress evidence, resolved by this existing-record update without changing reviewed source. No source blocker remains. Full-suite and docs validation also passed.

| Detection control | Evidence |
| --- | --- |
| 40 semantic/pointer deletions and reversals | HostNeutralOrchestrationCarrierTests detected all; focused tests have no skips. |
| Six independent code-review mutants | Each expected assertion failed, zero errors/skips; no effective survivor. |
| Four public fresh-render missing-template-pointer mutants | Each phase produced expected `AssertionError: 0 != 1`; incorrect initial read injection excluded. |
| Customized authored merge negatives | Missing pointer and lost content detected; conflicting/ambiguous intent was not overwritten. |

## Readiness Review

Review-plan stop condition: all Requirements, AC and Scope branches resolved. Host choice is per task/wave, sequential work is allowed, review independence remains required, and authored upgrades need a merge rather than a renderer-only claim. No operator questions remain.

Council primer (standard, adversarial/constructive/simplicity): old MCP inheritance claims and customized prompts could contradict portable guidance. Amended finite scope includes seed050 and AGENTS/coordinator clauses; actual worker capability replaces presumed inheritance.

Independent seats: architecture approved after that scope correction; security approved authority and fallback boundaries; QA approved AC falsifiers and ran the existing BriefingLoopCarrierTests (3 passed, no skips, deletion/reversal controls detected); reality-checker approved the guidance-only approach and required the no-independent-context outcome. Rotating docs-contract approved lifecycle-wide task-fit allocation and selected seed180 plus authored reconciliation over new renderer-owned migration machinery.

Anonymized synthesis: all final seat findings align on one canonical owner, explicit phase delivery, honest capabilities and unchanged independence. Reattached roster: architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, docs-contract-reviewer. Unanimous final approval, no remaining blocker; medium propagation omission corrected before approval. The current-carrier tests prove feasibility only, not the new policy or native-host execution.
