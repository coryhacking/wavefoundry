# Fresh Install Validation and Resume

Change ID: `1yp0x-bug fresh-install-validation-and-resume`
Change Status: `implementing`
Owner: Engineering
Status: active
Last verified: 2026-09-22
Wave: 1yp0y pre-release-install-reliability

## Rationale

A 1.25.0+pqn7 Windows installer reported blocking framework-model facts in project performance docs, empty upgrade-policy markers, context exhaustion and a partially authored prompt manifest. Fix the first two framework gaps and make resumption explicit before the next release. Current source confirms that docs_constants_validators applies framework-internal facts based on target filenames alone. It also confirms an existing MCP renderer, wf_sync_surfaces, reaches upgrade-policy reconciliation: the report's claim that no MCP equivalent exists is incorrect. The successful install-log resumption is evidence to retain that mechanism, not replace it.

## Requirements

1. Scope mandatory framework-internal docs/code-constant claims to the framework source repository using the explicit boolean docs_lint.framework_internal_constants in docs/workflow-config.json, enabled only in this source repository. Absence or false selects consumer behavior; a present non-boolean value or unreadable/malformed configuration reports a configuration error rather than silently disabling validation. Do not infer applicability from document names or packaged scripts. Preserve this project-owned opt-in through setup/upgrade absent-only defaults; do not seed it into consuming projects. Inventory the entire claim table (performance-budget, RELIABILITY and MCP specification), separating framework-self-documentation from genuinely generic target rules. Preserve missing/mismatched-claim detection in the source repository and generic structural validation in consuming repositories. Without the opt-in the nine mandatory claim-table entries are not checked, even if consumers voluntarily mention those facts. Existing optional CHANGELOG constant-claim checks remain unchanged; generic structural and wave-scaffolding checks remain active.
2. Keep seed-070 focused on the target project's quality and performance posture. Do not require consumers to copy model identifiers or chunker versions into project docs to appease a mis-scoped validator. Add concise guidance only where needed to distinguish framework tooling from product architecture.
3. Seeds 012 and 100 name wf_sync_surfaces(mode='run') when MCP is attached and wf render-surfaces as CLI fallback after required prompt/role sources exist. Explain that owned upgrade-policy regions must be populated by rendering; empty markers are insufficient. Update the tool description/help/spec to reflect actual renderer scope. Do not add a duplicate wf_render_surfaces tool, hand-copy UPGRADE_POLICY_BLOCK or expand the MCP renderer's permission-allowlist authority.
4. Seed 012 offers an optional session checkpoint after step 2.8, keeping the existing install-log row structure and completion semantics. On resuming partial seed-100 work, inventory actual prompt files and the manifest against the current canonical public-prompt catalog and conditional rules, preserve project-authored content, create/reconcile only missing or stale required surfaces, render owned regions, then audit before marking 2.9 complete. Do not hardcode the field report's count of 22 or pretend an agent-authored multi-file step is transactional.
5. Record per-sentence propagation for changed seed guidance, renderer/help constants and Wavefoundry's local install/upgrade surfaces. Validation errors must not be suppressed merely to advance the install log. Keep the field report's claimed resolutions distinct from reproduced evidence: its model-fact example includes colons that the current exact regex does not accept.

## Scope

In scope: docs-constant applicability, renderer discoverability, checkpoint/resume guidance and regression coverage. Intended owners: docs/workflow-config.json (source-only opt-in), wave_lint_lib/docs_constants_validators.py and its existing call sites as needed; seed 070, 012 and 100; wf_sync_surfaces docstring/help/spec; local install prompt and applicable prompt index; matching tests. No new install-log state machine, bulk regeneration of authored docs, prompt-template overhaul, new MCP tool or permission expansion.

Protected: source-repository drift detection, generic target docs gates, renderer-owned marker boundaries, operator-owned permission allowlists, install-log row numbering, public tool name/schema and project-authored prose. Implementation uses one write owner for overlapping seeds and renderers with the Windows change.

## Acceptance Criteria

- [x] AC-1: A generic consuming-project fixture containing its own performance-budget and reliability docs passes the docs-constant check without Wavefoundry-internal facts; source-repository fixtures still reject missing and mismatched mandatory facts. The applicability oracle is the explicit boolean opt-in: paired source/consumer fixtures differ in that setting, and invalid values produce an error; consumers with packaged framework scripts remain exempt from the mandatory claim table.
- [x] AC-2: The existing public MCP sync path fills an empty upgrade-policy region from real renderer output, preserves surrounding authored prose and is idempotent; regressions retain the permission-rendering boundary.
- [x] AC-3: Authored guidance provides the MCP and CLI paths, optional checkpoint and resume inventory. A partial-install fixture/walkthrough resumes from uncompleted 2.9, verifies the conditional catalog and manifest, and only marks completion after the real audit accepts the result.
- [x] AC-4: A propagation table accounts for every changed guidance sentence, and edited tool descriptions/specifications match actual capability without adding tool/schema surface.

## Tasks

- [x] Implement the operator-approved explicit docs-lint opt-in and census all docs-constant claims; record applicability decisions.
- [x] Repair applicability and add consumer/source counterexamples through real validation entry points.
- [x] Update canonical seeds, MCP description/help and local carriers; record propagation table.
- [x] Exercise public rendering on a producer-built partial install and verify resume/audit behavior with negative controls designed during implementation.
- [x] Obtain independent code, QA and docs-contract review; run required docs and framework gates.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Validator applicability | implementer | readiness | Preserve source drift detection |
| Seed and surface guidance | implementer | Windows prerequisite/remediation guidance | Serialize overlapping install docs |
| Independent verification | reviewer lanes | implementation | Read-only source review; coordinator records evidence |

## Serialization Points

- `.wavefoundry/framework/scripts/wave_lint_lib/docs_constants_validators.py`
- `.wavefoundry/framework/scripts/wave_lint_lib/cli.py`
- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/docs_handlers.py`
- `.wavefoundry/framework/scripts/tests/`
- `.wavefoundry/framework/seeds/012-install-wavefoundry-phase-2.prompt.md`
- `.wavefoundry/framework/seeds/070-quality-and-debt.prompt.md`
- `.wavefoundry/framework/seeds/100-project-prompt-surface-bootstrap.prompt.md`
- `docs/prompts/install-wavefoundry.prompt.md`
- `docs/specs/mcp-tool-surface.md`

## Affected Architecture Docs

Update testing-architecture.md for source-versus-consumer validation coverage and data-and-control-flow.md if the install/audit contract description needs correction. No new runtime subsystem or ownership layer.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Removes misplaced install blocker without weakening source validation |
| AC-2 | required | Demonstrates existing supported MCP remedy |
| AC-3 | required | Makes partial completion safely recoverable |
| AC-4 | required | Guidance must reach installers |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-22 | Use explicit docs_lint.framework_internal_constants boolean opt-in | Operator approved replacing the unsubstantiated existing source-identity premise | No filename or source-layout heuristic; absent/false means consumer, invalid configuration errors |
| 2026-09-22 | Select scoped validation and existing-renderer guidance | Addresses root causes with existing mechanisms | Forcing internal facts into every project contaminates target docs; new MCP alias and manual constant copying duplicate existing capability |
| 2026-09-22 | Retain install-log granularity with explicit resume inventory | Existing row recovery worked in the report | Per-file persistent substeps add lifecycle complexity; calling the whole seed atomic is inaccurate |

## Risks

| Risk | Mitigation |
| --- | --- |
| Applicability switch disables source checks accidentally | Paired source/packaged-consumer fixtures and missing-claim control |
| Renderer used to expand permissions | Preserve existing no-allowlist-expansion test and public-path probe |
| Static file-count guidance drifts | Derive expected set from canonical catalog and conditional semantics |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-22 | Readback: explicit internal-fact opt-in removes consumer-only install blockers while preserving source checks; existing sync renderer and resumable install guidance remain within current permissions. Owners: validator, source workflow-config, tests, seeds/tool prose/local carriers. | Current readiness approvals |
| 2026-09-22 | Thought: parallelize isolated validator implementation and authored guidance while coordinator owns Windows diagnostics; integrate before tests and delivery review | Disjoint file ownership |
| 2026-09-22 | Planned all four reported install issues with corrected root-cause attribution | docs_constants_validators._claims/check_docs_constants; docs_handlers.run_sync_surfaces; render_agent_surfaces upgrade-policy reconciliation; seeds 070/012/100 |
| 2026-09-22 | Explicit source opt-in implemented with nine-claim census, source/consumer counterexamples and real public sync/audit fixtures. Bypassing opt-in restores four consumer false errors. | implementation-evidence.md; test_docs_constants_lint.py; test_install_resume_integration.py |

## Session Handoff

Implementation underway following typed readiness approval and successful Prepare. Coordinator owns prerequisite diagnostics; isolated validator and guidance changes are integrated. Native Windows qualification remains unproven on this Darwin host and is operator-deferred to external testing after the next release. Final review and close-readiness checks are authorized; no commit requested.
